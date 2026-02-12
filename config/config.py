"""
設定管理模組
統一管理 Appium server、裝置能力 (capabilities) 等設定。
支援透過環境變數覆蓋預設值，方便 CI/CD 整合。
支援 capabilities 結構驗證，提前發現設定錯誤。
"""

import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = Path(__file__).resolve().parent

# capabilities 必填欄位定義
_REQUIRED_CAPS = {
    "android": ["appium:deviceName", "appium:app", "platformName"],
    "ios": ["appium:deviceName", "appium:app", "platformName"],
}

# capabilities 建議欄位（缺少時發出警告）
_RECOMMENDED_CAPS = {
    "android": ["appium:automationName", "appium:appPackage", "appium:appActivity"],
    "ios": ["appium:automationName", "appium:bundleId"],
}


class ConfigValidationError(Exception):
    """Capabilities 設定驗證失敗"""

    def __init__(self, errors: list[str]):
        self.errors = errors
        msg = "Capabilities 驗證失敗:\n" + "\n".join(f"  - {e}" for e in errors)
        super().__init__(msg)


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
    def load_caps(cls, platform: str | None = None, validate: bool = True) -> dict:
        """
        從 JSON 檔載入 desired capabilities。

        Args:
            platform: 'android' 或 'ios'，預設讀取 Config.PLATFORM
            validate: 是否驗證必填欄位（預設 True）

        Returns:
            capabilities dict

        Raises:
            FileNotFoundError: 設定檔不存在
            ConfigValidationError: 必填欄位缺失
        """
        platform = platform or cls.PLATFORM
        caps_file = CONFIG_DIR / f"{platform}_caps.json"
        if not caps_file.exists():
            raise FileNotFoundError(f"找不到 capabilities 設定檔: {caps_file}")
        with open(caps_file, "r", encoding="utf-8") as f:
            caps = json.load(f)

        if validate:
            cls.validate_caps(caps, platform)

        return caps

    @classmethod
    def validate_caps(cls, caps: dict, platform: str) -> list[str]:
        """
        驗證 capabilities 結構。

        Args:
            caps: capabilities dict
            platform: 'android' 或 'ios'

        Returns:
            警告訊息列表

        Raises:
            ConfigValidationError: 必填欄位缺失時拋出
        """
        errors: list[str] = []
        warnings: list[str] = []

        required = _REQUIRED_CAPS.get(platform, [])
        for key in required:
            if key not in caps:
                errors.append(f"缺少必填欄位: {key}")

        recommended = _RECOMMENDED_CAPS.get(platform, [])
        for key in recommended:
            if key not in caps:
                warnings.append(f"建議填寫欄位: {key}")

        if errors:
            raise ConfigValidationError(errors)

        return warnings
