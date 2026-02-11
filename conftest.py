"""
pytest 全域 fixtures

提供：
- driver fixture：每個測試自動建立/銷毀 Appium driver
- 失敗時自動截圖（含 Allure 報告附件）
- 命令列參數支援 (--platform, --env)
- Plugin 系統自動載入
- Event Bus 測試生命週期事件
- 各工具模組 fixtures
"""

import time
from pathlib import Path

import pytest

from core.driver_manager import DriverManager
from core.element_cache import element_cache
from core.plugin_manager import plugin_manager
from utils.logger import logger
from utils.screenshot import take_screenshot
from utils.allure_helper import attach_screenshot, attach_text

# 載入自訂報告 plugin
from utils import report_plugin  # noqa: F401


# ── 框架初始化 ──

def pytest_configure(config):
    """pytest 啟動時：自動掃描 plugins/ 目錄"""
    plugins_dir = Path(__file__).resolve().parent / "plugins"
    if plugins_dir.exists():
        loaded = plugin_manager.discover(plugins_dir)
        if loaded:
            logger.info(f"自動載入 {loaded} 個 plugin")


# ── 命令列參數 ──

def pytest_addoption(parser):
    """新增自訂命令列參數"""
    parser.addoption(
        "--platform",
        action="store",
        default="android",
        choices=["android", "ios"],
        help="測試平台: android 或 ios",
    )
    parser.addoption(
        "--env",
        action="store",
        default="dev",
        help="測試環境: dev / staging / prod",
    )


# ── Session / Environment ──

@pytest.fixture(scope="session")
def platform(request) -> str:
    """取得測試平台"""
    return request.config.getoption("--platform")


@pytest.fixture(scope="session")
def test_env(request) -> str:
    """取得測試環境並初始化 EnvManager"""
    env_name = request.config.getoption("--env")
    from core.env_manager import env
    env.switch(env_name)
    return env_name


# ── Driver ──

@pytest.fixture(scope="function")
def driver(platform):
    """
    每個測試函式自動建立並銷毀 driver。

    scope=function 確保每個測試獨立，互不影響。
    """
    logger.info(f"===== 建立 {platform} driver =====")
    drv = DriverManager.create_driver(platform)
    yield drv
    logger.info("===== 關閉 driver =====")
    DriverManager.quit_driver()


# ── 工具模組 Fixtures ──

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
    """WebView 切換 fixture"""
    from utils.webview_helper import WebViewHelper
    return WebViewHelper(driver)


@pytest.fixture
def a11y(driver):
    """無障礙測試 fixture"""
    from utils.accessibility_helper import AccessibilityHelper
    return AccessibilityHelper(driver)


@pytest.fixture
def biometric(driver):
    """生物辨識模擬 fixture"""
    from utils.biometric_helper import BiometricHelper
    return BiometricHelper(driver)


@pytest.fixture
def image_compare(driver):
    """視覺回歸測試 fixture"""
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


# ── 斷言工具 (不需 driver) ──

@pytest.fixture
def expect():
    """語意化斷言 fixture"""
    from core.assertions import expect as _expect
    return _expect


@pytest.fixture
def soft_assert():
    """Soft assert fixture"""
    from core.assertions import soft_assert as _soft_assert
    return _soft_assert


# ── 測試生命週期 Hook ──

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """測試結束時：截圖 + log + Plugin 通知"""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call":
        driver = item.funcargs.get("driver")
        test_name = item.name

        if report.passed:
            plugin_manager.emit_test_pass(test_name, report.duration)

        elif report.failed:
            logger.error(f"測試失敗: {test_name}")

            if driver:
                take_screenshot(driver, f"FAIL_{test_name}")
                attach_screenshot(driver, f"失敗截圖: {test_name}")
                attach_text(driver.page_source, "頁面結構 (XML)")
                # 通知 Plugin
                plugin_manager.emit_test_fail(
                    test_name, driver, Exception(str(report.longrepr))
                )

            # 儲存裝置 log
            collector = item.funcargs.get("log_collector")
            if collector:
                collector.save(f"FAIL_{test_name}")

        elif report.skipped:
            plugin_manager.emit_test_skip(test_name, str(report.longrepr))


def pytest_runtest_setup(item):
    """測試開始前通知"""
    plugin_manager.emit_test_start(item.name)
    element_cache.clear()  # 每個測試清空元素快取
