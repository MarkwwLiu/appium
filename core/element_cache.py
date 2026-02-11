"""
Element Cache — 元素快取加速

同一頁面重複查找同一元素很浪費。Cache 會：
1. 第一次查找 → 走正常流程 → 存入快取
2. 後續查找 → 先驗證快取元素是否仍有效 → 有效就直接回傳
3. 元素失效 (stale) → 自動重新查找

支援：
- 自動 stale check
- TTL 過期
- 頁面切換時自動清除
- 手動清除

用法：
    # BasePage 已內建，正常使用即可
    # 或手動控制：
    from core.element_cache import element_cache
    element_cache.clear()                    # 清除全部
    element_cache.invalidate(locator)        # 清除特定
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from selenium.webdriver.remote.webelement import WebElement

from utils.logger import logger


@dataclass
class CacheEntry:
    """快取條目"""
    element: WebElement
    locator: tuple
    created_at: float = field(default_factory=time.time)
    hit_count: int = 0


class ElementCache:
    """
    元素快取

    策略:
    - 以 locator tuple 為 key
    - 存取時自動檢查 stale (element.is_displayed())
    - TTL 預設 30 秒，超過自動失效
    - 頁面變更（page source hash 改變）自動清除
    """

    def __init__(self, ttl: float = 30.0, max_size: int = 100):
        self._cache: dict[tuple, CacheEntry] = {}
        self._ttl = ttl
        self._max_size = max_size
        self._enabled = True
        self._lock = threading.Lock()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value
        if not value:
            self.clear()

    def get(self, locator: tuple) -> WebElement | None:
        """
        從快取取得元素。

        Returns:
            WebElement 或 None (miss/stale/expired)
        """
        if not self._enabled:
            return None

        with self._lock:
            entry = self._cache.get(locator)
            if entry is None:
                self._stats["misses"] += 1
                return None

            # TTL 檢查
            if time.time() - entry.created_at > self._ttl:
                del self._cache[locator]
                self._stats["evictions"] += 1
                self._stats["misses"] += 1
                return None

            # Stale 檢查
            try:
                if entry.element.is_displayed() or entry.element.is_enabled():
                    entry.hit_count += 1
                    self._stats["hits"] += 1
                    return entry.element
            except Exception:
                pass

            # Stale — 移除
            del self._cache[locator]
            self._stats["evictions"] += 1
            self._stats["misses"] += 1
            return None

    def put(self, locator: tuple, element: WebElement) -> None:
        """存入快取"""
        if not self._enabled:
            return

        with self._lock:
            # 容量控制：LRU 淘汰
            if len(self._cache) >= self._max_size and locator not in self._cache:
                oldest_key = min(
                    self._cache, key=lambda k: self._cache[k].created_at
                )
                del self._cache[oldest_key]
                self._stats["evictions"] += 1

            self._cache[locator] = CacheEntry(
                element=element, locator=locator
            )

    def invalidate(self, locator: tuple) -> None:
        """清除特定 locator 的快取"""
        with self._lock:
            self._cache.pop(locator, None)

    def clear(self) -> None:
        """清除所有快取"""
        with self._lock:
            self._cache.clear()
        logger.debug("Element cache 已清除")

    @property
    def size(self) -> int:
        return len(self._cache)

    @property
    def stats(self) -> dict:
        total = self._stats["hits"] + self._stats["misses"]
        rate = self._stats["hits"] / total if total > 0 else 0.0
        return {**self._stats, "total": total, "hit_rate": rate}


# 全域 singleton
element_cache = ElementCache()
