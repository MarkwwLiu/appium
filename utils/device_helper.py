"""
裝置控制工具
螢幕旋轉、鍵盤操作、通知欄、網路切換、系統按鍵等。
"""

from utils.logger import logger


class DeviceHelper:
    """裝置層級操作"""

    def __init__(self, driver):
        self.driver = driver

    # ── 螢幕旋轉 ──

    def rotate_landscape(self) -> None:
        """切換為橫向"""
        logger.info("旋轉螢幕: 橫向")
        self.driver.orientation = "LANDSCAPE"

    def rotate_portrait(self) -> None:
        """切換為直向"""
        logger.info("旋轉螢幕: 直向")
        self.driver.orientation = "PORTRAIT"

    def get_orientation(self) -> str:
        """取得目前螢幕方向"""
        return self.driver.orientation

    # ── 系統按鍵 ──

    def press_back(self) -> None:
        """按返回鍵 (Android)"""
        logger.info("按下返回鍵")
        self.driver.back()

    def press_home(self) -> None:
        """按 Home 鍵 (Android)"""
        logger.info("按下 Home 鍵")
        self.driver.press_keycode(3)

    def press_recent_apps(self) -> None:
        """按多工鍵 (Android)"""
        logger.info("按下多工鍵")
        self.driver.press_keycode(187)

    def press_enter(self) -> None:
        """按 Enter 鍵"""
        logger.info("按下 Enter 鍵")
        self.driver.press_keycode(66)

    def press_volume_up(self) -> None:
        """按音量+"""
        self.driver.press_keycode(24)

    def press_volume_down(self) -> None:
        """按音量-"""
        self.driver.press_keycode(25)

    # ── 通知欄 ──

    def open_notifications(self) -> None:
        """打開通知欄 (Android)"""
        logger.info("打開通知欄")
        self.driver.open_notifications()

    # ── 鍵盤 ──

    def hide_keyboard(self) -> None:
        """隱藏鍵盤"""
        try:
            self.driver.hide_keyboard()
            logger.info("鍵盤已隱藏")
        except Exception:
            logger.debug("鍵盤不在畫面上")

    def is_keyboard_shown(self) -> bool:
        """判斷鍵盤是否顯示"""
        return self.driver.is_keyboard_shown()

    # ── 網路 ──

    def set_airplane_mode(self, on: bool = True) -> None:
        """開關飛航模式 (Android)"""
        logger.info(f"飛航模式: {'開啟' if on else '關閉'}")
        self.driver.set_network_connection(1 if on else 6)

    def set_wifi_only(self) -> None:
        """僅 WiFi (Android)"""
        logger.info("切換為僅 WiFi")
        self.driver.set_network_connection(2)

    def set_mobile_data_only(self) -> None:
        """僅行動數據 (Android)"""
        logger.info("切換為僅行動數據")
        self.driver.set_network_connection(4)

    def set_all_network(self) -> None:
        """開啟所有網路 (Android)"""
        logger.info("開啟所有網路")
        self.driver.set_network_connection(6)

    def get_network_connection(self) -> int:
        """
        取得網路狀態。
        0=無, 1=飛航, 2=WiFi, 4=行動數據, 6=全部
        """
        return self.driver.network_connection

    # ── 裝置資訊 ──

    def get_device_info(self) -> dict:
        """取得裝置基本資訊"""
        size = self.driver.get_window_size()
        info = {
            "platform": self.driver.capabilities.get("platformName", ""),
            "device_name": self.driver.capabilities.get("deviceName", ""),
            "os_version": self.driver.capabilities.get("platformVersion", ""),
            "screen_width": size["width"],
            "screen_height": size["height"],
            "orientation": self.driver.orientation,
        }
        logger.info(f"裝置資訊: {info}")
        return info

    # ── 剪貼簿 ──

    def set_clipboard(self, text: str) -> None:
        """設定剪貼簿內容"""
        self.driver.set_clipboard_text(text)
        logger.info(f"剪貼簿已設定: {text}")

    def get_clipboard(self) -> str:
        """取得剪貼簿內容"""
        return self.driver.get_clipboard_text()
