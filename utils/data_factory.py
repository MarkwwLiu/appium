"""
測試資料工廠
產生隨機但有意義的測試資料，避免硬編碼。
"""

import random
import string
import time


class DataFactory:
    """產生各類測試用隨機資料"""

    @staticmethod
    def random_string(length: int = 8) -> str:
        return "".join(random.choices(string.ascii_lowercase, k=length))

    @staticmethod
    def random_email() -> str:
        name = DataFactory.random_string(6)
        ts = int(time.time()) % 10000
        return f"test_{name}_{ts}@example.com"

    @staticmethod
    def random_phone() -> str:
        return f"09{random.randint(10000000, 99999999)}"

    @staticmethod
    def random_password(length: int = 12) -> str:
        chars = string.ascii_letters + string.digits + "!@#$%"
        pw = [
            random.choice(string.ascii_uppercase),
            random.choice(string.ascii_lowercase),
            random.choice(string.digits),
            random.choice("!@#$%"),
        ]
        pw += random.choices(chars, k=length - 4)
        random.shuffle(pw)
        return "".join(pw)

    @staticmethod
    def random_username() -> str:
        return f"user_{DataFactory.random_string(5)}_{random.randint(1, 999)}"

    @staticmethod
    def random_int(min_val: int = 1, max_val: int = 100) -> int:
        return random.randint(min_val, max_val)
