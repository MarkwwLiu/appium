"""
Appium 測試平台 — NiceGUI Web 應用

啟動方式：
    python -m web.app
    # 或
    cd web && python app.py

    瀏覽器開啟 http://localhost:8080
"""

from __future__ import annotations

import sys
from pathlib import Path

# 確保專案根目錄在 sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nicegui import app, ui

from web.auth import AuthManager
from web.components.layout import create_layout
from web.pages.dashboard import dashboard_page
from web.pages.tests import tests_page
from web.pages.devices import devices_page
from web.pages.videos import videos_page
from web.pages.history import history_page
from web.pages.settings import settings_page

# ── 認證設定 ──
auth = AuthManager()

# ── 儲存空間初始化 ──
app.storage.general.setdefault("running_tests", {})


# ── 登入頁 ──
@ui.page("/login")
def login():
    """登入頁面"""
    ui.dark_mode(True)

    with ui.card().classes("absolute-center w-96"):
        ui.label("Appium 測試平台").classes("text-h4 text-center w-full mb-4")
        ui.label("團隊登入").classes("text-subtitle1 text-center w-full text-grey mb-6")

        username = ui.input("帳號").classes("w-full").props("outlined")
        password = ui.input("密碼", password=True, password_toggle_button=True).classes(
            "w-full"
        ).props("outlined")
        error_label = ui.label("").classes("text-negative text-center w-full")
        error_label.set_visibility(False)

        async def try_login():
            if auth.login(username.value, password.value):
                app.storage.user["authenticated"] = True
                app.storage.user["username"] = username.value
                app.storage.user["role"] = auth.get_role(username.value)
                ui.navigate.to("/")
            else:
                error_label.text = "帳號或密碼錯誤"
                error_label.set_visibility(True)

        ui.button("登入", on_click=try_login).classes("w-full mt-4").props("size=lg color=primary")

        password.on("keydown.enter", try_login)


# ── 需要登入的頁面 ──
def require_auth():
    """認證中介層"""
    if not app.storage.user.get("authenticated"):
        ui.navigate.to("/login")
        return False
    return True


@ui.page("/")
def index():
    if not require_auth():
        return
    create_layout("Dashboard")
    dashboard_page()


@ui.page("/tests")
def tests():
    if not require_auth():
        return
    create_layout("測試管理")
    tests_page()


@ui.page("/devices")
def devices():
    if not require_auth():
        return
    create_layout("裝置管理")
    devices_page()


@ui.page("/videos")
def videos():
    if not require_auth():
        return
    create_layout("影片回放")
    videos_page()


@ui.page("/history")
def history():
    if not require_auth():
        return
    create_layout("歷史趨勢")
    history_page()


@ui.page("/settings")
def page_settings():
    if not require_auth():
        return
    create_layout("設定")
    settings_page()


@ui.page("/logout")
def logout():
    app.storage.user.clear()
    ui.navigate.to("/login")


# ── 靜態檔案 ──
app.add_static_files("/videos", str(PROJECT_ROOT / "reports" / "videos"))
app.add_static_files("/screenshots", str(PROJECT_ROOT / "reports" / "screenshots"))


# ── 啟動 ──
def main():
    ui.run(
        title="Appium 測試平台",
        host="0.0.0.0",
        port=8080,
        storage_secret="appium-test-platform-secret-key",
        dark=True,
        reload=True,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
