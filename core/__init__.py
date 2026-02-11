"""
core — 框架核心

統一匯出所有核心元件，方便外部 import。

用法：
    from core import BasePage, Component, expect, soft_assert
    from core import event_bus, plugin_manager, middleware_chain
    from core import env
    from core import ElementNotFoundError, PageNotLoadedError
"""

from core.assertions import expect, soft_assert
from core.base_page import BasePage
from core.component import Component, ComponentDescriptor
from core.driver_manager import DriverManager
from core.element_cache import element_cache
from core.env_manager import env
from core.event_bus import event_bus
from core.exceptions import (
    AppiumFrameworkError,
    CapsFileNotFoundError,
    ConfigError,
    DataFileNotFoundError,
    DriverConnectionError,
    DriverError,
    DriverNotInitializedError,
    ElementNotClickableError,
    ElementNotFoundError,
    ElementNotVisibleError,
    InvalidConfigError,
    PageError,
    PageNotLoadedError,
    PluginError,
    TestDataError,
)
from core.middleware import MiddlewareContext, middleware_chain
from core.plugin_manager import Plugin, plugin_manager

__all__ = [
    # Driver / Page / Component
    "DriverManager",
    "BasePage",
    "Component",
    "ComponentDescriptor",
    # Assertions
    "expect",
    "soft_assert",
    # Infrastructure
    "event_bus",
    "plugin_manager",
    "Plugin",
    "middleware_chain",
    "MiddlewareContext",
    "element_cache",
    "env",
    # Exceptions
    "AppiumFrameworkError",
    "DriverError",
    "DriverNotInitializedError",
    "DriverConnectionError",
    "PageError",
    "ElementNotFoundError",
    "ElementNotClickableError",
    "ElementNotVisibleError",
    "PageNotLoadedError",
    "ConfigError",
    "CapsFileNotFoundError",
    "InvalidConfigError",
    "TestDataError",
    "DataFileNotFoundError",
    "PluginError",
]
