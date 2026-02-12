"""
utils.app_manager 單元測試
驗證 AppManager 的 App 生命週期管理功能。
"""

import pytest
from unittest.mock import MagicMock, patch, call


@pytest.mark.unit
class TestInstallApp:
    """install_app — 安裝 App"""

    @pytest.mark.unit
    def test_calls_driver_install_app(self):
        """呼叫 driver.install_app 並傳入正確路徑"""
        from utils.app_manager import AppManager

        driver = MagicMock()
        manager = AppManager(driver)
        manager.install_app("/path/to/app.apk")

        driver.install_app.assert_called_once_with("/path/to/app.apk")


@pytest.mark.unit
class TestRemoveApp:
    """remove_app — 移除 App"""

    @pytest.mark.unit
    def test_calls_driver_remove_app(self):
        """呼叫 driver.remove_app 並傳入正確 bundle_id"""
        from utils.app_manager import AppManager

        driver = MagicMock()
        manager = AppManager(driver)
        manager.remove_app("com.example.app")

        driver.remove_app.assert_called_once_with("com.example.app")


@pytest.mark.unit
class TestIsAppInstalled:
    """is_app_installed — 檢查 App 是否安裝"""

    @pytest.mark.unit
    def test_returns_true_when_installed(self):
        """已安裝時回傳 True"""
        from utils.app_manager import AppManager

        driver = MagicMock()
        driver.is_app_installed.return_value = True
        manager = AppManager(driver)

        assert manager.is_app_installed("com.example.app") is True

    @pytest.mark.unit
    def test_returns_false_when_not_installed(self):
        """未安裝時回傳 False"""
        from utils.app_manager import AppManager

        driver = MagicMock()
        driver.is_app_installed.return_value = False
        manager = AppManager(driver)

        assert manager.is_app_installed("com.missing.app") is False

    @pytest.mark.unit
    def test_calls_driver_is_app_installed(self):
        """呼叫 driver.is_app_installed"""
        from utils.app_manager import AppManager

        driver = MagicMock()
        manager = AppManager(driver)
        manager.is_app_installed("com.example.app")

        driver.is_app_installed.assert_called_once_with("com.example.app")


@pytest.mark.unit
class TestLaunchApp:
    """launch_app — 啟動 App"""

    @pytest.mark.unit
    def test_calls_driver_activate_app(self):
        """呼叫 driver.activate_app"""
        from utils.app_manager import AppManager

        driver = MagicMock()
        manager = AppManager(driver)
        manager.launch_app("com.example.app")

        driver.activate_app.assert_called_once_with("com.example.app")


@pytest.mark.unit
class TestTerminateApp:
    """terminate_app — 強制結束 App"""

    @pytest.mark.unit
    def test_calls_driver_terminate_app(self):
        """呼叫 driver.terminate_app"""
        from utils.app_manager import AppManager

        driver = MagicMock()
        manager = AppManager(driver)
        manager.terminate_app("com.example.app")

        driver.terminate_app.assert_called_once_with("com.example.app")


@pytest.mark.unit
class TestResetApp:
    """reset_app — 重啟 App"""

    @pytest.mark.unit
    def test_calls_terminate_then_launch(self):
        """先呼叫 terminate_app 再呼叫 launch_app"""
        from utils.app_manager import AppManager

        driver = MagicMock()
        manager = AppManager(driver)
        manager.reset_app("com.example.app")

        # 驗證呼叫順序
        driver.terminate_app.assert_called_once_with("com.example.app")
        driver.activate_app.assert_called_once_with("com.example.app")

    @pytest.mark.unit
    def test_terminate_called_before_launch(self):
        """確認 terminate 在 activate 之前呼叫"""
        from utils.app_manager import AppManager

        driver = MagicMock()
        call_order = []
        driver.terminate_app.side_effect = lambda x: call_order.append("terminate")
        driver.activate_app.side_effect = lambda x: call_order.append("activate")

        manager = AppManager(driver)
        manager.reset_app("com.example.app")

        assert call_order == ["terminate", "activate"]


@pytest.mark.unit
class TestBackgroundApp:
    """background_app — App 進入背景"""

    @pytest.mark.unit
    def test_calls_driver_background_app(self):
        """呼叫 driver.background_app 並傳入秒數"""
        from utils.app_manager import AppManager

        driver = MagicMock()
        manager = AppManager(driver)
        manager.background_app(5)

        driver.background_app.assert_called_once_with(5)

    @pytest.mark.unit
    def test_default_seconds_is_3(self):
        """預設背景 3 秒"""
        from utils.app_manager import AppManager

        driver = MagicMock()
        manager = AppManager(driver)
        manager.background_app()

        driver.background_app.assert_called_once_with(3)


@pytest.mark.unit
class TestPutToBackground:
    """put_to_background — App 進入背景不自動回復"""

    @pytest.mark.unit
    def test_calls_driver_background_app_negative_one(self):
        """呼叫 driver.background_app(-1)"""
        from utils.app_manager import AppManager

        driver = MagicMock()
        manager = AppManager(driver)
        manager.put_to_background()

        driver.background_app.assert_called_once_with(-1)


@pytest.mark.unit
class TestOpenDeepLink:
    """open_deep_link — Deep Link 跳轉"""

    @pytest.mark.unit
    def test_with_bundle_id_calls_execute_script(self):
        """有 bundle_id 時呼叫 execute_script"""
        from utils.app_manager import AppManager

        driver = MagicMock()
        manager = AppManager(driver)
        manager.open_deep_link("myapp://product/123", bundle_id="com.example.app")

        driver.execute_script.assert_called_once_with(
            "mobile: deepLink",
            {"url": "myapp://product/123", "package": "com.example.app"},
        )

    @pytest.mark.unit
    def test_without_bundle_id_calls_driver_get(self):
        """沒有 bundle_id 時呼叫 driver.get"""
        from utils.app_manager import AppManager

        driver = MagicMock()
        manager = AppManager(driver)
        manager.open_deep_link("myapp://product/123")

        driver.get.assert_called_once_with("myapp://product/123")
        driver.execute_script.assert_not_called()

    @pytest.mark.unit
    def test_without_bundle_id_none_calls_driver_get(self):
        """bundle_id=None 時呼叫 driver.get"""
        from utils.app_manager import AppManager

        driver = MagicMock()
        manager = AppManager(driver)
        manager.open_deep_link("myapp://home", bundle_id=None)

        driver.get.assert_called_once_with("myapp://home")


@pytest.mark.unit
class TestGetAppState:
    """get_app_state — 取得 App 狀態"""

    @pytest.mark.unit
    def test_calls_query_app_state(self):
        """呼叫 driver.query_app_state"""
        from utils.app_manager import AppManager

        driver = MagicMock()
        driver.query_app_state.return_value = 4
        manager = AppManager(driver)

        manager.get_app_state("com.example.app")

        driver.query_app_state.assert_called_once_with("com.example.app")

    @pytest.mark.unit
    def test_returns_state_value(self):
        """回傳 state 值"""
        from utils.app_manager import AppManager

        driver = MagicMock()
        driver.query_app_state.return_value = 4
        manager = AppManager(driver)

        state = manager.get_app_state("com.example.app")
        assert state == 4

    @pytest.mark.unit
    def test_returns_not_running_state(self):
        """回傳 1 (未執行)"""
        from utils.app_manager import AppManager

        driver = MagicMock()
        driver.query_app_state.return_value = 1
        manager = AppManager(driver)

        state = manager.get_app_state("com.example.app")
        assert state == 1

    @pytest.mark.unit
    def test_returns_not_installed_state(self):
        """回傳 0 (未安裝)"""
        from utils.app_manager import AppManager

        driver = MagicMock()
        driver.query_app_state.return_value = 0
        manager = AppManager(driver)

        state = manager.get_app_state("com.missing.app")
        assert state == 0


@pytest.mark.unit
class TestClearAppData:
    """clear_app_data — 清除 App 資料"""

    @pytest.mark.unit
    def test_calls_subprocess_run(self):
        """呼叫 subprocess.run 執行 adb 指令"""
        from utils.app_manager import AppManager

        driver = MagicMock()
        manager = AppManager(driver)

        with patch("utils.app_manager.subprocess") as mock_subprocess:
            manager.clear_app_data("com.example.app")

            mock_subprocess.run.assert_called_once_with(
                ["adb", "shell", "pm", "clear", "com.example.app"],
                capture_output=True,
                text=True,
            )

    @pytest.mark.unit
    def test_correct_adb_command(self):
        """adb 指令格式正確"""
        from utils.app_manager import AppManager

        driver = MagicMock()
        manager = AppManager(driver)

        with patch("utils.app_manager.subprocess") as mock_subprocess:
            manager.clear_app_data("com.test.myapp")

            args = mock_subprocess.run.call_args[0][0]
            assert args == ["adb", "shell", "pm", "clear", "com.test.myapp"]
