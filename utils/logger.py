"""
日誌模組
統一的 logging 設定，同時輸出到 console 與檔案。
"""

import logging
import sys
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "reports"
LOG_DIR.mkdir(exist_ok=True)


def _create_logger() -> logging.Logger:
    _logger = logging.Logger("appium_test")
    _logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-7s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    _logger.addHandler(console)

    # File handler
    file_handler = logging.FileHandler(LOG_DIR / "test.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    _logger.addHandler(file_handler)

    return _logger


logger = _create_logger()
