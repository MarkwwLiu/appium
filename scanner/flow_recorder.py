"""
FlowRecorder — 動作執行 + 頁面轉場記錄

核心邏輯：
1. 在頁面上執行一個動作 (fill + submit)
2. 動作後重新掃描頁面
3. 比對前後 page_source_hash → 判斷是否發生轉場
4. 記錄 Transition: {from_page, action, to_page, type}
5. 所有快照與轉場儲存下來，供後續產出使用

同時截圖保存每一步的畫面。
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

from appium.webdriver.common.appiumby import AppiumBy

from scanner.analyzer import (
    AnalyzedElement,
    PageAnalyzer,
    PageSnapshot,
    PageType,
)
from scanner.smart_test_data import SmartTestDataGenerator, TestCase
from utils.logger import logger


@dataclass
class Transition:
    """一次頁面轉場"""
    from_page: str           # 起始頁面 ID
    from_page_name: str
    action: str              # 什麼動作觸發的
    action_detail: dict = field(default_factory=dict)  # 填入了什麼值
    to_page: str = ""        # 目標頁面 ID
    to_page_name: str = ""
    transition_type: str = ""  # "page_change" / "same_page" / "error_shown" / "dialog"
    screenshot_before: str = ""
    screenshot_after: str = ""
    timestamp: str = ""


@dataclass
class FlowSession:
    """一次完整的掃描 session"""
    app_name: str = ""
    platform: str = "android"
    start_time: str = ""
    end_time: str = ""
    snapshots: list[PageSnapshot] = field(default_factory=list)
    transitions: list[Transition] = field(default_factory=list)
    test_cases: dict[str, list[TestCase]] = field(default_factory=dict)  # page_name → cases
    # 統計
    pages_discovered: int = 0
    total_elements: int = 0
    total_test_cases: int = 0


class FlowRecorder:
    """
    流程記錄器

    掃描 → 操作 → 重新掃描 → 記錄轉場 → 重複
    """

    def __init__(self, driver, output_dir: str | Path):
        self.driver = driver
        self.analyzer = PageAnalyzer(driver)
        self.output = Path(output_dir)
        self.output.mkdir(parents=True, exist_ok=True)
        self.ss_dir = self.output / "screenshots"
        self.ss_dir.mkdir(exist_ok=True)
        self.session = FlowSession(
            start_time=datetime.now().isoformat(),
        )
        self._seen_pages: dict[str, PageSnapshot] = {}  # hash → snapshot
        self._step = 0

    def scan_current_page(self) -> PageSnapshot:
        """
        掃描當前頁面，自動截圖，回傳分析結果。
        如果是新頁面會加到 session.snapshots。
        """
        self._step += 1

        # 截圖
        ss_path = self._screenshot(f"step_{self._step:03d}")

        # 分析
        snap = self.analyzer.snapshot()

        # 產生測試資料
        gen = SmartTestDataGenerator(snap)
        cases = gen.generate()
        self.session.test_cases[snap.inferred_name] = cases

        # 是否新頁面
        if snap.page_source_hash not in self._seen_pages:
            self._seen_pages[snap.page_source_hash] = snap
            self.session.snapshots.append(snap)
            logger.info(
                f"[Step {self._step}] 新頁面: {snap.inferred_name} "
                f"({snap.page_type.value}) — {len(cases)} 組測試資料"
            )
        else:
            logger.info(
                f"[Step {self._step}] 已知頁面: {snap.inferred_name}"
            )

        return snap

    def fill_and_submit(
        self,
        snapshot: PageSnapshot,
        field_values: dict[str, str] | None = None,
        label: str = "",
    ) -> tuple[PageSnapshot, Transition]:
        """
        在頁面填入欄位並提交，然後重新掃描。

        Args:
            snapshot: 當前頁面的快照
            field_values: {var_name: value}，None 時自動用正向有效值
            label: 這次操作的標籤

        Returns:
            (新頁面快照, 轉場記錄)
        """
        # 預設用正向有效值
        if field_values is None:
            from scanner.smart_test_data import _positive
            field_values = {}
            for inp in snapshot.inputs:
                positives = _positive(inp.field_semantic)
                if positives:
                    field_values[inp.var_name] = positives[0][1]

        # 截圖 before
        ss_before = self._screenshot(f"step_{self._step:03d}_before")

        # 填入欄位
        for inp in snapshot.inputs:
            value = field_values.get(inp.var_name, "")
            if value:
                try:
                    el = self._find_element(inp)
                    el.clear()
                    el.send_keys(value)
                    logger.info(f"  填入 {inp.var_name} = '{value}'")
                except Exception as e:
                    logger.warning(f"  填入 {inp.var_name} 失敗: {e}")

        # 點擊提交
        action_desc = label or "fill_and_submit"
        if snapshot.submit_button:
            try:
                btn = self._find_element(snapshot.submit_button)
                btn.click()
                logger.info(f"  點擊 {snapshot.submit_button.var_name}")
                action_desc = f"click_{snapshot.submit_button.var_name}"
            except Exception as e:
                logger.warning(f"  點擊提交按鈕失敗: {e}")

        # 等待畫面穩定
        time.sleep(2)

        # 截圖 after
        ss_after = self._screenshot(f"step_{self._step:03d}_after")

        # 重新掃描
        new_snap = self.scan_current_page()

        # 判斷轉場類型
        t_type = self._detect_transition_type(snapshot, new_snap)

        transition = Transition(
            from_page=snapshot.page_id,
            from_page_name=snapshot.inferred_name,
            action=action_desc,
            action_detail=field_values,
            to_page=new_snap.page_id,
            to_page_name=new_snap.inferred_name,
            transition_type=t_type,
            screenshot_before=str(ss_before),
            screenshot_after=str(ss_after),
            timestamp=datetime.now().isoformat(),
        )
        self.session.transitions.append(transition)

        logger.info(
            f"  轉場: {snapshot.inferred_name} → {new_snap.inferred_name} "
            f"({t_type})"
        )

        return new_snap, transition

    def click_button(
        self,
        snapshot: PageSnapshot,
        button: AnalyzedElement,
    ) -> tuple[PageSnapshot, Transition]:
        """點擊一個按鈕並記錄轉場"""
        ss_before = self._screenshot(f"step_{self._step:03d}_before")

        try:
            el = self._find_element(button)
            el.click()
            logger.info(f"  點擊 {button.var_name}")
        except Exception as e:
            logger.warning(f"  點擊 {button.var_name} 失敗: {e}")

        time.sleep(2)
        ss_after = self._screenshot(f"step_{self._step:03d}_after")
        new_snap = self.scan_current_page()
        t_type = self._detect_transition_type(snapshot, new_snap)

        transition = Transition(
            from_page=snapshot.page_id,
            from_page_name=snapshot.inferred_name,
            action=f"click_{button.var_name}",
            to_page=new_snap.page_id,
            to_page_name=new_snap.inferred_name,
            transition_type=t_type,
            screenshot_before=str(ss_before),
            screenshot_after=str(ss_after),
            timestamp=datetime.now().isoformat(),
        )
        self.session.transitions.append(transition)
        return new_snap, transition

    def save_session(self) -> Path:
        """儲存完整 session 結果到 JSON"""
        self.session.end_time = datetime.now().isoformat()
        self.session.pages_discovered = len(self.session.snapshots)
        self.session.total_elements = sum(
            len(s.all_elements) for s in self.session.snapshots
        )
        self.session.total_test_cases = sum(
            len(cases) for cases in self.session.test_cases.values()
        )

        # 轉為可 JSON 化的 dict
        data = {
            "app_name": self.session.app_name,
            "platform": self.session.platform,
            "start_time": self.session.start_time,
            "end_time": self.session.end_time,
            "pages_discovered": self.session.pages_discovered,
            "total_elements": self.session.total_elements,
            "total_test_cases": self.session.total_test_cases,
            "snapshots": [self._snap_to_dict(s) for s in self.session.snapshots],
            "transitions": [self._transition_to_dict(t) for t in self.session.transitions],
            "test_cases": {
                page: [self._case_to_dict(c) for c in cases]
                for page, cases in self.session.test_cases.items()
            },
        }

        path = self.output / "session.json"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"Session 已儲存: {path}")
        return path

    # ── 內部方法 ──

    def _find_element(self, el: AnalyzedElement):
        """根據 locator 找元素"""
        strategy_map = {
            "id": AppiumBy.ID,
            "accessibility_id": AppiumBy.ACCESSIBILITY_ID,
            "xpath": AppiumBy.XPATH,
        }
        by = strategy_map.get(el.locator_strategy, AppiumBy.ID)
        return self.driver.find_element(by, el.locator_value)

    def _screenshot(self, name: str) -> Path:
        """截圖"""
        path = self.ss_dir / f"{name}.png"
        try:
            self.driver.save_screenshot(str(path))
        except Exception:
            pass
        return path

    def _detect_transition_type(
        self, before: PageSnapshot, after: PageSnapshot
    ) -> str:
        """判斷轉場類型"""
        if before.page_source_hash == after.page_source_hash:
            return "same_page"

        # 頁面結構大幅改變 → page_change
        before_ids = {e.resource_id for e in before.all_elements if e.resource_id}
        after_ids = {e.resource_id for e in after.all_elements if e.resource_id}
        overlap = len(before_ids & after_ids)
        total = max(len(before_ids | after_ids), 1)

        if overlap / total < 0.3:
            return "page_change"

        # 出現了新的錯誤元素
        if after.error_indicator and not before.error_indicator:
            return "error_shown"

        # 元素數量大幅增加（可能彈 dialog）
        if len(after.all_elements) > len(before.all_elements) * 1.5:
            return "dialog"

        return "content_change"

    @staticmethod
    def _snap_to_dict(snap: PageSnapshot) -> dict:
        return {
            "page_id": snap.page_id,
            "page_name": snap.inferred_name,
            "page_type": snap.page_type.value,
            "page_type_confidence": snap.page_type_confidence,
            "activity": snap.activity,
            "timestamp": snap.timestamp,
            "inputs": [SmartTestDataGenerator._el_to_dict(e) for e in snap.inputs],
            "buttons": [SmartTestDataGenerator._el_to_dict(e) for e in snap.buttons],
            "texts_count": len(snap.texts),
            "checkboxes_count": len(snap.checkboxes),
            "submit_button": snap.submit_button.var_name if snap.submit_button else None,
            "error_indicator": snap.error_indicator.var_name if snap.error_indicator else None,
        }

    @staticmethod
    def _transition_to_dict(t: Transition) -> dict:
        return {
            "from": t.from_page_name,
            "action": t.action,
            "to": t.to_page_name,
            "type": t.transition_type,
            "values": t.action_detail,
            "timestamp": t.timestamp,
        }

    @staticmethod
    def _case_to_dict(c: TestCase) -> dict:
        return {
            "case_id": c.case_id,
            "category": c.category,
            "description": c.description,
            "fields": c.fields,
            "expected": c.expected,
            "tags": c.tags,
        }


# 補 SmartTestDataGenerator 缺的 static method
SmartTestDataGenerator._el_to_dict = staticmethod(lambda e: {
    "var_name": e.var_name,
    "element_type": e.element_type,
    "semantic": e.field_semantic.value if hasattr(e.field_semantic, 'value') else str(e.field_semantic),
    "locator": f"{e.locator_strategy}={e.locator_value}",
    "confidence": e.confidence,
})
