"""
Page Object 基底類別
所有 Page Object 都繼承此類，提供通用的元素操作方法。
"""

from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config.config import Config
from utils.logger import logger
from utils.screenshot import take_screenshot


class BasePage:
    """
    Page Object 基底類別

    提供：
    - 元素等待與查找
    - 點擊、輸入、滑動等通用操作
    - 失敗時自動截圖
    """

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, Config.EXPLICIT_WAIT)

    # ── 元素查找 ──

    def find_element(self, locator: tuple) -> WebElement:
        """等待元素出現並回傳"""
        return self.wait.until(EC.presence_of_element_located(locator))

    def find_elements(self, locator: tuple) -> list[WebElement]:
        """等待至少一個元素出現並回傳列表"""
        self.wait.until(EC.presence_of_element_located(locator))
        return self.driver.find_elements(*locator)

    def wait_for_clickable(self, locator: tuple) -> WebElement:
        """等待元素可點擊"""
        return self.wait.until(EC.element_to_be_clickable(locator))

    def wait_for_visible(self, locator: tuple) -> WebElement:
        """等待元素可見"""
        return self.wait.until(EC.visibility_of_element_located(locator))

    def is_element_present(self, locator: tuple, timeout: int = 3) -> bool:
        """判斷元素是否存在（不拋出例外）"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(locator)
            )
            return True
        except Exception:
            return False

    # ── 元素操作 ──

    def click(self, locator: tuple) -> None:
        """點擊元素"""
        logger.info(f"點擊元素: {locator}")
        self.wait_for_clickable(locator).click()

    def input_text(self, locator: tuple, text: str) -> None:
        """清除後輸入文字"""
        logger.info(f"輸入文字: '{text}' -> {locator}")
        element = self.wait_for_visible(locator)
        element.clear()
        element.send_keys(text)

    def get_text(self, locator: tuple) -> str:
        """取得元素文字"""
        return self.find_element(locator).text

    def get_attribute(self, locator: tuple, attribute: str) -> str:
        """取得元素屬性"""
        return self.find_element(locator).get_attribute(attribute)

    # ── 滑動操作 ──

    def swipe_up(self, duration: int = 800) -> None:
        """向上滑動"""
        size = self.driver.get_window_size()
        x = size["width"] // 2
        start_y = int(size["height"] * 0.8)
        end_y = int(size["height"] * 0.2)
        self.driver.swipe(x, start_y, x, end_y, duration)

    def swipe_down(self, duration: int = 800) -> None:
        """向下滑動"""
        size = self.driver.get_window_size()
        x = size["width"] // 2
        start_y = int(size["height"] * 0.2)
        end_y = int(size["height"] * 0.8)
        self.driver.swipe(x, start_y, x, end_y, duration)

    def swipe_left(self, duration: int = 800) -> None:
        """向左滑動"""
        size = self.driver.get_window_size()
        y = size["height"] // 2
        start_x = int(size["width"] * 0.8)
        end_x = int(size["width"] * 0.2)
        self.driver.swipe(start_x, y, end_x, y, duration)

    def swipe_right(self, duration: int = 800) -> None:
        """向右滑動"""
        size = self.driver.get_window_size()
        y = size["height"] // 2
        start_x = int(size["width"] * 0.2)
        end_x = int(size["width"] * 0.8)
        self.driver.swipe(start_x, y, end_x, y, duration)

    # ── 頁面狀態 ──

    def get_page_source(self) -> str:
        """取得頁面原始碼（debug 用）"""
        return self.driver.page_source

    def screenshot(self, name: str) -> str:
        """截圖並回傳檔案路徑"""
        return take_screenshot(self.driver, name)
