"""
Allure 報告整合輔助
封裝 Allure 常用的步驟標記與附件功能。
如未安裝 allure-pytest，所有方法會 graceful fallback，不影響測試執行。
"""

import functools
from pathlib import Path

from utils.logger import logger

try:
    import allure
    ALLURE_AVAILABLE = True
except ImportError:
    ALLURE_AVAILABLE = False
    logger.debug("allure-pytest 未安裝，Allure 報告功能停用")


def allure_step(title: str):
    """
    裝飾器：將函式標記為 Allure step。
    未安裝 allure 時直接執行原函式。

    用法：
        @allure_step("輸入帳號密碼並登入")
        def login(self, user, pwd): ...
    """
    def decorator(func):
        if ALLURE_AVAILABLE:
            @allure.step(title)
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return func
    return decorator


def attach_screenshot(driver, name: str = "截圖") -> None:
    """將截圖附加到 Allure 報告"""
    if ALLURE_AVAILABLE:
        png = driver.get_screenshot_as_png()
        allure.attach(png, name=name, attachment_type=allure.attachment_type.PNG)


def attach_text(text: str, name: str = "log") -> None:
    """將文字附加到 Allure 報告"""
    if ALLURE_AVAILABLE:
        allure.attach(text, name=name, attachment_type=allure.attachment_type.TEXT)


def attach_file(filepath: str, name: str | None = None) -> None:
    """將檔案附加到 Allure 報告"""
    if ALLURE_AVAILABLE:
        path = Path(filepath)
        allure.attach.file(str(path), name=name or path.name)
