"""
等待與重試工具
提供通用的條件等待與重試機制。
"""

import time
from typing import Callable, TypeVar

from utils.logger import logger

T = TypeVar("T")


def wait_for(
    condition: Callable[[], T],
    timeout: int = 10,
    interval: float = 0.5,
    message: str = "",
) -> T:
    """
    等待某個條件成立。

    Args:
        condition: 回傳值為 truthy 時視為成立的 callable
        timeout: 最長等待秒數
        interval: 輪詢間隔秒數
        message: 超時時顯示的錯誤訊息

    Returns:
        condition 的回傳值

    Raises:
        TimeoutError: 超過 timeout 仍未成立
    """
    end_time = time.time() + timeout
    last_exception = None

    while time.time() < end_time:
        try:
            result = condition()
            if result:
                return result
        except Exception as e:
            last_exception = e
        time.sleep(interval)

    error = message or f"等待逾時 ({timeout}s)"
    if last_exception:
        error += f" | 最後的例外: {last_exception}"
    raise TimeoutError(error)


def retry(
    func: Callable[[], T],
    max_attempts: int = 3,
    delay: float = 1.0,
    exceptions: tuple = (Exception,),
) -> T:
    """
    重試機制，遇到指定例外時自動重試。

    Args:
        func: 要執行的 callable
        max_attempts: 最大嘗試次數
        delay: 每次重試間隔秒數
        exceptions: 要攔截重試的例外類型

    Returns:
        func 的回傳值

    Raises:
        最後一次嘗試的例外
    """
    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except exceptions as e:
            logger.warning(f"第 {attempt}/{max_attempts} 次嘗試失敗: {e}")
            if attempt == max_attempts:
                raise
            time.sleep(delay)
