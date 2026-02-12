"""
utils.parallel 單元測試
驗證多裝置平行測試的裝置設定取得與 Appium port 計算功能。
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from utils.parallel import get_device_config, get_appium_port


@pytest.mark.unit
class TestGetDeviceConfig:
    """get_device_config 函式"""

    @pytest.mark.unit
    def test_master_returns_default_caps(self):
        """worker_id='master' 時回傳 Config.load_caps()"""
        mock_caps = {"platformName": "Android", "appium:deviceName": "emulator-5554"}
        with patch("utils.parallel.Config.load_caps", return_value=mock_caps) as mock_load:
            result = get_device_config("master")
            mock_load.assert_called_once()
            assert result == mock_caps

    @pytest.mark.unit
    def test_gw0_returns_first_device(self, tmp_path):
        """worker_id='gw0' 時回傳第一台裝置設定"""
        devices = [
            {"platformName": "Android", "appium:deviceName": "device-0"},
            {"platformName": "Android", "appium:deviceName": "device-1"},
        ]
        devices_file = tmp_path / "devices.json"
        devices_file.write_text(json.dumps(devices), encoding="utf-8")

        with patch("utils.parallel.DEVICES_FILE", devices_file):
            result = get_device_config("gw0")
            assert result["appium:deviceName"] == "device-0"

    @pytest.mark.unit
    def test_gw1_returns_second_device(self, tmp_path):
        """worker_id='gw1' 時回傳第二台裝置設定"""
        devices = [
            {"platformName": "Android", "appium:deviceName": "device-0"},
            {"platformName": "Android", "appium:deviceName": "device-1"},
        ]
        devices_file = tmp_path / "devices.json"
        devices_file.write_text(json.dumps(devices), encoding="utf-8")

        with patch("utils.parallel.DEVICES_FILE", devices_file):
            result = get_device_config("gw1")
            assert result["appium:deviceName"] == "device-1"

    @pytest.mark.unit
    def test_out_of_range_raises_index_error(self, tmp_path):
        """worker_id 超出裝置數量時拋出 IndexError"""
        devices = [
            {"platformName": "Android", "appium:deviceName": "device-0"},
        ]
        devices_file = tmp_path / "devices.json"
        devices_file.write_text(json.dumps(devices), encoding="utf-8")

        with patch("utils.parallel.DEVICES_FILE", devices_file):
            with pytest.raises(IndexError, match="沒有對應的裝置設定"):
                get_device_config("gw5")

    @pytest.mark.unit
    def test_no_devices_json_returns_default_caps(self, tmp_path):
        """devices.json 不存在時回傳 Config.load_caps()"""
        nonexistent = tmp_path / "nonexistent_devices.json"
        mock_caps = {"platformName": "Android", "appium:deviceName": "default"}

        with patch("utils.parallel.DEVICES_FILE", nonexistent), \
             patch("utils.parallel.Config.load_caps", return_value=mock_caps):
            result = get_device_config("gw0")
            assert result == mock_caps


@pytest.mark.unit
class TestGetAppiumPort:
    """get_appium_port 函式"""

    @pytest.mark.unit
    def test_master_returns_base_port(self):
        """worker_id='master' 時回傳 base_port"""
        assert get_appium_port("master") == 4723

    @pytest.mark.unit
    def test_master_custom_base_port(self):
        """worker_id='master' 搭配自訂 base_port"""
        assert get_appium_port("master", base_port=5000) == 5000

    @pytest.mark.unit
    def test_gw0_returns_base_port_plus_0(self):
        """gw0 回傳 base_port + 0"""
        assert get_appium_port("gw0") == 4723

    @pytest.mark.unit
    def test_gw1_returns_base_port_plus_1(self):
        """gw1 回傳 base_port + 1"""
        assert get_appium_port("gw1") == 4724

    @pytest.mark.unit
    def test_gw2_returns_base_port_plus_2(self):
        """gw2 回傳 base_port + 2"""
        assert get_appium_port("gw2") == 4725

    @pytest.mark.unit
    def test_gw_with_custom_base_port(self):
        """自訂 base_port 的計算"""
        assert get_appium_port("gw3", base_port=5000) == 5003

    @pytest.mark.unit
    def test_gw_high_index(self):
        """高編號 worker 的 port 計算"""
        assert get_appium_port("gw10") == 4733
