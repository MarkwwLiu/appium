"""
UI Component 模式 — 可組合的共用元件

很多頁面有共用的 UI 區塊：Header、TabBar、SearchBar、Dialog...
把它們抽成 Component，任何 Page 都可以 mixin。

用法：
    class HeaderComponent(Component):
        BACK_BTN = (AppiumBy.ID, "com.app:id/btn_back")
        TITLE = (AppiumBy.ID, "com.app:id/tv_title")

        def tap_back(self):
            self.click(self.BACK_BTN)

        def get_title(self) -> str:
            return self.get_text(self.TITLE)

    class SettingsPage(BasePage):
        header = HeaderComponent        # 宣告使用 component
        WIFI_SWITCH = (AppiumBy.ID, "...")

        def tap_back(self):
            self.component("header").tap_back()

        # 或 BasePage 整合後直接：
        # self.header.tap_back()
"""

from __future__ import annotations

from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from utils.logger import logger


class Component:
    """
    可組合的 UI 元件基底

    共用 driver 和 wait，提供與 BasePage 相同的元素操作。
    差別在於 Component 代表一個 UI 區塊，而非整個頁面。
    """

    def __init__(self, driver, timeout: int = 10,
                 root_locator: tuple | None = None):
        """
        Args:
            driver: Appium driver
            timeout: 等待秒數
            root_locator: 此 Component 的根元素 locator（限定搜尋範圍）
        """
        self.driver = driver
        self.timeout = timeout
        self.root_locator = root_locator
        self._root_element: WebElement | None = None

    @property
    def root(self) -> WebElement | None:
        """取得此 Component 的根元素"""
        if self.root_locator and self._root_element is None:
            try:
                self._root_element = WebDriverWait(
                    self.driver, self.timeout
                ).until(EC.presence_of_element_located(self.root_locator))
            except Exception:
                self._root_element = None
        return self._root_element

    def _search_context(self):
        """取得搜尋 context（root element 或 driver）"""
        return self.root if self.root else self.driver

    # ── 元素操作（與 BasePage 一致）──

    def find_element(self, locator: tuple) -> WebElement:
        return WebDriverWait(self.driver, self.timeout).until(
            EC.presence_of_element_located(locator)
        )

    def find_elements(self, locator: tuple) -> list[WebElement]:
        self.find_element(locator)  # 先等第一個出現
        return self.driver.find_elements(*locator)

    def click(self, locator: tuple) -> None:
        logger.debug(f"[Component] click: {locator}")
        WebDriverWait(self.driver, self.timeout).until(
            EC.element_to_be_clickable(locator)
        ).click()

    def input_text(self, locator: tuple, text: str) -> None:
        logger.debug(f"[Component] input: '{text}' -> {locator}")
        el = WebDriverWait(self.driver, self.timeout).until(
            EC.visibility_of_element_located(locator)
        )
        el.clear()
        el.send_keys(text)

    def get_text(self, locator: tuple) -> str:
        return self.find_element(locator).text

    def is_displayed(self, locator: tuple, timeout: int = 3) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(locator)
            )
            return True
        except Exception:
            return False


class ComponentDescriptor:
    """
    Descriptor，讓 Page 可以用 class attribute 方式宣告 Component。

    用法：
        class MyPage(BasePage):
            header = ComponentDescriptor(HeaderComponent)

        page = MyPage(driver)
        page.header.tap_back()   # 自動建立 HeaderComponent 實例
    """

    def __init__(self, component_class: type[Component], **kwargs):
        self.component_class = component_class
        self.kwargs = kwargs
        self._attr_name = ""

    def __set_name__(self, owner, name):
        self._attr_name = f"_component_{name}"

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        # lazy init: 第一次存取時建立 Component 實例
        if not hasattr(obj, self._attr_name):
            instance = self.component_class(
                driver=obj.driver,
                timeout=getattr(obj, "timeout", 10),
                **self.kwargs,
            )
            setattr(obj, self._attr_name, instance)
        return getattr(obj, self._attr_name)
