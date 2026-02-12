"""
core/recovery.py 單元測試

驗證 RecoveryRecord、RecoveryManager 的初始化、策略註冊、恢復邏輯、
歷史記錄、統計資料，以及所有內建恢復策略。
使用 mock driver 避免依賴真實 Appium 環境。
"""

import time
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from core.recovery import RecoveryRecord, RecoveryManager


@pytest.mark.unit
class TestRecoveryRecord:
    """RecoveryRecord 資料結構"""

    @pytest.mark.unit
    def test_fields_assigned(self):
        """欄位正確指派"""
        record = RecoveryRecord(
            strategy_name="test_strategy",
            success=True,
            detail="some detail",
        )
        assert record.strategy_name == "test_strategy"
        assert record.success is True
        assert record.detail == "some detail"

    @pytest.mark.unit
    def test_timestamp_auto_set(self):
        """timestamp 自動設定為當前時間"""
        before = time.time()
        record = RecoveryRecord(strategy_name="x", success=False)
        after = time.time()
        assert before <= record.timestamp <= after

    @pytest.mark.unit
    def test_default_detail_empty(self):
        """detail 預設為空字串"""
        record = RecoveryRecord(strategy_name="x", success=True)
        assert record.detail == ""

    @pytest.mark.unit
    def test_success_false(self):
        """success=False 正確儲存"""
        record = RecoveryRecord(strategy_name="fail", success=False)
        assert record.success is False


@pytest.mark.unit
class TestRecoveryManagerInit:
    """RecoveryManager 初始化"""

    @pytest.mark.unit
    def test_defaults_registered(self):
        """初始化時內建策略已註冊"""
        mgr = RecoveryManager()
        strategy_names = [name for name, _, _ in mgr._strategies]
        assert "permission_dialog" in strategy_names
        assert "anr_dialog" in strategy_names
        assert "system_dialog" in strategy_names
        assert "ios_alert" in strategy_names
        assert "webview_escape" in strategy_names
        assert "crash_restart" in strategy_names
        assert "back_button" in strategy_names

    @pytest.mark.unit
    def test_enabled_default_true(self):
        """預設啟用"""
        mgr = RecoveryManager()
        assert mgr.enabled is True

    @pytest.mark.unit
    def test_max_attempts_default(self):
        """預設最大嘗試次數為 3"""
        mgr = RecoveryManager()
        assert mgr.max_attempts == 3

    @pytest.mark.unit
    def test_history_starts_empty(self):
        """歷史記錄初始為空"""
        mgr = RecoveryManager()
        assert mgr._history == []


@pytest.mark.unit
class TestRecoveryManagerRegister:
    """RecoveryManager.register 裝飾器"""

    @pytest.mark.unit
    def test_register_adds_strategy(self):
        """register 新增策略"""
        mgr = RecoveryManager()
        initial_count = len(mgr._strategies)

        @mgr.register("custom_strategy", priority=5)
        def my_strategy(driver):
            return True

        assert len(mgr._strategies) == initial_count + 1
        names = [name for name, _, _ in mgr._strategies]
        assert "custom_strategy" in names

    @pytest.mark.unit
    def test_register_returns_original_function(self):
        """register 回傳原始函式"""
        mgr = RecoveryManager()

        @mgr.register("test_fn")
        def my_fn(driver):
            return True

        assert callable(my_fn)
        assert my_fn(None) is True

    @pytest.mark.unit
    def test_priority_ordering(self):
        """策略按 priority 排序"""
        mgr = RecoveryManager()

        @mgr.register("low_priority", priority=100)
        def low(driver):
            return False

        @mgr.register("high_priority", priority=1)
        def high(driver):
            return False

        priorities = [p for _, p, _ in mgr._strategies]
        assert priorities == sorted(priorities)

        # high_priority 應排在 low_priority 之前
        names = [name for name, _, _ in mgr._strategies]
        assert names.index("high_priority") < names.index("low_priority")

    @pytest.mark.unit
    def test_default_priority_is_50(self):
        """不指定 priority 預設為 50"""
        mgr = RecoveryManager()

        @mgr.register("default_prio")
        def fn(driver):
            return False

        matched = [(n, p) for n, p, _ in mgr._strategies if n == "default_prio"]
        assert len(matched) == 1
        assert matched[0][1] == 50


@pytest.mark.unit
class TestRecoveryManagerTryRecover:
    """RecoveryManager.try_recover"""

    @pytest.mark.unit
    @patch("core.recovery.time.sleep")
    def test_disabled_returns_false(self, mock_sleep):
        """disabled 時直接回傳 False"""
        mgr = RecoveryManager()
        mgr.enabled = False
        driver = MagicMock()
        result = mgr.try_recover(driver)
        assert result is False

    @pytest.mark.unit
    @patch("core.recovery.time.sleep")
    def test_strategy_succeeds_first_try(self, mock_sleep):
        """策略第一次就成功"""
        mgr = RecoveryManager()
        mgr._strategies = []  # 清除內建策略

        @mgr.register("always_succeed", priority=1)
        def succeed(driver):
            return True

        driver = MagicMock()
        result = mgr.try_recover(driver)
        assert result is True
        assert len(mgr._history) == 1
        assert mgr._history[0].success is True
        assert mgr._history[0].strategy_name == "always_succeed"

    @pytest.mark.unit
    @patch("core.recovery.time.sleep")
    def test_first_fails_second_succeeds(self, mock_sleep):
        """第一個策略失敗，第二個成功"""
        mgr = RecoveryManager()
        mgr._strategies = []

        @mgr.register("fail_strategy", priority=1)
        def fail(driver):
            return False

        @mgr.register("succeed_strategy", priority=2)
        def succeed(driver):
            return True

        driver = MagicMock()
        result = mgr.try_recover(driver)
        assert result is True
        # 歷史中有兩筆：第一筆失敗、第二筆成功
        assert len(mgr._history) == 2
        assert mgr._history[0].success is False
        assert mgr._history[1].success is True

    @pytest.mark.unit
    @patch("core.recovery.time.sleep")
    def test_all_strategies_fail(self, mock_sleep):
        """所有策略都失敗"""
        mgr = RecoveryManager()
        mgr._strategies = []
        mgr.max_attempts = 1

        @mgr.register("fail1", priority=1)
        def fail1(driver):
            return False

        @mgr.register("fail2", priority=2)
        def fail2(driver):
            return False

        driver = MagicMock()
        result = mgr.try_recover(driver)
        assert result is False

    @pytest.mark.unit
    @patch("core.recovery.time.sleep")
    def test_max_attempts_reached(self, mock_sleep):
        """嘗試次數達到上限"""
        mgr = RecoveryManager()
        mgr._strategies = []
        mgr.max_attempts = 2

        call_count = 0

        @mgr.register("counter", priority=1)
        def counter_strategy(driver):
            nonlocal call_count
            call_count += 1
            return False

        driver = MagicMock()
        result = mgr.try_recover(driver)
        assert result is False
        # max_attempts=2, 1 個策略 → 被呼叫 2 次
        assert call_count == 2

    @pytest.mark.unit
    @patch("core.recovery.time.sleep")
    def test_strategy_throws_exception(self, mock_sleep):
        """策略拋出例外，不影響後續策略"""
        mgr = RecoveryManager()
        mgr._strategies = []
        mgr.max_attempts = 1

        @mgr.register("explode", priority=1)
        def explode(driver):
            raise RuntimeError("boom")

        @mgr.register("succeed_after", priority=2)
        def succeed(driver):
            return True

        driver = MagicMock()
        result = mgr.try_recover(driver)
        assert result is True
        # 例外策略不會產生歷史記錄，成功的會
        assert len(mgr._history) == 1
        assert mgr._history[0].success is True


@pytest.mark.unit
class TestRecoveryManagerHistory:
    """RecoveryManager.get_history"""

    @pytest.mark.unit
    def test_empty_history(self):
        """空歷史"""
        mgr = RecoveryManager()
        assert mgr.get_history() == []

    @pytest.mark.unit
    def test_with_records(self):
        """有記錄時回傳"""
        mgr = RecoveryManager()
        mgr._history.append(RecoveryRecord("s1", True))
        mgr._history.append(RecoveryRecord("s2", False))
        history = mgr.get_history()
        assert len(history) == 2
        assert history[0].strategy_name == "s1"
        assert history[1].strategy_name == "s2"

    @pytest.mark.unit
    def test_limit(self):
        """限制回傳數量"""
        mgr = RecoveryManager()
        for i in range(10):
            mgr._history.append(RecoveryRecord(f"s{i}", True))
        history = mgr.get_history(limit=3)
        assert len(history) == 3
        # 回傳最後 3 筆
        assert history[0].strategy_name == "s7"
        assert history[2].strategy_name == "s9"


@pytest.mark.unit
class TestRecoveryManagerStats:
    """RecoveryManager.stats 屬性"""

    @pytest.mark.unit
    def test_stats_empty(self):
        """空歷史的統計"""
        mgr = RecoveryManager()
        stats = mgr.stats
        assert stats["total_attempts"] == 0
        assert stats["success"] == 0
        assert stats["fail"] == 0
        assert isinstance(stats["strategies"], list)
        assert len(stats["strategies"]) > 0  # 有內建策略

    @pytest.mark.unit
    def test_stats_with_records(self):
        """有記錄的統計"""
        mgr = RecoveryManager()
        mgr._history.append(RecoveryRecord("s1", True))
        mgr._history.append(RecoveryRecord("s2", False))
        mgr._history.append(RecoveryRecord("s3", True))
        stats = mgr.stats
        assert stats["total_attempts"] == 3
        assert stats["success"] == 2
        assert stats["fail"] == 1

    @pytest.mark.unit
    def test_stats_strategies_list(self):
        """strategies 列出所有已註冊策略名"""
        mgr = RecoveryManager()
        strategies = mgr.stats["strategies"]
        assert "permission_dialog" in strategies
        assert "back_button" in strategies


# ── 內建策略測試 ──

def _get_strategy(mgr, name):
    """從管理器取得指定名稱的策略函式"""
    for sname, _, fn in mgr._strategies:
        if sname == name:
            return fn
    raise ValueError(f"Strategy '{name}' not found")


@pytest.mark.unit
class TestHandlePermission:
    """_handle_permission 策略"""

    @pytest.mark.unit
    def test_android_button_found_and_clicked(self):
        """找到 Android 權限按鈕並點擊"""
        mgr = RecoveryManager()
        strategy = _get_strategy(mgr, "permission_dialog")

        mock_element = MagicMock()
        mock_element.is_displayed.return_value = True
        driver = MagicMock()
        driver.find_element.return_value = mock_element

        result = strategy(driver)
        assert result is True
        mock_element.click.assert_called_once()

    @pytest.mark.unit
    def test_ios_label_found(self):
        """Android 按鈕全部找不到，但 iOS 標籤找到"""
        mgr = RecoveryManager()
        strategy = _get_strategy(mgr, "permission_dialog")

        mock_ios_element = MagicMock()
        mock_ios_element.is_displayed.return_value = True

        call_count = 0
        android_button_ids = [
            "com.android.packageinstaller:id/permission_allow_button",
            "com.android.permissioncontroller:id/permission_allow_button",
            "com.android.permissioncontroller:id/permission_allow_foreground_only_button",
            "com.android.packageinstaller:id/permission_allow_always_button",
        ]

        def mock_find_element(by, value):
            if by == "id" and value in android_button_ids:
                raise Exception("not found")
            # iOS accessibility ID
            return mock_ios_element

        driver = MagicMock()
        driver.find_element.side_effect = mock_find_element

        result = strategy(driver)
        assert result is True
        mock_ios_element.click.assert_called_once()

    @pytest.mark.unit
    def test_nothing_found(self):
        """什麼都找不到"""
        mgr = RecoveryManager()
        strategy = _get_strategy(mgr, "permission_dialog")

        driver = MagicMock()
        driver.find_element.side_effect = Exception("not found")

        result = strategy(driver)
        assert result is False


@pytest.mark.unit
class TestHandleAnr:
    """_handle_anr 策略"""

    @pytest.mark.unit
    def test_anr_dialog_found(self):
        """ANR 對話框找到並點擊"""
        mgr = RecoveryManager()
        strategy = _get_strategy(mgr, "anr_dialog")

        mock_btn = MagicMock()
        mock_btn.is_displayed.return_value = True
        driver = MagicMock()
        driver.find_element.return_value = mock_btn

        result = strategy(driver)
        assert result is True
        mock_btn.click.assert_called_once()

    @pytest.mark.unit
    def test_anr_dialog_not_found(self):
        """ANR 對話框找不到"""
        mgr = RecoveryManager()
        strategy = _get_strategy(mgr, "anr_dialog")

        driver = MagicMock()
        driver.find_element.side_effect = Exception("not found")

        result = strategy(driver)
        assert result is False

    @pytest.mark.unit
    def test_anr_dialog_not_displayed(self):
        """ANR 元素存在但不可見"""
        mgr = RecoveryManager()
        strategy = _get_strategy(mgr, "anr_dialog")

        mock_btn = MagicMock()
        mock_btn.is_displayed.return_value = False
        driver = MagicMock()
        driver.find_element.return_value = mock_btn

        result = strategy(driver)
        assert result is False


@pytest.mark.unit
class TestHandleSystemDialog:
    """_handle_system_dialog 策略"""

    @pytest.mark.unit
    def test_dismiss_text_found(self):
        """找到取消文字並點擊"""
        mgr = RecoveryManager()
        strategy = _get_strategy(mgr, "system_dialog")

        mock_element = MagicMock()
        mock_element.is_displayed.return_value = True
        driver = MagicMock()
        driver.find_element.return_value = mock_element

        result = strategy(driver)
        assert result is True
        mock_element.click.assert_called_once()

    @pytest.mark.unit
    def test_android_button2_found(self):
        """文字都沒找到，但 android:id/button2 找到"""
        mgr = RecoveryManager()
        strategy = _get_strategy(mgr, "system_dialog")

        mock_btn2 = MagicMock()
        mock_btn2.is_displayed.return_value = True

        call_count = [0]

        def mock_find(by, value):
            if by == "xpath":
                raise Exception("not found")
            if by == "id" and value == "android:id/button2":
                return mock_btn2
            raise Exception("not found")

        driver = MagicMock()
        driver.find_element.side_effect = mock_find

        result = strategy(driver)
        assert result is True
        mock_btn2.click.assert_called_once()

    @pytest.mark.unit
    def test_nothing_found(self):
        """全部都找不到"""
        mgr = RecoveryManager()
        strategy = _get_strategy(mgr, "system_dialog")

        driver = MagicMock()
        driver.find_element.side_effect = Exception("not found")

        result = strategy(driver)
        assert result is False


@pytest.mark.unit
class TestHandleIosAlert:
    """_handle_ios_alert 策略"""

    @pytest.mark.unit
    def test_alert_accept(self):
        """iOS alert 存在 → accept"""
        mgr = RecoveryManager()
        strategy = _get_strategy(mgr, "ios_alert")

        driver = MagicMock()
        driver.switch_to.alert.text = "Allow access?"

        result = strategy(driver)
        assert result is True
        driver.switch_to.alert.accept.assert_called_once()

    @pytest.mark.unit
    def test_alert_dismiss(self):
        """alert.text 失敗但 dismiss 成功"""
        mgr = RecoveryManager()
        strategy = _get_strategy(mgr, "ios_alert")

        driver = MagicMock()
        # 第一次存取 alert.text 失敗
        type(driver.switch_to.alert).text = PropertyMock(
            side_effect=Exception("no alert text")
        )
        # dismiss 成功（不拋例外）
        driver.switch_to.alert.dismiss.return_value = None

        result = strategy(driver)
        assert result is True

    @pytest.mark.unit
    def test_no_alert(self):
        """完全沒有 alert"""
        mgr = RecoveryManager()
        strategy = _get_strategy(mgr, "ios_alert")

        driver = MagicMock()
        type(driver.switch_to.alert).text = PropertyMock(
            side_effect=Exception("no alert")
        )
        driver.switch_to.alert.dismiss.side_effect = Exception("no alert")

        result = strategy(driver)
        assert result is False


@pytest.mark.unit
class TestHandleWebview:
    """_handle_webview 策略"""

    @pytest.mark.unit
    def test_in_webview_switches(self):
        """在 WEBVIEW context → 切回 Native"""
        mgr = RecoveryManager()
        strategy = _get_strategy(mgr, "webview_escape")

        driver = MagicMock()
        driver.context = "WEBVIEW_com.app"

        result = strategy(driver)
        assert result is True
        driver.switch_to.context.assert_called_once_with("NATIVE_APP")

    @pytest.mark.unit
    def test_in_native_returns_false(self):
        """在 NATIVE context → 不做任何事"""
        mgr = RecoveryManager()
        strategy = _get_strategy(mgr, "webview_escape")

        driver = MagicMock()
        driver.context = "NATIVE_APP"

        result = strategy(driver)
        assert result is False

    @pytest.mark.unit
    def test_context_none(self):
        """context 為 None"""
        mgr = RecoveryManager()
        strategy = _get_strategy(mgr, "webview_escape")

        driver = MagicMock()
        driver.context = None

        result = strategy(driver)
        assert result is False

    @pytest.mark.unit
    def test_context_raises_exception(self):
        """取 context 失敗"""
        mgr = RecoveryManager()
        strategy = _get_strategy(mgr, "webview_escape")

        driver = MagicMock()
        type(driver).context = PropertyMock(side_effect=Exception("error"))

        result = strategy(driver)
        assert result is False


@pytest.mark.unit
class TestHandleCrash:
    """_handle_crash 策略"""

    @pytest.mark.unit
    @patch("core.recovery.time.sleep")
    def test_crash_indicator_found_restart(self, mock_sleep):
        """crash 指示器找到 → 關閉 + 重啟"""
        mgr = RecoveryManager()
        strategy = _get_strategy(mgr, "crash_restart")

        mock_crash_el = MagicMock()
        mock_crash_el.is_displayed.return_value = True
        mock_close_el = MagicMock()

        def mock_find(by, value):
            # crash indicator xpath
            if "has stopped" in value or "已停止" in value:
                return mock_crash_el
            # close button xpath
            if "Close" in value or "關閉" in value:
                return mock_close_el
            raise Exception("not found")

        driver = MagicMock()
        driver.find_element.side_effect = mock_find
        driver.capabilities = {"appPackage": "com.test.app"}

        result = strategy(driver)
        assert result is True
        mock_close_el.click.assert_called_once()
        driver.activate_app.assert_called_once_with("com.test.app")

    @pytest.mark.unit
    def test_crash_not_found(self):
        """沒有 crash 指示器"""
        mgr = RecoveryManager()
        strategy = _get_strategy(mgr, "crash_restart")

        driver = MagicMock()
        driver.find_element.side_effect = Exception("not found")

        result = strategy(driver)
        assert result is False

    @pytest.mark.unit
    @patch("core.recovery.time.sleep")
    def test_crash_with_bundle_id(self, mock_sleep):
        """iOS crash 用 bundleId 重啟"""
        mgr = RecoveryManager()
        strategy = _get_strategy(mgr, "crash_restart")

        mock_crash_el = MagicMock()
        mock_crash_el.is_displayed.return_value = True

        def mock_find(by, value):
            if "Problem Report" in value:
                return mock_crash_el
            if "Close" in value or "OK" in value:
                return MagicMock()
            raise Exception("not found")

        driver = MagicMock()
        driver.find_element.side_effect = mock_find
        driver.capabilities = {"bundleId": "com.test.iosapp"}

        result = strategy(driver)
        assert result is True
        driver.activate_app.assert_called_once_with("com.test.iosapp")


@pytest.mark.unit
class TestHandleBack:
    """_handle_back 策略"""

    @pytest.mark.unit
    @patch("core.recovery.time.sleep")
    def test_back_succeeds_with_valid_page_source(self, mock_sleep):
        """按返回鍵成功，page_source 有效"""
        mgr = RecoveryManager()
        strategy = _get_strategy(mgr, "back_button")

        driver = MagicMock()
        driver.page_source = "x" * 200  # > 100 characters

        result = strategy(driver)
        assert result is True
        driver.back.assert_called_once()

    @pytest.mark.unit
    @patch("core.recovery.time.sleep")
    def test_back_fails(self, mock_sleep):
        """按返回鍵失敗（back() 拋例外）"""
        mgr = RecoveryManager()
        strategy = _get_strategy(mgr, "back_button")

        driver = MagicMock()
        driver.back.side_effect = Exception("back failed")

        result = strategy(driver)
        assert result is False

    @pytest.mark.unit
    @patch("core.recovery.time.sleep")
    def test_back_page_source_too_short(self, mock_sleep):
        """按返回鍵後 page_source 太短"""
        mgr = RecoveryManager()
        strategy = _get_strategy(mgr, "back_button")

        driver = MagicMock()
        driver.page_source = "short"  # len < 100

        result = strategy(driver)
        assert result is False

    @pytest.mark.unit
    @patch("core.recovery.time.sleep")
    def test_back_page_source_none(self, mock_sleep):
        """按返回鍵後 page_source 為 None"""
        mgr = RecoveryManager()
        strategy = _get_strategy(mgr, "back_button")

        driver = MagicMock()
        driver.page_source = None

        result = strategy(driver)
        assert result is False
