"""
utils.perf_monitor 單元測試
驗證 PerfSnapshot、PerfReport、PerfMonitor 的效能監控邏輯。
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import time

from utils.perf_monitor import PerfSnapshot, PerfReport, PerfMonitor


@pytest.mark.unit
class TestPerfSnapshot:
    """PerfSnapshot 資料類別"""

    @pytest.mark.unit
    def test_default_values(self):
        """預設值初始化"""
        snap = PerfSnapshot(timestamp=1000.0)

        assert snap.timestamp == 1000.0
        assert snap.memory_mb == 0.0
        assert snap.cpu_percent == 0.0
        assert snap.battery_level == 0
        assert snap.battery_temp == 0.0

    @pytest.mark.unit
    def test_custom_values(self):
        """自訂值初始化"""
        snap = PerfSnapshot(
            timestamp=1000.0,
            memory_mb=256.5,
            cpu_percent=45.3,
            battery_level=80,
            battery_temp=32.5,
        )

        assert snap.memory_mb == 256.5
        assert snap.cpu_percent == 45.3
        assert snap.battery_level == 80
        assert snap.battery_temp == 32.5


@pytest.mark.unit
class TestPerfReport:
    """PerfReport 效能報告"""

    @pytest.mark.unit
    def test_empty_report_avg_memory(self):
        """空報告的平均記憶體為 0"""
        report = PerfReport()
        assert report.avg_memory_mb == 0.0

    @pytest.mark.unit
    def test_empty_report_max_memory(self):
        """空報告的最大記憶體為 0"""
        report = PerfReport()
        assert report.max_memory_mb == 0.0

    @pytest.mark.unit
    def test_empty_report_avg_cpu(self):
        """空報告的平均 CPU 為 0"""
        report = PerfReport()
        assert report.avg_cpu_percent == 0.0

    @pytest.mark.unit
    def test_with_snapshots_avg_memory(self):
        """有快照時正確計算平均記憶體"""
        report = PerfReport(snapshots=[
            PerfSnapshot(timestamp=1.0, memory_mb=100.0),
            PerfSnapshot(timestamp=2.0, memory_mb=200.0),
            PerfSnapshot(timestamp=3.0, memory_mb=300.0),
        ])

        assert report.avg_memory_mb == pytest.approx(200.0)

    @pytest.mark.unit
    def test_with_snapshots_max_memory(self):
        """有快照時正確計算最大記憶體"""
        report = PerfReport(snapshots=[
            PerfSnapshot(timestamp=1.0, memory_mb=100.0),
            PerfSnapshot(timestamp=2.0, memory_mb=500.0),
            PerfSnapshot(timestamp=3.0, memory_mb=300.0),
        ])

        assert report.max_memory_mb == 500.0

    @pytest.mark.unit
    def test_with_snapshots_avg_cpu(self):
        """有快照時正確計算平均 CPU"""
        report = PerfReport(snapshots=[
            PerfSnapshot(timestamp=1.0, cpu_percent=10.0),
            PerfSnapshot(timestamp=2.0, cpu_percent=30.0),
            PerfSnapshot(timestamp=3.0, cpu_percent=50.0),
        ])

        assert report.avg_cpu_percent == pytest.approx(30.0)

    @pytest.mark.unit
    def test_summary_format(self):
        """summary 格式正確"""
        report = PerfReport(snapshots=[
            PerfSnapshot(timestamp=1.0, memory_mb=100.0, cpu_percent=20.0),
            PerfSnapshot(timestamp=2.0, memory_mb=200.0, cpu_percent=40.0),
        ])

        summary = report.summary()

        assert "2 筆取樣" in summary
        assert "150.0 MB" in summary
        assert "200.0 MB" in summary
        assert "30.0%" in summary

    @pytest.mark.unit
    def test_summary_empty(self):
        """空報告的 summary 格式"""
        report = PerfReport()
        summary = report.summary()

        assert "0 筆取樣" in summary


@pytest.mark.unit
class TestPerfMonitorInit:
    """PerfMonitor.__init__"""

    @pytest.mark.unit
    def test_android_default(self):
        """Android 預設初始化"""
        monitor = PerfMonitor("com.example.app")

        assert monitor.package_name == "com.example.app"
        assert monitor.platform == "android"
        assert monitor.driver is None
        assert monitor._running is False
        assert isinstance(monitor._report, PerfReport)

    @pytest.mark.unit
    def test_ios_with_driver(self):
        """iOS 初始化需要 driver"""
        driver = MagicMock()
        monitor = PerfMonitor("com.example.app", platform="iOS", driver=driver)

        assert monitor.platform == "ios"
        assert monitor.driver is driver


@pytest.mark.unit
class TestPerfMonitorSnapshot:
    """PerfMonitor.snapshot"""

    @pytest.mark.unit
    def test_android_snapshot(self):
        """Android 快照呼叫 _get_memory、_get_cpu、_get_battery"""
        monitor = PerfMonitor("com.example.app", platform="android")

        with patch.object(monitor, "_get_memory", return_value=128.5), \
             patch.object(monitor, "_get_cpu", return_value=25.3), \
             patch.object(monitor, "_get_battery", return_value=(85, 30.5)):
            snap = monitor.snapshot()

        assert snap.memory_mb == 128.5
        assert snap.cpu_percent == 25.3
        assert snap.battery_level == 85
        assert snap.battery_temp == 30.5

    @pytest.mark.unit
    def test_ios_snapshot(self):
        """iOS 快照呼叫 _get_memory_ios、_get_cpu_ios、_get_battery_ios"""
        driver = MagicMock()
        monitor = PerfMonitor("com.example.app", platform="ios", driver=driver)

        with patch.object(monitor, "_get_memory_ios", return_value=256.0), \
             patch.object(monitor, "_get_cpu_ios", return_value=15.0), \
             patch.object(monitor, "_get_battery_ios", return_value=72):
            snap = monitor.snapshot()

        assert snap.memory_mb == 256.0
        assert snap.cpu_percent == 15.0
        assert snap.battery_level == 72


@pytest.mark.unit
class TestPerfMonitorStop:
    """PerfMonitor.stop"""

    @pytest.mark.unit
    def test_stop_sets_running_false(self):
        """stop 設定 _running 為 False"""
        monitor = PerfMonitor("com.example.app")
        monitor._running = True

        monitor.stop()

        assert monitor._running is False

    @pytest.mark.unit
    def test_stop_returns_report(self):
        """stop 回傳 PerfReport"""
        monitor = PerfMonitor("com.example.app")
        monitor._report = PerfReport(snapshots=[
            PerfSnapshot(timestamp=1.0, memory_mb=100.0),
        ])

        report = monitor.stop()

        assert isinstance(report, PerfReport)
        assert len(report.snapshots) == 1


@pytest.mark.unit
class TestPerfMonitorSingleCheck:
    """PerfMonitor.single_check"""

    @pytest.mark.unit
    def test_single_check_returns_snapshot(self):
        """single_check 回傳 PerfSnapshot"""
        monitor = PerfMonitor("com.example.app")

        with patch.object(monitor, "snapshot") as mock_snapshot:
            expected = PerfSnapshot(timestamp=1.0, memory_mb=100.0, cpu_percent=10.0)
            mock_snapshot.return_value = expected

            result = monitor.single_check()

        assert result is expected
        mock_snapshot.assert_called_once()


@pytest.mark.unit
class TestRunAdb:
    """PerfMonitor._run_adb"""

    @pytest.mark.unit
    @patch("utils.perf_monitor.subprocess.run")
    def test_run_adb_returns_stdout(self, mock_subprocess_run):
        """_run_adb 回傳 subprocess stdout 並去除空白"""
        mock_subprocess_run.return_value = MagicMock(stdout="  output data  \n")

        monitor = PerfMonitor("com.example.app")
        result = monitor._run_adb("shell", "ls")

        mock_subprocess_run.assert_called_once_with(
            ["adb", "shell", "ls"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result == "output data"

    @pytest.mark.unit
    @patch("utils.perf_monitor.subprocess.run")
    def test_run_adb_multiple_args(self, mock_subprocess_run):
        """_run_adb 傳遞多個參數"""
        mock_subprocess_run.return_value = MagicMock(stdout="ok")

        monitor = PerfMonitor("com.example.app")
        monitor._run_adb("shell", "dumpsys", "meminfo", "com.example.app")

        mock_subprocess_run.assert_called_once_with(
            ["adb", "shell", "dumpsys", "meminfo", "com.example.app"],
            capture_output=True,
            text=True,
            timeout=10,
        )


@pytest.mark.unit
class TestGetMemory:
    """PerfMonitor._get_memory"""

    @pytest.mark.unit
    def test_parse_meminfo_output(self):
        """正確解析 meminfo 的 TOTAL 行"""
        meminfo_output = (
            "Applications Memory Usage (in Kilobytes):\n"
            "Uptime: 12345 Realtime: 67890\n"
            "** MEMINFO in pid 1234 [com.example.app] **\n"
            "                   Pss  Private  Private  SwapPss      Rss     Heap\n"
            "                 TOTAL    131072    65536        0   200000   262144\n"
        )
        monitor = PerfMonitor("com.example.app")

        with patch.object(monitor, "_run_adb", return_value=meminfo_output):
            result = monitor._get_memory()

        assert result == pytest.approx(131072 / 1024.0)

    @pytest.mark.unit
    def test_failure_returns_zero(self):
        """取得記憶體失敗時回傳 0"""
        monitor = PerfMonitor("com.example.app")

        with patch.object(monitor, "_run_adb", side_effect=Exception("adb error")):
            result = monitor._get_memory()

        assert result == 0.0


@pytest.mark.unit
class TestGetCpu:
    """PerfMonitor._get_cpu"""

    @pytest.mark.unit
    def test_parse_top_output_with_percent(self):
        """解析含 % 符號的 top 輸出"""
        # 注意：_get_cpu 會逐一檢查該行的每個 part，
        # 先檢查是否包含 '%'，再嘗試解析為 float (0 < val < 100)。
        # 因此 CPU% 欄位必須放在其他可解析數字欄位之前才能被正確匹配。
        top_output = (
            "  PID USER      PR  NI VIRT  RES  SHR S CPU% MEM%  TIME+  ARGS\n"
            "31234 u0_a1    120  -10 2.0G 150M  90M S 25.3%  5.0   1:23.45 com.example.app\n"
        )
        monitor = PerfMonitor("com.example.app")

        with patch.object(monitor, "_run_adb", return_value=top_output):
            result = monitor._get_cpu()

        assert result == 25.3

    @pytest.mark.unit
    def test_failure_returns_zero(self):
        """取得 CPU 失敗時回傳 0"""
        monitor = PerfMonitor("com.example.app")

        with patch.object(monitor, "_run_adb", side_effect=Exception("adb error")):
            result = monitor._get_cpu()

        assert result == 0.0


@pytest.mark.unit
class TestGetBattery:
    """PerfMonitor._get_battery"""

    @pytest.mark.unit
    def test_parse_battery_output(self):
        """解析電量與溫度"""
        battery_output = (
            "Current Battery Service state:\n"
            "  AC powered: false\n"
            "  USB powered: true\n"
            "  level: 85\n"
            "  temperature: 305\n"
        )
        monitor = PerfMonitor("com.example.app")

        with patch.object(monitor, "_run_adb", return_value=battery_output):
            level, temp = monitor._get_battery()

        assert level == 85
        assert temp == pytest.approx(30.5)

    @pytest.mark.unit
    def test_failure_returns_zero_tuple(self):
        """取得電量失敗時回傳 (0, 0.0)"""
        monitor = PerfMonitor("com.example.app")

        with patch.object(monitor, "_run_adb", side_effect=Exception("adb error")):
            level, temp = monitor._get_battery()

        assert level == 0
        assert temp == 0.0


@pytest.mark.unit
class TestGetMemoryIos:
    """PerfMonitor._get_memory_ios"""

    @pytest.mark.unit
    def test_no_driver_returns_zero(self):
        """無 driver 時回傳 0"""
        monitor = PerfMonitor("com.example.app", platform="ios", driver=None)

        result = monitor._get_memory_ios()

        assert result == 0.0

    @pytest.mark.unit
    def test_success_with_perf_data(self):
        """成功取得 iOS 記憶體（透過 Appium performanceData）"""
        driver = MagicMock()
        driver.execute_script.return_value = [
            ["totalMem", "realMem", "virtualMem"],
            ["524288", "262144", "1048576"],
        ]
        monitor = PerfMonitor("com.example.app", platform="ios", driver=driver)

        result = monitor._get_memory_ios()

        # 回傳第一個匹配的 header (totalMem) 對應的值 524288 / 1024.0
        assert result == pytest.approx(524288 / 1024.0)

    @pytest.mark.unit
    def test_exception_returns_zero(self):
        """driver.execute_script 拋例外時回傳 0"""
        driver = MagicMock()
        driver.execute_script.side_effect = Exception("script error")
        monitor = PerfMonitor("com.example.app", platform="ios", driver=driver)

        result = monitor._get_memory_ios()

        assert result == 0.0


@pytest.mark.unit
class TestGetCpuIos:
    """PerfMonitor._get_cpu_ios"""

    @pytest.mark.unit
    def test_no_driver_returns_zero(self):
        """無 driver 時回傳 0"""
        monitor = PerfMonitor("com.example.app", platform="ios", driver=None)

        result = monitor._get_cpu_ios()

        assert result == 0.0

    @pytest.mark.unit
    def test_success(self):
        """成功取得 iOS CPU"""
        driver = MagicMock()
        driver.execute_script.return_value = [
            ["user", "kernel"],
            [15.5, 3.2],
        ]
        monitor = PerfMonitor("com.example.app", platform="ios", driver=driver)

        result = monitor._get_cpu_ios()

        assert result == 15.5

    @pytest.mark.unit
    def test_exception_returns_zero(self):
        """driver.execute_script 拋例外時回傳 0"""
        driver = MagicMock()
        driver.execute_script.side_effect = Exception("error")
        monitor = PerfMonitor("com.example.app", platform="ios", driver=driver)

        result = monitor._get_cpu_ios()

        assert result == 0.0


@pytest.mark.unit
class TestGetBatteryIos:
    """PerfMonitor._get_battery_ios"""

    @pytest.mark.unit
    def test_no_driver_returns_zero(self):
        """無 driver 時回傳 0"""
        monitor = PerfMonitor("com.example.app", platform="ios", driver=None)

        result = monitor._get_battery_ios()

        assert result == 0

    @pytest.mark.unit
    def test_success_with_float_level(self):
        """level 為浮點數 (0.0~1.0) 時轉換為百分比"""
        driver = MagicMock()
        driver.execute_script.return_value = {"level": 0.85, "state": 2}
        monitor = PerfMonitor("com.example.app", platform="ios", driver=driver)

        result = monitor._get_battery_ios()

        assert result == 85

    @pytest.mark.unit
    def test_success_with_int_level(self):
        """level 為整數時直接使用"""
        driver = MagicMock()
        driver.execute_script.return_value = {"level": 72, "state": 2}
        monitor = PerfMonitor("com.example.app", platform="ios", driver=driver)

        result = monitor._get_battery_ios()

        assert result == 72

    @pytest.mark.unit
    def test_exception_returns_zero(self):
        """driver.execute_script 拋例外時回傳 0"""
        driver = MagicMock()
        driver.execute_script.side_effect = Exception("error")
        monitor = PerfMonitor("com.example.app", platform="ios", driver=driver)

        result = monitor._get_battery_ios()

        assert result == 0
