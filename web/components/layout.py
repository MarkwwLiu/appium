"""
共用佈局元件 — 頂部導航 + 側邊欄 + 主內容區
"""

from nicegui import app, ui


MENU_ITEMS = [
    {"label": "Dashboard", "icon": "dashboard", "path": "/"},
    {"label": "測試管理", "icon": "science", "path": "/tests"},
    {"label": "裝置管理", "icon": "devices", "path": "/devices"},
    {"label": "影片回放", "icon": "videocam", "path": "/videos"},
    {"label": "歷史趨勢", "icon": "trending_up", "path": "/history"},
    {"label": "設定", "icon": "settings", "path": "/settings"},
]


def create_layout(active_page: str = "Dashboard"):
    """建立共用佈局"""
    username = app.storage.user.get("username", "")
    role = app.storage.user.get("role", "viewer")
    role_badge = {"admin": "管理員", "member": "成員", "viewer": "觀察者"}.get(role, role)

    # ── 頂部導航列 ──
    with ui.header().classes("items-center justify-between bg-dark"):
        with ui.row().classes("items-center gap-2"):
            ui.icon("bug_report", size="md").classes("text-primary")
            ui.label("Appium 測試平台").classes("text-h6 font-bold")

        with ui.row().classes("items-center gap-4"):
            # 即時狀態指示
            running = app.storage.general.get("running_tests", {})
            if running:
                with ui.row().classes("items-center gap-1"):
                    ui.spinner("dots", size="sm", color="green")
                    ui.label(f"{len(running)} 個測試執行中").classes("text-caption")

            # 使用者資訊
            with ui.row().classes("items-center gap-2"):
                ui.icon("person", size="sm")
                ui.label(username).classes("text-subtitle2")
                ui.badge(role_badge, color="primary").classes("text-caption")
                ui.button(
                    icon="logout", on_click=lambda: ui.navigate.to("/logout")
                ).props("flat round size=sm").tooltip("登出")

    # ── 側邊欄 ──
    with ui.left_drawer(value=True).classes("bg-dark-page") as drawer:
        ui.label("功能選單").classes("text-subtitle2 text-grey q-px-md q-pt-md")
        ui.separator().classes("q-my-sm")

        for item in MENU_ITEMS:
            is_active = item["label"] == active_page
            btn_classes = "w-full justify-start"
            if is_active:
                btn_classes += " bg-primary text-white"

            ui.button(
                item["label"],
                icon=item["icon"],
                on_click=lambda path=item["path"]: ui.navigate.to(path),
            ).classes(btn_classes).props(
                f"{'color=primary' if is_active else 'flat'} align=left"
            )

        # 底部版本資訊
        ui.space()
        ui.separator()
        ui.label("v1.0.0 — 40 模組").classes("text-caption text-grey q-pa-md")


def stat_card(title: str, value: str, icon: str, color: str = "primary") -> ui.card:
    """統計卡片元件"""
    with ui.card().classes("w-full") as card:
        with ui.row().classes("items-center justify-between w-full no-wrap"):
            with ui.column().classes("gap-0"):
                ui.label(title).classes("text-caption text-grey")
                ui.label(value).classes(f"text-h5 font-bold text-{color}")
            ui.icon(icon, size="xl").classes(f"text-{color} opacity-50")
    return card
