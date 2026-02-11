"""
登入頁面 Page Object（範例）

示範如何使用 BasePage 建立一個 Page Object。
請依照你的 App 實際 UI 修改 locator。
"""

from appium.webdriver.common.appiumby import AppiumBy

from core.base_page import BasePage


class LoginPage(BasePage):
    """登入頁面"""

    # ── Locators ──
    # 請依照實際 App 的元素 ID / XPath 修改
    USERNAME_INPUT = (AppiumBy.ID, "com.example.app:id/username")
    PASSWORD_INPUT = (AppiumBy.ID, "com.example.app:id/password")
    LOGIN_BUTTON = (AppiumBy.ID, "com.example.app:id/btn_login")
    ERROR_MESSAGE = (AppiumBy.ID, "com.example.app:id/error_message")

    # ── 頁面操作 ──

    def enter_username(self, username: str) -> "LoginPage":
        self.input_text(self.USERNAME_INPUT, username)
        return self

    def enter_password(self, password: str) -> "LoginPage":
        self.input_text(self.PASSWORD_INPUT, password)
        return self

    def tap_login(self) -> None:
        self.click(self.LOGIN_BUTTON)

    def login(self, username: str, password: str) -> None:
        """完整的登入流程"""
        self.enter_username(username)
        self.enter_password(password)
        self.tap_login()

    # ── 頁面驗證 ──

    def get_error_message(self) -> str:
        return self.get_text(self.ERROR_MESSAGE)

    def is_login_page_displayed(self) -> bool:
        return self.is_element_present(self.LOGIN_BUTTON)
