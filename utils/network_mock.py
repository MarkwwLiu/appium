"""
Network Mock — API 攔截與模擬回應

在測試中攔截 HTTP 請求，回傳自訂回應，不依賴真實後端。
支援 URL 匹配、狀態碼模擬、延遲注入、回應覆寫。

用法：
    def test_error_handling(self, driver, network_mock):
        network_mock.mock("/api/login", status=500, body={"error": "伺服器錯誤"})
        network_mock.mock("/api/users", delay=10.0)  # 模擬逾時
        network_mock.mock("/api/data", body=[])       # 空資料
        # ... 操作 App，觸發 API 呼叫 ...
        network_mock.clear()
"""

from __future__ import annotations

import json
import re
import socket
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import urlparse

from utils.logger import logger


@dataclass
class MockRule:
    """單一 mock 規則"""
    url_pattern: str           # URL 匹配 (支援正則)
    method: str = "*"          # HTTP method (* = 全部)
    status: int = 200          # 回傳狀態碼
    body: Any = None           # 回傳 body (dict/list → JSON, str → 原樣)
    headers: dict = field(default_factory=dict)
    delay: float = 0.0         # 回應延遲 (秒)
    passthrough: bool = False  # True = 轉發到真實後端
    _compiled: re.Pattern | None = field(default=None, repr=False)

    def __post_init__(self):
        self._compiled = re.compile(self.url_pattern)

    def matches(self, path: str, method: str = "GET") -> bool:
        """檢查是否匹配此規則"""
        if self.method != "*" and self.method.upper() != method.upper():
            return False
        return bool(self._compiled.search(path))


class NetworkMock:
    """
    HTTP Mock 伺服器

    在本地啟動一個輕量 HTTP server，透過 Appium 設定 proxy
    或直接修改 App 的 API base URL 來攔截請求。
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 0):
        self._host = host
        self._port = port
        self._rules: list[MockRule] = []
        self._history: list[dict] = []
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    # ── 公開 API ──

    def mock(
        self,
        url_pattern: str,
        *,
        method: str = "*",
        status: int = 200,
        body: Any = None,
        headers: dict | None = None,
        delay: float = 0.0,
    ) -> "NetworkMock":
        """
        新增 mock 規則

        Args:
            url_pattern: URL 路徑匹配 (支援正則, 例如 "/api/users.*")
            method: HTTP method 篩選 (* = 全部)
            status: 回傳的 HTTP 狀態碼
            body: 回傳內容 (dict/list 自動轉 JSON)
            headers: 額外回應 header
            delay: 回應前等待秒數 (模擬慢回應/逾時)
        """
        rule = MockRule(
            url_pattern=url_pattern,
            method=method,
            status=status,
            body=body,
            headers=headers or {},
            delay=delay,
        )
        with self._lock:
            self._rules.append(rule)
        logger.debug(f"[NetworkMock] 新增規則: {method} {url_pattern} → {status}")
        return self

    def mock_error(self, url_pattern: str, status: int = 500, **kwargs) -> "NetworkMock":
        """快捷：模擬錯誤回應"""
        body = kwargs.pop("body", {"error": f"模擬錯誤 {status}"})
        return self.mock(url_pattern, status=status, body=body, **kwargs)

    def mock_timeout(self, url_pattern: str, delay: float = 30.0, **kwargs) -> "NetworkMock":
        """快捷：模擬逾時"""
        return self.mock(url_pattern, delay=delay, status=408, **kwargs)

    def mock_empty(self, url_pattern: str, **kwargs) -> "NetworkMock":
        """快捷：模擬空資料"""
        return self.mock(url_pattern, body=[], **kwargs)

    def clear(self) -> None:
        """清除所有 mock 規則"""
        with self._lock:
            self._rules.clear()
        logger.debug("[NetworkMock] 清除所有規則")

    def remove(self, url_pattern: str) -> None:
        """移除指定 URL 的 mock 規則"""
        with self._lock:
            self._rules = [r for r in self._rules if r.url_pattern != url_pattern]

    @property
    def history(self) -> list[dict]:
        """取得所有被攔截的請求記錄"""
        return list(self._history)

    @property
    def url(self) -> str:
        """取得 mock server 的 base URL"""
        if self._server:
            return f"http://{self._get_local_ip()}:{self._server.server_address[1]}"
        return ""

    @property
    def port(self) -> int:
        """取得 mock server 的 port"""
        if self._server:
            return self._server.server_address[1]
        return 0

    # ── 生命週期 ──

    def start(self) -> str:
        """啟動 mock server，回傳 base URL"""
        if self._server:
            return self.url

        mock_ref = self

        class _Handler(BaseHTTPRequestHandler):
            """處理所有 HTTP 請求"""

            def do_GET(self):
                self._handle()

            def do_POST(self):
                self._handle()

            def do_PUT(self):
                self._handle()

            def do_DELETE(self):
                self._handle()

            def do_PATCH(self):
                self._handle()

            def log_message(self, format, *args):
                pass  # 靜音 HTTP server log

            def _handle(self):
                # 讀取請求 body
                content_len = int(self.headers.get("Content-Length", 0))
                req_body = self.rfile.read(content_len) if content_len > 0 else b""

                # 記錄請求
                record = {
                    "method": self.command,
                    "path": self.path,
                    "headers": dict(self.headers),
                    "body": req_body.decode("utf-8", errors="replace"),
                    "timestamp": time.time(),
                }
                mock_ref._history.append(record)

                # 尋找匹配規則 (後加的優先)
                matched_rule = None
                with mock_ref._lock:
                    for rule in reversed(mock_ref._rules):
                        if rule.matches(self.path, self.command):
                            matched_rule = rule
                            break

                if matched_rule:
                    # 模擬延遲
                    if matched_rule.delay > 0:
                        time.sleep(matched_rule.delay)

                    # 組裝回應
                    self.send_response(matched_rule.status)

                    # 預設 headers
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    for k, v in matched_rule.headers.items():
                        self.send_header(k, v)
                    self.end_headers()

                    # 回傳 body
                    if matched_rule.body is not None:
                        if isinstance(matched_rule.body, (dict, list)):
                            resp = json.dumps(matched_rule.body, ensure_ascii=False)
                        else:
                            resp = str(matched_rule.body)
                        self.wfile.write(resp.encode("utf-8"))
                else:
                    # 無匹配：回傳 404
                    self.send_response(404)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    resp = json.dumps({"error": "未匹配任何 mock 規則", "path": self.path})
                    self.wfile.write(resp.encode("utf-8"))

        self._server = HTTPServer((self._host, self._port), _Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

        actual_port = self._server.server_address[1]
        logger.info(f"[NetworkMock] 啟動於 port {actual_port}")
        return self.url

    def stop(self) -> None:
        """停止 mock server"""
        if self._server:
            self._server.shutdown()
            self._server = None
            self._thread = None
            logger.info("[NetworkMock] 已停止")

    def _get_local_ip(self) -> str:
        """取得本機 IP (讓模擬器可存取)"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except OSError:
            return "127.0.0.1"

    # ── 斷言 helpers ──

    def assert_called(self, url_pattern: str, method: str = "*", times: int | None = None) -> None:
        """斷言某 URL 被呼叫過"""
        pattern = re.compile(url_pattern)
        matched = [
            r for r in self._history
            if pattern.search(r["path"])
            and (method == "*" or r["method"].upper() == method.upper())
        ]
        if times is not None:
            assert len(matched) == times, (
                f"預期 {url_pattern} 被呼叫 {times} 次，實際 {len(matched)} 次"
            )
        else:
            assert len(matched) > 0, f"預期 {url_pattern} 被呼叫，但從未被呼叫"

    def assert_not_called(self, url_pattern: str) -> None:
        """斷言某 URL 沒有被呼叫"""
        pattern = re.compile(url_pattern)
        matched = [r for r in self._history if pattern.search(r["path"])]
        assert len(matched) == 0, f"預期 {url_pattern} 未被呼叫，但被呼叫了 {len(matched)} 次"

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
