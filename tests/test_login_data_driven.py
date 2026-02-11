"""
資料驅動登入測試（範例）

從 test_data/login_data.json 載入多組測試資料，
一個 JSON 項目 = 一個獨立測試案例。
"""

import pytest

from pages.login_page import LoginPage
from pages.home_page import HomePage
from utils.data_loader import load_json, get_test_ids

# 載入測試資料
LOGIN_DATA = load_json("login_data.json")
TEST_IDS = get_test_ids(LOGIN_DATA)


class TestLoginDataDriven:
    """資料驅動：登入功能測試"""

    @pytest.mark.parametrize("data", LOGIN_DATA, ids=TEST_IDS)
    def test_login(self, driver, data):
        login_page = LoginPage(driver)
        home_page = HomePage(driver)

        login_page.login(
            username=data["username"],
            password=data["password"],
        )

        if data["expected"] == "success":
            assert home_page.is_home_page_displayed(), \
                f"[{data['case_id']}] 預期登入成功但未到首頁"
        else:
            assert login_page.is_login_page_displayed(), \
                f"[{data['case_id']}] 預期登入失敗但離開了登入頁"
