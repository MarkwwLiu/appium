"""
core.assertions 單元測試
驗證 expect() 和 soft_assert() 的各種斷言行為。
"""

import pytest

from core.assertions import expect, soft_assert


class TestExpectEqual:
    """to_equal / to_not_equal"""

    def test_equal_pass(self):
        expect(42).to_equal(42)

    def test_equal_fail(self):
        with pytest.raises(AssertionError, match="預期"):
            expect(42).to_equal(99)

    def test_not_equal_pass(self):
        expect(1).to_not_equal(2)

    def test_not_equal_fail(self):
        with pytest.raises(AssertionError):
            expect(1).to_not_equal(1)


class TestExpectBoolean:
    """to_be_true / to_be_false / truthy / falsy"""

    def test_true(self):
        expect(True).to_be_true()

    def test_true_fail(self):
        with pytest.raises(AssertionError):
            expect(1).to_be_true()  # 1 is truthy but not True

    def test_false(self):
        expect(False).to_be_false()

    def test_truthy(self):
        expect("hello").to_be_truthy()

    def test_falsy(self):
        expect("").to_be_falsy()
        expect(0).to_be_falsy()
        expect(None).to_be_falsy()


class TestExpectNone:
    def test_none(self):
        expect(None).to_be_none()

    def test_not_none(self):
        expect("x").to_not_be_none()

    def test_none_fail(self):
        with pytest.raises(AssertionError):
            expect("x").to_be_none()


class TestExpectString:
    def test_contain(self):
        expect("hello world").to_contain("world")

    def test_not_contain(self):
        expect("hello").to_not_contain("xyz")

    def test_start_with(self):
        expect("hello").to_start_with("hel")

    def test_end_with(self):
        expect("hello").to_end_with("llo")

    def test_match(self):
        expect("test123").to_match(r"\d+")

    def test_empty(self):
        expect("").to_be_empty()
        expect([]).to_be_empty()

    def test_not_empty(self):
        expect("x").not_to_be_empty()
        expect([1]).not_to_be_empty()


class TestExpectNumeric:
    def test_greater_than(self):
        expect(10).to_be_greater_than(5)

    def test_less_than(self):
        expect(3).to_be_less_than(10)

    def test_between(self):
        expect(5).to_be_between(1, 10)
        expect(1).to_be_between(1, 10)  # inclusive

    def test_between_fail(self):
        with pytest.raises(AssertionError):
            expect(0).to_be_between(1, 10)


class TestExpectCollection:
    def test_length(self):
        expect([1, 2, 3]).to_have_length(3)

    def test_include(self):
        expect([1, 2, 3]).to_include(2)

    def test_instance_of(self):
        expect("hello").to_be_instance_of(str)


class TestExpectNegation:
    """not_to 反向斷言"""

    def test_not_to_equal(self):
        expect(1).not_to.to_equal(2)

    def test_not_to_equal_fail(self):
        with pytest.raises(AssertionError, match="反向"):
            expect(1).not_to.to_equal(1)

    def test_not_to_contain(self):
        expect("hello").not_to.to_contain("xyz")


class TestExpectLabel:
    """label 出現在錯誤訊息中"""

    def test_label_in_error(self):
        with pytest.raises(AssertionError, match="登入按鈕"):
            expect(False, label="登入按鈕").to_be_true()


class TestSoftAssert:
    """Soft Assert 收集多個失敗"""

    def test_no_failure(self):
        with soft_assert() as sa:
            sa.expect(1).to_equal(1)
            sa.expect("a").to_contain("a")

    def test_collect_failures(self):
        with pytest.raises(AssertionError, match="2 項失敗"):
            with soft_assert() as sa:
                sa.expect(1).to_equal(2)
                sa.expect("a").to_equal("b")

    def test_failure_count(self):
        sa = soft_assert()
        sa.expect(1).to_equal(2)
        sa.expect(1).to_equal(1)  # pass
        sa.expect("a").to_equal("b")
        assert sa.failure_count == 2
