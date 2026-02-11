"""
Smart Test Selection — 智慧選測

根據歷史測試結果、失敗率、flaky 分數，自動計算每個測試的風險權重，
優先執行高風險測試，跳過低風險測試，大幅縮短 CI 回饋時間。

用法 (CLI)：
    pytest --smart-select                    # 自動排序，高風險先跑
    pytest --smart-select --risk-threshold 0.3  # 只跑風險 > 0.3 的測試
    pytest --smart-select --max-tests 50        # 最多跑 50 個

用法 (程式)：
    from utils.smart_selector import SmartSelector
    selector = SmartSelector(result_db_path="reports/test_results.db")
    ranked = selector.rank_tests()
    selected = selector.select(threshold=0.3, max_count=50)
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from utils.logger import logger


@dataclass
class TestRisk:
    """單一測試的風險評估"""
    test_name: str
    risk_score: float       # 0.0 ~ 1.0 綜合風險分數
    recent_fail_rate: float  # 最近 N 次的失敗率
    flaky_score: float       # 不穩定分數 (狀態切換次數 / 總次數)
    avg_duration: float      # 平均執行時間 (秒)
    last_outcome: str        # 最後一次結果
    run_count: int           # 歷史執行次數


class SmartSelector:
    """
    根據 ResultDB 歷史資料計算測試風險分數並排序

    風險分數公式：
        risk = w1 * recent_fail_rate + w2 * flaky_score + w3 * (1 if last_failed else 0)

    預設權重：
        recent_fail_rate: 0.5  (最近失敗率)
        flaky_score:      0.3  (不穩定度)
        last_failed:      0.2  (上次是否失敗)
    """

    def __init__(
        self,
        result_db_path: str = "reports/test_results.db",
        window: int = 20,
        weights: tuple[float, float, float] = (0.5, 0.3, 0.2),
    ):
        self._db_path = result_db_path
        self._window = window
        self._w_fail, self._w_flaky, self._w_last = weights

    def rank_tests(self) -> list[TestRisk]:
        """計算所有測試的風險分數，按風險高→低排序"""
        db_path = Path(self._db_path)
        if not db_path.exists():
            logger.warning(f"[SmartSelector] 找不到 ResultDB: {db_path}")
            return []

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            return self._calculate_risks(conn)
        finally:
            conn.close()

    def select(
        self,
        threshold: float = 0.0,
        max_count: int | None = None,
    ) -> list[TestRisk]:
        """
        篩選高風險測試

        Args:
            threshold: 最低風險分數 (0.0 = 全部, 0.3 = 只跑風險 > 0.3)
            max_count: 最多回傳幾個測試
        """
        ranked = self.rank_tests()
        filtered = [t for t in ranked if t.risk_score >= threshold]
        if max_count:
            filtered = filtered[:max_count]
        logger.info(
            f"[SmartSelector] 篩選結果: {len(filtered)}/{len(ranked)} "
            f"(threshold={threshold})"
        )
        return filtered

    def get_skip_list(self, threshold: float = 0.1) -> list[str]:
        """取得建議跳過的低風險測試名稱"""
        ranked = self.rank_tests()
        return [t.test_name for t in ranked if t.risk_score < threshold]

    def _calculate_risks(self, conn: sqlite3.Connection) -> list[TestRisk]:
        """計算每個測試的風險分數"""
        # 取得所有不重複測試名稱
        cursor = conn.execute(
            "SELECT DISTINCT test_name FROM results ORDER BY test_name"
        )
        test_names = [row["test_name"] for row in cursor.fetchall()]

        risks: list[TestRisk] = []

        for name in test_names:
            # 最近 N 次結果
            rows = conn.execute(
                """
                SELECT outcome, duration
                FROM results
                WHERE test_name = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (name, self._window),
            ).fetchall()

            if not rows:
                continue

            total = len(rows)
            failed = sum(1 for r in rows if r["outcome"] == "failed")
            recent_fail_rate = failed / total if total > 0 else 0.0

            # flaky 分數: 狀態切換次數 / (total - 1)
            transitions = 0
            for i in range(1, len(rows)):
                if rows[i]["outcome"] != rows[i - 1]["outcome"]:
                    transitions += 1
            flaky_score = transitions / (total - 1) if total > 1 else 0.0

            # 平均執行時間
            durations = [r["duration"] for r in rows if r["duration"]]
            avg_duration = sum(durations) / len(durations) if durations else 0.0

            # 最後結果
            last_outcome = rows[0]["outcome"]
            last_failed = 1.0 if last_outcome == "failed" else 0.0

            # 綜合風險分數
            risk_score = (
                self._w_fail * recent_fail_rate
                + self._w_flaky * flaky_score
                + self._w_last * last_failed
            )
            risk_score = min(1.0, max(0.0, risk_score))

            risks.append(TestRisk(
                test_name=name,
                risk_score=round(risk_score, 4),
                recent_fail_rate=round(recent_fail_rate, 4),
                flaky_score=round(flaky_score, 4),
                avg_duration=round(avg_duration, 2),
                last_outcome=last_outcome,
                run_count=total,
            ))

        # 按風險分數降序排列
        risks.sort(key=lambda t: (-t.risk_score, -t.recent_fail_rate))
        return risks

    def print_report(self, top_n: int = 20) -> None:
        """印出風險排名報告"""
        ranked = self.rank_tests()
        print("\n" + "=" * 75)
        print("  智慧選測 — 測試風險排名")
        print("=" * 75)
        print(f"  {'排名':<4} {'風險':<8} {'失敗率':<8} {'Flaky':<8} {'最後':<8} {'測試名稱'}")
        print("-" * 75)
        for i, t in enumerate(ranked[:top_n], 1):
            status = "FAIL" if t.last_outcome == "failed" else "PASS"
            print(
                f"  {i:<4} {t.risk_score:<8.3f} {t.recent_fail_rate:<8.1%} "
                f"{t.flaky_score:<8.2f} {status:<8} {t.test_name}"
            )
        print("=" * 75)
        print(f"  共 {len(ranked)} 個測試\n")
