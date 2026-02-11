"""
Timing Plugin — 操作耗時追蹤

記錄每個 Page 操作的執行時間，方便找出效能瓶頸。
超過閾值自動警告。
"""

import time
from collections import defaultdict

from core.plugin_manager import Plugin
from utils.logger import logger


class TimingPlugin(Plugin):
    """追蹤 Page 操作耗時"""

    name = "timing"
    version = "1.0.0"
    description = "記錄每個操作的耗時，超過閾值自動警告"

    def __init__(self, warn_threshold: float = 5.0):
        """
        Args:
            warn_threshold: 超過此秒數發出警告
        """
        self.warn_threshold = warn_threshold
        self.records: list[dict] = []
        self._action_timers: dict[int, float] = {}

    def on_register(self) -> None:
        from core.middleware import middleware_chain

        warn_threshold = self.warn_threshold
        records = self.records

        @middleware_chain.use
        def timing_middleware(context, next_fn):
            start = time.time()
            try:
                result = next_fn()
                return result
            finally:
                elapsed = time.time() - start
                record = {
                    "action": context.action,
                    "locator": str(context.locator),
                    "elapsed": elapsed,
                }
                records.append(record)

                if elapsed > warn_threshold:
                    logger.warning(
                        f"[Timing] {context.action} 耗時 {elapsed:.2f}s "
                        f"(超過 {warn_threshold}s): {context.locator}"
                    )

    def get_report(self) -> dict:
        """取得耗時報告"""
        if not self.records:
            return {"total": 0, "avg": 0, "max": 0, "slowest": []}

        times = [r["elapsed"] for r in self.records]
        slowest = sorted(self.records, key=lambda r: r["elapsed"], reverse=True)[:5]

        return {
            "total": len(self.records),
            "avg": sum(times) / len(times),
            "max": max(times),
            "slowest": slowest,
        }
