"""
Recovery Plugin — 操作失敗時自動嘗試恢復再重試

整合 RecoveryManager 到 Middleware 鏈：
1. Page 操作失敗
2. Recovery Manager 嘗試恢復（關彈窗、重啟 App 等）
3. 恢復成功 → 重試原操作
4. 恢復失敗 → 拋出原始例外
"""

from core.plugin_manager import Plugin
from utils.logger import logger


class RecoveryPlugin(Plugin):
    """操作失敗時自動恢復 + 重試"""

    name = "recovery"
    version = "1.0.0"
    description = "操作失敗時自動嘗試恢復再重試"

    def __init__(self, max_recovery_retries: int = 1):
        self.max_recovery_retries = max_recovery_retries

    def on_register(self) -> None:
        logger.info(f"[RecoveryPlugin] 恢復重試次數: {self.max_recovery_retries}")

        from core.middleware import middleware_chain
        from core.recovery import recovery_manager

        @middleware_chain.use
        def recovery_middleware(context, next_fn):
            try:
                return next_fn()
            except Exception as original_error:
                # 嘗試恢復
                for attempt in range(self.max_recovery_retries):
                    driver = getattr(context.page, "driver", None)
                    if not driver:
                        break

                    logger.info(
                        f"[Recovery] {context.action} 失敗，"
                        f"嘗試恢復 (第 {attempt + 1} 次)..."
                    )
                    recovered = recovery_manager.try_recover(driver)

                    if recovered:
                        try:
                            return next_fn()
                        except Exception:
                            continue
                    else:
                        break

                # 恢復失敗，拋出原始例外
                raise original_error
