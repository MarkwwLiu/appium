"""
utils.report_plugin 單元測試
驗證自訂 pytest 報告 plugin 的 TestMetrics 類別與 pytest hooks。
"""

import pytest
from unittest.mock import MagicMock, patch, call
from collections import defaultdict


@pytest.mark.unit
class TestTestMetricsInit:
    """TestMetrics.__init__ 初始化"""

    @pytest.mark.unit
    def test_results_empty_defaultdict(self):
        """初始化時 results 為空的 defaultdict"""
        from utils.report_plugin import TestMetrics

        metrics = TestMetrics()
        assert isinstance(metrics.results, defaultdict)
        assert len(metrics.results) == 0

    @pytest.mark.unit
    def test_durations_empty_dict(self):
        """初始化時 durations 為空字典"""
        from utils.report_plugin import TestMetrics

        metrics = TestMetrics()
        assert isinstance(metrics.durations, dict)
        assert len(metrics.durations) == 0

    @pytest.mark.unit
    def test_start_time_zero(self):
        """初始化時 start_time 為 0"""
        from utils.report_plugin import TestMetrics

        metrics = TestMetrics()
        assert metrics.start_time == 0

    @pytest.mark.unit
    def test_results_defaultdict_returns_list_for_new_key(self):
        """results 存取不存在的 key 時回傳空 list"""
        from utils.report_plugin import TestMetrics

        metrics = TestMetrics()
        assert metrics.results["nonexistent"] == []


@pytest.mark.unit
class TestTestMetricsRecord:
    """TestMetrics.record — 記錄測試結果"""

    @pytest.mark.unit
    def test_record_passed_test(self):
        """記錄 passed 測試"""
        from utils.report_plugin import TestMetrics

        metrics = TestMetrics()
        metrics.record("tests/test_login.py::test_success", "passed", 1.5)

        assert "tests/test_login.py::test_success" in metrics.results["passed"]
        assert metrics.durations["tests/test_login.py::test_success"] == 1.5

    @pytest.mark.unit
    def test_record_failed_test(self):
        """記錄 failed 測試"""
        from utils.report_plugin import TestMetrics

        metrics = TestMetrics()
        metrics.record("tests/test_login.py::test_fail", "failed", 2.3)

        assert "tests/test_login.py::test_fail" in metrics.results["failed"]
        assert metrics.durations["tests/test_login.py::test_fail"] == 2.3

    @pytest.mark.unit
    def test_record_skipped_test(self):
        """記錄 skipped 測試"""
        from utils.report_plugin import TestMetrics

        metrics = TestMetrics()
        metrics.record("tests/test_login.py::test_skip", "skipped", 0.0)

        assert "tests/test_login.py::test_skip" in metrics.results["skipped"]
        assert metrics.durations["tests/test_login.py::test_skip"] == 0.0

    @pytest.mark.unit
    def test_record_multiple_tests_same_outcome(self):
        """同一 outcome 可記錄多個測試"""
        from utils.report_plugin import TestMetrics

        metrics = TestMetrics()
        metrics.record("test1", "passed", 1.0)
        metrics.record("test2", "passed", 2.0)
        metrics.record("test3", "passed", 0.5)

        assert len(metrics.results["passed"]) == 3
        assert len(metrics.durations) == 3

    @pytest.mark.unit
    def test_record_duration_stored_correctly(self):
        """duration 正確儲存"""
        from utils.report_plugin import TestMetrics

        metrics = TestMetrics()
        metrics.record("slow_test", "passed", 99.99)

        assert metrics.durations["slow_test"] == 99.99


@pytest.mark.unit
class TestPytestSessionStart:
    """pytest_sessionstart hook"""

    @pytest.mark.unit
    def test_sets_start_time(self):
        """session 開始時設定 start_time"""
        import utils.report_plugin as rp

        mock_session = MagicMock()
        original_start_time = rp._metrics.start_time

        with patch("utils.report_plugin.time") as mock_time:
            mock_time.time.return_value = 1000.0
            rp.pytest_sessionstart(mock_session)

        assert rp._metrics.start_time == 1000.0

        # 復原
        rp._metrics.start_time = original_start_time

    @pytest.mark.unit
    def test_calls_time_time(self):
        """session 開始時呼叫 time.time()"""
        import utils.report_plugin as rp

        mock_session = MagicMock()

        with patch("utils.report_plugin.time") as mock_time:
            mock_time.time.return_value = 500.0
            rp.pytest_sessionstart(mock_session)
            mock_time.time.assert_called_once()

        # 復原
        rp._metrics.start_time = 0


@pytest.mark.unit
class TestPytestRuntestLogreport:
    """pytest_runtest_logreport hook"""

    @pytest.mark.unit
    def test_records_call_phase(self):
        """when='call' 時記錄結果"""
        import utils.report_plugin as rp

        # 儲存原始 metrics 並替換
        original_metrics = rp._metrics
        rp._metrics = MagicMock()

        mock_report = MagicMock()
        mock_report.when = "call"
        mock_report.nodeid = "tests/test_example.py::test_one"
        mock_report.outcome = "passed"
        mock_report.duration = 1.23

        rp.pytest_runtest_logreport(mock_report)

        rp._metrics.record.assert_called_once_with(
            "tests/test_example.py::test_one", "passed", 1.23
        )

        # 復原
        rp._metrics = original_metrics

    @pytest.mark.unit
    def test_ignores_setup_phase(self):
        """when='setup' 時不記錄"""
        import utils.report_plugin as rp

        original_metrics = rp._metrics
        rp._metrics = MagicMock()

        mock_report = MagicMock()
        mock_report.when = "setup"

        rp.pytest_runtest_logreport(mock_report)

        rp._metrics.record.assert_not_called()

        rp._metrics = original_metrics

    @pytest.mark.unit
    def test_ignores_teardown_phase(self):
        """when='teardown' 時不記錄"""
        import utils.report_plugin as rp

        original_metrics = rp._metrics
        rp._metrics = MagicMock()

        mock_report = MagicMock()
        mock_report.when = "teardown"

        rp.pytest_runtest_logreport(mock_report)

        rp._metrics.record.assert_not_called()

        rp._metrics = original_metrics


@pytest.mark.unit
class TestPytestTerminalSummary:
    """pytest_terminal_summary hook"""

    @pytest.mark.unit
    def test_generates_report_with_counts(self):
        """產生包含 passed/failed/skipped 統計的報告"""
        import utils.report_plugin as rp
        from utils.report_plugin import TestMetrics

        original_metrics = rp._metrics
        rp._metrics = TestMetrics()
        rp._metrics.start_time = 100.0
        rp._metrics.record("test1", "passed", 1.0)
        rp._metrics.record("test2", "passed", 2.0)
        rp._metrics.record("test3", "failed", 0.5)
        rp._metrics.record("test4", "skipped", 0.1)

        mock_writer = MagicMock()
        mock_config = MagicMock()

        with patch("utils.report_plugin.time") as mock_time:
            mock_time.time.return_value = 110.0
            rp.pytest_terminal_summary(mock_writer, 0, mock_config)

        # 驗證 section 被呼叫
        mock_writer.section.assert_called_once_with("Appium Test Report", sep="=")

        # 收集所有 line 呼叫的內容
        line_calls = [c.args[0] for c in mock_writer.line.call_args_list]
        all_text = "\n".join(line_calls)

        assert "4" in all_text  # 總計 4 個測試
        assert "2" in all_text  # 通過 2 個
        assert "1" in all_text  # 失敗 1 個

        rp._metrics = original_metrics

    @pytest.mark.unit
    def test_handles_empty_results(self):
        """沒有測試結果時直接返回"""
        import utils.report_plugin as rp
        from utils.report_plugin import TestMetrics

        original_metrics = rp._metrics
        rp._metrics = TestMetrics()
        rp._metrics.start_time = 100.0

        mock_writer = MagicMock()
        mock_config = MagicMock()

        with patch("utils.report_plugin.time") as mock_time:
            mock_time.time.return_value = 110.0
            rp.pytest_terminal_summary(mock_writer, 0, mock_config)

        # 沒有結果時不應呼叫 section 或 line
        mock_writer.section.assert_not_called()
        mock_writer.line.assert_not_called()

        rp._metrics = original_metrics

    @pytest.mark.unit
    def test_shows_failed_tests(self):
        """失敗測試清單顯示在報告中"""
        import utils.report_plugin as rp
        from utils.report_plugin import TestMetrics

        original_metrics = rp._metrics
        rp._metrics = TestMetrics()
        rp._metrics.start_time = 100.0
        rp._metrics.record("tests/test_a.py::test_broken", "failed", 3.5)
        rp._metrics.record("tests/test_b.py::test_ok", "passed", 1.0)

        mock_writer = MagicMock()
        mock_config = MagicMock()

        with patch("utils.report_plugin.time") as mock_time:
            mock_time.time.return_value = 110.0
            rp.pytest_terminal_summary(mock_writer, 1, mock_config)

        line_calls = [c.args[0] for c in mock_writer.line.call_args_list]
        all_text = "\n".join(line_calls)

        assert "FAIL" in all_text
        assert "tests/test_a.py::test_broken" in all_text

        rp._metrics = original_metrics

    @pytest.mark.unit
    def test_shows_slowest_tests(self):
        """最慢的測試顯示在報告中"""
        import utils.report_plugin as rp
        from utils.report_plugin import TestMetrics

        original_metrics = rp._metrics
        rp._metrics = TestMetrics()
        rp._metrics.start_time = 100.0
        rp._metrics.record("fast_test", "passed", 0.1)
        rp._metrics.record("slow_test", "passed", 10.5)
        rp._metrics.record("medium_test", "passed", 3.0)

        mock_writer = MagicMock()
        mock_config = MagicMock()

        with patch("utils.report_plugin.time") as mock_time:
            mock_time.time.return_value = 115.0
            rp.pytest_terminal_summary(mock_writer, 0, mock_config)

        line_calls = [c.args[0] for c in mock_writer.line.call_args_list]
        all_text = "\n".join(line_calls)

        # 最慢的測試應出現在報告中
        assert "slow_test" in all_text
        assert "10.50s" in all_text

        rp._metrics = original_metrics

    @pytest.mark.unit
    def test_pass_rate_calculation(self):
        """通過率計算正確"""
        import utils.report_plugin as rp
        from utils.report_plugin import TestMetrics

        original_metrics = rp._metrics
        rp._metrics = TestMetrics()
        rp._metrics.start_time = 100.0
        # 3 passed, 1 failed = 75%
        rp._metrics.record("t1", "passed", 1.0)
        rp._metrics.record("t2", "passed", 1.0)
        rp._metrics.record("t3", "passed", 1.0)
        rp._metrics.record("t4", "failed", 1.0)

        mock_writer = MagicMock()
        mock_config = MagicMock()

        with patch("utils.report_plugin.time") as mock_time:
            mock_time.time.return_value = 105.0
            rp.pytest_terminal_summary(mock_writer, 0, mock_config)

        line_calls = [c.args[0] for c in mock_writer.line.call_args_list]
        all_text = "\n".join(line_calls)

        assert "75.0%" in all_text

        rp._metrics = original_metrics

    @pytest.mark.unit
    def test_total_time_displayed(self):
        """總耗時正確顯示"""
        import utils.report_plugin as rp
        from utils.report_plugin import TestMetrics

        original_metrics = rp._metrics
        rp._metrics = TestMetrics()
        rp._metrics.start_time = 100.0
        rp._metrics.record("t1", "passed", 1.0)

        mock_writer = MagicMock()
        mock_config = MagicMock()

        with patch("utils.report_plugin.time") as mock_time:
            mock_time.time.return_value = 125.0  # 25 秒
            rp.pytest_terminal_summary(mock_writer, 0, mock_config)

        line_calls = [c.args[0] for c in mock_writer.line.call_args_list]
        all_text = "\n".join(line_calls)

        assert "25.0" in all_text

        rp._metrics = original_metrics

    @pytest.mark.unit
    def test_only_top_5_slowest_shown(self):
        """最多只顯示最慢的 5 個測試"""
        import utils.report_plugin as rp
        from utils.report_plugin import TestMetrics

        original_metrics = rp._metrics
        rp._metrics = TestMetrics()
        rp._metrics.start_time = 100.0

        for i in range(8):
            rp._metrics.record(f"test_{i}", "passed", float(i + 1))

        mock_writer = MagicMock()
        mock_config = MagicMock()

        with patch("utils.report_plugin.time") as mock_time:
            mock_time.time.return_value = 200.0
            rp.pytest_terminal_summary(mock_writer, 0, mock_config)

        line_calls = [c.args[0] for c in mock_writer.line.call_args_list]
        # 計算包含 "test_" 且有 "s" 的行（slowest 區段中的測試）
        slowest_lines = [
            line for line in line_calls
            if "test_" in line and "s  test_" in line
        ]
        assert len(slowest_lines) == 5

        rp._metrics = original_metrics
