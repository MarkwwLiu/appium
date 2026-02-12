"""
utils.image_compare 單元測試
驗證 ImageCompare 的截圖比對、baseline 管理與差異計算功能。
"""

import io
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path


@pytest.mark.unit
class TestImageCompareWhenPilNotAvailable:
    """PIL 不可用時的行為"""

    @pytest.mark.unit
    def test_capture_raises_runtime_error(self, tmp_path):
        """PIL 不可用時 capture 拋出 RuntimeError"""
        with patch("utils.image_compare.PIL_AVAILABLE", False), \
             patch("utils.image_compare.BASELINE_DIR", tmp_path / "baseline"), \
             patch("utils.image_compare.DIFF_DIR", tmp_path / "diff"):
            from utils.image_compare import ImageCompare
            driver = MagicMock()
            ic = ImageCompare(driver)
            with pytest.raises(RuntimeError, match="Pillow"):
                ic.capture()

    @pytest.mark.unit
    def test_compare_raises_runtime_error(self, tmp_path):
        """PIL 不可用時 compare 拋出 RuntimeError"""
        with patch("utils.image_compare.PIL_AVAILABLE", False), \
             patch("utils.image_compare.BASELINE_DIR", tmp_path / "baseline"), \
             patch("utils.image_compare.DIFF_DIR", tmp_path / "diff"):
            from utils.image_compare import ImageCompare
            driver = MagicMock()
            ic = ImageCompare(driver)
            with pytest.raises(RuntimeError, match="Pillow"):
                ic.compare("test_screen")


@pytest.mark.unit
class TestImageCompareInit:
    """ImageCompare 初始化"""

    @pytest.mark.unit
    def test_init_creates_directories(self, tmp_path):
        """初始化時建立 baseline 和 diff 目錄"""
        baseline_dir = tmp_path / "baseline"
        diff_dir = tmp_path / "diff"

        with patch("utils.image_compare.BASELINE_DIR", baseline_dir), \
             patch("utils.image_compare.DIFF_DIR", diff_dir):
            from utils.image_compare import ImageCompare
            driver = MagicMock()
            ic = ImageCompare(driver)
            assert baseline_dir.exists()
            assert diff_dir.exists()
            assert ic.threshold == 0.02

    @pytest.mark.unit
    def test_init_custom_threshold(self, tmp_path):
        """自訂閾值"""
        with patch("utils.image_compare.BASELINE_DIR", tmp_path / "baseline"), \
             patch("utils.image_compare.DIFF_DIR", tmp_path / "diff"):
            from utils.image_compare import ImageCompare
            driver = MagicMock()
            ic = ImageCompare(driver, threshold=0.05)
            assert ic.threshold == 0.05


@pytest.mark.unit
class TestImageCompareCapture:
    """ImageCompare.capture 方法"""

    @pytest.mark.unit
    def test_capture_calls_driver_get_screenshot(self, tmp_path):
        """capture 呼叫 driver.get_screenshot_as_png 並回傳 Image"""
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        with patch("utils.image_compare.BASELINE_DIR", tmp_path / "baseline"), \
             patch("utils.image_compare.DIFF_DIR", tmp_path / "diff"):
            from utils.image_compare import ImageCompare

            driver = MagicMock()
            # 建立一個小的 PNG 圖片作為模擬回傳
            img = Image.new("RGB", (100, 100), color="red")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            driver.get_screenshot_as_png.return_value = buf.getvalue()

            ic = ImageCompare(driver)
            result = ic.capture()

            driver.get_screenshot_as_png.assert_called_once()
            assert isinstance(result, Image.Image)
            assert result.size == (100, 100)


@pytest.mark.unit
class TestImageCompareSaveBaseline:
    """ImageCompare.save_baseline 方法"""

    @pytest.mark.unit
    def test_save_baseline_saves_image(self, tmp_path):
        """save_baseline 儲存截圖到 baseline 目錄"""
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        baseline_dir = tmp_path / "baseline"
        diff_dir = tmp_path / "diff"

        with patch("utils.image_compare.BASELINE_DIR", baseline_dir), \
             patch("utils.image_compare.DIFF_DIR", diff_dir):
            from utils.image_compare import ImageCompare

            driver = MagicMock()
            img = Image.new("RGB", (50, 50), color="blue")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            driver.get_screenshot_as_png.return_value = buf.getvalue()

            ic = ImageCompare(driver)
            result_path = ic.save_baseline("login_screen")

            assert result_path == baseline_dir / "login_screen.png"
            assert result_path.exists()


@pytest.mark.unit
class TestImageCompareCompare:
    """ImageCompare.compare 方法"""

    @pytest.mark.unit
    def test_compare_baseline_exists_match(self, tmp_path):
        """baseline 存在且匹配時回傳 match=True"""
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        baseline_dir = tmp_path / "baseline"
        diff_dir = tmp_path / "diff"
        baseline_dir.mkdir(parents=True)
        diff_dir.mkdir(parents=True)

        # 建立 baseline 圖片
        baseline_img = Image.new("RGB", (50, 50), color="green")
        baseline_path = baseline_dir / "test_match.png"
        baseline_img.save(str(baseline_path))

        # 模擬截圖回傳相同圖片
        buf = io.BytesIO()
        baseline_img.save(buf, format="PNG")
        screenshot_bytes = buf.getvalue()

        with patch("utils.image_compare.BASELINE_DIR", baseline_dir), \
             patch("utils.image_compare.DIFF_DIR", diff_dir):
            from utils.image_compare import ImageCompare

            driver = MagicMock()
            driver.get_screenshot_as_png.return_value = screenshot_bytes

            ic = ImageCompare(driver, threshold=0.02)
            result = ic.compare("test_match")

            assert result["match"] is True
            assert result["diff_percent"] == 0.0
            assert result["diff_image"] is None

    @pytest.mark.unit
    def test_compare_baseline_exists_mismatch(self, tmp_path):
        """baseline 存在但不匹配時回傳 match=False 並產生 diff 圖"""
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        baseline_dir = tmp_path / "baseline"
        diff_dir = tmp_path / "diff"
        baseline_dir.mkdir(parents=True)
        diff_dir.mkdir(parents=True)

        # 建立 baseline 圖片 (全黑)
        baseline_img = Image.new("RGB", (50, 50), color="black")
        baseline_path = baseline_dir / "test_mismatch.png"
        baseline_img.save(str(baseline_path))

        # 模擬截圖回傳不同圖片 (全白)
        current_img = Image.new("RGB", (50, 50), color="white")
        buf = io.BytesIO()
        current_img.save(buf, format="PNG")
        screenshot_bytes = buf.getvalue()

        with patch("utils.image_compare.BASELINE_DIR", baseline_dir), \
             patch("utils.image_compare.DIFF_DIR", diff_dir):
            from utils.image_compare import ImageCompare

            driver = MagicMock()
            driver.get_screenshot_as_png.return_value = screenshot_bytes

            ic = ImageCompare(driver, threshold=0.02)
            result = ic.compare("test_mismatch")

            assert result["match"] is False
            assert result["diff_percent"] > 0.02
            assert result["diff_image"] is not None
            assert result["diff_image"].exists()

    @pytest.mark.unit
    def test_compare_baseline_not_exists_auto_creates(self, tmp_path):
        """baseline 不存在時自動建立並回傳 match=True"""
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        baseline_dir = tmp_path / "baseline"
        diff_dir = tmp_path / "diff"
        baseline_dir.mkdir(parents=True)
        diff_dir.mkdir(parents=True)

        # 模擬截圖
        img = Image.new("RGB", (50, 50), color="red")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        screenshot_bytes = buf.getvalue()

        with patch("utils.image_compare.BASELINE_DIR", baseline_dir), \
             patch("utils.image_compare.DIFF_DIR", diff_dir):
            from utils.image_compare import ImageCompare

            driver = MagicMock()
            driver.get_screenshot_as_png.return_value = screenshot_bytes

            ic = ImageCompare(driver)
            result = ic.compare("new_screen")

            assert result["match"] is True
            assert result["diff_percent"] == 0.0
            # baseline 應被自動建立
            assert (baseline_dir / "new_screen.png").exists()


@pytest.mark.unit
class TestImageCompareAssertMatch:
    """ImageCompare.assert_match 方法"""

    @pytest.mark.unit
    def test_assert_match_passes(self, tmp_path):
        """匹配時不拋出異常"""
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        baseline_dir = tmp_path / "baseline"
        diff_dir = tmp_path / "diff"
        baseline_dir.mkdir(parents=True)
        diff_dir.mkdir(parents=True)

        # 建立 baseline
        img = Image.new("RGB", (50, 50), color="blue")
        baseline_path = baseline_dir / "pass_test.png"
        img.save(str(baseline_path))

        buf = io.BytesIO()
        img.save(buf, format="PNG")

        with patch("utils.image_compare.BASELINE_DIR", baseline_dir), \
             patch("utils.image_compare.DIFF_DIR", diff_dir):
            from utils.image_compare import ImageCompare

            driver = MagicMock()
            driver.get_screenshot_as_png.return_value = buf.getvalue()

            ic = ImageCompare(driver)
            # 不應拋出 AssertionError
            ic.assert_match("pass_test")

    @pytest.mark.unit
    def test_assert_match_raises_assertion_error_on_mismatch(self, tmp_path):
        """不匹配時拋出 AssertionError"""
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        baseline_dir = tmp_path / "baseline"
        diff_dir = tmp_path / "diff"
        baseline_dir.mkdir(parents=True)
        diff_dir.mkdir(parents=True)

        # 建立 baseline (全黑)
        baseline_img = Image.new("RGB", (50, 50), color="black")
        baseline_path = baseline_dir / "fail_test.png"
        baseline_img.save(str(baseline_path))

        # 截圖回傳 (全白)
        current_img = Image.new("RGB", (50, 50), color="white")
        buf = io.BytesIO()
        current_img.save(buf, format="PNG")

        with patch("utils.image_compare.BASELINE_DIR", baseline_dir), \
             patch("utils.image_compare.DIFF_DIR", diff_dir):
            from utils.image_compare import ImageCompare

            driver = MagicMock()
            driver.get_screenshot_as_png.return_value = buf.getvalue()

            ic = ImageCompare(driver, threshold=0.02)
            with pytest.raises(AssertionError, match="視覺回歸失敗"):
                ic.assert_match("fail_test")


@pytest.mark.unit
class TestImageCompareCalcDiff:
    """ImageCompare._calc_diff 方法"""

    @pytest.mark.unit
    def test_calc_diff_identical_images_zero(self, tmp_path):
        """相同圖片差異為 0.0"""
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        with patch("utils.image_compare.BASELINE_DIR", tmp_path / "baseline"), \
             patch("utils.image_compare.DIFF_DIR", tmp_path / "diff"):
            from utils.image_compare import ImageCompare

            driver = MagicMock()
            ic = ImageCompare(driver)

            img = Image.new("RGB", (50, 50), color="red")
            diff = ic._calc_diff(img, img)
            assert diff == 0.0

    @pytest.mark.unit
    def test_calc_diff_different_images_greater_than_zero(self, tmp_path):
        """不同圖片差異大於 0"""
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        with patch("utils.image_compare.BASELINE_DIR", tmp_path / "baseline"), \
             patch("utils.image_compare.DIFF_DIR", tmp_path / "diff"):
            from utils.image_compare import ImageCompare

            driver = MagicMock()
            ic = ImageCompare(driver)

            img1 = Image.new("RGB", (50, 50), color="black")
            img2 = Image.new("RGB", (50, 50), color="white")
            diff = ic._calc_diff(img1, img2)
            assert diff > 0.0

    @pytest.mark.unit
    def test_calc_diff_black_vs_white_is_one(self, tmp_path):
        """全黑對全白差異為 1.0"""
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        with patch("utils.image_compare.BASELINE_DIR", tmp_path / "baseline"), \
             patch("utils.image_compare.DIFF_DIR", tmp_path / "diff"):
            from utils.image_compare import ImageCompare

            driver = MagicMock()
            ic = ImageCompare(driver)

            img1 = Image.new("RGB", (10, 10), color=(0, 0, 0))
            img2 = Image.new("RGB", (10, 10), color=(255, 255, 255))
            diff = ic._calc_diff(img1, img2)
            assert abs(diff - 1.0) < 0.001


@pytest.mark.unit
class TestImageCompareSaveDiff:
    """ImageCompare._save_diff 方法"""

    @pytest.mark.unit
    def test_save_diff_creates_combined_image(self, tmp_path):
        """_save_diff 建立合併的差異對比圖"""
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow not installed")

        baseline_dir = tmp_path / "baseline"
        diff_dir = tmp_path / "diff"
        baseline_dir.mkdir(parents=True)
        diff_dir.mkdir(parents=True)

        with patch("utils.image_compare.BASELINE_DIR", baseline_dir), \
             patch("utils.image_compare.DIFF_DIR", diff_dir):
            from utils.image_compare import ImageCompare

            driver = MagicMock()
            ic = ImageCompare(driver)

            baseline = Image.new("RGB", (50, 50), color="black")
            current = Image.new("RGB", (50, 50), color="white")

            result_path = ic._save_diff("test_diff", baseline, current)

            assert result_path.exists()
            assert "test_diff_diff_" in result_path.name
            # 合併圖應為 3 倍寬
            combined = Image.open(str(result_path))
            assert combined.size[0] == 150  # 50 * 3
            assert combined.size[1] == 50
