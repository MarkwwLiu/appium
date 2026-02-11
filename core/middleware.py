"""
Middleware 層 — Page 操作前後攔截

類似 Express.js 的 middleware 概念：
每個操作 (click, input, get_text) 都經過 middleware 鏈。
可以在操作前後做任何事：log、截圖、等待、重試、快取...

用法：
    from core.middleware import middleware_chain

    # 加入 middleware
    @middleware_chain.use
    def log_actions(context, next_fn):
        print(f"開始: {context['action']} on {context['locator']}")
        result = next_fn()  # 執行下一層
        print(f"完成: {context['action']}")
        return result

    # 有條件的 middleware
    @middleware_chain.use_if(lambda ctx: ctx["action"] == "click")
    def click_screenshot(context, next_fn):
        result = next_fn()
        # click 後截圖
        return result

中介層順序：按 use() 註冊順序執行，最後才到真正的操作。
"""

from __future__ import annotations

from typing import Any, Callable

from utils.logger import logger


class MiddlewareContext:
    """傳遞給每個 middleware 的上下文"""

    def __init__(self, page, action: str, locator: tuple,
                 args: tuple = (), kwargs: dict | None = None):
        self.page = page
        self.action = action          # "click", "input_text", "get_text" 等
        self.locator = locator
        self.args = args
        self.kwargs = kwargs or {}
        self.extra: dict[str, Any] = {}   # middleware 間傳遞自訂資料
        self.skip = False              # 設 True 跳過後續 middleware + 操作

    def __getitem__(self, key):
        return getattr(self, key, self.extra.get(key))

    def __setitem__(self, key, value):
        self.extra[key] = value


# Middleware 函式簽名: (context: MiddlewareContext, next_fn: Callable) -> Any
MiddlewareFn = Callable[[MiddlewareContext, Callable], Any]


class MiddlewareChain:
    """Middleware 鏈管理器"""

    def __init__(self):
        self._middlewares: list[tuple[MiddlewareFn, Callable | None]] = []

    def use(self, fn: MiddlewareFn | None = None) -> MiddlewareFn | Callable:
        """
        加入 middleware。可當 decorator 或直接呼叫。

        Args:
            fn: middleware 函式 (context, next_fn) -> Any
        """
        def _register(middleware: MiddlewareFn) -> MiddlewareFn:
            self._middlewares.append((middleware, None))
            logger.debug(f"Middleware 已註冊: {middleware.__name__}")
            return middleware

        if fn is not None:
            return _register(fn)
        return _register

    def use_if(self, condition: Callable[[MiddlewareContext], bool]):
        """
        有條件的 middleware，只在 condition 為 True 時執行。

        用法:
            @middleware_chain.use_if(lambda ctx: ctx.action == "click")
            def click_only(context, next_fn):
                ...
        """
        def _decorator(middleware: MiddlewareFn) -> MiddlewareFn:
            self._middlewares.append((middleware, condition))
            return middleware
        return _decorator

    def remove(self, fn: MiddlewareFn) -> None:
        """移除 middleware"""
        self._middlewares = [
            (m, c) for m, c in self._middlewares if m is not fn
        ]

    def clear(self) -> None:
        """清除所有 middleware"""
        self._middlewares.clear()

    def execute(self, context: MiddlewareContext,
                core_fn: Callable) -> Any:
        """
        執行 middleware 鏈 + 核心操作。

        依序經過每個 middleware，最後執行 core_fn（實際操作）。
        """
        if context.skip:
            return None

        # 收集適用的 middleware
        applicable = []
        for mw, condition in self._middlewares:
            if condition is None or condition(context):
                applicable.append(mw)

        # 建構 chain（從後往前包）
        def _final():
            if context.skip:
                return None
            return core_fn()

        chain = _final
        for mw in reversed(applicable):
            chain = _make_next(mw, context, chain)

        return chain()

    @property
    def count(self) -> int:
        return len(self._middlewares)


def _make_next(middleware: MiddlewareFn, context: MiddlewareContext,
               next_fn: Callable) -> Callable:
    """建構 chain 節點（避免閉包變數問題）"""
    def _wrapper():
        return middleware(context, next_fn)
    return _wrapper


# 全域 singleton
middleware_chain = MiddlewareChain()
