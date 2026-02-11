"""
設定管理模組
統一管理 Appium server、裝置能力 (capabilities) 等設定。
支援透過環境變數覆蓋預設值，方便 CI/CD 整合。
"""

import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = Path(__file__).resolve().parent


class Config:
    """框架全域設定"""

    # Appium Server
    APPIUM_HOST = os.getenv("APPIUM_HOST", "127.0.0.1")
    APPIUM_PORT = int(os.getenv("APPIUM_PORT", "4723"))

    # 超時設定 (秒)
    IMPLICIT_WAIT = int(os.getenv("IMPLICIT_WAIT", "10"))
    EXPLICIT_WAIT = int(os.getenv("EXPLICIT_WAIT", "15"))
    LAUNCH_TIMEOUT = int(os.getenv("LAUNCH_TIMEOUT", "30"))

    # 截圖與報告
    SCREENSHOT_DIR = BASE_DIR / "screenshots"
    REPORT_DIR = BASE_DIR / "reports"

    # 平台
    PLATFORM = os.getenv("PLATFORM", "android").lower()

    @classmethod
    def appium_server_url(cls) -> str:
        return f"http://{cls.APPIUM_HOST}:{cls.APPIUM_PORT}"

    @classmethod
    def load_caps(cls, platform: str | None = None) -> dict:
        """
        從 JSON 檔載入 desired capabilities。
        可透過 platform 參數指定 'android' 或 'ios'。
        """
        platform = platform or cls.PLATFORM
        caps_file = CONFIG_DIR / f"{platform}_caps.json"
        if not caps_file.exists():
            raise FileNotFoundError(f"找不到 capabilities 設定檔: {caps_file}")
        with open(caps_file, "r", encoding="utf-8") as f:
            return json.load(f)
