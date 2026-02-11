"""
pytest 全域 fixtures

提供：
- driver fixture：每個測試自動建立/銷毀 Appium driver
- 失敗時自動截圖
- 命令列參數支援 (--platform)
"""

import pytest

from core.driver_manager import DriverManager
from utils.logger import logger
from utils.screenshot import take_screenshot


def pytest_addoption(parser):
    """新增自訂命令列參數"""
    parser.addoption(
        "--platform",
        action="store",
        default="android",
        choices=["android", "ios"],
        help="測試平台: android 或 ios",
    )


@pytest.fixture(scope="session")
def platform(request) -> str:
    """取得測試平台"""
    return request.config.getoption("--platform")


@pytest.fixture(scope="function")
def driver(platform):
    """
    每個測試函式自動建立並銷毀 driver。

    scope=function 確保每個測試獨立，互不影響。
    如果需要共享 driver（加速），可改為 scope=class 或 scope=session。
    """
    logger.info(f"===== 建立 {platform} driver =====")
    drv = DriverManager.create_driver(platform)
    yield drv
    logger.info("===== 關閉 driver =====")
    DriverManager.quit_driver()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """測試失敗時自動截圖"""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        driver = item.funcargs.get("driver")
        if driver:
            test_name = item.name
            logger.error(f"測試失敗: {test_name}")
            take_screenshot(driver, f"FAIL_{test_name}")
