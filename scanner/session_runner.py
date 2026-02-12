"""
SessionRunner — 串接全流程的控制器

一個指令完成：
1. 連線模擬器
2. 掃描當前頁面
3. 智慧分析所有元素
4. 自動用正向資料填入 + 提交
5. 重新掃描新頁面
6. 記錄轉場
7. (可選) 重複探索更多頁面
8. 輸出完整結果到外部目錄

所有結果包含：
- session.json       — 完整掃描記錄
- test_data/*.json   — 每頁的測試資料
- pages/*.py         — Page Object
- tests/*.py         — 測試案例
- screenshots/       — 每一步的截圖
- flow_map.md        — 頁面流程圖
"""

from __future__ import annotations

import json
import textwrap
from datetime import datetime
from pathlib import Path

from appium import webdriver
from appium.options.android import UiAutomator2Options

from config.config import Config
from scanner.analyzer import PageAnalyzer, PageSnapshot, PageType
from scanner.flow_recorder import FlowRecorder, FlowSession
from scanner.smart_test_data import SmartTestDataGenerator, TestCase
from utils.logger import logger


class SessionRunner:
    """
    智慧掃描 session 控制器

    用法:
        runner = SessionRunner(output_dir="/tmp/my_app_tests")
        runner.connect()                  # 連線模擬器
        runner.auto_explore(max_pages=5)  # 自動探索 5 個頁面
        runner.export_all()               # 輸出全部檔案
    """

    def __init__(self, output_dir: str | Path, platform: str = "android"):
        self.output = Path(output_dir).resolve()
        self.platform = platform
        self.driver = None
        self.recorder: FlowRecorder | None = None

    def connect(self, driver=None) -> None:
        """
        連線到模擬器。

        Args:
            driver: 已有的 driver（測試中使用）。
                    None 時自動從 config 建立。
        """
        if driver:
            self.driver = driver
        else:
            caps = Config.load_caps(self.platform)
            if self.platform == "android":
                options = UiAutomator2Options().load_capabilities(caps)
            else:
                from appium.options.ios import XCUITestOptions
                options = XCUITestOptions().load_capabilities(caps)

            self.driver = webdriver.Remote(
                command_executor=Config.appium_server_url(),
                options=options,
            )
            logger.info(f"已連線: {Config.appium_server_url()}")

        self.recorder = FlowRecorder(self.driver, self.output)

    def scan_current(self) -> PageSnapshot:
        """掃描當前頁面"""
        return self.recorder.scan_current_page()

    def auto_explore(self, max_pages: int = 5) -> FlowSession:
        """
        自動探索模式。

        從當前頁面開始，自動：
        1. 掃描分析
        2. 用正向資料填入表單
        3. 提交
        4. 到新頁面後繼續掃描
        5. 重複直到 max_pages 或無法再前進

        Args:
            max_pages: 最多探索幾個頁面

        Returns:
            FlowSession
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"  開始自動探索 (最多 {max_pages} 頁)")
        logger.info(f"  輸出: {self.output}")
        logger.info(f"{'='*60}\n")

        current = self.scan_current()
        explored = 1

        while explored < max_pages:
            if not current.inputs and not current.buttons:
                logger.info("此頁面無可操作元素，探索結束")
                break

            if current.inputs and current.submit_button:
                # 有表單 → 填入並提交
                logger.info(f"\n--- 第 {explored + 1} 步: 填入表單 ---")
                new_snap, transition = self.recorder.fill_and_submit(current)

                if transition.transition_type == "same_page":
                    logger.info("頁面未變化，嘗試其他按鈕...")
                    # 嘗試其他按鈕
                    moved = False
                    for btn in current.buttons:
                        if btn == current.submit_button:
                            continue
                        new_snap, transition = self.recorder.click_button(current, btn)
                        if transition.transition_type != "same_page":
                            moved = True
                            break
                    if not moved:
                        logger.info("無法離開當前頁面，探索結束")
                        break

                current = new_snap
                explored += 1
            elif current.buttons:
                # 無表單但有按鈕 → 逐個嘗試
                logger.info(f"\n--- 第 {explored + 1} 步: 嘗試按鈕 ---")
                moved = False
                for btn in current.buttons:
                    new_snap, transition = self.recorder.click_button(current, btn)
                    if transition.transition_type != "same_page":
                        current = new_snap
                        explored += 1
                        moved = True
                        break
                if not moved:
                    logger.info("所有按鈕都未產生轉場，探索結束")
                    break
            else:
                break

        logger.info(f"\n探索完成: 共 {explored} 個頁面")
        return self.recorder.session

    def export_all(self) -> dict:
        """
        輸出所有結果到 output_dir。

        產出：
        - session.json
        - test_data/{page}_data.json
        - pages/{page}_page.py
        - tests/test_{page}.py
        - conftest.py + pytest.ini + requirements.txt
        - flow_map.md
        - screenshots/
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"  輸出結果")
        logger.info(f"{'='*60}\n")

        created_files: list[str] = []

        # 1. Session JSON
        session_path = self.recorder.save_session()
        created_files.append(str(session_path.relative_to(self.output)))

        # 2. 每個頁面的 test data
        data_dir = self.output / "test_data"
        data_dir.mkdir(exist_ok=True)
        for page_name, cases in self.recorder.session.test_cases.items():
            path = data_dir / f"{page_name}_data.json"
            data = [
                {
                    "case_id": c.case_id,
                    "category": c.category,
                    "description": c.description,
                    **c.fields,
                    "expected": c.expected,
                    "tags": c.tags,
                }
                for c in cases
            ]
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            created_files.append(str(path.relative_to(self.output)))
            logger.info(f"  test_data/{page_name}_data.json ({len(data)} 組)")

        # 3. Page Objects
        pages_dir = self.output / "pages"
        pages_dir.mkdir(exist_ok=True)
        (pages_dir / "__init__.py").write_text("", encoding="utf-8")
        for snap in self.recorder.session.snapshots:
            path = self._write_page_object(snap, pages_dir)
            created_files.append(str(path.relative_to(self.output)))
            logger.info(f"  pages/{snap.inferred_name}_page.py")

        # 4. Tests
        tests_dir = self.output / "tests"
        tests_dir.mkdir(exist_ok=True)
        (tests_dir / "__init__.py").write_text("", encoding="utf-8")
        for snap in self.recorder.session.snapshots:
            cases = self.recorder.session.test_cases.get(snap.inferred_name, [])
            if cases:
                path = self._write_test_file(snap, cases, tests_dir)
                created_files.append(str(path.relative_to(self.output)))
                logger.info(f"  tests/test_{snap.inferred_name}.py ({len(cases)} cases)")

        # 5. conftest + pytest.ini + requirements
        self._write_conftest(self.output)
        created_files.append("conftest.py")
        self._write_pytest_ini(self.output)
        created_files.append("pytest.ini")
        self._write_requirements(self.output)
        created_files.append("requirements.txt")

        # 6. Flow map
        flow_path = self._write_flow_map()
        created_files.append(str(flow_path.relative_to(self.output)))

        # 統計
        summary = {
            "output_dir": str(self.output),
            "pages": len(self.recorder.session.snapshots),
            "transitions": len(self.recorder.session.transitions),
            "total_test_cases": sum(
                len(c) for c in self.recorder.session.test_cases.values()
            ),
            "files": created_files,
        }

        logger.info(f"\n{'='*60}")
        logger.info(f"  完成！")
        logger.info(f"  頁面: {summary['pages']}")
        logger.info(f"  轉場: {summary['transitions']}")
        logger.info(f"  測試: {summary['total_test_cases']} 組")
        logger.info(f"  檔案: {len(created_files)} 個")
        logger.info(f"  目錄: {self.output}")
        logger.info(f"{'='*60}\n")

        return summary

    def disconnect(self) -> None:
        """關閉 driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    # ── 檔案產生 ──

    def _write_page_object(self, snap: PageSnapshot, pages_dir: Path) -> Path:
        """產生 Page Object"""
        name = snap.inferred_name
        cls = "".join(p.capitalize() for p in name.split("_")) + "Page"

        lines = [
            f'"""',
            f'{cls} — 自動掃描產生',
            f'掃描時間: {snap.timestamp}',
            f'頁面類型: {snap.page_type.value} (信心 {snap.page_type_confidence:.0%})',
            f'"""',
            f'',
            f'from appium.webdriver.common.appiumby import AppiumBy',
            f'from selenium.webdriver.support import expected_conditions as EC',
            f'from selenium.webdriver.support.ui import WebDriverWait',
            f'',
            f'',
            f'class {cls}:',
            f'',
            f'    def __init__(self, driver, timeout: int = 10):',
            f'        self.driver = driver',
            f'        self.timeout = timeout',
            f'',
            f'    # ── Locators ──',
        ]

        seen = set()
        for el in snap.all_elements:
            if el.var_name in seen:
                continue
            seen.add(el.var_name)
            loc_map = {"id": "AppiumBy.ID", "accessibility_id": "AppiumBy.ACCESSIBILITY_ID", "xpath": "AppiumBy.XPATH"}
            loc_by = loc_map.get(el.locator_strategy, "AppiumBy.ID")
            semantic_comment = ""
            if el.element_type == "input" and el.field_semantic.value != "unknown":
                semantic_comment = f"  # [{el.field_semantic.value}]"
            elif el.element_type == "button" and el.button_semantic.value != "unknown":
                semantic_comment = f"  # [{el.button_semantic.value}]"
            lines.append(f'    {el.var_name.upper()} = ({loc_by}, "{el.locator_value}"){semantic_comment}')

        lines.append(f'')
        lines.append(f'    # ── 通用 ──')
        lines.append(f'    def _find(self, loc): return WebDriverWait(self.driver, self.timeout).until(EC.presence_of_element_located(loc))')
        lines.append(f'    def _click(self, loc): WebDriverWait(self.driver, self.timeout).until(EC.element_to_be_clickable(loc)).click()')
        lines.append(f'    def _input(self, loc, text): el = self._find(loc); el.clear(); el.send_keys(text)')
        lines.append(f'    def _text(self, loc) -> str: return self._find(loc).text')
        lines.append(f'    def _visible(self, loc, t=3) -> bool:')
        lines.append(f'        try: WebDriverWait(self.driver, t).until(EC.presence_of_element_located(loc)); return True')
        lines.append(f'        except Exception: return False')
        lines.append(f'')
        lines.append(f'    # ── 操作 ──')

        for el in snap.inputs:
            lines.append(f'    def enter_{el.var_name}(self, v: str): self._input(self.{el.var_name.upper()}, v); return self')

        for el in snap.buttons:
            lines.append(f'    def tap_{el.var_name}(self): self._click(self.{el.var_name.upper()})')

        for el in snap.checkboxes:
            lines.append(f'    def toggle_{el.var_name}(self): self._click(self.{el.var_name.upper()})')

        lines.append(f'')
        if snap.inputs and snap.submit_button:
            params = ", ".join(f'{e.var_name}=""' for e in snap.inputs)
            lines.append(f'    def fill_and_submit(self, {params}):')
            for e in snap.inputs:
                lines.append(f'        if {e.var_name}: self.enter_{e.var_name}({e.var_name})')
            lines.append(f'        self.tap_{snap.submit_button.var_name}()')
            lines.append(f'')

        if snap.all_elements:
            first = snap.all_elements[0]
            lines.append(f'    def is_page_displayed(self) -> bool: return self._visible(self.{first.var_name.upper()})')
        if snap.error_indicator:
            lines.append(f'    def is_error_displayed(self) -> bool: return self._visible(self.{snap.error_indicator.var_name.upper()})')
            lines.append(f'    def get_error_message(self) -> str: return self._text(self.{snap.error_indicator.var_name.upper()})')
        if snap.success_indicator:
            lines.append(f'    def is_success(self) -> bool: return self._visible(self.{snap.success_indicator.var_name.upper()})')

        code = "\n".join(lines) + "\n"
        path = pages_dir / f"{name}_page.py"
        path.write_text(code, encoding="utf-8")
        return path

    def _write_test_file(self, snap: PageSnapshot, cases: list[TestCase], tests_dir: Path) -> Path:
        """產生測試檔案"""
        name = snap.inferred_name
        cls = "".join(p.capitalize() for p in name.split("_")) + "Page"
        data_file = f"{name}_data.json"

        code = textwrap.dedent(f'''\
            """
            {cls} 測試 — 自動掃描產生
            頁面類型: {snap.page_type.value}
            """

            import json
            from pathlib import Path
            import pytest
            from pages.{name}_page import {cls}

            DATA_DIR = Path(__file__).resolve().parent.parent / "test_data"

            def _load(f):
                with open(DATA_DIR / f, encoding="utf-8") as fp:
                    return json.load(fp)

            def _by(data, cat):
                return [d for d in data if d.get("category") == cat]

            def _ids(data):
                return [d.get("case_id", str(i)) for i, d in enumerate(data)]

            ALL = _load("{data_file}")
            POS = _by(ALL, "positive")
            NEG = _by(ALL, "negative")
            BD  = _by(ALL, "boundary")
            SEC = _by(ALL, "security")


            class Test{cls}:

                @pytest.mark.smoke
                def test_page_loads(self, driver):
                    assert {cls}(driver).is_page_displayed()
        ''')

        inputs = snap.inputs
        if inputs:
            field_names = [e.var_name for e in inputs]

            # 正向
            code += textwrap.dedent(f'''
                @pytest.mark.smoke
                @pytest.mark.parametrize("d", POS, ids=_ids(POS))
                def test_positive(self, driver, d):
                    p = {cls}(driver)
            ''')
            if snap.submit_button:
                args = ", ".join(f'{n}=d.get("{n}","")' for n in field_names)
                code += f'        p.fill_and_submit({args})\n'
            if snap.success_indicator:
                code += f'        assert p.is_success(), f"[{{d[\'case_id\']}}] {{d[\'description\']}}"\n'
            else:
                code += f'        assert p.is_page_displayed(), f"[{{d[\'case_id\']}}] 正向操作後頁面異常"\n'

            # 反向
            code += textwrap.dedent(f'''
                @pytest.mark.negative
                @pytest.mark.parametrize("d", NEG, ids=_ids(NEG))
                def test_negative(self, driver, d):
                    p = {cls}(driver)
            ''')
            if snap.submit_button:
                args = ", ".join(f'{n}=d.get("{n}","")' for n in field_names)
                code += f'        p.fill_and_submit({args})\n'
            if snap.error_indicator:
                code += f'        assert p.is_error_displayed(), f"[{{d[\'case_id\']}}] {{d[\'description\']}}"\n'
            else:
                code += f'        assert p.is_page_displayed(), f"[{{d[\'case_id\']}}] App 不應 crash"\n'

            # 邊界
            code += textwrap.dedent(f'''
                @pytest.mark.boundary
                @pytest.mark.parametrize("d", BD, ids=_ids(BD))
                def test_boundary(self, driver, d):
                    p = {cls}(driver)
            ''')
            if snap.submit_button:
                args = ", ".join(f'{n}=d.get("{n}","")' for n in field_names)
                code += f'        p.fill_and_submit({args})\n'
            code += f'        assert p.is_page_displayed(), f"[{{d[\'case_id\']}}] App crash"\n'

            # 安全性
            code += textwrap.dedent(f'''
                @pytest.mark.security
                @pytest.mark.parametrize("d", SEC, ids=_ids(SEC))
                def test_security(self, driver, d):
                    p = {cls}(driver)
            ''')
            if snap.submit_button:
                args = ", ".join(f'{n}=d.get("{n}","")' for n in field_names)
                code += f'        p.fill_and_submit({args})\n'
            code += f'        assert p.is_page_displayed(), f"[{{d[\'case_id\']}}] 安全漏洞"\n'

        path = tests_dir / f"test_{name}.py"
        path.write_text(code, encoding="utf-8")
        return path

    def _write_flow_map(self) -> Path:
        """產生頁面流程圖 (Mermaid)"""
        lines = ["# Flow Map", "", "```mermaid", "graph TD"]

        for t in self.recorder.session.transitions:
            fr = t.from_page_name
            to = t.to_page_name
            act = t.action.replace("_", " ")
            lines.append(f"    {fr}-->|{act}|{to}")

        lines.append("```")
        lines.append("")

        # 頁面清單
        lines.append("## Pages")
        lines.append("")
        for snap in self.recorder.session.snapshots:
            cases = self.recorder.session.test_cases.get(snap.inferred_name, [])
            lines.append(
                f"- **{snap.inferred_name}** ({snap.page_type.value}) "
                f"— {len(snap.inputs)} inputs, {len(snap.buttons)} buttons, "
                f"{len(cases)} test cases"
            )

        lines.append("")
        lines.append("## Transitions")
        lines.append("")
        for t in self.recorder.session.transitions:
            lines.append(f"- {t.from_page_name} --[{t.action}]--> {t.to_page_name} ({t.transition_type})")

        path = self.output / "flow_map.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def _write_conftest(self, out: Path) -> None:
        code = textwrap.dedent(f'''\
            import pytest
            from appium import webdriver
            from appium.options.android import UiAutomator2Options
            import json
            from pathlib import Path

            CONFIG = Path(__file__).parent / "session.json"

            @pytest.fixture(scope="function")
            def driver():
                with open(CONFIG, encoding="utf-8") as f:
                    session = json.load(f)
                caps_file = Path(__file__).parent / "config" / "{self.platform}_caps.json"
                if caps_file.exists():
                    with open(caps_file, encoding="utf-8") as f:
                        caps = json.load(f)
                else:
                    caps = {{}}
                options = UiAutomator2Options().load_capabilities(caps)
                drv = webdriver.Remote(command_executor="http://127.0.0.1:4723", options=options)
                yield drv
                drv.quit()

            @pytest.hookimpl(tryfirst=True, hookwrapper=True)
            def pytest_runtest_makereport(item, call):
                outcome = yield
                report = outcome.get_result()
                if report.when == "call" and report.failed:
                    d = item.funcargs.get("driver")
                    if d:
                        ss = Path(__file__).parent / "screenshots"
                        ss.mkdir(exist_ok=True)
                        d.save_screenshot(str(ss / f"FAIL_{{item.name}}.png"))
        ''')
        (out / "conftest.py").write_text(code, encoding="utf-8")

    def _write_pytest_ini(self, out: Path) -> None:
        (out / "pytest.ini").write_text(textwrap.dedent("""\
            [pytest]
            testpaths = tests
            python_files = test_*.py
            python_classes = Test*
            python_functions = test_*
            addopts = -v --tb=short
            markers =
                smoke: smoke tests
                negative: negative tests
                boundary: boundary tests
                security: security tests
        """), encoding="utf-8")

    def _write_requirements(self, out: Path) -> None:
        (out / "requirements.txt").write_text(textwrap.dedent("""\
            Appium-Python-Client>=4.0.0
            pytest>=8.0.0
            selenium>=4.20.0
        """), encoding="utf-8")
