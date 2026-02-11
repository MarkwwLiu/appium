"""
歷史趨勢頁面

功能：
- Flaky Test 分析表格
- 單一測試的歷史結果 + 時間趨勢
- Run 比對 (回歸分析)
"""

from nicegui import ui

from web.services.result_service import result_service


def history_page():
    """歷史趨勢頁面主體"""

    with ui.tabs().classes("w-full") as tabs:
        tab_flaky = ui.tab("flaky", label="Flaky 分析", icon="bug_report")
        tab_detail = ui.tab("detail", label="測試歷史", icon="history")
        tab_compare = ui.tab("compare", label="Run 比對", icon="compare_arrows")

    with ui.tab_panels(tabs, value="flaky").classes("w-full"):
        with ui.tab_panel("flaky"):
            _flaky_panel()

        with ui.tab_panel("detail"):
            _detail_panel()

        with ui.tab_panel("compare"):
            _compare_panel()


def _flaky_panel():
    """Flaky Test 分析"""
    flaky_tests = result_service.get_flaky_tests(window=20)

    if not flaky_tests:
        ui.label("目前沒有偵測到 Flaky Test").classes("text-grey q-pa-lg")
        ui.label("需要至少 3 次以上的執行記錄才能偵測").classes("text-caption text-grey")
        return

    ui.label(f"偵測到 {len(flaky_tests)} 個 Flaky Test").classes("text-subtitle1 q-mb-md")

    # Flaky 分數分布圖
    with ui.card().classes("w-full q-mb-md"):
        chart_data = flaky_tests[:20]
        bar_chart = {
            "chart": {"type": "bar", "height": max(250, len(chart_data) * 30)},
            "title": {"text": "Flaky 分數排名 (Top 20)"},
            "xAxis": {
                "categories": [t["test_name"].split("::")[-1] for t in chart_data],
                "labels": {"style": {"fontSize": "11px"}},
            },
            "yAxis": {"title": {"text": "Flaky Score"}, "min": 0, "max": 1},
            "series": [
                {
                    "name": "Flaky Score",
                    "data": [t["flaky_score"] for t in chart_data],
                    "color": "#FF9800",
                },
                {
                    "name": "通過率 (%)",
                    "data": [t["pass_rate"] for t in chart_data],
                    "color": "#4CAF50",
                    "visible": False,
                },
            ],
            "credits": {"enabled": False},
        }
        ui.highchart(bar_chart).classes("w-full")

    # 詳細表格
    columns = [
        {"name": "test_name", "label": "測試名稱", "field": "test_name", "align": "left", "sortable": True},
        {"name": "flaky_score", "label": "Flaky Score", "field": "flaky_score", "sortable": True},
        {"name": "pass_rate", "label": "通過率", "field": "pass_rate_str", "sortable": True},
        {"name": "total", "label": "執行次數", "field": "total", "sortable": True},
        {"name": "passed", "label": "通過", "field": "passed"},
        {"name": "failed", "label": "失敗", "field": "failed"},
    ]

    rows = [
        {
            **t,
            "pass_rate_str": f"{t['pass_rate']}%",
        }
        for t in flaky_tests
    ]

    ui.table(columns=columns, rows=rows, row_key="test_name").classes("w-full").props(
        "dense flat"
    )


def _detail_panel():
    """單一測試歷史"""
    test_names = result_service.get_all_test_names()

    if not test_names:
        ui.label("尚無測試紀錄").classes("text-grey q-pa-lg")
        return

    detail_container = ui.column().classes("w-full")

    selected_test = ui.select(
        test_names,
        value=test_names[0] if test_names else None,
        label="選擇測試",
    ).classes("w-full q-mb-md").props("outlined")

    def load_detail():
        detail_container.clear()
        if not selected_test.value:
            return

        name = selected_test.value
        history = result_service.get_test_history(name, limit=30)
        duration_trend = result_service.get_duration_trend(name, limit=30)

        with detail_container:
            if not history:
                ui.label("無歷史紀錄").classes("text-grey")
                return

            # 執行時間趨勢
            if duration_trend:
                with ui.card().classes("w-full q-mb-md"):
                    ui.label("執行時間趨勢").classes("text-subtitle2 q-mb-sm")
                    chart = {
                        "chart": {"type": "area", "height": 250},
                        "title": {"text": ""},
                        "xAxis": {
                            "categories": [d["date"] for d in duration_trend],
                            "labels": {"rotation": -45, "style": {"fontSize": "10px"}},
                        },
                        "yAxis": {"title": {"text": "秒"}},
                        "series": [{
                            "name": "執行時間",
                            "data": [d["duration"] for d in duration_trend],
                            "color": "#2196F3",
                            "fillOpacity": 0.1,
                        }],
                        "credits": {"enabled": False},
                    }
                    ui.highchart(chart).classes("w-full")

            # 歷史結果表格
            with ui.card().classes("w-full"):
                ui.label("歷史紀錄").classes("text-subtitle2 q-mb-sm")
                columns = [
                    {"name": "outcome", "label": "結果", "field": "outcome"},
                    {"name": "duration", "label": "耗時(s)", "field": "duration"},
                    {"name": "platform", "label": "平台", "field": "platform"},
                    {"name": "env", "label": "環境", "field": "env"},
                    {"name": "timestamp", "label": "時間", "field": "timestamp", "align": "left"},
                    {"name": "error", "label": "錯誤訊息", "field": "error_message", "align": "left"},
                ]
                rows = [
                    {
                        **h,
                        "duration": round(h["duration"], 2) if h.get("duration") else 0,
                        "timestamp": h["timestamp"][:19] if h.get("timestamp") else "",
                        "error_message": (h.get("error_message", "") or "")[:100],
                    }
                    for h in history
                ]
                ui.table(columns=columns, rows=rows, row_key="timestamp").classes("w-full").props(
                    "dense flat"
                )

    selected_test.on("change", load_detail)
    load_detail()


def _compare_panel():
    """Run 比對"""
    runs = result_service.get_recent_runs(limit=20)

    if len(runs) < 2:
        ui.label("至少需要 2 次 Run 才能比對").classes("text-grey q-pa-lg")
        return

    run_options = {r["run_id"]: f"{r['run_id']} ({r['start_time'][:16]})" for r in runs}

    compare_container = ui.column().classes("w-full")

    with ui.row().classes("w-full gap-4 items-end q-mb-md"):
        run_a = ui.select(
            run_options,
            value=runs[1]["run_id"],
            label="Run A (舊)",
        ).classes("flex-grow").props("outlined")

        ui.icon("arrow_forward", size="md").classes("q-mb-sm")

        run_b = ui.select(
            run_options,
            value=runs[0]["run_id"],
            label="Run B (新)",
        ).classes("flex-grow").props("outlined")

    def do_compare():
        compare_container.clear()
        if not run_a.value or not run_b.value:
            return

        # 取得兩次 run 的結果
        results_a = {r["test_name"]: r for r in result_service.get_run_details(run_a.value)}
        results_b = {r["test_name"]: r for r in result_service.get_run_details(run_b.value)}

        tests_a = set(results_a.keys())
        tests_b = set(results_b.keys())

        new_failures = [t for t in tests_b if results_b[t]["outcome"] == "failed" and results_a.get(t, {}).get("outcome") != "failed"]
        fixed = [t for t in tests_a & tests_b if results_a[t]["outcome"] == "failed" and results_b[t]["outcome"] == "passed"]
        still_failing = [t for t in tests_a & tests_b if results_a[t]["outcome"] == "failed" and results_b[t]["outcome"] == "failed"]
        new_tests = list(tests_b - tests_a)

        with compare_container:
            # 摘要卡片
            with ui.row().classes("w-full gap-4 q-mb-md"):
                with ui.card().classes("col"):
                    ui.label("新增失敗").classes("text-caption text-grey")
                    ui.label(str(len(new_failures))).classes("text-h4 text-negative font-bold")
                with ui.card().classes("col"):
                    ui.label("已修復").classes("text-caption text-grey")
                    ui.label(str(len(fixed))).classes("text-h4 text-positive font-bold")
                with ui.card().classes("col"):
                    ui.label("持續失敗").classes("text-caption text-grey")
                    ui.label(str(len(still_failing))).classes("text-h4 text-warning font-bold")
                with ui.card().classes("col"):
                    ui.label("新增測試").classes("text-caption text-grey")
                    ui.label(str(len(new_tests))).classes("text-h4 text-info font-bold")

            # 詳細列表
            if new_failures:
                with ui.card().classes("w-full q-mb-sm"):
                    ui.label("新增失敗").classes("text-subtitle1 text-negative q-mb-sm")
                    for t in new_failures:
                        ui.label(f"  {t}").classes("text-body2")

            if fixed:
                with ui.card().classes("w-full q-mb-sm"):
                    ui.label("已修復").classes("text-subtitle1 text-positive q-mb-sm")
                    for t in fixed:
                        ui.label(f"  {t}").classes("text-body2")

            if still_failing:
                with ui.card().classes("w-full q-mb-sm"):
                    ui.label("持續失敗").classes("text-subtitle1 text-warning q-mb-sm")
                    for t in still_failing:
                        ui.label(f"  {t}").classes("text-body2")

    ui.button("開始比對", icon="compare_arrows", on_click=do_compare).props("color=primary")

    with compare_container:
        pass
