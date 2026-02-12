"""
utils.log_collector 單元測試
驗證 LogCollector 的日誌收集、搜尋、儲存功能。
"""

import subprocess
import pytest
from unittest.mock import MagicMock, patch, call
from pathlib import Path


@pytest.mark.unit
class TestLogCollectorInit:
    """LogCollector 初始化"""

    @pytest.mark.unit
    def test_init_defaults(self, tmp_path):
        """預設參數初始化"""
        with patch("utils.log_collector.LOG_OUTPUT_DIR", tmp_path / "device_logs"):
            from utils.log_collector import LogCollector
            lc = LogCollector()
            assert lc.package_name == ""
            assert lc.platform == "android"
            assert lc._process is None
            assert lc._thread is None
            assert lc._running is False
            assert lc._log_lines == []

    @pytest.mark.unit
    def test_init_creates_output_dir(self, tmp_path):
        """初始化時自動建立輸出目錄"""
        output_dir = tmp_path / "device_logs"
        with patch("utils.log_collector.LOG_OUTPUT_DIR", output_dir):
            from utils.log_collector import LogCollector
            LogCollector()
            assert output_dir.exists()

    @pytest.mark.unit
    def test_init_custom_params(self, tmp_path):
        """自訂參數初始化"""
        with patch("utils.log_collector.LOG_OUTPUT_DIR", tmp_path / "device_logs"):
            from utils.log_collector import LogCollector
            lc = LogCollector(package_name="com.example.app", platform="iOS")
            assert lc.package_name == "com.example.app"
            assert lc.platform == "ios"


@pytest.mark.unit
class TestLogCollectorStart:
    """LogCollector.start 方法"""

    @pytest.mark.unit
    def test_start_already_running_warns(self, tmp_path):
        """已在執行中時發出警告並返回"""
        with patch("utils.log_collector.LOG_OUTPUT_DIR", tmp_path / "device_logs"):
            from utils.log_collector import LogCollector
            lc = LogCollector()
            lc._running = True
            with patch("utils.log_collector.subprocess") as mock_sub:
                lc.start()
                mock_sub.run.assert_not_called()
                mock_sub.Popen.assert_not_called()

    @pytest.mark.unit
    def test_start_android_clears_logs_and_starts_logcat(self, tmp_path):
        """Android 平台先清除 log 再啟動 logcat"""
        with patch("utils.log_collector.LOG_OUTPUT_DIR", tmp_path / "device_logs"):
            from utils.log_collector import LogCollector
            lc = LogCollector(platform="android")

        mock_popen = MagicMock()
        mock_popen.stdout.readline.return_value = ""

        with patch("utils.log_collector.subprocess") as mock_sub:
            mock_sub.Popen.return_value = mock_popen
            lc.start()
            # 驗證 adb logcat -c 被呼叫
            mock_sub.run.assert_called_once_with(
                ["adb", "logcat", "-c"], capture_output=True
            )
            # 驗證 Popen 啟動 logcat
            popen_call = mock_sub.Popen.call_args
            assert popen_call[0][0] == ["adb", "logcat", "-v", "time"]
            assert lc._running is True

    @pytest.mark.unit
    def test_start_android_with_package_name_calls_get_pid(self, tmp_path):
        """Android 有 package_name 時呼叫 _get_pid 取得 PID"""
        with patch("utils.log_collector.LOG_OUTPUT_DIR", tmp_path / "device_logs"):
            from utils.log_collector import LogCollector
            lc = LogCollector(package_name="com.example.app", platform="android")

        mock_popen = MagicMock()
        mock_popen.stdout.readline.return_value = ""

        with patch("utils.log_collector.subprocess") as mock_sub:
            mock_sub.Popen.return_value = mock_popen
            # _get_pid 使用 subprocess.run
            mock_sub.run.return_value = MagicMock(stdout="12345\n")
            lc.start()
            # Popen 指令應包含 --pid
            popen_call = mock_sub.Popen.call_args[0][0]
            assert "--pid" in popen_call

    @pytest.mark.unit
    def test_start_ios_starts_idevicesyslog(self, tmp_path):
        """iOS 平台啟動 idevicesyslog"""
        with patch("utils.log_collector.LOG_OUTPUT_DIR", tmp_path / "device_logs"):
            from utils.log_collector import LogCollector
            lc = LogCollector(platform="ios")

        mock_popen = MagicMock()
        mock_popen.stdout.readline.return_value = ""

        with patch("utils.log_collector.subprocess") as mock_sub:
            mock_sub.Popen.return_value = mock_popen
            lc.start()
            mock_sub.run.assert_not_called()
            popen_call = mock_sub.Popen.call_args[0][0]
            assert popen_call == ["idevicesyslog"]


@pytest.mark.unit
class TestLogCollectorStop:
    """LogCollector.stop 方法"""

    @pytest.mark.unit
    def test_stop_terminates_process_and_returns_log_lines(self, tmp_path):
        """停止時終止 process 並回傳 log 內容"""
        with patch("utils.log_collector.LOG_OUTPUT_DIR", tmp_path / "device_logs"):
            from utils.log_collector import LogCollector
            lc = LogCollector()
            lc._running = True
            lc._log_lines = ["line1", "line2", "line3"]
            mock_process = MagicMock()
            lc._process = mock_process

            result = lc.stop()

            assert lc._running is False
            mock_process.terminate.assert_called_once()
            mock_process.wait.assert_called_once_with(timeout=5)
            assert lc._process is None
            assert result == ["line1", "line2", "line3"]

    @pytest.mark.unit
    def test_stop_no_process(self, tmp_path):
        """沒有 process 時安全停止"""
        with patch("utils.log_collector.LOG_OUTPUT_DIR", tmp_path / "device_logs"):
            from utils.log_collector import LogCollector
            lc = LogCollector()
            lc._running = True
            lc._log_lines = ["line1"]

            result = lc.stop()
            assert result == ["line1"]
            assert lc._running is False


@pytest.mark.unit
class TestLogCollectorSave:
    """LogCollector.save 方法"""

    @pytest.mark.unit
    def test_save_creates_file_with_timestamp(self, tmp_path):
        """儲存 log 到帶時間戳記的檔案"""
        output_dir = tmp_path / "device_logs"
        with patch("utils.log_collector.LOG_OUTPUT_DIR", output_dir):
            from utils.log_collector import LogCollector
            lc = LogCollector()
            lc._log_lines = ["log line 1", "log line 2"]

        with patch("utils.log_collector.LOG_OUTPUT_DIR", output_dir), \
             patch("utils.log_collector.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "20250101_120000"
            result = lc.save(name="test_save")

        assert result == output_dir / "test_save_20250101_120000.log"
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "log line 1\n" in content
        assert "log line 2\n" in content

    @pytest.mark.unit
    def test_save_default_name(self, tmp_path):
        """無名稱時使用預設 device_ 前綴"""
        output_dir = tmp_path / "device_logs"
        with patch("utils.log_collector.LOG_OUTPUT_DIR", output_dir):
            from utils.log_collector import LogCollector
            lc = LogCollector()
            lc._log_lines = ["data"]

        with patch("utils.log_collector.LOG_OUTPUT_DIR", output_dir), \
             patch("utils.log_collector.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "20250101_120000"
            result = lc.save()

        assert "device_20250101_120000.log" in str(result)


@pytest.mark.unit
class TestLogCollectorStopAndSave:
    """LogCollector.stop_and_save 方法"""

    @pytest.mark.unit
    def test_stop_and_save_calls_stop_then_save(self, tmp_path):
        """stop_and_save 先呼叫 stop 再呼叫 save"""
        output_dir = tmp_path / "device_logs"
        with patch("utils.log_collector.LOG_OUTPUT_DIR", output_dir):
            from utils.log_collector import LogCollector
            lc = LogCollector()
            lc._log_lines = ["line"]

        with patch.object(lc, "stop", return_value=["line"]) as mock_stop, \
             patch.object(lc, "save", return_value=Path("/fake/path.log")) as mock_save:
            result = lc.stop_and_save(name="combined")
            mock_stop.assert_called_once()
            mock_save.assert_called_once_with("combined")
            assert result == Path("/fake/path.log")


@pytest.mark.unit
class TestLogCollectorSearch:
    """LogCollector.search 方法"""

    @pytest.mark.unit
    def test_search_finds_matching_lines(self, tmp_path):
        """搜尋包含關鍵字的 log 行"""
        with patch("utils.log_collector.LOG_OUTPUT_DIR", tmp_path / "device_logs"):
            from utils.log_collector import LogCollector
            lc = LogCollector()
            lc._log_lines = [
                "INFO: App started",
                "ERROR: Connection failed",
                "INFO: Retry connection",
                "ERROR: Timeout",
            ]
            result = lc.search("ERROR")
            assert len(result) == 2
            assert "ERROR: Connection failed" in result
            assert "ERROR: Timeout" in result

    @pytest.mark.unit
    def test_search_no_matches(self, tmp_path):
        """搜尋無匹配結果時回傳空列表"""
        with patch("utils.log_collector.LOG_OUTPUT_DIR", tmp_path / "device_logs"):
            from utils.log_collector import LogCollector
            lc = LogCollector()
            lc._log_lines = ["INFO: all good"]
            result = lc.search("FATAL")
            assert result == []


@pytest.mark.unit
class TestLogCollectorSearchErrors:
    """LogCollector.search_errors 方法"""

    @pytest.mark.unit
    def test_search_errors_finds_error_keywords(self, tmp_path):
        """搜尋 E/, ERROR, FATAL, Exception, Crash 關鍵字"""
        with patch("utils.log_collector.LOG_OUTPUT_DIR", tmp_path / "device_logs"):
            from utils.log_collector import LogCollector
            lc = LogCollector()
            lc._log_lines = [
                "I/ActivityManager: Starting activity",
                "E/AndroidRuntime: java.lang.NullPointerException",
                "W/System: Warning message",
                "ERROR in module X",
                "FATAL exception caught",
                "Exception occurred in handler",
                "Crash detected at address 0x0",
                "D/Debug: normal message",
            ]
            result = lc.search_errors()
            assert len(result) == 5
            assert any("E/AndroidRuntime" in l for l in result)
            assert any("ERROR" in l for l in result)
            assert any("FATAL" in l for l in result)
            assert any("Exception" in l for l in result)
            assert any("Crash" in l for l in result)

    @pytest.mark.unit
    def test_search_errors_empty_logs(self, tmp_path):
        """空 log 列表回傳空結果"""
        with patch("utils.log_collector.LOG_OUTPUT_DIR", tmp_path / "device_logs"):
            from utils.log_collector import LogCollector
            lc = LogCollector()
            lc._log_lines = []
            result = lc.search_errors()
            assert result == []


@pytest.mark.unit
class TestLogCollectorGetCrashLogs:
    """LogCollector.get_crash_logs 方法"""

    @pytest.mark.unit
    def test_get_crash_logs_finds_crash_keywords(self, tmp_path):
        """搜尋 FATAL, ANR, Crash, SIGSEGV, SIGABRT 關鍵字"""
        with patch("utils.log_collector.LOG_OUTPUT_DIR", tmp_path / "device_logs"):
            from utils.log_collector import LogCollector
            lc = LogCollector()
            lc._log_lines = [
                "FATAL exception in thread main",
                "ANR in com.example.app",
                "Crash report generated",
                "SIGSEGV at 0x00000",
                "SIGABRT received",
                "ERROR: normal error",
                "INFO: all good",
            ]
            result = lc.get_crash_logs()
            assert len(result) == 5
            assert any("FATAL" in l for l in result)
            assert any("ANR" in l for l in result)
            assert any("Crash" in l for l in result)
            assert any("SIGSEGV" in l for l in result)
            assert any("SIGABRT" in l for l in result)


@pytest.mark.unit
class TestLogCollectorGetPid:
    """LogCollector._get_pid 方法"""

    @pytest.mark.unit
    def test_get_pid_success_returns_pid(self, tmp_path):
        """成功取得 PID"""
        with patch("utils.log_collector.LOG_OUTPUT_DIR", tmp_path / "device_logs"):
            from utils.log_collector import LogCollector
            lc = LogCollector(package_name="com.example.app")

        with patch("utils.log_collector.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="12345\n")
            result = lc._get_pid()
            assert result == "12345"
            mock_run.assert_called_once_with(
                ["adb", "shell", "pidof", "com.example.app"],
                capture_output=True, text=True, timeout=5,
            )

    @pytest.mark.unit
    def test_get_pid_empty_stdout_returns_zero(self, tmp_path):
        """PID 找不到時回傳 '0'"""
        with patch("utils.log_collector.LOG_OUTPUT_DIR", tmp_path / "device_logs"):
            from utils.log_collector import LogCollector
            lc = LogCollector(package_name="com.example.app")

        with patch("utils.log_collector.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="")
            result = lc._get_pid()
            assert result == "0"

    @pytest.mark.unit
    def test_get_pid_exception_returns_zero(self, tmp_path):
        """subprocess 異常時回傳 '0'"""
        with patch("utils.log_collector.LOG_OUTPUT_DIR", tmp_path / "device_logs"):
            from utils.log_collector import LogCollector
            lc = LogCollector(package_name="com.example.app")

        with patch("utils.log_collector.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="adb", timeout=5)
            result = lc._get_pid()
            assert result == "0"
