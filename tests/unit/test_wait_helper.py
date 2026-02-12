"""
utils.wait_helper 單元測試
驗證 wait_for、retry、FluentWait 的行為。
"""

import time

import pytest
from unittest.mock import patch, MagicMock

from utils.wait_helper import wait_for, retry, FluentWait


@pytest.mark.unit
class TestWaitFor:
    """wait_for 函式"""

    @pytest.mark.unit
    def test_immediate_success(self):
        """條件立即成立"""
        result = wait_for(lambda: "ok", timeout=1)
        assert result == "ok"

    @pytest.mark.unit
    def test_delayed_success(self):
        """條件延遲後成立"""
        counter = {"n": 0}

        def condition():
            counter["n"] += 1
            return "done" if counter["n"] >= 3 else None

        result = wait_for(condition, timeout=5, interval=0.1)
        assert result == "done"

    @pytest.mark.unit
    def test_timeout_raises(self):
        """超時拋出 TimeoutError"""
        with pytest.raises(TimeoutError, match="等待逾時"):
            wait_for(lambda: False, timeout=0.3, interval=0.1)

    @pytest.mark.unit
    def test_custom_message(self):
        """自訂逾時訊息"""
        with pytest.raises(TimeoutError, match="自訂訊息"):
            wait_for(lambda: False, timeout=0.2, interval=0.1, message="自訂訊息")

    @pytest.mark.unit
    def test_exception_in_condition(self):
        """條件拋出例外時包含在逾時錯誤中"""
        def bad():
            raise ValueError("boom")

        with pytest.raises(TimeoutError, match="boom"):
            wait_for(bad, timeout=0.3, interval=0.1)


@pytest.mark.unit
class TestRetry:
    """retry 函式"""

    @pytest.mark.unit
    def test_immediate_success(self):
        """第一次就成功"""
        result = retry(lambda: 42, max_attempts=3)
        assert result == 42

    @pytest.mark.unit
    def test_retry_on_failure(self):
        """失敗後重試成功"""
        counter = {"n": 0}

        def flaky():
            counter["n"] += 1
            if counter["n"] < 3:
                raise ValueError("not yet")
            return "ok"

        result = retry(flaky, max_attempts=3, delay=0.05)
        assert result == "ok"

    @pytest.mark.unit
    def test_exhausted_retries(self):
        """重試用盡後拋出最後一個例外"""
        with pytest.raises(ValueError, match="always fails"):
            retry(
                lambda: (_ for _ in ()).throw(ValueError("always fails")),
                max_attempts=2,
                delay=0.05,
            )

    @pytest.mark.unit
    def test_specific_exception_filter(self):
        """不在 exceptions 裡的例外不重試"""
        def raise_type():
            raise TypeError("wrong type")

        with pytest.raises(TypeError):
            retry(raise_type, max_attempts=3, delay=0.05, exceptions=(ValueError,))


@pytest.mark.unit
class TestFluentWait:
    """FluentWait 可鏈式等待器"""

    @pytest.mark.unit
    def test_default_values(self):
        """預設值：timeout=10, interval=0.5"""
        fw = FluentWait()
        assert fw._timeout == 10.0
        assert fw._interval == 0.5

    @pytest.mark.unit
    def test_timeout_returns_self(self):
        """timeout() 回傳自身以支援鏈式呼叫"""
        fw = FluentWait()
        result = fw.timeout(5)
        assert result is fw
        assert fw._timeout == 5

    @pytest.mark.unit
    def test_polling_returns_self(self):
        """polling() 回傳自身以支援鏈式呼叫"""
        fw = FluentWait()
        result = fw.polling(0.2)
        assert result is fw
        assert fw._interval == 0.2

    @pytest.mark.unit
    def test_ignoring_returns_self(self):
        """ignoring() 回傳自身以支援鏈式呼叫"""
        fw = FluentWait()
        result = fw.ignoring(ValueError, TypeError)
        assert result is fw
        assert fw._ignored == (ValueError, TypeError)

    @pytest.mark.unit
    def test_message_returns_self(self):
        """message() 回傳自身以支援鏈式呼叫"""
        fw = FluentWait()
        result = fw.message("custom message")
        assert result is fw
        assert fw._message == "custom message"

    @pytest.mark.unit
    def test_until_returns_self(self):
        """until() 回傳自身以支援鏈式呼叫"""
        fw = FluentWait()
        cond = lambda: True
        result = fw.until(cond)
        assert result is fw
        assert fw._condition is cond

    @pytest.mark.unit
    def test_wait_without_until_raises_valueerror(self):
        """未呼叫 until() 就呼叫 wait() 拋出 ValueError"""
        fw = FluentWait()
        with pytest.raises(ValueError, match="必須先呼叫 .until"):
            fw.wait()

    @pytest.mark.unit
    def test_wait_succeeds_immediately(self):
        """條件立即成立時回傳結果"""
        result = (
            FluentWait()
            .timeout(1)
            .polling(0.05)
            .until(lambda: "found")
            .wait()
        )
        assert result == "found"

    @pytest.mark.unit
    def test_wait_retries_until_condition_succeeds(self):
        """條件多次不成立後成功"""
        counter = {"n": 0}

        def condition():
            counter["n"] += 1
            return "ok" if counter["n"] >= 3 else None

        result = (
            FluentWait()
            .timeout(2)
            .polling(0.05)
            .until(condition)
            .wait()
        )
        assert result == "ok"
        assert counter["n"] >= 3

    @pytest.mark.unit
    def test_wait_ignores_specified_exceptions(self):
        """忽略指定例外，繼續等待"""
        counter = {"n": 0}

        def condition():
            counter["n"] += 1
            if counter["n"] < 3:
                raise ValueError("ignored error")
            return "success"

        result = (
            FluentWait()
            .timeout(2)
            .polling(0.05)
            .ignoring(ValueError)
            .until(condition)
            .wait()
        )
        assert result == "success"

    @pytest.mark.unit
    def test_wait_times_out_with_custom_message(self):
        """逾時時使用自訂訊息"""
        with pytest.raises(TimeoutError, match="找不到元素"):
            (
                FluentWait()
                .timeout(0.2)
                .polling(0.05)
                .message("找不到元素")
                .until(lambda: False)
                .wait()
            )

    @pytest.mark.unit
    def test_wait_includes_last_exception_in_error(self):
        """逾時錯誤包含最後的例外資訊"""
        def condition():
            raise RuntimeError("connection lost")

        with pytest.raises(TimeoutError, match="connection lost"):
            (
                FluentWait()
                .timeout(0.2)
                .polling(0.05)
                .until(condition)
                .wait()
            )


@pytest.mark.unit
class TestWaitForEdgeCases:
    """wait_for 邊界情況"""

    @pytest.mark.unit
    def test_wait_for_succeeds_immediately(self):
        """條件第一次就成立，不需等待"""
        call_count = 0

        def condition():
            nonlocal call_count
            call_count += 1
            return "immediate"

        result = wait_for(condition, timeout=1, interval=0.1)

        assert result == "immediate"
        assert call_count == 1

    @pytest.mark.unit
    def test_wait_for_exception_in_condition_included_in_timeout_error(self):
        """條件中拋出的例外包含在逾時錯誤中"""
        def condition():
            raise ConnectionError("network failure")

        with pytest.raises(TimeoutError) as exc_info:
            wait_for(condition, timeout=0.2, interval=0.05)

        assert "network failure" in str(exc_info.value)

    @pytest.mark.unit
    def test_wait_for_with_custom_message(self):
        """自訂訊息出現在逾時錯誤中"""
        with pytest.raises(TimeoutError) as exc_info:
            wait_for(
                lambda: None,
                timeout=0.2,
                interval=0.05,
                message="等待登入按鈕出現",
            )

        assert "等待登入按鈕出現" in str(exc_info.value)
