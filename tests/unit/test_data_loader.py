"""
utils.data_loader 單元測試
驗證 JSON / CSV / YAML 載入與自動偵測。
"""

import json
import csv
import pytest
from pathlib import Path

from utils.data_loader import (
    load_json,
    load_csv,
    load_data,
    get_test_ids,
    DATA_DIR,
)


@pytest.fixture(autouse=True)
def ensure_data_dir():
    """確保 test_data 目錄存在"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    yield


class TestLoadJson:
    def test_load_json(self, tmp_path, monkeypatch):
        data = [{"case_id": "T1", "value": "hello"}]
        filepath = DATA_DIR / "_unit_test.json"
        filepath.write_text(json.dumps(data), encoding="utf-8")
        try:
            result = load_json("_unit_test.json")
            assert result == data
        finally:
            filepath.unlink(missing_ok=True)


class TestLoadCsv:
    def test_load_csv(self):
        filepath = DATA_DIR / "_unit_test.csv"
        filepath.write_text("case_id,value\nT1,hello\nT2,world", encoding="utf-8")
        try:
            result = load_csv("_unit_test.csv")
            assert len(result) == 2
            assert result[0]["case_id"] == "T1"
            assert result[1]["value"] == "world"
        finally:
            filepath.unlink(missing_ok=True)


class TestLoadData:
    def test_auto_detect_json(self):
        filepath = DATA_DIR / "_unit_auto.json"
        filepath.write_text('[{"a": 1}]', encoding="utf-8")
        try:
            result = load_data("_unit_auto.json")
            assert result == [{"a": 1}]
        finally:
            filepath.unlink(missing_ok=True)

    def test_auto_detect_csv(self):
        filepath = DATA_DIR / "_unit_auto.csv"
        filepath.write_text("a,b\n1,2", encoding="utf-8")
        try:
            result = load_data("_unit_auto.csv")
            assert result[0]["a"] == "1"
        finally:
            filepath.unlink(missing_ok=True)

    def test_unsupported_format(self):
        with pytest.raises(ValueError, match="不支援"):
            load_data("test.xlsx")


class TestGetTestIds:
    def test_with_case_id(self):
        data = [{"case_id": "A"}, {"case_id": "B"}]
        assert get_test_ids(data) == ["A", "B"]

    def test_without_case_id(self):
        data = [{"x": 1}, {"x": 2}]
        ids = get_test_ids(data)
        assert ids == ["0", "1"]

    def test_custom_key(self):
        data = [{"name": "foo"}, {"name": "bar"}]
        assert get_test_ids(data, key="name") == ["foo", "bar"]
