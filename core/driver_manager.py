"""
Driver 生命週期管理

負責建立、取得、關閉 Appium driver，確保每個測試 session 獨立。
已整合 Event Bus 與 Plugin 通知。

支援：
- 執行緒安全（平行測試時每個 worker 獨立 driver）
- Appium server 連線前健康檢查
- 連線失敗自動重試（指數退避）
"""

import threading
import time
import urllib.request
import urllib.error

from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.options.ios import XCUITestOptions

from config.config import Config
from core.element_cache import element_cache
from core.exceptions import (
    DriverConnectionError,
    DriverNotInitializedError,
)
from core.plugin_manager import plugin_manager
from utils.logger import logger


class DriverManager:
    """
    管理 Appium WebDriver 的建立與銷毀

    使用 thread-local storage 確保平行測試時各 worker 的 driver 互不干擾。
    """

    _local = threading.local()

    # ── Appium Server 健康檢查 ──

    @classmethod
    def health_check(cls, url: str | None = None, timeout: float = 5.0) -> bool:
        """
        檢查 Appium server 是否可連線。

        Args:
            url: Appium server URL，預設讀取 Config
            timeout: 連線逾時秒數

        Returns:
            True = server 可用, False = 不可用
        """
        url = url or Config.appium_server_url()
        status_url = f"{url}/status"
        try:
            req = urllib.request.Request(status_url, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status == 200
        except (urllib.error.URLError, OSError, TimeoutError):
            return False

    # ── Driver 建立 ──

    @classmethod
    def create_driver(
        cls,
        platform: str | None = None,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ) -> webdriver.Remote:
        """
        根據平台建立 Appium driver，支援自動重試。

        Args:
            platform: 'android' 或 'ios'，預設讀取 Config.PLATFORM
            max_retries: 連線失敗時最多重試次數
            retry_delay: 首次重試等待秒數（後續指數退避）

        Returns:
            Appium WebDriver 實例
        """
        platform = platform or Config.PLATFORM
        caps = Config.load_caps(platform)

        if platform == "android":
            options = UiAutomator2Options().load_capabilities(caps)
        elif platform == "ios":
            options = XCUITestOptions().load_capabilities(caps)
        else:
            raise ValueError(f"不支援的平台: {platform}")

        url = Config.appium_server_url()

        # 連線前健康檢查
        if not cls.health_check(url):
            logger.warning(f"Appium server 健康檢查失敗: {url}，仍嘗試連線...")

        # 帶重試的連線
        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                drv = webdriver.Remote(
                    command_executor=url,
                    options=options,
                )
                break
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait = retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Driver 連線失敗 (第 {attempt + 1} 次)，"
                        f"{wait:.1f}s 後重試: {e}"
                    )
                    time.sleep(wait)
        else:
            raise DriverConnectionError(url, last_error)

        drv.implicitly_wait(Config.IMPLICIT_WAIT)

        # thread-local 儲存
        cls._local.driver = drv

        # 通知 Plugin / Event Bus
        plugin_manager.emit_driver_created(drv)
        logger.info(f"Driver 已建立: {platform} -> {url}")

        return drv

    @classmethod
    def get_driver(cls) -> webdriver.Remote:
        """取得當前執行緒的 driver 實例"""
        drv = getattr(cls._local, "driver", None)
        if drv is None:
            raise DriverNotInitializedError()
        return drv

    @classmethod
    def quit_driver(cls) -> None:
        """安全關閉當前執行緒的 driver"""
        drv = getattr(cls._local, "driver", None)
        if drv is not None:
            plugin_manager.emit_driver_quit(drv)
            element_cache.clear()
            drv.quit()
            cls._local.driver = None
            logger.info("Driver 已關閉")
