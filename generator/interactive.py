"""
互動式問答 CLI
透過 terminal 問答收集 App 資訊，產生 AppSpec。
"""

import json
from pathlib import Path

from generator.schema import (
    AppSpec, ElementSpec, ElementType, LocatorStrategy, PageSpec, Platform,
)


def _ask(prompt: str, default: str = "") -> str:
    hint = f" [{default}]" if default else ""
    answer = input(f"  {prompt}{hint}: ").strip()
    return answer or default


def _ask_choice(prompt: str, choices: list[str], default: str = "") -> str:
    hint = f" [{default}]" if default else ""
    choice_str = " / ".join(choices)
    answer = input(f"  {prompt} ({choice_str}){hint}: ").strip()
    return answer if answer in choices else default


def _ask_yn(prompt: str, default: bool = True) -> bool:
    yn = "Y/n" if default else "y/N"
    answer = input(f"  {prompt} ({yn}): ").strip().lower()
    if not answer:
        return default
    return answer.startswith("y")


def collect_app_spec() -> AppSpec:
    """互動式問答收集 AppSpec"""
    print("\n" + "=" * 60)
    print("  Appium 測試專案產生器 — 互動模式")
    print("=" * 60)

    # ── App 基本資訊 ──
    print("\n[1] App 基本資訊")
    app_name = _ask("App 名稱", "my_app")
    platform = _ask_choice("平台", ["android", "ios"], "android")

    if platform == "android":
        package_name = _ask("Package name", "com.example.app")
        activity_name = _ask("Main activity", ".MainActivity")
        bundle_id = ""
    else:
        package_name = ""
        activity_name = ""
        bundle_id = _ask("Bundle ID", "com.example.app")

    device_name = _ask("裝置名稱", "emulator-5554")
    appium_server = _ask("Appium Server URL", "http://127.0.0.1:4723")
    app_path = _ask("APK/IPA 路徑 (可空)")

    # ── 頁面 ──
    print("\n[2] 頁面設定")
    pages: list[PageSpec] = []

    while True:
        print(f"\n  --- 第 {len(pages) + 1} 個頁面 ---")
        page_name = _ask("頁面名稱 (如 login, home；輸入空白結束)")
        if not page_name:
            break

        page_desc = _ask("頁面說明", page_name)

        # 元素
        elements: list[ElementSpec] = []
        print(f"\n  [{page_name}] 新增元素（輸入空白名稱結束）")

        while True:
            el_name = _ask("    元素名稱 (如 username, login_btn)")
            if not el_name:
                break

            el_type = _ask_choice(
                "    類型",
                ["input", "button", "text", "checkbox", "switch", "image"],
                "input",
            )

            loc_strategy = _ask_choice(
                "    定位策略",
                ["id", "accessibility_id", "xpath", "class_name"],
                "id",
            )

            loc_value = _ask("    定位值")

            el_desc = _ask("    說明", el_name)

            spec_kwargs = {
                "name": el_name,
                "element_type": ElementType(el_type),
                "locator_strategy": LocatorStrategy(loc_strategy),
                "locator_value": loc_value,
                "description": el_desc,
            }

            if el_type == "input":
                fmt = _ask_choice(
                    "    輸入格式",
                    ["text", "email", "phone", "password", "number", "url", "date"],
                    "text",
                )
                spec_kwargs["input_format"] = fmt
                spec_kwargs["required"] = _ask_yn("    是否必填", True)
                valid = _ask("    有效測試值 (可空，會自動產生)")
                if valid:
                    spec_kwargs["valid_value"] = valid
                max_len = _ask("    最大長度", "256")
                spec_kwargs["max_length"] = int(max_len)

            elements.append(ElementSpec(**spec_kwargs))
            print(f"    ✓ 已加入: {el_name} ({el_type})")

        # 頁面額外設定
        submit_btn = ""
        success_ind = ""
        error_ind = ""
        next_page = ""

        buttons = [e.name for e in elements if e.element_type == ElementType.BUTTON]
        if buttons:
            submit_btn = _ask(
                f"  提交按鈕 ({', '.join(buttons)})", buttons[0]
            )

        text_els = [e.name for e in elements if e.element_type == ElementType.TEXT]
        if text_els:
            success_ind = _ask("  成功指示器元素名稱 (可空)")
            error_ind = _ask("  錯誤指示器元素名稱 (可空)")

        next_page = _ask("  成功後跳轉頁面 (可空)")

        pages.append(PageSpec(
            name=page_name,
            description=page_desc,
            elements=elements,
            submit_button=submit_btn,
            success_indicator=success_ind,
            error_indicator=error_ind,
            next_page=next_page,
        ))
        print(f"\n  ✓ 頁面 '{page_name}' 已加入 ({len(elements)} 個元素)")

    # ── 輸出目錄 ──
    print("\n[3] 輸出設定")
    output_dir = _ask("輸出目錄", f"./{app_name}_tests")

    spec = AppSpec(
        app_name=app_name,
        platform=Platform(platform),
        package_name=package_name,
        activity_name=activity_name,
        bundle_id=bundle_id,
        device_name=device_name,
        appium_server=appium_server,
        app_path=app_path,
        pages=pages,
        output_dir=output_dir,
    )

    # 確認
    print(f"\n{'='*60}")
    print(f"  摘要:")
    print(f"    App:    {app_name} ({platform})")
    print(f"    頁面:   {len(pages)} 個")
    total_el = sum(len(p.elements) for p in pages)
    print(f"    元素:   {total_el} 個")
    print(f"    輸出:   {output_dir}")
    print(f"{'='*60}")

    if _ask_yn("確定產生", True):
        return spec
    else:
        print("已取消。")
        raise SystemExit(0)


def load_from_json(path: str) -> AppSpec:
    """從 JSON 檔案載入 AppSpec"""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return AppSpec.from_dict(data)
