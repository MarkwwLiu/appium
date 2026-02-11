"""
Video Recorder — 測試錄影

測試執行時自動錄影，失敗時保留影片，通過時可選擇丟棄。
比截圖更有效重現問題。

用法：
    def test_login(self, driver, video_recorder):
        video_recorder.start()
        # ... 執行測試操作 ...
        video_recorder.stop_and_save("test_login")

    # 搭配 auto_save=True：失敗自動保留，通過自動丟棄
    def test_auto(self, driver, video_recorder):
        video_recorder.start()
        # ... 測試結束後自動處理 ...

    # 指定輸出目錄
    recorder = VideoRecorder(driver, output_dir="reports/videos")
"""

from __future__ import annotations

import base64
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING

from utils.logger import logger

if TYPE_CHECKING:
    from appium.webdriver import Remote as WebDriver


class VideoRecorder:
    """
    Appium 螢幕錄影工具

    支援兩種模式：
    1. Appium API: startRecordingScreen / stopRecordingScreen (推薦)
    2. ADB screenrecord: 直接用 ADB 錄影 (Android 備用)
    """

    def __init__(
        self,
        driver: "WebDriver",
        platform: str = "android",
        output_dir: str = "reports/videos",
        time_limit: int = 180,
    ):
        self._driver = driver
        self._platform = platform.lower()
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._time_limit = time_limit  # 最長錄影秒數
        self._recording = False
        self._mode: str = "appium"  # appium 或 adb

    # ── 公開 API ──

    def start(self) -> None:
        """開始錄影"""
        if self._recording:
            logger.debug("[VideoRecorder] 已在錄影中，忽略重複呼叫")
            return

        try:
            self._start_appium()
            self._mode = "appium"
            self._recording = True
            logger.info("[VideoRecorder] 開始錄影 (Appium API)")
        except Exception as e:
            logger.debug(f"[VideoRecorder] Appium API 錄影失敗: {e}")
            try:
                self._start_adb()
                self._mode = "adb"
                self._recording = True
                logger.info("[VideoRecorder] 開始錄影 (ADB screenrecord)")
            except Exception as e2:
                logger.warning(f"[VideoRecorder] 錄影啟動失敗: {e2}")

    def stop_and_save(self, name: str) -> Path | None:
        """停止錄影並儲存"""
        if not self._recording:
            logger.debug("[VideoRecorder] 未在錄影，忽略")
            return None

        self._recording = False
        output_path = self._output_dir / f"{name}_{int(time.time())}.mp4"

        try:
            if self._mode == "appium":
                return self._stop_appium(output_path)
            else:
                return self._stop_adb(output_path)
        except Exception as e:
            logger.warning(f"[VideoRecorder] 儲存影片失敗: {e}")
            return None

    def stop_and_discard(self) -> None:
        """停止錄影但不儲存"""
        if not self._recording:
            return
        self._recording = False
        try:
            if self._mode == "appium":
                self._driver.stop_recording_screen()
            else:
                self._stop_adb_process()
        except Exception:
            pass
        logger.debug("[VideoRecorder] 錄影已丟棄")

    @property
    def is_recording(self) -> bool:
        """是否正在錄影"""
        return self._recording

    @property
    def output_dir(self) -> Path:
        """影片輸出目錄"""
        return self._output_dir

    # ── Appium API 模式 ──

    def _start_appium(self) -> None:
        """透過 Appium API 開始錄影"""
        options = {
            "timeLimit": self._time_limit,
            "forceRestart": True,
        }

        if self._platform == "android":
            options["bitRate"] = 4000000   # 4Mbps
            options["videoSize"] = "720x1280"
        else:
            # iOS
            options["videoType"] = "mpeg4"
            options["videoQuality"] = "medium"

        self._driver.start_recording_screen(**options)

    def _stop_appium(self, output_path: Path) -> Path | None:
        """透過 Appium API 停止錄影並儲存"""
        b64_data = self._driver.stop_recording_screen()
        if b64_data:
            video_data = base64.b64decode(b64_data)
            output_path.write_bytes(video_data)
            size_mb = len(video_data) / (1024 * 1024)
            logger.info(f"[VideoRecorder] 影片已儲存: {output_path} ({size_mb:.1f}MB)")
            return output_path
        return None

    # ── ADB screenrecord 模式 ──

    def _start_adb(self) -> None:
        """透過 ADB 開始錄影 (僅 Android)"""
        if self._platform != "android":
            raise RuntimeError("ADB screenrecord 僅支援 Android")

        self._adb_device_path = "/sdcard/monkey_record.mp4"
        self._adb_process = subprocess.Popen(
            [
                "adb", "shell", "screenrecord",
                "--time-limit", str(self._time_limit),
                "--bit-rate", "4000000",
                "--size", "720x1280",
                self._adb_device_path,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _stop_adb(self, output_path: Path) -> Path | None:
        """透過 ADB 停止錄影並拉取檔案"""
        self._stop_adb_process()
        time.sleep(1)  # 等待檔案寫入完成

        # 從裝置拉取影片
        result = subprocess.run(
            ["adb", "pull", self._adb_device_path, str(output_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and output_path.exists():
            size_mb = output_path.stat().st_size / (1024 * 1024)
            logger.info(f"[VideoRecorder] 影片已儲存: {output_path} ({size_mb:.1f}MB)")
            # 清理裝置上的檔案
            subprocess.run(
                ["adb", "shell", "rm", self._adb_device_path],
                capture_output=True,
                timeout=5,
            )
            return output_path
        return None

    def _stop_adb_process(self) -> None:
        """停止 ADB screenrecord process"""
        if hasattr(self, "_adb_process") and self._adb_process:
            try:
                self._adb_process.terminate()
                self._adb_process.wait(timeout=5)
            except Exception:
                self._adb_process.kill()
            self._adb_process = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        if self._recording:
            self.stop_and_discard()
