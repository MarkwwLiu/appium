"""
測試資料載入器
支援從 JSON / CSV / YAML 載入測試資料，搭配 pytest.mark.parametrize 做資料驅動測試。

用法：
    from utils.data_loader import load_data, load_json, load_csv, load_yaml

    # 自動偵測格式
    data = load_data("login_data.json")
    data = load_data("login_data.csv")
    data = load_data("login_data.yaml")

    # 搭配 parametrize
    @pytest.mark.parametrize("case", load_data("login.json"), ids=get_test_ids(data))
    def test_login(case):
        ...
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


def load_yaml(filename: str) -> list[dict]:
    """
    從 YAML 檔載入測試資料。

    需要安裝 PyYAML: pip install pyyaml
    """
    try:
        import yaml
    except ImportError:
        raise ImportError(
            "載入 YAML 需要 PyYAML 套件，請執行: pip install pyyaml"
        )
    filepath = DATA_DIR / filename
    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "cases" in data:
        return data["cases"]
    return [data]


def load_data(filename: str) -> list[dict]:
    """
    自動偵測檔案格式並載入測試資料。

    支援副檔名: .json, .csv, .yaml, .yml
    """
    suffix = Path(filename).suffix.lower()
    loaders = {
        ".json": load_json,
        ".csv": load_csv,
        ".yaml": load_yaml,
        ".yml": load_yaml,
    }
    loader = loaders.get(suffix)
    if loader is None:
        raise ValueError(
            f"不支援的檔案格式: {suffix} "
            f"(支援: {', '.join(loaders.keys())})"
        )
    return loader(filename)


def get_test_ids(data: list[dict], key: str = "case_id") -> list[str]:
    """從測試資料中提取 case_id 作為 pytest 的 test ID"""
    return [item.get(key, str(i)) for i, item in enumerate(data)]
