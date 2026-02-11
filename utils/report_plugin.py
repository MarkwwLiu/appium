"""
自訂 pytest 報告 plugin
在終端機輸出更豐富的測試摘要：耗時排行、失敗分析、通過率統計等。
在 conftest.py 引入即可生效。
"""

import time
from collections import defaultdict

from utils.logger import logger


class TestMetrics:
    """收集測試指標"""

    def __init__(self):
        self.results: dict[str, list] = defaultdict(list)
        self.durations: dict[str, float] = {}
        self.start_time: float = 0

    def record(self, nodeid: str, outcome: str, duration: float) -> None:
        self.results[outcome].append(nodeid)
        self.durations[nodeid] = duration


_metrics = TestMetrics()


# ── pytest hooks ──

def pytest_sessionstart(session):
    """測試 session 開始"""
    _metrics.start_time = time.time()


def pytest_runtest_logreport(report):
    """每個測試結果回報"""
    if report.when == "call":
        _metrics.record(report.nodeid, report.outcome, report.duration)


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """在終端機輸出自訂測試摘要"""
    total_time = time.time() - _metrics.start_time
    passed = _metrics.results.get("passed", [])
    failed = _metrics.results.get("failed", [])
    skipped = _metrics.results.get("skipped", [])
    total = len(passed) + len(failed) + len(skipped)

    if total == 0:
        return

    pass_rate = len(passed) / total * 100 if total > 0 else 0

    sep = "=" * 60
    lines = [
        "",
        sep,
        "  APPIUM 測試報告摘要",
        sep,
        "",
        f"  總計:   {total} 個測試",
        f"  通過:   {len(passed)}",
        f"  失敗:   {len(failed)}",
        f"  跳過:   {len(skipped)}",
        f"  通過率: {pass_rate:.1f}%",
        f"  總耗時: {total_time:.1f} 秒",
        "",
    ]

    # 失敗測試清單
    if failed:
        lines.append("  --- 失敗測試 ---")
        for nodeid in failed:
            dur = _metrics.durations.get(nodeid, 0)
            lines.append(f"    FAIL  {nodeid}  ({dur:.2f}s)")
        lines.append("")

    # 最慢的 5 個測試
    if _metrics.durations:
        sorted_by_time = sorted(
            _metrics.durations.items(), key=lambda x: x[1], reverse=True
        )[:5]
        lines.append("  --- 最慢的測試 (Top 5) ---")
        for nodeid, dur in sorted_by_time:
            lines.append(f"    {dur:.2f}s  {nodeid}")
        lines.append("")

    lines.append(sep)

    # 輸出到終端機
    writer = terminalreporter
    writer.section("Appium Test Report", sep="=")
    for line in lines:
        writer.line(line)

    # 同時寫入 log
    for line in lines:
        logger.info(line)
