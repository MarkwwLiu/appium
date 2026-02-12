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
        """註冊內建恢復策略（Android + iOS 雙平台）"""

        @self.register("permission_dialog", priority=10)
        def _handle_permission(driver) -> bool:
            """處理權限彈窗（Android + iOS）"""
            # Android 權限按鈕
            android_buttons = [
                "com.android.packageinstaller:id/permission_allow_button",
                "com.android.permissioncontroller:id/permission_allow_button",
                "com.android.permissioncontroller:id/permission_allow_foreground_only_button",
                "com.android.packageinstaller:id/permission_allow_always_button",
            ]
            for btn_id in android_buttons:
                try:
                    el = driver.find_element(AppiumBy.ID, btn_id)
                    if el.is_displayed():
                        el.click()
                        logger.info("[Recovery] 已點擊 Android 權限允許按鈕")
                        return True
                except Exception:
                    continue

            # iOS 系統權限彈窗（通知、位置、相機、麥克風等）
            ios_allow_labels = [
                "Allow", "允許", "OK", "好",
                "Allow While Using App", "使用 App 時允許",
                "Allow Once", "允許一次",
            ]
            for label in ios_allow_labels:
                try:
                    el = driver.find_element(
                        AppiumBy.ACCESSIBILITY_ID, label
                    )
                    if el.is_displayed():
                        el.click()
                        logger.info(f"[Recovery] 已點擊 iOS 權限按鈕: {label}")
                        return True
                except Exception:
                    continue

            return False

        @self.register("anr_dialog", priority=15)
        def _handle_anr(driver) -> bool:
            """處理 ANR 對話框（Android）"""
            anr_texts = ["等待", "Wait", "Close app", "關閉應用程式", "关闭应用"]
            xpath_parts = " or ".join(f'@text="{t}"' for t in anr_texts)
            try:
                wait_btn = driver.find_element(
                    AppiumBy.XPATH,
                    f'//*[{xpath_parts}]'
                )
                if wait_btn.is_displayed():
                    wait_btn.click()
                    logger.info("[Recovery] 已點擊 ANR 等待/關閉按鈕")
                    return True
            except Exception:
                pass
            return False

        @self.register("system_dialog", priority=20)
        def _handle_system_dialog(driver) -> bool:
            """處理各種系統彈窗 — 多語系支援（中/英/日/韓）"""
            dismiss_texts = [
                # 英文
                "Cancel", "No thanks", "Dismiss", "Close", "OK",
                "Got it", "Not Now", "Later", "Skip", "Deny",
                # 繁體中文
                "取消", "不用了", "關閉", "確定", "稍後", "略過",
                # 簡體中文
                "关闭", "确定", "稍后", "跳过",
                # 日文
                "キャンセル", "閉じる", "後で", "スキップ",
                # 韓文
                "취소", "닫기", "나중에", "건너뛰기",
            ]
            seen: set[str] = set()
            unique_texts: list[str] = []
            for t in dismiss_texts:
                if t not in seen:
                    seen.add(t)
                    unique_texts.append(t)

            for text in unique_texts:
                try:
                    # @text 用於 Android, @label 用於 iOS
                    el = driver.find_element(
                        AppiumBy.XPATH, f'//*[@text="{text}" or @label="{text}"]'
                    )
                    if el.is_displayed():
                        el.click()
                        logger.info(f"[Recovery] 已關閉系統彈窗: {text}")
                        return True
                except Exception:
                    continue

            # Android 特定 resource-id（取消按鈕）
            try:
                el = driver.find_element(AppiumBy.ID, "android:id/button2")
                if el.is_displayed():
                    el.click()
                    logger.info("[Recovery] 已點擊 android:id/button2 (取消)")
                    return True
            except Exception:
                pass

            return False

        @self.register("ios_alert", priority=25)
        def _handle_ios_alert(driver) -> bool:
            """處理 iOS 系統 alert（使用 Appium 內建 API）"""
            try:
                alert_text = driver.switch_to.alert.text
                if alert_text:
                    driver.switch_to.alert.accept()
                    logger.info(f"[Recovery] 已接受 iOS alert: {alert_text}")
                    return True
            except Exception:
                pass
            try:
                driver.switch_to.alert.dismiss()
                logger.info("[Recovery] 已關閉 iOS alert (dismiss)")
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

        @self.register("crash_restart", priority=40)
        def _handle_crash(driver) -> bool:
            """App crash 後重啟（Android + iOS）"""
            crash_indicators = [
                '//*[contains(@text,"has stopped")]',
                '//*[contains(@text,"已停止")]',
                '//*[contains(@text,"keeps stopping")]',
                '//*[contains(@text,"持續停止")]',
                '//*[contains(@label,"Problem Report")]',
            ]
            for xpath in crash_indicators:
                try:
                    el = driver.find_element(AppiumBy.XPATH, xpath)
                    if el.is_displayed():
                        close_xpaths = [
                            '//*[@text="Close" or @text="關閉" or @text="OK" or @text="確定"]',
                            '//*[@label="Close" or @label="OK"]',
                        ]
                        for close_xpath in close_xpaths:
                            try:
                                close = driver.find_element(
                                    AppiumBy.XPATH, close_xpath
                                )
                                close.click()
                                break
                            except Exception:
                                continue

                        app_id = driver.capabilities.get(
                            "appPackage",
                            driver.capabilities.get("bundleId", "")
                        )
                        if app_id:
                            driver.activate_app(app_id)
                            time.sleep(3)
                            logger.info("[Recovery] App crash → 已重啟")
                            return True
                except Exception:
                    continue
            return False

        @self.register("back_button", priority=50)
        def _handle_back(driver) -> bool:
            """按返回鍵嘗試恢復"""
            try:
                driver.back()
                time.sleep(1)
                source = driver.page_source
                if source and len(source) > 100:
                    logger.info("[Recovery] 已按返回鍵")
                    return True
            except Exception:
                pass
            return False


# 全域 singleton
recovery_manager = RecoveryManager()
