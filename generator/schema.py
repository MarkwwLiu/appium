"""
資料結構定義
使用者輸入的 App / 頁面 / 元素資訊的統一格式。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Platform(Enum):
    ANDROID = "android"
    IOS = "ios"


class ElementType(Enum):
    INPUT = "input"        # 輸入框
    BUTTON = "button"      # 按鈕
    TEXT = "text"          # 文字標籤
    CHECKBOX = "checkbox"  # 勾選框
    SWITCH = "switch"      # 開關
    IMAGE = "image"        # 圖片
    LIST = "list"          # 列表
    CUSTOM = "custom"      # 自訂


class LocatorStrategy(Enum):
    ID = "id"
    ACCESSIBILITY_ID = "accessibility_id"
    XPATH = "xpath"
    CLASS_NAME = "class_name"
    ANDROID_UIAUTOMATOR = "android_uiautomator"
    IOS_PREDICATE = "ios_predicate"
    IOS_CLASS_CHAIN = "ios_class_chain"


@dataclass
class ElementSpec:
    """單一元素規格"""
    name: str                              # 變數名稱，如 "username"
    element_type: ElementType              # 元素類型
    locator_strategy: LocatorStrategy      # 定位策略
    locator_value: str                     # 定位值
    description: str = ""                  # 說明
    required: bool = True                  # 是否必填（用於產生反向測試）
    # 輸入框專用
    valid_value: str = ""                  # 正向測試值
    max_length: int = 256                  # 最大長度（邊界測試用）
    input_format: str = ""                # "email", "phone", "password", "number", "text"


@dataclass
class PageSpec:
    """單一頁面規格"""
    name: str                              # 頁面名稱，如 "login"
    description: str = ""
    elements: list[ElementSpec] = field(default_factory=list)
    # 頁面流程
    submit_button: str = ""               # 提交按鈕的 element name
    success_indicator: str = ""           # 成功後出現的元素 name
    error_indicator: str = ""             # 失敗後出現的元素 name
    # 導航
    next_page: str = ""                   # 成功後跳轉的頁面名稱

    @property
    def inputs(self) -> list[ElementSpec]:
        return [e for e in self.elements if e.element_type == ElementType.INPUT]

    @property
    def buttons(self) -> list[ElementSpec]:
        return [e for e in self.elements if e.element_type == ElementType.BUTTON]

    @property
    def checkboxes(self) -> list[ElementSpec]:
        return [e for e in self.elements
                if e.element_type in (ElementType.CHECKBOX, ElementType.SWITCH)]


@dataclass
class AppSpec:
    """完整 App 測試規格"""
    app_name: str                          # App 名稱
    platform: Platform = Platform.ANDROID
    # Android
    package_name: str = ""                 # com.example.app
    activity_name: str = ""                # .MainActivity
    # iOS
    bundle_id: str = ""                    # com.example.app
    # 共用
    appium_server: str = "http://127.0.0.1:4723"
    device_name: str = "emulator-5554"
    app_path: str = ""                     # APK / IPA 路徑
    # 頁面
    pages: list[PageSpec] = field(default_factory=list)
    # 輸出
    output_dir: str = ""                   # 產出目錄

    def to_dict(self) -> dict:
        """轉為 dict (存檔 / 傳遞用)，所有 Enum 轉為 .value"""
        import dataclasses

        def _convert(obj):
            if isinstance(obj, Enum):
                return obj.value
            if isinstance(obj, dict):
                return {k: _convert(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_convert(i) for i in obj]
            return obj

        raw = dataclasses.asdict(self)
        return _convert(raw)

    @classmethod
    def from_dict(cls, data: dict) -> "AppSpec":
        """從 dict 建立（讀取 JSON 設定檔用）"""
        pages = []
        for p in data.get("pages", []):
            elements = [
                ElementSpec(
                    name=e["name"],
                    element_type=ElementType(e.get("element_type", "input")),
                    locator_strategy=LocatorStrategy(e.get("locator_strategy", "id")),
                    locator_value=e.get("locator_value", ""),
                    description=e.get("description", ""),
                    required=e.get("required", True),
                    valid_value=e.get("valid_value", ""),
                    max_length=e.get("max_length", 256),
                    input_format=e.get("input_format", "text"),
                )
                for e in p.get("elements", [])
            ]
            pages.append(PageSpec(
                name=p["name"],
                description=p.get("description", ""),
                elements=elements,
                submit_button=p.get("submit_button", ""),
                success_indicator=p.get("success_indicator", ""),
                error_indicator=p.get("error_indicator", ""),
                next_page=p.get("next_page", ""),
            ))

        return cls(
            app_name=data.get("app_name", "my_app"),
            platform=Platform(data.get("platform", "android")),
            package_name=data.get("package_name", ""),
            activity_name=data.get("activity_name", ""),
            bundle_id=data.get("bundle_id", ""),
            appium_server=data.get("appium_server", "http://127.0.0.1:4723"),
            device_name=data.get("device_name", "emulator-5554"),
            app_path=data.get("app_path", ""),
            pages=pages,
            output_dir=data.get("output_dir", ""),
        )
