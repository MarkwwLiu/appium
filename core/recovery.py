"""
Recovery Manager — 自動從異常狀態恢復

測試過程中可能遇到：
- App crash → 重啟 App
- 系統彈窗（權限、更新、廣告）→ 自動關閉
- ANR 對話框 → 點擊等待/關閉
- 非預期頁面 → 返回到已知頁面
- WebView 卡死 → 切回 Native

Recovery 在每次 Page 操作失敗時自動嘗試，
也可以手動調用或搭配 Plugin/Middleware 使用。

用法：
    from core.recovery import recovery_manager

    # 自動模式（已整合進 Middleware）
    # 操作失敗 → 自動嘗試恢復 → 重試操作

    # 手動調用
    recovery_manager.try_recover(driver)

    # 註冊自訂恢復策略
    @recovery_manager.register("my_dialog")
    def handle_my_dialog(driver):
        # 關閉自訂 dialog
        ...
        return True  # 已恢復
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from appium.webdriver.common.appiumby import AppiumBy

from utils.logger import logger


@dataclass
class RecoveryRecord:
    """恢復記錄"""
    strategy_name: str
    success: bool
    timestamp: float = field(default_factory=time.time)
    detail: str = ""


class RecoveryManager:
    """
    自動恢復管理器

    內建策略（按優先序）：
    1. 系統權限彈窗
    2. ANR 對話框
    3. 系統更新/評價彈窗
    4. App crash 重啟
    5. 返回鍵恢復

    可註冊自訂策略。
    """

    def __init__(self):
        self._strategies: list[tuple[str, int, Callable]] = []
        self._history: list[RecoveryRecord] = []
        self.enabled = True
        self.max_attempts = 3
        self._register_defaults()

    def register(self, name: str, priority: int = 50):
        """
        註冊恢復策略。可當 decorator。

        Args:
            name: 策略名稱
            priority: 優先序，數字小先執行

        策略函式簽名: (driver) -> bool
            回傳 True 表示已恢復成功。
        """
        def _decorator(fn: Callable) -> Callable:
            self._strategies.append((name, priority, fn))
            self._strategies.sort(key=lambda x: x[1])
            logger.debug(f"Recovery 策略已註冊: {name} (priority={priority})")
            return fn
        return _decorator

    def try_recover(self, driver) -> bool:
        """
        嘗試所有恢復策略。

        Returns:
            True = 恢復成功，False = 所有策略都失敗
        """
        if not self.enabled:
            return False

        for attempt in range(self.max_attempts):
            for name, _, strategy in self._strategies:
                try:
                    recovered = strategy(driver)
                    record = RecoveryRecord(
                        strategy_name=name,
                        success=bool(recovered),
                    )
                    self._history.append(record)

                    if recovered:
                        logger.info(
                            f"[Recovery] 成功恢復: {name} "
                            f"(第 {attempt + 1} 次嘗試)"
                        )
                        time.sleep(1)  # 等畫面穩定
                        return True
                except Exception as e:
                    logger.debug(f"[Recovery] {name} 執行失敗: {e}")

        logger.warning("[Recovery] 所有恢復策略都失敗")
        return False

    def get_history(self, limit: int = 20) -> list[RecoveryRecord]:
        return self._history[-limit:]

    @property
    def stats(self) -> dict:
        total = len(self._history)
        success = sum(1 for r in self._history if r.success)
        return {
            "total_attempts": total,
            "success": success,
            "fail": total - success,
            "strategies": [name for name, _, _ in self._strategies],
        }

    # ── 內建策略 ──

    def _register_defaults(self):
        """註冊內建恢復策略"""

        @self.register("permission_dialog", priority=10)
        def _handle_permission(driver) -> bool:
            """處理 Android 權限彈窗"""
            permission_buttons = [
                "com.android.packageinstaller:id/permission_allow_button",
                "com.android.permissioncontroller:id/permission_allow_button",
                "com.android.permissioncontroller:id/permission_allow_foreground_only_button",
                "com.android.packageinstaller:id/permission_allow_always_button",
            ]
            for btn_id in permission_buttons:
                try:
                    el = driver.find_element(AppiumBy.ID, btn_id)
                    if el.is_displayed():
                        el.click()
                        logger.info("[Recovery] 已點擊權限允許按鈕")
                        return True
                except Exception:
                    continue
            return False

        @self.register("anr_dialog", priority=15)
        def _handle_anr(driver) -> bool:
            """處理 ANR 對話框"""
            try:
                # "等待" 或 "關閉應用程式"
                wait_btn = driver.find_element(
                    AppiumBy.XPATH,
                    '//*[@text="等待" or @text="Wait" or @text="等待"]'
                )
                if wait_btn.is_displayed():
                    wait_btn.click()
                    logger.info("[Recovery] 已點擊 ANR 等待按鈕")
                    return True
            except Exception:
                pass
            return False

        @self.register("system_dialog", priority=20)
        def _handle_system_dialog(driver) -> bool:
            """處理各種系統彈窗（更新、評價等）"""
            dismiss_patterns = [
                '//*[@text="取消" or @text="Cancel" or @text="稍後"]',
                '//*[@text="不用了" or @text="No thanks" or @text="略過"]',
                '//*[@text="關閉" or @text="Close" or @text="Dismiss"]',
                '//*[@text="OK" or @text="確定" or @text="Got it"]',
                '//*[@resource-id="android:id/button2"]',  # 通常是取消
            ]
            for xpath in dismiss_patterns:
                try:
                    el = driver.find_element(AppiumBy.XPATH, xpath)
                    if el.is_displayed():
                        el.click()
                        logger.info(f"[Recovery] 已關閉系統彈窗: {el.text}")
                        return True
                except Exception:
                    continue
            return False

        @self.register("crash_restart", priority=40)
        def _handle_crash(driver) -> bool:
            """App crash 後重啟"""
            try:
                # 檢查是否有 "has stopped" 或 "已停止"
                crash_indicators = [
                    '//*[contains(@text,"has stopped")]',
                    '//*[contains(@text,"已停止")]',
                    '//*[contains(@text,"keeps stopping")]',
                    '//*[contains(@text,"持續停止")]',
                ]
                for xpath in crash_indicators:
                    try:
                        el = driver.find_element(AppiumBy.XPATH, xpath)
                        if el.is_displayed():
                            # 點關閉
                            try:
                                close = driver.find_element(
                                    AppiumBy.XPATH,
                                    '//*[@text="Close" or @text="關閉" or @text="OK" or @text="確定"]'
                                )
                                close.click()
                            except Exception:
                                pass
                            # 重啟 App
                            driver.activate_app(
                                driver.capabilities.get(
                                    "appPackage",
                                    driver.capabilities.get("bundleId", "")
                                )
                            )
                            time.sleep(3)
                            logger.info("[Recovery] App crash → 已重啟")
                            return True
                    except Exception:
                        continue
            except Exception:
                pass
            return False

        @self.register("back_button", priority=50)
        def _handle_back(driver) -> bool:
            """按返回鍵嘗試恢復"""
            try:
                driver.back()
                time.sleep(1)
                # 檢查是否還在 App 中
                source = driver.page_source
                if source and len(source) > 100:
                    logger.info("[Recovery] 已按返回鍵")
                    return True
            except Exception:
                pass
            return False

        @self.register("webview_escape", priority=35)
        def _handle_webview(driver) -> bool:
            """WebView 卡住時切回 Native"""
            try:
                context = driver.context
                if context and "WEBVIEW" in context.upper():
                    driver.switch_to.context("NATIVE_APP")
                    logger.info("[Recovery] 已從 WebView 切回 Native")
                    return True
            except Exception:
                pass
            return False


# 全域 singleton
recovery_manager = RecoveryManager()
