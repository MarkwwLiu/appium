"""
App 生命週期管理
安裝/移除/重啟 App、前背景切換、Deep Link 跳轉等。
"""

import subprocess

from utils.logger import logger


class AppManager:
    """管理 App 的安裝、啟動、前背景切換"""

    def __init__(self, driver):
        self.driver = driver

    # ── App 控制 ──

    def install_app(self, app_path: str) -> None:
        """安裝 App"""
        logger.info(f"安裝 App: {app_path}")
        self.driver.install_app(app_path)

    def remove_app(self, bundle_id: str) -> None:
        """移除 App"""
        logger.info(f"移除 App: {bundle_id}")
        self.driver.remove_app(bundle_id)

    def is_app_installed(self, bundle_id: str) -> bool:
        """檢查 App 是否已安裝"""
        return self.driver.is_app_installed(bundle_id)

    def launch_app(self, bundle_id: str) -> None:
        """啟動 App"""
        logger.info(f"啟動 App: {bundle_id}")
        self.driver.activate_app(bundle_id)

    def terminate_app(self, bundle_id: str) -> None:
        """強制結束 App"""
        logger.info(f"結束 App: {bundle_id}")
        self.driver.terminate_app(bundle_id)

    def reset_app(self, bundle_id: str) -> None:
        """結束並重新啟動 App（模擬重啟）"""
        logger.info(f"重啟 App: {bundle_id}")
        self.terminate_app(bundle_id)
        self.launch_app(bundle_id)

    # ── 前背景 ──

    def background_app(self, seconds: int = 3) -> None:
        """
        將 App 放到背景指定秒數後自動回到前景。
        用於測試 App 從背景回復的行為。
        """
        logger.info(f"App 進入背景 {seconds} 秒")
        self.driver.background_app(seconds)

    def put_to_background(self) -> None:
        """將 App 放到背景（不自動回復）"""
        logger.info("App 進入背景")
        self.driver.background_app(-1)

    # ── Deep Link ──

    def open_deep_link(self, url: str, bundle_id: str | None = None) -> None:
        """
        透過 Deep Link 開啟 App 特定頁面。

        Args:
            url: deep link URL，如 "myapp://product/123"
            bundle_id: iOS 需要指定 bundle ID
        """
        logger.info(f"開啟 Deep Link: {url}")
        if bundle_id:
            self.driver.execute_script("mobile: deepLink", {
                "url": url,
                "package": bundle_id,
            })
        else:
            self.driver.get(url)

    # ── App 狀態 ──

    def get_app_state(self, bundle_id: str) -> int:
        """
        取得 App 狀態。

        Returns:
            0: 未安裝
            1: 未執行
            2: 背景執行（暫停）
            3: 背景執行中
            4: 前景執行中
        """
        state = self.driver.query_app_state(bundle_id)
        state_map = {
            0: "未安裝",
            1: "未執行",
            2: "背景(暫停)",
            3: "背景(執行)",
            4: "前景執行",
        }
        logger.info(f"App 狀態: {state_map.get(state, '未知')} ({state})")
        return state

    def clear_app_data(self, bundle_id: str) -> None:
        """清除 App 資料（僅 Android）"""
        logger.info(f"清除 App 資料: {bundle_id}")
        subprocess.run(
            ["adb", "shell", "pm", "clear", bundle_id],
            capture_output=True,
            text=True,
        )
