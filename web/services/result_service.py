"""
ResultDB 查詢服務

封裝 ResultDB 的查詢邏輯，供 Web 頁面使用。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from config.config import Config

DB_PATH = Config.REPORT_DIR / "test_results.db"


class ResultService:
    """測試結果查詢服務"""

    def __init__(self, db_path: str | None = None):
        self._db_path = str(db_path or DB_PATH)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_db(self) -> bool:
        """確認 DB 存在"""
        return Path(self._db_path).exists()

    # ── Dashboard 查詢 ──

    def get_overview(self) -> dict:
        """Dashboard 總覽資料"""
        if not self._ensure_db():
            return self._empty_overview()

        conn = self._connect()
        try:
            # 最新一次 run
            latest = conn.execute(
                "SELECT * FROM runs ORDER BY start_time DESC LIMIT 1"
            ).fetchone()

            # 總計
            total_runs = conn.execute("SELECT COUNT(*) as cnt FROM runs").fetchone()["cnt"]
            total_tests = conn.execute(
                "SELECT COUNT(DISTINCT test_name) as cnt FROM results"
            ).fetchone()["cnt"]

            # 最近 7 次 run 的平均通過率
            recent_runs = conn.execute(
                "SELECT passed, total FROM runs ORDER BY start_time DESC LIMIT 7"
            ).fetchall()
            avg_pass_rate = 0.0
            if recent_runs:
                rates = [r["passed"] / r["total"] for r in recent_runs if r["total"] > 0]
                avg_pass_rate = sum(rates) / len(rates) if rates else 0.0

            return {
                "latest_run": dict(latest) if latest else None,
                "total_runs": total_runs,
                "total_tests": total_tests,
                "avg_pass_rate": round(avg_pass_rate * 100, 1),
            }
        finally:
            conn.close()

    def get_recent_runs(self, limit: int = 20) -> list[dict]:
        """取得最近 N 次 run"""
        if not self._ensure_db():
            return []
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM runs ORDER BY start_time DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_pass_rate_trend(self, limit: int = 30) -> list[dict]:
        """通過率趨勢"""
        if not self._ensure_db():
            return []
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM runs WHERE total > 0 ORDER BY start_time DESC LIMIT ?",
                (limit,),
            ).fetchall()
            trend = []
            for r in reversed(rows):
                trend.append({
                    "run_id": r["run_id"],
                    "date": r["start_time"][:16] if r["start_time"] else "",
                    "pass_rate": round(r["passed"] / r["total"] * 100, 1) if r["total"] > 0 else 0,
                    "total": r["total"],
                    "passed": r["passed"],
                    "failed": r["failed"],
                    "duration": round(r["duration"], 1) if r["duration"] else 0,
                })
            return trend
        finally:
            conn.close()

    def get_run_details(self, run_id: str) -> list[dict]:
        """取得某次 run 的所有測試結果"""
        if not self._ensure_db():
            return []
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM results WHERE run_id = ? ORDER BY timestamp",
                (run_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_all_test_names(self) -> list[str]:
        """取得所有測試名稱"""
        if not self._ensure_db():
            return []
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT DISTINCT test_name FROM results ORDER BY test_name"
            ).fetchall()
            return [r["test_name"] for r in rows]
        finally:
            conn.close()

    def get_test_history(self, test_name: str, limit: int = 30) -> list[dict]:
        """某測試的歷史紀錄"""
        if not self._ensure_db():
            return []
        conn = self._connect()
        try:
            rows = conn.execute(
                """SELECT r.*, runs.platform, runs.env
                   FROM results r
                   LEFT JOIN runs ON r.run_id = runs.run_id
                   WHERE r.test_name = ?
                   ORDER BY r.timestamp DESC LIMIT ?""",
                (test_name, limit),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_flaky_tests(self, window: int = 20) -> list[dict]:
        """取得 flaky 測試列表"""
        if not self._ensure_db():
            return []
        conn = self._connect()
        try:
            test_names = conn.execute(
                "SELECT DISTINCT test_name FROM results"
            ).fetchall()

            flaky = []
            for row in test_names:
                name = row["test_name"]
                results = conn.execute(
                    "SELECT outcome FROM results WHERE test_name = ? ORDER BY timestamp DESC LIMIT ?",
                    (name, window),
                ).fetchall()

                if len(results) < 3:
                    continue

                outcomes = [r["outcome"] for r in results]
                passed = outcomes.count("passed")
                failed = outcomes.count("failed")
                total = len(outcomes)
                rate = passed / total

                # 計算 flaky 分數 (狀態切換次數)
                transitions = sum(
                    1 for i in range(1, len(outcomes)) if outcomes[i] != outcomes[i - 1]
                )
                flaky_score = transitions / (total - 1) if total > 1 else 0

                if 0 < rate < 1:
                    flaky.append({
                        "test_name": name,
                        "pass_rate": round(rate * 100, 1),
                        "flaky_score": round(flaky_score, 2),
                        "total": total,
                        "passed": passed,
                        "failed": failed,
                    })

            flaky.sort(key=lambda x: -x["flaky_score"])
            return flaky
        finally:
            conn.close()

    def get_duration_trend(self, test_name: str, limit: int = 20) -> list[dict]:
        """某測試的執行時間趨勢"""
        if not self._ensure_db():
            return []
        conn = self._connect()
        try:
            rows = conn.execute(
                """SELECT duration, timestamp, outcome
                   FROM results WHERE test_name = ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (test_name, limit),
            ).fetchall()
            return [
                {
                    "duration": round(r["duration"], 2) if r["duration"] else 0,
                    "date": r["timestamp"][:16] if r["timestamp"] else "",
                    "outcome": r["outcome"],
                }
                for r in reversed(rows)
            ]
        finally:
            conn.close()

    def _empty_overview(self) -> dict:
        return {
            "latest_run": None,
            "total_runs": 0,
            "total_tests": 0,
            "avg_pass_rate": 0.0,
        }


# 全域 singleton
result_service = ResultService()
