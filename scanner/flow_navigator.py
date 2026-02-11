"""
FlowNavigator — 根據錄製的轉場記錄自動導航到指定頁面

核心邏輯：
1. 讀取 session.json（FlowRecorder 產出的轉場圖）
2. 建立頁面之間的有向圖
3. 用 BFS 找到從 current → target 的最短路徑
4. 依序執行路徑上的操作（填值 + 點擊）
5. 每步驗證是否到達預期頁面

用法：
    from scanner.flow_navigator import FlowNavigator

    nav = FlowNavigator(driver, "output/session.json")

    # 自動導航到 "register_page"
    success = nav.navigate_to("register_page")

    # 查看所有已知頁面
    print(nav.known_pages)

    # 查看路徑（不執行）
    path = nav.find_path("login_page", "home_page")
"""

from __future__ import annotations

import json
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from appium.webdriver.common.appiumby import AppiumBy

from scanner.analyzer import PageAnalyzer
from utils.logger import logger


@dataclass
class NavStep:
    """單步導航指令"""
    from_page: str
    to_page: str
    action: str
    field_values: dict[str, str] = field(default_factory=dict)


@dataclass
class NavResult:
    """導航結果"""
    success: bool
    target_page: str
    steps_taken: int
    actual_page: str = ""
    path: list[NavStep] = field(default_factory=list)
    error: str = ""


class FlowNavigator:
    """
    流程導航器 — 根據錄製的轉場圖自動導航

    建立有向圖後用 BFS 找最短路徑，然後依序執行操作。
    """

    def __init__(self, driver, session_path: str | Path):
        self.driver = driver
        self.analyzer = PageAnalyzer(driver)
        self._graph: dict[str, list[dict]] = {}  # page_name → [{to, action, values}]
        self._page_info: dict[str, dict] = {}    # page_name → snapshot info
        self._load_session(Path(session_path))

    def _load_session(self, path: Path) -> None:
        """從 session.json 載入轉場圖"""
        data = json.loads(path.read_text(encoding="utf-8"))

        # 建立頁面資訊
        for snap in data.get("snapshots", []):
            name = snap["page_name"]
            self._page_info[name] = snap

        # 建立轉場圖
        for t in data.get("transitions", []):
            from_page = t["from"]
            to_page = t["to"]
            if from_page == to_page:
                continue  # 跳過 same_page 轉場

            if from_page not in self._graph:
                self._graph[from_page] = []

            self._graph[from_page].append({
                "to": to_page,
                "action": t["action"],
                "values": t.get("values", {}),
            })

        logger.info(
            f"[Navigator] 載入 {len(self._page_info)} 頁面, "
            f"{sum(len(v) for v in self._graph.values())} 條轉場"
        )

    @property
    def known_pages(self) -> list[str]:
        """所有已知頁面名稱"""
        return sorted(self._page_info.keys())

    @property
    def graph_summary(self) -> dict[str, list[str]]:
        """轉場圖摘要：{from_page: [to_page, ...]}"""
        return {k: [e["to"] for e in v] for k, v in self._graph.items()}

    def find_path(self, from_page: str, to_page: str) -> list[NavStep] | None:
        """
        BFS 找最短路徑。

        Returns:
            NavStep 列表，或 None（無法到達）
        """
        if from_page == to_page:
            return []

        if from_page not in self._graph:
            return None

        # BFS
        visited = {from_page}
        queue: deque[tuple[str, list[NavStep]]] = deque()

        for edge in self._graph.get(from_page, []):
            step = NavStep(
                from_page=from_page,
                to_page=edge["to"],
                action=edge["action"],
                field_values=edge.get("values", {}),
            )
            if edge["to"] == to_page:
                return [step]
            queue.append((edge["to"], [step]))
            visited.add(edge["to"])

        while queue:
            current, path = queue.popleft()

            for edge in self._graph.get(current, []):
                if edge["to"] in visited:
                    continue

                step = NavStep(
                    from_page=current,
                    to_page=edge["to"],
                    action=edge["action"],
                    field_values=edge.get("values", {}),
                )
                new_path = path + [step]

                if edge["to"] == to_page:
                    return new_path

                visited.add(edge["to"])
                queue.append((edge["to"], new_path))

        return None

    def detect_current_page(self) -> str:
        """掃描當前頁面，回傳最可能的頁面名稱"""
        snap = self.analyzer.snapshot()
        return snap.inferred_name

    def navigate_to(
        self,
        target: str,
        from_page: str | None = None,
        max_retries: int = 2,
    ) -> NavResult:
        """
        自動導航到目標頁面。

        Args:
            target: 目標頁面名稱
            from_page: 起始頁面（None = 自動偵測）
            max_retries: 每步失敗最多重試次數

        Returns:
            NavResult
        """
        # 偵測當前頁面
        if from_page is None:
            from_page = self.detect_current_page()
            logger.info(f"[Navigator] 當前頁面: {from_page}")

        if from_page == target:
            logger.info(f"[Navigator] 已在目標頁面: {target}")
            return NavResult(
                success=True,
                target_page=target,
                steps_taken=0,
                actual_page=target,
            )

        # 找路徑
        path = self.find_path(from_page, target)
        if path is None:
            logger.warning(
                f"[Navigator] 找不到從 {from_page} 到 {target} 的路徑"
            )
            return NavResult(
                success=False,
                target_page=target,
                steps_taken=0,
                actual_page=from_page,
                error=f"找不到從 '{from_page}' 到 '{target}' 的路徑",
            )

        logger.info(
            f"[Navigator] 規劃路徑: {from_page}"
            + "".join(f" → {s.to_page}" for s in path)
        )

        # 依序執行
        steps_done = 0
        for step in path:
            success = self._execute_step(step, max_retries)
            if not success:
                actual = self.detect_current_page()
                logger.warning(
                    f"[Navigator] 步驟失敗: {step.action} "
                    f"(預期到 {step.to_page}，實際在 {actual})"
                )
                return NavResult(
                    success=False,
                    target_page=target,
                    steps_taken=steps_done,
                    actual_page=actual,
                    path=path,
                    error=f"步驟失敗: {step.action}",
                )
            steps_done += 1

        # 驗證最終頁面
        actual = self.detect_current_page()
        reached = actual == target

        if reached:
            logger.info(f"[Navigator] 成功到達: {target} ({steps_done} 步)")
        else:
            logger.warning(
                f"[Navigator] 預期到 {target}，但偵測為 {actual}"
            )

        return NavResult(
            success=reached,
            target_page=target,
            steps_taken=steps_done,
            actual_page=actual,
            path=path,
        )

    def _execute_step(self, step: NavStep, max_retries: int) -> bool:
        """執行單步導航"""
        for attempt in range(1 + max_retries):
            try:
                # 填入欄位值
                for var_name, value in step.field_values.items():
                    if not value:
                        continue
                    try:
                        # 嘗試多種定位策略
                        el = self._find_input(var_name)
                        if el:
                            el.clear()
                            el.send_keys(value)
                    except Exception:
                        pass

                # 執行動作（通常是 click_xxx）
                action = step.action
                if action.startswith("click_"):
                    btn_name = action[6:]  # 去掉 "click_" 前綴
                    btn = self._find_button(btn_name)
                    if btn:
                        btn.click()
                    else:
                        logger.warning(f"[Navigator] 找不到按鈕: {btn_name}")
                        if attempt >= max_retries:
                            return False
                        continue

                time.sleep(2)  # 等待頁面切換

                # 驗證是否到達目標
                current = self.detect_current_page()
                if current == step.to_page:
                    return True

                logger.debug(
                    f"[Navigator] 嘗試 {attempt + 1}: "
                    f"預期 {step.to_page}，實際 {current}"
                )
            except Exception as e:
                logger.debug(f"[Navigator] 嘗試 {attempt + 1} 失敗: {e}")

        return False

    def _find_input(self, var_name: str):
        """根據 var_name 找輸入框"""
        strategies = [
            (AppiumBy.ID, var_name),
            (AppiumBy.ACCESSIBILITY_ID, var_name),
            (AppiumBy.XPATH, f'//*[contains(@resource-id,"{var_name}")]'),
        ]
        for by, value in strategies:
            try:
                el = self.driver.find_element(by, value)
                if el.is_displayed():
                    return el
            except Exception:
                continue
        return None

    def _find_button(self, btn_name: str):
        """根據 btn_name 找按鈕"""
        strategies = [
            (AppiumBy.ID, btn_name),
            (AppiumBy.ACCESSIBILITY_ID, btn_name),
            (AppiumBy.XPATH, f'//*[contains(@resource-id,"{btn_name}")]'),
            (AppiumBy.XPATH, f'//*[contains(@text,"{btn_name}")]'),
            (AppiumBy.XPATH,
             f'//*[@clickable="true" and contains(@resource-id,"{btn_name}")]'),
        ]
        for by, value in strategies:
            try:
                el = self.driver.find_element(by, value)
                if el.is_displayed():
                    return el
            except Exception:
                continue
        return None
