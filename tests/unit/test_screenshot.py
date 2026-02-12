"""
utils.screenshot 單元測試
驗證 take_screenshot 的截圖目錄建立、檔名生成、driver 呼叫與回傳值。
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path


@pytest.mark.unit
class TestTakeScreenshot:
    """take_screenshot 函式"""

    @pytest.mark.unit
    def test_creates_screenshot_directory(self, tmp_path):
        """截圖目錄不存在時自動建立"""
        screenshot_dir = tmp_path / "screenshots"
        driver = MagicMock()

        with patch("utils.screenshot.Config") as mock_config:
            mock_config.SCREENSHOT_DIR = screenshot_dir
            from utils.screenshot import take_screenshot
            take_screenshot(driver, "test_create_dir")

        assert screenshot_dir.exists()

    @pytest.mark.unit
    def test_generates_correct_filename_with_timestamp(self, tmp_path):
        """產生的檔名包含名稱與時間戳記"""
        screenshot_dir = tmp_path / "screenshots"
        screenshot_dir.mkdir()
        driver = MagicMock()

        with patch("utils.screenshot.Config") as mock_config, \
             patch("utils.screenshot.datetime") as mock_datetime:
            mock_config.SCREENSHOT_DIR = screenshot_dir
            mock_datetime.now.return_value.strftime.return_value = "20250101_120000"

            from utils.screenshot import take_screenshot
            result = take_screenshot(driver, "login_fail")

        expected_filename = "login_fail_20250101_120000.png"
        assert expected_filename in result

    @pytest.mark.unit
    def test_calls_driver_save_screenshot(self, tmp_path):
        """呼叫 driver.save_screenshot 並傳入正確路徑"""
        screenshot_dir = tmp_path / "screenshots"
        screenshot_dir.mkdir()
        driver = MagicMock()

        with patch("utils.screenshot.Config") as mock_config, \
             patch("utils.screenshot.datetime") as mock_datetime:
            mock_config.SCREENSHOT_DIR = screenshot_dir
            mock_datetime.now.return_value.strftime.return_value = "20250101_120000"

            from utils.screenshot import take_screenshot
            take_screenshot(driver, "test_call")

        driver.save_screenshot.assert_called_once()
        call_arg = driver.save_screenshot.call_args[0][0]
        assert "test_call_20250101_120000.png" in call_arg

    @pytest.mark.unit
    def test_returns_filepath_string(self, tmp_path):
        """回傳截圖檔案的完整路徑字串"""
        screenshot_dir = tmp_path / "screenshots"
        screenshot_dir.mkdir()
        driver = MagicMock()

        with patch("utils.screenshot.Config") as mock_config, \
             patch("utils.screenshot.datetime") as mock_datetime:
            mock_config.SCREENSHOT_DIR = screenshot_dir
            mock_datetime.now.return_value.strftime.return_value = "20250101_120000"

            from utils.screenshot import take_screenshot
            result = take_screenshot(driver, "result_test")

        assert isinstance(result, str)
        assert result == str(screenshot_dir / "result_test_20250101_120000.png")

    @pytest.mark.unit
    def test_existing_directory_no_error(self, tmp_path):
        """截圖目錄已存在時不應報錯"""
        screenshot_dir = tmp_path / "screenshots"
        screenshot_dir.mkdir()
        driver = MagicMock()

        with patch("utils.screenshot.Config") as mock_config:
            mock_config.SCREENSHOT_DIR = screenshot_dir
            from utils.screenshot import take_screenshot
            # 不應拋出任何例外
            result = take_screenshot(driver, "existing_dir")

        assert isinstance(result, str)
