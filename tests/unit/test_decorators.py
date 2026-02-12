"""
utils/decorators.py 單元測試

驗證 retry_on_failure、timer、timeout、android_only、ios_only 裝飾器。
"""

import time
import threading

import pytest
from unittest.mock import patch, MagicMock

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


@pytest.mark.unit
class TestTimeoutWindows:
    """timeout 裝飾器 Windows 分支"""

    @pytest.mark.unit
    def test_windows_within_timeout(self):
        """Windows: 未超時時正常回傳"""
        # sys.platform 在 wrapper 函式內部被讀取（每次呼叫時），
        # 所以只需 patch sys.platform 就能進入 Windows 分支
        @timeout(5)
        def fast():
            return "done"

        with patch.object(__import__("sys"), "platform", "win32"):
            result = fast()
        assert result == "done"

    @pytest.mark.unit
    def test_windows_exceeds_timeout(self):
        """Windows: 超時拋出 TimeoutError"""
        @timeout(1)
        def slow():
            time.sleep(5)
            return "late"

        with patch.object(__import__("sys"), "platform", "win32"):
            with pytest.raises(TimeoutError):
                slow()

    @pytest.mark.unit
    def test_windows_function_raises_exception(self):
        """Windows: 函式拋出例外時正確傳播"""
        @timeout(5)
        def failing():
            raise ValueError("test error")

        with patch.object(__import__("sys"), "platform", "win32"):
            with pytest.raises(ValueError, match="test error"):
                failing()


@pytest.mark.unit
class TestAndroidOnly:
    """android_only 裝飾器"""

    @pytest.mark.unit
    def test_skips_when_not_android(self):
        """非 Android 平台時跳過"""
        from config.config import Config
        original_platform = Config.PLATFORM
        try:
            Config.PLATFORM = "ios"
            import importlib
            import utils.decorators as dec_module
            importlib.reload(dec_module)

            @dec_module.android_only
            def android_test():
                return "android"

            # android_only 使用 pytest.mark.skipif，檢查標記已套用
            markers = list(android_test.pytestmark)
            skip_markers = [m for m in markers if m.name == "skipif"]
            assert len(skip_markers) > 0
            # 條件應為 True (因為 PLATFORM != "android")
            assert skip_markers[0].args[0] is True
        finally:
            Config.PLATFORM = original_platform
            importlib.reload(dec_module)

    @pytest.mark.unit
    def test_runs_when_android(self):
        """Android 平台時不跳過"""
        from config.config import Config
        original_platform = Config.PLATFORM
        try:
            Config.PLATFORM = "android"
            import importlib
            import utils.decorators as dec_module
            importlib.reload(dec_module)

            @dec_module.android_only
            def android_test():
                return "android"

            markers = list(android_test.pytestmark)
            skip_markers = [m for m in markers if m.name == "skipif"]
            assert len(skip_markers) > 0
            # 條件應為 False (因為 PLATFORM == "android")
            assert skip_markers[0].args[0] is False
        finally:
            Config.PLATFORM = original_platform
            importlib.reload(dec_module)


@pytest.mark.unit
class TestIosOnly:
    """ios_only 裝飾器"""

    @pytest.mark.unit
    def test_skips_when_not_ios(self):
        """非 iOS 平台時跳過"""
        from config.config import Config
        original_platform = Config.PLATFORM
        try:
            Config.PLATFORM = "android"
            import importlib
            import utils.decorators as dec_module
            importlib.reload(dec_module)

            @dec_module.ios_only
            def ios_test():
                return "ios"

            markers = list(ios_test.pytestmark)
            skip_markers = [m for m in markers if m.name == "skipif"]
            assert len(skip_markers) > 0
            # 條件應為 True (因為 PLATFORM != "ios")
            assert skip_markers[0].args[0] is True
        finally:
            Config.PLATFORM = original_platform
            importlib.reload(dec_module)

    @pytest.mark.unit
    def test_runs_when_ios(self):
        """iOS 平台時不跳過"""
        from config.config import Config
        original_platform = Config.PLATFORM
        try:
            Config.PLATFORM = "ios"
            import importlib
            import utils.decorators as dec_module
            importlib.reload(dec_module)

            @dec_module.ios_only
            def ios_test():
                return "ios"

            markers = list(ios_test.pytestmark)
            skip_markers = [m for m in markers if m.name == "skipif"]
            assert len(skip_markers) > 0
            # 條件應為 False (因為 PLATFORM == "ios")
            assert skip_markers[0].args[0] is False
        finally:
            Config.PLATFORM = original_platform
            importlib.reload(dec_module)
