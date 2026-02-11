"""
Page Object Writer
根據 PageSpec 產生 Page Object 檔案。
"""

from pathlib import Path

from generator.schema import (
    ElementSpec, ElementType, LocatorStrategy, PageSpec,
)


# Locator 策略 → import / 程式碼 對應
_LOCATOR_MAP = {
    LocatorStrategy.ID: ("AppiumBy.ID", "AppiumBy"),
    LocatorStrategy.ACCESSIBILITY_ID: ("AppiumBy.ACCESSIBILITY_ID", "AppiumBy"),
    LocatorStrategy.XPATH: ("AppiumBy.XPATH", "AppiumBy"),
    LocatorStrategy.CLASS_NAME: ("AppiumBy.CLASS_NAME", "AppiumBy"),
    LocatorStrategy.ANDROID_UIAUTOMATOR: ("AppiumBy.ANDROID_UIAUTOMATOR", "AppiumBy"),
    LocatorStrategy.IOS_PREDICATE: ("AppiumBy.IOS_PREDICATE_STRING", "AppiumBy"),
    LocatorStrategy.IOS_CLASS_CHAIN: ("AppiumBy.IOS_CLASS_CHAIN", "AppiumBy"),
}


class PageWriter:
    """產生 Page Object .py 檔"""

    def __init__(self, output_dir: Path):
        self.pages_dir = output_dir / "pages"
        self.pages_dir.mkdir(parents=True, exist_ok=True)
        # 確保 __init__.py
        init = self.pages_dir / "__init__.py"
        if not init.exists():
            init.write_text("", encoding="utf-8")

    def write(self, page: PageSpec) -> Path:
        """產生單一頁面的 Page Object"""
        class_name = self._to_class_name(page.name)
        lines: list[str] = []

        # --- header ---
        lines.append(f'"""')
        lines.append(f'{class_name} — {page.description or page.name} 頁面')
        lines.append(f'自動產生，可自行擴充。')
        lines.append(f'"""')
        lines.append(f'')
        lines.append(f'from appium.webdriver.common.appiumby import AppiumBy')
        lines.append(f'from selenium.webdriver.support import expected_conditions as EC')
        lines.append(f'from selenium.webdriver.support.ui import WebDriverWait')
        lines.append(f'')
        lines.append(f'')
        lines.append(f'class {class_name}:')
        lines.append(f'    """')
        lines.append(f'    {page.description or page.name} 頁面操作')
        lines.append(f'    """')
        lines.append(f'')
        lines.append(f'    def __init__(self, driver, timeout: int = 10):')
        lines.append(f'        self.driver = driver')
        lines.append(f'        self.timeout = timeout')
        lines.append(f'')

        # --- locators ---
        lines.append(f'    # ── Locators ──')
        lines.append(f'')
        for el in page.elements:
            loc_code, _ = _LOCATOR_MAP.get(
                el.locator_strategy, ("AppiumBy.ID", "AppiumBy")
            )
            comment = f"  # {el.description}" if el.description else ""
            lines.append(
                f'    {el.name.upper()} = ({loc_code}, "{el.locator_value}"){comment}'
            )
        lines.append(f'')

        # --- 通用方法 ---
        lines.append(f'    # ── 通用 ──')
        lines.append(f'')
        lines.append(f'    def _find(self, locator):')
        lines.append(f'        return WebDriverWait(self.driver, self.timeout).until(')
        lines.append(f'            EC.presence_of_element_located(locator)')
        lines.append(f'        )')
        lines.append(f'')
        lines.append(f'    def _click(self, locator):')
        lines.append(f'        WebDriverWait(self.driver, self.timeout).until(')
        lines.append(f'            EC.element_to_be_clickable(locator)')
        lines.append(f'        ).click()')
        lines.append(f'')
        lines.append(f'    def _input(self, locator, text: str):')
        lines.append(f'        el = self._find(locator)')
        lines.append(f'        el.clear()')
        lines.append(f'        el.send_keys(text)')
        lines.append(f'')
        lines.append(f'    def _get_text(self, locator) -> str:')
        lines.append(f'        return self._find(locator).text')
        lines.append(f'')
        lines.append(f'    def _is_displayed(self, locator, timeout: int = 3) -> bool:')
        lines.append(f'        try:')
        lines.append(f'            WebDriverWait(self.driver, timeout).until(')
        lines.append(f'                EC.presence_of_element_located(locator)')
        lines.append(f'            )')
        lines.append(f'            return True')
        lines.append(f'        except Exception:')
        lines.append(f'            return False')
        lines.append(f'')

        # --- 每個元素的專屬方法 ---
        lines.append(f'    # ── 元素操作 ──')
        lines.append(f'')

        for el in page.elements:
            name_lower = el.name.lower()
            name_upper = el.name.upper()

            if el.element_type == ElementType.INPUT:
                lines.append(f'    def enter_{name_lower}(self, value: str) -> "{class_name}":')
                lines.append(f'        """輸入 {el.description or el.name}"""')
                lines.append(f'        self._input(self.{name_upper}, value)')
                lines.append(f'        return self')
                lines.append(f'')
                lines.append(f'    def get_{name_lower}_text(self) -> str:')
                lines.append(f'        return self._get_text(self.{name_upper})')
                lines.append(f'')

            elif el.element_type == ElementType.BUTTON:
                lines.append(f'    def tap_{name_lower}(self) -> None:')
                lines.append(f'        """點擊 {el.description or el.name}"""')
                lines.append(f'        self._click(self.{name_upper})')
                lines.append(f'')

            elif el.element_type in (ElementType.CHECKBOX, ElementType.SWITCH):
                lines.append(f'    def toggle_{name_lower}(self) -> None:')
                lines.append(f'        """切換 {el.description or el.name}"""')
                lines.append(f'        self._click(self.{name_upper})')
                lines.append(f'')

            elif el.element_type == ElementType.TEXT:
                lines.append(f'    def get_{name_lower}(self) -> str:')
                lines.append(f'        """取得 {el.description or el.name} 文字"""')
                lines.append(f'        return self._get_text(self.{name_upper})')
                lines.append(f'')

        # --- 頁面層級方法 ---
        lines.append(f'    # ── 頁面操作 ──')
        lines.append(f'')

        # is_page_displayed
        if page.elements:
            first = page.elements[0]
            lines.append(f'    def is_page_displayed(self) -> bool:')
            lines.append(f'        """頁面是否載入完成"""')
            lines.append(f'        return self._is_displayed(self.{first.name.upper()})')
            lines.append(f'')

        # 成功/失敗指示器
        if page.success_indicator:
            lines.append(f'    def is_success(self) -> bool:')
            lines.append(f'        """操作是否成功"""')
            lines.append(f'        return self._is_displayed(self.{page.success_indicator.upper()})')
            lines.append(f'')

        if page.error_indicator:
            lines.append(f'    def is_error_displayed(self) -> bool:')
            lines.append(f'        """是否顯示錯誤"""')
            lines.append(f'        return self._is_displayed(self.{page.error_indicator.upper()})')
            lines.append(f'')
            lines.append(f'    def get_error_message(self) -> str:')
            lines.append(f'        """取得錯誤訊息"""')
            lines.append(f'        return self._get_text(self.{page.error_indicator.upper()})')
            lines.append(f'')

        # 快捷 fill + submit
        inputs = page.inputs
        if inputs and page.submit_button:
            params = ", ".join(f'{e.name.lower()}: str = ""' for e in inputs)
            lines.append(f'    def fill_and_submit(self, {params}) -> None:')
            lines.append(f'        """填入所有欄位並提交"""')
            for e in inputs:
                lines.append(f'        if {e.name.lower()}:')
                lines.append(f'            self.enter_{e.name.lower()}({e.name.lower()})')
            lines.append(f'        self.tap_{page.submit_button.lower()}()')
            lines.append(f'')

        code = "\n".join(lines)
        filepath = self.pages_dir / f"{page.name}_page.py"
        filepath.write_text(code, encoding="utf-8")
        return filepath

    def _to_class_name(self, name: str) -> str:
        parts = name.replace("-", "_").split("_")
        return "".join(p.capitalize() for p in parts) + "Page"
