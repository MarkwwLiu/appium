"""
Network Condition Simulator — 弱網模擬

模擬各種網路環境 (2G/3G/4G/離線/高延遲/丟包)，
驗證 App 在惡劣網路下的行為（loading 顯示、重試、離線模式）。

用法：
    def test_slow_network(self, driver, network_condition):
        network_condition.set_3g()
        # ... 操作 App，驗證 loading 畫面 ...

        network_condition.set_offline()
        # ... 驗證離線提示 ...

        network_condition.reset()

    # 自訂網路條件
    def test_custom_network(self, driver, network_condition):
        network_condition.set_custom(
            latency_ms=500,
            download_kbps=128,
            upload_kbps=64,
            packet_loss=10,  # 10% 丟包
        )
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

from utils.logger import logger

if TYPE_CHECKING:
    from appium.webdriver import Remote as WebDriver


@dataclass
class NetworkProfile:
    """網路設定檔"""
    name: str
    latency_ms: int       # 延遲 (毫秒)
    download_kbps: int    # 下行速度 (kbps)
    upload_kbps: int      # 上行速度 (kbps)
    packet_loss: int = 0  # 丟包率 (%)


# 預設網路設定檔
PROFILES = {
    "2g": NetworkProfile("2G", latency_ms=800, download_kbps=50, upload_kbps=30, packet_loss=5),
    "3g": NetworkProfile("3G", latency_ms=200, download_kbps=750, upload_kbps=250, packet_loss=2),
    "4g": NetworkProfile("4G", latency_ms=50, download_kbps=4000, upload_kbps=3000),
    "wifi": NetworkProfile("WiFi", latency_ms=10, download_kbps=30000, upload_kbps=15000),
    "lossy": NetworkProfile("高丟包", latency_ms=100, download_kbps=1000, upload_kbps=500, packet_loss=20),
    "slow": NetworkProfile("極慢", latency_ms=2000, download_kbps=10, upload_kbps=5, packet_loss=10),
}


class NetworkSimulator:
    """
    網路狀態模擬器

    支援兩種模式：
    1. Appium API: 透過 driver 設定 connection type (Android)
    2. ADB: 透過 tc/iptables 模擬網路條件 (需要 root)

    自動偵測可用模式。
    """

    def __init__(self, driver: "WebDriver", platform: str = "android"):
        self._driver = driver
        self._platform = platform.lower()
        self._original_state: int | None = None
        self._tc_active = False

    # ── 預設設定檔 ──

    def set_2g(self) -> None:
        """模擬 2G 網路 (高延遲、極低頻寬)"""
        self._apply_profile(PROFILES["2g"])

    def set_3g(self) -> None:
        """模擬 3G 網路"""
        self._apply_profile(PROFILES["3g"])

    def set_4g(self) -> None:
        """模擬 4G 網路"""
        self._apply_profile(PROFILES["4g"])

    def set_wifi(self) -> None:
        """模擬 WiFi 網路"""
        self._apply_profile(PROFILES["wifi"])

    def set_lossy(self) -> None:
        """模擬高丟包網路 (20%)"""
        self._apply_profile(PROFILES["lossy"])

    def set_slow(self) -> None:
        """模擬極慢網路 (接近不可用)"""
        self._apply_profile(PROFILES["slow"])

    def set_offline(self) -> None:
        """設為離線模式"""
        logger.info("[NetworkSim] 設定: 離線模式")
        if self._platform == "android":
            self._save_original_state()
            # Appium 的 network connection type: 0 = no connection
            try:
                self._driver.set_network_connection(0)
                return
            except Exception:
                pass
            # 備用方案: ADB
            self._adb("svc wifi disable")
            self._adb("svc data disable")
        else:
            # iOS: 只能透過 Appium 或控制中心
            logger.warning("[NetworkSim] iOS 離線模式需手動設定或使用 Xcode 工具")

    def set_wifi_only(self) -> None:
        """僅 WiFi (關閉行動數據)"""
        logger.info("[NetworkSim] 設定: 僅 WiFi")
        if self._platform == "android":
            self._save_original_state()
            # network connection type: 2 = wifi only
            try:
                self._driver.set_network_connection(2)
                return
            except Exception:
                pass
            self._adb("svc data disable")
            self._adb("svc wifi enable")

    def set_data_only(self) -> None:
        """僅行動數據 (關閉 WiFi)"""
        logger.info("[NetworkSim] 設定: 僅行動數據")
        if self._platform == "android":
            self._save_original_state()
            # network connection type: 4 = data only
            try:
                self._driver.set_network_connection(4)
                return
            except Exception:
                pass
            self._adb("svc wifi disable")
            self._adb("svc data enable")

    def set_custom(
        self,
        latency_ms: int = 0,
        download_kbps: int = 0,
        upload_kbps: int = 0,
        packet_loss: int = 0,
    ) -> None:
        """自訂網路條件"""
        profile = NetworkProfile(
            name="自訂",
            latency_ms=latency_ms,
            download_kbps=download_kbps,
            upload_kbps=upload_kbps,
            packet_loss=packet_loss,
        )
        self._apply_profile(profile)

    def reset(self) -> None:
        """恢復原始網路狀態"""
        logger.info("[NetworkSim] 恢復網路狀態")

        # 清除 tc 規則
        if self._tc_active:
            self._adb_shell("tc qdisc del dev wlan0 root", ignore_error=True)
            self._adb_shell("tc qdisc del dev rmnet0 root", ignore_error=True)
            self._tc_active = False

        if self._platform == "android":
            if self._original_state is not None:
                try:
                    self._driver.set_network_connection(self._original_state)
                    return
                except Exception:
                    pass
            # 備用: 全部啟用
            self._adb("svc wifi enable")
            self._adb("svc data enable")

    # ── 查詢 ──

    @property
    def current_state(self) -> dict:
        """取得當前網路狀態"""
        if self._platform == "android":
            try:
                conn = self._driver.network_connection
                return {
                    "airplane": bool(conn & 1),
                    "wifi": bool(conn & 2),
                    "data": bool(conn & 4),
                    "raw": conn,
                }
            except Exception:
                pass
        return {"unknown": True}

    # ── 內部方法 ──

    def _apply_profile(self, profile: NetworkProfile) -> None:
        """套用網路設定檔 (透過 tc 指令)"""
        logger.info(
            f"[NetworkSim] 套用: {profile.name} "
            f"(延遲={profile.latency_ms}ms, "
            f"下行={profile.download_kbps}kbps, "
            f"丟包={profile.packet_loss}%)"
        )

        if self._platform != "android":
            logger.warning("[NetworkSim] tc 模擬目前僅支援 Android")
            return

        # 清除舊規則
        self._adb_shell("tc qdisc del dev wlan0 root", ignore_error=True)

        # 建立 netem + tbf 規則
        # netem: 延遲 + 丟包
        netem_params = f"delay {profile.latency_ms}ms"
        if profile.packet_loss > 0:
            netem_params += f" loss {profile.packet_loss}%"

        # tbf: 頻寬限制
        rate = f"{profile.download_kbps}kbit"
        burst = max(profile.download_kbps // 8, 1)

        cmd = (
            f"tc qdisc add dev wlan0 root netem {netem_params} "
            f"rate {rate} burst {burst}k latency 50ms"
        )
        self._adb_shell(cmd, ignore_error=True)
        self._tc_active = True

    def _save_original_state(self) -> None:
        """儲存原始網路狀態 (只儲存一次)"""
        if self._original_state is None:
            try:
                self._original_state = self._driver.network_connection
            except Exception:
                self._original_state = 6  # wifi + data

    def _adb(self, command: str) -> str:
        """透過 ADB shell 執行指令"""
        return self._adb_shell(command)

    def _adb_shell(self, command: str, ignore_error: bool = False) -> str:
        """執行 ADB shell 指令"""
        try:
            result = subprocess.run(
                ["adb", "shell", command],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0 and not ignore_error:
                logger.debug(f"[NetworkSim] ADB 指令失敗: {command} → {result.stderr}")
            return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            if not ignore_error:
                logger.debug(f"[NetworkSim] ADB 指令異常: {e}")
            return ""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.reset()
