"""
utils/logger.py 單元測試

驗證 JsonFormatter 格式正確、logger 基本功能。
"""

import json
import logging

import pytest

from utils.logger import JsonFormatter, logger


@pytest.mark.unit
class TestJsonFormatter:
    """JsonFormatter"""

    @pytest.mark.unit
    def test_format_produces_valid_json(self):
        """輸出合法 JSON"""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py",
            lineno=1, msg="hello", args=(), exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["message"] == "hello"
        assert parsed["level"] == "INFO"

    @pytest.mark.unit
    def test_format_contains_required_fields(self):
        """包含必要欄位"""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="appium", level=logging.WARNING, pathname="core/base.py",
            lineno=42, msg="warn msg", args=(), exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert "timestamp" in parsed
        assert "level" in parsed
        assert "message" in parsed
        assert "logger" in parsed
        assert "module" in parsed
        assert "line" in parsed

    @pytest.mark.unit
    def test_format_with_exception(self):
        """有例外時包含 exception 欄位"""
        formatter = JsonFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test", level=logging.ERROR, pathname="test.py",
            lineno=1, msg="error", args=(), exc_info=exc_info,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert "exception" in parsed
        assert "ValueError" in parsed["exception"]

    @pytest.mark.unit
    def test_format_unicode(self):
        """支援中文等 unicode"""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py",
            lineno=1, msg="測試中文訊息", args=(), exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["message"] == "測試中文訊息"


@pytest.mark.unit
class TestLoggerInstance:
    """logger 實例"""

    @pytest.mark.unit
    def test_logger_exists(self):
        """全域 logger 已建立"""
        assert logger is not None

    @pytest.mark.unit
    def test_logger_name(self):
        """logger 名稱正確"""
        assert logger.name == "appium_test"

    @pytest.mark.unit
    def test_logger_has_handlers(self):
        """logger 至少有 handler"""
        assert len(logger.handlers) >= 1

    @pytest.mark.unit
    def test_logger_level(self):
        """logger level 是 DEBUG（最細粒度）"""
        assert logger.level == logging.DEBUG
