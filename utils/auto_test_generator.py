"""
自動化測試產生器
連接模擬器後自動掃描當前頁面元素，產生：
1. Page Object 檔案
2. 正向 / 反向 / 邊界測試案例（含 parametrize 參數）

用法：
    python -m utils.auto_test_generator --page login --package com.example.app
"""

import argparse
import json
import re
import textwrap
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy

from config.config import Config

# 輸出目錄
PAGES_DIR = Path(__file__).resolve().parent.parent / "pages"
TESTS_DIR = Path(__file__).resolve().parent.parent / "tests"
DATA_DIR = Path(__file__).resolve().parent.parent / "test_data"


@dataclass
class ElementInfo:
    """掃描到的元素資訊"""
    resource_id: str = ""
    text: str = ""
    content_desc: str = ""
    class_name: str = ""
    clickable: bool = False
    editable: bool = False
    checkable: bool = False
    scrollable: bool = False
    bounds: str = ""
    # 產生用
    var_name: str = ""
    locator_type: str = ""
    locator_value: str = ""


@dataclass
class PageScan:
    """頁面掃描結果"""
    page_name: str
    elements: list[ElementInfo] = field(default_factory=list)
    input_fields: list[ElementInfo] = field(default_factory=list)
    buttons: list[ElementInfo] = field(default_factory=list)
    text_views: list[ElementInfo] = field(default_factory=list)
    checkboxes: list[ElementInfo] = field(default_factory=list)


class AutoTestGenerator:
    """自動掃描元素並產生 Page Object + 測試案例"""

    def __init__(self, driver=None):
        self.driver = driver

    def connect(self, platform: str = "android") -> None:
        """連接到已開啟的模擬器（用於獨立執行）"""
        caps = Config.load_caps(platform)
        if platform == "android":
            options = UiAutomator2Options().load_capabilities(caps)
        else:
            from appium.options.ios import XCUITestOptions
            options = XCUITestOptions().load_capabilities(caps)
        self.driver = webdriver.Remote(
            command_executor=Config.appium_server_url(),
            options=options,
        )

    def scan_page(self, page_name: str) -> PageScan:
        """
        掃描當前頁面所有可用元素。

        Args:
            page_name: 頁面名稱（如 "login", "home"）

        Returns:
            PageScan 物件
        """
        scan = PageScan(page_name=page_name)
        source = self.driver.page_source

        # 取得所有元素
        all_elements = self.driver.find_elements(AppiumBy.XPATH, "//*")

        for el in all_elements:
            info = ElementInfo(
                resource_id=el.get_attribute("resourceId") or "",
                text=el.get_attribute("text") or "",
                content_desc=el.get_attribute("contentDescription") or "",
                class_name=el.get_attribute("className") or "",
                clickable=el.get_attribute("clickable") == "true",
                editable=el.get_attribute("className", "").endswith("EditText"),
                checkable=el.get_attribute("checkable") == "true",
                scrollable=el.get_attribute("scrollable") == "true",
                bounds=el.get_attribute("bounds") or "",
            )

            # 跳過無辨識資訊的元素
            if not info.resource_id and not info.text and not info.content_desc:
                continue

            # 決定 locator
            if info.resource_id:
                info.locator_type = "AppiumBy.ID"
                info.locator_value = info.resource_id
                info.var_name = self._to_var_name(
                    info.resource_id.split("/")[-1] if "/" in info.resource_id
                    else info.resource_id
                )
            elif info.content_desc:
                info.locator_type = "AppiumBy.ACCESSIBILITY_ID"
                info.locator_value = info.content_desc
                info.var_name = self._to_var_name(info.content_desc)
            elif info.text:
                info.locator_type = "AppiumBy.XPATH"
                info.locator_value = f'//*[@text="{info.text}"]'
                info.var_name = self._to_var_name(info.text)
            else:
                continue

            scan.elements.append(info)

            # 分類
            if "EditText" in info.class_name:
                scan.input_fields.append(info)
            elif info.clickable and ("Button" in info.class_name or "button" in info.resource_id.lower()):
                scan.buttons.append(info)
            elif info.checkable:
                scan.checkboxes.append(info)
            elif "TextView" in info.class_name:
                scan.text_views.append(info)

        print(f"\n掃描完成: {page_name}")
        print(f"  輸入框: {len(scan.input_fields)}")
        print(f"  按鈕:   {len(scan.buttons)}")
        print(f"  文字:   {len(scan.text_views)}")
        print(f"  勾選框: {len(scan.checkboxes)}")
        print(f"  總計:   {len(scan.elements)} 個有效元素")

        return scan

    def generate_page_object(self, scan: PageScan) -> str:
        """從掃描結果產生 Page Object 原始碼"""
        class_name = self._to_class_name(scan.page_name)
        lines = [
            f'"""',
            f'{class_name} Page Object',
            f'自動產生於 {datetime.now().strftime("%Y-%m-%d %H:%M")}',
            f'"""',
            f'',
            f'from appium.webdriver.common.appiumby import AppiumBy',
            f'from core.base_page import BasePage',
            f'',
            f'',
            f'class {class_name}(BasePage):',
            f'    """{scan.page_name} 頁面"""',
            f'',
            f'    # ── Locators ──',
        ]

        # Locators
        seen_vars = set()
        for el in scan.elements:
            if el.var_name in seen_vars:
                continue
            seen_vars.add(el.var_name)
            lines.append(
                f'    {el.var_name.upper()} = '
                f'({el.locator_type}, "{el.locator_value}")'
            )

        lines.append('')
        lines.append('    # ── 操作方法 ──')
        lines.append('')

        # 輸入框方法
        for el in scan.input_fields:
            method = f"enter_{el.var_name.lower()}"
            lines.extend([
                f'    def {method}(self, value: str) -> "{class_name}":',
                f'        self.input_text(self.{el.var_name.upper()}, value)',
                f'        return self',
                f'',
            ])

        # 按鈕方法
        for el in scan.buttons:
            method = f"tap_{el.var_name.lower()}"
            lines.extend([
                f'    def {method}(self) -> None:',
                f'        self.click(self.{el.var_name.upper()})',
                f'',
            ])

        # 勾選框方法
        for el in scan.checkboxes:
            method = f"toggle_{el.var_name.lower()}"
            lines.extend([
                f'    def {method}(self) -> None:',
                f'        self.click(self.{el.var_name.upper()})',
                f'',
            ])

        # 文字驗證方法
        for el in scan.text_views:
            if el.var_name:
                method = f"get_{el.var_name.lower()}_text"
                lines.extend([
                    f'    def {method}(self) -> str:',
                    f'        return self.get_text(self.{el.var_name.upper()})',
                    f'',
                ])

        # 頁面驗證
        if scan.elements:
            first = scan.elements[0]
            lines.extend([
                f'    # ── 頁面驗證 ──',
                f'',
                f'    def is_page_displayed(self) -> bool:',
                f'        return self.is_element_present(self.{first.var_name.upper()})',
            ])

        code = '\n'.join(lines)

        # 儲存
        filepath = PAGES_DIR / f"{scan.page_name}_page.py"
        filepath.write_text(code, encoding="utf-8")
        print(f"Page Object 已產生: {filepath}")
        return code

    def generate_test_data(self, scan: PageScan) -> dict:
        """
        根據輸入框產生正向/反向/邊界測試資料。

        Returns:
            dict 包含 positive, negative, boundary 三組資料
        """
        test_data = {
            "positive": [],
            "negative": [],
            "boundary": [],
        }

        # 正向測試資料
        positive = {"case_id": f"{scan.page_name.upper()}_POS_001", "description": "正向-有效資料"}
        for field in scan.input_fields:
            name = field.var_name.lower()
            if "email" in name or "mail" in name:
                positive[name] = "test@example.com"
            elif "phone" in name or "tel" in name:
                positive[name] = "0912345678"
            elif "password" in name or "pwd" in name:
                positive[name] = "Abc123!@#"
            elif "name" in name or "user" in name:
                positive[name] = "testuser"
            elif "age" in name:
                positive[name] = "25"
            else:
                positive[name] = "test_value"
        positive["expected"] = "success"
        test_data["positive"].append(positive)

        # 反向測試資料
        for i, field in enumerate(scan.input_fields):
            name = field.var_name.lower()

            # 空白值
            neg_empty = {
                "case_id": f"{scan.page_name.upper()}_NEG_{(i*3+1):03d}",
                "description": f"反向-{name}空白",
                "expected": "error",
            }
            for f in scan.input_fields:
                fn = f.var_name.lower()
                if fn == name:
                    neg_empty[fn] = ""
                else:
                    neg_empty[fn] = positive.get(fn, "valid")
            test_data["negative"].append(neg_empty)

            # 特殊字元
            neg_special = {
                "case_id": f"{scan.page_name.upper()}_NEG_{(i*3+2):03d}",
                "description": f"反向-{name}特殊字元",
                "expected": "error",
            }
            for f in scan.input_fields:
                fn = f.var_name.lower()
                if fn == name:
                    neg_special[fn] = "<script>alert(1)</script>"
                else:
                    neg_special[fn] = positive.get(fn, "valid")
            test_data["negative"].append(neg_special)

            # SQL injection
            neg_sql = {
                "case_id": f"{scan.page_name.upper()}_NEG_{(i*3+3):03d}",
                "description": f"反向-{name} SQL injection",
                "expected": "error",
            }
            for f in scan.input_fields:
                fn = f.var_name.lower()
                if fn == name:
                    neg_sql[fn] = "' OR '1'='1"
                else:
                    neg_sql[fn] = positive.get(fn, "valid")
            test_data["negative"].append(neg_sql)

        # 邊界測試資料
        for field in scan.input_fields:
            name = field.var_name.lower()

            # 最短 (1 字元)
            bd_min = {
                "case_id": f"{scan.page_name.upper()}_BD_MIN_{name.upper()}",
                "description": f"邊界-{name}最短(1字元)",
                "expected": "check",
            }
            for f in scan.input_fields:
                fn = f.var_name.lower()
                bd_min[fn] = "a" if fn == name else positive.get(fn, "valid")
            test_data["boundary"].append(bd_min)

            # 最長 (256 字元)
            bd_max = {
                "case_id": f"{scan.page_name.upper()}_BD_MAX_{name.upper()}",
                "description": f"邊界-{name}最長(256字元)",
                "expected": "check",
            }
            for f in scan.input_fields:
                fn = f.var_name.lower()
                bd_max[fn] = "a" * 256 if fn == name else positive.get(fn, "valid")
            test_data["boundary"].append(bd_max)

            # Unicode
            bd_unicode = {
                "case_id": f"{scan.page_name.upper()}_BD_UNI_{name.upper()}",
                "description": f"邊界-{name}中文/Emoji",
                "expected": "check",
            }
            for f in scan.input_fields:
                fn = f.var_name.lower()
                bd_unicode[fn] = "測試用戶名稱" if fn == name else positive.get(fn, "valid")
            test_data["boundary"].append(bd_unicode)

        # 儲存
        DATA_DIR.mkdir(exist_ok=True)
        filepath = DATA_DIR / f"{scan.page_name}_test_data.json"
        with open(filepath, "w", encoding="utf-8") as f:
            all_data = test_data["positive"] + test_data["negative"] + test_data["boundary"]
            json.dump(all_data, f, ensure_ascii=False, indent=4)
        print(f"測試資料已產生: {filepath} ({len(all_data)} 組)")

        return test_data

    def generate_test_file(self, scan: PageScan) -> str:
        """從掃描結果產生 pytest 測試案例"""
        class_name = self._to_class_name(scan.page_name)
        page_module = f"{scan.page_name}_page"
        data_file = f"{scan.page_name}_test_data.json"

        field_names = [f.var_name.lower() for f in scan.input_fields]

        code = textwrap.dedent(f'''\
            """
            {class_name} 自動產生測試案例
            包含正向、反向、邊界測試。
            自動產生於 {datetime.now().strftime("%Y-%m-%d %H:%M")}
            """

            import pytest
            from pages.{page_module} import {class_name}
            from utils.data_loader import load_json, get_test_ids
            from utils.decorators import retry_on_failure

            # 載入測試資料
            TEST_DATA = load_json("{data_file}")
            TEST_IDS = get_test_ids(TEST_DATA)


            class Test{class_name}:
                """{scan.page_name} 頁面測試"""

                @pytest.mark.parametrize("data", TEST_DATA, ids=TEST_IDS)
                def test_with_data(self, driver, data):
                    """資料驅動測試：正向/反向/邊界"""
                    page = {class_name}(driver)
        ''')

        # 加入欄位操作
        for name in field_names:
            code += f'            page.enter_{name}(data.get("{name}", ""))\n'

        # 按鈕
        if scan.buttons:
            btn = scan.buttons[0]
            code += f'            page.tap_{btn.var_name.lower()}()\n'

        code += textwrap.dedent(f'''
                    if data["expected"] == "success":
                        # 正向：驗證操作成功
                        pass  # TODO: 加入成功驗證邏輯
                    elif data["expected"] == "error":
                        # 反向：驗證顯示錯誤
                        assert page.is_page_displayed(), (
                            f"[{{data['case_id']}}] {{data['description']}} - 預期停留在頁面"
                        )
                    else:
                        # 邊界：記錄行為（不一定是錯誤）
                        pass  # TODO: 根據需求調整斷言

                @pytest.mark.smoke
                def test_page_displayed(self, driver):
                    """冒煙：頁面正確載入"""
                    page = {class_name}(driver)
                    assert page.is_page_displayed()
        ''')

        # 儲存
        filepath = TESTS_DIR / f"test_{scan.page_name}_auto.py"
        filepath.write_text(code, encoding="utf-8")
        print(f"測試案例已產生: {filepath}")
        return code

    def generate_all(self, page_name: str) -> None:
        """
        一鍵掃描 + 產生全部檔案。

        會產生：
        1. pages/{page_name}_page.py   — Page Object
        2. test_data/{page_name}_test_data.json — 測試資料
        3. tests/test_{page_name}_auto.py — 測試案例
        """
        print(f"\n{'='*50}")
        print(f"  自動產生測試: {page_name}")
        print(f"{'='*50}")

        scan = self.scan_page(page_name)
        self.generate_page_object(scan)
        self.generate_test_data(scan)
        self.generate_test_file(scan)

        print(f"\n全部完成！產生的檔案：")
        print(f"  1. pages/{page_name}_page.py")
        print(f"  2. test_data/{page_name}_test_data.json")
        print(f"  3. tests/test_{page_name}_auto.py")

    # ── 內部方法 ──

    def _to_var_name(self, text: str) -> str:
        """轉換為 Python 變數名稱 (UPPER_SNAKE_CASE)"""
        name = re.sub(r'[^a-zA-Z0-9_]', '_', text)
        name = re.sub(r'_+', '_', name).strip('_')
        if name and name[0].isdigit():
            name = f"el_{name}"
        return name.upper() if name else "UNKNOWN"

    def _to_class_name(self, page_name: str) -> str:
        """轉換為 ClassName (PascalCase + Page)"""
        parts = page_name.replace('-', '_').split('_')
        return ''.join(p.capitalize() for p in parts) + 'Page'


# ── CLI 入口 ──

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="自動掃描頁面並產生測試")
    parser.add_argument("--page", required=True, help="頁面名稱 (如 login, home)")
    parser.add_argument("--platform", default="android", choices=["android", "ios"])
    args = parser.parse_args()

    gen = AutoTestGenerator()
    gen.connect(args.platform)
    try:
        gen.generate_all(args.page)
    finally:
        gen.driver.quit()
