"""
core/env_manager.py 單元測試

驗證 EnvManager 的設定合併、dot notation、環境變數覆蓋、型別轉換。
"""

import json
import os

import pytest

from core.env_manager import EnvManager, _deep_merge


@pytest.mark.unit
class TestDeepMerge:
    """深層合併"""

    @pytest.mark.unit
    def test_flat_merge(self):
        """平面 dict 合併"""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    @pytest.mark.unit
    def test_nested_merge(self):
        """巢狀 dict 深層合併"""
        base = {"x": {"a": 1, "b": 2}}
        override = {"x": {"b": 99, "c": 3}}
        result = _deep_merge(base, override)
        assert result == {"x": {"a": 1, "b": 99, "c": 3}}

    @pytest.mark.unit
    def test_override_replaces_non_dict(self):
        """非 dict 值直接覆蓋"""
        base = {"x": [1, 2]}
        override = {"x": [3]}
        result = _deep_merge(base, override)
        assert result == {"x": [3]}

    @pytest.mark.unit
    def test_does_not_mutate_base(self):
        """不改變原始 base dict"""
        base = {"a": {"b": 1}}
        override = {"a": {"b": 2}}
        _deep_merge(base, override)
        assert base["a"]["b"] == 1


@pytest.mark.unit
class TestEnvManagerDefaults:
    """預設值"""

    @pytest.mark.unit
    def test_default_values(self):
        """未載入任何檔案時使用內建預設值"""
        mgr = EnvManager()
        mgr._config = {}
        mgr._loaded = True
        # get 走 dot notation，預設值沒有則回 default
        assert mgr.get("nonexistent", "fallback") == "fallback"

    @pytest.mark.unit
    def test_get_with_default(self):
        """key 不存在時回傳 default"""
        mgr = EnvManager()
        mgr._config = {"a": 1}
        mgr._loaded = True
        assert mgr.get("b", 42) == 42


@pytest.mark.unit
class TestEnvManagerDotNotation:
    """Dot notation"""

    @pytest.mark.unit
    def test_flat_key(self):
        """單層 key"""
        mgr = EnvManager()
        mgr._config = {"appium_server": "http://localhost"}
        mgr._loaded = True
        assert mgr.get("appium_server") == "http://localhost"

    @pytest.mark.unit
    def test_nested_key(self):
        """巢狀 key"""
        mgr = EnvManager()
        mgr._config = {"capabilities": {"android": {"device": "emulator"}}}
        mgr._loaded = True
        assert mgr.get("capabilities.android.device") == "emulator"

    @pytest.mark.unit
    def test_nested_key_missing(self):
        """巢狀 key 中間不存在"""
        mgr = EnvManager()
        mgr._config = {"capabilities": {}}
        mgr._loaded = True
        assert mgr.get("capabilities.android.device", "default") == "default"


@pytest.mark.unit
class TestEnvManagerSet:
    """動態設定"""

    @pytest.mark.unit
    def test_set_flat(self):
        """設定單層值"""
        mgr = EnvManager()
        mgr._config = {}
        mgr._loaded = True
        mgr.set("key", "value")
        assert mgr.get("key") == "value"

    @pytest.mark.unit
    def test_set_nested(self):
        """設定巢狀值"""
        mgr = EnvManager()
        mgr._config = {}
        mgr._loaded = True
        mgr.set("a.b.c", 123)
        assert mgr.get("a.b.c") == 123


@pytest.mark.unit
class TestEnvManagerCast:
    """型別轉換"""

    @pytest.mark.unit
    def test_cast_true(self):
        """字串 true → bool True"""
        assert EnvManager._cast("true") is True
        assert EnvManager._cast("1") is True
        assert EnvManager._cast("yes") is True

    @pytest.mark.unit
    def test_cast_false(self):
        """字串 false → bool False"""
        assert EnvManager._cast("false") is False
        assert EnvManager._cast("0") is False

    @pytest.mark.unit
    def test_cast_int(self):
        """數字字串 → int"""
        assert EnvManager._cast("42") == 42

    @pytest.mark.unit
    def test_cast_float(self):
        """浮點字串 → float"""
        assert EnvManager._cast("3.14") == 3.14

    @pytest.mark.unit
    def test_cast_string(self):
        """一般字串不轉換"""
        assert EnvManager._cast("hello") == "hello"


@pytest.mark.unit
class TestEnvManagerSwitch:
    """環境切換"""

    @pytest.mark.unit
    def test_switch_reloads(self):
        """切換環境後重新載入"""
        mgr = EnvManager()
        mgr._loaded = True
        mgr.switch("staging")
        assert mgr.env_name == "staging"

    @pytest.mark.unit
    def test_env_override(self, monkeypatch):
        """環境變數覆蓋設定值"""
        mgr = EnvManager()
        mgr._config = {"platform": "android"}
        mgr._loaded = True
        monkeypatch.setenv("PLATFORM", "ios")
        assert mgr.get("platform") == "ios"
