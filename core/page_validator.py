"""
Page Validator — 通用頁面驗證規則引擎

用宣告式的方式定義驗證規則，而不是每個測試寫一堆 assert。
規則可以複用、組合、動態載入。

用法：
    from core.page_validator import PageValidator, rule

    # 定義規則
    validator = PageValidator(driver)
    validator.add_rules([
        rule.element_visible(LoginPage.USERNAME),
        rule.element_visible(LoginPage.PASSWORD),
        rule.element_clickable(LoginPage.LOGIN_BTN),
        rule.text_equals(LoginPage.TITLE, "登入"),
        rule.no_error_toast(),
        rule.page_load_under(seconds=5),
    ])

    # 執行驗證
    result = validator.validate()
    assert result.all_passed, result.summary

    # 或一行搞定
    validator.assert_all()
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from utils.logger import logger


@dataclass
class RuleResult:
    """單一規則的驗證結果"""
    rule_name: str
    passed: bool
    message: str = ""
    actual: Any = None
    expected: Any = None
    duration: float = 0.0


@dataclass
class ValidationResult:
    """整體驗證結果"""
    results: list[RuleResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def summary(self) -> str:
        lines = [
            f"驗證結果: {self.passed_count}/{len(self.results)} 通過"
        ]
        for r in self.results:
            icon = "PASS" if r.passed else "FAIL"
            lines.append(f"  [{icon}] {r.rule_name}: {r.message}")
        return "\n".join(lines)

    @property
    def failures(self) -> list[RuleResult]:
        return [r for r in self.results if not r.passed]


# Rule = Callable[[driver], RuleResult]
Rule = Callable


class PageValidator:
    """頁面驗證器"""

    def __init__(self, driver, timeout: int = 10):
        self.driver = driver
        self.timeout = timeout
        self._rules: list[Rule] = []

    def add_rule(self, rule_fn: Rule) -> "PageValidator":
        self._rules.append(rule_fn)
        return self

    def add_rules(self, rules: list[Rule]) -> "PageValidator":
        self._rules.extend(rules)
        return self

    def clear(self) -> "PageValidator":
        self._rules.clear()
        return self

    def validate(self) -> ValidationResult:
        """執行所有規則"""
        result = ValidationResult()
        for rule_fn in self._rules:
            start = time.time()
            try:
                r = rule_fn(self.driver, self.timeout)
                r.duration = time.time() - start
            except Exception as e:
                r = RuleResult(
                    rule_name=getattr(rule_fn, '__name__', 'unknown'),
                    passed=False,
                    message=str(e),
                    duration=time.time() - start,
                )
            result.results.append(r)

        if result.all_passed:
            logger.info(f"驗證通過: {result.passed_count} 條規則")
        else:
            logger.warning(result.summary)

        return result

    def assert_all(self) -> None:
        """驗證並 assert"""
        result = self.validate()
        if not result.all_passed:
            raise AssertionError(result.summary)


# ── 預定義規則工廠 ──

class rule:
    """規則工廠 — 產生可複用的驗證規則"""

    @staticmethod
    def element_visible(locator: tuple, name: str = "") -> Rule:
        """元素可見"""
        label = name or str(locator)
        def _check(driver, timeout):
            try:
                WebDriverWait(driver, timeout).until(
                    EC.visibility_of_element_located(locator)
                )
                return RuleResult(
                    rule_name=f"element_visible({label})",
                    passed=True,
                    message="元素可見",
                )
            except Exception:
                return RuleResult(
                    rule_name=f"element_visible({label})",
                    passed=False,
                    message=f"元素不可見 (等待 {timeout}s)",
                )
        return _check

    @staticmethod
    def element_clickable(locator: tuple, name: str = "") -> Rule:
        """元素可點擊"""
        label = name or str(locator)
        def _check(driver, timeout):
            try:
                WebDriverWait(driver, timeout).until(
                    EC.element_to_be_clickable(locator)
                )
                return RuleResult(
                    rule_name=f"element_clickable({label})",
                    passed=True,
                    message="元素可點擊",
                )
            except Exception:
                return RuleResult(
                    rule_name=f"element_clickable({label})",
                    passed=False,
                    message="元素不可點擊",
                )
        return _check

    @staticmethod
    def element_not_present(locator: tuple, name: str = "") -> Rule:
        """元素不存在"""
        label = name or str(locator)
        def _check(driver, timeout):
            try:
                WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located(locator)
                )
                return RuleResult(
                    rule_name=f"element_not_present({label})",
                    passed=False,
                    message="元素不應存在但存在",
                )
            except Exception:
                return RuleResult(
                    rule_name=f"element_not_present({label})",
                    passed=True,
                    message="元素不存在（正確）",
                )
        return _check

    @staticmethod
    def text_equals(locator: tuple, expected: str, name: str = "") -> Rule:
        """文字完全相等"""
        label = name or str(locator)
        def _check(driver, timeout):
            try:
                el = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located(locator)
                )
                actual = el.text
                passed = actual == expected
                return RuleResult(
                    rule_name=f"text_equals({label})",
                    passed=passed,
                    message=f"預期 '{expected}'，實際 '{actual}'" if not passed else "文字正確",
                    actual=actual,
                    expected=expected,
                )
            except Exception as e:
                return RuleResult(
                    rule_name=f"text_equals({label})",
                    passed=False,
                    message=f"找不到元素: {e}",
                )
        return _check

    @staticmethod
    def text_contains(locator: tuple, substring: str, name: str = "") -> Rule:
        """文字包含"""
        label = name or str(locator)
        def _check(driver, timeout):
            try:
                el = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located(locator)
                )
                actual = el.text
                passed = substring in actual
                return RuleResult(
                    rule_name=f"text_contains({label})",
                    passed=passed,
                    message=f"預期包含 '{substring}'，實際 '{actual}'" if not passed else "包含正確",
                    actual=actual,
                    expected=substring,
                )
            except Exception as e:
                return RuleResult(
                    rule_name=f"text_contains({label})",
                    passed=False,
                    message=str(e),
                )
        return _check

    @staticmethod
    def element_count(locator: tuple, expected: int, name: str = "") -> Rule:
        """元素數量"""
        label = name or str(locator)
        def _check(driver, timeout):
            elements = driver.find_elements(*locator)
            actual = len(elements)
            passed = actual == expected
            return RuleResult(
                rule_name=f"element_count({label})",
                passed=passed,
                message=f"預期 {expected} 個，實際 {actual} 個" if not passed else f"{actual} 個（正確）",
                actual=actual,
                expected=expected,
            )
        return _check

    @staticmethod
    def element_count_gte(locator: tuple, minimum: int, name: str = "") -> Rule:
        """元素數量 >= minimum"""
        label = name or str(locator)
        def _check(driver, timeout):
            elements = driver.find_elements(*locator)
            actual = len(elements)
            passed = actual >= minimum
            return RuleResult(
                rule_name=f"element_count_gte({label})",
                passed=passed,
                message=f"預期 >= {minimum}，實際 {actual}" if not passed else f"{actual} >= {minimum}",
                actual=actual,
                expected=minimum,
            )
        return _check

    @staticmethod
    def no_error_toast() -> Rule:
        """畫面上不應有 error/crash 訊息"""
        def _check(driver, timeout):
            error_xpaths = [
                '//*[contains(@text,"error")]',
                '//*[contains(@text,"Error")]',
                '//*[contains(@text,"crash")]',
                '//*[contains(@text,"stopped")]',
                '//*[contains(@text,"錯誤")]',
                '//*[contains(@text,"已停止")]',
            ]
            from appium.webdriver.common.appiumby import AppiumBy
            for xpath in error_xpaths:
                try:
                    els = driver.find_elements(AppiumBy.XPATH, xpath)
                    visible = [e for e in els if e.is_displayed()]
                    if visible:
                        return RuleResult(
                            rule_name="no_error_toast",
                            passed=False,
                            message=f"發現錯誤訊息: '{visible[0].text}'",
                            actual=visible[0].text,
                        )
                except Exception:
                    continue
            return RuleResult(
                rule_name="no_error_toast",
                passed=True,
                message="無錯誤訊息",
            )
        return _check

    @staticmethod
    def page_load_under(seconds: float) -> Rule:
        """頁面載入時間不超過指定秒數"""
        def _check(driver, timeout):
            start = time.time()
            # 等待任意元素出現
            from appium.webdriver.common.appiumby import AppiumBy
            try:
                WebDriverWait(driver, seconds).until(
                    EC.presence_of_element_located(
                        (AppiumBy.XPATH, "//*[@clickable='true']")
                    )
                )
                elapsed = time.time() - start
                return RuleResult(
                    rule_name=f"page_load_under({seconds}s)",
                    passed=elapsed <= seconds,
                    message=f"載入耗時 {elapsed:.2f}s",
                    actual=elapsed,
                    expected=seconds,
                )
            except Exception:
                elapsed = time.time() - start
                return RuleResult(
                    rule_name=f"page_load_under({seconds}s)",
                    passed=False,
                    message=f"載入逾時 ({elapsed:.2f}s > {seconds}s)",
                    actual=elapsed,
                    expected=seconds,
                )
        return _check

    @staticmethod
    def custom(name: str, check_fn: Callable) -> Rule:
        """
        自訂規則。

        Args:
            name: 規則名稱
            check_fn: (driver) -> bool 或 (driver) -> str (回傳錯誤訊息)
        """
        def _check(driver, timeout):
            result = check_fn(driver)
            if isinstance(result, bool):
                return RuleResult(
                    rule_name=name,
                    passed=result,
                    message="通過" if result else "失敗",
                )
            elif isinstance(result, str):
                return RuleResult(
                    rule_name=name,
                    passed=False,
                    message=result,
                )
            return RuleResult(rule_name=name, passed=bool(result))
        return _check
