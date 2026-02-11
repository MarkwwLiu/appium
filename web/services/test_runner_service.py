"""
測試執行服務

在背景執行 pytest，透過 WebSocket 即時回報狀態。
"""

from __future__ import annotations

import asyncio
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from nicegui import app

from utils.logger import logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class TestJob:
    """一個測試執行工作"""
    job_id: str
    tests: list[str]
    platform: str = "android"
    env: str = "dev"
    status: str = "pending"       # pending / running / completed / failed
    start_time: float = 0.0
    end_time: float = 0.0
    output: str = ""
    triggered_by: str = ""
    process: subprocess.Popen | None = field(default=None, repr=False)


class TestRunnerService:
    """測試執行服務"""

    def __init__(self):
        self._jobs: dict[str, TestJob] = {}
        self._listeners: list[Callable] = []

    def create_job(
        self,
        tests: list[str] | None = None,
        platform: str = "android",
        env: str = "dev",
        triggered_by: str = "",
        extra_args: list[str] | None = None,
    ) -> str:
        """建立測試工作"""
        job_id = f"job_{int(time.time())}_{uuid.uuid4().hex[:4]}"
        job = TestJob(
            job_id=job_id,
            tests=tests or [],
            platform=platform,
            env=env,
            triggered_by=triggered_by,
        )
        self._jobs[job_id] = job
        return job_id

    async def run_job(self, job_id: str) -> None:
        """非同步執行測試工作"""
        job = self._jobs.get(job_id)
        if not job:
            return

        job.status = "running"
        job.start_time = time.time()
        app.storage.general.setdefault("running_tests", {})[job_id] = {
            "status": "running",
            "triggered_by": job.triggered_by,
        }

        # 組裝 pytest 命令
        cmd = [
            "python", "-m", "pytest",
            f"--platform={job.platform}",
            f"--env={job.env}",
            "-v",
            "--tb=short",
        ]

        if job.tests:
            cmd.extend(job.tests)
        else:
            cmd.append("tests/")

        logger.info(f"[TestRunner] 啟動: {' '.join(cmd)}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(PROJECT_ROOT),
            )

            output_lines = []
            async for line in process.stdout:
                text = line.decode("utf-8", errors="replace")
                output_lines.append(text)
                # 通知所有監聽者
                self._notify(job_id, text)

            await process.wait()

            job.output = "".join(output_lines)
            job.status = "completed" if process.returncode == 0 else "failed"
        except Exception as e:
            job.output = str(e)
            job.status = "failed"
            logger.error(f"[TestRunner] 執行失敗: {e}")
        finally:
            job.end_time = time.time()
            running = app.storage.general.get("running_tests", {})
            running.pop(job_id, None)
            app.storage.general["running_tests"] = running
            self._notify(job_id, f"\n=== 完成: {job.status} ===\n")

    def get_job(self, job_id: str) -> TestJob | None:
        """取得工作資訊"""
        return self._jobs.get(job_id)

    def get_recent_jobs(self, limit: int = 20) -> list[TestJob]:
        """取得最近的工作"""
        jobs = sorted(self._jobs.values(), key=lambda j: j.start_time, reverse=True)
        return jobs[:limit]

    def add_listener(self, callback: Callable) -> None:
        """新增即時輸出監聽"""
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable) -> None:
        """移除監聽"""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify(self, job_id: str, line: str) -> None:
        """通知所有監聽者"""
        for listener in self._listeners:
            try:
                listener(job_id, line)
            except Exception:
                pass

    def discover_tests(self) -> list[dict]:
        """掃描可用的測試檔案"""
        tests_dir = PROJECT_ROOT / "tests"
        if not tests_dir.exists():
            return []

        discovered = []
        for f in sorted(tests_dir.rglob("test_*.py")):
            rel = f.relative_to(PROJECT_ROOT)
            discovered.append({
                "file": str(rel),
                "name": f.stem,
                "module": str(rel).replace("/", ".").replace(".py", ""),
            })
        return discovered


# 全域 singleton
test_runner = TestRunnerService()
