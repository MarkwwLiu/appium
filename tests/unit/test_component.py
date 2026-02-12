"""
core/component.py 單元測試

驗證 Component 初始化、ComponentDescriptor lazy init。
不依賴真實 driver，使用 mock。
"""

from unittest.mock import MagicMock

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
