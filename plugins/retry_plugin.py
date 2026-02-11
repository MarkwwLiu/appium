"""
Retry Plugin — 操作失敗自動重試

當 Page 操作 (click, input_text) 失敗時，自動重試 N 次。
適用於網路不穩、畫面載入延遲等場景。
"""

import time

from core.plugin_manager import Plugin
from utils.logger import logger


class RetryPlugin(Plugin):
    """操作失敗自動重試"""

    name = "retry"
    version = "1.0.0"
    description = "Page 操作失敗時自動重試"

    def __init__(self, max_retries: int = 2, delay: float = 1.0):
        self.max_retries = max_retries
        self.delay = delay

    def on_register(self) -> None:
        logger.info(f"[RetryPlugin] 重試次數: {self.max_retries}, 間隔: {self.delay}s")

        # 註冊 middleware 而非 hook（middleware 能攔截並重試）
        from core.middleware import middleware_chain

        @middleware_chain.use
        def retry_middleware(context, next_fn):
            last_error = None
            for attempt in range(1 + self.max_retries):
                try:
                    return next_fn()
                except Exception as e:
                    last_error = e
                    if attempt < self.max_retries:
                        logger.warning(
                            f"[Retry] {context.action} 失敗 (第 {attempt + 1} 次)，"
                            f"{self.delay}s 後重試: {e}"
                        )
                        time.sleep(self.delay)
                    else:
                        logger.error(
                            f"[Retry] {context.action} 重試 {self.max_retries} 次後仍失敗"
                        )
            raise last_error
