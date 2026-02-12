"""
utils.smart_selector 單元測試
驗證 SmartSelector 的風險計算、排序、篩選與報告功能。
"""

import sqlite3
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from utils.smart_selector import TestRisk, SmartSelector


def _create_test_db(db_path: str, rows: list[tuple]) -> None:
    """建立測試用 SQLite 資料庫並寫入測試資料"""
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS results (
            test_name TEXT,
            outcome TEXT,
            duration REAL,
            created_at TEXT
        )
        """
    )
    conn.executemany(
        "INSERT INTO results (test_name, outcome, duration, created_at) VALUES (?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()


@pytest.mark.unit
class TestTestRiskDataclass:
    """TestRisk 資料類別"""

    @pytest.mark.unit
    def test_create_test_risk(self):
        """建立 TestRisk 實例"""
        risk = TestRisk(
            test_name="test_login",
            risk_score=0.75,
            recent_fail_rate=0.5,
            flaky_score=0.3,
            avg_duration=2.5,
            last_outcome="failed",
            run_count=10,
        )
        assert risk.test_name == "test_login"
        assert risk.risk_score == 0.75
        assert risk.recent_fail_rate == 0.5
        assert risk.flaky_score == 0.3
        assert risk.avg_duration == 2.5
        assert risk.last_outcome == "failed"
        assert risk.run_count == 10


@pytest.mark.unit
class TestSmartSelectorInit:
    """SmartSelector 初始化"""

    @pytest.mark.unit
    def test_init_default_params(self):
        """預設參數"""
        selector = SmartSelector()
        assert selector._db_path == "reports/test_results.db"
        assert selector._window == 20
        assert selector._w_fail == 0.5
        assert selector._w_flaky == 0.3
        assert selector._w_last == 0.2

    @pytest.mark.unit
    def test_init_custom_weights(self):
        """自訂權重"""
        selector = SmartSelector(weights=(0.6, 0.2, 0.2))
        assert selector._w_fail == 0.6
        assert selector._w_flaky == 0.2
        assert selector._w_last == 0.2

    @pytest.mark.unit
    def test_init_custom_window(self):
        """自訂 window"""
        selector = SmartSelector(window=50)
        assert selector._window == 50


@pytest.mark.unit
class TestSmartSelectorRankTests:
    """SmartSelector.rank_tests 方法"""

    @pytest.mark.unit
    def test_rank_tests_no_db_returns_empty(self, tmp_path):
        """DB 不存在時回傳空列表"""
        selector = SmartSelector(result_db_path=str(tmp_path / "nonexistent.db"))
        result = selector.rank_tests()
        assert result == []

    @pytest.mark.unit
    def test_rank_tests_with_db_returns_ranked_list(self, tmp_path):
        """有 DB 資料時回傳風險排序列表"""
        db_path = str(tmp_path / "test.db")
        _create_test_db(db_path, [
            # test_a: 全部失敗 -> 高風險
            ("test_a", "failed", 1.0, "2025-01-01 10:00:00"),
            ("test_a", "failed", 1.2, "2025-01-01 10:01:00"),
            ("test_a", "failed", 0.9, "2025-01-01 10:02:00"),
            # test_b: 全部通過 -> 低風險
            ("test_b", "passed", 0.5, "2025-01-01 10:00:00"),
            ("test_b", "passed", 0.6, "2025-01-01 10:01:00"),
            ("test_b", "passed", 0.4, "2025-01-01 10:02:00"),
        ])

        selector = SmartSelector(result_db_path=db_path)
        ranked = selector.rank_tests()

        assert len(ranked) == 2
        # test_a (全失敗) 應排在前面
        assert ranked[0].test_name == "test_a"
        assert ranked[0].risk_score > ranked[1].risk_score
        assert ranked[1].test_name == "test_b"
        assert ranked[1].risk_score == 0.0  # 全部通過

    @pytest.mark.unit
    def test_rank_tests_flaky_detection(self, tmp_path):
        """交替 pass/fail 的測試有較高的 flaky_score"""
        db_path = str(tmp_path / "test.db")
        _create_test_db(db_path, [
            # test_flaky: 交替通過/失敗
            ("test_flaky", "passed", 1.0, "2025-01-01 10:00:00"),
            ("test_flaky", "failed", 1.0, "2025-01-01 10:01:00"),
            ("test_flaky", "passed", 1.0, "2025-01-01 10:02:00"),
            ("test_flaky", "failed", 1.0, "2025-01-01 10:03:00"),
        ])

        selector = SmartSelector(result_db_path=db_path)
        ranked = selector.rank_tests()

        assert len(ranked) == 1
        assert ranked[0].flaky_score > 0.5  # 高不穩定性


@pytest.mark.unit
class TestSmartSelectorSelect:
    """SmartSelector.select 方法"""

    @pytest.mark.unit
    def test_select_with_threshold(self, tmp_path):
        """以閾值篩選高風險測試"""
        db_path = str(tmp_path / "test.db")
        _create_test_db(db_path, [
            ("test_high", "failed", 1.0, "2025-01-01 10:00:00"),
            ("test_high", "failed", 1.0, "2025-01-01 10:01:00"),
            ("test_low", "passed", 0.5, "2025-01-01 10:00:00"),
            ("test_low", "passed", 0.5, "2025-01-01 10:01:00"),
        ])

        selector = SmartSelector(result_db_path=db_path)
        selected = selector.select(threshold=0.3)

        # 只有 test_high 應被選中
        assert len(selected) >= 1
        assert all(t.risk_score >= 0.3 for t in selected)

    @pytest.mark.unit
    def test_select_with_max_count(self, tmp_path):
        """以 max_count 限制回傳數量"""
        db_path = str(tmp_path / "test.db")
        _create_test_db(db_path, [
            ("test_a", "failed", 1.0, "2025-01-01 10:00:00"),
            ("test_b", "failed", 1.0, "2025-01-01 10:00:00"),
            ("test_c", "failed", 1.0, "2025-01-01 10:00:00"),
        ])

        selector = SmartSelector(result_db_path=db_path)
        selected = selector.select(max_count=1)

        assert len(selected) == 1

    @pytest.mark.unit
    def test_select_threshold_zero_returns_all(self, tmp_path):
        """閾值為 0 時回傳所有測試"""
        db_path = str(tmp_path / "test.db")
        _create_test_db(db_path, [
            ("test_a", "passed", 1.0, "2025-01-01 10:00:00"),
            ("test_b", "passed", 1.0, "2025-01-01 10:00:00"),
        ])

        selector = SmartSelector(result_db_path=db_path)
        selected = selector.select(threshold=0.0)

        assert len(selected) == 2


@pytest.mark.unit
class TestSmartSelectorGetSkipList:
    """SmartSelector.get_skip_list 方法"""

    @pytest.mark.unit
    def test_get_skip_list_returns_low_risk_names(self, tmp_path):
        """回傳低風險測試名稱"""
        db_path = str(tmp_path / "test.db")
        _create_test_db(db_path, [
            ("test_high", "failed", 1.0, "2025-01-01 10:00:00"),
            ("test_high", "failed", 1.0, "2025-01-01 10:01:00"),
            ("test_low", "passed", 0.5, "2025-01-01 10:00:00"),
            ("test_low", "passed", 0.5, "2025-01-01 10:01:00"),
        ])

        selector = SmartSelector(result_db_path=db_path)
        skip_list = selector.get_skip_list(threshold=0.3)

        assert "test_low" in skip_list
        assert "test_high" not in skip_list


@pytest.mark.unit
class TestSmartSelectorCalculateRisks:
    """SmartSelector._calculate_risks 方法"""

    @pytest.mark.unit
    def test_calculate_risks_fail_rate(self, tmp_path):
        """失敗率計算正確"""
        db_path = str(tmp_path / "test.db")
        _create_test_db(db_path, [
            ("test_x", "failed", 1.0, "2025-01-01 10:00:00"),
            ("test_x", "passed", 1.0, "2025-01-01 10:01:00"),
            ("test_x", "failed", 1.0, "2025-01-01 10:02:00"),
            ("test_x", "passed", 1.0, "2025-01-01 10:03:00"),
        ])

        selector = SmartSelector(result_db_path=db_path)
        ranked = selector.rank_tests()

        assert len(ranked) == 1
        # 4 筆中 2 筆失敗 -> fail_rate = 0.5
        assert ranked[0].recent_fail_rate == 0.5

    @pytest.mark.unit
    def test_calculate_risks_last_failed_weight(self, tmp_path):
        """最後一次失敗增加風險分數"""
        db_path = str(tmp_path / "test.db")
        # test_last_fail: 最後一次是失敗
        _create_test_db(db_path, [
            ("test_last_fail", "passed", 1.0, "2025-01-01 10:00:00"),
            ("test_last_fail", "failed", 1.0, "2025-01-01 10:01:00"),
        ])

        selector = SmartSelector(result_db_path=db_path)
        ranked = selector.rank_tests()

        assert len(ranked) == 1
        # last_outcome 是 failed (最新的 created_at DESC)
        assert ranked[0].last_outcome == "failed"
        # risk_score = 0.5 * 0.5 + 0.3 * 1.0 + 0.2 * 1.0 = 0.75
        assert ranked[0].risk_score > 0.0

    @pytest.mark.unit
    def test_calculate_risks_avg_duration(self, tmp_path):
        """平均執行時間計算正確"""
        db_path = str(tmp_path / "test.db")
        _create_test_db(db_path, [
            ("test_dur", "passed", 2.0, "2025-01-01 10:00:00"),
            ("test_dur", "passed", 4.0, "2025-01-01 10:01:00"),
        ])

        selector = SmartSelector(result_db_path=db_path)
        ranked = selector.rank_tests()

        assert len(ranked) == 1
        assert ranked[0].avg_duration == 3.0

    @pytest.mark.unit
    def test_calculate_risks_risk_score_clamped(self, tmp_path):
        """風險分數限制在 0.0 ~ 1.0"""
        db_path = str(tmp_path / "test.db")
        _create_test_db(db_path, [
            ("test_max", "failed", 1.0, "2025-01-01 10:00:00"),
        ])

        # 使用很高的權重
        selector = SmartSelector(result_db_path=db_path, weights=(1.0, 1.0, 1.0))
        ranked = selector.rank_tests()

        assert len(ranked) == 1
        assert ranked[0].risk_score <= 1.0


@pytest.mark.unit
class TestSmartSelectorPrintReport:
    """SmartSelector.print_report 方法"""

    @pytest.mark.unit
    def test_print_report_no_error(self, tmp_path, capsys):
        """print_report 不應拋出錯誤"""
        db_path = str(tmp_path / "test.db")
        _create_test_db(db_path, [
            ("test_a", "failed", 1.0, "2025-01-01 10:00:00"),
            ("test_b", "passed", 0.5, "2025-01-01 10:00:00"),
        ])

        selector = SmartSelector(result_db_path=db_path)
        selector.print_report(top_n=10)

        captured = capsys.readouterr()
        assert "智慧選測" in captured.out
        assert "test_a" in captured.out
        assert "test_b" in captured.out

    @pytest.mark.unit
    def test_print_report_empty_db(self, tmp_path, capsys):
        """空 DB 時 print_report 不應拋出錯誤"""
        db_path = str(tmp_path / "test.db")
        _create_test_db(db_path, [])

        selector = SmartSelector(result_db_path=db_path)
        selector.print_report()

        captured = capsys.readouterr()
        assert "共 0 個測試" in captured.out

    @pytest.mark.unit
    def test_print_report_nonexistent_db(self, tmp_path, capsys):
        """DB 不存在時 print_report 不拋錯"""
        selector = SmartSelector(result_db_path=str(tmp_path / "missing.db"))
        selector.print_report()

        captured = capsys.readouterr()
        assert "共 0 個測試" in captured.out
