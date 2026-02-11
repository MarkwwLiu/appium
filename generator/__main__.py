"""
CLI 入口

用法:
    # 互動模式 — 一步步問你
    python -m generator

    # 從 JSON 設定檔產生（非互動）
    python -m generator --spec app_spec.json

    # 指定輸出目錄
    python -m generator --spec app_spec.json --output ~/my_tests

    # 範例：產生範例 JSON 設定檔
    python -m generator --example > app_spec.json
"""

import argparse
import json
import sys

from generator.engine import GeneratorEngine
from generator.interactive import collect_app_spec, load_from_json
from generator.schema import AppSpec


EXAMPLE_SPEC = {
    "app_name": "demo_app",
    "platform": "android",
    "package_name": "com.example.demo",
    "activity_name": ".MainActivity",
    "appium_server": "http://127.0.0.1:4723",
    "device_name": "emulator-5554",
    "app_path": "",
    "output_dir": "./demo_app_tests",
    "pages": [
        {
            "name": "login",
            "description": "登入頁面",
            "submit_button": "login_btn",
            "success_indicator": "welcome_text",
            "error_indicator": "error_msg",
            "next_page": "home",
            "elements": [
                {
                    "name": "username",
                    "element_type": "input",
                    "locator_strategy": "id",
                    "locator_value": "com.example.demo:id/et_username",
                    "description": "帳號輸入框",
                    "required": True,
                    "input_format": "email",
                    "valid_value": "test@example.com",
                    "max_length": 100,
                },
                {
                    "name": "password",
                    "element_type": "input",
                    "locator_strategy": "id",
                    "locator_value": "com.example.demo:id/et_password",
                    "description": "密碼輸入框",
                    "required": True,
                    "input_format": "password",
                    "valid_value": "Abc123!@#",
                    "max_length": 50,
                },
                {
                    "name": "remember_me",
                    "element_type": "checkbox",
                    "locator_strategy": "id",
                    "locator_value": "com.example.demo:id/cb_remember",
                    "description": "記住我",
                },
                {
                    "name": "login_btn",
                    "element_type": "button",
                    "locator_strategy": "id",
                    "locator_value": "com.example.demo:id/btn_login",
                    "description": "登入按鈕",
                },
                {
                    "name": "welcome_text",
                    "element_type": "text",
                    "locator_strategy": "id",
                    "locator_value": "com.example.demo:id/tv_welcome",
                    "description": "歡迎文字（登入成功後顯示）",
                },
                {
                    "name": "error_msg",
                    "element_type": "text",
                    "locator_strategy": "id",
                    "locator_value": "com.example.demo:id/tv_error",
                    "description": "錯誤訊息",
                },
            ],
        },
        {
            "name": "register",
            "description": "註冊頁面",
            "submit_button": "register_btn",
            "error_indicator": "error_msg",
            "elements": [
                {
                    "name": "email",
                    "element_type": "input",
                    "locator_strategy": "id",
                    "locator_value": "com.example.demo:id/et_email",
                    "description": "Email",
                    "required": True,
                    "input_format": "email",
                    "max_length": 100,
                },
                {
                    "name": "phone",
                    "element_type": "input",
                    "locator_strategy": "id",
                    "locator_value": "com.example.demo:id/et_phone",
                    "description": "手機號碼",
                    "required": True,
                    "input_format": "phone",
                    "max_length": 15,
                },
                {
                    "name": "password",
                    "element_type": "input",
                    "locator_strategy": "id",
                    "locator_value": "com.example.demo:id/et_reg_password",
                    "description": "密碼",
                    "required": True,
                    "input_format": "password",
                    "max_length": 50,
                },
                {
                    "name": "confirm_password",
                    "element_type": "input",
                    "locator_strategy": "id",
                    "locator_value": "com.example.demo:id/et_reg_confirm",
                    "description": "確認密碼",
                    "required": True,
                    "input_format": "password",
                    "max_length": 50,
                },
                {
                    "name": "agree_terms",
                    "element_type": "checkbox",
                    "locator_strategy": "id",
                    "locator_value": "com.example.demo:id/cb_terms",
                    "description": "同意條款",
                },
                {
                    "name": "register_btn",
                    "element_type": "button",
                    "locator_strategy": "id",
                    "locator_value": "com.example.demo:id/btn_register",
                    "description": "註冊按鈕",
                },
                {
                    "name": "error_msg",
                    "element_type": "text",
                    "locator_strategy": "id",
                    "locator_value": "com.example.demo:id/tv_reg_error",
                    "description": "錯誤訊息",
                },
            ],
        },
    ],
}


def main():
    parser = argparse.ArgumentParser(
        description="Appium 測試專案產生器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
範例:
  python -m generator                        # 互動模式
  python -m generator --spec app_spec.json   # 從設定檔
  python -m generator --example              # 印出範例 JSON
""",
    )
    parser.add_argument(
        "--spec", help="JSON 設定檔路徑 (非互動模式)"
    )
    parser.add_argument(
        "--output", help="覆蓋輸出目錄"
    )
    parser.add_argument(
        "--example", action="store_true",
        help="印出範例 JSON 設定檔",
    )

    args = parser.parse_args()

    # 印範例
    if args.example:
        print(json.dumps(EXAMPLE_SPEC, indent=4, ensure_ascii=False))
        return

    # 從 JSON 或互動
    if args.spec:
        spec = load_from_json(args.spec)
    else:
        spec = collect_app_spec()

    # 覆蓋輸出目錄
    if args.output:
        spec.output_dir = args.output

    if not spec.output_dir:
        spec.output_dir = f"./{spec.app_name}_tests"

    # 產生
    engine = GeneratorEngine(spec)
    result = engine.generate()

    print(f"共產生 {result['summary']['total_files']} 個檔案。")


if __name__ == "__main__":
    main()
