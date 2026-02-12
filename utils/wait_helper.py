"""
等待與重試工具
提供通用的條件等待、Fluent Wait、重試機制。

用法：
    from utils.wait_helper import wait_for, retry, FluentWait

    # 簡易等待
    wait_for(lambda: element.is_displayed(), timeout=10)

    # Fluent Wait（可鏈式設定）
    result = (
        FluentWait()
        .timeout(15)
        .polling(0.3)
        .ignoring(StaleElementReferenceException)
        .until(lambda: driver.find_element(...))
        .message("登入按鈕未出現")
        .wait()
    )

    # 重試
    retry(api_call, max_attempts=3, delay=1.0)
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


class FluentWait:
    """
    Fluent Wait — 可鏈式設定的等待器

    比 wait_for() 更彈性：
    - 自訂輪詢間隔
    - 指定要忽略的例外類型
    - 可讀性更好的鏈式 API

    用法：
        element = (
            FluentWait()
            .timeout(10)
            .polling(0.5)
            .ignoring(NoSuchElementException, StaleElementReferenceException)
            .message("找不到登入按鈕")
            .until(lambda: driver.find_element(By.ID, "login"))
            .wait()
        )
    """

    def __init__(self):
        self._timeout: float = 10.0
        self._interval: float = 0.5
        self._condition: Callable | None = None
        self._message: str = ""
        self._ignored: tuple = ()

    def timeout(self, seconds: float) -> "FluentWait":
        """設定最大等待秒數"""
        self._timeout = seconds
        return self

    def polling(self, interval: float) -> "FluentWait":
        """設定輪詢間隔秒數"""
        self._interval = interval
        return self

    def ignoring(self, *exception_types: type) -> "FluentWait":
        """設定要忽略的例外類型（視為「尚未滿足」而非真正錯誤）"""
        self._ignored = exception_types
        return self

    def message(self, msg: str) -> "FluentWait":
        """設定逾時錯誤訊息"""
        self._message = msg
        return self

    def until(self, condition: Callable[[], T]) -> "FluentWait":
        """設定等待條件"""
        self._condition = condition
        return self

    def wait(self) -> T:
        """執行等待，回傳條件的回傳值"""
        if self._condition is None:
            raise ValueError("必須先呼叫 .until(condition) 設定等待條件")

        end_time = time.time() + self._timeout
        last_exception = None

        while time.time() < end_time:
            try:
                result = self._condition()
                if result:
                    return result
            except self._ignored:
                pass  # 忽略指定例外，繼續等待
            except Exception as e:
                last_exception = e
            time.sleep(self._interval)

        error = self._message or f"Fluent wait 逾時 ({self._timeout}s)"
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
