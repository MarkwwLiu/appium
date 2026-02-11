"""
Plugin 系統 — 可插拔擴充不改核心

讓使用者自訂功能（截圖策略、通知管道、自訂報告...），
只要實作 Plugin 介面，放進 plugins/ 目錄或手動註冊即可生效。

用法：
    1. 繼承 Plugin 基底類別
    2. 實作需要的 hook method
    3. 註冊到 plugin_manager

範例：
    class MyPlugin(Plugin):
        name = "my_plugin"

        def on_test_fail(self, test_name, driver, error):
            # 失敗時做什麼事
            ...

    plugin_manager.register(MyPlugin())

也可以用自動掃描：
    plugin_manager.discover("plugins/")
"""

from __future__ import annotations

import importlib
import inspect
import sys
from abc import ABC
from pathlib import Path
from typing import Any

from core.event_bus import event_bus
from core.exceptions import PluginError
from utils.logger import logger


class Plugin(ABC):
    """
    Plugin 基底類別

    所有 hook method 都是可選的，覆寫你需要的即可。
    不必全部實作。
    """

    name: str = "unnamed_plugin"
    version: str = "1.0.0"
    description: str = ""
    enabled: bool = True

    # ── Lifecycle hooks ──

    def on_register(self) -> None:
        """Plugin 被註冊時呼叫（初始化）"""

    def on_unregister(self) -> None:
        """Plugin 被移除時呼叫（清理）"""

    # ── Driver hooks ──

    def on_driver_created(self, driver) -> None:
        """Driver 建立後"""

    def on_driver_quit(self, driver) -> None:
        """Driver 關閉前"""

    # ── Page hooks ──

    def on_before_action(self, page, action: str, locator: tuple, **kwargs) -> None:
        """Page 操作前 (click, input_text, ...)"""

    def on_after_action(self, page, action: str, locator: tuple, **kwargs) -> None:
        """Page 操作後"""

    def on_action_error(self, page, action: str, locator: tuple,
                        error: Exception) -> None:
        """Page 操作出錯"""

    # ── Test hooks ──

    def on_test_start(self, test_name: str) -> None:
        """測試開始"""

    def on_test_pass(self, test_name: str, duration: float) -> None:
        """測試通過"""

    def on_test_fail(self, test_name: str, driver, error: Exception) -> None:
        """測試失敗"""

    def on_test_skip(self, test_name: str, reason: str) -> None:
        """測試跳過"""

    # ── Screenshot hooks ──

    def on_screenshot(self, path: str, test_name: str) -> None:
        """截圖完成"""


class PluginManager:
    """Plugin 管理器"""

    def __init__(self):
        self._plugins: dict[str, Plugin] = {}

    def register(self, plugin: Plugin) -> None:
        """註冊 Plugin"""
        if not isinstance(plugin, Plugin):
            raise PluginError(
                plugin_name=getattr(plugin, "name", str(type(plugin))),
                message="必須繼承 Plugin 基底類別",
            )

        name = plugin.name
        if name in self._plugins:
            logger.warning(f"Plugin '{name}' 已存在，將被替換")
            self.unregister(name)

        self._plugins[name] = plugin
        self._bind_events(plugin)
        plugin.on_register()
        logger.info(f"Plugin 已註冊: {name} v{plugin.version}")

    def unregister(self, name: str) -> None:
        """移除 Plugin"""
        plugin = self._plugins.pop(name, None)
        if plugin:
            plugin.on_unregister()
            logger.info(f"Plugin 已移除: {name}")

    def get(self, name: str) -> Plugin | None:
        """取得 Plugin 實例"""
        return self._plugins.get(name)

    def list_plugins(self) -> list[dict]:
        """列出所有已註冊的 Plugin"""
        return [
            {
                "name": p.name,
                "version": p.version,
                "description": p.description,
                "enabled": p.enabled,
            }
            for p in self._plugins.values()
        ]

    def discover(self, directory: str | Path) -> int:
        """
        自動掃描目錄下的 Plugin 檔案並註冊。

        檔案命名規則：*_plugin.py
        檔案中需有繼承 Plugin 的 class。

        Returns:
            成功載入的 Plugin 數量
        """
        directory = Path(directory)
        if not directory.exists():
            logger.warning(f"Plugin 目錄不存在: {directory}")
            return 0

        loaded = 0
        for py_file in directory.glob("*_plugin.py"):
            try:
                module_name = py_file.stem
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

                # 找出所有 Plugin 子類別
                for _, cls in inspect.getmembers(module, inspect.isclass):
                    if issubclass(cls, Plugin) and cls is not Plugin:
                        instance = cls()
                        self.register(instance)
                        loaded += 1
            except Exception as e:
                logger.error(f"載入 Plugin 失敗 [{py_file.name}]: {e}")

        logger.info(f"Plugin 自動掃描完成: {loaded} 個已載入")
        return loaded

    def _bind_events(self, plugin: Plugin) -> None:
        """將 Plugin 的 hook method 綁定到 event_bus"""
        hook_map = {
            "on_driver_created": "driver.created",
            "on_driver_quit": "driver.quit",
            "on_before_action": "page.action.before",
            "on_after_action": "page.action.after",
            "on_action_error": "page.action.error",
            "on_test_start": "test.start",
            "on_test_pass": "test.pass",
            "on_test_fail": "test.fail",
            "on_test_skip": "test.skip",
            "on_screenshot": "screenshot.taken",
        }

        for method_name, event_name in hook_map.items():
            method = getattr(plugin, method_name, None)
            if method and _is_overridden(plugin, method_name):
                def _make_handler(m):
                    def handler(event):
                        if plugin.enabled:
                            m(**event.data)
                    return handler
                event_bus.on(event_name, _make_handler(method))

    # ── 便捷的 emit 方法 ──

    def emit_driver_created(self, driver) -> None:
        event_bus.emit("driver.created", {"driver": driver}, source="driver_manager")

    def emit_driver_quit(self, driver) -> None:
        event_bus.emit("driver.quit", {"driver": driver}, source="driver_manager")

    def emit_before_action(self, page, action: str, locator: tuple,
                           **kwargs) -> None:
        event_bus.emit("page.action.before", {
            "page": page, "action": action, "locator": locator, **kwargs,
        }, source="base_page")

    def emit_after_action(self, page, action: str, locator: tuple,
                          **kwargs) -> None:
        event_bus.emit("page.action.after", {
            "page": page, "action": action, "locator": locator, **kwargs,
        }, source="base_page")

    def emit_action_error(self, page, action: str, locator: tuple,
                          error: Exception) -> None:
        event_bus.emit("page.action.error", {
            "page": page, "action": action, "locator": locator, "error": error,
        }, source="base_page")

    def emit_test_start(self, test_name: str) -> None:
        event_bus.emit("test.start", {"test_name": test_name}, source="conftest")

    def emit_test_pass(self, test_name: str, duration: float) -> None:
        event_bus.emit("test.pass", {
            "test_name": test_name, "duration": duration,
        }, source="conftest")

    def emit_test_fail(self, test_name: str, driver, error: Exception) -> None:
        event_bus.emit("test.fail", {
            "test_name": test_name, "driver": driver, "error": error,
        }, source="conftest")

    def emit_test_skip(self, test_name: str, reason: str) -> None:
        event_bus.emit("test.skip", {
            "test_name": test_name, "reason": reason,
        }, source="conftest")

    def emit_screenshot(self, path: str, test_name: str) -> None:
        event_bus.emit("screenshot.taken", {
            "path": path, "test_name": test_name,
        }, source="screenshot")


def _is_overridden(instance: Plugin, method_name: str) -> bool:
    """判斷 Plugin 子類別是否覆寫了某方法"""
    base_method = getattr(Plugin, method_name, None)
    instance_method = getattr(type(instance), method_name, None)
    return instance_method is not base_method


# 全域 singleton
plugin_manager = PluginManager()
