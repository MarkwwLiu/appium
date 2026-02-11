"""
裝置 Log 收集器
自動收集 Android logcat / iOS syslog，用於測試失敗時的除錯分析。
"""

import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

from config.config import Config
from utils.logger import logger

LOG_OUTPUT_DIR = Config.REPORT_DIR / "device_logs"


class LogCollector:
    """收集裝置端日誌"""

    def __init__(self, package_name: str = "", platform: str = "android"):
        """
        Args:
            package_name: App package name (Android 過濾用)
            platform: 'android' 或 'ios'
        """
        self.package_name = package_name
        self.platform = platform.lower()
        self._process = None
        self._thread = None
        self._running = False
        self._log_lines: list[str] = []
        LOG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def start(self) -> None:
        """開始收集裝置 log（背景執行）"""
        if self._running:
            logger.warning("LogCollector 已在執行中")
            return

        self._running = True
        self._log_lines = []

        if self.platform == "android":
            # 先清除舊 log
            subprocess.run(["adb", "logcat", "-c"], capture_output=True)
            cmd = ["adb", "logcat", "-v", "time"]
            if self.package_name:
                cmd += ["--pid", self._get_pid()]
        else:
            cmd = ["idevicesyslog"]

        logger.info(f"開始收集裝置 log: {' '.join(cmd)}")

        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self._thread = threading.Thread(target=self._read_output, daemon=True)
        self._thread.start()

    def stop(self) -> list[str]:
        """停止收集並回傳 log 內容"""
        self._running = False
        if self._process:
            self._process.terminate()
            self._process.wait(timeout=5)
            self._process = None
        logger.info(f"已停止收集，共 {len(self._log_lines)} 行 log")
        return self._log_lines

    def save(self, name: str = "") -> Path:
        """儲存 log 到檔案"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{ts}.log" if name else f"device_{ts}.log"
        filepath = LOG_OUTPUT_DIR / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(line + "\n" for line in self._log_lines)

        logger.info(f"裝置 log 已儲存: {filepath}")
        return filepath

    def stop_and_save(self, name: str = "") -> Path:
        """停止收集並儲存"""
        self.stop()
        return self.save(name)

    def search(self, keyword: str) -> list[str]:
        """在已收集的 log 中搜尋關鍵字"""
        matches = [line for line in self._log_lines if keyword in line]
        logger.info(f"搜尋 '{keyword}': 找到 {len(matches)} 筆")
        return matches

    def search_errors(self) -> list[str]:
        """搜尋 error 等級的 log"""
        error_keywords = ["E/", "ERROR", "FATAL", "Exception", "Crash"]
        errors = [
            line for line in self._log_lines
            if any(kw in line for kw in error_keywords)
        ]
        return errors

    def get_crash_logs(self) -> list[str]:
        """取得 crash 相關 log"""
        crash_keywords = ["FATAL", "ANR", "Crash", "SIGSEGV", "SIGABRT"]
        return [
            line for line in self._log_lines
            if any(kw in line for kw in crash_keywords)
        ]

    # ── 內部方法 ──

    def _read_output(self) -> None:
        """背景讀取 process 輸出"""
        while self._running and self._process:
            line = self._process.stdout.readline()
            if line:
                self._log_lines.append(line.rstrip())

    def _get_pid(self) -> str:
        """取得 App 的 PID (Android)"""
        try:
            result = subprocess.run(
                ["adb", "shell", "pidof", self.package_name],
                capture_output=True, text=True, timeout=5,
            )
            return result.stdout.strip() or "0"
        except Exception:
            return "0"
