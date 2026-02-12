"""
core/plugin_manager.py 單元測試

驗證 Plugin 註冊/移除、列表、hook 覆寫偵測、錯誤處理。
"""

import pytest

from core.exceptions import PluginError
from core.plugin_manager import Plugin, PluginManager, _is_overridden


class DummyPlugin(Plugin):
    """測試用 Plugin"""
    name = "dummy"
    version = "1.0.0"
    description = "測試 Plugin"

    def __init__(self):
        super().__init__()
        self.registered = False
        self.unregistered = False

    def on_register(self):
        self.registered = True

    def on_unregister(self):
        self.unregistered = True

    def on_test_start(self, test_name: str):
        pass


class MinimalPlugin(Plugin):
    """不覆寫任何 hook 的最小 Plugin"""
    name = "minimal"


@pytest.fixture
def manager():
    """每個測試取得乾淨的 PluginManager"""
    return PluginManager()


@pytest.mark.unit
class TestPluginRegister:
    """Plugin 註冊/移除"""

    @pytest.mark.unit
    def test_register(self, manager):
        """註冊 Plugin"""
        p = DummyPlugin()
        manager.register(p)
        assert manager.get("dummy") is p

    @pytest.mark.unit
    def test_on_register_called(self, manager):
        """註冊時呼叫 on_register"""
        p = DummyPlugin()
        manager.register(p)
        assert p.registered is True

    @pytest.mark.unit
    def test_unregister(self, manager):
        """移除 Plugin"""
        p = DummyPlugin()
        manager.register(p)
        manager.unregister("dummy")
        assert manager.get("dummy") is None

    @pytest.mark.unit
    def test_on_unregister_called(self, manager):
        """移除時呼叫 on_unregister"""
        p = DummyPlugin()
        manager.register(p)
        manager.unregister("dummy")
        assert p.unregistered is True

    @pytest.mark.unit
    def test_register_non_plugin_raises(self, manager):
        """註冊非 Plugin 物件拋出 PluginError"""
        with pytest.raises(PluginError):
            manager.register("not a plugin")

    @pytest.mark.unit
    def test_register_replace_existing(self, manager):
        """重複註冊同名 Plugin 會替換"""
        p1 = DummyPlugin()
        p2 = DummyPlugin()
        manager.register(p1)
        manager.register(p2)
        assert manager.get("dummy") is p2
        assert p1.unregistered is True

    @pytest.mark.unit
    def test_unregister_nonexistent(self, manager):
        """移除不存在的 Plugin 不報錯"""
        manager.unregister("nonexistent")  # 不應拋出


@pytest.mark.unit
class TestPluginList:
    """Plugin 列表"""

    @pytest.mark.unit
    def test_list_empty(self, manager):
        """空的 manager 回傳空列表"""
        assert manager.list_plugins() == []

    @pytest.mark.unit
    def test_list_plugins(self, manager):
        """列出已註冊 Plugin 的資訊"""
        manager.register(DummyPlugin())
        plugins = manager.list_plugins()
        assert len(plugins) == 1
        assert plugins[0]["name"] == "dummy"
        assert plugins[0]["version"] == "1.0.0"
        assert plugins[0]["enabled"] is True


@pytest.mark.unit
class TestPluginOverrideDetection:
    """Hook 覆寫偵測"""

    @pytest.mark.unit
    def test_overridden_method(self):
        """偵測被覆寫的方法"""
        p = DummyPlugin()
        assert _is_overridden(p, "on_test_start") is True
        assert _is_overridden(p, "on_register") is True

    @pytest.mark.unit
    def test_not_overridden_method(self):
        """偵測未覆寫的方法"""
        p = MinimalPlugin()
        assert _is_overridden(p, "on_test_start") is False
        assert _is_overridden(p, "on_test_fail") is False
