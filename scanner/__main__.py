"""
Scanner CLI 入口

用法:
    # 掃描當前頁面（不操作）
    python -m scanner --output ~/my_tests --scan-only

    # 自動探索模式（掃描 → 操作 → 掃描 → ...）
    python -m scanner --output ~/my_tests --explore --max-pages 5

    # 指定平台
    python -m scanner --output ~/my_tests --explore --platform ios

    # 從 session.json 重新產出（不連線）
    python -m scanner --output ~/my_tests --regenerate

    # 從 session.json 產出 HTML 報告
    python -m scanner --output ~/my_tests --report
"""

import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="智慧頁面掃描器 — 自動抓元素、分析語意、產生測試",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="輸出目錄（所有產出寫到這裡）",
    )
    parser.add_argument(
        "--platform", "-p",
        default="android",
        choices=["android", "ios"],
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--scan-only",
        action="store_true",
        help="只掃描當前頁面，不操作",
    )
    mode.add_argument(
        "--explore",
        action="store_true",
        help="自動探索模式：掃描 → 操作 → 重新掃描",
    )
    mode.add_argument(
        "--regenerate",
        action="store_true",
        help="從 session.json 重新產出檔案（不連線）",
    )
    mode.add_argument(
        "--report",
        action="store_true",
        help="從 session.json 產出 HTML 報告",
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=5,
        help="自動探索時最多掃幾個頁面 (預設 5)",
    )

    args = parser.parse_args()
    output = Path(args.output).resolve()

    if args.regenerate:
        _regenerate(output)
        return

    if args.report:
        _generate_report(output)
        return

    from scanner.session_runner import SessionRunner

    runner = SessionRunner(output_dir=output, platform=args.platform)

    print(f"\n連線到模擬器 ({args.platform})...")
    runner.connect()

    try:
        if args.scan_only:
            print("掃描當前頁面...\n")
            snap = runner.scan_current()
            _print_snapshot(snap, runner)
            runner.export_all()
        else:
            print(f"開始自動探索 (最多 {args.max_pages} 頁)...\n")
            runner.auto_explore(max_pages=args.max_pages)
            result = runner.export_all()
            print(f"\n完成！共 {result['total_test_cases']} 組測試資料")
            print(f"目錄: {output}")
            print(f"\n下一步:")
            print(f"  cd {output}")
            print(f"  pip install -r requirements.txt")
            print(f"  pytest -m smoke")

        # 自動產出 HTML 報告
        _generate_report(output)
    finally:
        runner.disconnect()


def _print_snapshot(snap, runner):
    """印出掃描結果摘要"""
    cases = runner.recorder.session.test_cases.get(snap.inferred_name, [])

    print(f"{'='*50}")
    print(f"  頁面: {snap.inferred_name}")
    print(f"  類型: {snap.page_type.value} (信心 {snap.page_type_confidence:.0%})")
    print(f"  Activity: {snap.activity}")
    print(f"{'='*50}")

    if snap.inputs:
        print(f"\n  輸入框 ({len(snap.inputs)}):")
        for el in snap.inputs:
            print(f"    - {el.var_name} [{el.field_semantic.value}] "
                  f"({el.locator_strategy}={el.locator_value})")

    if snap.buttons:
        print(f"\n  按鈕 ({len(snap.buttons)}):")
        for el in snap.buttons:
            sem = f" [{el.button_semantic.value}]" if el.button_semantic.value != "unknown" else ""
            print(f"    - {el.var_name}{sem}")

    if snap.submit_button:
        print(f"\n  提交按鈕: {snap.submit_button.var_name}")
    if snap.error_indicator:
        print(f"  錯誤指示: {snap.error_indicator.var_name}")

    # 測試資料統計
    if cases:
        from collections import Counter
        cats = Counter(c.category for c in cases)
        print(f"\n  測試資料: {len(cases)} 組")
        for cat, count in cats.items():
            print(f"    {cat}: {count}")


def _regenerate(output: Path):
    """從 session.json 重新產出"""
    session_file = output / "session.json"
    if not session_file.exists():
        print(f"找不到 {session_file}")
        sys.exit(1)

    print(f"從 {session_file} 重新產出...")

    from scanner.session_runner import SessionRunner
    runner = SessionRunner(output_dir=output)
    # 載入 session 並重新 export
    data = json.loads(session_file.read_text(encoding="utf-8"))
    print(f"載入 {data.get('pages_discovered', 0)} 頁面, "
          f"{data.get('total_test_cases', 0)} 測試案例")

    # 產出 HTML 報告
    _generate_report(output)
    print("完成！")


def _generate_report(output: Path):
    """產出 HTML 報告"""
    session_file = output / "session.json"
    if not session_file.exists():
        print("(跳過 HTML 報告：找不到 session.json)")
        return

    from scanner.html_report import HtmlReportGenerator

    report_path = output / "report.html"
    gen = HtmlReportGenerator(session_file)
    gen.generate(report_path)
    print(f"\nHTML 報告: {report_path}")


if __name__ == "__main__":
    main()
