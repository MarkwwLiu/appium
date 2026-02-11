"""
Fail Handler Plugin — 測試失敗時的進階處理

失敗時自動：
1. 截圖
2. 保存 page source (XML)
3. 收集裝置資訊
4. (可選) 推送通知

可取代 conftest 中的簡單截圖邏輯，提供更完整的現場保全。
"""

import json
from datetime import datetime
from pathlib import Path

from config.config import Config
from core.plugin_manager import Plugin
from utils.logger import logger

FAIL_DIR = Config.REPORT_DIR / "failures"


class FailHandlerPlugin(Plugin):
    """測試失敗時自動收集完整現場資訊"""

    name = "fail_handler"
    version = "1.0.0"
    description = "測試失敗時自動截圖 + 保存 page source + 裝置資訊"

    def on_register(self) -> None:
        FAIL_DIR.mkdir(parents=True, exist_ok=True)

    def on_test_fail(self, test_name: str, driver, error: Exception) -> None:
        """測試失敗時收集現場"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = test_name.replace("/", "_").replace(":", "_")
        prefix = f"{safe_name}_{ts}"

        fail_data = {
            "test_name": test_name,
            "error": str(error),
            "error_type": type(error).__name__,
            "timestamp": ts,
        }

        # 1. 截圖
        try:
            ss_path = FAIL_DIR / f"{prefix}_screenshot.png"
            driver.save_screenshot(str(ss_path))
            fail_data["screenshot"] = str(ss_path)
            logger.info(f"[FailHandler] 截圖: {ss_path}")
        except Exception as e:
            logger.error(f"[FailHandler] 截圖失敗: {e}")

        # 2. Page source
        try:
            xml_path = FAIL_DIR / f"{prefix}_page.xml"
            xml_path.write_text(driver.page_source, encoding="utf-8")
            fail_data["page_source"] = str(xml_path)
        except Exception as e:
            logger.error(f"[FailHandler] Page source 失敗: {e}")

        # 3. 裝置資訊
        try:
            caps = driver.capabilities
            fail_data["device"] = {
                "platform": caps.get("platformName", ""),
                "device_name": caps.get("deviceName", ""),
                "os_version": caps.get("platformVersion", ""),
                "app": caps.get("appPackage", caps.get("bundleId", "")),
            }
        except Exception:
            pass

        # 4. 儲存 JSON 摘要
        try:
            json_path = FAIL_DIR / f"{prefix}_info.json"
            json_path.write_text(
                json.dumps(fail_data, indent=4, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

        logger.error(
            f"[FailHandler] 現場已保全: {FAIL_DIR / prefix}*"
        )
