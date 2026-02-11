"""
Driver 生命週期管理
負責建立、取得、關閉 Appium driver，確保每個測試 session 獨立。
"""

from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.options.ios import XCUITestOptions

from config.config import Config


class DriverManager:
    """管理 Appium WebDriver 的建立與銷毀"""

    _driver = None

    @classmethod
    def create_driver(cls, platform: str | None = None) -> webdriver.Remote:
        """
        根據平台建立 Appium driver。

        Args:
            platform: 'android' 或 'ios'，預設讀取 Config.PLATFORM

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

        cls._driver = webdriver.Remote(
            command_executor=Config.appium_server_url(),
            options=options,
        )
        cls._driver.implicitly_wait(Config.IMPLICIT_WAIT)
        return cls._driver

    @classmethod
    def get_driver(cls) -> webdriver.Remote:
        """取得目前的 driver 實例"""
        if cls._driver is None:
            raise RuntimeError("Driver 尚未建立，請先呼叫 create_driver()")
        return cls._driver

    @classmethod
    def quit_driver(cls) -> None:
        """安全關閉 driver"""
        if cls._driver is not None:
            cls._driver.quit()
            cls._driver = None
