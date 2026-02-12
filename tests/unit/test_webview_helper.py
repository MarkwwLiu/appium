"""
utils.webview_helper 單元測試
驗證 WebViewHelper 的 Context 切換與 WebView 內操作功能。
"""

import pytest
from unittest.mock import MagicMock, patch, call


@pytest.mark.unit
class TestGetContexts:
    """get_contexts — 取得所有可用的 context"""

    @pytest.mark.unit
    def test_returns_contexts_list(self):
        """回傳 driver.contexts 的值"""
        with patch("utils.webview_helper.WebDriverWait"), \
             patch("utils.webview_helper.EC"), \
             patch("utils.webview_helper.By"):
            from utils.webview_helper import WebViewHelper

            driver = MagicMock()
            driver.contexts = ["NATIVE_APP", "WEBVIEW_com.example"]
            helper = WebViewHelper(driver)

            result = helper.get_contexts()

            assert result == ["NATIVE_APP", "WEBVIEW_com.example"]

    @pytest.mark.unit
    def test_returns_only_native(self):
        """只有 NATIVE_APP 時回傳"""
        with patch("utils.webview_helper.WebDriverWait"), \
             patch("utils.webview_helper.EC"), \
             patch("utils.webview_helper.By"):
            from utils.webview_helper import WebViewHelper

            driver = MagicMock()
            driver.contexts = ["NATIVE_APP"]
            helper = WebViewHelper(driver)

            result = helper.get_contexts()
            assert result == ["NATIVE_APP"]


@pytest.mark.unit
class TestGetCurrentContext:
    """get_current_context — 取得目前 context"""

    @pytest.mark.unit
    def test_returns_current_context(self):
        """回傳 driver.context 的值"""
        with patch("utils.webview_helper.WebDriverWait"), \
             patch("utils.webview_helper.EC"), \
             patch("utils.webview_helper.By"):
            from utils.webview_helper import WebViewHelper

            driver = MagicMock()
            driver.context = "NATIVE_APP"
            helper = WebViewHelper(driver)

            assert helper.get_current_context() == "NATIVE_APP"

    @pytest.mark.unit
    def test_returns_webview_context(self):
        """回傳 WEBVIEW context"""
        with patch("utils.webview_helper.WebDriverWait"), \
             patch("utils.webview_helper.EC"), \
             patch("utils.webview_helper.By"):
            from utils.webview_helper import WebViewHelper

            driver = MagicMock()
            driver.context = "WEBVIEW_com.example"
            helper = WebViewHelper(driver)

            assert helper.get_current_context() == "WEBVIEW_com.example"


@pytest.mark.unit
class TestSwitchToNative:
    """switch_to_native — 切換到 Native context"""

    @pytest.mark.unit
    def test_switches_to_native_app(self):
        """切換到 NATIVE_APP context"""
        with patch("utils.webview_helper.WebDriverWait"), \
             patch("utils.webview_helper.EC"), \
             patch("utils.webview_helper.By"):
            from utils.webview_helper import WebViewHelper

            driver = MagicMock()
            helper = WebViewHelper(driver)
            helper.switch_to_native()

            driver.switch_to.context.assert_called_once_with("NATIVE_APP")


@pytest.mark.unit
class TestSwitchToWebview:
    """switch_to_webview — 切換到 WebView context"""

    @pytest.mark.unit
    def test_switches_to_first_webview(self):
        """切換到第一個 WebView"""
        with patch("utils.webview_helper.WebDriverWait"), \
             patch("utils.webview_helper.EC"), \
             patch("utils.webview_helper.By"):
            from utils.webview_helper import WebViewHelper

            driver = MagicMock()
            driver.contexts = ["NATIVE_APP", "WEBVIEW_com.example"]
            helper = WebViewHelper(driver)

            result = helper.switch_to_webview()

            driver.switch_to.context.assert_called_once_with("WEBVIEW_com.example")
            assert result == "WEBVIEW_com.example"

    @pytest.mark.unit
    def test_switches_to_specific_index(self):
        """切換到指定 index 的 WebView"""
        with patch("utils.webview_helper.WebDriverWait"), \
             patch("utils.webview_helper.EC"), \
             patch("utils.webview_helper.By"):
            from utils.webview_helper import WebViewHelper

            driver = MagicMock()
            driver.contexts = [
                "NATIVE_APP",
                "WEBVIEW_com.app1",
                "WEBVIEW_com.app2",
            ]
            helper = WebViewHelper(driver)

            result = helper.switch_to_webview(index=1)

            driver.switch_to.context.assert_called_once_with("WEBVIEW_com.app2")
            assert result == "WEBVIEW_com.app2"

    @pytest.mark.unit
    def test_raises_runtime_error_no_webview(self):
        """找不到 WebView 時拋出 RuntimeError"""
        with patch("utils.webview_helper.WebDriverWait"), \
             patch("utils.webview_helper.EC"), \
             patch("utils.webview_helper.By"):
            from utils.webview_helper import WebViewHelper

            driver = MagicMock()
            driver.contexts = ["NATIVE_APP"]
            helper = WebViewHelper(driver)

            with pytest.raises(RuntimeError, match="找不到 WebView"):
                helper.switch_to_webview()

    @pytest.mark.unit
    def test_raises_index_error_out_of_range(self):
        """index 超出範圍時拋出 IndexError"""
        with patch("utils.webview_helper.WebDriverWait"), \
             patch("utils.webview_helper.EC"), \
             patch("utils.webview_helper.By"):
            from utils.webview_helper import WebViewHelper

            driver = MagicMock()
            driver.contexts = ["NATIVE_APP", "WEBVIEW_com.app1"]
            helper = WebViewHelper(driver)

            with pytest.raises(IndexError, match="超出範圍"):
                helper.switch_to_webview(index=5)


@pytest.mark.unit
class TestWaitForWebview:
    """wait_for_webview — 等待 WebView 出現"""

    @pytest.mark.unit
    def test_finds_webview_immediately(self):
        """WebView 立即出現時切換"""
        with patch("utils.webview_helper.WebDriverWait"), \
             patch("utils.webview_helper.EC"), \
             patch("utils.webview_helper.By"):
            from utils.webview_helper import WebViewHelper

            driver = MagicMock()
            driver.contexts = ["NATIVE_APP", "WEBVIEW_com.example"]
            helper = WebViewHelper(driver, timeout=5)

            result = helper.wait_for_webview()

            assert result == "WEBVIEW_com.example"
            driver.switch_to.context.assert_called_once_with("WEBVIEW_com.example")

    @pytest.mark.unit
    def test_raises_timeout_error(self):
        """等待逾時時拋出 TimeoutError"""
        import time as time_mod

        with patch("utils.webview_helper.WebDriverWait"), \
             patch("utils.webview_helper.EC"), \
             patch("utils.webview_helper.By"):
            from utils.webview_helper import WebViewHelper

            driver = MagicMock()
            driver.contexts = ["NATIVE_APP"]  # 永遠沒有 WebView
            helper = WebViewHelper(driver, timeout=1)

            # 使用很小的 timeout 讓迴圈快速結束
            with pytest.raises(TimeoutError, match="逾時"):
                helper.wait_for_webview(timeout=0)

    @pytest.mark.unit
    def test_uses_default_timeout(self):
        """使用預設 timeout"""
        with patch("utils.webview_helper.WebDriverWait"), \
             patch("utils.webview_helper.EC"), \
             patch("utils.webview_helper.By"):
            from utils.webview_helper import WebViewHelper

            driver = MagicMock()
            driver.contexts = ["NATIVE_APP", "WEBVIEW_test"]
            helper = WebViewHelper(driver, timeout=15)

            result = helper.wait_for_webview()
            assert result == "WEBVIEW_test"


@pytest.mark.unit
class TestIsInWebview:
    """is_in_webview — 判斷是否在 WebView"""

    @pytest.mark.unit
    def test_returns_true_in_webview(self):
        """在 WebView 時回傳 True"""
        with patch("utils.webview_helper.WebDriverWait"), \
             patch("utils.webview_helper.EC"), \
             patch("utils.webview_helper.By"):
            from utils.webview_helper import WebViewHelper

            driver = MagicMock()
            driver.context = "WEBVIEW_com.example"
            helper = WebViewHelper(driver)

            assert helper.is_in_webview() is True

    @pytest.mark.unit
    def test_returns_false_in_native(self):
        """在 Native 時回傳 False"""
        with patch("utils.webview_helper.WebDriverWait"), \
             patch("utils.webview_helper.EC"), \
             patch("utils.webview_helper.By"):
            from utils.webview_helper import WebViewHelper

            driver = MagicMock()
            driver.context = "NATIVE_APP"
            helper = WebViewHelper(driver)

            assert helper.is_in_webview() is False


@pytest.mark.unit
class TestExecuteJs:
    """execute_js — 在 WebView 中執行 JavaScript"""

    @pytest.mark.unit
    def test_calls_execute_script(self):
        """呼叫 driver.execute_script"""
        with patch("utils.webview_helper.WebDriverWait"), \
             patch("utils.webview_helper.EC"), \
             patch("utils.webview_helper.By"):
            from utils.webview_helper import WebViewHelper

            driver = MagicMock()
            driver.execute_script.return_value = "result"
            helper = WebViewHelper(driver)

            result = helper.execute_js("return document.title")

            driver.execute_script.assert_called_once_with("return document.title")
            assert result == "result"

    @pytest.mark.unit
    def test_passes_args(self):
        """傳遞額外參數"""
        with patch("utils.webview_helper.WebDriverWait"), \
             patch("utils.webview_helper.EC"), \
             patch("utils.webview_helper.By"):
            from utils.webview_helper import WebViewHelper

            driver = MagicMock()
            helper = WebViewHelper(driver)

            helper.execute_js("arguments[0].click()", "elem")

            driver.execute_script.assert_called_once_with("arguments[0].click()", "elem")


@pytest.mark.unit
class TestGetPageTitle:
    """get_page_title — 取得頁面標題"""

    @pytest.mark.unit
    def test_returns_title(self):
        """回傳 driver.title"""
        with patch("utils.webview_helper.WebDriverWait"), \
             patch("utils.webview_helper.EC"), \
             patch("utils.webview_helper.By"):
            from utils.webview_helper import WebViewHelper

            driver = MagicMock()
            driver.title = "My App Page"
            helper = WebViewHelper(driver)

            assert helper.get_page_title() == "My App Page"


@pytest.mark.unit
class TestGetCurrentUrl:
    """get_current_url — 取得目前 URL"""

    @pytest.mark.unit
    def test_returns_current_url(self):
        """回傳 driver.current_url"""
        with patch("utils.webview_helper.WebDriverWait"), \
             patch("utils.webview_helper.EC"), \
             patch("utils.webview_helper.By"):
            from utils.webview_helper import WebViewHelper

            driver = MagicMock()
            driver.current_url = "https://example.com/page"
            helper = WebViewHelper(driver)

            assert helper.get_current_url() == "https://example.com/page"


@pytest.mark.unit
class TestFindByCss:
    """find_by_css — CSS selector 查找"""

    @pytest.mark.unit
    def test_uses_webdriverwait(self):
        """使用 WebDriverWait 等待元素"""
        with patch("utils.webview_helper.By") as mock_by:
            mock_by.CSS_SELECTOR = "css selector"
            from utils.webview_helper import WebViewHelper

            driver = MagicMock()
            mock_element = MagicMock()

            with patch("utils.webview_helper.WebDriverWait") as mock_wait, \
                 patch("utils.webview_helper.EC") as mock_ec:
                mock_wait_instance = MagicMock()
                mock_wait_instance.until.return_value = mock_element
                mock_wait.return_value = mock_wait_instance

                helper = WebViewHelper(driver, timeout=10)
                result = helper.find_by_css(".my-class")

                mock_wait.assert_called_once_with(driver, 10)
                assert result == mock_element


@pytest.mark.unit
class TestFindByXpath:
    """find_by_xpath — XPath 查找"""

    @pytest.mark.unit
    def test_uses_webdriverwait(self):
        """使用 WebDriverWait 等待元素"""
        with patch("utils.webview_helper.By") as mock_by:
            mock_by.XPATH = "xpath"
            from utils.webview_helper import WebViewHelper

            driver = MagicMock()
            mock_element = MagicMock()

            with patch("utils.webview_helper.WebDriverWait") as mock_wait, \
                 patch("utils.webview_helper.EC") as mock_ec:
                mock_wait_instance = MagicMock()
                mock_wait_instance.until.return_value = mock_element
                mock_wait.return_value = mock_wait_instance

                helper = WebViewHelper(driver, timeout=5)
                result = helper.find_by_xpath("//div[@id='content']")

                mock_wait.assert_called_once_with(driver, 5)
                assert result == mock_element


@pytest.mark.unit
class TestClickByCss:
    """click_by_css — CSS selector 點擊"""

    @pytest.mark.unit
    def test_finds_and_clicks_element(self):
        """查找元素並點擊"""
        with patch("utils.webview_helper.By") as mock_by:
            mock_by.CSS_SELECTOR = "css selector"
            from utils.webview_helper import WebViewHelper

            driver = MagicMock()
            mock_element = MagicMock()

            with patch("utils.webview_helper.WebDriverWait") as mock_wait, \
                 patch("utils.webview_helper.EC"):
                mock_wait_instance = MagicMock()
                mock_wait_instance.until.return_value = mock_element
                mock_wait.return_value = mock_wait_instance

                helper = WebViewHelper(driver)
                helper.click_by_css("#submit-btn")

                mock_element.click.assert_called_once()


@pytest.mark.unit
class TestInputByCss:
    """input_by_css — CSS selector 輸入文字"""

    @pytest.mark.unit
    def test_clears_and_sends_keys(self):
        """清空欄位並輸入文字"""
        with patch("utils.webview_helper.By") as mock_by:
            mock_by.CSS_SELECTOR = "css selector"
            from utils.webview_helper import WebViewHelper

            driver = MagicMock()
            mock_element = MagicMock()

            with patch("utils.webview_helper.WebDriverWait") as mock_wait, \
                 patch("utils.webview_helper.EC"):
                mock_wait_instance = MagicMock()
                mock_wait_instance.until.return_value = mock_element
                mock_wait.return_value = mock_wait_instance

                helper = WebViewHelper(driver)
                helper.input_by_css("#username", "admin")

                mock_element.clear.assert_called_once()
                mock_element.send_keys.assert_called_once_with("admin")

    @pytest.mark.unit
    def test_clear_called_before_send_keys(self):
        """clear 在 send_keys 之前呼叫"""
        with patch("utils.webview_helper.By") as mock_by:
            mock_by.CSS_SELECTOR = "css selector"
            from utils.webview_helper import WebViewHelper

            driver = MagicMock()
            mock_element = MagicMock()
            call_order = []
            mock_element.clear.side_effect = lambda: call_order.append("clear")
            mock_element.send_keys.side_effect = lambda x: call_order.append("send_keys")

            with patch("utils.webview_helper.WebDriverWait") as mock_wait, \
                 patch("utils.webview_helper.EC"):
                mock_wait_instance = MagicMock()
                mock_wait_instance.until.return_value = mock_element
                mock_wait.return_value = mock_wait_instance

                helper = WebViewHelper(driver)
                helper.input_by_css("#email", "test@test.com")

                assert call_order == ["clear", "send_keys"]


@pytest.mark.unit
class TestScrollToElementJs:
    """scroll_to_element_js — JS 滾動到元素"""

    @pytest.mark.unit
    def test_calls_execute_js_with_scroll_script(self):
        """呼叫 execute_js 執行滾動腳本"""
        with patch("utils.webview_helper.WebDriverWait"), \
             patch("utils.webview_helper.EC"), \
             patch("utils.webview_helper.By"):
            from utils.webview_helper import WebViewHelper

            driver = MagicMock()
            helper = WebViewHelper(driver)

            helper.scroll_to_element_js("#target")

            driver.execute_script.assert_called_once_with(
                'document.querySelector("#target").scrollIntoView({behavior:"smooth"})'
            )

    @pytest.mark.unit
    def test_handles_class_selector(self):
        """處理 class selector"""
        with patch("utils.webview_helper.WebDriverWait"), \
             patch("utils.webview_helper.EC"), \
             patch("utils.webview_helper.By"):
            from utils.webview_helper import WebViewHelper

            driver = MagicMock()
            helper = WebViewHelper(driver)

            helper.scroll_to_element_js(".footer")

            driver.execute_script.assert_called_once_with(
                'document.querySelector(".footer").scrollIntoView({behavior:"smooth"})'
            )


@pytest.mark.unit
class TestWebViewHelperInit:
    """WebViewHelper.__init__ — 初始化"""

    @pytest.mark.unit
    def test_default_timeout(self):
        """預設 timeout 為 10"""
        with patch("utils.webview_helper.WebDriverWait"), \
             patch("utils.webview_helper.EC"), \
             patch("utils.webview_helper.By"):
            from utils.webview_helper import WebViewHelper

            driver = MagicMock()
            helper = WebViewHelper(driver)

            assert helper.timeout == 10

    @pytest.mark.unit
    def test_custom_timeout(self):
        """自訂 timeout"""
        with patch("utils.webview_helper.WebDriverWait"), \
             patch("utils.webview_helper.EC"), \
             patch("utils.webview_helper.By"):
            from utils.webview_helper import WebViewHelper

            driver = MagicMock()
            helper = WebViewHelper(driver, timeout=30)

            assert helper.timeout == 30

    @pytest.mark.unit
    def test_driver_stored(self):
        """driver 正確儲存"""
        with patch("utils.webview_helper.WebDriverWait"), \
             patch("utils.webview_helper.EC"), \
             patch("utils.webview_helper.By"):
            from utils.webview_helper import WebViewHelper

            driver = MagicMock()
            helper = WebViewHelper(driver)

            assert helper.driver is driver
