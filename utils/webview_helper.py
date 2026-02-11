"""
WebView 切換工具
Hybrid App 在 Native 與 WebView 之間切換，並提供 WebView 內的操作。
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from utils.logger import logger


class WebViewHelper:
    """Hybrid App 的 Native / WebView context 切換"""

    def __init__(self, driver, timeout: int = 10):
        self.driver = driver
        self.timeout = timeout

    # ── Context 切換 ──

    def get_contexts(self) -> list[str]:
        """取得所有可用的 context"""
        contexts = self.driver.contexts
        logger.info(f"可用 contexts: {contexts}")
        return contexts

    def get_current_context(self) -> str:
        """取得目前 context"""
        return self.driver.context

    def switch_to_native(self) -> None:
        """切換到 Native context"""
        logger.info("切換到 NATIVE_APP")
        self.driver.switch_to.context("NATIVE_APP")

    def switch_to_webview(self, index: int = 0) -> str:
        """
        切換到 WebView context。

        Args:
            index: 若有多個 WebView，指定 index (0-based)

        Returns:
            切換到的 context 名稱
        """
        contexts = self.get_contexts()
        webviews = [c for c in contexts if "WEBVIEW" in c.upper()]

        if not webviews:
            raise RuntimeError("找不到 WebView context")

        if index >= len(webviews):
            raise IndexError(
                f"WebView index {index} 超出範圍 (共 {len(webviews)} 個)"
            )

        target = webviews[index]
        logger.info(f"切換到 WebView: {target}")
        self.driver.switch_to.context(target)
        return target

    def wait_for_webview(self, timeout: int | None = None) -> str:
        """等待 WebView context 出現後切換"""
        timeout = timeout or self.timeout
        logger.info(f"等待 WebView 出現 (最多 {timeout}s)...")

        end_time = __import__("time").time() + timeout
        while __import__("time").time() < end_time:
            contexts = self.driver.contexts
            webviews = [c for c in contexts if "WEBVIEW" in c.upper()]
            if webviews:
                self.driver.switch_to.context(webviews[0])
                logger.info(f"已切換到: {webviews[0]}")
                return webviews[0]
            __import__("time").sleep(0.5)

        raise TimeoutError(f"等待 WebView 逾時 ({timeout}s)")

    def is_in_webview(self) -> bool:
        """判斷目前是否在 WebView"""
        return "WEBVIEW" in self.get_current_context().upper()

    # ── WebView 內操作 ──

    def execute_js(self, script: str, *args) -> any:
        """在 WebView 中執行 JavaScript"""
        logger.info(f"執行 JS: {script[:80]}...")
        return self.driver.execute_script(script, *args)

    def get_page_title(self) -> str:
        """取得 WebView 頁面標題"""
        return self.driver.title

    def get_current_url(self) -> str:
        """取得 WebView 目前 URL"""
        return self.driver.current_url

    def find_by_css(self, selector: str):
        """在 WebView 中用 CSS selector 查找元素"""
        return WebDriverWait(self.driver, self.timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )

    def find_by_xpath(self, xpath: str):
        """在 WebView 中用 XPath 查找元素"""
        return WebDriverWait(self.driver, self.timeout).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )

    def click_by_css(self, selector: str) -> None:
        """用 CSS selector 點擊元素"""
        element = self.find_by_css(selector)
        element.click()

    def input_by_css(self, selector: str, text: str) -> None:
        """用 CSS selector 輸入文字"""
        element = self.find_by_css(selector)
        element.clear()
        element.send_keys(text)

    def scroll_to_element_js(self, selector: str) -> None:
        """用 JS 滾動到指定元素"""
        self.execute_js(
            f'document.querySelector("{selector}").scrollIntoView({{behavior:"smooth"}})'
        )
