"""
utils.network_simulator 單元測試
驗證 NetworkSimulator 的網路模擬功能，包含預設設定檔、離線模式、自訂設定與 ADB 指令。
"""

import subprocess
import pytest
from unittest.mock import MagicMock, patch, call

from utils.network_simulator import NetworkProfile, PROFILES, NetworkSimulator


def _make_driver() -> MagicMock:
    """建立模擬 driver"""
    driver = MagicMock()
    driver.network_connection = 6  # wifi + data
    return driver


@pytest.mark.unit
class TestNetworkProfileDataclass:
    """NetworkProfile 資料類別"""

    @pytest.mark.unit
    def test_create_profile(self):
        """建立 NetworkProfile 實例"""
        profile = NetworkProfile(
            name="Test", latency_ms=100, download_kbps=500,
            upload_kbps=250, packet_loss=5
        )
        assert profile.name == "Test"
        assert profile.latency_ms == 100
        assert profile.download_kbps == 500
        assert profile.upload_kbps == 250
        assert profile.packet_loss == 5

    @pytest.mark.unit
    def test_default_packet_loss_is_zero(self):
        """packet_loss 預設為 0"""
        profile = NetworkProfile(
            name="NoLoss", latency_ms=10, download_kbps=1000, upload_kbps=500
        )
        assert profile.packet_loss == 0


@pytest.mark.unit
class TestProfiles:
    """PROFILES 預設設定檔"""

    @pytest.mark.unit
    def test_profiles_has_expected_keys(self):
        """PROFILES 包含所有預期的網路類型"""
        expected_keys = {"2g", "3g", "4g", "wifi", "lossy", "slow"}
        assert set(PROFILES.keys()) == expected_keys

    @pytest.mark.unit
    def test_profiles_2g_has_high_latency(self):
        """2G 設定檔有高延遲"""
        assert PROFILES["2g"].latency_ms >= 500

    @pytest.mark.unit
    def test_profiles_wifi_has_low_latency(self):
        """WiFi 設定檔有低延遲"""
        assert PROFILES["wifi"].latency_ms <= 20

    @pytest.mark.unit
    def test_profiles_lossy_has_high_packet_loss(self):
        """lossy 設定檔有高丟包率"""
        assert PROFILES["lossy"].packet_loss >= 10


@pytest.mark.unit
class TestNetworkSimulatorInit:
    """NetworkSimulator 初始化"""

    @pytest.mark.unit
    def test_init_default_android(self):
        """預設為 Android 平台"""
        driver = _make_driver()
        sim = NetworkSimulator(driver)
        assert sim._platform == "android"
        assert sim._driver is driver
        assert sim._original_state is None
        assert sim._tc_active is False

    @pytest.mark.unit
    def test_init_ios(self):
        """iOS 平台初始化"""
        driver = _make_driver()
        sim = NetworkSimulator(driver, platform="iOS")
        assert sim._platform == "ios"

    @pytest.mark.unit
    def test_init_case_insensitive(self):
        """平台名稱不分大小寫"""
        driver = _make_driver()
        sim = NetworkSimulator(driver, platform="ANDROID")
        assert sim._platform == "android"


@pytest.mark.unit
class TestNetworkSimulatorSetProfiles:
    """NetworkSimulator 預設設定檔方法"""

    @pytest.mark.unit
    def test_set_2g_calls_apply_profile(self):
        """set_2g 呼叫 _apply_profile 並傳入 2g 設定"""
        driver = _make_driver()
        sim = NetworkSimulator(driver)
        with patch.object(sim, "_apply_profile") as mock_apply:
            sim.set_2g()
            mock_apply.assert_called_once_with(PROFILES["2g"])

    @pytest.mark.unit
    def test_set_3g_calls_apply_profile(self):
        """set_3g 呼叫 _apply_profile 並傳入 3g 設定"""
        driver = _make_driver()
        sim = NetworkSimulator(driver)
        with patch.object(sim, "_apply_profile") as mock_apply:
            sim.set_3g()
            mock_apply.assert_called_once_with(PROFILES["3g"])

    @pytest.mark.unit
    def test_set_4g_calls_apply_profile(self):
        """set_4g 呼叫 _apply_profile 並傳入 4g 設定"""
        driver = _make_driver()
        sim = NetworkSimulator(driver)
        with patch.object(sim, "_apply_profile") as mock_apply:
            sim.set_4g()
            mock_apply.assert_called_once_with(PROFILES["4g"])

    @pytest.mark.unit
    def test_set_wifi_calls_apply_profile(self):
        """set_wifi 呼叫 _apply_profile 並傳入 wifi 設定"""
        driver = _make_driver()
        sim = NetworkSimulator(driver)
        with patch.object(sim, "_apply_profile") as mock_apply:
            sim.set_wifi()
            mock_apply.assert_called_once_with(PROFILES["wifi"])

    @pytest.mark.unit
    def test_set_lossy_calls_apply_profile(self):
        """set_lossy 呼叫 _apply_profile 並傳入 lossy 設定"""
        driver = _make_driver()
        sim = NetworkSimulator(driver)
        with patch.object(sim, "_apply_profile") as mock_apply:
            sim.set_lossy()
            mock_apply.assert_called_once_with(PROFILES["lossy"])

    @pytest.mark.unit
    def test_set_slow_calls_apply_profile(self):
        """set_slow 呼叫 _apply_profile 並傳入 slow 設定"""
        driver = _make_driver()
        sim = NetworkSimulator(driver)
        with patch.object(sim, "_apply_profile") as mock_apply:
            sim.set_slow()
            mock_apply.assert_called_once_with(PROFILES["slow"])


@pytest.mark.unit
class TestNetworkSimulatorSetOffline:
    """NetworkSimulator.set_offline 方法"""

    @pytest.mark.unit
    def test_set_offline_android_tries_set_network_connection(self):
        """Android 嘗試呼叫 set_network_connection(0)"""
        driver = _make_driver()
        sim = NetworkSimulator(driver)
        sim.set_offline()
        driver.set_network_connection.assert_called_once_with(0)

    @pytest.mark.unit
    def test_set_offline_android_fallback_to_adb(self):
        """Android set_network_connection 失敗時 fallback 到 ADB"""
        driver = _make_driver()
        driver.set_network_connection.side_effect = Exception("Not supported")
        sim = NetworkSimulator(driver)

        with patch.object(sim, "_adb") as mock_adb:
            sim.set_offline()
            assert mock_adb.call_count == 2
            mock_adb.assert_any_call("svc wifi disable")
            mock_adb.assert_any_call("svc data disable")

    @pytest.mark.unit
    def test_set_offline_non_android_warns(self):
        """非 Android 平台只發出警告"""
        driver = _make_driver()
        sim = NetworkSimulator(driver, platform="ios")
        sim.set_offline()
        driver.set_network_connection.assert_not_called()


@pytest.mark.unit
class TestNetworkSimulatorSetWifiOnly:
    """NetworkSimulator.set_wifi_only 方法"""

    @pytest.mark.unit
    def test_set_wifi_only_android_calls_set_network_connection(self):
        """Android 呼叫 set_network_connection(2)"""
        driver = _make_driver()
        sim = NetworkSimulator(driver)
        sim.set_wifi_only()
        driver.set_network_connection.assert_called_once_with(2)

    @pytest.mark.unit
    def test_set_wifi_only_android_fallback_to_adb(self):
        """Android set_network_connection 失敗時 fallback 到 ADB"""
        driver = _make_driver()
        driver.set_network_connection.side_effect = Exception("Not supported")
        sim = NetworkSimulator(driver)

        with patch.object(sim, "_adb") as mock_adb:
            sim.set_wifi_only()
            mock_adb.assert_any_call("svc data disable")
            mock_adb.assert_any_call("svc wifi enable")

    @pytest.mark.unit
    def test_set_wifi_only_non_android_does_nothing(self):
        """非 Android 平台不執行任何操作"""
        driver = _make_driver()
        sim = NetworkSimulator(driver, platform="ios")
        sim.set_wifi_only()
        driver.set_network_connection.assert_not_called()


@pytest.mark.unit
class TestNetworkSimulatorSetDataOnly:
    """NetworkSimulator.set_data_only 方法"""

    @pytest.mark.unit
    def test_set_data_only_android_calls_set_network_connection(self):
        """Android 呼叫 set_network_connection(4)"""
        driver = _make_driver()
        sim = NetworkSimulator(driver)
        sim.set_data_only()
        driver.set_network_connection.assert_called_once_with(4)

    @pytest.mark.unit
    def test_set_data_only_android_fallback_to_adb(self):
        """Android set_network_connection 失敗時 fallback 到 ADB"""
        driver = _make_driver()
        driver.set_network_connection.side_effect = Exception("Not supported")
        sim = NetworkSimulator(driver)

        with patch.object(sim, "_adb") as mock_adb:
            sim.set_data_only()
            mock_adb.assert_any_call("svc wifi disable")
            mock_adb.assert_any_call("svc data enable")


@pytest.mark.unit
class TestNetworkSimulatorSetCustom:
    """NetworkSimulator.set_custom 方法"""

    @pytest.mark.unit
    def test_set_custom_creates_custom_profile(self):
        """set_custom 建立自訂設定檔並套用"""
        driver = _make_driver()
        sim = NetworkSimulator(driver)

        with patch.object(sim, "_apply_profile") as mock_apply:
            sim.set_custom(latency_ms=500, download_kbps=128,
                           upload_kbps=64, packet_loss=10)
            called_profile = mock_apply.call_args[0][0]
            assert called_profile.name == "自訂"
            assert called_profile.latency_ms == 500
            assert called_profile.download_kbps == 128
            assert called_profile.upload_kbps == 64
            assert called_profile.packet_loss == 10


@pytest.mark.unit
class TestNetworkSimulatorReset:
    """NetworkSimulator.reset 方法"""

    @pytest.mark.unit
    def test_reset_clears_tc_rules_when_active(self):
        """有 tc 規則時清除"""
        driver = _make_driver()
        sim = NetworkSimulator(driver)
        sim._tc_active = True
        sim._original_state = 6

        with patch.object(sim, "_adb_shell") as mock_adb:
            sim.reset()
            # 應清除 wlan0 和 rmnet0 的 tc 規則
            mock_adb.assert_any_call("tc qdisc del dev wlan0 root", ignore_error=True)
            mock_adb.assert_any_call("tc qdisc del dev rmnet0 root", ignore_error=True)
            assert sim._tc_active is False

    @pytest.mark.unit
    def test_reset_restores_original_state(self):
        """恢復原始網路狀態"""
        driver = _make_driver()
        sim = NetworkSimulator(driver)
        sim._original_state = 6

        sim.reset()
        driver.set_network_connection.assert_called_once_with(6)

    @pytest.mark.unit
    def test_reset_fallback_adb_enable_all(self):
        """set_network_connection 失敗時用 ADB 全部啟用"""
        driver = _make_driver()
        driver.set_network_connection.side_effect = Exception("fail")
        sim = NetworkSimulator(driver)
        sim._original_state = 6

        with patch.object(sim, "_adb") as mock_adb, \
             patch.object(sim, "_adb_shell"):
            sim.reset()
            mock_adb.assert_any_call("svc wifi enable")
            mock_adb.assert_any_call("svc data enable")

    @pytest.mark.unit
    def test_reset_no_original_state_enables_all(self):
        """無原始狀態時用 ADB 全部啟用"""
        driver = _make_driver()
        sim = NetworkSimulator(driver)
        sim._original_state = None

        with patch.object(sim, "_adb") as mock_adb:
            sim.reset()
            mock_adb.assert_any_call("svc wifi enable")
            mock_adb.assert_any_call("svc data enable")


@pytest.mark.unit
class TestNetworkSimulatorCurrentState:
    """NetworkSimulator.current_state 屬性"""

    @pytest.mark.unit
    def test_current_state_android_returns_network_info(self):
        """Android 回傳網路資訊字典"""
        driver = _make_driver()
        driver.network_connection = 6  # wifi(2) + data(4)
        sim = NetworkSimulator(driver)

        state = sim.current_state
        assert state["airplane"] is False  # 6 & 1 = 0
        assert state["wifi"] is True       # 6 & 2 = 2
        assert state["data"] is True       # 6 & 4 = 4
        assert state["raw"] == 6

    @pytest.mark.unit
    def test_current_state_android_exception(self):
        """Android 取得網路狀態異常時回傳 unknown"""
        driver = _make_driver()
        type(driver).network_connection = property(
            lambda self: (_ for _ in ()).throw(Exception("fail"))
        )
        sim = NetworkSimulator(driver)
        state = sim.current_state
        assert state == {"unknown": True}

    @pytest.mark.unit
    def test_current_state_non_android(self):
        """非 Android 平台回傳 unknown"""
        driver = _make_driver()
        sim = NetworkSimulator(driver, platform="ios")
        state = sim.current_state
        assert state == {"unknown": True}


@pytest.mark.unit
class TestNetworkSimulatorApplyProfile:
    """NetworkSimulator._apply_profile 方法"""

    @pytest.mark.unit
    def test_apply_profile_non_android_warns(self):
        """非 Android 平台發出警告並返回"""
        driver = _make_driver()
        sim = NetworkSimulator(driver, platform="ios")

        with patch.object(sim, "_adb_shell") as mock_adb:
            sim._apply_profile(PROFILES["3g"])
            mock_adb.assert_not_called()

    @pytest.mark.unit
    def test_apply_profile_android_runs_tc_commands(self):
        """Android 平台執行 tc 指令"""
        driver = _make_driver()
        sim = NetworkSimulator(driver)

        with patch.object(sim, "_adb_shell") as mock_adb:
            sim._apply_profile(PROFILES["3g"])
            # 應先清除舊規則再建立新規則
            assert mock_adb.call_count == 2
            # 第一次呼叫: 清除
            first_call = mock_adb.call_args_list[0]
            assert "tc qdisc del" in first_call[0][0]
            # 第二次呼叫: 建立新規則
            second_call = mock_adb.call_args_list[1]
            assert "tc qdisc add" in second_call[0][0]
            assert sim._tc_active is True

    @pytest.mark.unit
    def test_apply_profile_includes_packet_loss(self):
        """有丟包率時指令中包含 loss 參數"""
        driver = _make_driver()
        sim = NetworkSimulator(driver)

        with patch.object(sim, "_adb_shell") as mock_adb:
            sim._apply_profile(PROFILES["lossy"])
            add_call = mock_adb.call_args_list[1][0][0]
            assert "loss" in add_call
            assert "20%" in add_call


@pytest.mark.unit
class TestNetworkSimulatorSaveOriginalState:
    """NetworkSimulator._save_original_state 方法"""

    @pytest.mark.unit
    def test_save_original_state_only_saves_once(self):
        """只儲存一次原始狀態"""
        driver = _make_driver()
        driver.network_connection = 6
        sim = NetworkSimulator(driver)

        sim._save_original_state()
        assert sim._original_state == 6

        # 再次呼叫不應改變
        driver.network_connection = 2
        sim._save_original_state()
        assert sim._original_state == 6  # 仍然是第一次的值

    @pytest.mark.unit
    def test_save_original_state_exception_defaults_to_6(self):
        """取得 network_connection 異常時預設為 6"""
        driver = _make_driver()
        type(driver).network_connection = property(
            lambda self: (_ for _ in ()).throw(Exception("fail"))
        )
        sim = NetworkSimulator(driver)
        sim._save_original_state()
        assert sim._original_state == 6


@pytest.mark.unit
class TestNetworkSimulatorAdbShell:
    """NetworkSimulator._adb_shell 方法"""

    @pytest.mark.unit
    def test_adb_shell_success(self):
        """ADB 指令成功執行"""
        driver = _make_driver()
        sim = NetworkSimulator(driver)

        with patch("utils.network_simulator.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="output\n", stderr="")
            result = sim._adb_shell("ls /sdcard")
            assert result == "output"
            mock_run.assert_called_once_with(
                ["adb", "shell", "ls /sdcard"],
                capture_output=True, text=True, timeout=10,
            )

    @pytest.mark.unit
    def test_adb_shell_timeout(self):
        """ADB 指令超時"""
        driver = _make_driver()
        sim = NetworkSimulator(driver)

        with patch("utils.network_simulator.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="adb", timeout=10)
            result = sim._adb_shell("slow_cmd", ignore_error=True)
            assert result == ""

    @pytest.mark.unit
    def test_adb_shell_ignore_error(self):
        """ignore_error=True 時不因非零 returncode 而報錯"""
        driver = _make_driver()
        sim = NetworkSimulator(driver)

        with patch("utils.network_simulator.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error msg")
            result = sim._adb_shell("bad_cmd", ignore_error=True)
            assert result == ""

    @pytest.mark.unit
    def test_adb_shell_file_not_found(self):
        """adb 不存在時處理 FileNotFoundError"""
        driver = _make_driver()
        sim = NetworkSimulator(driver)

        with patch("utils.network_simulator.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("adb not found")
            result = sim._adb_shell("cmd", ignore_error=True)
            assert result == ""


@pytest.mark.unit
class TestNetworkSimulatorContextManager:
    """NetworkSimulator 上下文管理器"""

    @pytest.mark.unit
    def test_enter_returns_self(self):
        """__enter__ 回傳自身"""
        driver = _make_driver()
        sim = NetworkSimulator(driver)
        result = sim.__enter__()
        assert result is sim

    @pytest.mark.unit
    def test_exit_calls_reset(self):
        """__exit__ 呼叫 reset"""
        driver = _make_driver()
        sim = NetworkSimulator(driver)

        with patch.object(sim, "reset") as mock_reset:
            sim.__exit__(None, None, None)
            mock_reset.assert_called_once()

    @pytest.mark.unit
    def test_context_manager_usage(self):
        """with 語句使用"""
        driver = _make_driver()

        with patch.object(NetworkSimulator, "reset") as mock_reset:
            with NetworkSimulator(driver) as sim:
                assert isinstance(sim, NetworkSimulator)
            mock_reset.assert_called_once()
