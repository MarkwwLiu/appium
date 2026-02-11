"""
自訂 Decorators
提供常用的測試裝飾器：平台跳過、自動重試、效能計時等。
"""

import functools
import time

import pytest

from config.config import Config
from utils.logger import logger


def android_only(func):
    """僅在 Android 平台執行"""
    return pytest.mark.skipif(
        Config.PLATFORM != "android",
        reason="僅限 Android 平台",
    )(func)


def ios_only(func):
    """僅在 iOS 平台執行"""
    return pytest.mark.skipif(
        Config.PLATFORM != "ios",
        reason="僅限 iOS 平台",
    )(func)


def retry_on_failure(max_retries: int = 2, delay: float = 1.0):
    """
    測試失敗時自動重試。

    用法：
        @retry_on_failure(max_retries=3, delay=2.0)
        def test_flaky_feature(self, driver):
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(
                        f"[重試] {func.__name__} 第 {attempt}/{max_retries} 次失敗: {e}"
                    )
                    if attempt < max_retries:
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator


def timer(func):
    """
    計算測試執行時間。

    用法：
        @timer
        def test_performance(self, driver):
            ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        logger.info(f"[計時] {func.__name__} 耗時 {elapsed:.2f} 秒")
        return result
    return wrapper
