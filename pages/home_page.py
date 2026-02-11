"""
首頁 Page Object（範例）

示範如何建立第二個 Page Object，並從登入後導航到首頁。
請依照你的 App 實際 UI 修改 locator。
"""

from appium.webdriver.common.appiumby import AppiumBy

from core.base_page import BasePage


class HomePage(BasePage):
    """首頁"""

    # ── Locators ──
    WELCOME_TEXT = (AppiumBy.ID, "com.example.app:id/welcome_text")
    MENU_BUTTON = (AppiumBy.ACCESSIBILITY_ID, "menu")
    LOGOUT_BUTTON = (AppiumBy.ID, "com.example.app:id/btn_logout")
    PROFILE_BUTTON = (AppiumBy.ID, "com.example.app:id/btn_profile")

    # ── 頁面操作 ──

    def get_welcome_text(self) -> str:
        return self.get_text(self.WELCOME_TEXT)

    def open_menu(self) -> "HomePage":
        self.click(self.MENU_BUTTON)
        return self

    def tap_logout(self) -> None:
        self.open_menu()
        self.click(self.LOGOUT_BUTTON)

    def tap_profile(self) -> None:
        self.click(self.PROFILE_BUTTON)

    # ── 頁面驗證 ──

    def is_home_page_displayed(self) -> bool:
        return self.is_element_present(self.WELCOME_TEXT)
