"""
core/component.py 單元測試

驗證 Component 初始化、ComponentDescriptor lazy init。
不依賴真實 driver，使用 mock。
"""

from unittest.mock import MagicMock, patch

import pytest

from core.component import Component, ComponentDescriptor


class FakeComponent(Component):
    """測試用 Component"""
    BUTTON = ("id", "btn")


@pytest.mark.unit
class TestComponent:
    """Component 基本功能"""

    @pytest.mark.unit
    def test_init(self):
        """Component 初始化"""
        driver = MagicMock()
        comp = FakeComponent(driver, timeout=5)
        assert comp.driver is driver
        assert comp.timeout == 5
        assert comp.root_locator is None

    @pytest.mark.unit
    def test_init_with_root(self):
        """Component 帶 root_locator"""
        driver = MagicMock()
        comp = FakeComponent(driver, root_locator=("id", "container"))
        assert comp.root_locator == ("id", "container")

    @pytest.mark.unit
    def test_search_context_no_root(self):
        """無 root 時搜尋 context 是 driver"""
        driver = MagicMock()
        comp = FakeComponent(driver)
        assert comp._search_context() is driver

    @pytest.mark.unit
    def test_default_timeout(self):
        """預設 timeout 是 10"""
        driver = MagicMock()
        comp = FakeComponent(driver)
        assert comp.timeout == 10


@pytest.mark.unit
class TestComponentDescriptor:
    """ComponentDescriptor lazy init"""

    @pytest.mark.unit
    def test_lazy_init(self):
        """第一次存取時自動建立 Component 實例"""
        descriptor = ComponentDescriptor(FakeComponent)
        descriptor.__set_name__(None, "header")

        # 模擬 Page 物件
        page = MagicMock()
        page.driver = MagicMock()
        page.timeout = 15
        # 確保沒有事先設定
        del page._component_header

        instance = descriptor.__get__(page)
        assert isinstance(instance, FakeComponent)
        assert instance.driver is page.driver
        assert instance.timeout == 15

    @pytest.mark.unit
    def test_lazy_init_cached(self):
        """第二次存取返回同一實例"""
        descriptor = ComponentDescriptor(FakeComponent)
        descriptor.__set_name__(None, "nav")

        page = MagicMock()
        page.driver = MagicMock()
        page.timeout = 10
        del page._component_nav

        first = descriptor.__get__(page)
        second = descriptor.__get__(page)
        assert first is second

    @pytest.mark.unit
    def test_class_access_returns_descriptor(self):
        """從 class 層級存取回傳 descriptor 本身"""
        descriptor = ComponentDescriptor(FakeComponent)
        result = descriptor.__get__(None)
        assert result is descriptor

    @pytest.mark.unit
    def test_with_kwargs(self):
        """傳遞額外 kwargs"""
        root = ("id", "root")
        descriptor = ComponentDescriptor(FakeComponent, root_locator=root)
        descriptor.__set_name__(None, "footer")

        page = MagicMock()
        page.driver = MagicMock()
        page.timeout = 10
        del page._component_footer

        instance = descriptor.__get__(page)
        assert instance.root_locator == root


# ── 新增測試類別 ──


@pytest.mark.unit
class TestComponentRoot:
    """Component.root 屬性"""

    @pytest.mark.unit
    @patch("core.component.WebDriverWait")
    def test_root_with_root_locator_finds_element(self, MockWait):
        """有 root_locator → WebDriverWait 找到元素"""
        driver = MagicMock()
        mock_element = MagicMock()
        MockWait.return_value.until.return_value = mock_element

        comp = FakeComponent(driver, root_locator=("id", "container"))
        result = comp.root

        assert result is mock_element
        MockWait.assert_called_once_with(driver, 10)
        MockWait.return_value.until.assert_called_once()

    @pytest.mark.unit
    @patch("core.component.WebDriverWait")
    def test_root_with_root_locator_wait_raises(self, MockWait):
        """有 root_locator → WebDriverWait 拋例外 → _root_element 為 None"""
        driver = MagicMock()
        MockWait.return_value.until.side_effect = Exception("timeout")

        comp = FakeComponent(driver, root_locator=("id", "missing"))
        result = comp.root

        assert result is None
        assert comp._root_element is None

    @pytest.mark.unit
    def test_root_without_root_locator(self):
        """無 root_locator → 回傳 None"""
        driver = MagicMock()
        comp = FakeComponent(driver)
        result = comp.root

        assert result is None


@pytest.mark.unit
class TestComponentOperations:
    """Component 元素操作"""

    @pytest.mark.unit
    @patch("core.component.WebDriverWait")
    def test_find_element(self, MockWait):
        """find_element → 呼叫 WebDriverWait.until"""
        driver = MagicMock()
        comp = FakeComponent(driver, timeout=5)

        mock_element = MagicMock()
        MockWait.return_value.until.return_value = mock_element

        result = comp.find_element(("id", "btn"))
        assert result is mock_element
        MockWait.assert_called_once_with(driver, 5)
        MockWait.return_value.until.assert_called_once()

    @pytest.mark.unit
    @patch("core.component.WebDriverWait")
    def test_find_elements(self, MockWait):
        """find_elements → 先等第一個出現再呼叫 driver.find_elements"""
        driver = MagicMock()
        comp = FakeComponent(driver, timeout=5)

        mock_first = MagicMock()
        MockWait.return_value.until.return_value = mock_first

        mock_list = [MagicMock(), MagicMock()]
        driver.find_elements.return_value = mock_list

        result = comp.find_elements(("id", "items"))
        assert result is mock_list
        # 先呼叫 WebDriverWait.until（等第一個元素）
        MockWait.return_value.until.assert_called_once()
        # 再呼叫 driver.find_elements
        driver.find_elements.assert_called_once_with("id", "items")

    @pytest.mark.unit
    @patch("core.component.WebDriverWait")
    def test_click(self, MockWait):
        """click → WebDriverWait.until(clickable).click()"""
        driver = MagicMock()
        comp = FakeComponent(driver, timeout=5)

        mock_element = MagicMock()
        MockWait.return_value.until.return_value = mock_element

        comp.click(("id", "btn_ok"))
        MockWait.assert_called_once_with(driver, 5)
        MockWait.return_value.until.assert_called_once()
        mock_element.click.assert_called_once()

    @pytest.mark.unit
    @patch("core.component.WebDriverWait")
    def test_input_text(self, MockWait):
        """input_text → WebDriverWait.until(visible) → clear + send_keys"""
        driver = MagicMock()
        comp = FakeComponent(driver, timeout=5)

        mock_element = MagicMock()
        MockWait.return_value.until.return_value = mock_element

        comp.input_text(("id", "input_name"), "Hello World")
        MockWait.assert_called_once_with(driver, 5)
        MockWait.return_value.until.assert_called_once()
        mock_element.clear.assert_called_once()
        mock_element.send_keys.assert_called_once_with("Hello World")

    @pytest.mark.unit
    @patch("core.component.WebDriverWait")
    def test_get_text(self, MockWait):
        """get_text → find_element.text"""
        driver = MagicMock()
        comp = FakeComponent(driver, timeout=5)

        mock_element = MagicMock()
        mock_element.text = "Some Text"
        MockWait.return_value.until.return_value = mock_element

        result = comp.get_text(("id", "tv_label"))
        assert result == "Some Text"

    @pytest.mark.unit
    @patch("core.component.WebDriverWait")
    def test_is_displayed_true(self, MockWait):
        """is_displayed → 元素找到 → True"""
        driver = MagicMock()
        comp = FakeComponent(driver)

        mock_element = MagicMock()
        MockWait.return_value.until.return_value = mock_element

        result = comp.is_displayed(("id", "visible_btn"), timeout=3)
        assert result is True

    @pytest.mark.unit
    @patch("core.component.WebDriverWait")
    def test_is_displayed_false_on_exception(self, MockWait):
        """is_displayed → 拋例外 → False"""
        driver = MagicMock()
        comp = FakeComponent(driver)

        MockWait.return_value.until.side_effect = Exception("timeout")

        result = comp.is_displayed(("id", "hidden_btn"), timeout=3)
        assert result is False
