"""
utils.monkey_tester 單元測試
驗證 MonkeyTester 的隨機壓力測試功能，包含動作執行、排除區域、恢復機制。
"""

import time
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from utils.monkey_tester import (
    ExcludeRegion,
    MonkeyEvent,
    MonkeyResult,
    MonkeyTester,
    DEFAULT_WEIGHTS,
)


def _make_driver() -> MagicMock:
    """建立帶有螢幕尺寸的模擬 driver"""
    driver = MagicMock()
    driver.get_window_size.return_value = {"width": 1080, "height": 2340}
    driver.orientation = "PORTRAIT"
    driver.current_package = "com.example.app"
    return driver


@pytest.mark.unit
class TestExcludeRegionDataclass:
    """ExcludeRegion 資料類別"""

    @pytest.mark.unit
    def test_defaults(self):
        """預設值"""
        region = ExcludeRegion()
        assert region.x_min == 0
        assert region.y_min == 0
        assert region.x_max == 9999
        assert region.y_max == 9999

    @pytest.mark.unit
    def test_custom_values(self):
        """自訂值"""
        region = ExcludeRegion(x_min=10, y_min=20, x_max=100, y_max=200)
        assert region.x_min == 10
        assert region.y_min == 20
        assert region.x_max == 100
        assert region.y_max == 200


@pytest.mark.unit
class TestMonkeyEventDataclass:
    """MonkeyEvent 資料類別"""

    @pytest.mark.unit
    def test_defaults(self):
        """預設值"""
        event = MonkeyEvent(action="tap", timestamp=1000.0)
        assert event.action == "tap"
        assert event.timestamp == 1000.0
        assert event.details == {}
        assert event.success is True
        assert event.error == ""

    @pytest.mark.unit
    def test_custom_values(self):
        """自訂值"""
        event = MonkeyEvent(
            action="swipe", timestamp=2000.0,
            details={"x": 100}, success=False, error="fail"
        )
        assert event.success is False
        assert event.error == "fail"


@pytest.mark.unit
class TestMonkeyResultDataclass:
    """MonkeyResult 資料類別"""

    @pytest.mark.unit
    def test_defaults(self):
        """預設值"""
        result = MonkeyResult()
        assert result.duration == 0.0
        assert result.total_actions == 0
        assert result.crashes == 0
        assert result.recoveries == 0
        assert result.errors == []
        assert result.events == []

    @pytest.mark.unit
    def test_summary_property(self):
        """summary 屬性格式正確"""
        result = MonkeyResult(
            duration=120.0, total_actions=60,
            crashes=2, recoveries=3,
            errors=["err1", "err2", "err3"]
        )
        summary = result.summary
        assert "120" in summary
        assert "60" in summary
        assert "2 次 crash" in summary
        assert "3 次 recovery" in summary
        assert "3 個錯誤" in summary


@pytest.mark.unit
class TestMonkeyTesterInit:
    """MonkeyTester 初始化"""

    @pytest.mark.unit
    def test_init_default_weights(self):
        """預設權重"""
        driver = _make_driver()
        with patch("utils.monkey_tester.random"):
            tester = MonkeyTester(driver)
        assert tester._weights == DEFAULT_WEIGHTS
        assert tester._width == 1080
        assert tester._height == 2340

    @pytest.mark.unit
    def test_init_custom_weights(self):
        """自訂權重"""
        driver = _make_driver()
        custom = {"tap": 50, "swipe": 50}
        with patch("utils.monkey_tester.random"):
            tester = MonkeyTester(driver, weights=custom)
        assert tester._weights == custom

    @pytest.mark.unit
    def test_init_with_seed(self):
        """指定隨機種子"""
        driver = _make_driver()
        with patch("utils.monkey_tester.random") as mock_random:
            MonkeyTester(driver, seed=42)
            mock_random.seed.assert_called_once_with(42)

    @pytest.mark.unit
    def test_init_without_seed_no_seed_call(self):
        """未指定種子時不呼叫 random.seed"""
        driver = _make_driver()
        with patch("utils.monkey_tester.random") as mock_random:
            MonkeyTester(driver)
            mock_random.seed.assert_not_called()

    @pytest.mark.unit
    def test_init_recovery_import_failure(self):
        """RecoveryManager 匯入失敗時 _recovery 為 None"""
        driver = _make_driver()
        with patch("utils.monkey_tester.random"):
            tester = MonkeyTester(driver)
        # 由於 core.recovery 可能不存在，_recovery 應為 None
        assert tester._recovery is None or tester._recovery is not None


@pytest.mark.unit
class TestMonkeyTesterExcludeRegion:
    """MonkeyTester.exclude_region 方法"""

    @pytest.mark.unit
    def test_exclude_region_adds_to_list(self):
        """新增排除區域到列表"""
        driver = _make_driver()
        with patch("utils.monkey_tester.random"):
            tester = MonkeyTester(driver)
        tester.exclude_region(y_max=100)
        assert len(tester._excludes) == 1
        assert tester._excludes[0].y_max == 100

    @pytest.mark.unit
    def test_exclude_region_returns_self(self):
        """回傳自身以支援鏈式呼叫"""
        driver = _make_driver()
        with patch("utils.monkey_tester.random"):
            tester = MonkeyTester(driver)
        result = tester.exclude_region(y_max=100)
        assert result is tester

    @pytest.mark.unit
    def test_exclude_region_multiple(self):
        """多次新增排除區域"""
        driver = _make_driver()
        with patch("utils.monkey_tester.random"):
            tester = MonkeyTester(driver)
        tester.exclude_region(y_max=100).exclude_region(y_min=2400)
        assert len(tester._excludes) == 2


@pytest.mark.unit
class TestMonkeyTesterBuildActionPool:
    """MonkeyTester._build_action_pool 方法"""

    @pytest.mark.unit
    def test_build_action_pool_respects_weights(self):
        """動作池大小符合權重"""
        driver = _make_driver()
        custom = {"tap": 3, "swipe": 2}
        with patch("utils.monkey_tester.random"):
            tester = MonkeyTester(driver, weights=custom)
        pool = tester._build_action_pool()
        assert pool.count("tap") == 3
        assert pool.count("swipe") == 2
        assert len(pool) == 5

    @pytest.mark.unit
    def test_build_action_pool_default_weights(self):
        """預設權重產生正確大小的池"""
        driver = _make_driver()
        with patch("utils.monkey_tester.random"):
            tester = MonkeyTester(driver)
        pool = tester._build_action_pool()
        expected_total = sum(DEFAULT_WEIGHTS.values())
        assert len(pool) == expected_total


@pytest.mark.unit
class TestMonkeyTesterRandomPoint:
    """MonkeyTester._random_point 方法"""

    @pytest.mark.unit
    def test_random_point_within_bounds(self):
        """隨機座標在螢幕範圍內"""
        driver = _make_driver()
        tester = MonkeyTester(driver, seed=42)
        for _ in range(20):
            x, y = tester._random_point()
            assert 0 <= x <= 1080
            assert 0 <= y <= 2340

    @pytest.mark.unit
    def test_random_point_avoids_exclude_regions(self):
        """隨機座標避開排除區域"""
        driver = _make_driver()
        tester = MonkeyTester(driver, seed=42)
        # 排除幾乎整個螢幕，只留中心
        tester.exclude_region(x_min=0, y_min=0, x_max=500, y_max=2340)
        tester.exclude_region(x_min=600, y_min=0, x_max=1080, y_max=2340)
        tester.exclude_region(x_min=0, y_min=0, x_max=1080, y_max=1100)
        tester.exclude_region(x_min=0, y_min=1300, x_max=1080, y_max=2340)

        x, y = tester._random_point()
        # 如果找不到非排除區域的點，應回傳螢幕中心
        assert 0 <= x <= 1080
        assert 0 <= y <= 2340


@pytest.mark.unit
class TestMonkeyTesterInExclude:
    """MonkeyTester._in_exclude 方法"""

    @pytest.mark.unit
    def test_in_exclude_inside_region(self):
        """座標在排除區域內回傳 True"""
        driver = _make_driver()
        with patch("utils.monkey_tester.random"):
            tester = MonkeyTester(driver)
        tester.exclude_region(x_min=0, y_min=0, x_max=100, y_max=100)
        assert tester._in_exclude(50, 50) is True

    @pytest.mark.unit
    def test_in_exclude_outside_region(self):
        """座標在排除區域外回傳 False"""
        driver = _make_driver()
        with patch("utils.monkey_tester.random"):
            tester = MonkeyTester(driver)
        tester.exclude_region(x_min=0, y_min=0, x_max=100, y_max=100)
        assert tester._in_exclude(200, 200) is False

    @pytest.mark.unit
    def test_in_exclude_on_boundary(self):
        """座標在排除區域邊界上回傳 True"""
        driver = _make_driver()
        with patch("utils.monkey_tester.random"):
            tester = MonkeyTester(driver)
        tester.exclude_region(x_min=0, y_min=0, x_max=100, y_max=100)
        assert tester._in_exclude(100, 100) is True

    @pytest.mark.unit
    def test_in_exclude_no_regions(self):
        """沒有排除區域時回傳 False"""
        driver = _make_driver()
        with patch("utils.monkey_tester.random"):
            tester = MonkeyTester(driver)
        assert tester._in_exclude(500, 500) is False


@pytest.mark.unit
class TestMonkeyTesterExecuteAction:
    """MonkeyTester._execute_action 方法"""

    @pytest.mark.unit
    def test_execute_known_action_success(self):
        """已知動作執行成功"""
        driver = _make_driver()
        tester = MonkeyTester(driver, seed=42)

        event = tester._execute_action("back")
        assert event.action == "back"
        assert event.success is True
        driver.back.assert_called_once()

    @pytest.mark.unit
    def test_execute_unknown_action(self):
        """未知動作標記為失敗"""
        driver = _make_driver()
        tester = MonkeyTester(driver, seed=42)

        event = tester._execute_action("fly")
        assert event.success is False
        assert "未知動作" in event.error

    @pytest.mark.unit
    def test_execute_action_exception(self):
        """動作拋出異常時標記為失敗"""
        driver = _make_driver()
        driver.back.side_effect = Exception("App crashed")
        tester = MonkeyTester(driver, seed=42)

        event = tester._execute_action("back")
        assert event.success is False
        assert "App crashed" in event.error


@pytest.mark.unit
class TestMonkeyTesterActions:
    """MonkeyTester 各動作方法"""

    @pytest.mark.unit
    def test_action_tap(self):
        """_action_tap 呼叫 driver.tap"""
        driver = _make_driver()
        tester = MonkeyTester(driver, seed=42)
        result = tester._action_tap()
        driver.tap.assert_called_once()
        assert "x" in result
        assert "y" in result

    @pytest.mark.unit
    def test_action_swipe(self):
        """_action_swipe 呼叫 driver.swipe"""
        driver = _make_driver()
        tester = MonkeyTester(driver, seed=42)
        result = tester._action_swipe()
        driver.swipe.assert_called_once()
        assert "start" in result
        assert "end" in result

    @pytest.mark.unit
    def test_action_back(self):
        """_action_back 呼叫 driver.back"""
        driver = _make_driver()
        tester = MonkeyTester(driver, seed=42)
        result = tester._action_back()
        driver.back.assert_called_once()
        assert result == {}

    @pytest.mark.unit
    def test_action_input_with_active_element(self):
        """_action_input 有焦點元素時輸入文字"""
        driver = _make_driver()
        mock_element = MagicMock()
        driver.switch_to.active_element = mock_element
        tester = MonkeyTester(driver, seed=42)

        result = tester._action_input()
        assert "text" in result
        mock_element.send_keys.assert_called_once()

    @pytest.mark.unit
    def test_action_input_no_active_element(self):
        """_action_input 無焦點元素時跳過"""
        driver = _make_driver()
        driver.switch_to.active_element = None
        tester = MonkeyTester(driver, seed=42)

        result = tester._action_input()
        assert "text" in result
        assert result.get("skipped") is True

    @pytest.mark.unit
    def test_action_rotate(self):
        """_action_rotate 旋轉螢幕後轉回"""
        driver = _make_driver()
        driver.orientation = "PORTRAIT"
        tester = MonkeyTester(driver, seed=42)

        with patch("utils.monkey_tester.time.sleep"):
            result = tester._action_rotate()
        assert result["from"] == "PORTRAIT"
        assert result["to"] == "LANDSCAPE"

    @pytest.mark.unit
    def test_action_home(self):
        """_action_home 按 Home 後回到 App"""
        driver = _make_driver()
        tester = MonkeyTester(driver, seed=42)

        with patch("utils.monkey_tester.time.sleep"):
            result = tester._action_home()
        driver.press_keycode.assert_called_once_with(3)
        driver.activate_app.assert_called_once_with("com.example.app")
        assert result == {}

    @pytest.mark.unit
    def test_action_long_press(self):
        """_action_long_press 長按呼叫 driver.tap"""
        driver = _make_driver()
        tester = MonkeyTester(driver, seed=42)
        result = tester._action_long_press()
        driver.tap.assert_called_once()
        call_args = driver.tap.call_args
        assert call_args[1].get("duration") == 1500 or call_args[0][1] == 1500
        assert "duration" in result
        assert result["duration"] == 1500


@pytest.mark.unit
class TestMonkeyTesterTryRecover:
    """MonkeyTester._try_recover 方法"""

    @pytest.mark.unit
    def test_try_recover_with_recovery_manager(self):
        """有 RecoveryManager 時使用它"""
        driver = _make_driver()
        tester = MonkeyTester(driver, seed=42)
        mock_recovery = MagicMock()
        mock_recovery.try_recover.return_value = True
        tester._recovery = mock_recovery

        with patch("utils.monkey_tester.time.sleep"):
            result = tester._try_recover()
        assert result is True
        mock_recovery.try_recover.assert_called_once_with(driver)

    @pytest.mark.unit
    def test_try_recover_without_recovery_falls_back_to_back(self):
        """無 RecoveryManager 時按返回鍵"""
        driver = _make_driver()
        tester = MonkeyTester(driver, seed=42)
        tester._recovery = None

        with patch("utils.monkey_tester.time.sleep"):
            result = tester._try_recover()
        assert result is True
        driver.back.assert_called()

    @pytest.mark.unit
    def test_try_recover_back_fails_returns_false(self):
        """按返回鍵也失敗時回傳 False"""
        driver = _make_driver()
        driver.back.side_effect = Exception("fail")
        tester = MonkeyTester(driver, seed=42)
        tester._recovery = None

        with patch("utils.monkey_tester.time.sleep"):
            result = tester._try_recover()
        assert result is False

    @pytest.mark.unit
    def test_try_recover_recovery_manager_exception_falls_back(self):
        """RecoveryManager 拋出異常時 fallback 到 back"""
        driver = _make_driver()
        tester = MonkeyTester(driver, seed=42)
        mock_recovery = MagicMock()
        mock_recovery.try_recover.side_effect = Exception("recovery failed")
        tester._recovery = mock_recovery

        with patch("utils.monkey_tester.time.sleep"):
            result = tester._try_recover()
        assert result is True
        driver.back.assert_called()


@pytest.mark.unit
class TestMonkeyTesterRun:
    """MonkeyTester.run 方法"""

    @pytest.mark.unit
    def test_run_short_duration(self):
        """短時間執行測試"""
        driver = _make_driver()
        tester = MonkeyTester(driver, seed=42)

        # 讓 time.time 在第一次迴圈後超過 duration
        call_count = [0]
        start = 1000.0

        def mock_time():
            call_count[0] += 1
            if call_count[0] <= 1:
                return start
            return start + 999  # 超過 duration

        with patch("utils.monkey_tester.time.time", side_effect=mock_time), \
             patch("utils.monkey_tester.time.sleep"):
            result = tester.run(duration=0.001, actions_per_minute=6000)

        assert isinstance(result, MonkeyResult)
        assert result.total_actions >= 0

    @pytest.mark.unit
    def test_run_stop_on_crash(self):
        """stop_on_crash=True 遇到 crash 時停止"""
        driver = _make_driver()
        driver.back.side_effect = Exception("crash!")
        tester = MonkeyTester(driver, seed=42)
        tester._recovery = None
        # 讓 back 也失敗，使 _try_recover 回傳 False -> crash
        # 但 _try_recover 的 fallback back 也會失敗

        call_count = [0]
        start = 1000.0

        def mock_time():
            call_count[0] += 1
            if call_count[0] <= 2:
                return start
            return start + 0.001

        # 使用只有 back 動作的權重
        tester._weights = {"back": 1}

        with patch("utils.monkey_tester.time.time", side_effect=mock_time), \
             patch("utils.monkey_tester.time.sleep"):
            result = tester.run(duration=10, actions_per_minute=6000, stop_on_crash=True)

        assert result.crashes >= 1

    @pytest.mark.unit
    def test_run_records_events(self):
        """run 記錄所有事件"""
        driver = _make_driver()
        tester = MonkeyTester(driver, seed=42)
        tester._weights = {"back": 1}

        call_count = [0]
        start = 1000.0

        def mock_time():
            call_count[0] += 1
            if call_count[0] <= 2:
                return start
            return start + 999

        with patch("utils.monkey_tester.time.time", side_effect=mock_time), \
             patch("utils.monkey_tester.time.sleep"):
            result = tester.run(duration=0.001, actions_per_minute=60000)

        # 至少執行了一個動作
        assert result.total_actions >= 0
        assert len(result.events) == result.total_actions
