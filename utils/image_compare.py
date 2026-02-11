"""
圖片比對工具 — 視覺回歸測試
比較兩張截圖的差異，超過閾值即判定 UI 有變動。
使用純 Python 實作，不依賴 OpenCV。
"""

import io
import math
import os
from datetime import datetime
from pathlib import Path

from config.config import Config
from utils.logger import logger

try:
    from PIL import Image, ImageChops, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.debug("Pillow 未安裝，圖片比對功能停用 (pip install Pillow)")


BASELINE_DIR = Config.SCREENSHOT_DIR / "baseline"
DIFF_DIR = Config.SCREENSHOT_DIR / "diff"


class ImageCompare:
    """視覺回歸測試：比對截圖是否與 baseline 一致"""

    def __init__(self, driver, threshold: float = 0.02):
        """
        Args:
            driver: Appium driver
            threshold: 容許差異比例 (0.0~1.0)，預設 2%
        """
        self.driver = driver
        self.threshold = threshold
        BASELINE_DIR.mkdir(parents=True, exist_ok=True)
        DIFF_DIR.mkdir(parents=True, exist_ok=True)

    def capture(self) -> "Image.Image":
        """擷取當前畫面為 PIL Image"""
        if not PIL_AVAILABLE:
            raise RuntimeError("需安裝 Pillow: pip install Pillow")
        png_bytes = self.driver.get_screenshot_as_png()
        return Image.open(io.BytesIO(png_bytes))

    def save_baseline(self, name: str) -> Path:
        """儲存目前畫面作為 baseline"""
        img = self.capture()
        path = BASELINE_DIR / f"{name}.png"
        img.save(str(path))
        logger.info(f"Baseline 已儲存: {path}")
        return path

    def compare(self, name: str) -> dict:
        """
        比對目前畫面與 baseline。

        Args:
            name: baseline 名稱

        Returns:
            {
                "match": bool,
                "diff_percent": float,
                "diff_image": Path | None,
            }
        """
        if not PIL_AVAILABLE:
            raise RuntimeError("需安裝 Pillow: pip install Pillow")

        baseline_path = BASELINE_DIR / f"{name}.png"
        if not baseline_path.exists():
            logger.warning(f"Baseline 不存在，自動建立: {name}")
            self.save_baseline(name)
            return {"match": True, "diff_percent": 0.0, "diff_image": None}

        baseline = Image.open(str(baseline_path))
        current = self.capture()

        # 統一尺寸
        if baseline.size != current.size:
            current = current.resize(baseline.size)

        diff_percent = self._calc_diff(baseline, current)
        match = diff_percent <= self.threshold

        result = {
            "match": match,
            "diff_percent": diff_percent,
            "diff_image": None,
        }

        if not match:
            diff_path = self._save_diff(name, baseline, current)
            result["diff_image"] = diff_path
            logger.warning(
                f"視覺差異 {diff_percent:.2%} 超過閾值 {self.threshold:.2%} "
                f"-> {diff_path}"
            )
        else:
            logger.info(f"視覺比對通過: {name} (差異 {diff_percent:.4%})")

        return result

    def assert_match(self, name: str) -> None:
        """比對並 assert，不一致時 raise AssertionError"""
        result = self.compare(name)
        assert result["match"], (
            f"視覺回歸失敗: '{name}' 差異 {result['diff_percent']:.2%} "
            f"(閾值 {self.threshold:.2%})。差異圖: {result['diff_image']}"
        )

    def _calc_diff(self, img1: "Image.Image", img2: "Image.Image") -> float:
        """計算兩張圖片的差異比例"""
        diff = ImageChops.difference(img1.convert("RGB"), img2.convert("RGB"))
        pixels = list(diff.getdata())
        total = len(pixels) * 3 * 255  # R+G+B 每個最大 255
        diff_sum = sum(sum(p) for p in pixels)
        return diff_sum / total if total > 0 else 0.0

    def _save_diff(
        self, name: str, baseline: "Image.Image", current: "Image.Image"
    ) -> Path:
        """產生並儲存差異對比圖（左：baseline, 中：current, 右：diff）"""
        diff = ImageChops.difference(baseline.convert("RGB"), current.convert("RGB"))

        w, h = baseline.size
        combined = Image.new("RGB", (w * 3, h))
        combined.paste(baseline.convert("RGB"), (0, 0))
        combined.paste(current.convert("RGB"), (w, 0))
        combined.paste(diff, (w * 2, 0))

        # 加標籤
        draw = ImageDraw.Draw(combined)
        draw.text((10, 10), "Baseline", fill="white")
        draw.text((w + 10, 10), "Current", fill="white")
        draw.text((w * 2 + 10, 10), "Diff", fill="white")

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = DIFF_DIR / f"{name}_diff_{ts}.png"
        combined.save(str(path))
        return path
