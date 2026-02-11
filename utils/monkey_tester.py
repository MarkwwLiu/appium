"""
Monkey Testing — 隨機壓力測試

對 App 執行隨機操作（點擊、滑動、返回、輸入），找出 crash 和 ANR。
搭配 RecoveryManager 自動處理異常，記錄問題現場。

用法：
    from utils.monkey_tester import MonkeyTester

    monkey = MonkeyTester(driver)
    result = monkey.run(duration=120, actions_per_minute=30)
    print(result.summary)
    # → 執行 120秒, 共 60 動作, 2 次 crash, 3 次 recovery

    # 自訂動作權重
    monkey = MonkeyTester(driver, weights={
        "tap": 40, "swipe": 25, "back": 15, "input": 10, "rotate": 10
    })

    # 排除區域 (避免點到通知欄/導航列)
    monkey.exclude_region(y_max=100)   # 排除頂部 100px
    monkey.exclude_region(y_min=2400)  # 排除底部
"""

from __future__ import annotations

import random
import string
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from utils.logger import logger

if TYPE_CHECKING:
    from appium.webdriver import Remote as WebDriver


@dataclass
class ExcludeRegion:
    """排除區域"""
    x_min: int = 0
    y_min: int = 0
    x_max: int = 9999
    y_max: int = 9999


@dataclass
class MonkeyEvent:
    """單一 monkey 事件"""
    action: str
    timestamp: float
    details: dict = field(default_factory=dict)
    success: bool = True
    error: str = ""


@dataclass
class MonkeyResult:
    """Monkey 測試結果"""
    duration: float = 0.0
    total_actions: int = 0
    crashes: int = 0
    recoveries: int = 0
    errors: list[str] = field(default_factory=list)
    events: list[MonkeyEvent] = field(default_factory=list)

    @property
    def summary(self) -> str:
        """產生摘要文字"""
        return (
            f"Monkey 測試結果: "
            f"執行 {self.duration:.0f}秒, "
            f"共 {self.total_actions} 動作, "
            f"{self.crashes} 次 crash, "
            f"{self.recoveries} 次 recovery, "
            f"{len(self.errors)} 個錯誤"
        )


# 預設動作權重
DEFAULT_WEIGHTS = {
    "tap": 35,       # 隨機點擊
    "swipe": 25,     # 隨機滑動
    "back": 15,      # 按返回鍵
    "input": 10,     # 隨機輸入文字
    "rotate": 5,     # 旋轉螢幕
    "home": 5,       # 按 Home 鍵後回到 App
    "long_press": 5, # 長按
}


class MonkeyTester:
    """
    隨機壓力測試工具

    模擬使用者隨機操作，測試 App 的穩定性和異常處理。
    """

    def __init__(
        self,
        driver: "WebDriver",
        weights: dict[str, int] | None = None,
        seed: int | None = None,
    ):
        self._driver = driver
        self._weights = weights or DEFAULT_WEIGHTS.copy()
        self._excludes: list[ExcludeRegion] = []
        self._recovery = None

        # 可重現的隨機種子
        if seed is not None:
            random.seed(seed)

        # 取得螢幕尺寸
        size = driver.get_window_size()
        self._width = size["width"]
        self._height = size["height"]

        # 嘗試載入 RecoveryManager
        try:
            from core.recovery import recovery_manager
            self._recovery = recovery_manager
        except ImportError:
            pass

    def exclude_region(
        self,
        x_min: int = 0,
        y_min: int = 0,
        x_max: int = 9999,
        y_max: int = 9999,
    ) -> "MonkeyTester":
        """新增排除區域 (不會在此區域操作)"""
        self._excludes.append(ExcludeRegion(x_min, y_min, x_max, y_max))
        return self

    def run(
        self,
        duration: float = 60.0,
        actions_per_minute: int = 30,
        stop_on_crash: bool = False,
    ) -> MonkeyResult:
        """
        執行 monkey 測試

        Args:
            duration: 執行時間 (秒)
            actions_per_minute: 每分鐘動作數
            stop_on_crash: 遇到 crash 是否停止
        """
        result = MonkeyResult()
        interval = 60.0 / actions_per_minute
        start_time = time.time()
        action_pool = self._build_action_pool()

        logger.info(
            f"[Monkey] 開始: duration={duration}s, "
            f"rate={actions_per_minute}/min, seed={random.getstate()[1][0]}"
        )

        while time.time() - start_time < duration:
            action = random.choice(action_pool)
            event = self._execute_action(action)
            result.events.append(event)
            result.total_actions += 1

            if not event.success:
                result.errors.append(f"[{event.action}] {event.error}")
                # 嘗試恢復
                if self._try_recover():
                    result.recoveries += 1
                else:
                    result.crashes += 1
                    if stop_on_crash:
                        logger.warning("[Monkey] 遇到 crash，停止測試")
                        break

            time.sleep(interval)

        result.duration = time.time() - start_time
        logger.info(f"[Monkey] {result.summary}")
        return result

    # ── 動作執行 ──

    def _execute_action(self, action: str) -> MonkeyEvent:
        """執行單一隨機動作"""
        event = MonkeyEvent(action=action, timestamp=time.time())
        try:
            handler = getattr(self, f"_action_{action}", None)
            if handler:
                details = handler()
                event.details = details or {}
            else:
                event.error = f"未知動作: {action}"
                event.success = False
        except Exception as e:
            event.success = False
            event.error = str(e)
            logger.debug(f"[Monkey] {action} 失敗: {e}")
        return event

    def _action_tap(self) -> dict:
        """隨機點擊"""
        x, y = self._random_point()
        self._driver.tap([(x, y)], duration=100)
        return {"x": x, "y": y}

    def _action_swipe(self) -> dict:
        """隨機滑動"""
        sx, sy = self._random_point()
        ex, ey = self._random_point()
        self._driver.swipe(sx, sy, ex, ey, duration=300)
        return {"start": (sx, sy), "end": (ex, ey)}

    def _action_back(self) -> dict:
        """按返回鍵"""
        self._driver.back()
        return {}

    def _action_input(self) -> dict:
        """隨機輸入文字 (如果有焦點中的輸入框)"""
        text = "".join(random.choices(
            string.ascii_letters + string.digits + "!@#$%&",
            k=random.randint(1, 20),
        ))
        # 嘗試找到可輸入的元素
        try:
            focused = self._driver.switch_to.active_element
            if focused:
                focused.send_keys(text)
                return {"text": text}
        except Exception:
            pass
        return {"text": text, "skipped": True}

    def _action_rotate(self) -> dict:
        """旋轉螢幕"""
        current = self._driver.orientation
        new_orient = "LANDSCAPE" if current == "PORTRAIT" else "PORTRAIT"
        self._driver.orientation = new_orient
        time.sleep(0.5)
        # 轉回來
        self._driver.orientation = current
        return {"from": current, "to": new_orient}

    def _action_home(self) -> dict:
        """按 Home 後回到 App"""
        self._driver.press_keycode(3)  # KEYCODE_HOME
        time.sleep(1.0)
        self._driver.activate_app(self._driver.current_package)
        time.sleep(0.5)
        return {}

    def _action_long_press(self) -> dict:
        """長按"""
        x, y = self._random_point()
        self._driver.tap([(x, y)], duration=1500)
        return {"x": x, "y": y, "duration": 1500}

    # ── 輔助方法 ──

    def _random_point(self) -> tuple[int, int]:
        """產生隨機座標 (排除禁區)"""
        for _ in range(50):
            x = random.randint(10, self._width - 10)
            y = random.randint(10, self._height - 10)
            if not self._in_exclude(x, y):
                return x, y
        # fallback: 螢幕中心
        return self._width // 2, self._height // 2

    def _in_exclude(self, x: int, y: int) -> bool:
        """檢查座標是否在排除區域內"""
        for region in self._excludes:
            if (region.x_min <= x <= region.x_max
                    and region.y_min <= y <= region.y_max):
                return True
        return False

    def _build_action_pool(self) -> list[str]:
        """根據權重建立動作池"""
        pool = []
        for action, weight in self._weights.items():
            pool.extend([action] * weight)
        return pool

    def _try_recover(self) -> bool:
        """嘗試恢復 App"""
        if self._recovery:
            try:
                return self._recovery.try_recover(self._driver)
            except Exception:
                pass
        # fallback: 按返回鍵
        try:
            self._driver.back()
            time.sleep(0.5)
            return True
        except Exception:
            return False
