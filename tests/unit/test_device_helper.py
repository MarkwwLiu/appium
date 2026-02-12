"""
utils.device_helper 單元測試
驗證 DeviceHelper 的所有裝置控制功能。
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock


@pytest.mark.unit
class TestRotation:
    """螢幕旋轉相關方法"""

    @pytest.mark.unit
    def test_rotate_landscape(self):
        """rotate_landscape 設定 orientation 為 LANDSCAPE"""
        from utils.device_helper import DeviceHelper

        driver = MagicMock()
        helper = DeviceHelper(driver)
        helper.rotate_landscape()

        assert driver.orientation == "LANDSCAPE"

    @pytest.mark.unit
    def test_rotate_portrait(self):
        """rotate_portrait 設定 orientation 為 PORTRAIT"""
        from utils.device_helper import DeviceHelper

        driver = MagicMock()
        helper = DeviceHelper(driver)
        helper.rotate_portrait()

        assert driver.orientation == "PORTRAIT"

    @pytest.mark.unit
    def test_get_orientation(self):
        """get_orientation 回傳 driver.orientation 的值"""
        from utils.device_helper import DeviceHelper

        driver = MagicMock()
        driver.orientation = "LANDSCAPE"
        helper = DeviceHelper(driver)

        assert helper.get_orientation() == "LANDSCAPE"

    @pytest.mark.unit
    def test_get_orientation_portrait(self):
        """get_orientation 回傳 PORTRAIT"""
        from utils.device_helper import DeviceHelper

        driver = MagicMock()
        driver.orientation = "PORTRAIT"
        helper = DeviceHelper(driver)

        assert helper.get_orientation() == "PORTRAIT"


@pytest.mark.unit
class TestSystemKeys:
    """系統按鍵相關方法"""

    @pytest.mark.unit
    def test_press_back(self):
        """press_back 呼叫 driver.back()"""
        from utils.device_helper import DeviceHelper

        driver = MagicMock()
        helper = DeviceHelper(driver)
        helper.press_back()

        driver.back.assert_called_once()

    @pytest.mark.unit
    def test_press_home(self):
        """press_home 呼叫 driver.press_keycode(3)"""
        from utils.device_helper import DeviceHelper

        driver = MagicMock()
        helper = DeviceHelper(driver)
        helper.press_home()

        driver.press_keycode.assert_called_once_with(3)

    @pytest.mark.unit
    def test_press_recent_apps(self):
        """press_recent_apps 呼叫 driver.press_keycode(187)"""
        from utils.device_helper import DeviceHelper

        driver = MagicMock()
        helper = DeviceHelper(driver)
        helper.press_recent_apps()

        driver.press_keycode.assert_called_once_with(187)

    @pytest.mark.unit
    def test_press_enter(self):
        """press_enter 呼叫 driver.press_keycode(66)"""
        from utils.device_helper import DeviceHelper

        driver = MagicMock()
        helper = DeviceHelper(driver)
        helper.press_enter()

        driver.press_keycode.assert_called_once_with(66)

    @pytest.mark.unit
    def test_press_volume_up(self):
        """press_volume_up 呼叫 driver.press_keycode(24)"""
        from utils.device_helper import DeviceHelper

        driver = MagicMock()
        helper = DeviceHelper(driver)
        helper.press_volume_up()

        driver.press_keycode.assert_called_once_with(24)

    @pytest.mark.unit
    def test_press_volume_down(self):
        """press_volume_down 呼叫 driver.press_keycode(25)"""
        from utils.device_helper import DeviceHelper

        driver = MagicMock()
        helper = DeviceHelper(driver)
        helper.press_volume_down()

        driver.press_keycode.assert_called_once_with(25)


@pytest.mark.unit
class TestOpenNotifications:
    """open_notifications — 打開通知欄"""

    @pytest.mark.unit
    def test_calls_driver_open_notifications(self):
        """呼叫 driver.open_notifications()"""
        from utils.device_helper import DeviceHelper

        driver = MagicMock()
        helper = DeviceHelper(driver)
        helper.open_notifications()

        driver.open_notifications.assert_called_once()


@pytest.mark.unit
class TestKeyboard:
    """鍵盤相關方法"""

    @pytest.mark.unit
    def test_hide_keyboard_success(self):
        """hide_keyboard 成功時呼叫 driver.hide_keyboard()"""
        from utils.device_helper import DeviceHelper

        driver = MagicMock()
        helper = DeviceHelper(driver)
        helper.hide_keyboard()

        driver.hide_keyboard.assert_called_once()

    @pytest.mark.unit
    def test_hide_keyboard_no_keyboard_shown(self):
        """鍵盤不在畫面上時不報錯"""
        from utils.device_helper import DeviceHelper

        driver = MagicMock()
        driver.hide_keyboard.side_effect = Exception("No keyboard")
        helper = DeviceHelper(driver)

        # 不應拋出例外
        helper.hide_keyboard()

    @pytest.mark.unit
    def test_is_keyboard_shown_true(self):
        """鍵盤顯示時回傳 True"""
        from utils.device_helper import DeviceHelper

        driver = MagicMock()
        driver.is_keyboard_shown.return_value = True
        helper = DeviceHelper(driver)

        assert helper.is_keyboard_shown() is True

    @pytest.mark.unit
    def test_is_keyboard_shown_false(self):
        """鍵盤未顯示時回傳 False"""
        from utils.device_helper import DeviceHelper

        driver = MagicMock()
        driver.is_keyboard_shown.return_value = False
        helper = DeviceHelper(driver)

        assert helper.is_keyboard_shown() is False


@pytest.mark.unit
class TestNetwork:
    """網路相關方法"""

    @pytest.mark.unit
    def test_set_airplane_mode_on(self):
        """開啟飛航模式 — set_network_connection(1)"""
        from utils.device_helper import DeviceHelper

        driver = MagicMock()
        helper = DeviceHelper(driver)
        helper.set_airplane_mode(on=True)

        driver.set_network_connection.assert_called_once_with(1)

    @pytest.mark.unit
    def test_set_airplane_mode_off(self):
        """關閉飛航模式 — set_network_connection(6)"""
        from utils.device_helper import DeviceHelper

        driver = MagicMock()
        helper = DeviceHelper(driver)
        helper.set_airplane_mode(on=False)

        driver.set_network_connection.assert_called_once_with(6)

    @pytest.mark.unit
    def test_set_airplane_mode_default_on(self):
        """set_airplane_mode 預設開啟"""
        from utils.device_helper import DeviceHelper

        driver = MagicMock()
        helper = DeviceHelper(driver)
        helper.set_airplane_mode()

        driver.set_network_connection.assert_called_once_with(1)

    @pytest.mark.unit
    def test_set_wifi_only(self):
        """僅 WiFi — set_network_connection(2)"""
        from utils.device_helper import DeviceHelper

        driver = MagicMock()
        helper = DeviceHelper(driver)
        helper.set_wifi_only()

        driver.set_network_connection.assert_called_once_with(2)

    @pytest.mark.unit
    def test_set_mobile_data_only(self):
        """僅行動數據 — set_network_connection(4)"""
        from utils.device_helper import DeviceHelper

        driver = MagicMock()
        helper = DeviceHelper(driver)
        helper.set_mobile_data_only()

        driver.set_network_connection.assert_called_once_with(4)

    @pytest.mark.unit
    def test_set_all_network(self):
        """開啟所有網路 — set_network_connection(6)"""
        from utils.device_helper import DeviceHelper

        driver = MagicMock()
        helper = DeviceHelper(driver)
        helper.set_all_network()

        driver.set_network_connection.assert_called_once_with(6)

    @pytest.mark.unit
    def test_get_network_connection(self):
        """取得網路連接狀態"""
        from utils.device_helper import DeviceHelper

        driver = MagicMock()
        driver.network_connection = 6
        helper = DeviceHelper(driver)

        assert helper.get_network_connection() == 6

    @pytest.mark.unit
    def test_get_network_connection_airplane(self):
        """取得飛航模式狀態"""
        from utils.device_helper import DeviceHelper

        driver = MagicMock()
        driver.network_connection = 1
        helper = DeviceHelper(driver)

        assert helper.get_network_connection() == 1


@pytest.mark.unit
class TestDeviceInfo:
    """get_device_info — 裝置資訊"""

    @pytest.mark.unit
    def test_returns_device_info_dict(self):
        """回傳包含所有裝置資訊的字典"""
        from utils.device_helper import DeviceHelper

        driver = MagicMock()
        driver.get_window_size.return_value = {"width": 1080, "height": 1920}
        driver.capabilities = {
            "platformName": "Android",
            "deviceName": "Pixel 5",
            "platformVersion": "12",
        }
        driver.orientation = "PORTRAIT"

        helper = DeviceHelper(driver)
        info = helper.get_device_info()

        assert info["platform"] == "Android"
        assert info["device_name"] == "Pixel 5"
        assert info["os_version"] == "12"
        assert info["screen_width"] == 1080
        assert info["screen_height"] == 1920
        assert info["orientation"] == "PORTRAIT"

    @pytest.mark.unit
    def test_missing_capabilities_returns_empty_string(self):
        """capabilities 缺少欄位時回傳空字串"""
        from utils.device_helper import DeviceHelper

        driver = MagicMock()
        driver.get_window_size.return_value = {"width": 720, "height": 1280}
        driver.capabilities = {}
        driver.orientation = "LANDSCAPE"

        helper = DeviceHelper(driver)
        info = helper.get_device_info()

        assert info["platform"] == ""
        assert info["device_name"] == ""
        assert info["os_version"] == ""

    @pytest.mark.unit
    def test_calls_get_window_size(self):
        """呼叫 driver.get_window_size()"""
        from utils.device_helper import DeviceHelper

        driver = MagicMock()
        driver.get_window_size.return_value = {"width": 1080, "height": 1920}
        driver.capabilities = {}
        driver.orientation = "PORTRAIT"

        helper = DeviceHelper(driver)
        helper.get_device_info()

        driver.get_window_size.assert_called_once()


@pytest.mark.unit
class TestClipboard:
    """剪貼簿相關方法"""

    @pytest.mark.unit
    def test_set_clipboard(self):
        """set_clipboard 呼叫 driver.set_clipboard_text"""
        from utils.device_helper import DeviceHelper

        driver = MagicMock()
        helper = DeviceHelper(driver)
        helper.set_clipboard("Hello World")

        driver.set_clipboard_text.assert_called_once_with("Hello World")

    @pytest.mark.unit
    def test_get_clipboard(self):
        """get_clipboard 回傳 driver.get_clipboard_text() 的結果"""
        from utils.device_helper import DeviceHelper

        driver = MagicMock()
        driver.get_clipboard_text.return_value = "copied text"
        helper = DeviceHelper(driver)

        result = helper.get_clipboard()
        assert result == "copied text"

    @pytest.mark.unit
    def test_get_clipboard_empty(self):
        """get_clipboard 回傳空字串"""
        from utils.device_helper import DeviceHelper

        driver = MagicMock()
        driver.get_clipboard_text.return_value = ""
        helper = DeviceHelper(driver)

        result = helper.get_clipboard()
        assert result == ""

    @pytest.mark.unit
    def test_set_clipboard_chinese(self):
        """set_clipboard 支援中文"""
        from utils.device_helper import DeviceHelper

        driver = MagicMock()
        helper = DeviceHelper(driver)
        helper.set_clipboard("你好世界")

        driver.set_clipboard_text.assert_called_once_with("你好世界")
