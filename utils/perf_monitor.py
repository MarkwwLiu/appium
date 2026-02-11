"""
效能監控工具
測試期間追蹤 App 的 CPU、記憶體、電量等指標。
僅支援 Android（透過 adb）。
"""

import subprocess
import time
from dataclasses import dataclass, field

from utils.logger import logger


@dataclass
class PerfSnapshot:
    """單次效能快照"""
    timestamp: float
    memory_mb: float = 0.0
    cpu_percent: float = 0.0
    battery_level: int = 0
    battery_temp: float = 0.0


@dataclass
class PerfReport:
    """效能報告"""
    snapshots: list[PerfSnapshot] = field(default_factory=list)

    @property
    def avg_memory_mb(self) -> float:
        if not self.snapshots:
            return 0.0
        return sum(s.memory_mb for s in self.snapshots) / len(self.snapshots)

    @property
    def max_memory_mb(self) -> float:
        if not self.snapshots:
            return 0.0
        return max(s.memory_mb for s in self.snapshots)

    @property
    def avg_cpu_percent(self) -> float:
        if not self.snapshots:
            return 0.0
        return sum(s.cpu_percent for s in self.snapshots) / len(self.snapshots)

    def summary(self) -> str:
        return (
            f"效能報告 ({len(self.snapshots)} 筆取樣)\n"
            f"  記憶體: 平均 {self.avg_memory_mb:.1f} MB / 最大 {self.max_memory_mb:.1f} MB\n"
            f"  CPU:    平均 {self.avg_cpu_percent:.1f}%"
        )


class PerfMonitor:
    """
    效能監控器 (Android)

    用法：
        monitor = PerfMonitor("com.example.app")
        monitor.start(interval=2)
        # ... 執行測試 ...
        report = monitor.stop()
        print(report.summary())
    """

    def __init__(self, package_name: str):
        self.package_name = package_name
        self._running = False
        self._report = PerfReport()

    def snapshot(self) -> PerfSnapshot:
        """擷取一次效能快照"""
        snap = PerfSnapshot(timestamp=time.time())
        snap.memory_mb = self._get_memory()
        snap.cpu_percent = self._get_cpu()
        snap.battery_level, snap.battery_temp = self._get_battery()
        return snap

    def start(self, interval: float = 2.0, duration: float = 0) -> None:
        """
        開始持續監控。

        Args:
            interval: 取樣間隔秒數
            duration: 持續秒數（0 表示直到呼叫 stop）
        """
        logger.info(f"開始效能監控: {self.package_name} (間隔 {interval}s)")
        self._running = True
        self._report = PerfReport()

        end_time = time.time() + duration if duration > 0 else float("inf")
        while self._running and time.time() < end_time:
            snap = self.snapshot()
            self._report.snapshots.append(snap)
            logger.debug(
                f"[perf] mem={snap.memory_mb:.1f}MB "
                f"cpu={snap.cpu_percent:.1f}%"
            )
            time.sleep(interval)

    def stop(self) -> PerfReport:
        """停止監控並回傳報告"""
        self._running = False
        logger.info(self._report.summary())
        return self._report

    def single_check(self) -> PerfSnapshot:
        """單次檢查（不需 start/stop）"""
        snap = self.snapshot()
        logger.info(
            f"[效能] mem={snap.memory_mb:.1f}MB "
            f"cpu={snap.cpu_percent:.1f}% "
            f"battery={snap.battery_level}%"
        )
        return snap

    # ── 內部方法 ──

    def _run_adb(self, *args) -> str:
        result = subprocess.run(
            ["adb", *args],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip()

    def _get_memory(self) -> float:
        """取得 App 記憶體用量 (MB)"""
        try:
            output = self._run_adb("shell", "dumpsys", "meminfo", self.package_name)
            for line in output.splitlines():
                if "TOTAL" in line and "PSS" not in line:
                    parts = line.split()
                    for part in parts:
                        if part.isdigit():
                            return int(part) / 1024.0
        except Exception as e:
            logger.debug(f"取得記憶體失敗: {e}")
        return 0.0

    def _get_cpu(self) -> float:
        """取得 App CPU 使用率"""
        try:
            output = self._run_adb("shell", "top", "-n", "1", "-b")
            for line in output.splitlines():
                if self.package_name in line:
                    parts = line.split()
                    for part in parts:
                        if "%" in part:
                            return float(part.replace("%", ""))
                        try:
                            val = float(part)
                            if 0 < val < 100:
                                return val
                        except ValueError:
                            continue
        except Exception as e:
            logger.debug(f"取得 CPU 失敗: {e}")
        return 0.0

    def _get_battery(self) -> tuple[int, float]:
        """取得電量百分比和溫度"""
        level = 0
        temp = 0.0
        try:
            output = self._run_adb("shell", "dumpsys", "battery")
            for line in output.splitlines():
                if "level:" in line:
                    level = int(line.split(":")[1].strip())
                elif "temperature:" in line:
                    temp = int(line.split(":")[1].strip()) / 10.0
        except Exception as e:
            logger.debug(f"取得電量失敗: {e}")
        return level, temp
