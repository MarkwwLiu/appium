"""
Event Bus — 事件發佈/訂閱系統

讓框架各模組可以在不直接耦合的情況下互相溝通。
Plugin、Middleware、Logger 都可以訂閱事件做事。

內建事件：
    driver.created       — Driver 建立後
    driver.quit          — Driver 關閉前
    page.action.before   — Page 操作前 (click, input 等)
    page.action.after    — Page 操作後
    page.action.error    — Page 操作失敗
    test.start           — 測試開始
    test.pass            — 測試通過
    test.fail            — 測試失敗
    screenshot.taken     — 截圖完成

用法：
    from core.event_bus import event_bus

    # 訂閱
    @event_bus.on("page.action.error")
    def on_error(event_data):
        print(f"操作失敗: {event_data}")

    # 發佈
    event_bus.emit("page.action.error", {"locator": ..., "error": ...})
"""

from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from utils.logger import logger


@dataclass
class Event:
    """事件物件"""
    name: str
    data: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""


class EventBus:
    """
    全域事件匯流排

    支援：
    - 精確訂閱: event_bus.on("page.action.error", handler)
    - 萬用字元:  event_bus.on("page.*", handler)        → 符合 page.xxx
    - 全域監聽:  event_bus.on("*", handler)              → 接收所有事件
    - 優先序:    event_bus.on("xxx", handler, priority=1) → 數字小先執行
    """

    def __init__(self):
        self._handlers: dict[str, list[tuple[int, Callable]]] = defaultdict(list)
        self._history: list[Event] = []
        self._max_history = 500
        self._lock = threading.Lock()

    def on(self, event_name: str, handler: Callable | None = None,
           priority: int = 10) -> Callable:
        """
        訂閱事件。可當 decorator 或直接呼叫。

        用法:
            # 作為 decorator
            @event_bus.on("test.fail")
            def handle_fail(event):
                ...

            # 直接呼叫
            event_bus.on("test.fail", my_handler, priority=1)
        """
        def _register(fn: Callable) -> Callable:
            with self._lock:
                self._handlers[event_name].append((priority, fn))
                self._handlers[event_name].sort(key=lambda x: x[0])
            return fn

        if handler is not None:
            _register(handler)
            return handler
        return _register

    def off(self, event_name: str, handler: Callable | None = None) -> None:
        """取消訂閱。不指定 handler 則移除該事件所有 handler。"""
        with self._lock:
            if handler is None:
                self._handlers.pop(event_name, None)
            else:
                self._handlers[event_name] = [
                    (p, h) for p, h in self._handlers[event_name] if h is not handler
                ]

    def emit(self, event_name: str, data: dict | None = None,
             source: str = "") -> Event:
        """發佈事件"""
        event = Event(name=event_name, data=data or {}, source=source)

        with self._lock:
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

        # 收集要執行的 handlers
        to_call: list[tuple[int, Callable]] = []

        with self._lock:
            # 精確比對
            if event_name in self._handlers:
                to_call.extend(self._handlers[event_name])

            # 萬用字元: "page.*" 比對 "page.action.error"
            for pattern, handlers in self._handlers.items():
                if pattern == event_name:
                    continue  # 已加過
                if pattern == "*":
                    to_call.extend(handlers)
                elif pattern.endswith(".*"):
                    prefix = pattern[:-2]
                    if event_name.startswith(prefix + "."):
                        to_call.extend(handlers)

        # 按優先序排序並執行
        to_call.sort(key=lambda x: x[0])
        for _, handler in to_call:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler 錯誤 [{event_name}]: {e}")

        return event

    def once(self, event_name: str, handler: Callable,
             priority: int = 10) -> None:
        """訂閱一次性事件，觸發後自動取消"""
        def _wrapper(event: Event):
            handler(event)
            self.off(event_name, _wrapper)
        self.on(event_name, _wrapper, priority)

    def get_history(self, event_name: str = "",
                    limit: int = 50) -> list[Event]:
        """查詢事件歷史"""
        with self._lock:
            if event_name:
                filtered = [e for e in self._history if e.name == event_name]
            else:
                filtered = list(self._history)
        return filtered[-limit:]

    def clear(self) -> None:
        """清除所有訂閱與歷史"""
        with self._lock:
            self._handlers.clear()
            self._history.clear()

    @property
    def registered_events(self) -> list[str]:
        """列出所有已註冊的事件名稱"""
        with self._lock:
            return list(self._handlers.keys())


# 全域 singleton
event_bus = EventBus()
