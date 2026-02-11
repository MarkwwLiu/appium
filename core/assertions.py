"""
Assertion Library — 可鏈式呼叫的語意化斷言

讓測試更好讀，失敗訊息更明確。
支援 soft assert（收集所有失敗，最後一次報告）。

用法：
    from core.assertions import expect, soft_assert

    # 基本斷言
    expect(page.get_title()).to_equal("首頁")
    expect(page.get_price()).to_be_greater_than(0)
    expect(page.is_login_btn_displayed()).to_be_true()
    expect(element_list).to_have_length(5)
    expect(error_text).to_contain("密碼錯誤")

    # 反向
    expect(page.get_error()).not_to_be_empty()

    # Soft Assert（不立即中斷）
    with soft_assert() as sa:
        sa.expect(title).to_equal("首頁")
        sa.expect(price).to_be_greater_than(0)
        sa.expect(count).to_equal(10)
    # 結束 with 時，如果有任何失敗，才一次拋出全部
"""

from __future__ import annotations

from typing import Any


class AssertionResult:
    """單一斷言結果"""

    def __init__(self, passed: bool, message: str, actual: Any, expected: Any = None):
        self.passed = passed
        self.message = message
        self.actual = actual
        self.expected = expected


class Expect:
    """
    可鏈式呼叫的斷言物件

    expect(actual).to_equal(expected)
    """

    def __init__(self, actual: Any, label: str = ""):
        self._actual = actual
        self._label = label
        self._negated = False

    @property
    def not_to(self) -> "Expect":
        """反向斷言: expect(x).not_to.equal(y)"""
        # 回傳新物件避免污染
        clone = Expect(self._actual, self._label)
        clone._negated = True
        return clone

    # ── 相等 ──

    def to_equal(self, expected: Any, msg: str = "") -> None:
        """assert actual == expected"""
        passed = self._actual == expected
        self._assert(passed, msg or f"預期 {self._repr(expected)}，實際 {self._repr(self._actual)}", expected)

    def to_not_equal(self, expected: Any, msg: str = "") -> None:
        """assert actual != expected"""
        passed = self._actual != expected
        self._assert(passed, msg or f"預期不等於 {self._repr(expected)}，實際 {self._repr(self._actual)}", expected)

    # ── 布林 ──

    def to_be_true(self, msg: str = "") -> None:
        passed = self._actual is True
        self._assert(passed, msg or f"預期 True，實際 {self._repr(self._actual)}")

    def to_be_false(self, msg: str = "") -> None:
        passed = self._actual is False
        self._assert(passed, msg or f"預期 False，實際 {self._repr(self._actual)}")

    def to_be_truthy(self, msg: str = "") -> None:
        passed = bool(self._actual)
        self._assert(passed, msg or f"預期 truthy，實際 {self._repr(self._actual)}")

    def to_be_falsy(self, msg: str = "") -> None:
        passed = not bool(self._actual)
        self._assert(passed, msg or f"預期 falsy，實際 {self._repr(self._actual)}")

    # ── None ──

    def to_be_none(self, msg: str = "") -> None:
        passed = self._actual is None
        self._assert(passed, msg or f"預期 None，實際 {self._repr(self._actual)}")

    def to_not_be_none(self, msg: str = "") -> None:
        passed = self._actual is not None
        self._assert(passed, msg or f"預期非 None，實際 None")

    # ── 字串 ──

    def to_contain(self, substring: str, msg: str = "") -> None:
        passed = substring in str(self._actual)
        self._assert(passed, msg or f"預期包含 '{substring}'，實際 '{self._actual}'", substring)

    def to_not_contain(self, substring: str, msg: str = "") -> None:
        passed = substring not in str(self._actual)
        self._assert(passed, msg or f"預期不包含 '{substring}'，但出現在 '{self._actual}'", substring)

    def to_start_with(self, prefix: str, msg: str = "") -> None:
        passed = str(self._actual).startswith(prefix)
        self._assert(passed, msg or f"預期以 '{prefix}' 開頭，實際 '{self._actual}'", prefix)

    def to_end_with(self, suffix: str, msg: str = "") -> None:
        passed = str(self._actual).endswith(suffix)
        self._assert(passed, msg or f"預期以 '{suffix}' 結尾，實際 '{self._actual}'", suffix)

    def to_match(self, pattern: str, msg: str = "") -> None:
        """正規表達式比對"""
        import re
        passed = bool(re.search(pattern, str(self._actual)))
        self._assert(passed, msg or f"預期匹配 /{pattern}/，實際 '{self._actual}'", pattern)

    def to_be_empty(self, msg: str = "") -> None:
        passed = len(self._actual) == 0 if hasattr(self._actual, '__len__') else not self._actual
        self._assert(passed, msg or f"預期為空，實際 {self._repr(self._actual)}")

    def not_to_be_empty(self, msg: str = "") -> None:
        passed = len(self._actual) > 0 if hasattr(self._actual, '__len__') else bool(self._actual)
        self._assert(passed, msg or f"預期非空，實際為空")

    # ── 數值 ──

    def to_be_greater_than(self, expected, msg: str = "") -> None:
        passed = self._actual > expected
        self._assert(passed, msg or f"預期 > {expected}，實際 {self._actual}", expected)

    def to_be_less_than(self, expected, msg: str = "") -> None:
        passed = self._actual < expected
        self._assert(passed, msg or f"預期 < {expected}，實際 {self._actual}", expected)

    def to_be_between(self, low, high, msg: str = "") -> None:
        passed = low <= self._actual <= high
        self._assert(passed, msg or f"預期在 [{low}, {high}]，實際 {self._actual}", (low, high))

    # ── 集合 ──

    def to_have_length(self, expected: int, msg: str = "") -> None:
        actual_len = len(self._actual)
        passed = actual_len == expected
        self._assert(passed, msg or f"預期長度 {expected}，實際 {actual_len}", expected)

    def to_include(self, item: Any, msg: str = "") -> None:
        """assert item in actual (list/set/dict)"""
        passed = item in self._actual
        self._assert(passed, msg or f"預期包含 {self._repr(item)}", item)

    def to_be_instance_of(self, expected_type: type, msg: str = "") -> None:
        passed = isinstance(self._actual, expected_type)
        self._assert(
            passed,
            msg or f"預期型別 {expected_type.__name__}，實際 {type(self._actual).__name__}",
            expected_type,
        )

    # ── 內部 ──

    def _assert(self, passed: bool, message: str, expected: Any = None) -> None:
        if self._negated:
            passed = not passed
            message = f"[反向] {message}"

        if not passed:
            label = f"[{self._label}] " if self._label else ""
            raise AssertionError(f"{label}{message}")

    @staticmethod
    def _repr(value: Any) -> str:
        if isinstance(value, str):
            return f"'{value}'" if len(value) < 100 else f"'{value[:50]}...'"
        return repr(value)


def expect(actual: Any, label: str = "") -> Expect:
    """
    建立斷言物件。

    Args:
        actual: 要驗證的值
        label: 斷言標籤（出現在錯誤訊息中）
    """
    return Expect(actual, label)


class SoftAssert:
    """
    Soft Assert — 收集所有失敗，最後一次報告。

    用法:
        with soft_assert() as sa:
            sa.expect(a).to_equal(1)
            sa.expect(b).to_equal(2)
        # 結束 with 時才 raise（如果有失敗）
    """

    def __init__(self):
        self._failures: list[str] = []

    def expect(self, actual: Any, label: str = "") -> "SoftExpect":
        return SoftExpect(actual, label, self)

    def _record_failure(self, message: str) -> None:
        self._failures.append(message)

    def __enter__(self) -> "SoftAssert":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._failures:
            summary = f"Soft Assert: {len(self._failures)} 項失敗\n"
            for i, msg in enumerate(self._failures, 1):
                summary += f"  {i}. {msg}\n"
            raise AssertionError(summary)

    @property
    def failure_count(self) -> int:
        return len(self._failures)


class SoftExpect(Expect):
    """Soft 版本的 Expect，失敗時記錄而非立即拋出"""

    def __init__(self, actual: Any, label: str, soft_assert: SoftAssert):
        super().__init__(actual, label)
        self._soft = soft_assert

    def _assert(self, passed: bool, message: str, expected: Any = None) -> None:
        if self._negated:
            passed = not passed
            message = f"[反向] {message}"

        if not passed:
            label = f"[{self._label}] " if self._label else ""
            self._soft._record_failure(f"{label}{message}")


def soft_assert() -> SoftAssert:
    """建立 Soft Assert context manager"""
    return SoftAssert()
