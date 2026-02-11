"""
SmartTestData — 根據欄位語意產生針對性測試資料

不再是通用的 "test_value"，而是：
- email 欄位 → 測 "no@", "double@@", 缺 domain, 超長 email
- password 欄位 → 測短密碼、純數字、無特殊字元
- phone 欄位 → 測字母、不足位數、國際格式

每種語意有專屬的正向/反向/邊界資料庫。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from scanner.analyzer import AnalyzedElement, FieldSemantic, PageSnapshot


@dataclass
class TestCase:
    """單一測試案例"""
    case_id: str
    category: str          # positive / negative / boundary / security
    description: str
    fields: dict[str, str]  # {var_name: value}
    expected: str           # success / error / check
    tags: list[str] = field(default_factory=list)


# ── 每種語意的專屬測試資料 ──

def _positive(semantic: FieldSemantic) -> list[tuple[str, str]]:
    """(description, value)"""
    return {
        FieldSemantic.EMAIL: [
            ("有效 email", "test@example.com"),
            ("子網域 email", "user@mail.example.com"),
            ("含 + 號 email", "user+tag@example.com"),
        ],
        FieldSemantic.PASSWORD: [
            ("強密碼", "Abc123!@#"),
            ("長密碼", "MyP@ssw0rd2025!"),
        ],
        FieldSemantic.CONFIRM_PASSWORD: [
            ("與密碼一致", "Abc123!@#"),
        ],
        FieldSemantic.USERNAME: [
            ("英文帳號", "testuser"),
            ("含底線帳號", "test_user_01"),
        ],
        FieldSemantic.PHONE: [
            ("手機號碼", "0912345678"),
            ("含國碼", "+886912345678"),
        ],
        FieldSemantic.NAME: [
            ("英文名", "John Doe"),
            ("中文名", "王小明"),
        ],
        FieldSemantic.SEARCH: [
            ("一般搜尋", "test keyword"),
        ],
        FieldSemantic.URL: [
            ("https URL", "https://example.com"),
        ],
        FieldSemantic.NUMBER: [
            ("正整數", "42"),
            ("小數", "3.14"),
        ],
        FieldSemantic.DATE: [
            ("標準日期", "2025-01-15"),
        ],
        FieldSemantic.ADDRESS: [
            ("中文地址", "台北市信義區信義路五段7號"),
        ],
        FieldSemantic.CAPTCHA: [
            ("6位驗證碼", "123456"),
        ],
        FieldSemantic.GENERIC_TEXT: [
            ("一般文字", "test_value"),
        ],
    }.get(semantic, [("通用有效值", "test_value")])


def _negative(semantic: FieldSemantic) -> list[tuple[str, str, list[str]]]:
    """(description, value, tags)"""
    base = [
        ("空白", "", ["required"]),
    ]

    specific = {
        FieldSemantic.EMAIL: [
            ("缺少 @", "testexample.com", ["format"]),
            ("缺少 domain", "test@", ["format"]),
            ("雙重 @", "test@@example.com", ["format"]),
            ("中文 email", "測試@example.com", ["format"]),
            ("空格 email", "test @example.com", ["format"]),
            ("特殊字元", "test<>@example.com", ["format", "xss"]),
        ],
        FieldSemantic.PASSWORD: [
            ("1 字元", "a", ["too_short"]),
            ("純數字", "12345678", ["weak"]),
            ("純小寫", "abcdefgh", ["weak"]),
            ("含空格", "abc 123", ["format"]),
        ],
        FieldSemantic.CONFIRM_PASSWORD: [
            ("與密碼不一致", "WrongPassword!", ["mismatch"]),
        ],
        FieldSemantic.USERNAME: [
            ("特殊字元", "user<>!@#", ["format"]),
            ("全空格", "   ", ["whitespace"]),
            ("太短", "ab", ["too_short"]),
        ],
        FieldSemantic.PHONE: [
            ("含字母", "091234abcd", ["format"]),
            ("太短", "091", ["too_short"]),
            ("太長", "091234567890123", ["too_long"]),
            ("全字母", "abcdefghij", ["format"]),
        ],
        FieldSemantic.NAME: [
            ("純數字", "12345", ["format"]),
            ("特殊字元", "John<script>", ["xss"]),
        ],
        FieldSemantic.NUMBER: [
            ("字母", "abc", ["format"]),
            ("負數", "-1", ["range"]),
            ("超大數", "99999999999", ["range"]),
        ],
        FieldSemantic.CAPTCHA: [
            ("不足位數", "123", ["too_short"]),
            ("字母", "abcdef", ["format"]),
            ("過期碼", "000000", ["expired"]),
        ],
    }

    return base + specific.get(semantic, [])


def _boundary(semantic: FieldSemantic, max_len: int = 256) -> list[tuple[str, str, list[str]]]:
    """(description, value, tags)"""
    common = [
        ("最短 1 字元", "a", ["min"]),
        (f"最長 {max_len} 字元", "a" * max_len, ["max"]),
        (f"超長 {max_len + 1} 字元", "a" * (max_len + 1), ["overflow"]),
        ("前後空白", "  test  ", ["whitespace"]),
        ("Unicode 中文", "測試用戶名稱", ["unicode"]),
        ("Emoji", "😀🔥💯🎉", ["unicode", "emoji"]),
    ]

    specific = {
        FieldSemantic.EMAIL: [
            ("極長 local part", "a" * 64 + "@example.com", ["max"]),
            ("極長 domain", "test@" + "a" * 200 + ".com", ["max"]),
        ],
        FieldSemantic.PASSWORD: [
            ("128 字元密碼", "Aa1!" * 32, ["max"]),
        ],
        FieldSemantic.PHONE: [
            ("全 0", "0000000000", ["edge"]),
            ("含 +", "+886 912 345 678", ["format"]),
        ],
        FieldSemantic.NUMBER: [
            ("零", "0", ["edge"]),
            ("小數點", "0.001", ["precision"]),
            ("負零", "-0", ["edge"]),
        ],
    }

    return common + specific.get(semantic, [])


def _security(semantic: FieldSemantic) -> list[tuple[str, str, list[str]]]:
    """安全性測試資料"""
    return [
        ("XSS script", "<script>alert('xss')</script>", ["xss"]),
        ("XSS img", '<img src=x onerror=alert(1)>', ["xss"]),
        ("SQL injection OR", "' OR '1'='1' --", ["sqli"]),
        ("SQL injection UNION", "' UNION SELECT * FROM users --", ["sqli"]),
        ("Path traversal", "../../etc/passwd", ["path_traversal"]),
        ("Null byte", "test\x00value", ["null_byte"]),
        ("CRLF injection", "test\r\nHeader: injected", ["crlf"]),
    ]


class SmartTestDataGenerator:
    """根據 PageSnapshot 分析結果產生智慧測試資料"""

    def __init__(self, snapshot: PageSnapshot):
        self.snap = snapshot

    def generate(self) -> list[TestCase]:
        """產生完整測試資料"""
        cases: list[TestCase] = []
        counter = 0

        inputs = self.snap.inputs
        if not inputs:
            return cases

        page_prefix = self.snap.inferred_name.upper()

        # ── 正向 ──
        for pos_variants in self._positive_combos(inputs):
            counter += 1
            cases.append(TestCase(
                case_id=f"{page_prefix}_POS_{counter:03d}",
                category="positive",
                description=pos_variants["description"],
                fields=pos_variants["fields"],
                expected="success",
                tags=["positive", "smoke"],
            ))

        # ── 反向：每個欄位 × 每種 negative ──
        for inp in inputs:
            neg_patterns = _negative(inp.field_semantic)
            for desc, value, tags in neg_patterns:
                counter += 1
                fields = self._default_valid_fields(inputs)
                fields[inp.var_name] = value
                cases.append(TestCase(
                    case_id=f"{page_prefix}_NEG_{counter:03d}",
                    category="negative",
                    description=f"{inp.var_name}-{desc}",
                    fields=fields,
                    expected="error",
                    tags=["negative"] + tags,
                ))

        # ── 邊界：每個欄位 × 每種 boundary ──
        for inp in inputs:
            bd_patterns = _boundary(inp.field_semantic)
            for desc, value, tags in bd_patterns:
                counter += 1
                fields = self._default_valid_fields(inputs)
                fields[inp.var_name] = value
                cases.append(TestCase(
                    case_id=f"{page_prefix}_BD_{counter:03d}",
                    category="boundary",
                    description=f"{inp.var_name}-{desc}",
                    fields=fields,
                    expected="check",
                    tags=["boundary"] + tags,
                ))

        # ── 安全性：每個欄位 × 每種 attack ──
        for inp in inputs:
            sec_patterns = _security(inp.field_semantic)
            for desc, value, tags in sec_patterns:
                counter += 1
                fields = self._default_valid_fields(inputs)
                fields[inp.var_name] = value
                cases.append(TestCase(
                    case_id=f"{page_prefix}_SEC_{counter:03d}",
                    category="security",
                    description=f"{inp.var_name}-{desc}",
                    fields=fields,
                    expected="error",
                    tags=["security"] + tags,
                ))

        return cases

    def _positive_combos(self, inputs: list[AnalyzedElement]) -> list[dict]:
        """產生正向組合"""
        combos = []

        # 第一組：每個欄位取第一個 positive
        fields = {}
        for inp in inputs:
            positives = _positive(inp.field_semantic)
            if positives:
                fields[inp.var_name] = positives[0][1]
        combos.append({"description": "正向-所有欄位有效", "fields": dict(fields)})

        # 額外組合：每個欄位有多個 positive 時展開
        for inp in inputs:
            positives = _positive(inp.field_semantic)
            for desc, val in positives[1:]:  # 跳過第一個（已包含）
                alt_fields = dict(fields)
                alt_fields[inp.var_name] = val
                combos.append({
                    "description": f"正向-{inp.var_name}-{desc}",
                    "fields": alt_fields,
                })

        return combos

    def _default_valid_fields(self, inputs: list[AnalyzedElement]) -> dict[str, str]:
        """所有欄位的預設有效值"""
        fields = {}
        for inp in inputs:
            positives = _positive(inp.field_semantic)
            fields[inp.var_name] = positives[0][1] if positives else "test"
        return fields
