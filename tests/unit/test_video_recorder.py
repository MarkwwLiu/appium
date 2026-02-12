"""
utils.video_recorder 單元測試
驗證 VideoRecorder 的錄影功能：啟動、停止儲存、丟棄、context manager。
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path


@pytest.mark.unit
class TestVideoRecorderInit:
    """VideoRecorder.__init__ — 初始化"""

    @pytest.mark.unit
    def test_default_values(self, tmp_path):
        """預設值正確"""
        with patch("utils.video_recorder.Path.mkdir"):
            from utils.video_recorder import VideoRecorder

            driver = MagicMock()
            recorder = VideoRecorder(driver)

            assert recorder._driver is driver
            assert recorder._platform == "android"
            assert recorder._time_limit == 180
            assert recorder._recording is False
            assert recorder._mode == "appium"

    @pytest.mark.unit
    def test_custom_values(self, tmp_path):
        """自訂值正確"""
        with patch("utils.video_recorder.Path.mkdir"):
            from utils.video_recorder import VideoRecorder

            driver = MagicMock()
            recorder = VideoRecorder(
                driver,
                platform="ios",
                output_dir=str(tmp_path / "my_videos"),
                time_limit=300,
            )

            assert recorder._platform == "ios"
            assert recorder._time_limit == 300

    @pytest.mark.unit
    def test_output_dir_created(self, tmp_path):
        """輸出目錄自動建立"""
        from utils.video_recorder import VideoRecorder

        driver = MagicMock()
        output = tmp_path / "test_videos"
        recorder = VideoRecorder(driver, output_dir=str(output))

        assert output.exists()

    @pytest.mark.unit
    def test_platform_case_insensitive(self, tmp_path):
        """platform 不區分大小寫"""
        with patch("utils.video_recorder.Path.mkdir"):
            from utils.video_recorder import VideoRecorder

            driver = MagicMock()
            recorder = VideoRecorder(driver, platform="Android")

            assert recorder._platform == "android"

    @pytest.mark.unit
    def test_recording_starts_false(self, tmp_path):
        """初始 _recording 為 False"""
        with patch("utils.video_recorder.Path.mkdir"):
            from utils.video_recorder import VideoRecorder

            driver = MagicMock()
            recorder = VideoRecorder(driver)

            assert recorder._recording is False
            assert recorder.is_recording is False


@pytest.mark.unit
class TestVideoRecorderStart:
    """VideoRecorder.start — 開始錄影"""

    @pytest.mark.unit
    def test_sets_recording_true_appium_mode(self, tmp_path):
        """Appium API 模式成功時設定 _recording=True"""
        with patch("utils.video_recorder.Path.mkdir"):
            from utils.video_recorder import VideoRecorder

            driver = MagicMock()
            recorder = VideoRecorder(driver, output_dir=str(tmp_path))

            recorder.start()

            assert recorder._recording is True
            assert recorder._mode == "appium"

    @pytest.mark.unit
    def test_calls_start_recording_screen(self, tmp_path):
        """呼叫 driver.start_recording_screen"""
        with patch("utils.video_recorder.Path.mkdir"):
            from utils.video_recorder import VideoRecorder

            driver = MagicMock()
            recorder = VideoRecorder(driver, output_dir=str(tmp_path))

            recorder.start()

            driver.start_recording_screen.assert_called_once()

    @pytest.mark.unit
    def test_ignores_duplicate_start(self, tmp_path):
        """已在錄影時忽略重複呼叫"""
        with patch("utils.video_recorder.Path.mkdir"):
            from utils.video_recorder import VideoRecorder

            driver = MagicMock()
            recorder = VideoRecorder(driver, output_dir=str(tmp_path))

            recorder.start()
            recorder.start()  # 重複呼叫

            # start_recording_screen 只被呼叫一次
            driver.start_recording_screen.assert_called_once()

    @pytest.mark.unit
    def test_falls_back_to_adb_on_appium_failure(self, tmp_path):
        """Appium API 失敗時 fallback 到 ADB"""
        with patch("utils.video_recorder.Path.mkdir"):
            from utils.video_recorder import VideoRecorder

            driver = MagicMock()
            driver.start_recording_screen.side_effect = Exception("Not supported")

            recorder = VideoRecorder(driver, output_dir=str(tmp_path))

            with patch("utils.video_recorder.subprocess") as mock_subprocess:
                mock_subprocess.Popen.return_value = MagicMock()
                recorder.start()

                assert recorder._recording is True
                assert recorder._mode == "adb"

    @pytest.mark.unit
    def test_both_modes_fail(self, tmp_path):
        """兩種模式都失敗時 _recording 仍為 False"""
        with patch("utils.video_recorder.Path.mkdir"):
            from utils.video_recorder import VideoRecorder

            driver = MagicMock()
            driver.start_recording_screen.side_effect = Exception("Not supported")

            recorder = VideoRecorder(driver, output_dir=str(tmp_path))

            with patch("utils.video_recorder.subprocess") as mock_subprocess:
                mock_subprocess.Popen.side_effect = Exception("ADB not found")
                recorder.start()

                assert recorder._recording is False


@pytest.mark.unit
class TestVideoRecorderStopAndSave:
    """VideoRecorder.stop_and_save — 停止錄影並儲存"""

    @pytest.mark.unit
    def test_saves_video_appium_mode(self, tmp_path):
        """Appium 模式成功儲存影片"""
        import base64
        from utils.video_recorder import VideoRecorder

        driver = MagicMock()
        fake_video = b"fake_video_data"
        driver.stop_recording_screen.return_value = base64.b64encode(fake_video).decode()

        recorder = VideoRecorder(driver, output_dir=str(tmp_path))
        recorder._recording = True
        recorder._mode = "appium"

        result = recorder.stop_and_save("test_login")

        assert result is not None
        assert result.exists()
        assert result.read_bytes() == fake_video

    @pytest.mark.unit
    def test_returns_path(self, tmp_path):
        """回傳儲存路徑"""
        import base64
        from utils.video_recorder import VideoRecorder

        driver = MagicMock()
        driver.stop_recording_screen.return_value = base64.b64encode(b"data").decode()

        recorder = VideoRecorder(driver, output_dir=str(tmp_path))
        recorder._recording = True
        recorder._mode = "appium"

        result = recorder.stop_and_save("my_test")

        assert isinstance(result, Path)
        assert "my_test" in result.name

    @pytest.mark.unit
    def test_returns_none_when_not_recording(self, tmp_path):
        """未在錄影時回傳 None"""
        with patch("utils.video_recorder.Path.mkdir"):
            from utils.video_recorder import VideoRecorder

            driver = MagicMock()
            recorder = VideoRecorder(driver, output_dir=str(tmp_path))

            result = recorder.stop_and_save("test")

            assert result is None

    @pytest.mark.unit
    def test_sets_recording_false(self, tmp_path):
        """停止後 _recording 設為 False"""
        import base64
        from utils.video_recorder import VideoRecorder

        driver = MagicMock()
        driver.stop_recording_screen.return_value = base64.b64encode(b"data").decode()

        recorder = VideoRecorder(driver, output_dir=str(tmp_path))
        recorder._recording = True
        recorder._mode = "appium"

        recorder.stop_and_save("test")

        assert recorder._recording is False

    @pytest.mark.unit
    def test_returns_none_on_exception(self, tmp_path):
        """儲存失敗時回傳 None"""
        with patch("utils.video_recorder.Path.mkdir"):
            from utils.video_recorder import VideoRecorder

            driver = MagicMock()
            driver.stop_recording_screen.side_effect = Exception("Save failed")

            recorder = VideoRecorder(driver, output_dir=str(tmp_path))
            recorder._recording = True
            recorder._mode = "appium"

            result = recorder.stop_and_save("fail_test")

            assert result is None


@pytest.mark.unit
class TestVideoRecorderStopAndDiscard:
    """VideoRecorder.stop_and_discard — 停止錄影不儲存"""

    @pytest.mark.unit
    def test_discards_appium_recording(self, tmp_path):
        """Appium 模式丟棄錄影"""
        with patch("utils.video_recorder.Path.mkdir"):
            from utils.video_recorder import VideoRecorder

            driver = MagicMock()
            recorder = VideoRecorder(driver, output_dir=str(tmp_path))
            recorder._recording = True
            recorder._mode = "appium"

            recorder.stop_and_discard()

            assert recorder._recording is False
            driver.stop_recording_screen.assert_called_once()

    @pytest.mark.unit
    def test_does_nothing_when_not_recording(self, tmp_path):
        """未在錄影時不執行任何操作"""
        with patch("utils.video_recorder.Path.mkdir"):
            from utils.video_recorder import VideoRecorder

            driver = MagicMock()
            recorder = VideoRecorder(driver, output_dir=str(tmp_path))

            recorder.stop_and_discard()

            driver.stop_recording_screen.assert_not_called()

    @pytest.mark.unit
    def test_handles_exception_gracefully(self, tmp_path):
        """停止失敗時不報錯"""
        with patch("utils.video_recorder.Path.mkdir"):
            from utils.video_recorder import VideoRecorder

            driver = MagicMock()
            driver.stop_recording_screen.side_effect = Exception("Failed")
            recorder = VideoRecorder(driver, output_dir=str(tmp_path))
            recorder._recording = True
            recorder._mode = "appium"

            # 不應拋出例外
            recorder.stop_and_discard()
            assert recorder._recording is False


@pytest.mark.unit
class TestVideoRecorderIsRecording:
    """VideoRecorder.is_recording property"""

    @pytest.mark.unit
    def test_returns_false_initially(self, tmp_path):
        """初始為 False"""
        with patch("utils.video_recorder.Path.mkdir"):
            from utils.video_recorder import VideoRecorder

            driver = MagicMock()
            recorder = VideoRecorder(driver, output_dir=str(tmp_path))

            assert recorder.is_recording is False

    @pytest.mark.unit
    def test_returns_true_after_start(self, tmp_path):
        """start 後為 True"""
        with patch("utils.video_recorder.Path.mkdir"):
            from utils.video_recorder import VideoRecorder

            driver = MagicMock()
            recorder = VideoRecorder(driver, output_dir=str(tmp_path))
            recorder.start()

            assert recorder.is_recording is True

    @pytest.mark.unit
    def test_returns_false_after_stop(self, tmp_path):
        """stop 後為 False"""
        with patch("utils.video_recorder.Path.mkdir"):
            from utils.video_recorder import VideoRecorder

            driver = MagicMock()
            recorder = VideoRecorder(driver, output_dir=str(tmp_path))
            recorder._recording = True
            recorder._mode = "appium"

            recorder.stop_and_discard()

            assert recorder.is_recording is False


@pytest.mark.unit
class TestVideoRecorderContextManager:
    """VideoRecorder context manager"""

    @pytest.mark.unit
    def test_enter_calls_start(self, tmp_path):
        """__enter__ 呼叫 start()"""
        with patch("utils.video_recorder.Path.mkdir"):
            from utils.video_recorder import VideoRecorder

            driver = MagicMock()
            recorder = VideoRecorder(driver, output_dir=str(tmp_path))

            with patch.object(recorder, "start") as mock_start, \
                 patch.object(recorder, "stop_and_discard"):
                recorder.__enter__()
                mock_start.assert_called_once()

    @pytest.mark.unit
    def test_exit_calls_stop_and_discard_when_recording(self, tmp_path):
        """__exit__ 在錄影中時呼叫 stop_and_discard()"""
        with patch("utils.video_recorder.Path.mkdir"):
            from utils.video_recorder import VideoRecorder

            driver = MagicMock()
            recorder = VideoRecorder(driver, output_dir=str(tmp_path))
            recorder._recording = True

            with patch.object(recorder, "stop_and_discard") as mock_stop:
                recorder.__exit__(None, None, None)
                mock_stop.assert_called_once()

    @pytest.mark.unit
    def test_exit_does_not_call_stop_when_not_recording(self, tmp_path):
        """__exit__ 未錄影時不呼叫 stop_and_discard()"""
        with patch("utils.video_recorder.Path.mkdir"):
            from utils.video_recorder import VideoRecorder

            driver = MagicMock()
            recorder = VideoRecorder(driver, output_dir=str(tmp_path))
            recorder._recording = False

            with patch.object(recorder, "stop_and_discard") as mock_stop:
                recorder.__exit__(None, None, None)
                mock_stop.assert_not_called()

    @pytest.mark.unit
    def test_context_manager_returns_self(self, tmp_path):
        """context manager 回傳自身"""
        with patch("utils.video_recorder.Path.mkdir"):
            from utils.video_recorder import VideoRecorder

            driver = MagicMock()
            recorder = VideoRecorder(driver, output_dir=str(tmp_path))

            result = recorder.__enter__()
            assert result is recorder

            # 清理
            recorder._recording = False
            recorder.__exit__(None, None, None)


@pytest.mark.unit
class TestVideoRecorderOutputDir:
    """VideoRecorder.output_dir property"""

    @pytest.mark.unit
    def test_returns_output_dir_path(self, tmp_path):
        """回傳輸出目錄 Path"""
        from utils.video_recorder import VideoRecorder

        driver = MagicMock()
        output = tmp_path / "videos"
        recorder = VideoRecorder(driver, output_dir=str(output))

        assert recorder.output_dir == output
