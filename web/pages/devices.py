"""
裝置管理頁面

顯示已連線裝置資訊、狀態、電量等。
支援手動重新整理。
"""

from nicegui import ui

from web.services.device_service import device_service


def devices_page():
    """裝置管理頁面主體"""

    devices_container = ui.column().classes("w-full")

    def refresh_devices():
        devices_container.clear()
        with devices_container:
            _render_devices()

    with ui.row().classes("w-full items-center justify-between q-mb-md"):
        ui.label("已連線裝置").classes("text-h6")
        ui.button("重新整理", icon="refresh", on_click=refresh_devices).props("flat")

    with devices_container:
        _render_devices()


def _render_devices():
    """渲染裝置卡片"""
    devices = device_service.get_devices()

    if not devices:
        with ui.card().classes("w-full"):
            with ui.column().classes("items-center q-pa-xl w-full"):
                ui.icon("devices_other", size="4rem").classes("text-grey")
                ui.label("未偵測到已連線裝置").classes("text-h6 text-grey q-mt-md")
                ui.label("請確認裝置已連接並啟用 USB 偵錯").classes("text-caption text-grey")

                with ui.expansion("偵錯提示", icon="help_outline").classes("w-full q-mt-md"):
                    ui.markdown("""
**Android:**
- 確認 ADB 已安裝: `adb version`
- 確認裝置已連線: `adb devices`
- 開啟 USB 偵錯模式

**iOS:**
- 確認已安裝 libimobiledevice: `brew install libimobiledevice`
- 或使用 Xcode 的 `xcrun xctrace list devices`
- 需要信任此電腦
                    """)
        return

    # 裝置統計
    android_count = sum(1 for d in devices if d.platform == "android")
    ios_count = sum(1 for d in devices if d.platform == "ios")

    with ui.row().classes("w-full gap-2 q-mb-md"):
        ui.badge(f"共 {len(devices)} 台", color="primary").classes("text-body2")
        if android_count:
            ui.badge(f"Android {android_count}", color="green").classes("text-body2")
        if ios_count:
            ui.badge(f"iOS {ios_count}", color="grey").classes("text-body2")

    # 裝置卡片
    with ui.row().classes("w-full gap-4"):
        for device in devices:
            with ui.card().classes("w-80"):
                with ui.row().classes("items-center gap-3 q-mb-sm"):
                    icon = "phone_android" if device.platform == "android" else "phone_iphone"
                    color = "green" if device.status == "online" else "red"
                    ui.icon(icon, size="lg").classes(f"text-{color}")
                    with ui.column().classes("gap-0"):
                        ui.label(
                            device.model or device.serial
                        ).classes("text-subtitle1 font-bold")
                        ui.label(device.serial).classes("text-caption text-grey")

                ui.separator()

                with ui.grid(columns=2).classes("w-full gap-2 q-mt-sm"):
                    ui.label("平台").classes("text-caption text-grey")
                    platform_label = device.platform.upper()
                    if device.os_version:
                        platform_label += f" {device.os_version}"
                    ui.label(platform_label).classes("text-caption")

                    if device.brand:
                        ui.label("品牌").classes("text-caption text-grey")
                        ui.label(device.brand.capitalize()).classes("text-caption")

                    if device.screen_size:
                        ui.label("螢幕").classes("text-caption text-grey")
                        ui.label(device.screen_size).classes("text-caption")

                    if device.battery:
                        ui.label("電量").classes("text-caption text-grey")
                        battery_val = int(device.battery.replace("%", "")) if device.battery.replace("%", "").isdigit() else 0
                        bat_color = "green" if battery_val > 50 else "orange" if battery_val > 20 else "red"
                        ui.label(device.battery).classes(f"text-caption text-{bat_color}")

                    ui.label("狀態").classes("text-caption text-grey")
                    status_color = "positive" if device.status == "online" else "negative"
                    ui.badge(device.status, color=status_color)
