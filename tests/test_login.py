"""
登入功能測試（範例）

示範如何使用 Page Object + pytest 撰寫測試。
"""

import pytest

from pages.login_page import LoginPage
from pages.home_page import HomePage


class TestLogin:
    """登入相關測試"""

    def test_login_success(self, driver):
        """測試：正確帳密可以成功登入"""
        login_page = LoginPage(driver)
        home_page = HomePage(driver)

        # 驗證在登入頁面
        assert login_page.is_login_page_displayed()

        # 執行登入
        login_page.login(username="testuser", password="password123")

        # 驗證成功導航到首頁
        assert home_page.is_home_page_displayed()

    def test_login_wrong_password(self, driver):
        """測試：錯誤密碼會顯示錯誤訊息"""
        login_page = LoginPage(driver)

        login_page.login(username="testuser", password="wrong_password")

        error = login_page.get_error_message()
        assert "密碼錯誤" in error or "incorrect" in error.lower()

    def test_login_empty_fields(self, driver):
        """測試：空白欄位不能登入"""
        login_page = LoginPage(driver)

        login_page.tap_login()

        # 應該仍停留在登入頁面
        assert login_page.is_login_page_displayed()
