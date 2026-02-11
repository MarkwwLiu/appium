"""
自訂 Exception 體系

統一的錯誤處理階層，讓每種失敗都有明確的分類與訊息。
上層可以 catch 大類別 (如 AppiumFrameworkError)，
也可以精準 catch 子類別 (如 ElementNotFoundError)。

Exception 樹：
    AppiumFrameworkError
    ├── DriverError
    │   ├── DriverNotInitializedError
    │   └── DriverConnectionError
    ├── PageError
    │   ├── ElementNotFoundError
    │   ├── ElementNotClickableError
    │   ├── ElementNotVisibleError
    │   └── PageNotLoadedError
    ├── ConfigError
    │   ├── CapsFileNotFoundError
    │   └── InvalidConfigError
    ├── TestDataError
    │   └── DataFileNotFoundError
    └── PluginError
"""


class AppiumFrameworkError(Exception):
    """框架所有例外的基底，catch 這個就能攔截一切框架錯誤"""

    def __init__(self, message: str = "", context: dict | None = None):
        self.context = context or {}
        super().__init__(message)


# ── Driver 相關 ──

class DriverError(AppiumFrameworkError):
    """Driver 相關錯誤"""


class DriverNotInitializedError(DriverError):
    """Driver 尚未初始化就被使用"""

    def __init__(self, message: str = "Driver 尚未建立，請先呼叫 create_driver()"):
        super().__init__(message)


class DriverConnectionError(DriverError):
    """無法連接到 Appium Server"""

    def __init__(self, url: str = "", original: Exception | None = None):
        self.original = original
        msg = f"無法連接到 Appium Server: {url}"
        if original:
            msg += f" ({type(original).__name__}: {original})"
        super().__init__(msg, context={"url": url})


# ── Page / Element 相關 ──

class PageError(AppiumFrameworkError):
    """頁面操作相關錯誤"""


class ElementNotFoundError(PageError):
    """找不到指定元素"""

    def __init__(self, locator: tuple = (), timeout: int = 0):
        msg = f"找不到元素: {locator}"
        if timeout:
            msg += f" (等待 {timeout}s)"
        super().__init__(msg, context={"locator": locator, "timeout": timeout})


class ElementNotClickableError(PageError):
    """元素無法點擊"""

    def __init__(self, locator: tuple = ()):
        super().__init__(f"元素無法點擊: {locator}", context={"locator": locator})


class ElementNotVisibleError(PageError):
    """元素不可見"""

    def __init__(self, locator: tuple = ()):
        super().__init__(f"元素不可見: {locator}", context={"locator": locator})


class PageNotLoadedError(PageError):
    """頁面未載入完成"""

    def __init__(self, page_name: str = ""):
        super().__init__(
            f"頁面未載入: {page_name}" if page_name else "頁面未載入",
            context={"page_name": page_name},
        )


# ── Config 相關 ──

class ConfigError(AppiumFrameworkError):
    """設定相關錯誤"""


class CapsFileNotFoundError(ConfigError):
    """找不到 capabilities 設定檔"""

    def __init__(self, path: str = ""):
        super().__init__(
            f"找不到 capabilities 檔案: {path}",
            context={"path": path},
        )


class InvalidConfigError(ConfigError):
    """設定值無效"""

    def __init__(self, key: str = "", value: str = "", reason: str = ""):
        msg = f"設定值無效: {key}={value}"
        if reason:
            msg += f" ({reason})"
        super().__init__(msg, context={"key": key, "value": value})


# ── Test Data 相關 ──

class TestDataError(AppiumFrameworkError):
    """測試資料相關錯誤"""


class DataFileNotFoundError(TestDataError):
    """找不到測試資料檔案"""

    def __init__(self, path: str = ""):
        super().__init__(f"找不到測試資料: {path}", context={"path": path})


# ── Plugin 相關 ──

class PluginError(AppiumFrameworkError):
    """Plugin 載入或執行錯誤"""

    def __init__(self, plugin_name: str = "", message: str = ""):
        msg = f"Plugin 錯誤 [{plugin_name}]: {message}" if plugin_name else message
        super().__init__(msg, context={"plugin_name": plugin_name})
