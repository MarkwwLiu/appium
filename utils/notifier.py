"""
測試結果通知工具
測試完成後將結果推送到 Slack 或自訂 Webhook。
"""

import json
import os
from datetime import datetime
from urllib.request import Request, urlopen

from utils.logger import logger


class Notifier:
    """測試結果通知推送"""

    def __init__(self, webhook_url: str | None = None):
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL", "")

    def send_slack(self, message: str) -> bool:
        """
        發送 Slack 訊息。

        Args:
            message: 訊息內容（支援 Slack markdown）

        Returns:
            是否發送成功
        """
        if not self.webhook_url:
            logger.warning("未設定 SLACK_WEBHOOK_URL，跳過通知")
            return False

        payload = json.dumps({"text": message}).encode("utf-8")
        req = Request(
            self.webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(req, timeout=10) as resp:
                success = resp.status == 200
                if success:
                    logger.info("Slack 通知已發送")
                return success
        except Exception as e:
            logger.error(f"Slack 通知發送失敗: {e}")
            return False

    def send_webhook(self, url: str, data: dict) -> bool:
        """發送自訂 Webhook (POST JSON)"""
        payload = json.dumps(data).encode("utf-8")
        req = Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as e:
            logger.error(f"Webhook 發送失敗: {e}")
            return False

    def format_test_report(
        self,
        total: int,
        passed: int,
        failed: int,
        skipped: int,
        duration: float,
        platform: str = "",
    ) -> str:
        """
        格式化測試報告為 Slack 訊息。

        Returns:
            格式化後的訊息字串
        """
        status = "PASS" if failed == 0 else "FAIL"
        emoji = ":white_check_mark:" if failed == 0 else ":x:"
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        return (
            f"{emoji} *Appium 測試報告* ({now})\n"
            f"{'─' * 30}\n"
            f"*平台:* {platform or 'N/A'}\n"
            f"*狀態:* {status}\n"
            f"*總計:* {total} 個測試\n"
            f"  :white_check_mark: 通過: {passed}\n"
            f"  :x: 失敗: {failed}\n"
            f"  :fast_forward: 跳過: {skipped}\n"
            f"*耗時:* {duration:.1f} 秒"
        )


# ── pytest plugin：測試結束後自動發送通知 ──

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """
    pytest hook：在測試結束時自動發送通知。
    需要設定環境變數 SLACK_WEBHOOK_URL。
    將此函式加入 conftest.py 即可啟用。
    """
    webhook = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook:
        return

    stats = terminalreporter.stats
    passed = len(stats.get("passed", []))
    failed = len(stats.get("failed", []))
    skipped = len(stats.get("skipped", []))
    total = passed + failed + skipped

    duration = terminalreporter._sessionstarttime
    elapsed = __import__("time").time() - duration

    platform = config.getoption("--platform", default="")

    notifier = Notifier(webhook)
    message = notifier.format_test_report(
        total=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        duration=elapsed,
        platform=platform,
    )
    notifier.send_slack(message)
