"""
HTML Report — 從 session.json 產生豐富的 HTML 測試報告

功能：
- 頁面掃描總覽（每頁的元素、分類統計）
- 轉場流程圖（Mermaid 渲染）
- 測試資料表格（正向/反向/邊界/安全 分類）
- 內嵌截圖（Base64 編碼，獨立 HTML 檔）
- 結果統計面板

用法：
    from scanner.html_report import HtmlReportGenerator

    gen = HtmlReportGenerator("output/session.json")
    gen.generate("output/report.html")

    # 或搭配 ResultDB 的結果
    gen.generate("output/report.html", result_db_path="reports/test_results.db")
"""

from __future__ import annotations

import base64
import json
from datetime import datetime
from pathlib import Path

from utils.logger import logger


class HtmlReportGenerator:
    """從 session.json 產生 HTML 報告"""

    def __init__(self, session_path: str | Path):
        self._path = Path(session_path)
        self._data = json.loads(self._path.read_text(encoding="utf-8"))
        self._base_dir = self._path.parent

    def generate(
        self,
        output_path: str | Path,
        result_db_path: str | Path | None = None,
    ) -> Path:
        """產生 HTML 報告"""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        # 組合各區塊
        sections = [
            self._section_header(),
            self._section_stats(),
            self._section_pages(),
            self._section_flow_diagram(),
            self._section_transitions(),
            self._section_test_cases(),
            self._section_screenshots(),
        ]

        # 加入 ResultDB 資料（如果有）
        if result_db_path and Path(result_db_path).exists():
            sections.append(self._section_result_db(result_db_path))

        html = self._wrap_html("\n".join(sections))
        out.write_text(html, encoding="utf-8")
        logger.info(f"[HtmlReport] 報告已產生: {out}")
        return out

    # ── 各區塊 ──

    def _section_header(self) -> str:
        d = self._data
        return f"""
        <div class="header">
            <h1>📱 Appium Scanner 測試報告</h1>
            <div class="meta">
                <span>App: <strong>{d.get('app_name', 'N/A')}</strong></span>
                <span>平台: <strong>{d.get('platform', 'N/A')}</strong></span>
                <span>時間: {d.get('start_time', '')[:19]} ~ {d.get('end_time', '')[:19]}</span>
            </div>
        </div>
        """

    def _section_stats(self) -> str:
        d = self._data
        return f"""
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{d.get('pages_discovered', 0)}</div>
                <div class="stat-label">頁面數</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{d.get('total_elements', 0)}</div>
                <div class="stat-label">元素數</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{d.get('total_test_cases', 0)}</div>
                <div class="stat-label">測試案例</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(d.get('transitions', []))}</div>
                <div class="stat-label">轉場記錄</div>
            </div>
        </div>
        """

    def _section_pages(self) -> str:
        snapshots = self._data.get("snapshots", [])
        if not snapshots:
            return ""

        rows = []
        for snap in snapshots:
            inputs = snap.get("inputs", [])
            buttons = snap.get("buttons", [])
            input_list = ", ".join(
                f'<span class="tag">{i["var_name"]}</span>'
                for i in inputs
            )
            button_list = ", ".join(
                f'<span class="tag btn-tag">{b["var_name"]}</span>'
                for b in buttons
            )
            rows.append(f"""
            <tr>
                <td><strong>{snap['page_name']}</strong></td>
                <td><span class="badge">{snap['page_type']}</span></td>
                <td>{len(inputs)}</td>
                <td>{len(buttons)}</td>
                <td>{input_list or '-'}</td>
                <td>{button_list or '-'}</td>
            </tr>
            """)

        return f"""
        <div class="section">
            <h2>📄 頁面掃描結果</h2>
            <table>
                <thead>
                    <tr>
                        <th>頁面</th>
                        <th>類型</th>
                        <th>輸入框</th>
                        <th>按鈕</th>
                        <th>輸入框列表</th>
                        <th>按鈕列表</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        """

    def _section_flow_diagram(self) -> str:
        transitions = self._data.get("transitions", [])
        if not transitions:
            return ""

        # 產生 Mermaid 圖
        mermaid_lines = ["graph TD"]
        seen = set()
        for t in transitions:
            from_p = t["from"].replace(" ", "_")
            to_p = t["to"].replace(" ", "_")
            action = t["action"]
            key = f"{from_p}-{to_p}-{action}"
            if key not in seen:
                seen.add(key)
                mermaid_lines.append(
                    f'    {from_p}["{t["from"]}"] -->|{action}| {to_p}["{t["to"]}"]'
                )

        mermaid_code = "\n".join(mermaid_lines)

        return f"""
        <div class="section">
            <h2>🔀 頁面流程圖</h2>
            <div class="mermaid">
{mermaid_code}
            </div>
        </div>
        """

    def _section_transitions(self) -> str:
        transitions = self._data.get("transitions", [])
        if not transitions:
            return ""

        rows = []
        for i, t in enumerate(transitions, 1):
            type_class = {
                "page_change": "type-change",
                "error_shown": "type-error",
                "same_page": "type-same",
                "dialog": "type-dialog",
            }.get(t["type"], "type-other")

            values_str = ", ".join(
                f"{k}={v}" for k, v in t.get("values", {}).items() if v
            ) or "-"

            rows.append(f"""
            <tr>
                <td>{i}</td>
                <td>{t['from']}</td>
                <td>{t['action']}</td>
                <td>{t['to']}</td>
                <td><span class="badge {type_class}">{t['type']}</span></td>
                <td class="values-cell">{values_str}</td>
            </tr>
            """)

        return f"""
        <div class="section">
            <h2>🔗 轉場記錄</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>起始頁面</th>
                        <th>動作</th>
                        <th>目標頁面</th>
                        <th>類型</th>
                        <th>填入值</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        """

    def _section_test_cases(self) -> str:
        test_cases = self._data.get("test_cases", {})
        if not test_cases:
            return ""

        sections_html = []
        for page_name, cases in test_cases.items():
            if not cases:
                continue

            # 分類統計
            categories = {}
            for c in cases:
                cat = c["category"]
                categories[cat] = categories.get(cat, 0) + 1

            cat_badges = " ".join(
                f'<span class="badge cat-{cat}">{cat}: {count}</span>'
                for cat, count in sorted(categories.items())
            )

            # 前 10 筆明細
            rows = []
            for c in cases[:10]:
                fields_str = ", ".join(
                    f"{k}=<code>{v[:30]}{'...' if len(v) > 30 else ''}</code>"
                    for k, v in c["fields"].items()
                )
                tags_str = " ".join(
                    f'<span class="tag">{t}</span>' for t in c.get("tags", [])
                )
                rows.append(f"""
                <tr>
                    <td><code>{c['case_id']}</code></td>
                    <td><span class="badge cat-{c['category']}">{c['category']}</span></td>
                    <td>{c['description']}</td>
                    <td>{fields_str}</td>
                    <td>{c['expected']}</td>
                    <td>{tags_str}</td>
                </tr>
                """)

            more_text = ""
            if len(cases) > 10:
                more_text = f'<p class="more-hint">...還有 {len(cases) - 10} 筆，完整資料請見 session.json</p>'

            sections_html.append(f"""
            <div class="page-cases">
                <h3>{page_name}</h3>
                <div class="cat-summary">{cat_badges} — 共 {len(cases)} 筆</div>
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>分類</th>
                            <th>描述</th>
                            <th>欄位值</th>
                            <th>預期</th>
                            <th>標籤</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(rows)}
                    </tbody>
                </table>
                {more_text}
            </div>
            """)

        return f"""
        <div class="section">
            <h2>🧪 測試資料</h2>
            {''.join(sections_html)}
        </div>
        """

    def _section_screenshots(self) -> str:
        """內嵌截圖（Base64）"""
        ss_dir = self._base_dir / "screenshots"
        if not ss_dir.exists():
            return ""

        images = sorted(ss_dir.glob("*.png"))
        if not images:
            return ""

        img_html = []
        for img_path in images[:20]:  # 最多 20 張
            try:
                data = base64.b64encode(img_path.read_bytes()).decode()
                img_html.append(f"""
                <div class="screenshot-card">
                    <img src="data:image/png;base64,{data}" alt="{img_path.stem}" />
                    <div class="screenshot-label">{img_path.stem}</div>
                </div>
                """)
            except Exception:
                continue

        if not img_html:
            return ""

        more_text = ""
        if len(images) > 20:
            more_text = f'<p class="more-hint">...還有 {len(images) - 20} 張截圖</p>'

        return f"""
        <div class="section">
            <h2>📸 截圖</h2>
            <div class="screenshot-grid">
                {''.join(img_html)}
            </div>
            {more_text}
        </div>
        """

    def _section_result_db(self, db_path: str | Path) -> str:
        """從 ResultDB 讀取歷史趨勢"""
        try:
            from core.result_db import ResultDB
            db = ResultDB(db_path)
            trend = db.get_pass_rate_trend(limit=10)
            flaky = db.get_flaky_tests(window=20)
        except Exception:
            return ""

        # 趨勢表
        trend_rows = []
        for r in trend:
            rate_pct = f"{r['pass_rate'] * 100:.0f}%"
            bar_width = int(r["pass_rate"] * 100)
            trend_rows.append(f"""
            <tr>
                <td>{r['date']}</td>
                <td>{r['passed']}/{r['total']}</td>
                <td>
                    <div class="bar-bg">
                        <div class="bar-fill" style="width:{bar_width}%">{rate_pct}</div>
                    </div>
                </td>
                <td>{r['duration']:.1f}s</td>
            </tr>
            """)

        # Flaky 表
        flaky_rows = []
        for f in flaky[:10]:
            rate_pct = f"{f['pass_rate'] * 100:.0f}%"
            flaky_rows.append(f"""
            <tr>
                <td><code>{f['test_name']}</code></td>
                <td>{rate_pct}</td>
                <td>{f['passed']}/{f['total']}</td>
            </tr>
            """)

        trend_html = ""
        if trend_rows:
            trend_html = f"""
            <h3>通過率趨勢</h3>
            <table>
                <thead><tr><th>日期</th><th>通過/總計</th><th>通過率</th><th>耗時</th></tr></thead>
                <tbody>{''.join(trend_rows)}</tbody>
            </table>
            """

        flaky_html = ""
        if flaky_rows:
            flaky_html = f"""
            <h3>不穩定測試 (Flaky)</h3>
            <table>
                <thead><tr><th>測試</th><th>通過率</th><th>通過/總計</th></tr></thead>
                <tbody>{''.join(flaky_rows)}</tbody>
            </table>
            """

        return f"""
        <div class="section">
            <h2>📊 歷史趨勢</h2>
            {trend_html}
            {flaky_html}
        </div>
        """

    # ── HTML 模板 ──

    def _wrap_html(self, body: str) -> str:
        return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Appium Scanner 測試報告</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>mermaid.initialize({{startOnLoad: true, theme: 'default'}});</script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 24px;
        }}
        .header h1 {{ font-size: 24px; margin-bottom: 8px; }}
        .header .meta span {{
            margin-right: 24px;
            font-size: 14px;
            opacity: 0.9;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .stat-card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .stat-number {{
            font-size: 36px;
            font-weight: 700;
            color: #667eea;
        }}
        .stat-label {{
            font-size: 14px;
            color: #888;
            margin-top: 4px;
        }}
        .section {{
            background: white;
            border-radius: 10px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .section h2 {{
            font-size: 18px;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid #f0f0f0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        th, td {{
            padding: 8px 12px;
            text-align: left;
            border-bottom: 1px solid #f0f0f0;
        }}
        th {{
            background: #fafafa;
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
            color: #666;
        }}
        tr:hover {{ background: #fafafa; }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
        }}
        .type-change {{ background: #e3f2fd; color: #1565c0; }}
        .type-error {{ background: #fce4ec; color: #c62828; }}
        .type-same {{ background: #f5f5f5; color: #757575; }}
        .type-dialog {{ background: #fff3e0; color: #e65100; }}
        .type-other {{ background: #f3e5f5; color: #6a1b9a; }}
        .cat-positive {{ background: #e8f5e9; color: #2e7d32; }}
        .cat-negative {{ background: #fce4ec; color: #c62828; }}
        .cat-boundary {{ background: #fff3e0; color: #e65100; }}
        .cat-security {{ background: #fbe9e7; color: #bf360c; }}
        .tag {{
            display: inline-block;
            padding: 1px 6px;
            border-radius: 4px;
            font-size: 11px;
            background: #e8eaf6;
            color: #3949ab;
            margin: 1px;
        }}
        .btn-tag {{ background: #e8f5e9; color: #2e7d32; }}
        .cat-summary {{ margin-bottom: 12px; }}
        .cat-summary .badge {{ margin-right: 8px; }}
        .page-cases {{ margin-bottom: 24px; }}
        .page-cases h3 {{ margin-bottom: 8px; color: #444; }}
        .more-hint {{ color: #999; font-size: 13px; margin-top: 8px; }}
        .values-cell {{ font-size: 12px; color: #666; max-width: 300px; }}
        code {{
            background: #f5f5f5;
            padding: 1px 4px;
            border-radius: 3px;
            font-size: 12px;
        }}
        .mermaid {{
            text-align: center;
            padding: 16px 0;
        }}
        .screenshot-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 16px;
        }}
        .screenshot-card {{
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            overflow: hidden;
        }}
        .screenshot-card img {{
            width: 100%;
            display: block;
        }}
        .screenshot-label {{
            padding: 8px;
            font-size: 12px;
            color: #666;
            text-align: center;
            background: #fafafa;
        }}
        .bar-bg {{
            background: #f0f0f0;
            border-radius: 8px;
            overflow: hidden;
            height: 22px;
        }}
        .bar-fill {{
            background: linear-gradient(90deg, #66bb6a, #43a047);
            height: 100%;
            text-align: center;
            color: white;
            font-size: 11px;
            font-weight: 600;
            line-height: 22px;
            min-width: 40px;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #999;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    {body}
    <div class="footer">
        由 Appium Scanner 自動產生 &mdash; {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    </div>
</body>
</html>"""
