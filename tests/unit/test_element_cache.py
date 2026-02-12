"""
core.element_cache 單元測試
驗證快取的 TTL、LRU 淘汰、stale 檢測、thread-local 隔離。
"""

import threading
import time
from unittest.mock import MagicMock, PropertyMock

import pytest

from core.element_cache import ElementCache


def _make_element(displayed=True, enabled=True):
    """建立 mock WebElement"""
    el = MagicMock()
    el.is_displayed.return_value = displayed
    el.is_enabled.return_value = enabled
    return el


class TestElementCacheBasic:
    """基本 get / put / invalidate / clear"""

    def setup_method(self):
        self.cache = ElementCache(ttl=10.0, max_size=5)

    def test_put_and_get(self):
        el = _make_element()
        loc = ("id", "btn_login")
        self.cache.put(loc, el)
        assert self.cache.get(loc) is el

    def test_get_miss(self):
        assert self.cache.get(("id", "nonexistent")) is None

    def test_invalidate(self):
        el = _make_element()
        loc = ("id", "test")
        self.cache.put(loc, el)
        self.cache.invalidate(loc)
        assert self.cache.get(loc) is None

    def test_clear(self):
        for i in range(3):
            self.cache.put(("id", f"el_{i}"), _make_element())
        assert self.cache.size == 3
        self.cache.clear()
        assert self.cache.size == 0

    def test_disabled(self):
        self.cache.enabled = False
        el = _make_element()
        self.cache.put(("id", "test"), el)
        assert self.cache.get(("id", "test")) is None


class TestElementCacheTTL:
    """TTL 過期測試"""

    def test_ttl_expiry(self):
        cache = ElementCache(ttl=0.1, max_size=10)
        el = _make_element()
        loc = ("id", "test")
        cache.put(loc, el)
        assert cache.get(loc) is el  # 立即取得

        time.sleep(0.15)
        assert cache.get(loc) is None  # 已過期


class TestElementCacheLRU:
    """LRU 淘汰測試"""

    def test_max_size_eviction(self):
        cache = ElementCache(ttl=60.0, max_size=3)
        for i in range(4):
            cache.put(("id", f"el_{i}"), _make_element())
            time.sleep(0.01)  # 確保 created_at 有差異
        # 最舊的 el_0 應被淘汰
        assert cache.size == 3
        assert cache.get(("id", "el_0")) is None


class TestElementCacheStale:
    """Stale element 檢測"""

    def test_stale_element_removed(self):
        cache = ElementCache(ttl=60.0)
        el = _make_element()
        el.is_displayed.side_effect = Exception("StaleElementReference")
        el.is_enabled.side_effect = Exception("StaleElementReference")
        loc = ("id", "test")
        cache.put(loc, el)
        assert cache.get(loc) is None  # stale → 回傳 None


class TestElementCacheStats:
    """統計功能"""

    def test_hit_miss_tracking(self):
        cache = ElementCache(ttl=60.0)
        el = _make_element()
        loc = ("id", "test")

        cache.get(loc)  # miss
        cache.put(loc, el)
        cache.get(loc)  # hit

        stats = cache.stats
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5


class TestElementCacheThreadIsolation:
    """Thread-local 隔離測試"""

    def test_threads_have_separate_caches(self):
        cache = ElementCache(ttl=60.0)
        results = {}

        def thread_fn(thread_id):
            loc = ("id", f"el_{thread_id}")
            el = _make_element()
            cache.put(loc, el)
            results[thread_id] = cache.size

        t1 = threading.Thread(target=thread_fn, args=("t1",))
        t2 = threading.Thread(target=thread_fn, args=("t2",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # 每個執行緒只應有 1 個元素（互相隔離）
        assert results["t1"] == 1
        assert results["t2"] == 1
