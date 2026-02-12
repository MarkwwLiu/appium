"""
core/middleware.py 單元測試

驗證 MiddlewareChain 的註冊、執行順序、條件過濾、skip 機制。
"""

import pytest

from core.middleware import MiddlewareChain, MiddlewareContext


@pytest.fixture
def chain():
    """每個測試取得一條乾淨的 middleware chain"""
    return MiddlewareChain()


@pytest.fixture
def ctx():
    """建立基本 context"""
    return MiddlewareContext(page=None, action="click", locator=("id", "btn"))


@pytest.mark.unit
class TestMiddlewareChainBasic:
    """基本功能"""

    @pytest.mark.unit
    def test_execute_core_fn(self, chain, ctx):
        """無 middleware 時直接執行 core_fn"""
        result = chain.execute(ctx, lambda: "done")
        assert result == "done"

    @pytest.mark.unit
    def test_use_registers(self, chain):
        """use() 能註冊 middleware"""
        def mw(context, next_fn):
            return next_fn()
        chain.use(mw)
        assert chain.count == 1

    @pytest.mark.unit
    def test_use_as_decorator(self, chain):
        """use() 可作為 decorator"""
        @chain.use
        def my_mw(context, next_fn):
            return next_fn()
        assert chain.count == 1

    @pytest.mark.unit
    def test_middleware_wraps_core(self, chain, ctx):
        """middleware 能包裹 core_fn"""
        log = []

        @chain.use
        def mw(context, next_fn):
            log.append("before")
            result = next_fn()
            log.append("after")
            return result

        chain.execute(ctx, lambda: log.append("core"))
        assert log == ["before", "core", "after"]

    @pytest.mark.unit
    def test_remove(self, chain):
        """remove() 能移除 middleware"""
        def mw(context, next_fn):
            return next_fn()
        chain.use(mw)
        assert chain.count == 1
        chain.remove(mw)
        assert chain.count == 0

    @pytest.mark.unit
    def test_clear(self, chain):
        """clear() 清除所有"""
        chain.use(lambda c, n: n())
        chain.use(lambda c, n: n())
        chain.clear()
        assert chain.count == 0


@pytest.mark.unit
class TestMiddlewareChainOrder:
    """執行順序"""

    @pytest.mark.unit
    def test_execution_order(self, chain, ctx):
        """middleware 按註冊順序執行"""
        order = []

        @chain.use
        def mw1(context, next_fn):
            order.append(1)
            return next_fn()

        @chain.use
        def mw2(context, next_fn):
            order.append(2)
            return next_fn()

        chain.execute(ctx, lambda: order.append("core"))
        assert order == [1, 2, "core"]


@pytest.mark.unit
class TestMiddlewareChainConditional:
    """條件式 middleware"""

    @pytest.mark.unit
    def test_use_if_matches(self, chain):
        """use_if 條件符合時執行"""
        log = []

        @chain.use_if(lambda ctx: ctx.action == "click")
        def click_only(context, next_fn):
            log.append("click_mw")
            return next_fn()

        ctx = MiddlewareContext(page=None, action="click", locator=("id", "x"))
        chain.execute(ctx, lambda: log.append("core"))
        assert "click_mw" in log

    @pytest.mark.unit
    def test_use_if_not_matches(self, chain):
        """use_if 條件不符時跳過"""
        log = []

        @chain.use_if(lambda ctx: ctx.action == "click")
        def click_only(context, next_fn):
            log.append("click_mw")
            return next_fn()

        ctx = MiddlewareContext(page=None, action="input_text", locator=("id", "x"))
        chain.execute(ctx, lambda: log.append("core"))
        assert "click_mw" not in log
        assert "core" in log


@pytest.mark.unit
class TestMiddlewareChainSkip:
    """skip 機制"""

    @pytest.mark.unit
    def test_skip_prevents_core(self, chain):
        """context.skip = True 時不執行 core_fn"""
        @chain.use
        def skipper(context, next_fn):
            context.skip = True
            return next_fn()

        ctx = MiddlewareContext(page=None, action="click", locator=("id", "x"))
        result = chain.execute(ctx, lambda: "should_not_run")
        assert result is None

    @pytest.mark.unit
    def test_skip_at_start(self, chain):
        """context 一開始就 skip"""
        ctx = MiddlewareContext(page=None, action="click", locator=("id", "x"))
        ctx.skip = True
        result = chain.execute(ctx, lambda: "no")
        assert result is None


@pytest.mark.unit
class TestMiddlewareContext:
    """MiddlewareContext 功能"""

    @pytest.mark.unit
    def test_getitem(self):
        """支援 dict 式讀取"""
        ctx = MiddlewareContext(page="p", action="click", locator=("id", "x"))
        assert ctx["action"] == "click"

    @pytest.mark.unit
    def test_setitem_extra(self):
        """支援 dict 式寫入 extra"""
        ctx = MiddlewareContext(page=None, action="click", locator=("id", "x"))
        ctx["my_key"] = 42
        assert ctx["my_key"] == 42
