"""
utils.data_loader 單元測試
驗證 JSON / CSV / YAML 載入與自動偵測。
"""

import json
import csv
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from utils.data_loader import (
    load_json,
    load_csv,
    load_yaml,
    load_data,
    get_test_ids,
    DATA_DIR,
)


@pytest.fixture(autouse=True)
def ensure_data_dir():
    """確保 test_data 目錄存在"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    yield


@pytest.mark.unit
class TestLoadJson:
    """load_json 函式"""

    @pytest.mark.unit
    def test_load_json(self, tmp_path, monkeypatch):
        """載入 JSON 檔案"""
        data = [{"case_id": "T1", "value": "hello"}]
        filepath = DATA_DIR / "_unit_test.json"
        filepath.write_text(json.dumps(data), encoding="utf-8")
        try:
            result = load_json("_unit_test.json")
            assert result == data
        finally:
            filepath.unlink(missing_ok=True)


@pytest.mark.unit
class TestLoadCsv:
    """load_csv 函式"""

    @pytest.mark.unit
    def test_load_csv(self):
        """載入 CSV 檔案"""
        filepath = DATA_DIR / "_unit_test.csv"
        filepath.write_text("case_id,value\nT1,hello\nT2,world", encoding="utf-8")
        try:
            result = load_csv("_unit_test.csv")
            assert len(result) == 2
            assert result[0]["case_id"] == "T1"
            assert result[1]["value"] == "world"
        finally:
            filepath.unlink(missing_ok=True)

    @pytest.mark.unit
    def test_load_csv_reads_correctly(self, tmp_path):
        """CSV 載入後每一列為 dict"""
        test_dir = tmp_path / "test_data"
        test_dir.mkdir()
        csv_file = test_dir / "sample.csv"
        csv_file.write_text("name,age,city\nAlice,30,Taipei\nBob,25,Tokyo", encoding="utf-8")

        with patch("utils.data_loader.DATA_DIR", test_dir):
            result = load_csv("sample.csv")

        assert len(result) == 2
        assert result[0]["name"] == "Alice"
        assert result[0]["age"] == "30"
        assert result[1]["city"] == "Tokyo"


@pytest.mark.unit
class TestLoadYaml:
    """load_yaml 函式"""

    @pytest.mark.unit
    def test_load_yaml_list_data(self, tmp_path):
        """YAML 內容為 list 時直接回傳"""
        test_dir = tmp_path / "test_data"
        test_dir.mkdir()
        yaml_file = test_dir / "list_data.yaml"
        yaml_file.write_text(
            "- case_id: T1\n  value: hello\n- case_id: T2\n  value: world\n",
            encoding="utf-8",
        )

        with patch("utils.data_loader.DATA_DIR", test_dir):
            result = load_yaml("list_data.yaml")

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["case_id"] == "T1"

    @pytest.mark.unit
    def test_load_yaml_dict_with_cases_key(self, tmp_path):
        """YAML 內容為 dict 且有 'cases' key 時回傳 cases"""
        test_dir = tmp_path / "test_data"
        test_dir.mkdir()
        yaml_file = test_dir / "cases_data.yaml"
        yaml_file.write_text(
            "cases:\n  - case_id: T1\n    value: hello\n  - case_id: T2\n    value: world\n",
            encoding="utf-8",
        )

        with patch("utils.data_loader.DATA_DIR", test_dir):
            result = load_yaml("cases_data.yaml")

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["case_id"] == "T1"

    @pytest.mark.unit
    def test_load_yaml_single_dict_wrapped_in_list(self, tmp_path):
        """YAML 內容為單一 dict（無 cases key）時包裝為 list"""
        test_dir = tmp_path / "test_data"
        test_dir.mkdir()
        yaml_file = test_dir / "single.yaml"
        yaml_file.write_text("name: test\nvalue: 42\n", encoding="utf-8")

        with patch("utils.data_loader.DATA_DIR", test_dir):
            result = load_yaml("single.yaml")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["name"] == "test"
        assert result[0]["value"] == 42

    @pytest.mark.unit
    def test_load_yaml_import_error(self):
        """yaml 未安裝時拋出 ImportError"""
        import importlib
        import utils.data_loader as dl_module

        original_load_yaml_code = dl_module.load_yaml

        # 模擬 yaml 無法 import 的情況
        with patch.dict("sys.modules", {"yaml": None}):
            # 需要重新定義函式讓 import yaml 在函式內觸發
            with pytest.raises(ImportError, match="PyYAML"):
                # 直接在此觸發 import 失敗
                import sys
                saved = sys.modules.get("yaml")
                sys.modules["yaml"] = None
                try:
                    # 重新載入模組以觸發 import
                    importlib.reload(dl_module)
                    dl_module.load_yaml("test.yaml")
                finally:
                    if saved is not None:
                        sys.modules["yaml"] = saved
                    else:
                        sys.modules.pop("yaml", None)
                    importlib.reload(dl_module)


@pytest.mark.unit
class TestLoadData:
    """load_data 自動偵測"""

    @pytest.mark.unit
    def test_auto_detect_json(self):
        """自動偵測 .json"""
        filepath = DATA_DIR / "_unit_auto.json"
        filepath.write_text('[{"a": 1}]', encoding="utf-8")
        try:
            result = load_data("_unit_auto.json")
            assert result == [{"a": 1}]
        finally:
            filepath.unlink(missing_ok=True)

    @pytest.mark.unit
    def test_auto_detect_csv(self):
        """自動偵測 .csv"""
        filepath = DATA_DIR / "_unit_auto.csv"
        filepath.write_text("a,b\n1,2", encoding="utf-8")
        try:
            result = load_data("_unit_auto.csv")
            assert result[0]["a"] == "1"
        finally:
            filepath.unlink(missing_ok=True)

    @pytest.mark.unit
    def test_auto_detect_yaml(self, tmp_path):
        """自動偵測 .yaml"""
        test_dir = tmp_path / "test_data"
        test_dir.mkdir()
        yaml_file = test_dir / "auto.yaml"
        yaml_file.write_text("- key: val\n", encoding="utf-8")

        with patch("utils.data_loader.DATA_DIR", test_dir):
            result = load_data("auto.yaml")

        assert result == [{"key": "val"}]

    @pytest.mark.unit
    def test_auto_detect_yml(self, tmp_path):
        """自動偵測 .yml"""
        test_dir = tmp_path / "test_data"
        test_dir.mkdir()
        yml_file = test_dir / "auto.yml"
        yml_file.write_text("- x: 1\n", encoding="utf-8")

        with patch("utils.data_loader.DATA_DIR", test_dir):
            result = load_data("auto.yml")

        assert result == [{"x": 1}]

    @pytest.mark.unit
    def test_unsupported_format(self):
        """不支援的格式拋出 ValueError"""
        with pytest.raises(ValueError, match="不支援"):
            load_data("test.xlsx")


@pytest.mark.unit
class TestGetTestIds:
    """get_test_ids 函式"""

    @pytest.mark.unit
    def test_with_case_id(self):
        """有 case_id key 時使用其值"""
        data = [{"case_id": "A"}, {"case_id": "B"}]
        assert get_test_ids(data) == ["A", "B"]

    @pytest.mark.unit
    def test_without_case_id(self):
        """無 case_id key 時使用索引"""
        data = [{"x": 1}, {"x": 2}]
        ids = get_test_ids(data)
        assert ids == ["0", "1"]

    @pytest.mark.unit
    def test_custom_key(self):
        """自訂 key"""
        data = [{"name": "foo"}, {"name": "bar"}]
        assert get_test_ids(data, key="name") == ["foo", "bar"]
