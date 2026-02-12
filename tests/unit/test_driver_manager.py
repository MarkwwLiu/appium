"""
core.driver_manager 單元測試

驗證 DriverManager 的所有方法：
- health_check（成功、URLError、Timeout）
- create_driver（android/ios/invalid 平台、重試邏輯、全部失敗拋出 DriverConnectionError）
- get_driver（有 driver、無 driver）
- quit_driver（有 driver、無 driver）
"""

import urllib.error
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from core.driver_manager import DriverManager
from core.exceptions import DriverConnectionError, DriverNotInitializedError


@pytest.mark.unit
class TestDriverManagerHealthCheck:
    """health_check 測試"""

    @pytest.mark.unit
    @patch("core.driver_manager.Config")
    @patch("core.driver_manager.urllib.request.urlopen")
    @patch("core.driver_manager.urllib.request.Request")
    def test_health_check_success(self, mock_request_cls, mock_urlopen, mock_config):
        """server 回傳 200 時回傳 True"""
        mock_config.appium_server_url.return_value = "http://127.0.0.1:4723"
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = DriverManager.health_check("http://127.0.0.1:4723")

        assert result is True
        mock_request_cls.assert_called_once_with(
            "http://127.0.0.1:4723/status", method="GET"
        )

    @pytest.mark.unit
    @patch("core.driver_manager.Config")
    @patch("core.driver_manager.urllib.request.urlopen")
    @patch("core.driver_manager.urllib.request.Request")
    def test_health_check_url_error_returns_false(
        self, mock_request_cls, mock_urlopen, mock_config
    ):
        """URLError 時回傳 False"""
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        result = DriverManager.health_check("http://127.0.0.1:4723")

        assert result is False

    @pytest.mark.unit
    @patch("core.driver_manager.Config")
    @patch("core.driver_manager.urllib.request.urlopen")
    @patch("core.driver_manager.urllib.request.Request")
    def test_health_check_timeout_returns_false(
        self, mock_request_cls, mock_urlopen, mock_config
    ):
        """Timeout 時回傳 False"""
        mock_urlopen.side_effect = TimeoutError("Timed out")

        result = DriverManager.health_check("http://127.0.0.1:4723")

        assert result is False

    @pytest.mark.unit
    @patch("core.driver_manager.Config")
    @patch("core.driver_manager.urllib.request.urlopen")
    @patch("core.driver_manager.urllib.request.Request")
    def test_health_check_os_error_returns_false(
        self, mock_request_cls, mock_urlopen, mock_config
    ):
        """OSError 時回傳 False"""
        mock_urlopen.side_effect = OSError("Network unreachable")

        result = DriverManager.health_check("http://127.0.0.1:4723")

        assert result is False

    @pytest.mark.unit
    @patch("core.driver_manager.urllib.request.urlopen")
    @patch("core.driver_manager.urllib.request.Request")
    @patch("core.driver_manager.Config")
    def test_health_check_uses_config_url_when_none(
        self, mock_config, mock_request_cls, mock_urlopen
    ):
        """未指定 URL 時使用 Config.appium_server_url()"""
        mock_config.appium_server_url.return_value = "http://localhost:4723"
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        DriverManager.health_check()

        mock_config.appium_server_url.assert_called_once()
        mock_request_cls.assert_called_once_with(
            "http://localhost:4723/status", method="GET"
        )


@pytest.mark.unit
class TestDriverManagerCreateDriver:
    """create_driver 測試"""

    def setup_method(self):
        """每次測試前重設 thread-local driver"""
        DriverManager._local.driver = None

    @pytest.mark.unit
    @patch("core.driver_manager.time.sleep")
    @patch("core.driver_manager.plugin_manager")
    @patch("core.driver_manager.element_cache")
    @patch("core.driver_manager.webdriver.Remote")
    @patch("core.driver_manager.UiAutomator2Options")
    @patch("core.driver_manager.Config")
    @patch.object(DriverManager, "health_check", return_value=True)
    def test_create_driver_android(
        self, mock_health, mock_config, mock_ui2_opts, mock_remote,
        mock_cache, mock_pm, mock_sleep
    ):
        """建立 Android driver 使用 UiAutomator2Options"""
        mock_config.PLATFORM = "android"
        mock_config.load_caps.return_value = {"platformName": "Android"}
        mock_config.appium_server_url.return_value = "http://127.0.0.1:4723"
        mock_config.IMPLICIT_WAIT = 10

        mock_options_instance = MagicMock()
        mock_ui2_opts.return_value.load_capabilities.return_value = mock_options_instance
        mock_driver = MagicMock()
        mock_remote.return_value = mock_driver

        result = DriverManager.create_driver(platform="android")

        assert result is mock_driver
        mock_config.load_caps.assert_called_once_with("android")
        mock_ui2_opts.return_value.load_capabilities.assert_called_once_with(
            {"platformName": "Android"}
        )
        mock_driver.implicitly_wait.assert_called_once_with(10)
        mock_pm.emit_driver_created.assert_called_once_with(mock_driver)

    @pytest.mark.unit
    @patch("core.driver_manager.time.sleep")
    @patch("core.driver_manager.plugin_manager")
    @patch("core.driver_manager.element_cache")
    @patch("core.driver_manager.webdriver.Remote")
    @patch("core.driver_manager.XCUITestOptions")
    @patch("core.driver_manager.Config")
    @patch.object(DriverManager, "health_check", return_value=True)
    def test_create_driver_ios(
        self, mock_health, mock_config, mock_xcui_opts, mock_remote,
        mock_cache, mock_pm, mock_sleep
    ):
        """建立 iOS driver 使用 XCUITestOptions"""
        mock_config.PLATFORM = "ios"
        mock_config.load_caps.return_value = {"platformName": "iOS"}
        mock_config.appium_server_url.return_value = "http://127.0.0.1:4723"
        mock_config.IMPLICIT_WAIT = 10

        mock_options_instance = MagicMock()
        mock_xcui_opts.return_value.load_capabilities.return_value = mock_options_instance
        mock_driver = MagicMock()
        mock_remote.return_value = mock_driver

        result = DriverManager.create_driver(platform="ios")

        assert result is mock_driver
        mock_xcui_opts.return_value.load_capabilities.assert_called_once_with(
            {"platformName": "iOS"}
        )
        mock_pm.emit_driver_created.assert_called_once_with(mock_driver)

    @pytest.mark.unit
    @patch("core.driver_manager.Config")
    def test_create_driver_invalid_platform_raises_value_error(self, mock_config):
        """不支援的平台拋出 ValueError"""
        mock_config.PLATFORM = "windows"
        mock_config.load_caps.return_value = {}

        with pytest.raises(ValueError, match="不支援的平台"):
            DriverManager.create_driver(platform="windows")

    @pytest.mark.unit
    @patch("core.driver_manager.time.sleep")
    @patch("core.driver_manager.plugin_manager")
    @patch("core.driver_manager.element_cache")
    @patch("core.driver_manager.webdriver.Remote")
    @patch("core.driver_manager.UiAutomator2Options")
    @patch("core.driver_manager.Config")
    @patch.object(DriverManager, "health_check", return_value=True)
    def test_create_driver_retry_on_failure(
        self, mock_health, mock_config, mock_ui2_opts, mock_remote,
        mock_cache, mock_pm, mock_sleep
    ):
        """連線失敗後重試並最終成功"""
        mock_config.PLATFORM = "android"
        mock_config.load_caps.return_value = {"platformName": "Android"}
        mock_config.appium_server_url.return_value = "http://127.0.0.1:4723"
        mock_config.IMPLICIT_WAIT = 10

        mock_options_instance = MagicMock()
        mock_ui2_opts.return_value.load_capabilities.return_value = mock_options_instance
        mock_driver = MagicMock()

        # 前兩次失敗，第三次成功
        mock_remote.side_effect = [
            ConnectionError("Fail 1"),
            ConnectionError("Fail 2"),
            mock_driver,
        ]

        result = DriverManager.create_driver(
            platform="android", max_retries=3, retry_delay=1.0,
        )

        assert result is mock_driver
        assert mock_remote.call_count == 3
        # 指數退避: sleep(1.0), sleep(2.0)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1.0)
        mock_sleep.assert_any_call(2.0)

    @pytest.mark.unit
    @patch("core.driver_manager.time.sleep")
    @patch("core.driver_manager.plugin_manager")
    @patch("core.driver_manager.element_cache")
    @patch("core.driver_manager.webdriver.Remote")
    @patch("core.driver_manager.UiAutomator2Options")
    @patch("core.driver_manager.Config")
    @patch.object(DriverManager, "health_check", return_value=False)
    def test_create_driver_all_retries_fail_raises_error(
        self, mock_health, mock_config, mock_ui2_opts, mock_remote,
        mock_cache, mock_pm, mock_sleep
    ):
        """所有重試失敗後拋出 DriverConnectionError"""
        mock_config.PLATFORM = "android"
        mock_config.load_caps.return_value = {"platformName": "Android"}
        mock_config.appium_server_url.return_value = "http://127.0.0.1:4723"

        mock_options_instance = MagicMock()
        mock_ui2_opts.return_value.load_capabilities.return_value = mock_options_instance

        mock_remote.side_effect = ConnectionError("Connection refused")

        with pytest.raises(DriverConnectionError):
            DriverManager.create_driver(
                platform="android", max_retries=3, retry_delay=0.5,
            )

        assert mock_remote.call_count == 3

    @pytest.mark.unit
    @patch("core.driver_manager.time.sleep")
    @patch("core.driver_manager.plugin_manager")
    @patch("core.driver_manager.element_cache")
    @patch("core.driver_manager.webdriver.Remote")
    @patch("core.driver_manager.UiAutomator2Options")
    @patch("core.driver_manager.Config")
    @patch.object(DriverManager, "health_check", return_value=False)
    def test_create_driver_health_check_fails_still_attempts(
        self, mock_health, mock_config, mock_ui2_opts, mock_remote,
        mock_cache, mock_pm, mock_sleep
    ):
        """健康檢查失敗時仍嘗試連線"""
        mock_config.PLATFORM = "android"
        mock_config.load_caps.return_value = {"platformName": "Android"}
        mock_config.appium_server_url.return_value = "http://127.0.0.1:4723"
        mock_config.IMPLICIT_WAIT = 10

        mock_options_instance = MagicMock()
        mock_ui2_opts.return_value.load_capabilities.return_value = mock_options_instance
        mock_driver = MagicMock()
        mock_remote.return_value = mock_driver

        result = DriverManager.create_driver(platform="android")

        assert result is mock_driver
        mock_remote.assert_called_once()

    @pytest.mark.unit
    @patch("core.driver_manager.time.sleep")
    @patch("core.driver_manager.plugin_manager")
    @patch("core.driver_manager.element_cache")
    @patch("core.driver_manager.webdriver.Remote")
    @patch("core.driver_manager.UiAutomator2Options")
    @patch("core.driver_manager.Config")
    @patch.object(DriverManager, "health_check", return_value=True)
    def test_create_driver_uses_config_platform_when_none(
        self, mock_health, mock_config, mock_ui2_opts, mock_remote,
        mock_cache, mock_pm, mock_sleep
    ):
        """未指定 platform 時使用 Config.PLATFORM"""
        mock_config.PLATFORM = "android"
        mock_config.load_caps.return_value = {"platformName": "Android"}
        mock_config.appium_server_url.return_value = "http://127.0.0.1:4723"
        mock_config.IMPLICIT_WAIT = 10

        mock_options_instance = MagicMock()
        mock_ui2_opts.return_value.load_capabilities.return_value = mock_options_instance
        mock_driver = MagicMock()
        mock_remote.return_value = mock_driver

        DriverManager.create_driver(platform=None)

        mock_config.load_caps.assert_called_once_with("android")


@pytest.mark.unit
class TestDriverManagerGetDriver:
    """get_driver 測試"""

    def setup_method(self):
        DriverManager._local.driver = None

    @pytest.mark.unit
    def test_get_driver_with_driver_returns_it(self):
        """有 driver 時回傳 driver"""
        mock_driver = MagicMock()
        DriverManager._local.driver = mock_driver

        result = DriverManager.get_driver()

        assert result is mock_driver

    @pytest.mark.unit
    def test_get_driver_without_driver_raises_error(self):
        """無 driver 時拋出 DriverNotInitializedError"""
        DriverManager._local.driver = None

        with pytest.raises(DriverNotInitializedError):
            DriverManager.get_driver()


@pytest.mark.unit
class TestDriverManagerQuitDriver:
    """quit_driver 測試"""

    def setup_method(self):
        DriverManager._local.driver = None

    @pytest.mark.unit
    @patch("core.driver_manager.plugin_manager")
    @patch("core.driver_manager.element_cache")
    def test_quit_driver_with_driver_calls_quit_and_cleanup(
        self, mock_cache, mock_pm
    ):
        """有 driver 時呼叫 quit、清除快取、通知 Plugin"""
        mock_driver = MagicMock()
        DriverManager._local.driver = mock_driver

        DriverManager.quit_driver()

        mock_pm.emit_driver_quit.assert_called_once_with(mock_driver)
        mock_cache.clear.assert_called_once()
        mock_driver.quit.assert_called_once()
        assert DriverManager._local.driver is None

    @pytest.mark.unit
    @patch("core.driver_manager.plugin_manager")
    @patch("core.driver_manager.element_cache")
    def test_quit_driver_without_driver_does_nothing(self, mock_cache, mock_pm):
        """無 driver 時不做任何事"""
        DriverManager._local.driver = None

        DriverManager.quit_driver()

        mock_pm.emit_driver_quit.assert_not_called()
        mock_cache.clear.assert_not_called()
