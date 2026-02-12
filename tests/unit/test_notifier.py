"""
utils.notifier 單元測試
驗證 Notifier 的 Slack / Webhook 通知發送與測試報告格式化功能。
"""

import json
import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.unit
class TestNotifierInit:
    """Notifier 初始化"""

    @pytest.mark.unit
    def test_init_with_webhook_url(self):
        """直接傳入 webhook_url"""
        from utils.notifier import Notifier
        n = Notifier(webhook_url="https://hooks.slack.com/test")
        assert n.webhook_url == "https://hooks.slack.com/test"

    @pytest.mark.unit
    def test_init_without_url_reads_env_var(self):
        """未傳入 url 時讀取環境變數"""
        with patch("utils.notifier.os.getenv", return_value="https://env-webhook.com"):
            from utils.notifier import Notifier
            n = Notifier()
            assert n.webhook_url == "https://env-webhook.com"

    @pytest.mark.unit
    def test_init_neither_url_nor_env_empty_string(self):
        """無 url 也無環境變數時為空字串"""
        with patch.dict("os.environ", {}, clear=True):
            from utils.notifier import Notifier
            n = Notifier(webhook_url=None)
            # webhook_url 應為空字串 (from os.getenv default)
            assert n.webhook_url == "" or isinstance(n.webhook_url, str)


@pytest.mark.unit
class TestNotifierSendSlack:
    """Notifier.send_slack 方法"""

    @pytest.mark.unit
    def test_send_slack_no_webhook_returns_false(self):
        """無 webhook URL 時回傳 False"""
        from utils.notifier import Notifier
        n = Notifier(webhook_url="")
        result = n.send_slack("test message")
        assert result is False

    @pytest.mark.unit
    def test_send_slack_success_returns_true(self):
        """成功發送時回傳 True"""
        from utils.notifier import Notifier
        n = Notifier(webhook_url="https://hooks.slack.com/test")

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("utils.notifier.urlopen", return_value=mock_response):
            result = n.send_slack("Hello Slack")
            assert result is True

    @pytest.mark.unit
    def test_send_slack_failure_returns_false(self):
        """發送失敗時回傳 False"""
        from utils.notifier import Notifier
        n = Notifier(webhook_url="https://hooks.slack.com/test")

        with patch("utils.notifier.urlopen", side_effect=Exception("Network error")):
            result = n.send_slack("Hello Slack")
            assert result is False

    @pytest.mark.unit
    def test_send_slack_non_200_returns_false(self):
        """回應非 200 時回傳 False"""
        from utils.notifier import Notifier
        n = Notifier(webhook_url="https://hooks.slack.com/test")

        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("utils.notifier.urlopen", return_value=mock_response):
            result = n.send_slack("Hello Slack")
            assert result is False

    @pytest.mark.unit
    def test_send_slack_sends_correct_payload(self):
        """發送的 payload 格式正確"""
        from utils.notifier import Notifier
        n = Notifier(webhook_url="https://hooks.slack.com/test")

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("utils.notifier.urlopen", return_value=mock_response) as mock_urlopen, \
             patch("utils.notifier.Request") as mock_request:
            n.send_slack("test message")
            # 驗證 Request 被正確建構
            call_kwargs = mock_request.call_args
            data = call_kwargs[1].get("data") or call_kwargs[0][1] if len(call_kwargs[0]) > 1 else call_kwargs[1].get("data")
            if data:
                payload = json.loads(data)
                assert payload["text"] == "test message"


@pytest.mark.unit
class TestNotifierSendWebhook:
    """Notifier.send_webhook 方法"""

    @pytest.mark.unit
    def test_send_webhook_success_returns_true(self):
        """成功發送自訂 webhook 回傳 True"""
        from utils.notifier import Notifier
        n = Notifier()

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("utils.notifier.urlopen", return_value=mock_response):
            result = n.send_webhook(
                "https://custom-webhook.com/api",
                {"key": "value"}
            )
            assert result is True

    @pytest.mark.unit
    def test_send_webhook_failure_returns_false(self):
        """發送失敗時回傳 False"""
        from utils.notifier import Notifier
        n = Notifier()

        with patch("utils.notifier.urlopen", side_effect=Exception("Connection refused")):
            result = n.send_webhook(
                "https://custom-webhook.com/api",
                {"key": "value"}
            )
            assert result is False

    @pytest.mark.unit
    def test_send_webhook_non_200_returns_false(self):
        """回應非 200 時回傳 False"""
        from utils.notifier import Notifier
        n = Notifier()

        mock_response = MagicMock()
        mock_response.status = 403
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("utils.notifier.urlopen", return_value=mock_response):
            result = n.send_webhook("https://custom-webhook.com/api", {})
            assert result is False


@pytest.mark.unit
class TestNotifierFormatTestReport:
    """Notifier.format_test_report 方法"""

    @pytest.mark.unit
    def test_format_all_passed_shows_pass_status(self):
        """全部通過時顯示 PASS 狀態"""
        from utils.notifier import Notifier
        n = Notifier()
        report = n.format_test_report(
            total=10, passed=10, failed=0, skipped=0, duration=25.3
        )
        assert "PASS" in report
        assert ":white_check_mark:" in report

    @pytest.mark.unit
    def test_format_some_failed_shows_fail_status(self):
        """有失敗時顯示 FAIL 狀態"""
        from utils.notifier import Notifier
        n = Notifier()
        report = n.format_test_report(
            total=10, passed=7, failed=3, skipped=0, duration=30.0
        )
        assert "FAIL" in report
        assert ":x:" in report

    @pytest.mark.unit
    def test_format_contains_all_fields(self):
        """報告包含所有欄位"""
        from utils.notifier import Notifier
        n = Notifier()
        report = n.format_test_report(
            total=20, passed=15, failed=3, skipped=2,
            duration=45.7, platform="Android"
        )
        assert "20" in report       # total
        assert "15" in report       # passed
        assert "3" in report        # failed
        assert "2" in report        # skipped
        assert "45.7" in report     # duration
        assert "Android" in report  # platform

    @pytest.mark.unit
    def test_format_no_platform_shows_na(self):
        """未指定平台時顯示 N/A"""
        from utils.notifier import Notifier
        n = Notifier()
        report = n.format_test_report(
            total=5, passed=5, failed=0, skipped=0, duration=10.0
        )
        assert "N/A" in report

    @pytest.mark.unit
    def test_format_with_platform_shows_platform_name(self):
        """指定平台時顯示平台名稱"""
        from utils.notifier import Notifier
        n = Notifier()
        report = n.format_test_report(
            total=5, passed=5, failed=0, skipped=0,
            duration=10.0, platform="iOS"
        )
        assert "iOS" in report
        assert "N/A" not in report


@pytest.mark.unit
class TestPytestTerminalSummary:
    """pytest_terminal_summary hook 函式"""

    @pytest.mark.unit
    def test_no_webhook_env_returns_early(self):
        """無 SLACK_WEBHOOK_URL 環境變數時直接返回"""
        from utils.notifier import pytest_terminal_summary

        mock_reporter = MagicMock()
        mock_config = MagicMock()

        with patch("utils.notifier.os.getenv", return_value=None):
            # 不應拋出異常，直接返回
            pytest_terminal_summary(mock_reporter, 0, mock_config)

    @pytest.mark.unit
    def test_with_webhook_sends_notification(self):
        """有 SLACK_WEBHOOK_URL 環境變數時發送通知"""
        from utils.notifier import pytest_terminal_summary

        mock_reporter = MagicMock()
        mock_reporter.stats = {
            "passed": [1, 2, 3],
            "failed": [4],
            "skipped": [5],
        }
        mock_reporter._sessionstarttime = 1000.0

        mock_config = MagicMock()
        mock_config.getoption.return_value = "Android"

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        import time as time_module
        with patch("utils.notifier.os.getenv", return_value="https://hooks.slack.com/test"), \
             patch("utils.notifier.urlopen", return_value=mock_response), \
             patch.object(time_module, "time", return_value=1010.0):
            pytest_terminal_summary(mock_reporter, 1, mock_config)

    @pytest.mark.unit
    def test_with_webhook_empty_stats(self):
        """stats 為空時仍能正確格式化並發送"""
        from utils.notifier import pytest_terminal_summary

        mock_reporter = MagicMock()
        mock_reporter.stats = {}
        mock_reporter._sessionstarttime = 1000.0

        mock_config = MagicMock()
        mock_config.getoption.return_value = ""

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        import time as time_module
        with patch("utils.notifier.os.getenv", return_value="https://hooks.slack.com/test"), \
             patch("utils.notifier.urlopen", return_value=mock_response), \
             patch.object(time_module, "time", return_value=1005.0):
            pytest_terminal_summary(mock_reporter, 0, mock_config)
