"""
Test Result DB — SQLite 測試結果儲存

每次跑完測試自動存入 SQLite，提供：
- 歷史查詢（某個測試最近 N 次結果）
- 回歸比對（這次 vs 上次）
- 趨勢分析（通過率趨勢、耗時趨勢）
- Flaky test 偵測（時過時不過的測試）

用法：
    from core.result_db import result_db

    # 自動模式（conftest 已整合）
    # 測試結束後自動寫入

    # 手動查詢
    result_db.get_history("test_login::test_positive", limit=10)
    result_db.get_flaky_tests(window=20)
    result_db.compare_runs(run_id_a, run_id_b)
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from config.config import Config
from utils.logger import logger

DB_PATH = Config.REPORT_DIR / "test_results.db"


class ResultDB:
    """SQLite 測試結果儲存"""

    def __init__(self, db_path: Path | str | None = None):
        self._db_path = str(db_path or DB_PATH)
        self._local = threading.local()
        self._init_db()

    @property
    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
            self._local.conn = sqlite3.connect(self._db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self):
        conn = self._conn
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                start_time TEXT,
                end_time TEXT,
                platform TEXT,
                env TEXT,
                total INTEGER DEFAULT 0,
                passed INTEGER DEFAULT 0,
                failed INTEGER DEFAULT 0,
                skipped INTEGER DEFAULT 0,
                duration REAL DEFAULT 0,
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                test_name TEXT,
                outcome TEXT,
                duration REAL,
                error_message TEXT DEFAULT '',
                timestamp TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            );

            CREATE INDEX IF NOT EXISTS idx_results_test ON results(test_name);
            CREATE INDEX IF NOT EXISTS idx_results_run ON results(run_id);
        """)
        conn.commit()

    # ── Run 管理 ──

    def start_run(self, platform: str = "", env: str = "") -> str:
        """建立新的 test run，回傳 run_id"""
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6]
        self._conn.execute(
            "INSERT INTO runs (run_id, start_time, platform, env) VALUES (?, ?, ?, ?)",
            (run_id, datetime.now().isoformat(), platform, env),
        )
        self._conn.commit()
        logger.debug(f"[ResultDB] 新 run: {run_id}")
        return run_id

    def end_run(self, run_id: str) -> None:
        """結束 run，更新統計"""
        cursor = self._conn.execute(
            "SELECT outcome, duration FROM results WHERE run_id = ?", (run_id,)
        )
        rows = cursor.fetchall()
        total = len(rows)
        passed = sum(1 for r in rows if r["outcome"] == "passed")
        failed = sum(1 for r in rows if r["outcome"] == "failed")
        skipped = sum(1 for r in rows if r["outcome"] == "skipped")
        duration = sum(r["duration"] for r in rows)

        self._conn.execute(
            """UPDATE runs SET end_time=?, total=?, passed=?, failed=?,
               skipped=?, duration=? WHERE run_id=?""",
            (datetime.now().isoformat(), total, passed, failed, skipped, duration, run_id),
        )
        self._conn.commit()
        logger.debug(
            f"[ResultDB] run 結束: {run_id} "
            f"({passed}/{total} passed, {duration:.1f}s)"
        )

    # ── 結果寫入 ──

    def record(self, run_id: str, test_name: str, outcome: str,
               duration: float, error_message: str = "") -> None:
        """寫入單筆結果"""
        self._conn.execute(
            """INSERT INTO results (run_id, test_name, outcome, duration,
               error_message, timestamp) VALUES (?, ?, ?, ?, ?, ?)""",
            (run_id, test_name, outcome, duration, error_message,
             datetime.now().isoformat()),
        )
        self._conn.commit()

    # ── 查詢 ──

    def get_history(self, test_name: str, limit: int = 10) -> list[dict]:
        """查詢某測試的歷史結果"""
        cursor = self._conn.execute(
            """SELECT r.run_id, r.outcome, r.duration, r.error_message, r.timestamp
               FROM results r
               WHERE r.test_name = ?
               ORDER BY r.timestamp DESC LIMIT ?""",
            (test_name, limit),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_run_summary(self, run_id: str) -> dict | None:
        """取得單次 run 的摘要"""
        cursor = self._conn.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_recent_runs(self, limit: int = 10) -> list[dict]:
        """取得最近 N 次 run"""
        cursor = self._conn.execute(
            "SELECT * FROM runs ORDER BY start_time DESC LIMIT ?", (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def compare_runs(self, run_a: str, run_b: str) -> dict:
        """
        比較兩次 run 的差異。

        Returns:
            {
                "new_failures": [...],     # run_b 新增的失敗
                "fixed": [...],            # run_a 失敗但 run_b 通過
                "still_failing": [...],    # 兩次都失敗
                "new_tests": [...],        # run_b 新增的測試
                "removed_tests": [...],    # run_a 有但 run_b 沒有
            }
        """
        results_a = {
            r["test_name"]: r["outcome"]
            for r in self._get_run_results(run_a)
        }
        results_b = {
            r["test_name"]: r["outcome"]
            for r in self._get_run_results(run_b)
        }

        tests_a = set(results_a.keys())
        tests_b = set(results_b.keys())

        new_failures = [
            t for t in tests_b
            if results_b[t] == "failed" and results_a.get(t) != "failed"
        ]
        fixed = [
            t for t in tests_a & tests_b
            if results_a[t] == "failed" and results_b[t] == "passed"
        ]
        still_failing = [
            t for t in tests_a & tests_b
            if results_a[t] == "failed" and results_b[t] == "failed"
        ]

        return {
            "new_failures": new_failures,
            "fixed": fixed,
            "still_failing": still_failing,
            "new_tests": list(tests_b - tests_a),
            "removed_tests": list(tests_a - tests_b),
        }

    def get_flaky_tests(self, window: int = 20) -> list[dict]:
        """
        偵測 flaky tests（最近 N 次結果中時過時不過）。

        Returns:
            [{"test_name": ..., "pass_rate": 0.6, "total": 20, ...}]
        """
        cursor = self._conn.execute(
            """SELECT test_name, outcome
               FROM results
               ORDER BY timestamp DESC""",
        )
        # 按 test_name 分組，取最近 window 筆
        from collections import defaultdict
        groups: dict[str, list[str]] = defaultdict(list)
        for row in cursor.fetchall():
            name = row["test_name"]
            if len(groups[name]) < window:
                groups[name].append(row["outcome"])

        flaky = []
        for name, outcomes in groups.items():
            if len(outcomes) < 3:
                continue
            passed = outcomes.count("passed")
            total = len(outcomes)
            rate = passed / total
            # 不是全過也不是全敗 → flaky
            if 0 < rate < 1:
                flaky.append({
                    "test_name": name,
                    "pass_rate": round(rate, 2),
                    "total": total,
                    "passed": passed,
                    "failed": outcomes.count("failed"),
                })

        flaky.sort(key=lambda x: x["pass_rate"])
        return flaky

    def get_pass_rate_trend(self, limit: int = 20) -> list[dict]:
        """取得通過率趨勢"""
        runs = self.get_recent_runs(limit)
        runs.reverse()  # 時間正序
        return [
            {
                "run_id": r["run_id"],
                "date": r["start_time"][:10],
                "total": r["total"],
                "passed": r["passed"],
                "pass_rate": round(r["passed"] / r["total"], 2) if r["total"] > 0 else 0,
                "duration": r["duration"],
            }
            for r in runs
            if r["total"] > 0
        ]

    def _get_run_results(self, run_id: str) -> list[dict]:
        cursor = self._conn.execute(
            "SELECT test_name, outcome, duration FROM results WHERE run_id = ?",
            (run_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


# 全域 singleton
result_db = ResultDB()
