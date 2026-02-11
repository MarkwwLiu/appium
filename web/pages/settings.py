"""
設定頁面

功能：
- 使用者管理 (admin only)
- 修改密碼
- 框架模組狀態
"""

from nicegui import app, ui

from web.auth import AuthManager

auth = AuthManager()


def settings_page():
    """設定頁面主體"""
    username = app.storage.user.get("username", "")
    role = app.storage.user.get("role", "viewer")

    with ui.tabs().classes("w-full") as tabs:
        tab_profile = ui.tab("profile", label="個人設定", icon="person")
        tab_modules = ui.tab("modules", label="框架模組", icon="extension")
        if role == "admin":
            tab_users = ui.tab("users", label="使用者管理", icon="group")

    with ui.tab_panels(tabs, value="profile").classes("w-full"):
        with ui.tab_panel("profile"):
            _profile_panel(username)

        with ui.tab_panel("modules"):
            _modules_panel()

        if role == "admin":
            with ui.tab_panel("users"):
                _users_panel()


def _profile_panel(username: str):
    """個人設定面板"""
    with ui.card().classes("w-full max-w-lg"):
        ui.label("修改密碼").classes("text-h6 q-mb-md")

        old_pw = ui.input("目前密碼", password=True, password_toggle_button=True).classes("w-full").props("outlined")
        new_pw = ui.input("新密碼", password=True, password_toggle_button=True).classes("w-full").props("outlined")
        confirm_pw = ui.input("確認新密碼", password=True, password_toggle_button=True).classes("w-full").props("outlined")

        def change_password():
            if not auth.login(username, old_pw.value):
                ui.notify("目前密碼錯誤", type="negative")
                return
            if new_pw.value != confirm_pw.value:
                ui.notify("新密碼不一致", type="negative")
                return
            if len(new_pw.value) < 4:
                ui.notify("密碼至少 4 個字元", type="negative")
                return
            auth.change_password(username, new_pw.value)
            ui.notify("密碼已更新", type="positive")
            old_pw.value = ""
            new_pw.value = ""
            confirm_pw.value = ""

        ui.button("更新密碼", icon="lock", on_click=change_password).props("color=primary").classes("q-mt-md")


def _modules_panel():
    """框架模組狀態"""
    modules = [
        # Core
        {"name": "BasePage", "category": "Core", "status": "active"},
        {"name": "DriverManager", "category": "Core", "status": "active"},
        {"name": "Assertions", "category": "Core", "status": "active"},
        {"name": "PageValidator", "category": "Core", "status": "active"},
        {"name": "SelfHealer", "category": "Core", "status": "active"},
        {"name": "Component", "category": "Core", "status": "active"},
        {"name": "EventBus", "category": "Core", "status": "active"},
        {"name": "Middleware", "category": "Core", "status": "active"},
        {"name": "PluginManager", "category": "Core", "status": "active"},
        {"name": "RecoveryManager", "category": "Core", "status": "active"},
        {"name": "ResultDB", "category": "Core", "status": "active"},
        {"name": "EnvManager", "category": "Core", "status": "active"},
        {"name": "ElementCache", "category": "Core", "status": "active"},
        {"name": "Exceptions", "category": "Core", "status": "active"},
        # Utils
        {"name": "Screenshot", "category": "Utils", "status": "active"},
        {"name": "Logger", "category": "Utils", "status": "active"},
        {"name": "ApiClient", "category": "Utils", "status": "active"},
        {"name": "GestureHelper", "category": "Utils", "status": "active"},
        {"name": "AppManager", "category": "Utils", "status": "active"},
        {"name": "DeviceHelper", "category": "Utils", "status": "active"},
        {"name": "WebViewHelper", "category": "Utils", "status": "active"},
        {"name": "AccessibilityHelper", "category": "Utils", "status": "active"},
        {"name": "BiometricHelper", "category": "Utils", "status": "active"},
        {"name": "ImageCompare", "category": "Utils", "status": "active"},
        {"name": "LogCollector", "category": "Utils", "status": "active"},
        {"name": "NetworkMock", "category": "Utils", "status": "active"},
        {"name": "SmartSelector", "category": "Utils", "status": "active"},
        {"name": "MonkeyTester", "category": "Utils", "status": "active"},
        {"name": "NetworkSimulator", "category": "Utils", "status": "active"},
        {"name": "VideoRecorder", "category": "Utils", "status": "active"},
        # Scanner
        {"name": "PageAnalyzer", "category": "Scanner", "status": "active"},
        {"name": "FlowRecorder", "category": "Scanner", "status": "active"},
        {"name": "FlowNavigator", "category": "Scanner", "status": "active"},
        {"name": "HtmlReport", "category": "Scanner", "status": "active"},
        # Web
        {"name": "Web Dashboard", "category": "Web", "status": "active"},
    ]

    ui.label(f"共 {len(modules)} 個模組").classes("text-subtitle1 q-mb-md")

    # 按 category 分組顯示
    categories = {}
    for m in modules:
        categories.setdefault(m["category"], []).append(m)

    for cat, items in categories.items():
        with ui.card().classes("w-full q-mb-sm"):
            with ui.row().classes("items-center gap-2 q-mb-sm"):
                ui.label(cat).classes("text-subtitle1 font-bold")
                ui.badge(str(len(items)), color="primary")

            with ui.row().classes("gap-2 flex-wrap"):
                for m in items:
                    color = "positive" if m["status"] == "active" else "grey"
                    ui.badge(m["name"], color=color).classes("text-body2")


def _users_panel():
    """使用者管理面板 (admin only)"""
    users_container = ui.column().classes("w-full")

    def refresh_users():
        users_container.clear()
        with users_container:
            _render_users_table()

    # 新增使用者
    with ui.card().classes("w-full q-mb-md"):
        ui.label("新增使用者").classes("text-subtitle1 q-mb-sm")
        with ui.row().classes("w-full gap-2 items-end"):
            new_user = ui.input("帳號").props("outlined dense")
            new_pw = ui.input("密碼", password=True).props("outlined dense")
            new_role = ui.select(
                ["admin", "member", "viewer"],
                value="member",
                label="角色",
            ).props("outlined dense")
            new_name = ui.input("顯示名稱").props("outlined dense")

            def add_user():
                if not new_user.value or not new_pw.value:
                    ui.notify("帳號和密碼不能為空", type="negative")
                    return
                if auth.add_user(new_user.value, new_pw.value, new_role.value, new_name.value):
                    ui.notify(f"已新增使用者: {new_user.value}", type="positive")
                    new_user.value = ""
                    new_pw.value = ""
                    new_name.value = ""
                    refresh_users()
                else:
                    ui.notify("使用者已存在", type="negative")

            ui.button("新增", icon="person_add", on_click=add_user).props("color=primary")

    with users_container:
        _render_users_table()


def _render_users_table():
    """渲染使用者列表"""
    users = auth.list_users()
    columns = [
        {"name": "username", "label": "帳號", "field": "username", "align": "left"},
        {"name": "display_name", "label": "顯示名稱", "field": "display_name", "align": "left"},
        {"name": "role", "label": "角色", "field": "role"},
    ]
    ui.table(columns=columns, rows=users, row_key="username").classes("w-full").props("dense flat")
