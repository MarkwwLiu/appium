"""
截圖工具
測試失敗時自動截圖，方便 debug。
"""

from datetime import datetime
from pathlib import Path

from config.config import Config
from utils.logger import logger


def take_screenshot(driver, name: str) -> str:
    """
    擷取螢幕截圖並儲存到 screenshots 目錄。

    Args:
        driver: Appium driver 實例
        name: 截圖名稱（不含副檔名）

    Returns:
        截圖檔案的完整路徑
    """
    Config.SCREENSHOT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name}_{timestamp}.png"
    filepath = Config.SCREENSHOT_DIR / filename
    driver.save_screenshot(str(filepath))
    logger.info(f"截圖已儲存: {filepath}")
    return str(filepath)
