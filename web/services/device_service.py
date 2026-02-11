"""
裝置管理服務

偵測已連線的 Android/iOS 裝置，查詢裝置資訊。
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass
class DeviceInfo:
    """裝置資訊"""
    serial: str
    platform: str
    model: str = ""
    brand: str = ""
    os_version: str = ""
    status: str = "online"
    screen_size: str = ""
    battery: str = ""


class DeviceService:
    """裝置管理服務"""

    def get_devices(self) -> list[DeviceInfo]:
        """取得所有已連線裝置"""
        devices = []
        devices.extend(self._get_android_devices())
        devices.extend(self._get_ios_devices())
        return devices

    def _get_android_devices(self) -> list[DeviceInfo]:
        """透過 ADB 取得 Android 裝置"""
        try:
            result = subprocess.run(
                ["adb", "devices", "-l"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return []

            devices = []
            for line in result.stdout.strip().split("\n")[1:]:
                if not line.strip() or "offline" in line:
                    continue

                parts = line.split()
                if len(parts) < 2:
                    continue

                serial = parts[0]
                status = "online" if "device" in parts[1] else parts[1]

                # 取得裝置詳細資訊
                info = DeviceInfo(
                    serial=serial,
                    platform="android",
                    status=status,
                    model=self._adb_prop(serial, "ro.product.model"),
                    brand=self._adb_prop(serial, "ro.product.brand"),
                    os_version=self._adb_prop(serial, "ro.build.version.release"),
                    screen_size=self._adb_screen_size(serial),
                    battery=self._adb_battery(serial),
                )
                devices.append(info)

            return devices
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []

    def _get_ios_devices(self) -> list[DeviceInfo]:
        """透過 idevice_id 或 xcrun 取得 iOS 裝置"""
        devices = []

        # 嘗試 idevice_id (libimobiledevice)
        try:
            result = subprocess.run(
                ["idevice_id", "-l"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                for udid in result.stdout.strip().split("\n"):
                    if udid.strip():
                        devices.append(DeviceInfo(
                            serial=udid.strip(),
                            platform="ios",
                            model=self._ios_info(udid.strip(), "DeviceName"),
                            os_version=self._ios_info(udid.strip(), "ProductVersion"),
                        ))
                return devices
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # 嘗試 xcrun (macOS)
        try:
            result = subprocess.run(
                ["xcrun", "xctrace", "list", "devices"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if "(" in line and "Simulator" not in line:
                        name = line.split("(")[0].strip()
                        if name:
                            devices.append(DeviceInfo(
                                serial=name,
                                platform="ios",
                                model=name,
                            ))
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return devices

    def _adb_prop(self, serial: str, prop: str) -> str:
        """讀取 Android 系統屬性"""
        try:
            result = subprocess.run(
                ["adb", "-s", serial, "shell", "getprop", prop],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return ""

    def _adb_screen_size(self, serial: str) -> str:
        """取得螢幕解析度"""
        try:
            result = subprocess.run(
                ["adb", "-s", serial, "shell", "wm", "size"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            # "Physical size: 1080x1920"
            for line in result.stdout.split("\n"):
                if "size" in line.lower() and "x" in line:
                    return line.split(":")[-1].strip()
            return ""
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return ""

    def _adb_battery(self, serial: str) -> str:
        """取得電池電量"""
        try:
            result = subprocess.run(
                ["adb", "-s", serial, "shell", "dumpsys", "battery"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in result.stdout.split("\n"):
                if "level" in line.lower():
                    return line.split(":")[-1].strip() + "%"
            return ""
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return ""

    def _ios_info(self, udid: str, key: str) -> str:
        """讀取 iOS 裝置資訊"""
        try:
            result = subprocess.run(
                ["ideviceinfo", "-u", udid, "-k", key],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return ""


# 全域 singleton
device_service = DeviceService()
