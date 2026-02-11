"""
使用自訂 decorators 的測試範例

示範 @android_only, @retry_on_failure, @timer 的用法。
"""

import pytest

from pages.login_page import LoginPage
from pages.home_page import HomePage
from utils.decorators import android_only, ios_only, retry_on_failure, timer
from utils.data_factory import DataFactory


class TestWithDecorators:
    """示範 decorators 用法"""

    @android_only
    def test_android_back_button(self, driver):
        """僅 Android：測試實體返回鍵"""
        driver.back()

    @ios_only
    def test_ios_swipe_back(self, driver):
        """僅 iOS：測試滑動返回"""
        size = driver.get_window_size()
        driver.swipe(0, size["height"] // 2, size["width"], size["height"] // 2)

    @retry_on_failure(max_retries=3, delay=1.0)
    def test_flaky_feature(self, driver):
        """不穩定功能：自動重試最多 3 次"""
        home_page = HomePage(driver)
        assert home_page.is_home_page_displayed()

    @timer
    def test_login_performance(self, driver):
        """計時：量測登入流程耗時"""
        login_page = LoginPage(driver)
        login_page.login(
            username=DataFactory.random_username(),
            password=DataFactory.random_password(),
        )
