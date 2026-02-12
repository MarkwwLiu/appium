"""
core.event_bus 單元測試
驗證事件發佈/訂閱、萬用字元、優先序、一次性訂閱。
"""

from core.event_bus import EventBus


class TestEventBusBasic:
    """基本 emit / on / off"""

    def setup_method(self):
        self.bus = EventBus()

    def test_emit_and_receive(self):
        received = []
        self.bus.on("test.event", lambda e: received.append(e.data))
        self.bus.emit("test.event", {"key": "value"})
        assert len(received) == 1
        assert received[0]["key"] == "value"

    def test_decorator_style(self):
        received = []

        @self.bus.on("test.deco")
        def handler(event):
            received.append(event.name)

        self.bus.emit("test.deco")
        assert received == ["test.deco"]

    def test_off_removes_handler(self):
        received = []
        handler = lambda e: received.append(1)
        self.bus.on("test.off", handler)
        self.bus.off("test.off", handler)
        self.bus.emit("test.off")
        assert received == []

    def test_off_all_handlers(self):
        received = []
        self.bus.on("test.all", lambda e: received.append(1))
        self.bus.on("test.all", lambda e: received.append(2))
        self.bus.off("test.all")
        self.bus.emit("test.all")
        assert received == []

    def test_no_handler_no_error(self):
        """沒有 handler 也不應報錯"""
        self.bus.emit("nonexistent.event")


class TestEventBusWildcard:
    """萬用字元訂閱"""

    def setup_method(self):
        self.bus = EventBus()

    def test_wildcard_star(self):
        received = []
        self.bus.on("*", lambda e: received.append(e.name))
        self.bus.emit("anything")
        self.bus.emit("page.action.click")
        assert len(received) == 2

    def test_prefix_wildcard(self):
        received = []
        self.bus.on("page.*", lambda e: received.append(e.name))
        self.bus.emit("page.click")
        self.bus.emit("page.input")
        self.bus.emit("driver.created")  # 不匹配
        assert len(received) == 2


class TestEventBusPriority:
    """優先序"""

    def setup_method(self):
        self.bus = EventBus()

    def test_priority_order(self):
        order = []
        self.bus.on("test.prio", lambda e: order.append("low"), priority=20)
        self.bus.on("test.prio", lambda e: order.append("high"), priority=1)
        self.bus.emit("test.prio")
        assert order == ["high", "low"]


class TestEventBusOnce:
    """一次性訂閱"""

    def setup_method(self):
        self.bus = EventBus()

    def test_once_fires_once(self):
        received = []
        self.bus.once("test.once", lambda e: received.append(1))
        self.bus.emit("test.once")
        self.bus.emit("test.once")
        assert received == [1]


class TestEventBusHistory:
    """事件歷史"""

    def setup_method(self):
        self.bus = EventBus()

    def test_history_recorded(self):
        self.bus.emit("a")
        self.bus.emit("b")
        history = self.bus.get_history()
        assert len(history) == 2
        assert history[0].name == "a"

    def test_history_filter(self):
        self.bus.emit("a")
        self.bus.emit("b")
        self.bus.emit("a")
        history = self.bus.get_history("a")
        assert len(history) == 2

    def test_clear(self):
        self.bus.on("x", lambda e: None)
        self.bus.emit("x")
        self.bus.clear()
        assert self.bus.get_history() == []
        assert self.bus.registered_events == []
