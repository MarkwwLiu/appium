"""
多裝置平行測試設定

搭配 pytest-xdist 在多台裝置上平行執行測試。
每個 worker 使用不同的 Appium port 和裝置。
"""

import json
import os
from pathlib import Path

from config.config import Config
from utils.logger import logger

# 裝置清單設定檔路徑
DEVICES_FILE = Path(__file__).resolve().parent.parent / "config" / "devices.json"


def get_device_config(worker_id: str) -> dict:
    """
    根據 pytest-xdist 的 worker_id 取得對應的裝置設定。

    Args:
        worker_id: pytest-xdist worker ID (如 "gw0", "gw1")
                   若非平行模式則為 "master"

    Returns:
        該 worker 對應的 capabilities dict
    """
    if worker_id == "master":
        return Config.load_caps()

    if not DEVICES_FILE.exists():
        logger.warning(f"找不到 {DEVICES_FILE}，使用預設 caps")
        return Config.load_caps()

    with open(DEVICES_FILE, "r", encoding="utf-8") as f:
        devices = json.load(f)

    # gw0 -> index 0, gw1 -> index 1, ...
    idx = int(worker_id.replace("gw", ""))
    if idx >= len(devices):
        raise IndexError(
            f"Worker {worker_id} 沒有對應的裝置設定 "
            f"(共 {len(devices)} 台裝置)"
        )

    device = devices[idx]
    logger.info(f"[{worker_id}] 使用裝置: {device.get('appium:deviceName', 'unknown')}")
    return device


def get_appium_port(worker_id: str, base_port: int = 4723) -> int:
    """
    根據 worker_id 計算 Appium server port。

    gw0 -> 4723, gw1 -> 4724, gw2 -> 4725 ...
    """
    if worker_id == "master":
        return base_port
    idx = int(worker_id.replace("gw", ""))
    return base_port + idx
