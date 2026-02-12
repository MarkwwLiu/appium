"""
utils/decorators.py 單元測試

驗證 retry_on_failure、timer、timeout 裝飾器。
"""

import time

import pytest

from utils.decorators import retry_on_failure, timer, timeout


@pytest.mark.unit
class TestRetryOnFailure:
    """retry_on_failure 裝飾器"""

    @pytest.mark.unit
    def test_no_retry_on_success(self):
        """成功時不重試"""
        call_count = 0

        @retry_on_failure(max_retries=3, delay=0)
        def ok():
            nonlocal call_count
            call_count += 1
            return "ok"

        assert ok() == "ok"
        assert call_count == 1

    @pytest.mark.unit
    def test_retry_then_succeed(self):
        """失敗後重試成功"""
        call_count = 0

        @retry_on_failure(max_retries=3, delay=0)
        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("not yet")
            return "ok"

        assert flaky() == "ok"
        assert call_count == 3

    @pytest.mark.unit
    def test_exhausted_retries(self):
        """重試用盡後拋出最後一個例外"""
        @retry_on_failure(max_retries=2, delay=0)
        def always_fail():
            raise RuntimeError("fail")

        with pytest.raises(RuntimeError, match="fail"):
            always_fail()

    @pytest.mark.unit
    def test_preserves_function_name(self):
        """functools.wraps 保留函式名稱"""
        @retry_on_failure(max_retries=2)
        def my_func():
            pass

        assert my_func.__name__ == "my_func"


@pytest.mark.unit
class TestTimer:
    """timer 裝飾器"""

    @pytest.mark.unit
    def test_timer_returns_result(self):
        """timer 不影響回傳值"""
        @timer
        def add(a, b):
            return a + b

        assert add(1, 2) == 3

    @pytest.mark.unit
    def test_timer_preserves_name(self):
        """functools.wraps 保留函式名稱"""
        @timer
        def my_timed():
            pass

        assert my_timed.__name__ == "my_timed"


@pytest.mark.unit
class TestTimeout:
    """timeout 裝飾器"""

    @pytest.mark.unit
    def test_within_timeout(self):
        """未超時時正常回傳"""
        @timeout(5)
        def fast():
            return "done"

        assert fast() == "done"

    @pytest.mark.unit
    def test_exceeds_timeout(self):
        """超時拋出 TimeoutError"""
        @timeout(1)
        def slow():
            time.sleep(3)
            return "late"

        with pytest.raises(TimeoutError):
            slow()

    @pytest.mark.unit
    def test_preserves_function_name(self):
        """functools.wraps 保留函式名稱"""
        @timeout(10)
        def named():
            pass

        assert named.__name__ == "named"
