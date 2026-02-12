"""
utils.element_helper 單元測試
驗證 ElementHelper 的頁面匯出、文字搜尋、content-desc 搜尋、可點擊元素搜尋、resource-id 提取。
"""

import pytest
from unittest.mock import MagicMock, patch, mock_open, call

from utils.element_helper import ElementHelper


@pytest.mark.unit
class TestDumpPage:
    """dump_page 方法"""

    @pytest.mark.unit
    def test_returns_page_source(self):
        """回傳 driver 的 page_source"""
        driver = MagicMock()
        driver.page_source = "<hierarchy><node text='Hello'/></hierarchy>"
        helper = ElementHelper(driver)

        result = helper.dump_page()

        assert result == "<hierarchy><node text='Hello'/></hierarchy>"

    @pytest.mark.unit
    def test_saves_to_file_when_save_to_provided(self, tmp_path):
        """指定 save_to 時儲存到檔案"""
        driver = MagicMock()
        driver.page_source = "<hierarchy><node text='Test'/></hierarchy>"
        helper = ElementHelper(driver)
        filepath = str(tmp_path / "page.xml")

        result = helper.dump_page(save_to=filepath)

        assert result == driver.page_source
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        assert content == driver.page_source

    @pytest.mark.unit
    def test_does_not_save_when_save_to_is_none(self):
        """未指定 save_to 時不寫入檔案"""
        driver = MagicMock()
        driver.page_source = "<hierarchy/>"
        helper = ElementHelper(driver)

        with patch("builtins.open", mock_open()) as mocked_file:
            helper.dump_page(save_to=None)
            mocked_file.assert_not_called()


@pytest.mark.unit
class TestFindByText:
    """find_by_text 方法"""

    @pytest.mark.unit
    def test_exact_match(self):
        """精確比對文字"""
        driver = MagicMock()
        mock_element = MagicMock()
        driver.find_elements.return_value = [mock_element]
        helper = ElementHelper(driver)

        result = helper.find_by_text("Login")

        driver.find_elements.assert_called_once()
        call_args = driver.find_elements.call_args
        xpath_used = call_args[0][1]
        assert '@text="Login"' in xpath_used
        assert "contains" not in xpath_used
        assert result == [mock_element]

    @pytest.mark.unit
    def test_partial_match(self):
        """模糊比對文字"""
        driver = MagicMock()
        mock_elements = [MagicMock(), MagicMock()]
        driver.find_elements.return_value = mock_elements
        helper = ElementHelper(driver)

        result = helper.find_by_text("Log", partial=True)

        call_args = driver.find_elements.call_args
        xpath_used = call_args[0][1]
        assert "contains(@text" in xpath_used
        assert result == mock_elements

    @pytest.mark.unit
    def test_no_elements_found(self):
        """找不到元素時回傳空列表"""
        driver = MagicMock()
        driver.find_elements.return_value = []
        helper = ElementHelper(driver)

        result = helper.find_by_text("NonExistent")

        assert result == []


@pytest.mark.unit
class TestFindByContentDesc:
    """find_by_content_desc 方法"""

    @pytest.mark.unit
    def test_find_by_content_desc(self):
        """依照 accessibility id 搜尋元素"""
        driver = MagicMock()
        mock_element = MagicMock()
        driver.find_elements.return_value = [mock_element]
        helper = ElementHelper(driver)

        result = helper.find_by_content_desc("menu_button")

        driver.find_elements.assert_called_once()
        call_args = driver.find_elements.call_args
        assert call_args[0][1] == "menu_button"
        assert result == [mock_element]

    @pytest.mark.unit
    def test_find_by_content_desc_no_result(self):
        """找不到符合 content-desc 的元素"""
        driver = MagicMock()
        driver.find_elements.return_value = []
        helper = ElementHelper(driver)

        result = helper.find_by_content_desc("nonexistent")

        assert result == []


@pytest.mark.unit
class TestFindClickableElements:
    """find_clickable_elements 方法"""

    @pytest.mark.unit
    def test_find_clickable_elements(self):
        """找到可點擊元素"""
        driver = MagicMock()
        el1 = MagicMock()
        el1.get_attribute.side_effect = lambda attr: {
            "className": "android.widget.Button",
            "text": "Submit",
            "resourceId": "com.app:id/btn_submit",
        }.get(attr, "")
        el2 = MagicMock()
        el2.get_attribute.side_effect = lambda attr: {
            "className": "android.widget.ImageButton",
            "text": "",
            "resourceId": "com.app:id/btn_back",
        }.get(attr, "")
        driver.find_elements.return_value = [el1, el2]
        helper = ElementHelper(driver)

        result = helper.find_clickable_elements()

        assert len(result) == 2
        call_args = driver.find_elements.call_args
        xpath_used = call_args[0][1]
        assert '@clickable="true"' in xpath_used

    @pytest.mark.unit
    def test_find_clickable_elements_empty(self):
        """頁面上沒有可點擊元素"""
        driver = MagicMock()
        driver.find_elements.return_value = []
        helper = ElementHelper(driver)

        result = helper.find_clickable_elements()

        assert result == []


@pytest.mark.unit
class TestFindAllIds:
    """find_all_ids 方法"""

    @pytest.mark.unit
    def test_extracts_unique_resource_ids(self):
        """提取唯一的 resource-id 並排序"""
        driver = MagicMock()
        driver.page_source = (
            '<hierarchy>'
            '<node resource-id="com.app:id/btn_login" />'
            '<node resource-id="com.app:id/txt_username" />'
            '<node resource-id="com.app:id/btn_login" />'
            '<node resource-id="com.app:id/txt_password" />'
            '</hierarchy>'
        )
        helper = ElementHelper(driver)

        result = helper.find_all_ids()

        assert result == [
            "com.app:id/btn_login",
            "com.app:id/txt_password",
            "com.app:id/txt_username",
        ]

    @pytest.mark.unit
    def test_returns_sorted_list(self):
        """回傳排序後的列表"""
        driver = MagicMock()
        driver.page_source = (
            '<node resource-id="z_id" />'
            '<node resource-id="a_id" />'
            '<node resource-id="m_id" />'
        )
        helper = ElementHelper(driver)

        result = helper.find_all_ids()

        assert result == ["a_id", "m_id", "z_id"]

    @pytest.mark.unit
    def test_no_resource_ids(self):
        """頁面無 resource-id 時回傳空列表"""
        driver = MagicMock()
        driver.page_source = "<hierarchy><node text='Hello' /></hierarchy>"
        helper = ElementHelper(driver)

        result = helper.find_all_ids()

        assert result == []
