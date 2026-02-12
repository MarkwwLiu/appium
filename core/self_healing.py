"""
Locator Self-Healing — 元素定位自動修復

當 locator 失效時，自動嘗試備選策略找到目標元素，並記錄修復結果。
整合進 Middleware 鏈，對測試程式碼透明。

流程：
    原 locator 失敗
    → 分析 page source 找候選元素
    → 依序嘗試備選策略 (text / content-desc / class+index / XPath)
    → 找到 → 記錄修復建議 + 回傳元素
    → 找不到 → 拋出原始例外

用法 (自動模式 — 推薦)：
    # 在 conftest.py 啟用 SelfHealingMiddleware 即可
    # 所有 BasePage 操作自動擁有 self-healing 能力

用法 (手動模式)：
    from core.self_healing import SelfHealer
    healer = SelfHealer(driver)
    element = healer.find_element(("id", "old_login_btn"))
    # 如果 ID 失效，會自動嘗試 text/content-desc 等策略
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from xml.etree import ElementTree

from utils.logger import logger

if TYPE_CHECKING:
    from appium.webdriver import Remote as WebDriver
    from selenium.webdriver.remote.webelement import WebElement


@dataclass
class HealRecord:
    """一次修復記錄"""
    original_locator: tuple[str, str]
    healed_locator: tuple[str, str]
    strategy: str
    page_context: str
    timestamp: float = field(default_factory=time.time)

    @property
    def suggestion(self) -> str:
        """產生修復建議"""
        by, value = self.healed_locator
        return f"建議更新 locator: ({by!r}, {value!r})  # 策略: {self.strategy}"


class SelfHealer:
    """
    元素定位自動修復器

    當原始 locator 找不到元素時，分析頁面結構嘗試其他定位策略。
    """

    # 歷史修復記錄 (類級別共享，限制容量避免記憶體洩漏)
    _heal_history: list[HealRecord] = []
    _max_history: int = 500

    def __init__(self, driver: "WebDriver"):
        self._driver = driver

    @classmethod
    def _append_history(cls, record: HealRecord) -> None:
        """安全地新增修復記錄（含容量控制）"""
        cls._heal_history.append(record)
        if len(cls._heal_history) > cls._max_history:
            cls._heal_history = cls._heal_history[-cls._max_history:]

    @property
    def heal_history(self) -> list[HealRecord]:
        """向後相容：取得修復歷史"""
        return self._heal_history

    def find_element(self, locator: tuple[str, str], timeout: float = 3.0) -> "WebElement":
        """
        嘗試找元素，失敗時自動修復

        Args:
            locator: (by, value) 定位器
            timeout: 原始定位的等待時間

        Returns:
            找到的元素

        Raises:
            原始例外 (如果自動修復也失敗)
        """
        by, value = locator

        # 先嘗試原始 locator
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            return WebDriverWait(self._driver, timeout).until(
                EC.presence_of_element_located(locator)
            )
        except Exception as original_error:
            logger.info(f"[SelfHealing] 原始 locator 失敗: {locator}, 嘗試自動修復...")

        # 取得頁面結構
        try:
            page_source = self._driver.page_source
        except Exception:
            raise original_error

        # 嘗試各種備選策略
        candidates = self._generate_candidates(locator, page_source)

        for strategy_name, alt_locator in candidates:
            try:
                element = self._driver.find_element(*alt_locator)
                if element.is_displayed():
                    # 修復成功！
                    record = HealRecord(
                        original_locator=locator,
                        healed_locator=alt_locator,
                        strategy=strategy_name,
                        page_context=self._get_page_context(),
                    )
                    SelfHealer._append_history(record)
                    logger.warning(
                        f"[SelfHealing] 自動修復成功!\n"
                        f"  原始: {locator}\n"
                        f"  修復: {alt_locator}\n"
                        f"  策略: {strategy_name}\n"
                        f"  {record.suggestion}"
                    )
                    return element
            except Exception:
                continue

        # 全部策略都失敗
        logger.error(f"[SelfHealing] 自動修復失敗，所有策略均無法找到元素: {locator}")
        raise original_error

    def _generate_candidates(
        self, original: tuple[str, str], page_source: str
    ) -> list[tuple[str, tuple[str, str]]]:
        """
        根據原始 locator 產生候選策略

        分析原始 locator 的意圖 (例如從 ID 推斷 text)，
        再從 page source 中搜尋可能匹配的元素。
        """
        by, value = original
        candidates: list[tuple[str, tuple[str, str]]] = []

        try:
            root = ElementTree.fromstring(page_source)
        except ElementTree.ParseError:
            return candidates

        # 從原始 value 提取關鍵字
        keywords = self._extract_keywords(value)

        # 策略 1: 用 text 屬性搜尋
        for kw in keywords:
            for elem in root.iter():
                text = elem.attrib.get("text", "")
                if kw.lower() in text.lower() and text:
                    candidates.append(
                        ("text_match", ("xpath", f'//*[@text="{text}"]'))
                    )

        # 策略 2: 用 content-desc 搜尋
        for kw in keywords:
            for elem in root.iter():
                desc = elem.attrib.get("content-desc", "")
                if kw.lower() in desc.lower() and desc:
                    candidates.append(
                        ("content_desc", ("accessibility id", desc))
                    )

        # 策略 3: 用 resource-id 做部分匹配
        if by != "id":
            for kw in keywords:
                for elem in root.iter():
                    rid = elem.attrib.get("resource-id", "")
                    if kw.lower() in rid.lower() and rid:
                        candidates.append(
                            ("partial_id", ("id", rid))
                        )

        # 策略 4: 用 class + text 組合
        for kw in keywords:
            for elem in root.iter():
                text = elem.attrib.get("text", "")
                cls = elem.tag
                if kw.lower() in text.lower() and text:
                    candidates.append(
                        ("class_text", ("xpath", f'//{cls}[@text="{text}"]'))
                    )

        # 策略 5: 用 hint 屬性 (Android EditText)
        for kw in keywords:
            for elem in root.iter():
                hint = elem.attrib.get("hint", "")
                if kw.lower() in hint.lower() and hint:
                    candidates.append(
                        ("hint_match", ("xpath", f'//*[@hint="{hint}"]'))
                    )

        # 去重
        seen = set()
        unique = []
        for name, loc in candidates:
            key = (name, loc)
            if key not in seen:
                seen.add(key)
                unique.append((name, loc))

        return unique

    def _extract_keywords(self, value: str) -> list[str]:
        """
        從 locator value 提取語意關鍵字

        例如：
            "com.app:id/btn_login" → ["login", "btn"]
            "//XCUIElementTypeButton[@name='Submit']" → ["submit"]
            "Login" → ["login"]
        """
        # 移除常見前綴
        clean = value
        clean = re.sub(r"com\.\w+:id/", "", clean)
        clean = re.sub(r"//\w+\[@\w+=['\"]?", "", clean)
        clean = re.sub(r"['\"\]]", "", clean)

        # 拆分
        parts = re.split(r"[_\-./\s]+", clean)
        # 過濾太短或太通用的詞
        stopwords = {"id", "btn", "tv", "et", "img", "iv", "ll", "rl", "fl", "view"}
        keywords = [p.lower() for p in parts if len(p) > 2 and p.lower() not in stopwords]

        return keywords or [clean.lower()]

    def _get_page_context(self) -> str:
        """取得當前頁面上下文 (activity 或 URL)"""
        try:
            return self._driver.current_activity or ""
        except Exception:
            return ""

    # ── 類方法 ──

    @classmethod
    def get_report(cls) -> str:
        """產生修復報告"""
        if not cls._heal_history:
            return "無自動修復記錄"

        lines = [
            "",
            "=" * 70,
            "  Locator 自動修復報告",
            "=" * 70,
        ]
        for i, record in enumerate(cls._heal_history, 1):
            lines.extend([
                f"\n  [{i}] {record.strategy}",
                f"      原始: {record.original_locator}",
                f"      修復: {record.healed_locator}",
                f"      {record.suggestion}",
            ])
        lines.append("=" * 70)
        return "\n".join(lines)

    @classmethod
    def clear_history(cls) -> None:
        """清除修復歷史"""
        cls._heal_history.clear()


class SelfHealingMiddleware:
    """
    Self-Healing Middleware

    接入 Middleware 鏈，讓所有 BasePage 操作自動擁有 self-healing 能力。
    """

    def __init__(self):
        self._healer_cache: dict[int, SelfHealer] = {}

    def __call__(self, context, next_fn):
        """Middleware 入口"""
        try:
            return next_fn()
        except Exception as e:
            # 只在元素找不到時嘗試修復
            error_name = type(e).__name__
            if "NoSuchElement" not in error_name and "TimeoutException" not in error_name:
                raise

            driver = getattr(context, "driver", None)
            locator = getattr(context, "locator", None)

            if not driver or not locator:
                raise

            # 取得或建立 healer
            driver_id = id(driver)
            if driver_id not in self._healer_cache:
                self._healer_cache[driver_id] = SelfHealer(driver)
            healer = self._healer_cache[driver_id]

            # 嘗試自動修復
            element = healer.find_element(locator, timeout=2.0)

            # 重新執行操作
            action = getattr(context, "action", "")
            kwargs = getattr(context, "kwargs", {})

            if action == "click":
                element.click()
                return element
            elif action == "input_text":
                element.clear()
                element.send_keys(kwargs.get("text", ""))
                return element
            elif action == "get_text":
                return element.text
            else:
                return element
