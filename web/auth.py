"""
認證管理

簡單的團隊帳號管理，使用 JSON 檔案儲存。
支援角色：admin / member / viewer
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from utils.logger import logger

USERS_FILE = Path(__file__).parent / "users.json"

# 預設帳號
DEFAULT_USERS = {
    "admin": {
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "role": "admin",
        "display_name": "管理員",
    },
    "tester": {
        "password_hash": hashlib.sha256("test123".encode()).hexdigest(),
        "role": "member",
        "display_name": "測試工程師",
    },
}


class AuthManager:
    """認證管理器"""

    def __init__(self):
        self._users = self._load_users()

    def login(self, username: str, password: str) -> bool:
        """驗證帳號密碼"""
        user = self._users.get(username)
        if not user:
            return False
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        return user["password_hash"] == pw_hash

    def get_role(self, username: str) -> str:
        """取得使用者角色"""
        user = self._users.get(username)
        return user["role"] if user else "viewer"

    def get_display_name(self, username: str) -> str:
        """取得顯示名稱"""
        user = self._users.get(username)
        return user.get("display_name", username) if user else username

    def add_user(
        self, username: str, password: str, role: str = "member", display_name: str = ""
    ) -> bool:
        """新增使用者"""
        if username in self._users:
            return False
        self._users[username] = {
            "password_hash": hashlib.sha256(password.encode()).hexdigest(),
            "role": role,
            "display_name": display_name or username,
        }
        self._save_users()
        return True

    def remove_user(self, username: str) -> bool:
        """移除使用者"""
        if username not in self._users or username == "admin":
            return False
        del self._users[username]
        self._save_users()
        return True

    def list_users(self) -> list[dict]:
        """列出所有使用者"""
        return [
            {"username": k, "role": v["role"], "display_name": v.get("display_name", k)}
            for k, v in self._users.items()
        ]

    def change_password(self, username: str, new_password: str) -> bool:
        """修改密碼"""
        if username not in self._users:
            return False
        self._users[username]["password_hash"] = hashlib.sha256(
            new_password.encode()
        ).hexdigest()
        self._save_users()
        return True

    def _load_users(self) -> dict:
        """載入使用者資料"""
        if USERS_FILE.exists():
            try:
                return json.loads(USERS_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        # 建立預設使用者檔案
        self._users = DEFAULT_USERS.copy()
        self._save_users()
        return self._users

    def _save_users(self) -> None:
        """儲存使用者資料"""
        USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        USERS_FILE.write_text(
            json.dumps(self._users, ensure_ascii=False, indent=2), encoding="utf-8"
        )
