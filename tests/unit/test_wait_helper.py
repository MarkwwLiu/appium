"""
utils.wait_helper 單元測試
驗證 wait_for 和 retry 的行為。
"""

import pytest

from utils.wait_helper import wait_for, retry


class TestWaitFor:
    def test_immediate_success(self):
        result = wait_for(lambda: "ok", timeout=1)
        assert result == "ok"

    def test_delayed_success(self):
        counter = {"n": 0}

        def condition():
            counter["n"] += 1
            return "done" if counter["n"] >= 3 else None

        result = wait_for(condition, timeout=5, interval=0.1)
        assert result == "done"

    def test_timeout_raises(self):
        with pytest.raises(TimeoutError, match="等待逾時"):
            wait_for(lambda: False, timeout=0.3, interval=0.1)

    def test_custom_message(self):
        with pytest.raises(TimeoutError, match="自訂訊息"):
            wait_for(lambda: False, timeout=0.2, interval=0.1, message="自訂訊息")

    def test_exception_in_condition(self):
        def bad():
            raise ValueError("boom")

        with pytest.raises(TimeoutError, match="boom"):
            wait_for(bad, timeout=0.3, interval=0.1)


class TestRetry:
    def test_immediate_success(self):
        result = retry(lambda: 42, max_attempts=3)
        assert result == 42

    def test_retry_on_failure(self):
        counter = {"n": 0}

        def flaky():
            counter["n"] += 1
            if counter["n"] < 3:
                raise ValueError("not yet")
            return "ok"

        result = retry(flaky, max_attempts=3, delay=0.05)
        assert result == "ok"

    def test_exhausted_retries(self):
        with pytest.raises(ValueError, match="always fails"):
            retry(
                lambda: (_ for _ in ()).throw(ValueError("always fails")),
                max_attempts=2,
                delay=0.05,
            )

    def test_specific_exception_filter(self):
        def raise_type():
            raise TypeError("wrong type")

        # TypeError 不在 exceptions 裡，應直接拋出（不重試）
        with pytest.raises(TypeError):
            retry(raise_type, max_attempts=3, delay=0.05, exceptions=(ValueError,))
