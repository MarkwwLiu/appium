"""
core/exceptions.py 單元測試

驗證自訂例外體系的繼承關係、訊息格式、context 欄位。
"""

import pytest

from core.exceptions import (
    AppiumFrameworkError,
    CapsFileNotFoundError,
    ConfigError,
    DataFileNotFoundError,
    DriverConnectionError,
    DriverError,
    DriverNotInitializedError,
    ElementNotClickableError,
    ElementNotFoundError,
    ElementNotVisibleError,
    InvalidConfigError,
    PageError,
    PageNotLoadedError,
    PluginError,
    TestDataError,
)


@pytest.mark.unit
class TestExceptionHierarchy:
    """測試例外繼承關係"""

    @pytest.mark.unit
    def test_all_inherit_from_base(self):
        """所有例外都繼承 AppiumFrameworkError"""
        classes = [
            DriverError, DriverNotInitializedError, DriverConnectionError,
            PageError, ElementNotFoundError, ElementNotClickableError,
            ElementNotVisibleError, PageNotLoadedError,
            ConfigError, CapsFileNotFoundError, InvalidConfigError,
            TestDataError, DataFileNotFoundError, PluginError,
        ]
        for cls in classes:
            assert issubclass(cls, AppiumFrameworkError), f"{cls.__name__} 未繼承 AppiumFrameworkError"

    @pytest.mark.unit
    def test_driver_errors_inherit_driver_error(self):
        """Driver 類例外繼承 DriverError"""
        assert issubclass(DriverNotInitializedError, DriverError)
        assert issubclass(DriverConnectionError, DriverError)

    @pytest.mark.unit
    def test_page_errors_inherit_page_error(self):
        """Page 類例外繼承 PageError"""
        assert issubclass(ElementNotFoundError, PageError)
        assert issubclass(ElementNotClickableError, PageError)
        assert issubclass(ElementNotVisibleError, PageError)
        assert issubclass(PageNotLoadedError, PageError)

    @pytest.mark.unit
    def test_catch_base_catches_all(self):
        """catch AppiumFrameworkError 能攔截所有子類別"""
        with pytest.raises(AppiumFrameworkError):
            raise ElementNotFoundError(("id", "test"), 10)

        with pytest.raises(AppiumFrameworkError):
            raise DriverNotInitializedError()

        with pytest.raises(AppiumFrameworkError):
            raise PluginError("test", "error")


@pytest.mark.unit
class TestExceptionMessages:
    """測試例外訊息格式"""

    @pytest.mark.unit
    def test_driver_not_initialized_default_msg(self):
        """DriverNotInitializedError 有預設訊息"""
        e = DriverNotInitializedError()
        assert "create_driver" in str(e)

    @pytest.mark.unit
    def test_driver_connection_error_with_url(self):
        """DriverConnectionError 包含 URL"""
        e = DriverConnectionError(url="http://localhost:4723")
        assert "localhost:4723" in str(e)

    @pytest.mark.unit
    def test_driver_connection_error_with_original(self):
        """DriverConnectionError 包含原始錯誤資訊"""
        orig = ConnectionRefusedError("refused")
        e = DriverConnectionError(url="http://x", original=orig)
        assert "ConnectionRefusedError" in str(e)
        assert e.original is orig

    @pytest.mark.unit
    def test_element_not_found_with_timeout(self):
        """ElementNotFoundError 包含 locator 和 timeout"""
        e = ElementNotFoundError(("id", "btn_login"), 15)
        msg = str(e)
        assert "btn_login" in msg
        assert "15s" in msg

    @pytest.mark.unit
    def test_element_not_found_without_timeout(self):
        """ElementNotFoundError 無 timeout 時不顯示秒數"""
        e = ElementNotFoundError(("id", "test"))
        assert "s)" not in str(e)

    @pytest.mark.unit
    def test_page_not_loaded_with_name(self):
        """PageNotLoadedError 包含頁面名稱"""
        e = PageNotLoadedError("LoginPage")
        assert "LoginPage" in str(e)

    @pytest.mark.unit
    def test_page_not_loaded_empty(self):
        """PageNotLoadedError 無名稱時有預設訊息"""
        e = PageNotLoadedError()
        assert "頁面未載入" in str(e)

    @pytest.mark.unit
    def test_invalid_config_with_reason(self):
        """InvalidConfigError 包含 key/value/reason"""
        e = InvalidConfigError(key="timeout", value="-1", reason="必須為正整數")
        msg = str(e)
        assert "timeout" in msg
        assert "-1" in msg
        assert "正整數" in msg

    @pytest.mark.unit
    def test_plugin_error_format(self):
        """PluginError 格式正確"""
        e = PluginError(plugin_name="retry", message="載入失敗")
        assert "retry" in str(e)
        assert "載入失敗" in str(e)


@pytest.mark.unit
class TestExceptionContext:
    """測試 context 欄位"""

    @pytest.mark.unit
    def test_base_context_default_empty(self):
        """AppiumFrameworkError context 預設空 dict"""
        e = AppiumFrameworkError("test")
        assert e.context == {}

    @pytest.mark.unit
    def test_element_not_found_context(self):
        """ElementNotFoundError context 包含 locator 和 timeout"""
        e = ElementNotFoundError(("xpath", "//btn"), 20)
        assert e.context["locator"] == ("xpath", "//btn")
        assert e.context["timeout"] == 20

    @pytest.mark.unit
    def test_caps_file_context(self):
        """CapsFileNotFoundError context 包含 path"""
        e = CapsFileNotFoundError("/path/to/caps.json")
        assert e.context["path"] == "/path/to/caps.json"

    @pytest.mark.unit
    def test_driver_connection_context(self):
        """DriverConnectionError context 包含 url"""
        e = DriverConnectionError(url="http://test:4723")
        assert e.context["url"] == "http://test:4723"
