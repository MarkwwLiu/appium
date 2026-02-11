"""
首頁功能測試（範例）

示範登入後對首頁進行測試。
"""

import pytest

from pages.login_page import LoginPage
from pages.home_page import HomePage


class TestHome:
    """首頁相關測試"""

    @pytest.fixture(autouse=True)
    def setup_login(self, driver):
        """每個測試前先登入"""
        login_page = LoginPage(driver)
        login_page.login(username="testuser", password="password123")
        yield

    def test_welcome_message(self, driver):
        """測試：登入後顯示歡迎訊息"""
        home_page = HomePage(driver)

        welcome = home_page.get_welcome_text()
        assert "testuser" in welcome.lower() or "歡迎" in welcome

    def test_logout(self, driver):
        """測試：可以成功登出"""
        home_page = HomePage(driver)
        login_page = LoginPage(driver)

        home_page.tap_logout()

        # 驗證回到登入頁面
        assert login_page.is_login_page_displayed()
