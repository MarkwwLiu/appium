"""
Test Writer
根據 PageSpec 產生 pytest 測試檔案（含 parametrize、分類 marker）。
同時產生 conftest.py。
"""

from pathlib import Path

from generator.schema import AppSpec, PageSpec, Platform


class TestWriter:
    """產生測試 .py 檔案"""

    def __init__(self, spec: AppSpec, output_dir: Path):
        self.spec = spec
        self.output = output_dir
        self.tests_dir = output_dir / "tests"
        self.tests_dir.mkdir(parents=True, exist_ok=True)
        # __init__.py
        init = self.tests_dir / "__init__.py"
        if not init.exists():
            init.write_text("", encoding="utf-8")

    def write_conftest(self) -> Path:
        """產生 conftest.py (driver fixture + 失敗截圖)"""
        platform = self.spec.platform.value
        server = self.spec.appium_server

        code = f'''\
"""
pytest fixtures — 自動產生
"""

import pytest
from appium import webdriver
from appium.options.android import UiAutomator2Options

from config.config import load_caps, SCREENSHOT_DIR


@pytest.fixture(scope="function")
def driver():
    """建立 Appium driver"""
    caps = load_caps("{platform}")
    options = UiAutomator2Options().load_capabilities(caps)
    drv = webdriver.Remote(
        command_executor="{server}",
        options=options,
    )
    yield drv
    drv.quit()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """測試失敗時自動截圖"""
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        driver = item.funcargs.get("driver")
        if driver:
            SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            path = SCREENSHOT_DIR / f"FAIL_{{item.name}}.png"
            driver.save_screenshot(str(path))
'''
        filepath = self.output / "conftest.py"
        filepath.write_text(code, encoding="utf-8")
        return filepath

    def write_test(self, page: PageSpec) -> Path:
        """產生單一頁面的測試檔案"""
        class_name = self._to_class_name(page.name)
        data_file = f"{page.name}_data.json"

        lines: list[str] = []

        # --- header ---
        lines.append(f'"""')
        lines.append(f'{class_name} 測試案例')
        lines.append(f'自動產生 — 包含正向 / 反向 / 邊界測試')
        lines.append(f'"""')
        lines.append(f'')
        lines.append(f'import json')
        lines.append(f'from pathlib import Path')
        lines.append(f'')
        lines.append(f'import pytest')
        lines.append(f'')
        lines.append(f'from pages.{page.name}_page import {class_name}')
        lines.append(f'')
        lines.append(f'')
        lines.append(f'# ── 載入測試資料 ──')
        lines.append(f'')
        lines.append(f'DATA_DIR = Path(__file__).resolve().parent.parent / "test_data"')
        lines.append(f'')
        lines.append(f'')
        lines.append(f'def _load_data(filename: str) -> list[dict]:')
        lines.append(f'    with open(DATA_DIR / filename, encoding="utf-8") as f:')
        lines.append(f'        return json.load(f)')
        lines.append(f'')
        lines.append(f'')
        lines.append(f'def _filter(data: list[dict], category: str) -> list[dict]:')
        lines.append(f'    return [d for d in data if d.get("category") == category]')
        lines.append(f'')
        lines.append(f'')
        lines.append(f'def _ids(data: list[dict]) -> list[str]:')
        lines.append(f'    return [d.get("case_id", str(i)) for i, d in enumerate(data)]')
        lines.append(f'')
        lines.append(f'')
        lines.append(f'ALL_DATA = _load_data("{data_file}")')
        lines.append(f'POSITIVE = _filter(ALL_DATA, "positive")')
        lines.append(f'NEGATIVE = _filter(ALL_DATA, "negative")')
        lines.append(f'BOUNDARY = _filter(ALL_DATA, "boundary")')
        lines.append(f'')
        lines.append(f'')

        # --- Test class ---
        lines.append(f'class Test{class_name}:')
        lines.append(f'    """{page.description or page.name} 頁面測試"""')
        lines.append(f'')

        # smoke
        lines.append(f'    @pytest.mark.smoke')
        lines.append(f'    def test_page_displayed(self, driver):')
        lines.append(f'        """冒煙：頁面正確載入"""')
        lines.append(f'        page = {class_name}(driver)')
        lines.append(f'        assert page.is_page_displayed()')
        lines.append(f'')

        inputs = page.inputs

        if inputs:
            # --- 正向測試 ---
            lines.append(f'    # ── 正向測試 ──')
            lines.append(f'')
            lines.append(f'    @pytest.mark.smoke')
            lines.append(f'    @pytest.mark.parametrize("data", POSITIVE, ids=_ids(POSITIVE))')
            lines.append(f'    def test_positive(self, driver, data):')
            lines.append(f'        """正向：有效資料應成功"""')
            lines.append(f'        page = {class_name}(driver)')
            if page.submit_button:
                params = ", ".join(
                    f'{e.name.lower()}=data.get("{e.name}", "")' for e in inputs
                )
                lines.append(f'        page.fill_and_submit({params})')
            else:
                for e in inputs:
                    lines.append(f'        page.enter_{e.name.lower()}(data.get("{e.name}", ""))')
            if page.success_indicator:
                lines.append(f'        assert page.is_success(), (')
                lines.append(f'            f"[{{data[\'case_id\']}}] {{data[\'description\']}} — 預期成功"')
                lines.append(f'        )')
            else:
                lines.append(f'        # 正向操作後頁面應正常（無 success_indicator 時驗證頁面不 crash）')
                lines.append(f'        assert page.is_page_displayed(), (')
                lines.append(f'            f"[{{data[\'case_id\']}}] {{data[\'description\']}} — 正向操作後頁面異常"')
                lines.append(f'        )')
            lines.append(f'')

            # --- 反向測試 ---
            lines.append(f'    # ── 反向測試 ──')
            lines.append(f'')
            lines.append(f'    @pytest.mark.negative')
            lines.append(f'    @pytest.mark.regression')
            lines.append(f'    @pytest.mark.parametrize("data", NEGATIVE, ids=_ids(NEGATIVE))')
            lines.append(f'    def test_negative(self, driver, data):')
            lines.append(f'        """反向：無效資料應顯示錯誤"""')
            lines.append(f'        page = {class_name}(driver)')
            if page.submit_button:
                params = ", ".join(
                    f'{e.name.lower()}=data.get("{e.name}", "")' for e in inputs
                )
                lines.append(f'        page.fill_and_submit({params})')
            else:
                for e in inputs:
                    lines.append(f'        page.enter_{e.name.lower()}(data.get("{e.name}", ""))')
            if page.error_indicator:
                lines.append(f'        assert page.is_error_displayed(), (')
                lines.append(f'            f"[{{data[\'case_id\']}}] {{data[\'description\']}} — 預期顯示錯誤"')
                lines.append(f'        )')
            else:
                lines.append(f'        # 反向驗證：至少應停留在同一頁')
                lines.append(f'        assert page.is_page_displayed(), (')
                lines.append(f'            f"[{{data[\'case_id\']}}] {{data[\'description\']}} — 預期停留在頁面"')
                lines.append(f'        )')
            lines.append(f'')

            # --- 邊界測試 ---
            lines.append(f'    # ── 邊界測試 ──')
            lines.append(f'')
            lines.append(f'    @pytest.mark.boundary')
            lines.append(f'    @pytest.mark.regression')
            lines.append(f'    @pytest.mark.parametrize("data", BOUNDARY, ids=_ids(BOUNDARY))')
            lines.append(f'    def test_boundary(self, driver, data):')
            lines.append(f'        """邊界：極端輸入不應 crash"""')
            lines.append(f'        page = {class_name}(driver)')
            if page.submit_button:
                params = ", ".join(
                    f'{e.name.lower()}=data.get("{e.name}", "")' for e in inputs
                )
                lines.append(f'        page.fill_and_submit({params})')
            else:
                for e in inputs:
                    lines.append(f'        page.enter_{e.name.lower()}(data.get("{e.name}", ""))')
            lines.append(f'        # 邊界測試：App 不應 crash，頁面仍可操作')
            lines.append(f'        assert page.is_page_displayed(), (')
            lines.append(f'            f"[{{data[\'case_id\']}}] {{data[\'description\']}} — App 可能已 crash"')
            lines.append(f'        )')
            lines.append(f'')

        code = "\n".join(lines)
        filepath = self.tests_dir / f"test_{page.name}.py"
        filepath.write_text(code, encoding="utf-8")
        return filepath

    def _to_class_name(self, name: str) -> str:
        parts = name.replace("-", "_").split("_")
        return "".join(p.capitalize() for p in parts) + "Page"
