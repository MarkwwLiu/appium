"""
Dashboard 頁面 — 測試結果總覽

顯示：
- 統計卡片 (總 Run 數、測試數、平均通過率、最近 Run 狀態)
- 通過率趨勢折線圖
- 最近 Run 列表
- 失敗測試快速瀏覽
"""

from nicegui import ui

from web.components.layout import stat_card
from web.services.result_service import result_service


def dashboard_page():
    """Dashboard 頁面主體"""
    overview = result_service.get_overview()
    trend = result_service.get_pass_rate_trend(limit=30)
    recent_runs = result_service.get_recent_runs(limit=10)

    # ── 統計卡片 ──
    with ui.row().classes("w-full gap-4 q-mb-lg"):
        with ui.column().classes("col"):
            stat_card(
                "總 Run 次數",
                str(overview["total_runs"]),
                "play_circle",
                "primary",
            )
        with ui.column().classes("col"):
            stat_card(
                "測試案例數",
                str(overview["total_tests"]),
                "list_alt",
                "info",
            )
        with ui.column().classes("col"):
            rate = overview["avg_pass_rate"]
            color = "positive" if rate >= 90 else "warning" if rate >= 70 else "negative"
            stat_card(
                "平均通過率",
                f"{rate}%",
                "check_circle",
                color,
            )
        with ui.column().classes("col"):
            latest = overview.get("latest_run")
            if latest:
                status_text = f"{latest['passed']}/{latest['total']}"
                latest_color = (
                    "positive" if latest["failed"] == 0 else "negative"
                )
            else:
                status_text = "N/A"
                latest_color = "grey"
            stat_card(
                "最近 Run",
                status_text,
                "schedule",
                latest_color,
            )

    # ── 通過率趨勢圖 ──
    with ui.card().classes("w-full q-mb-lg"):
        ui.label("通過率趨勢").classes("text-h6 q-mb-sm")

        if trend:
            chart_options = {
                "chart": {"type": "area", "height": 300},
                "title": {"text": ""},
                "xAxis": {
                    "categories": [t["date"] for t in trend],
                    "labels": {"rotation": -45, "style": {"fontSize": "10px"}},
                },
                "yAxis": {
                    "title": {"text": "通過率 (%)"},
                    "min": 0,
                    "max": 100,
                    "plotBands": [
                        {"from": 90, "to": 100, "color": "rgba(76,175,80,0.1)"},
                        {"from": 0, "to": 70, "color": "rgba(244,67,54,0.1)"},
                    ],
                },
                "series": [
                    {
                        "name": "通過率",
                        "data": [t["pass_rate"] for t in trend],
                        "color": "#4CAF50",
                        "fillOpacity": 0.1,
                    },
                ],
                "tooltip": {"valueSuffix": "%"},
                "credits": {"enabled": False},
            }
            ui.highchart(chart_options).classes("w-full")
        else:
            ui.label("尚無測試資料").classes("text-grey text-center q-pa-xl")

    # ── 執行時間 + 失敗數趨勢 ──
    if trend:
        with ui.row().classes("w-full gap-4 q-mb-lg"):
            with ui.card().classes("col"):
                ui.label("執行時間趨勢").classes("text-h6 q-mb-sm")
                time_chart = {
                    "chart": {"type": "column", "height": 250},
                    "title": {"text": ""},
                    "xAxis": {
                        "categories": [t["date"] for t in trend],
                        "labels": {"rotation": -45, "style": {"fontSize": "10px"}},
                    },
                    "yAxis": {"title": {"text": "秒"}},
                    "series": [
                        {
                            "name": "執行時間",
                            "data": [t["duration"] for t in trend],
                            "color": "#2196F3",
                        },
                    ],
                    "credits": {"enabled": False},
                }
                ui.highchart(time_chart).classes("w-full")

            with ui.card().classes("col"):
                ui.label("失敗數趨勢").classes("text-h6 q-mb-sm")
                fail_chart = {
                    "chart": {"type": "column", "height": 250},
                    "title": {"text": ""},
                    "xAxis": {
                        "categories": [t["date"] for t in trend],
                        "labels": {"rotation": -45, "style": {"fontSize": "10px"}},
                    },
                    "yAxis": {"title": {"text": "失敗數"}, "min": 0},
                    "series": [
                        {
                            "name": "失敗",
                            "data": [t["failed"] for t in trend],
                            "color": "#F44336",
                        },
                    ],
                    "credits": {"enabled": False},
                }
                ui.highchart(fail_chart).classes("w-full")

    # ── 最近 Run 列表 ──
    with ui.card().classes("w-full"):
        ui.label("最近執行記錄").classes("text-h6 q-mb-sm")

        if recent_runs:
            columns = [
                {"name": "run_id", "label": "Run ID", "field": "run_id", "align": "left"},
                {"name": "platform", "label": "平台", "field": "platform"},
                {"name": "env", "label": "環境", "field": "env"},
                {"name": "total", "label": "總數", "field": "total"},
                {"name": "passed", "label": "通過", "field": "passed"},
                {"name": "failed", "label": "失敗", "field": "failed"},
                {"name": "duration", "label": "耗時(s)", "field": "duration"},
                {"name": "start_time", "label": "時間", "field": "start_time"},
            ]
            rows = [
                {
                    **r,
                    "duration": round(r["duration"], 1) if r["duration"] else 0,
                    "start_time": r["start_time"][:19] if r["start_time"] else "",
                }
                for r in recent_runs
            ]
            ui.table(columns=columns, rows=rows, row_key="run_id").classes(
                "w-full"
            ).props("dense flat")
        else:
            ui.label("尚無執行記錄").classes("text-grey text-center q-pa-lg")
