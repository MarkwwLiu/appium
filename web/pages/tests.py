"""
測試管理頁面

功能：
- 測試檔案列表
- 選擇測試執行
- Smart Select 風險排名
- 即時執行輸出
"""

import asyncio

from nicegui import app, ui

from web.services.result_service import result_service
from web.services.test_runner_service import test_runner


def tests_page():
    """測試管理頁面主體"""

    with ui.tabs().classes("w-full") as tabs:
        tab_list = ui.tab("tests", label="測試列表", icon="list")
        tab_risk = ui.tab("risk", label="風險排名", icon="warning")
        tab_run = ui.tab("run", label="執行測試", icon="play_arrow")

    with ui.tab_panels(tabs, value="tests").classes("w-full"):
        # ── 測試列表 Tab ──
        with ui.tab_panel("tests"):
            _test_list_panel()

        # ── 風險排名 Tab ──
        with ui.tab_panel("risk"):
            _risk_ranking_panel()

        # ── 執行測試 Tab ──
        with ui.tab_panel("run"):
            _run_panel()


def _test_list_panel():
    """測試列表面板"""
    discovered = test_runner.discover_tests()

    if not discovered:
        ui.label("在 tests/ 目錄中未找到測試檔案").classes("text-grey q-pa-lg")
        return

    ui.label(f"共 {len(discovered)} 個測試檔案").classes("text-subtitle1 q-mb-md")

    columns = [
        {"name": "name", "label": "測試名稱", "field": "name", "align": "left", "sortable": True},
        {"name": "file", "label": "檔案路徑", "field": "file", "align": "left"},
        {"name": "module", "label": "模組", "field": "module", "align": "left"},
    ]

    ui.table(
        columns=columns,
        rows=discovered,
        row_key="file",
        selection="multiple",
    ).classes("w-full").props("dense flat")


def _risk_ranking_panel():
    """風險排名面板"""
    try:
        from utils.smart_selector import SmartSelector
        selector = SmartSelector()
        ranked = selector.rank_tests()
    except Exception:
        ranked = []

    if not ranked:
        ui.label("尚無歷史資料，無法計算風險排名").classes("text-grey q-pa-lg")
        ui.label("執行更多測試後，系統會自動分析測試風險").classes("text-caption text-grey")
        return

    ui.label(f"共 {len(ranked)} 個測試的風險評估").classes("text-subtitle1 q-mb-md")

    # 風險分布圖
    with ui.card().classes("w-full q-mb-md"):
        ui.label("風險分布").classes("text-subtitle2 q-mb-sm")
        high_risk = sum(1 for t in ranked if t.risk_score >= 0.7)
        med_risk = sum(1 for t in ranked if 0.3 <= t.risk_score < 0.7)
        low_risk = sum(1 for t in ranked if t.risk_score < 0.3)

        pie_chart = {
            "chart": {"type": "pie", "height": 250},
            "title": {"text": ""},
            "series": [{
                "name": "測試數",
                "data": [
                    {"name": f"高風險 ({high_risk})", "y": high_risk, "color": "#F44336"},
                    {"name": f"中風險 ({med_risk})", "y": med_risk, "color": "#FF9800"},
                    {"name": f"低風險 ({low_risk})", "y": low_risk, "color": "#4CAF50"},
                ],
            }],
            "credits": {"enabled": False},
        }
        ui.highchart(pie_chart).classes("w-full")

    # 排名表格
    columns = [
        {"name": "rank", "label": "#", "field": "rank"},
        {"name": "test_name", "label": "測試名稱", "field": "test_name", "align": "left", "sortable": True},
        {"name": "risk_score", "label": "風險分數", "field": "risk_score", "sortable": True},
        {"name": "fail_rate", "label": "失敗率", "field": "fail_rate", "sortable": True},
        {"name": "flaky_score", "label": "Flaky", "field": "flaky_score", "sortable": True},
        {"name": "last", "label": "最後結果", "field": "last"},
        {"name": "count", "label": "執行次數", "field": "count"},
    ]

    rows = [
        {
            "rank": i + 1,
            "test_name": t.test_name,
            "risk_score": t.risk_score,
            "fail_rate": f"{t.recent_fail_rate:.0%}",
            "flaky_score": t.flaky_score,
            "last": t.last_outcome,
            "count": t.run_count,
        }
        for i, t in enumerate(ranked[:50])
    ]

    ui.table(columns=columns, rows=rows, row_key="rank").classes("w-full").props("dense flat")


def _run_panel():
    """執行測試面板"""
    username = app.storage.user.get("username", "")

    with ui.row().classes("w-full gap-4 items-end q-mb-md"):
        platform_select = ui.select(
            ["android", "ios"],
            value="android",
            label="平台",
        ).classes("w-40")

        env_select = ui.select(
            ["dev", "staging", "prod"],
            value="dev",
            label="環境",
        ).classes("w-40")

        test_input = ui.input(
            "指定測試 (選填)",
            placeholder="tests/test_login.py 或留空跑全部",
        ).classes("flex-grow")

    output_log = ui.log(max_lines=500).classes("w-full h-96 q-mb-md")
    output_log.push("等待執行...\n")

    status_label = ui.label("").classes("text-subtitle1")

    async def start_run():
        tests = [test_input.value] if test_input.value.strip() else []
        job_id = test_runner.create_job(
            tests=tests,
            platform=platform_select.value,
            env=env_select.value,
            triggered_by=username,
        )

        output_log.clear()
        output_log.push(f"啟動測試 (Job: {job_id})...\n")
        output_log.push(f"平台: {platform_select.value}, 環境: {env_select.value}\n")
        output_log.push("=" * 50 + "\n")
        status_label.text = "執行中..."

        def on_output(jid, line):
            if jid == job_id:
                output_log.push(line)

        test_runner.add_listener(on_output)
        try:
            await test_runner.run_job(job_id)
        finally:
            test_runner.remove_listener(on_output)

        job = test_runner.get_job(job_id)
        status_label.text = f"完成: {job.status}" if job else "完成"
        ui.notify(
            f"測試執行完成: {job.status}" if job else "完成",
            type="positive" if job and job.status == "completed" else "negative",
        )

    ui.button("開始執行", icon="play_arrow", on_click=start_run).props(
        "color=primary size=lg"
    )

    # 最近執行歷史
    ui.separator().classes("q-my-md")
    ui.label("最近執行").classes("text-subtitle1 q-mb-sm")

    recent_jobs = test_runner.get_recent_jobs(limit=5)
    if recent_jobs:
        for job in recent_jobs:
            with ui.row().classes("items-center gap-2 q-mb-xs"):
                status_color = {
                    "completed": "positive",
                    "failed": "negative",
                    "running": "warning",
                    "pending": "grey",
                }.get(job.status, "grey")
                ui.badge(job.status, color=status_color)
                ui.label(job.job_id).classes("text-caption")
                ui.label(f"by {job.triggered_by}").classes("text-caption text-grey")
    else:
        ui.label("尚無執行記錄").classes("text-grey")
