"""
Environment Manager — 多環境設定繼承

支援 dev / staging / prod 等多套環境，透過繼承合併設定。
不用每個環境都寫一份完整的 config，只需覆寫差異。

設定查找順序：
    1. 環境變數 (最高優先)
    2. config/env/{env_name}.json (環境專用)
    3. config/env/base.json (基底)
    4. 程式碼內建預設值

用法：
    from core.env_manager import env

    # 讀取（自動合併）
    url = env.get("appium_server")
    caps = env.get("capabilities.android")

    # 切換環境
    env.switch("staging")

    # 在測試中
    pytest --env staging
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path

from utils.logger import logger

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
_ENV_DIR = _CONFIG_DIR / "env"


def _deep_merge(base: dict, override: dict) -> dict:
    """深層合併兩個 dict，override 覆蓋 base"""
    merged = deepcopy(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


# 內建預設值
_DEFAULTS = {
    "appium_server": "http://127.0.0.1:4723",
    "platform": "android",
    "implicit_wait": 10,
    "explicit_wait": 15,
    "launch_timeout": 30,
    "screenshot_on_fail": True,
    "log_level": "INFO",
    "retry_count": 2,
    "capabilities": {
        "android": {},
        "ios": {},
    },
}


class EnvManager:
    """
    多環境設定管理

    合併順序: 預設值 → base.json → {env}.json → 環境變數覆蓋
    """

    def __init__(self):
        self._env_name: str = os.getenv("TEST_ENV", "dev")
        self._config: dict = {}
        self._loaded = False

    @property
    def env_name(self) -> str:
        return self._env_name

    def switch(self, env_name: str) -> None:
        """切換環境並重新載入"""
        logger.info(f"切換環境: {self._env_name} → {env_name}")
        self._env_name = env_name
        self._loaded = False
        self._load()

    def get(self, key: str, default=None):
        """
        取得設定值，支援 dot notation。

        範例:
            env.get("appium_server")           → "http://..."
            env.get("capabilities.android")    → {...}
            env.get("capabilities.android.deviceName")
        """
        self._ensure_loaded()

        # 先檢查環境變數覆蓋 (用底線替代 dot)
        env_key = key.upper().replace(".", "_")
        env_val = os.getenv(env_key)
        if env_val is not None:
            return self._cast(env_val)

        # 走 dot notation
        parts = key.split(".")
        value = self._config
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        return value

    def get_all(self) -> dict:
        """取得完整合併後的設定"""
        self._ensure_loaded()
        return deepcopy(self._config)

    def set(self, key: str, value) -> None:
        """動態設定值（runtime only，不寫檔）"""
        self._ensure_loaded()
        parts = key.split(".")
        target = self._config
        for part in parts[:-1]:
            target = target.setdefault(part, {})
        target[parts[-1]] = value

    def create_env_files(self) -> None:
        """
        產生環境設定檔範本（首次使用時呼叫）。

        產生：
            config/env/base.json
            config/env/dev.json
            config/env/staging.json
            config/env/prod.json
        """
        _ENV_DIR.mkdir(parents=True, exist_ok=True)

        templates = {
            "base": {
                "_comment": "基底設定，所有環境共用",
                "appium_server": "http://127.0.0.1:4723",
                "platform": "android",
                "implicit_wait": 10,
                "explicit_wait": 15,
                "screenshot_on_fail": True,
                "retry_count": 2,
            },
            "dev": {
                "_comment": "開發環境 (覆蓋 base)",
                "log_level": "DEBUG",
            },
            "staging": {
                "_comment": "Staging 環境",
                "appium_server": "http://staging-appium:4723",
                "log_level": "INFO",
                "retry_count": 3,
            },
            "prod": {
                "_comment": "生產環境 (通常不跑自動化)",
                "appium_server": "http://prod-appium:4723",
                "log_level": "WARNING",
                "screenshot_on_fail": True,
            },
        }

        for name, content in templates.items():
            path = _ENV_DIR / f"{name}.json"
            if not path.exists():
                path.write_text(
                    json.dumps(content, indent=4, ensure_ascii=False),
                    encoding="utf-8",
                )
                logger.info(f"已建立環境設定: {path}")

    # ── 內部方法 ──

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self._load()

    def _load(self) -> None:
        """載入並合併設定"""
        config = deepcopy(_DEFAULTS)

        # 合併 base.json
        base_file = _ENV_DIR / "base.json"
        if base_file.exists():
            base = self._read_json(base_file)
            config = _deep_merge(config, base)

        # 合併 {env}.json
        env_file = _ENV_DIR / f"{self._env_name}.json"
        if env_file.exists():
            env_config = self._read_json(env_file)
            config = _deep_merge(config, env_config)

        self._config = config
        self._loaded = True
        logger.debug(f"環境設定已載入: {self._env_name}")

    @staticmethod
    def _read_json(path: Path) -> dict:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        # 移除 _comment 欄位
        return {k: v for k, v in data.items() if not k.startswith("_")}

    @staticmethod
    def _cast(value: str):
        """嘗試將環境變數字串轉為適當型別"""
        if value.lower() in ("true", "1", "yes"):
            return True
        if value.lower() in ("false", "0", "no"):
            return False
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        return value


# 全域 singleton
env = EnvManager()
