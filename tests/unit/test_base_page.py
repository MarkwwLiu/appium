"""
core.base_page 單元測試

驗證 BasePage 的所有公開與內部方法，包含：
- 初始化（含預設/自訂 timeout）
- 元素查找（快取命中、快取未命中、例外）
- 等待操作（clickable、visible）
- 元素操作（click、input_text、get_text、get_attribute）
- 內部操作方法（_do_click、_do_input_text、_do_get_text）
- Middleware 執行（成功、失敗觸發 emit_action_error）
- 滑動操作（上下左右）
- 頁面狀態（get_page_source、screenshot）
- Component 存取
"""

from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from core.base_page import BasePage
from core.exceptions import (
    ElementNotClickableError,
    ElementNotFoundError,
    ElementNotVisibleError,
)


@pytest.mark.unit
class TestBasePageInit:
    """BasePage 初始化測試"""

    @pytest.mark.unit
    @patch("core.base_page.WebDriverWait")
    @patch("core.base_page.Config")
    def test_init_with_default_timeout(self, mock_config, mock_wait_cls):
        """未指定 timeout 時使用 Config.EXPLICIT_WAIT"""
        mock_config.EXPLICIT_WAIT = 15
        driver = MagicMock()

        page = BasePage(driver)

        assert page.driver is driver
        assert page.timeout == 15
        mock_wait_cls.assert_called_once_with(driver, 15)

    @pytest.mark.unit
    @patch("core.base_page.WebDriverWait")
    @patch("core.base_page.Config")
    def test_init_with_custom_timeout(self, mock_config, mock_wait_cls):
        """指定 timeout 時覆蓋 Config 預設值"""
        mock_config.EXPLICIT_WAIT = 15
        driver = MagicMock()

        page = BasePage(driver, timeout=30)

        assert page.timeout == 30
        mock_wait_cls.assert_called_once_with(driver, 30)


@pytest.mark.unit
class TestBasePageFindElement:
    """find_element / find_elements 測試"""

    def setup_method(self):
        with patch("core.base_page.WebDriverWait"), \
             patch("core.base_page.Config") as mock_config:
            mock_config.EXPLICIT_WAIT = 10
            self.driver = MagicMock()
            self.page = BasePage(self.driver, timeout=10)
            self.page.wait = MagicMock()

    @pytest.mark.unit
    @patch("core.base_page.element_cache")
    def test_find_element_cache_hit(self, mock_cache):
        """快取命中時直接回傳快取元素"""
        locator = ("id", "btn_login")
        cached_element = MagicMock()
        mock_cache.get.return_value = cached_element

        result = self.page.find_element(locator)

        assert result is cached_element
        mock_cache.get.assert_called_once_with(locator)
        self.page.wait.until.assert_not_called()

    @pytest.mark.unit
    @patch("core.base_page.element_cache")
    def test_find_element_cache_miss(self, mock_cache):
        """快取未命中時透過 wait 查找並存入快取"""
        locator = ("id", "btn_login")
        mock_cache.get.return_value = None
        found_element = MagicMock()
        self.page.wait.until.return_value = found_element

        result = self.page.find_element(locator)

        assert result is found_element
        mock_cache.put.assert_called_once_with(locator, found_element)

    @pytest.mark.unit
    @patch("core.base_page.element_cache")
    def test_find_element_raises_element_not_found_error(self, mock_cache):
        """等待超時時拋出 ElementNotFoundError"""
        locator = ("id", "nonexistent")
        mock_cache.get.return_value = None
        self.page.wait.until.side_effect = Exception("Timeout")

        with pytest.raises(ElementNotFoundError):
            self.page.find_element(locator)

    @pytest.mark.unit
    def test_find_elements_success(self):
        """find_elements 成功回傳元素列表"""
        locator = ("xpath", "//button")
        mock_elements = [MagicMock(), MagicMock()]
        self.page.wait.until.return_value = True
        self.driver.find_elements.return_value = mock_elements

        result = self.page.find_elements(locator)

        assert result == mock_elements
        self.driver.find_elements.assert_called_once_with(*locator)


@pytest.mark.unit
class TestBasePageWait:
    """wait_for_clickable / wait_for_visible / is_element_present 測試"""

    def setup_method(self):
        with patch("core.base_page.WebDriverWait"), \
             patch("core.base_page.Config") as mock_config:
            mock_config.EXPLICIT_WAIT = 10
            self.driver = MagicMock()
            self.page = BasePage(self.driver, timeout=10)
            self.page.wait = MagicMock()

    @pytest.mark.unit
    def test_wait_for_clickable_success(self):
        """元素可點擊時正常回傳"""
        locator = ("id", "btn")
        expected_element = MagicMock()
        self.page.wait.until.return_value = expected_element

        result = self.page.wait_for_clickable(locator)

        assert result is expected_element

    @pytest.mark.unit
    def test_wait_for_clickable_raises_error(self):
        """元素不可點擊時拋出 ElementNotClickableError"""
        locator = ("id", "disabled_btn")
        self.page.wait.until.side_effect = Exception("Not clickable")

        with pytest.raises(ElementNotClickableError):
            self.page.wait_for_clickable(locator)

    @pytest.mark.unit
    def test_wait_for_visible_success(self):
        """元素可見時正常回傳"""
        locator = ("id", "label")
        expected_element = MagicMock()
        self.page.wait.until.return_value = expected_element

        result = self.page.wait_for_visible(locator)

        assert result is expected_element

    @pytest.mark.unit
    def test_wait_for_visible_raises_error(self):
        """元素不可見時拋出 ElementNotVisibleError"""
        locator = ("id", "hidden")
        self.page.wait.until.side_effect = Exception("Not visible")

        with pytest.raises(ElementNotVisibleError):
            self.page.wait_for_visible(locator)

    @pytest.mark.unit
    @patch("core.base_page.WebDriverWait")
    def test_is_element_present_true(self, mock_wait_cls):
        """元素存在時回傳 True"""
        locator = ("id", "exists")
        mock_wait_instance = MagicMock()
        mock_wait_cls.return_value = mock_wait_instance
        mock_wait_instance.until.return_value = MagicMock()

        result = self.page.is_element_present(locator, timeout=3)

        assert result is True
        mock_wait_cls.assert_called_once_with(self.driver, 3)

    @pytest.mark.unit
    @patch("core.base_page.WebDriverWait")
    def test_is_element_present_false(self, mock_wait_cls):
        """元素不存在時回傳 False"""
        locator = ("id", "missing")
        mock_wait_instance = MagicMock()
        mock_wait_cls.return_value = mock_wait_instance
        mock_wait_instance.until.side_effect = Exception("Not found")

        result = self.page.is_element_present(locator, timeout=3)

        assert result is False


@pytest.mark.unit
class TestBasePageActions:
    """click / input_text / get_text / get_attribute 測試"""

    def setup_method(self):
        with patch("core.base_page.WebDriverWait"), \
             patch("core.base_page.Config") as mock_config:
            mock_config.EXPLICIT_WAIT = 10
            self.driver = MagicMock()
            self.page = BasePage(self.driver, timeout=10)
            self.page.wait = MagicMock()

    @pytest.mark.unit
    def test_click_calls_run_with_middleware(self):
        """click 透過 _run_with_middleware 執行"""
        locator = ("id", "btn")
        self.page._run_with_middleware = MagicMock(return_value=None)

        self.page.click(locator)

        self.page._run_with_middleware.assert_called_once()
        call_args = self.page._run_with_middleware.call_args
        assert call_args[0][0] == "click"
        assert call_args[0][1] == locator

    @pytest.mark.unit
    def test_input_text_calls_run_with_middleware(self):
        """input_text 透過 _run_with_middleware 執行"""
        locator = ("id", "input_field")
        self.page._run_with_middleware = MagicMock(return_value=None)

        self.page.input_text(locator, "hello")

        self.page._run_with_middleware.assert_called_once()
        call_args = self.page._run_with_middleware.call_args
        assert call_args[0][0] == "input_text"
        assert call_args[0][1] == locator
        assert call_args[1]["text"] == "hello"

    @pytest.mark.unit
    def test_get_text_calls_run_with_middleware(self):
        """get_text 透過 _run_with_middleware 執行"""
        locator = ("id", "label")
        self.page._run_with_middleware = MagicMock(return_value="Hello World")

        result = self.page.get_text(locator)

        assert result == "Hello World"
        self.page._run_with_middleware.assert_called_once()

    @pytest.mark.unit
    @patch("core.base_page.element_cache")
    def test_get_attribute_returns_value(self, mock_cache):
        """get_attribute 回傳元素屬性"""
        locator = ("id", "el")
        mock_element = MagicMock()
        mock_element.get_attribute.return_value = "some_value"
        mock_cache.get.return_value = mock_element

        result = self.page.get_attribute(locator, "content-desc")

        assert result == "some_value"
        mock_element.get_attribute.assert_called_once_with("content-desc")


@pytest.mark.unit
class TestBasePageInternalActions:
    """_do_click / _do_input_text / _do_get_text 測試"""

    def setup_method(self):
        with patch("core.base_page.WebDriverWait"), \
             patch("core.base_page.Config") as mock_config:
            mock_config.EXPLICIT_WAIT = 10
            self.driver = MagicMock()
            self.page = BasePage(self.driver, timeout=10)
            self.page.wait = MagicMock()

    @pytest.mark.unit
    @patch("core.base_page.element_cache")
    def test_do_click_invalidates_cache_and_clicks(self, mock_cache):
        """_do_click 會清除快取並點擊可點擊元素"""
        locator = ("id", "btn")
        mock_element = MagicMock()
        self.page.wait.until.return_value = mock_element

        self.page._do_click(locator=locator)

        mock_cache.invalidate.assert_called_once_with(locator)
        mock_element.click.assert_called_once()

    @pytest.mark.unit
    def test_do_input_text_clears_and_sends_keys(self):
        """_do_input_text 會清除後輸入文字"""
        locator = ("id", "input")
        mock_element = MagicMock()
        self.page.wait.until.return_value = mock_element

        self.page._do_input_text(locator=locator, text="test123")

        mock_element.clear.assert_called_once()
        mock_element.send_keys.assert_called_once_with("test123")

    @pytest.mark.unit
    @patch("core.base_page.element_cache")
    def test_do_get_text_returns_element_text(self, mock_cache):
        """_do_get_text 回傳元素的 text"""
        locator = ("id", "label")
        mock_element = MagicMock()
        mock_element.text = "Expected Text"
        mock_cache.get.return_value = mock_element

        result = self.page._do_get_text(locator=locator)

        assert result == "Expected Text"


@pytest.mark.unit
class TestBasePageMiddleware:
    """_run_with_middleware 測試"""

    def setup_method(self):
        with patch("core.base_page.WebDriverWait"), \
             patch("core.base_page.Config") as mock_config:
            mock_config.EXPLICIT_WAIT = 10
            self.driver = MagicMock()
            self.page = BasePage(self.driver, timeout=10)
            self.page.wait = MagicMock()

    @pytest.mark.unit
    @patch("core.base_page.plugin_manager")
    @patch("core.base_page.middleware_chain")
    def test_run_with_middleware_success(self, mock_mw, mock_pm):
        """成功時觸發 before 和 after action"""
        locator = ("id", "el")
        mock_mw.execute.return_value = "result"
        core_fn = MagicMock()

        result = self.page._run_with_middleware(
            "click", locator, core_fn, some_key="some_val",
        )

        assert result == "result"
        mock_pm.emit_before_action.assert_called_once()
        mock_pm.emit_after_action.assert_called_once()
        mock_pm.emit_action_error.assert_not_called()

    @pytest.mark.unit
    @patch("core.base_page.plugin_manager")
    @patch("core.base_page.middleware_chain")
    def test_run_with_middleware_exception_triggers_error_event(
        self, mock_mw, mock_pm
    ):
        """middleware 執行失敗時觸發 emit_action_error 並重新拋出例外"""
        locator = ("id", "el")
        error = RuntimeError("Something went wrong")
        mock_mw.execute.side_effect = error
        core_fn = MagicMock()

        with pytest.raises(RuntimeError, match="Something went wrong"):
            self.page._run_with_middleware(
                "click", locator, core_fn, some_key="some_val",
            )

        mock_pm.emit_before_action.assert_called_once()
        mock_pm.emit_after_action.assert_not_called()
        mock_pm.emit_action_error.assert_called_once_with(
            self.page, "click", locator, error,
        )


@pytest.mark.unit
class TestBasePageSwipe:
    """swipe_up / swipe_down / swipe_left / swipe_right 測試"""

    def setup_method(self):
        with patch("core.base_page.WebDriverWait"), \
             patch("core.base_page.Config") as mock_config:
            mock_config.EXPLICIT_WAIT = 10
            self.driver = MagicMock()
            self.driver.get_window_size.return_value = {
                "width": 1080,
                "height": 1920,
            }
            self.page = BasePage(self.driver, timeout=10)

    @pytest.mark.unit
    @patch("core.base_page.element_cache")
    def test_swipe_up(self, mock_cache):
        """向上滑動：start_y > end_y，並清除快取"""
        self.page.swipe_up(duration=500)

        self.driver.swipe.assert_called_once_with(
            540,                    # width // 2
            int(1920 * 0.8),       # start_y
            540,                    # x
            int(1920 * 0.2),       # end_y
            500,
        )
        mock_cache.clear.assert_called_once()

    @pytest.mark.unit
    @patch("core.base_page.element_cache")
    def test_swipe_down(self, mock_cache):
        """向下滑動：start_y < end_y，並清除快取"""
        self.page.swipe_down(duration=600)

        self.driver.swipe.assert_called_once_with(
            540,
            int(1920 * 0.2),
            540,
            int(1920 * 0.8),
            600,
        )
        mock_cache.clear.assert_called_once()

    @pytest.mark.unit
    @patch("core.base_page.element_cache")
    def test_swipe_left(self, mock_cache):
        """向左滑動：start_x > end_x，並清除快取"""
        self.page.swipe_left(duration=700)

        self.driver.swipe.assert_called_once_with(
            int(1080 * 0.8),
            960,                    # height // 2
            int(1080 * 0.2),
            960,
            700,
        )
        mock_cache.clear.assert_called_once()

    @pytest.mark.unit
    @patch("core.base_page.element_cache")
    def test_swipe_right(self, mock_cache):
        """向右滑動：start_x < end_x，並清除快取"""
        self.page.swipe_right(duration=800)

        self.driver.swipe.assert_called_once_with(
            int(1080 * 0.2),
            960,
            int(1080 * 0.8),
            960,
            800,
        )
        mock_cache.clear.assert_called_once()

    @pytest.mark.unit
    @patch("core.base_page.element_cache")
    def test_swipe_up_default_duration(self, mock_cache):
        """swipe_up 預設 duration=800"""
        self.page.swipe_up()

        args = self.driver.swipe.call_args[0]
        assert args[4] == 800


@pytest.mark.unit
class TestBasePagePageState:
    """get_page_source / screenshot 測試"""

    def setup_method(self):
        with patch("core.base_page.WebDriverWait"), \
             patch("core.base_page.Config") as mock_config:
            mock_config.EXPLICIT_WAIT = 10
            self.driver = MagicMock()
            self.page = BasePage(self.driver, timeout=10)

    @pytest.mark.unit
    def test_get_page_source(self):
        """回傳 driver 的 page_source"""
        self.driver.page_source = "<xml>mock page</xml>"

        result = self.page.get_page_source()

        assert result == "<xml>mock page</xml>"

    @pytest.mark.unit
    @patch("core.base_page.take_screenshot")
    def test_screenshot_returns_filepath(self, mock_screenshot):
        """截圖回傳檔案路徑"""
        mock_screenshot.return_value = "/screenshots/test_20240101.png"

        result = self.page.screenshot("test")

        assert result == "/screenshots/test_20240101.png"
        mock_screenshot.assert_called_once_with(self.driver, "test")


@pytest.mark.unit
class TestBasePageComponent:
    """component 存取測試"""

    def setup_method(self):
        with patch("core.base_page.WebDriverWait"), \
             patch("core.base_page.Config") as mock_config:
            mock_config.EXPLICIT_WAIT = 10
            self.driver = MagicMock()
            self.page = BasePage(self.driver, timeout=10)

    @pytest.mark.unit
    def test_component_returns_attribute(self):
        """component 回傳 page 上的屬性"""
        mock_component = MagicMock()
        self.page.header = mock_component

        result = self.page.component("header")

        assert result is mock_component

    @pytest.mark.unit
    def test_component_raises_attribute_error_for_missing(self):
        """不存在的 component 拋出 AttributeError"""
        with pytest.raises(AttributeError):
            self.page.component("nonexistent_component")
