"""
core/result_db.py 單元測試

使用 in-memory SQLite 測試 ResultDB 的 CRUD、比較、flaky 偵測。
"""

import pytest

from core.result_db import ResultDB


@pytest.fixture
def db(tmp_path):
    """每個測試取得獨立的 SQLite DB"""
    return ResultDB(db_path=tmp_path / "test.db")


@pytest.mark.unit
class TestResultDBRun:
    """Run 管理"""

    @pytest.mark.unit
    def test_start_run(self, db):
        """建立 run 回傳 run_id"""
        run_id = db.start_run(platform="android", env="dev")
        assert isinstance(run_id, str)
        assert len(run_id) > 0

    @pytest.mark.unit
    def test_end_run_updates_stats(self, db):
        """結束 run 時更新統計"""
        run_id = db.start_run()
        db.record(run_id, "test_a", "passed", 1.0)
        db.record(run_id, "test_b", "failed", 2.0, "AssertionError")
        db.record(run_id, "test_c", "skipped", 0.0)
        db.end_run(run_id)

        summary = db.get_run_summary(run_id)
        assert summary["total"] == 3
        assert summary["passed"] == 1
        assert summary["failed"] == 1
        assert summary["skipped"] == 1

    @pytest.mark.unit
    def test_get_run_summary_nonexistent(self, db):
        """查詢不存在的 run 回傳 None"""
        assert db.get_run_summary("nonexistent") is None


@pytest.mark.unit
class TestResultDBRecord:
    """結果寫入與查詢"""

    @pytest.mark.unit
    def test_record_and_history(self, db):
        """寫入後可查詢歷史"""
        run_id = db.start_run()
        db.record(run_id, "test_login", "passed", 1.5)
        db.record(run_id, "test_login", "failed", 2.0, "timeout")

        history = db.get_history("test_login", limit=10)
        assert len(history) == 2

    @pytest.mark.unit
    def test_history_order(self, db):
        """歷史按時間倒序"""
        run_id = db.start_run()
        db.record(run_id, "test_x", "passed", 1.0)
        db.record(run_id, "test_x", "failed", 2.0)

        history = db.get_history("test_x")
        # 最後寫入的在前
        assert history[0]["outcome"] == "failed"

    @pytest.mark.unit
    def test_history_limit(self, db):
        """limit 限制回傳筆數"""
        run_id = db.start_run()
        for i in range(20):
            db.record(run_id, "test_many", "passed", 1.0)

        history = db.get_history("test_many", limit=5)
        assert len(history) == 5


@pytest.mark.unit
class TestResultDBCompare:
    """Run 比較"""

    @pytest.mark.unit
    def test_compare_runs(self, db):
        """比較兩次 run 的差異"""
        run_a = db.start_run()
        db.record(run_a, "test_1", "passed", 1.0)
        db.record(run_a, "test_2", "failed", 1.0)
        db.record(run_a, "test_3", "failed", 1.0)
        db.end_run(run_a)

        run_b = db.start_run()
        db.record(run_b, "test_1", "passed", 1.0)
        db.record(run_b, "test_2", "passed", 1.0)  # fixed
        db.record(run_b, "test_3", "failed", 1.0)  # still failing
        db.record(run_b, "test_4", "failed", 1.0)  # new failure
        db.end_run(run_b)

        diff = db.compare_runs(run_a, run_b)
        assert "test_2" in diff["fixed"]
        assert "test_3" in diff["still_failing"]
        assert "test_4" in diff["new_failures"]
        assert "test_4" in diff["new_tests"]


@pytest.mark.unit
class TestResultDBFlaky:
    """Flaky 偵測"""

    @pytest.mark.unit
    def test_detect_flaky(self, db):
        """交替 pass/fail 的測試被偵測為 flaky"""
        run_id = db.start_run()
        for i in range(10):
            outcome = "passed" if i % 2 == 0 else "failed"
            db.record(run_id, "test_flaky", outcome, 1.0)
        db.end_run(run_id)

        flaky = db.get_flaky_tests(window=20)
        names = [f["test_name"] for f in flaky]
        assert "test_flaky" in names

    @pytest.mark.unit
    def test_stable_not_flaky(self, db):
        """全部通過的測試不是 flaky"""
        run_id = db.start_run()
        for _ in range(5):
            db.record(run_id, "test_stable", "passed", 1.0)
        db.end_run(run_id)

        flaky = db.get_flaky_tests()
        names = [f["test_name"] for f in flaky]
        assert "test_stable" not in names


@pytest.mark.unit
class TestResultDBTrend:
    """趨勢分析"""

    @pytest.mark.unit
    def test_pass_rate_trend(self, db):
        """通過率趨勢有資料"""
        run_id = db.start_run()
        db.record(run_id, "test_a", "passed", 1.0)
        db.record(run_id, "test_b", "failed", 1.0)
        db.end_run(run_id)

        trend = db.get_pass_rate_trend()
        assert len(trend) == 1
        assert trend[0]["pass_rate"] == 0.5

    @pytest.mark.unit
    def test_recent_runs(self, db):
        """取得最近 run"""
        r1 = db.start_run()
        db.end_run(r1)
        r2 = db.start_run()
        db.end_run(r2)

        runs = db.get_recent_runs(limit=5)
        assert len(runs) == 2
