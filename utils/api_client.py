"""
API Client 工具
用於 API + UI 混合測試：透過 API 建立測試前置資料，再用 UI 驗證。
"""

import requests

from config.config import Config
from utils.logger import logger


class ApiClient:
    """簡易 REST API 客戶端"""

    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def set_token(self, token: str) -> None:
        """設定 Bearer Token"""
        self.session.headers["Authorization"] = f"Bearer {token}"

    def get(self, path: str, params: dict | None = None) -> requests.Response:
        url = f"{self.base_url}/{path.lstrip('/')}"
        logger.info(f"[API] GET {url}")
        resp = self.session.get(url, params=params, timeout=self.timeout)
        logger.info(f"[API] Status: {resp.status_code}")
        return resp

    def post(self, path: str, json_data: dict | None = None) -> requests.Response:
        url = f"{self.base_url}/{path.lstrip('/')}"
        logger.info(f"[API] POST {url}")
        resp = self.session.post(url, json=json_data, timeout=self.timeout)
        logger.info(f"[API] Status: {resp.status_code}")
        return resp

    def put(self, path: str, json_data: dict | None = None) -> requests.Response:
        url = f"{self.base_url}/{path.lstrip('/')}"
        logger.info(f"[API] PUT {url}")
        resp = self.session.put(url, json=json_data, timeout=self.timeout)
        logger.info(f"[API] Status: {resp.status_code}")
        return resp

    def delete(self, path: str) -> requests.Response:
        url = f"{self.base_url}/{path.lstrip('/')}"
        logger.info(f"[API] DELETE {url}")
        resp = self.session.delete(url, timeout=self.timeout)
        logger.info(f"[API] Status: {resp.status_code}")
        return resp
