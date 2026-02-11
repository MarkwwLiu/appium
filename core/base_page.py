"""
Page Object 基底類別

所有 Page Object 都繼承此類，提供通用的元素操作方法。
已整合：
- Middleware 攔截
- Element Cache
- Event Bus 通知
- 自訂 Exception
- Component 支援
"""

from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config.config import Config
from core.element_cache import element_cache
from core.exceptions import (
    ElementNotClickableError,
    ElementNotFoundError,
    ElementNotVisibleError,
)
from core.middleware import MiddlewareContext, middleware_chain
from core.plugin_manager import plugin_manager
from utils.logger import logger
from utils.screenshot import take_screenshot


class BasePage:
    """
    Page Object 基底類別

    提供：
    - 元素等待與查找（含快取）
    - 點擊、輸入、滑動等通用操作
    - Middleware 前後攔截
    - 失敗時自動截圖 + 事件通知
    - Component 組合
    """

    def __init__(self, driver, timeout: int | None = None):
        self.driver = driver
        self.timeout = timeout or Config.EXPLICIT_WAIT
        self.wait = WebDriverWait(driver, self.timeout)

    # ── 元素查找（含快取）──

    def find_element(self, locator: tuple) -> WebElement:
        """等待元素出現並回傳（優先從快取取）"""
        cached = element_cache.get(locator)
        if cached is not None:
            return cached
        try:
            element = self.wait.until(EC.presence_of_element_located(locator))
            element_cache.put(locator, element)
            return element
        except Exception:
            raise ElementNotFoundError(locator, self.timeout)

    def find_elements(self, locator: tuple) -> list[WebElement]:
        """等待至少一個元素出現並回傳列表"""
        self.wait.until(EC.presence_of_element_located(locator))
        return self.driver.find_elements(*locator)

    def wait_for_clickable(self, locator: tuple) -> WebElement:
        """等待元素可點擊"""
        try:
            return self.wait.until(EC.element_to_be_clickable(locator))
        except Exception:
            raise ElementNotClickableError(locator)

    def wait_for_visible(self, locator: tuple) -> WebElement:
        """等待元素可見"""
        try:
            return self.wait.until(EC.visibility_of_element_located(locator))
        except Exception:
            raise ElementNotVisibleError(locator)

    def is_element_present(self, locator: tuple, timeout: int = 3) -> bool:
        """判斷元素是否存在（不拋出例外）"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(locator)
            )
            return True
        except Exception:
            return False

    # ── 元素操作（經過 Middleware）──

    def click(self, locator: tuple) -> None:
        """點擊元素"""
        self._run_with_middleware("click", locator, self._do_click, locator=locator)

    def input_text(self, locator: tuple, text: str) -> None:
        """清除後輸入文字"""
        self._run_with_middleware(
            "input_text", locator, self._do_input_text,
            locator=locator, text=text,
        )

    def get_text(self, locator: tuple) -> str:
        """取得元素文字"""
        return self._run_with_middleware(
            "get_text", locator, self._do_get_text, locator=locator,
        )

    def get_attribute(self, locator: tuple, attribute: str) -> str:
        """取得元素屬性"""
        return self.find_element(locator).get_attribute(attribute)

    # ── 實際操作（被 Middleware 包裹）──

    def _do_click(self, locator: tuple) -> None:
        logger.info(f"點擊元素: {locator}")
        element_cache.invalidate(locator)  # click 可能改變頁面
        self.wait_for_clickable(locator).click()

    def _do_input_text(self, locator: tuple, text: str) -> None:
        logger.info(f"輸入文字: '{text}' -> {locator}")
        element = self.wait_for_visible(locator)
        element.clear()
        element.send_keys(text)

    def _do_get_text(self, locator: tuple) -> str:
        return self.find_element(locator).text

    # ── Middleware 執行 ──

    def _run_with_middleware(self, action: str, locator: tuple,
                            core_fn, **kwargs):
        """經過 middleware 鏈執行操作"""
        context = MiddlewareContext(
            page=self, action=action, locator=locator, kwargs=kwargs,
        )

        plugin_manager.emit_before_action(self, action, locator, **kwargs)

        try:
            result = middleware_chain.execute(
                context,
                lambda: core_fn(**kwargs),
            )
            plugin_manager.emit_after_action(self, action, locator, **kwargs)
            return result
        except Exception as e:
            plugin_manager.emit_action_error(self, action, locator, e)
            raise

    # ── 滑動操作 ──

    def swipe_up(self, duration: int = 800) -> None:
        """向上滑動"""
        size = self.driver.get_window_size()
        x = size["width"] // 2
        start_y = int(size["height"] * 0.8)
        end_y = int(size["height"] * 0.2)
        self.driver.swipe(x, start_y, x, end_y, duration)
        element_cache.clear()  # 滑動後快取失效

    def swipe_down(self, duration: int = 800) -> None:
        """向下滑動"""
        size = self.driver.get_window_size()
        x = size["width"] // 2
        start_y = int(size["height"] * 0.2)
        end_y = int(size["height"] * 0.8)
        self.driver.swipe(x, start_y, x, end_y, duration)
        element_cache.clear()

    def swipe_left(self, duration: int = 800) -> None:
        """向左滑動"""
        size = self.driver.get_window_size()
        y = size["height"] // 2
        start_x = int(size["width"] * 0.8)
        end_x = int(size["width"] * 0.2)
        self.driver.swipe(start_x, y, end_x, y, duration)
        element_cache.clear()

    def swipe_right(self, duration: int = 800) -> None:
        """向右滑動"""
        size = self.driver.get_window_size()
        y = size["height"] // 2
        start_x = int(size["width"] * 0.2)
        end_x = int(size["width"] * 0.8)
        self.driver.swipe(start_x, y, end_x, y, duration)
        element_cache.clear()

    # ── 頁面狀態 ──

    def get_page_source(self) -> str:
        """取得頁面原始碼（debug 用）"""
        return self.driver.page_source

    def screenshot(self, name: str) -> str:
        """截圖並回傳檔案路徑"""
        return take_screenshot(self.driver, name)

    # ── Component 存取 ──

    def component(self, name: str):
        """
        取得 Component 實例。

        配合 ComponentDescriptor 使用：
            class MyPage(BasePage):
                header = ComponentDescriptor(HeaderComponent)

            page.component("header").tap_back()
            # 或直接 page.header.tap_back()
        """
        return getattr(self, name)
