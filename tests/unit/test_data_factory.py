"""
utils/data_factory.py 單元測試

驗證 DataFactory 產生的隨機資料格式正確。
"""

import re

import pytest

from utils.data_factory import DataFactory


@pytest.mark.unit
class TestRandomString:
    """random_string"""

    @pytest.mark.unit
    def test_default_length(self):
        """預設長度 8"""
        s = DataFactory.random_string()
        assert len(s) == 8

    @pytest.mark.unit
    def test_custom_length(self):
        """自訂長度"""
        s = DataFactory.random_string(20)
        assert len(s) == 20

    @pytest.mark.unit
    def test_only_lowercase(self):
        """只含小寫字母"""
        s = DataFactory.random_string(100)
        assert s.isalpha()
        assert s.islower()


@pytest.mark.unit
class TestRandomEmail:
    """random_email"""

    @pytest.mark.unit
    def test_email_format(self):
        """email 格式正確"""
        email = DataFactory.random_email()
        assert "@example.com" in email
        assert email.startswith("test_")

    @pytest.mark.unit
    def test_email_unique(self):
        """兩次產生不同"""
        e1 = DataFactory.random_email()
        e2 = DataFactory.random_email()
        assert e1 != e2


@pytest.mark.unit
class TestRandomPhone:
    """random_phone"""

    @pytest.mark.unit
    def test_phone_format(self):
        """手機號碼格式：09xxxxxxxx"""
        phone = DataFactory.random_phone()
        assert phone.startswith("09")
        assert len(phone) == 10
        assert phone.isdigit()


@pytest.mark.unit
class TestRandomPassword:
    """random_password"""

    @pytest.mark.unit
    def test_default_length(self):
        """預設長度 12"""
        pw = DataFactory.random_password()
        assert len(pw) == 12

    @pytest.mark.unit
    def test_has_uppercase(self):
        """包含大寫"""
        pw = DataFactory.random_password(20)
        assert any(c.isupper() for c in pw)

    @pytest.mark.unit
    def test_has_lowercase(self):
        """包含小寫"""
        pw = DataFactory.random_password(20)
        assert any(c.islower() for c in pw)

    @pytest.mark.unit
    def test_has_digit(self):
        """包含數字"""
        pw = DataFactory.random_password(20)
        assert any(c.isdigit() for c in pw)

    @pytest.mark.unit
    def test_has_special(self):
        """包含特殊字元"""
        pw = DataFactory.random_password(20)
        assert any(c in "!@#$%" for c in pw)


@pytest.mark.unit
class TestRandomUsername:
    """random_username"""

    @pytest.mark.unit
    def test_username_format(self):
        """username 以 user_ 開頭"""
        name = DataFactory.random_username()
        assert name.startswith("user_")

    @pytest.mark.unit
    def test_username_unique(self):
        """兩次不同"""
        n1 = DataFactory.random_username()
        n2 = DataFactory.random_username()
        assert n1 != n2


@pytest.mark.unit
class TestRandomInt:
    """random_int"""

    @pytest.mark.unit
    def test_within_range(self):
        """回傳值在範圍內"""
        for _ in range(50):
            val = DataFactory.random_int(10, 20)
            assert 10 <= val <= 20

    @pytest.mark.unit
    def test_default_range(self):
        """預設範圍 1-100"""
        for _ in range(50):
            val = DataFactory.random_int()
            assert 1 <= val <= 100
