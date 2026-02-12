"""
utils.allure_helper 單元測試
驗證 Allure 報告整合輔助的 fallback 行為與正常功能。
當 allure 未安裝時，所有功能應 graceful fallback 不報錯。
"""

import pytest
from unittest.mock import MagicMock, patch, call
import functools


@pytest.mark.unit
class TestAllureStepNotAvailable:
    """allure_step 裝飾器 — allure 未安裝時"""

    @pytest.mark.unit
    def test_returns_original_function_when_allure_not_available(self):
        """ALLURE_AVAILABLE=False 時，裝飾器直接回傳原函式"""
        with patch("utils.allure_helper.ALLURE_AVAILABLE", False):
            from utils.allure_helper import allure_step

            @allure_step("測試步驟")
            def my_func(x, y):
                """原始 docstring"""
                return x + y

            # 應直接回傳原函式，不包裝
            assert my_func(1, 2) == 3

    @pytest.mark.unit
    def test_function_name_preserved_when_not_available(self):
        """ALLURE_AVAILABLE=False 時，函式名稱不被改變"""
        with patch("utils.allure_helper.ALLURE_AVAILABLE", False):
            from utils.allure_helper import allure_step

            @allure_step("some step")
            def original_func():
                pass

            assert original_func.__name__ == "original_func"

    @pytest.mark.unit
    def test_decorator_does_not_error_when_allure_missing(self):
        """ALLURE_AVAILABLE=False 時，裝飾器不拋出任何異常"""
        with patch("utils.allure_helper.ALLURE_AVAILABLE", False):
            from utils.allure_helper import allure_step

            # 不應拋出任何例外
            @allure_step("步驟名稱")
            def safe_func():
                return "ok"

            result = safe_func()
            assert result == "ok"

    @pytest.mark.unit
    def test_kwargs_passed_through_when_not_available(self):
        """ALLURE_AVAILABLE=False 時，關鍵字參數正確傳遞"""
        with patch("utils.allure_helper.ALLURE_AVAILABLE", False):
            from utils.allure_helper import allure_step

            @allure_step("帶參數步驟")
            def func_with_kwargs(a, b=10, c=20):
                return a + b + c

            assert func_with_kwargs(1, b=2, c=3) == 6


@pytest.mark.unit
class TestAllureStepAvailable:
    """allure_step 裝飾器 — allure 可用時"""

    @pytest.mark.unit
    def test_wraps_with_allure_step_when_available(self):
        """ALLURE_AVAILABLE=True 時，函式被 allure.step 包裝"""
        mock_allure = MagicMock()

        # 建立一個模擬的 allure.step 裝飾器
        def mock_step(title):
            def decorator(func):
                @functools.wraps(func)
                def wrapper(*args, **kwargs):
                    return func(*args, **kwargs)
                wrapper._allure_wrapped = True
                return wrapper
            return decorator

        mock_allure.step = mock_step

        with patch("utils.allure_helper.ALLURE_AVAILABLE", True), \
             patch("utils.allure_helper.allure", mock_allure, create=True):
            from utils.allure_helper import allure_step

            @allure_step("登入步驟")
            def login(user, pwd):
                return f"{user}:{pwd}"

            result = login("admin", "123")
            assert result == "admin:123"

    @pytest.mark.unit
    def test_function_is_callable_when_available(self):
        """ALLURE_AVAILABLE=True 時，包裝後的函式仍可正常呼叫"""
        mock_allure = MagicMock()

        def mock_step(title):
            def decorator(func):
                @functools.wraps(func)
                def wrapper(*args, **kwargs):
                    return func(*args, **kwargs)
                return wrapper
            return decorator

        mock_allure.step = mock_step

        with patch("utils.allure_helper.ALLURE_AVAILABLE", True), \
             patch("utils.allure_helper.allure", mock_allure, create=True):
            from utils.allure_helper import allure_step

            @allure_step("計算")
            def add(a, b):
                return a + b

            assert add(3, 4) == 7


@pytest.mark.unit
class TestAttachScreenshot:
    """attach_screenshot — 截圖附件功能"""

    @pytest.mark.unit
    def test_does_nothing_when_allure_not_available(self):
        """allure 未安裝時，不執行任何操作，也不報錯"""
        with patch("utils.allure_helper.ALLURE_AVAILABLE", False):
            from utils.allure_helper import attach_screenshot

            driver = MagicMock()
            # 不應拋出任何例外
            attach_screenshot(driver, "test_screenshot")
            # driver 的截圖方法不應被呼叫
            driver.get_screenshot_as_png.assert_not_called()

    @pytest.mark.unit
    def test_calls_driver_and_allure_when_available(self):
        """allure 可用時，呼叫 driver 截圖並附加到 allure"""
        mock_allure = MagicMock()
        mock_allure.attachment_type.PNG = "PNG_TYPE"

        with patch("utils.allure_helper.ALLURE_AVAILABLE", True), \
             patch("utils.allure_helper.allure", mock_allure, create=True):
            from utils.allure_helper import attach_screenshot

            driver = MagicMock()
            driver.get_screenshot_as_png.return_value = b"fake_png_data"

            attach_screenshot(driver, "截圖名稱")

            driver.get_screenshot_as_png.assert_called_once()
            mock_allure.attach.assert_called_once_with(
                b"fake_png_data",
                name="截圖名稱",
                attachment_type="PNG_TYPE",
            )

    @pytest.mark.unit
    def test_default_name_parameter(self):
        """attach_screenshot 預設名稱為 '截圖'"""
        mock_allure = MagicMock()
        mock_allure.attachment_type.PNG = "PNG_TYPE"

        with patch("utils.allure_helper.ALLURE_AVAILABLE", True), \
             patch("utils.allure_helper.allure", mock_allure, create=True):
            from utils.allure_helper import attach_screenshot

            driver = MagicMock()
            driver.get_screenshot_as_png.return_value = b"png"

            attach_screenshot(driver)

            mock_allure.attach.assert_called_once_with(
                b"png",
                name="截圖",
                attachment_type="PNG_TYPE",
            )


@pytest.mark.unit
class TestAttachText:
    """attach_text — 文字附件功能"""

    @pytest.mark.unit
    def test_does_nothing_when_allure_not_available(self):
        """allure 未安裝時，不執行任何操作"""
        with patch("utils.allure_helper.ALLURE_AVAILABLE", False):
            from utils.allure_helper import attach_text

            # 不應拋出任何例外
            attach_text("some text", "my log")

    @pytest.mark.unit
    def test_calls_allure_attach_when_available(self):
        """allure 可用時，呼叫 allure.attach 附加文字"""
        mock_allure = MagicMock()
        mock_allure.attachment_type.TEXT = "TEXT_TYPE"

        with patch("utils.allure_helper.ALLURE_AVAILABLE", True), \
             patch("utils.allure_helper.allure", mock_allure, create=True):
            from utils.allure_helper import attach_text

            attach_text("test log content", "test_log")

            mock_allure.attach.assert_called_once_with(
                "test log content",
                name="test_log",
                attachment_type="TEXT_TYPE",
            )

    @pytest.mark.unit
    def test_default_name_is_log(self):
        """attach_text 預設名稱為 'log'"""
        mock_allure = MagicMock()
        mock_allure.attachment_type.TEXT = "TEXT_TYPE"

        with patch("utils.allure_helper.ALLURE_AVAILABLE", True), \
             patch("utils.allure_helper.allure", mock_allure, create=True):
            from utils.allure_helper import attach_text

            attach_text("content")

            mock_allure.attach.assert_called_once_with(
                "content",
                name="log",
                attachment_type="TEXT_TYPE",
            )


@pytest.mark.unit
class TestAttachFile:
    """attach_file — 檔案附件功能"""

    @pytest.mark.unit
    def test_does_nothing_when_allure_not_available(self):
        """allure 未安裝時，不執行任何操作"""
        with patch("utils.allure_helper.ALLURE_AVAILABLE", False):
            from utils.allure_helper import attach_file

            # 不應拋出任何例外
            attach_file("/path/to/file.txt", "myfile")

    @pytest.mark.unit
    def test_calls_allure_attach_file_when_available(self):
        """allure 可用時，呼叫 allure.attach.file 附加檔案"""
        mock_allure = MagicMock()

        with patch("utils.allure_helper.ALLURE_AVAILABLE", True), \
             patch("utils.allure_helper.allure", mock_allure, create=True):
            from utils.allure_helper import attach_file

            attach_file("/tmp/report.html", "報告")

            mock_allure.attach.file.assert_called_once_with(
                "/tmp/report.html",
                name="報告",
            )

    @pytest.mark.unit
    def test_uses_filename_as_default_name(self):
        """attach_file 未指定 name 時使用檔案名稱"""
        mock_allure = MagicMock()

        with patch("utils.allure_helper.ALLURE_AVAILABLE", True), \
             patch("utils.allure_helper.allure", mock_allure, create=True):
            from utils.allure_helper import attach_file

            attach_file("/tmp/data/results.json")

            mock_allure.attach.file.assert_called_once_with(
                "/tmp/data/results.json",
                name="results.json",
            )


@pytest.mark.unit
class TestFallbackBehavior:
    """整體 fallback 行為 — 所有函式在 allure 缺失時不報錯"""

    @pytest.mark.unit
    def test_all_functions_safe_when_allure_missing(self):
        """所有公開函式在 ALLURE_AVAILABLE=False 時都不報錯"""
        with patch("utils.allure_helper.ALLURE_AVAILABLE", False):
            from utils.allure_helper import (
                allure_step,
                attach_screenshot,
                attach_text,
                attach_file,
            )

            driver = MagicMock()

            # 全部不應拋出任何例外
            @allure_step("步驟")
            def dummy():
                return 42

            assert dummy() == 42
            attach_screenshot(driver, "name")
            attach_text("text", "name")
            attach_file("/path/to/file")

    @pytest.mark.unit
    def test_allure_step_with_no_args_function(self):
        """allure_step 裝飾無參數函式時正常運作"""
        with patch("utils.allure_helper.ALLURE_AVAILABLE", False):
            from utils.allure_helper import allure_step

            @allure_step("無參數")
            def no_args():
                return "hello"

            assert no_args() == "hello"

    @pytest.mark.unit
    def test_allure_step_with_method(self):
        """allure_step 裝飾類別方法時正常運作"""
        with patch("utils.allure_helper.ALLURE_AVAILABLE", False):
            from utils.allure_helper import allure_step

            class MyPage:
                @allure_step("點擊按鈕")
                def click_button(self):
                    return "clicked"

            page = MyPage()
            assert page.click_button() == "clicked"
