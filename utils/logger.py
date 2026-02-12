"""
日誌模組
統一的 logging 設定，同時輸出到 console 與檔案。

支援：
- Console 彩色輸出（人類可讀格式）
- 檔案輸出（純文字 + 可選 JSON 結構化格式）
- 環境變數控制:
    LOG_LEVEL: console 日誌等級 (預設 INFO)
    LOG_JSON: 設為 "1" 啟用 JSON 結構化日誌檔
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "reports"
LOG_DIR.mkdir(exist_ok=True)


class JsonFormatter(logging.Formatter):
    """JSON 結構化日誌格式器，適合 ELK / Loki 等日誌系統"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


def _create_logger() -> logging.Logger:
    _logger = logging.Logger("appium_test")
    _logger.setLevel(logging.DEBUG)

    console_level = getattr(
        logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO
    )

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-7s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler（人類可讀）
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(console_level)
    console.setFormatter(fmt)
    _logger.addHandler(console)

    # File handler（純文字）
    file_handler = logging.FileHandler(LOG_DIR / "test.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    _logger.addHandler(file_handler)

    # JSON file handler（可選，設 LOG_JSON=1 啟用）
    if os.getenv("LOG_JSON", "").strip() == "1":
        json_handler = logging.FileHandler(
            LOG_DIR / "test.json.log", encoding="utf-8"
        )
        json_handler.setLevel(logging.DEBUG)
        json_handler.setFormatter(JsonFormatter())
        _logger.addHandler(json_handler)

    return _logger


logger = _create_logger()
