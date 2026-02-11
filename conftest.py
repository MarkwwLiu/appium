"""
pytest 全域 fixtures

提供：
- driver fixture：每個測試自動建立/銷毀 Appium driver
- 失敗時自動截圖（含 Allure 報告附件）
- 命令列參數支援 (--platform)
- 各工具模組 fixtures
- 失敗時自動收集裝置 log
"""

import pytest

from core.driver_manager import DriverManager
from utils.logger import logger
from utils.screenshot import take_screenshot
from utils.allure_helper import attach_screenshot, attach_text

# 載入自訂報告 plugin
from utils import report_plugin  # noqa: F401


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


@pytest.fixture
def api_client():
    """API client fixture：API + UI 混合測試"""
    from utils.api_client import ApiClient
    import os

    base_url = os.getenv("API_BASE_URL", "http://localhost:8080")
    client = ApiClient(base_url)
    yield client


@pytest.fixture
def element_helper(driver):
    """元素探索工具 fixture"""
    from utils.element_helper import ElementHelper
    return ElementHelper(driver)


@pytest.fixture
def gesture(driver):
    """手勢操作 fixture：長按、雙擊、拖放、縮放"""
    from utils.gesture_helper import GestureHelper
    return GestureHelper(driver)


@pytest.fixture
def app_manager(driver):
    """App 生命週期 fixture：安裝/移除/重啟/前背景/deep link"""
    from utils.app_manager import AppManager
    return AppManager(driver)


@pytest.fixture
def device(driver):
    """裝置控制 fixture：旋轉、鍵盤、網路、系統鍵"""
    from utils.device_helper import DeviceHelper
    return DeviceHelper(driver)


@pytest.fixture
def webview(driver):
    """WebView 切換 fixture：Native / WebView context 切換"""
    from utils.webview_helper import WebViewHelper
    return WebViewHelper(driver)


@pytest.fixture
def a11y(driver):
    """無障礙測試 fixture：content-description、觸控區域檢查"""
    from utils.accessibility_helper import AccessibilityHelper
    return AccessibilityHelper(driver)


@pytest.fixture
def biometric(driver):
    """生物辨識模擬 fixture：Touch ID / Face ID / 指紋"""
    from utils.biometric_helper import BiometricHelper
    return BiometricHelper(driver)


@pytest.fixture
def image_compare(driver):
    """視覺回歸測試 fixture：截圖比對"""
    from utils.image_compare import ImageCompare
    return ImageCompare(driver)


@pytest.fixture
def log_collector(platform):
    """裝置 log 收集 fixture：自動啟停"""
    from utils.log_collector import LogCollector
    collector = LogCollector(platform=platform)
    collector.start()
    yield collector
    collector.stop()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """測試失敗時自動截圖 + 收集裝置 log"""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        driver = item.funcargs.get("driver")
        if driver:
            test_name = item.name
            logger.error(f"測試失敗: {test_name}")
            take_screenshot(driver, f"FAIL_{test_name}")
            attach_screenshot(driver, f"失敗截圖: {test_name}")
            attach_text(driver.page_source, "頁面結構 (XML)")

        # 儲存裝置 log
        collector = item.funcargs.get("log_collector")
        if collector:
            collector.save(f"FAIL_{item.name}")
