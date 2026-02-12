"""
config.config 單元測試
驗證 Config 的 capabilities 驗證功能。
"""

import pytest

from config.config import Config, ConfigValidationError


class TestConfigValidation:
    """Capabilities 驗證"""

    def test_valid_android_caps(self):
        caps = {
            "platformName": "Android",
            "appium:deviceName": "emulator",
            "appium:app": "/path/to/app.apk",
            "appium:automationName": "UiAutomator2",
            "appium:appPackage": "com.example",
            "appium:appActivity": ".MainActivity",
        }
        warnings = Config.validate_caps(caps, "android")
        assert len(warnings) == 0

    def test_valid_ios_caps(self):
        caps = {
            "platformName": "iOS",
            "appium:deviceName": "iPhone 15",
            "appium:app": "/path/to/app.ipa",
            "appium:automationName": "XCUITest",
            "appium:bundleId": "com.example.app",
        }
        warnings = Config.validate_caps(caps, "ios")
        assert len(warnings) == 0

    def test_missing_required_raises(self):
        caps = {"platformName": "Android"}
        with pytest.raises(ConfigValidationError) as exc_info:
            Config.validate_caps(caps, "android")
        assert "appium:deviceName" in str(exc_info.value)
        assert "appium:app" in str(exc_info.value)

    def test_missing_recommended_returns_warnings(self):
        caps = {
            "platformName": "Android",
            "appium:deviceName": "emulator",
            "appium:app": "/path/to/app.apk",
        }
        warnings = Config.validate_caps(caps, "android")
        assert any("appium:automationName" in w for w in warnings)

    def test_validation_error_has_error_list(self):
        caps = {}
        with pytest.raises(ConfigValidationError) as exc_info:
            Config.validate_caps(caps, "android")
        assert len(exc_info.value.errors) >= 3

    def test_appium_server_url(self):
        url = Config.appium_server_url()
        assert url.startswith("http://")
        assert ":" in url
