"""
Test Data Writer
根據 PageSpec 自動產生正向 / 反向 / 邊界測試資料 JSON。
"""

import json
from pathlib import Path

from generator.schema import ElementType, PageSpec


# 根據 input_format 產生預設有效值
_FORMAT_DEFAULTS = {
    "email": "test@example.com",
    "phone": "0912345678",
    "password": "Abc123!@#",
    "number": "42",
    "url": "https://example.com",
    "date": "2025-01-01",
    "text": "test_value",
}

# 反向測試：各種無效輸入
_NEGATIVE_PATTERNS = {
    "empty": ("空白", ""),
    "xss": ("XSS 注入", "<script>alert('xss')</script>"),
    "sqli": ("SQL injection", "' OR '1'='1' --"),
    "special_chars": ("特殊字元", "!@#$%^&*(){}[]|\\<>?/~`"),
}

# 邊界測試
_BOUNDARY_PATTERNS = {
    "min_1": ("最短 1 字元", "a"),
    "spaces": ("全空白", "   "),
    "unicode_cjk": ("中文字", "測試用戶"),
    "unicode_emoji": ("Emoji", "😀🔥💯"),
    "leading_spaces": ("前後空白", "  test  "),
}


class TestDataWriter:
    """產生測試資料 JSON"""

    def __init__(self, output_dir: Path):
        self.data_dir = output_dir / "test_data"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def write(self, page: PageSpec) -> Path:
        """
        根據頁面規格產生測試資料。

        回傳 JSON 檔案路徑。
        JSON 結構:
        [
            {"case_id": "...", "category": "positive|negative|boundary",
             "description": "...", "field1": "...", "expected": "success|error|check"}
        ]
        """
        inputs = page.inputs
        if not inputs:
            # 沒有輸入框就產生空檔
            path = self.data_dir / f"{page.name}_data.json"
            path.write_text("[]", encoding="utf-8")
            return path

        all_cases: list[dict] = []
        case_counter = 0

        # ── 正向測試 ──
        case_counter += 1
        positive = self._make_case(
            page, case_counter, "positive", "正向-有效資料",
            {e.name: self._valid_value(e) for e in inputs},
            "success",
        )
        all_cases.append(positive)

        # ── 反向測試（每個必填欄位 × 每種 pattern）──
        required_inputs = [e for e in inputs if e.required]
        for field in required_inputs:
            for key, (desc, value) in _NEGATIVE_PATTERNS.items():
                case_counter += 1
                field_values = {e.name: self._valid_value(e) for e in inputs}
                field_values[field.name] = value
                case = self._make_case(
                    page, case_counter, "negative",
                    f"反向-{field.name}-{desc}",
                    field_values, "error",
                )
                all_cases.append(case)

        # ── 邊界測試（每個輸入欄位 × 每種 pattern）──
        for field in inputs:
            for key, (desc, value) in _BOUNDARY_PATTERNS.items():
                case_counter += 1
                field_values = {e.name: self._valid_value(e) for e in inputs}
                field_values[field.name] = value
                case = self._make_case(
                    page, case_counter, "boundary",
                    f"邊界-{field.name}-{desc}",
                    field_values, "check",
                )
                all_cases.append(case)

            # 超長字串
            case_counter += 1
            field_values = {e.name: self._valid_value(e) for e in inputs}
            field_values[field.name] = "a" * field.max_length
            case = self._make_case(
                page, case_counter, "boundary",
                f"邊界-{field.name}-最長({field.max_length}字元)",
                field_values, "check",
            )
            all_cases.append(case)

            # 超過最大長度
            case_counter += 1
            field_values = {e.name: self._valid_value(e) for e in inputs}
            field_values[field.name] = "a" * (field.max_length + 1)
            case = self._make_case(
                page, case_counter, "boundary",
                f"邊界-{field.name}-超長({field.max_length + 1}字元)",
                field_values, "check",
            )
            all_cases.append(case)

        # 輸出
        path = self.data_dir / f"{page.name}_data.json"
        path.write_text(
            json.dumps(all_cases, indent=4, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def _make_case(
        self, page: PageSpec, counter: int, category: str,
        description: str, field_values: dict, expected: str,
    ) -> dict:
        prefix = page.name.upper()
        return {
            "case_id": f"{prefix}_{counter:03d}",
            "category": category,
            "description": description,
            **field_values,
            "expected": expected,
        }

    def _valid_value(self, el) -> str:
        """取得欄位的有效值"""
        if el.valid_value:
            return el.valid_value
        return _FORMAT_DEFAULTS.get(el.input_format, "test_value")
