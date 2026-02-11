"""
PageAnalyzer — 智慧頁面掃描與語意分析

不只抓元素，還推斷：
1. 每個元素的「用途」(email? password? phone? search? ...)
2. 頁面的「類型」(login? register? search? settings? ...)
3. 哪個按鈕是提交、哪個是取消
4. 哪些是成功/錯誤指示器

推斷依據：resource-id、text、hint、content-desc、class 的關鍵字綜合判斷。
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from appium.webdriver.common.appiumby import AppiumBy
from utils.logger import logger


# ── 語意分類 ──

class FieldSemantic(Enum):
    """欄位語意（推斷結果）"""
    EMAIL = "email"
    PASSWORD = "password"
    CONFIRM_PASSWORD = "confirm_password"
    USERNAME = "username"
    PHONE = "phone"
    NAME = "name"
    SEARCH = "search"
    URL = "url"
    NUMBER = "number"
    DATE = "date"
    ADDRESS = "address"
    CAPTCHA = "captcha"
    GENERIC_TEXT = "generic_text"
    UNKNOWN = "unknown"


class ButtonSemantic(Enum):
    """按鈕語意"""
    SUBMIT = "submit"       # 登入、註冊、送出
    CANCEL = "cancel"       # 取消
    BACK = "back"           # 返回
    NEXT = "next"           # 下一步
    DELETE = "delete"       # 刪除
    TOGGLE = "toggle"       # 開關
    NAVIGATION = "navigation"  # 導航
    UNKNOWN = "unknown"


class PageType(Enum):
    """頁面類型"""
    LOGIN = "login"
    REGISTER = "register"
    SEARCH = "search"
    SETTINGS = "settings"
    PROFILE = "profile"
    LIST = "list"
    DETAIL = "detail"
    FORM = "form"
    HOME = "home"
    UNKNOWN = "unknown"


# ── 關鍵字對照表 ──

_FIELD_KEYWORDS: dict[FieldSemantic, list[str]] = {
    FieldSemantic.EMAIL: [
        "email", "mail", "e-mail", "電子郵件", "信箱", "邮箱",
    ],
    FieldSemantic.PASSWORD: [
        "password", "passwd", "pwd", "密碼", "密码",
    ],
    FieldSemantic.CONFIRM_PASSWORD: [
        "confirm_password", "confirm_pwd", "re_password", "repeat_password",
        "確認密碼", "确认密码",
    ],
    FieldSemantic.USERNAME: [
        "username", "user_name", "account", "login_id", "uid",
        "帳號", "用戶名", "账号", "用户名",
    ],
    FieldSemantic.PHONE: [
        "phone", "mobile", "tel", "telephone", "cell",
        "手機", "電話", "手机", "电话",
    ],
    FieldSemantic.NAME: [
        "name", "full_name", "first_name", "last_name", "real_name", "nickname",
        "姓名", "名字", "暱稱", "昵称",
    ],
    FieldSemantic.SEARCH: [
        "search", "query", "keyword", "filter",
        "搜尋", "搜索", "查詢", "关键词",
    ],
    FieldSemantic.URL: [
        "url", "link", "website", "href", "網址", "链接",
    ],
    FieldSemantic.NUMBER: [
        "number", "amount", "quantity", "count", "price", "age",
        "數量", "金額", "價格", "年齡", "数量",
    ],
    FieldSemantic.DATE: [
        "date", "birthday", "birth", "日期", "生日",
    ],
    FieldSemantic.ADDRESS: [
        "address", "addr", "location", "city", "zip",
        "地址", "城市", "郵遞區號",
    ],
    FieldSemantic.CAPTCHA: [
        "captcha", "verify_code", "verification", "otp", "sms_code",
        "驗證碼", "验证码",
    ],
}

_BUTTON_KEYWORDS: dict[ButtonSemantic, list[str]] = {
    ButtonSemantic.SUBMIT: [
        "login", "signin", "sign_in", "register", "signup", "sign_up",
        "submit", "send", "confirm", "save", "ok", "done", "apply", "continue",
        "登入", "登錄", "登录", "註冊", "注册", "送出", "提交",
        "確認", "确认", "儲存", "保存", "完成",
    ],
    ButtonSemantic.CANCEL: [
        "cancel", "dismiss", "close", "no", "取消", "關閉", "关闭",
    ],
    ButtonSemantic.BACK: [
        "back", "return", "previous", "返回", "上一步",
    ],
    ButtonSemantic.NEXT: [
        "next", "forward", "step", "下一步", "繼續", "继续",
    ],
    ButtonSemantic.DELETE: [
        "delete", "remove", "trash", "刪除", "删除", "移除",
    ],
}

_PAGE_KEYWORDS: dict[PageType, list[str]] = {
    PageType.LOGIN: ["login", "signin", "sign_in", "登入", "登錄", "登录"],
    PageType.REGISTER: ["register", "signup", "sign_up", "create_account", "註冊", "注册"],
    PageType.SEARCH: ["search", "搜尋", "搜索"],
    PageType.SETTINGS: ["setting", "preference", "config", "設定", "设置"],
    PageType.PROFILE: ["profile", "account", "my", "me", "個人", "我的"],
    PageType.LIST: ["list", "feed", "timeline", "列表"],
    PageType.DETAIL: ["detail", "info", "view", "詳情", "详情"],
}


# ── 元素分析結果 ──

@dataclass
class AnalyzedElement:
    """分析完成的單一元素"""
    # 原始屬性
    resource_id: str = ""
    text: str = ""
    hint: str = ""
    content_desc: str = ""
    class_name: str = ""
    clickable: bool = False
    editable: bool = False
    checkable: bool = False
    scrollable: bool = False
    enabled: bool = True
    bounds: str = ""
    index: int = 0
    # 推斷結果
    var_name: str = ""
    element_type: str = ""          # "input", "button", "text", "checkbox", "image"
    field_semantic: FieldSemantic = FieldSemantic.UNKNOWN
    button_semantic: ButtonSemantic = ButtonSemantic.UNKNOWN
    confidence: float = 0.0         # 推斷信心 0~1
    locator_strategy: str = ""      # "id", "accessibility_id", "xpath"
    locator_value: str = ""

    @property
    def identity_text(self) -> str:
        """用於辨識的所有文字合併（小寫）"""
        parts = [self.resource_id, self.text, self.hint, self.content_desc]
        return " ".join(p.lower() for p in parts if p)

    @property
    def short_id(self) -> str:
        """短 ID：取 resource_id 最後一段或 text 前 20 字"""
        if self.resource_id and "/" in self.resource_id:
            return self.resource_id.split("/")[-1]
        if self.resource_id:
            return self.resource_id
        if self.text:
            return self.text[:20]
        if self.content_desc:
            return self.content_desc[:20]
        return f"el_{self.index}"


@dataclass
class PageSnapshot:
    """單一頁面的完整快照"""
    page_id: str = ""                # 頁面指紋 (hash)
    page_type: PageType = PageType.UNKNOWN
    page_type_confidence: float = 0.0
    timestamp: str = ""
    activity: str = ""               # Android current activity
    # 元素
    all_elements: list[AnalyzedElement] = field(default_factory=list)
    inputs: list[AnalyzedElement] = field(default_factory=list)
    buttons: list[AnalyzedElement] = field(default_factory=list)
    texts: list[AnalyzedElement] = field(default_factory=list)
    checkboxes: list[AnalyzedElement] = field(default_factory=list)
    images: list[AnalyzedElement] = field(default_factory=list)
    # 推斷
    submit_button: AnalyzedElement | None = None
    error_indicator: AnalyzedElement | None = None
    success_indicator: AnalyzedElement | None = None
    # 原始
    page_source_hash: str = ""

    @property
    def inferred_name(self) -> str:
        """推斷的頁面名稱"""
        if self.page_type != PageType.UNKNOWN:
            return self.page_type.value
        if self.activity:
            # com.example.app.LoginActivity → login
            name = self.activity.rsplit(".", 1)[-1]
            name = name.replace("Activity", "").replace("Fragment", "")
            return _to_snake(name) if name else "unknown"
        return "unknown"


# ── PageAnalyzer ──

class PageAnalyzer:
    """
    智慧頁面分析器

    掃描模擬器當前頁面，分析每個元素的語意，
    推斷頁面類型與提交/錯誤指示器。
    """

    def __init__(self, driver):
        self.driver = driver

    def snapshot(self) -> PageSnapshot:
        """
        擷取當前頁面快照並進行完整分析。

        Returns:
            PageSnapshot 包含所有分析結果
        """
        snap = PageSnapshot(timestamp=datetime.now().isoformat())

        # 取得 activity
        try:
            snap.activity = self.driver.current_activity or ""
        except Exception:
            snap.activity = ""

        # 取得 page source hash (用於偵測頁面變更)
        source = self.driver.page_source
        snap.page_source_hash = hashlib.md5(source.encode()).hexdigest()

        # 掃描所有元素
        raw_elements = self.driver.find_elements(AppiumBy.XPATH, "//*")
        logger.info(f"掃描到 {len(raw_elements)} 個原始元素")

        idx = 0
        for el in raw_elements:
            try:
                analyzed = self._analyze_element(el, idx)
                if analyzed:
                    snap.all_elements.append(analyzed)
                    self._classify(analyzed, snap)
                    idx += 1
            except Exception:
                continue

        # 頁面層級推斷
        snap.page_type, snap.page_type_confidence = self._infer_page_type(snap)
        snap.submit_button = self._find_submit_button(snap)
        snap.error_indicator = self._find_error_indicator(snap)
        snap.success_indicator = self._find_success_indicator(snap)
        snap.page_id = f"{snap.inferred_name}_{snap.page_source_hash[:8]}"

        logger.info(
            f"分析完成: {snap.inferred_name} ({snap.page_type.value}) "
            f"— {len(snap.inputs)} 輸入, {len(snap.buttons)} 按鈕, "
            f"{len(snap.texts)} 文字, {len(snap.checkboxes)} 勾選"
        )

        return snap

    def detect_change(self, previous_hash: str) -> bool:
        """偵測頁面是否有變化"""
        source = self.driver.page_source
        current_hash = hashlib.md5(source.encode()).hexdigest()
        return current_hash != previous_hash

    # ── 元素分析 ──

    def _analyze_element(self, el, index: int) -> AnalyzedElement | None:
        """分析單一元素"""
        rid = el.get_attribute("resourceId") or ""
        text = el.get_attribute("text") or ""
        hint = ""
        try:
            hint = el.get_attribute("hint") or ""
        except Exception:
            pass
        desc = el.get_attribute("contentDescription") or ""
        cls = el.get_attribute("className") or ""
        clickable = el.get_attribute("clickable") == "true"
        checkable = el.get_attribute("checkable") == "true"
        enabled = el.get_attribute("enabled") != "false"
        bounds = el.get_attribute("bounds") or ""

        # 過濾：完全無辨識資訊的跳過
        if not rid and not text and not desc and not hint:
            return None

        # 過濾：純 layout 容器跳過
        layout_classes = [
            "LinearLayout", "RelativeLayout", "FrameLayout",
            "ConstraintLayout", "CoordinatorLayout", "ScrollView",
            "RecyclerView", "ViewGroup",
        ]
        if any(lc in cls for lc in layout_classes) and not text and not desc:
            return None

        analyzed = AnalyzedElement(
            resource_id=rid,
            text=text,
            hint=hint,
            content_desc=desc,
            class_name=cls,
            clickable=clickable,
            editable="EditText" in cls or "TextInput" in cls,
            checkable=checkable,
            enabled=enabled,
            bounds=bounds,
            index=index,
        )

        # 決定 element_type
        if analyzed.editable:
            analyzed.element_type = "input"
        elif checkable:
            analyzed.element_type = "checkbox"
        elif "Button" in cls or (clickable and ("btn" in rid.lower() or "button" in rid.lower())):
            analyzed.element_type = "button"
        elif "ImageView" in cls or "Image" in cls:
            analyzed.element_type = "image"
        elif "TextView" in cls or text:
            analyzed.element_type = "text"
        elif clickable:
            analyzed.element_type = "button"
        else:
            analyzed.element_type = "text"

        # 決定 locator
        if rid:
            analyzed.locator_strategy = "id"
            analyzed.locator_value = rid
        elif desc:
            analyzed.locator_strategy = "accessibility_id"
            analyzed.locator_value = desc
        else:
            analyzed.locator_strategy = "xpath"
            if text:
                safe = text.replace('"', '\\"')
                analyzed.locator_value = f'//*[@text="{safe}"]'
            else:
                analyzed.locator_value = f'//*[@class="{cls}"][@index="{index}"]'

        # 語意推斷
        if analyzed.element_type == "input":
            analyzed.field_semantic, analyzed.confidence = self._infer_field_semantic(analyzed)
        elif analyzed.element_type == "button":
            analyzed.button_semantic, analyzed.confidence = self._infer_button_semantic(analyzed)

        # 變數名稱
        analyzed.var_name = self._make_var_name(analyzed)

        return analyzed

    def _classify(self, el: AnalyzedElement, snap: PageSnapshot) -> None:
        """分類到 snap 的對應列表"""
        if el.element_type == "input":
            snap.inputs.append(el)
        elif el.element_type == "button":
            snap.buttons.append(el)
        elif el.element_type == "checkbox":
            snap.checkboxes.append(el)
        elif el.element_type == "image":
            snap.images.append(el)
        else:
            snap.texts.append(el)

    # ── 語意推斷 ──

    def _infer_field_semantic(self, el: AnalyzedElement) -> tuple[FieldSemantic, float]:
        """推斷輸入欄位語意"""
        identity = el.identity_text

        # 先做精確比對（confirm_password 要在 password 之前）
        ordered_checks = [
            FieldSemantic.CONFIRM_PASSWORD,
            FieldSemantic.EMAIL,
            FieldSemantic.PASSWORD,
            FieldSemantic.USERNAME,
            FieldSemantic.PHONE,
            FieldSemantic.NAME,
            FieldSemantic.SEARCH,
            FieldSemantic.URL,
            FieldSemantic.NUMBER,
            FieldSemantic.DATE,
            FieldSemantic.ADDRESS,
            FieldSemantic.CAPTCHA,
        ]

        for semantic in ordered_checks:
            keywords = _FIELD_KEYWORDS.get(semantic, [])
            for kw in keywords:
                if kw in identity:
                    # 在 resource_id 中找到信心更高
                    if kw in el.resource_id.lower():
                        return semantic, 0.95
                    if kw in el.hint.lower():
                        return semantic, 0.85
                    return semantic, 0.70

        # inputType 屬性推斷
        try:
            input_type = self.driver.execute_script(
                "mobile: shell",
                {"command": "dumpsys", "args": ["input_method"]},
            )
        except Exception:
            pass

        return FieldSemantic.GENERIC_TEXT, 0.3

    def _infer_button_semantic(self, el: AnalyzedElement) -> tuple[ButtonSemantic, float]:
        """推斷按鈕語意"""
        identity = el.identity_text

        for semantic, keywords in _BUTTON_KEYWORDS.items():
            for kw in keywords:
                if kw in identity:
                    if kw in el.resource_id.lower():
                        return semantic, 0.95
                    return semantic, 0.70

        # 沒有匹配到任何關鍵字
        if el.clickable:
            return ButtonSemantic.UNKNOWN, 0.3
        return ButtonSemantic.UNKNOWN, 0.1

    def _infer_page_type(self, snap: PageSnapshot) -> tuple[PageType, float]:
        """推斷頁面類型"""
        # 從 activity 名稱推斷
        activity_lower = snap.activity.lower()
        for ptype, keywords in _PAGE_KEYWORDS.items():
            if any(kw in activity_lower for kw in keywords):
                return ptype, 0.90

        # 從輸入欄位語意推斷
        semantics = [el.field_semantic for el in snap.inputs]
        btn_semantics = [el.button_semantic for el in snap.buttons]

        has_password = FieldSemantic.PASSWORD in semantics
        has_email = FieldSemantic.EMAIL in semantics
        has_username = FieldSemantic.USERNAME in semantics
        has_confirm_pwd = FieldSemantic.CONFIRM_PASSWORD in semantics
        has_phone = FieldSemantic.PHONE in semantics
        has_search = FieldSemantic.SEARCH in semantics

        if has_password and has_confirm_pwd:
            return PageType.REGISTER, 0.85
        if has_password and (has_email or has_username):
            return PageType.LOGIN, 0.80
        if has_search:
            return PageType.SEARCH, 0.75
        if len(snap.inputs) >= 3:
            return PageType.FORM, 0.60

        # 從頁面文字推斷
        all_text = " ".join(t.text.lower() for t in snap.texts)
        for ptype, keywords in _PAGE_KEYWORDS.items():
            if any(kw in all_text for kw in keywords):
                return ptype, 0.55

        return PageType.UNKNOWN, 0.2

    def _find_submit_button(self, snap: PageSnapshot) -> AnalyzedElement | None:
        """找出提交按鈕"""
        submits = [
            b for b in snap.buttons
            if b.button_semantic == ButtonSemantic.SUBMIT
        ]
        if submits:
            return max(submits, key=lambda b: b.confidence)

        # 沒有明確 submit → 取最後一個 enabled button
        enabled_btns = [b for b in snap.buttons if b.enabled]
        return enabled_btns[-1] if enabled_btns else None

    def _find_error_indicator(self, snap: PageSnapshot) -> AnalyzedElement | None:
        """找出錯誤訊息元素"""
        error_keywords = ["error", "err", "warning", "alert", "錯誤", "警告", "失敗"]
        for el in snap.texts:
            if any(kw in el.identity_text for kw in error_keywords):
                return el
        return None

    def _find_success_indicator(self, snap: PageSnapshot) -> AnalyzedElement | None:
        """找出成功指示器"""
        success_keywords = [
            "success", "welcome", "home", "dashboard", "profile",
            "成功", "歡迎", "首頁",
        ]
        for el in snap.texts:
            if any(kw in el.identity_text for kw in success_keywords):
                return el
        return None

    def _make_var_name(self, el: AnalyzedElement) -> str:
        """產生變數名稱"""
        base = el.short_id
        name = re.sub(r'[^a-zA-Z0-9_]', '_', base)
        name = re.sub(r'_+', '_', name).strip('_').lower()
        if not name or name[0].isdigit():
            name = f"el_{name}" if name else f"el_{el.index}"
        return name


def _to_snake(text: str) -> str:
    """PascalCase → snake_case"""
    s = re.sub(r'([A-Z])', r'_\1', text).lower().strip('_')
    return re.sub(r'_+', '_', s)
