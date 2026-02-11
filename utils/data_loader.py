"""
測試資料載入器
支援從 JSON / CSV 載入測試資料，搭配 pytest.mark.parametrize 做資料驅動測試。
"""

import csv
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "test_data"


def load_json(filename: str) -> list[dict]:
    """從 JSON 檔載入測試資料"""
    filepath = DATA_DIR / filename
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def load_csv(filename: str) -> list[dict]:
    """從 CSV 檔載入測試資料"""
    filepath = DATA_DIR / filename
    with open(filepath, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def get_test_ids(data: list[dict], key: str = "case_id") -> list[str]:
    """從測試資料中提取 case_id 作為 pytest 的 test ID"""
    return [item.get(key, str(i)) for i, item in enumerate(data)]
