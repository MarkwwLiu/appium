# Appium App 自動化測試框架

基於 **Python + Appium + pytest** 的 App 自動化測試框架，採用 **Page Object Model (POM)** 設計模式，易於擴充與維護。

支援 **Android** 與 **iOS** 雙平台。

---

## 目錄

- [架構總覽](#架構總覽)
- [目錄結構](#目錄結構)
- [各模組詳解](#各模組詳解)
- [環境建置教學](#環境建置教學)
- [如何執行測試](#如何執行測試)
- [如何新增測試](#如何新增測試)
- [進階用法](#進階用法)

---

## 架構總覽

```
┌────────────────────────────────────────────────────────────┐
│                      pytest 測試層                          │
│          tests/test_login.py ...  (+ markers/parametrize)  │
├────────────────┬───────────────────────────────────────────┤
│  Page Object   │  Component (可組合 UI 元件)                │
│  pages/*.py    │  core/component.py                        │
├────────────────┴───────────────────────────────────────────┤
│                  核心基底 (core/)                            │
│  BasePage   DriverManager   Assertions   EnvManager        │
├────────────────────────────────────────────────────────────┤
│           基礎設施 — 可插拔，不改核心即可擴充                  │
│  ┌──────────────┐ ┌────────────┐ ┌───────────────────┐     │
│  │ Plugin 系統   │ │ Middleware │ │ Event Bus         │     │
│  │ plugins/*.py  │ │ 前後攔截    │ │ 發佈/訂閱事件      │     │
│  └──────────────┘ └────────────┘ └───────────────────┘     │
│  ┌──────────────┐ ┌────────────┐ ┌───────────────────┐     │
│  │ Element Cache│ │ Exception  │ │ Env/Config 繼承    │     │
│  │ 元素快取加速  │ │ 階層體系    │ │ dev/staging/prod  │     │
│  └──────────────┘ └────────────┘ └───────────────────┘     │
├────────────────────────────────────────────────────────────┤
│                    工具層 (utils/)                          │
│  Logger  Screenshot  Gesture  API  A11y  WebView  ...     │
├────────────────────────────────────────────────────────────┤
│               設定層 (config/)                              │
│  Config  caps.json  env/base.json  env/dev.json  ...      │
├────────────────────────────────────────────────────────────┤
│               Appium Python Client + Server                │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│  generator/ — 獨立產生器模組                                │
│  讀取 AppSpec JSON → 在外部目錄產生完整測試專案              │
│  (不影響本框架任何程式碼)                                    │
└────────────────────────────────────────────────────────────┘
```

**設計原則：**

| 原則 | 說明 |
|------|------|
| **分層架構** | 測試邏輯、頁面操作、底層驅動分離，職責清晰 |
| **Page Object Model** | 每個頁面封裝為一個類別，UI 變動只需改一處 |
| **設定集中管理** | capabilities、超時設定統一在 config/ 管理 |
| **失敗自動截圖** | 測試失敗時自動截圖，快速定位問題 |
| **跨平台支援** | 同一套測試，透過參數切換 Android / iOS |

---

## 目錄結構

```
appium/
├── config/                     # 設定管理
│   ├── __init__.py
│   ├── config.py               # 全域設定 (server、超時、路徑)
│   ├── android_caps.json       # Android desired capabilities
│   └── ios_caps.json           # iOS desired capabilities
│
├── core/                       # 核心模組
│   ├── __init__.py
│   ├── driver_manager.py       # Driver 建立/銷毀管理
│   └── base_page.py            # Page Object 基底類別
│
├── pages/                      # Page Objects (每個頁面一個檔案)
│   ├── __init__.py
│   ├── login_page.py           # 範例：登入頁面
│   └── home_page.py            # 範例：首頁
│
├── tests/                      # 測試案例
│   ├── __init__.py
│   ├── test_login.py           # 範例：登入測試
│   └── test_home.py            # 範例：首頁測試
│
├── utils/                      # 工具模組
│   ├── __init__.py
│   ├── logger.py               # 日誌工具
│   ├── screenshot.py           # 截圖工具
│   └── wait_helper.py          # 等待/重試工具
│
├── reports/                    # 測試報告輸出目錄
├── screenshots/                # 截圖輸出目錄
├── conftest.py                 # pytest 全域 fixtures
├── pytest.ini                  # pytest 設定
├── requirements.txt            # Python 依賴
├── appium_env.sh               # macOS 環境變數設定腳本
└── .gitignore
```

---

## 各模組詳解

### 1. `config/` — 設定管理

**`config.py`** 集中管理所有設定，支援環境變數覆蓋：

```python
from config import Config

# 取得 Appium server URL
url = Config.appium_server_url()  # http://127.0.0.1:4723

# 載入 capabilities
caps = Config.load_caps("android")  # 從 android_caps.json 讀取
```

可透過環境變數在 CI/CD 中覆蓋預設值：

```bash
APPIUM_HOST=10.0.0.1 APPIUM_PORT=4724 PLATFORM=ios pytest
```

**`android_caps.json` / `ios_caps.json`** 定義裝置能力：

```json
{
    "platformName": "Android",
    "appium:automationName": "UiAutomator2",
    "appium:deviceName": "emulator-5554",
    "appium:app": "/path/to/your/app.apk"
}
```

### 2. `core/` — 核心模組

**`driver_manager.py`** 管理 Appium driver 的生命週期：

```python
from core import DriverManager

driver = DriverManager.create_driver("android")  # 建立
driver = DriverManager.get_driver()               # 取得
DriverManager.quit_driver()                        # 銷毀
```

**`base_page.py`** 是所有 Page Object 的基底類別，提供：

| 方法 | 用途 |
|------|------|
| `find_element(locator)` | 等待元素出現後回傳 |
| `click(locator)` | 等待可點擊後點擊 |
| `input_text(locator, text)` | 清除後輸入文字 |
| `get_text(locator)` | 取得元素文字 |
| `is_element_present(locator)` | 判斷元素是否存在 |
| `swipe_up/down/left/right()` | 滑動操作 |
| `screenshot(name)` | 手動截圖 |

### 3. `pages/` — Page Objects

每個 App 頁面對應一個 Python 類別，繼承 `BasePage`：

```python
from appium.webdriver.common.appiumby import AppiumBy
from core.base_page import BasePage

class LoginPage(BasePage):
    # 1. 定義 locators
    USERNAME_INPUT = (AppiumBy.ID, "com.example.app:id/username")
    LOGIN_BUTTON = (AppiumBy.ID, "com.example.app:id/btn_login")

    # 2. 封裝頁面操作
    def enter_username(self, username: str) -> "LoginPage":
        self.input_text(self.USERNAME_INPUT, username)
        return self  # 支援鏈式呼叫

    def tap_login(self) -> None:
        self.click(self.LOGIN_BUTTON)
```

### 4. `tests/` — 測試案例

使用 pytest 撰寫，透過 `driver` fixture 自動管理 driver：

```python
class TestLogin:
    def test_login_success(self, driver):
        login_page = LoginPage(driver)
        home_page = HomePage(driver)

        login_page.login(username="testuser", password="password123")
        assert home_page.is_home_page_displayed()
```

### 5. `utils/` — 工具模組

| 模組 | 用途 |
|------|------|
| `logger.py` | 統一日誌，同時輸出到 console 和 `reports/test.log` |
| `screenshot.py` | 截圖工具，儲存到 `screenshots/` 目錄 |
| `wait_helper.py` | 通用等待 (`wait_for`) 和重試 (`retry`) 機制 |

### 6. `conftest.py` — pytest 全域設定

- **`driver` fixture**：每個測試自動建立/銷毀 driver
- **失敗自動截圖**：測試失敗時自動截圖到 `screenshots/FAIL_xxx.png`
- **`--platform` 參數**：命令列指定測試平台

---

## 環境建置教學

### 前置條件

1. **Python 3.10+**
2. **Node.js 18+**（安裝 Appium Server 用）
3. **Android SDK** 或 **Xcode**（依測試平台）

### Step 1：安裝 Appium Server

```bash
npm install -g appium

# 安裝 driver
appium driver install uiautomator2    # Android
appium driver install xcuitest        # iOS
```

### Step 2：設定環境變數（macOS）

可以使用本專案的 `appium_env.sh`：

```bash
chmod +x appium_env.sh
./appium_env.sh
```

或手動加入 `~/.zshrc`：

```bash
export ANDROID_HOME="$HOME/Library/Android/sdk"
export JAVA_HOME=$(/usr/libexec/java_home)
export PATH="$JAVA_HOME/bin:$ANDROID_HOME/platform-tools:$PATH"
```

### Step 3：安裝 Python 依賴

```bash
# 建立虛擬環境（建議）
python3 -m venv venv
source venv/bin/activate

# 安裝依賴
pip install -r requirements.txt
```

### Step 4：設定 capabilities

編輯 `config/android_caps.json`（或 `ios_caps.json`），填入你的 App 資訊：

```json
{
    "platformName": "Android",
    "appium:automationName": "UiAutomator2",
    "appium:deviceName": "emulator-5554",
    "appium:app": "/absolute/path/to/your/app.apk"
}
```

**如何取得 deviceName：**

```bash
adb devices   # Android，例如 emulator-5554
```

### Step 5：啟動 Appium Server

```bash
appium
```

預設會在 `http://127.0.0.1:4723` 啟動。

---

## 如何執行測試

```bash
# 執行所有測試（預設 Android）
pytest

# 指定平台
pytest --platform=android
pytest --platform=ios

# 執行特定測試檔
pytest tests/test_login.py

# 執行特定測試
pytest tests/test_login.py::TestLogin::test_login_success

# 依照標記執行
pytest -m smoke
pytest -m "not ios"

# 產生 HTML 報告
pytest --html=reports/report.html --self-contained-html
```

---

## 如何新增測試

### 新增一個頁面（Page Object）

**Step 1：** 在 `pages/` 建立新檔案，例如 `pages/settings_page.py`：

```python
from appium.webdriver.common.appiumby import AppiumBy
from core.base_page import BasePage


class SettingsPage(BasePage):
    """設定頁面"""

    # 定義 locators
    TITLE = (AppiumBy.ID, "com.example.app:id/settings_title")
    DARK_MODE_SWITCH = (AppiumBy.ID, "com.example.app:id/switch_dark_mode")
    LANGUAGE_OPTION = (AppiumBy.ACCESSIBILITY_ID, "language")

    # 封裝操作
    def toggle_dark_mode(self) -> None:
        self.click(self.DARK_MODE_SWITCH)

    def select_language(self) -> None:
        self.click(self.LANGUAGE_OPTION)

    def get_title(self) -> str:
        return self.get_text(self.TITLE)

    def is_settings_displayed(self) -> bool:
        return self.is_element_present(self.TITLE)
```

### 新增測試案例

**Step 2：** 在 `tests/` 建立新檔案，例如 `tests/test_settings.py`：

```python
import pytest
from pages.login_page import LoginPage
from pages.settings_page import SettingsPage


class TestSettings:

    @pytest.fixture(autouse=True)
    def setup(self, driver):
        """前置：先登入"""
        LoginPage(driver).login("testuser", "password123")

    def test_dark_mode_toggle(self, driver):
        settings = SettingsPage(driver)
        settings.toggle_dark_mode()
        # 驗證 dark mode 狀態...

    @pytest.mark.smoke
    def test_settings_page_displayed(self, driver):
        settings = SettingsPage(driver)
        assert settings.is_settings_displayed()
```

### Locator 查找技巧

| 工具 | 用途 |
|------|------|
| **Appium Inspector** | GUI 工具，可視化檢視元素屬性 |
| `adb shell uiautomator dump` | Android 匯出 UI 階層 |
| `driver.page_source` | 程式內取得頁面結構 |

**Locator 優先順序（推薦）：**

1. `AppiumBy.ID` — 最穩定
2. `AppiumBy.ACCESSIBILITY_ID` — 跨平台通用
3. `AppiumBy.CLASS_NAME` — 搭配 index
4. `AppiumBy.XPATH` — 最後手段（效能較差）

---

## 進階用法

### 使用 pytest marker 分類測試

在 `pytest.ini` 已定義以下標記：

```python
# 在測試上加標記
@pytest.mark.smoke
def test_login_success(self, driver):
    ...

@pytest.mark.regression
@pytest.mark.android
def test_android_specific_feature(self, driver):
    ...
```

```bash
# 只跑 smoke 測試
pytest -m smoke

# 跑 regression 但排除 ios
pytest -m "regression and not ios"
```

### 使用 retry 重試不穩定的操作

```python
from utils.wait_helper import retry

def test_flaky_element(self, driver):
    page = HomePage(driver)
    # 最多重試 3 次，每次間隔 1 秒
    text = retry(lambda: page.get_welcome_text(), max_attempts=3, delay=1.0)
    assert "歡迎" in text
```

### 使用 wait_for 等待自訂條件

```python
from utils.wait_helper import wait_for

def test_data_loaded(self, driver):
    page = HomePage(driver)
    # 等待清單至少有 5 筆資料，最多等 15 秒
    items = wait_for(
        condition=lambda: page.find_elements(page.LIST_ITEMS)
            if len(page.find_elements(page.LIST_ITEMS)) >= 5 else None,
        timeout=15,
        message="等待清單資料載入",
    )
```

### CI/CD 整合

透過環境變數控制所有設定，不需改程式碼：

```yaml
# GitHub Actions 範例
- name: Run Appium Tests
  env:
    APPIUM_HOST: "127.0.0.1"
    APPIUM_PORT: "4723"
    PLATFORM: "android"
    IMPLICIT_WAIT: "15"
  run: |
    pytest --html=reports/report.html --self-contained-html
```

---

## 擴充模組（已內建）

以下進階功能已全部內建在框架中，可直接使用：

### 1. 資料驅動測試

將測試資料放在 `test_data/` 目錄，支援 JSON 和 CSV 格式：

```python
from utils.data_loader import load_json, get_test_ids

LOGIN_DATA = load_json("login_data.json")

class TestLoginDataDriven:
    @pytest.mark.parametrize("data", LOGIN_DATA, ids=get_test_ids(LOGIN_DATA))
    def test_login(self, driver, data):
        LoginPage(driver).login(data["username"], data["password"])
        if data["expected"] == "success":
            assert HomePage(driver).is_home_page_displayed()
```

### 2. 自訂 Decorators

```python
from utils.decorators import android_only, ios_only, retry_on_failure, timer

@android_only                           # 僅 Android 執行
def test_back_button(self, driver): ...

@ios_only                               # 僅 iOS 執行
def test_swipe_back(self, driver): ...

@retry_on_failure(max_retries=3)        # 失敗自動重試
def test_flaky(self, driver): ...

@timer                                  # 印出執行耗時
def test_perf(self, driver): ...
```

### 3. API + UI 混合測試

透過 `api_client` fixture 直接使用：

```python
def test_create_then_verify(self, driver, api_client):
    # 用 API 建立資料
    api_client.post("/users", {"name": "mark", "email": "mark@test.com"})

    # 用 UI 驗證顯示
    home = HomePage(driver)
    assert "mark" in home.get_welcome_text()
```

### 4. 測試資料工廠

不再硬編碼，隨機產生有意義的測試資料：

```python
from utils.data_factory import DataFactory

email = DataFactory.random_email()       # test_abcdef_1234@example.com
phone = DataFactory.random_phone()       # 0912345678
pwd   = DataFactory.random_password()    # 含大小寫+數字+符號
user  = DataFactory.random_username()    # user_abcde_42
```

### 5. 元素探索工具

開發階段快速定位元素，透過 `element_helper` fixture 使用：

```python
def test_debug(self, driver, element_helper):
    element_helper.dump_page("debug.xml")        # 匯出頁面結構
    element_helper.find_all_ids()                 # 列出所有 resource-id
    element_helper.find_by_text("登入")           # 搜尋文字元素
    element_helper.find_clickable_elements()      # 列出所有可點擊元素
```

### 6. Allure 報告

選裝 `allure-pytest` 後自動啟用，測試失敗時會附加截圖與頁面 XML：

```bash
pip install allure-pytest
pytest --alluredir=reports/allure-results
allure serve reports/allure-results
```

在 Page Object 中使用 `@allure_step` 標記步驟：

```python
from utils.allure_helper import allure_step

class LoginPage(BasePage):
    @allure_step("輸入帳號密碼並登入")
    def login(self, username, password):
        self.enter_username(username)
        self.enter_password(password)
        self.tap_login()
```

### 7. GitHub Actions CI/CD

已內建 `.github/workflows/appium-test.yml`，支援：

- **Android**：自動啟動模擬器 + Appium Server + 跑測試
- **iOS**：在 macOS runner 上啟動 Simulator + 跑測試
- 自動上傳測試報告與失敗截圖
- 支援手動觸發並選擇平台

### 8. 手勢操作工具

透過 `gesture` fixture 使用進階手勢：

```python
def test_map_zoom(self, driver, gesture):
    gesture.long_press(element)                # 長按
    gesture.double_tap(element)                # 雙擊
    gesture.drag_and_drop(source, target)      # 拖放
    gesture.zoom()                             # 雙指放大
    gesture.pinch()                            # 雙指縮小
    gesture.scroll_to_text("載入更多")          # 滑動找文字
    gesture.tap_at(100, 200)                   # 點擊座標
```

### 9. App 生命週期管理

透過 `app_manager` fixture 控制 App：

```python
def test_background_resume(self, driver, app_manager):
    app_manager.background_app(5)              # 背景 5 秒後回前景
    app_manager.reset_app("com.example.app")   # 強制重啟
    app_manager.open_deep_link("myapp://page") # Deep Link 跳轉
    state = app_manager.get_app_state("com.example.app")  # 查狀態
    app_manager.clear_app_data("com.example.app")         # 清資料
```

### 10. 裝置控制工具

透過 `device` fixture 操作裝置：

```python
def test_rotation(self, driver, device):
    device.rotate_landscape()         # 橫向
    device.rotate_portrait()          # 直向
    device.hide_keyboard()            # 隱藏鍵盤
    device.open_notifications()       # 開通知欄
    device.set_airplane_mode(True)    # 飛航模式
    device.set_wifi_only()            # 僅 WiFi
    device.press_back()               # 返回鍵
    device.set_clipboard("text")      # 設剪貼簿
    info = device.get_device_info()   # 裝置資訊
```

### 11. 效能監控

追蹤 App 的記憶體、CPU、電量：

```python
from utils.perf_monitor import PerfMonitor

def test_performance(self, driver):
    monitor = PerfMonitor("com.example.app")

    # 單次檢查
    snap = monitor.single_check()
    assert snap.memory_mb < 200

    # 持續監控（需在背景執行緒使用 start/stop）
    snap = monitor.snapshot()
    print(f"記憶體: {snap.memory_mb}MB, CPU: {snap.cpu_percent}%")
```

### 12. Slack / Webhook 通知

測試完成後自動推送結果到 Slack：

```bash
# 設定環境變數後自動啟用
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx pytest
```

也可以手動呼叫：

```python
from utils.notifier import Notifier

notifier = Notifier("https://hooks.slack.com/services/xxx")
message = notifier.format_test_report(
    total=50, passed=48, failed=2, skipped=0,
    duration=120.5, platform="android",
)
notifier.send_slack(message)
```

### 13. 多裝置平行測試

搭配 `pytest-xdist` 在多台裝置上同時跑測試：

```bash
pip install pytest-xdist

# 設定 config/devices.json（每台裝置一筆）
# 啟動多個 Appium server（port 4723, 4724, ...）
appium -p 4723 &
appium -p 4724 &

# 平行跑測試（2 台裝置）
pytest -n 2
```

### 14. 視覺回歸測試

截圖比對，偵測 UI 是否有非預期變動：

```python
def test_ui_unchanged(self, driver, image_compare):
    # 第一次執行：自動建立 baseline
    # 之後執行：與 baseline 比對，差異超過 2% 即失敗
    image_compare.assert_match("home_page")

    # 手動儲存 baseline
    image_compare.save_baseline("login_page")

    # 取得比對結果（不 assert）
    result = image_compare.compare("home_page")
    print(f"差異: {result['diff_percent']:.2%}")
```

需安裝 `pip install Pillow`，差異圖會自動儲存到 `screenshots/diff/`。

### 15. WebView 切換 (Hybrid App)

Native 與 WebView 之間切換操作：

```python
def test_hybrid_app(self, driver, webview):
    webview.wait_for_webview()             # 等待 WebView 出現並切換
    webview.click_by_css("#login-btn")     # CSS selector 操作
    webview.execute_js("return document.title")  # 執行 JS
    webview.switch_to_native()             # 切回 Native
```

### 16. 裝置 Log 收集

自動收集 logcat / syslog，測試失敗時自動儲存：

```python
def test_with_logs(self, driver, log_collector):
    # log_collector 會自動啟動/停止
    # 測試失敗時自動儲存到 reports/device_logs/

    # 手動搜尋 log
    errors = log_collector.search_errors()
    crashes = log_collector.get_crash_logs()
    log_collector.search("NetworkException")
```

### 17. 無障礙 (Accessibility) 測試

自動檢查 App 的無障礙合規性：

```python
def test_accessibility(self, driver, a11y):
    result = a11y.full_audit()
    assert result["overall_pass"], "無障礙稽核未通過"

    # 單獨檢查
    a11y.check_content_descriptions()   # 是否都有 content-description
    a11y.check_touch_target_size()      # 觸控區域是否 >= 48x48
    a11y.check_text_size()              # 文字是否太小
```

### 18. 生物辨識模擬

模擬 Touch ID / Face ID / 指紋：

```python
def test_fingerprint_login(self, driver, biometric):
    biometric.simulate_auth_success()   # 跨平台：模擬驗證成功
    biometric.simulate_auth_failure()   # 跨平台：模擬驗證失敗

    # iOS 專用
    biometric.ios_face_id_match()
    biometric.ios_face_id_no_match()

    # Android 專用
    biometric.android_fingerprint_match(finger_id=1)
```

### 19. 自動測試產生器 (核心功能)

**連接模擬器，自動抓取頁面元素，一鍵產生 Page Object + 正向/反向/邊界測試資料 + 測試案例：**

```bash
# 確保 Appium Server 啟動、模擬器開啟並停在目標頁面
python -m utils.auto_test_generator --page login --platform android
```

會自動產生 3 個檔案：

```
pages/login_page.py            ← Page Object (自動抓取 locators)
test_data/login_test_data.json ← 正向/反向/邊界測試資料
tests/test_login_auto.py       ← pytest 測試案例 (含 parametrize)
```

**自動產生的測試資料範例：**

| 類型 | 說明 | 範例 |
|------|------|------|
| **正向** | 有效資料 | email=test@example.com, password=Abc123!@# |
| **反向-空白** | 某欄位為空 | email="", password=Abc123!@# |
| **反向-XSS** | 特殊字元注入 | `<script>alert(1)</script>` |
| **反向-SQLi** | SQL injection | `' OR '1'='1` |
| **邊界-最短** | 1 字元 | email=a |
| **邊界-最長** | 256 字元 | email=aaa...aaa (256) |
| **邊界-Unicode** | 中文/Emoji | email=測試用戶名稱 |

也可以在測試中程式化使用：

```python
from utils.auto_test_generator import AutoTestGenerator

def test_scan_and_verify(self, driver):
    gen = AutoTestGenerator(driver)
    scan = gen.scan_page("settings")
    print(f"找到 {len(scan.input_fields)} 個輸入框")
    gen.generate_all("settings")  # 一鍵產生全部
```

### 20. 自訂測試報告

終端機自動輸出豐富的測試摘要（已自動啟用）：

```
============================================================
  APPIUM 測試報告摘要
============================================================

  總計:   50 個測試
  通過:   48
  失敗:   2
  跳過:   0
  通過率: 96.0%
  總耗時: 120.5 秒

  --- 失敗測試 ---
    FAIL  tests/test_login.py::TestLogin::test_login_empty  (1.23s)

  --- 最慢的測試 (Top 5) ---
    5.21s  tests/test_home.py::TestHome::test_data_loaded
    ...
============================================================
```

---

## 基礎設施（維護性 / 擴充性）

以下是讓框架「不用一直改核心就能擴充」的底層機制：

### 21. Plugin 系統 — 可插拔擴充

自訂功能放在 `plugins/` 目錄，框架啟動時自動載入，不改核心程式碼：

```python
# plugins/my_plugin.py
from core import Plugin

class MyPlugin(Plugin):
    name = "my_plugin"
    version = "1.0.0"

    def on_test_fail(self, test_name, driver, error):
        """測試失敗時做什麼"""
        driver.save_screenshot(f"/tmp/{test_name}.png")
        # 推 Slack、寫 DB、任何事...

    def on_before_action(self, page, action, locator, **kwargs):
        """每個 Page 操作前"""
        print(f"即將執行: {action} on {locator}")
```

內建 Plugin：`retry_plugin`（自動重試）、`timing_plugin`（耗時追蹤）、`fail_handler_plugin`（失敗現場保全）。

### 22. Event Bus — 事件發佈/訂閱

模組間不用互相 import，透過事件解耦：

```python
from core import event_bus

@event_bus.on("test.fail")
def on_fail(event):
    print(f"測試失敗: {event.data['test_name']}")

@event_bus.on("page.*")    # 萬用字元：所有 page 事件
def on_page_event(event):
    print(f"{event.name}: {event.data}")

# 內建事件：
# driver.created, driver.quit
# page.action.before, page.action.after, page.action.error
# test.start, test.pass, test.fail, test.skip
# screenshot.taken
```

### 23. Middleware — Page 操作前後攔截

類似 Express.js 的 middleware 概念，每個 click / input 都經過 middleware 鏈：

```python
from core import middleware_chain

@middleware_chain.use
def log_all_actions(context, next_fn):
    print(f"開始: {context.action}")
    result = next_fn()          # 呼叫下一層
    print(f"完成: {context.action}")
    return result

# 有條件的 middleware（只對 click 生效）
@middleware_chain.use_if(lambda ctx: ctx.action == "click")
def click_wait(context, next_fn):
    import time; time.sleep(0.3)   # click 前等 0.3s
    return next_fn()
```

### 24. Component 模式 — 可組合的 UI 元件

Header、TabBar、Dialog 這些共用區塊抽成 Component，任何 Page 都能用：

```python
from core import Component, ComponentDescriptor, BasePage

class HeaderComponent(Component):
    BACK_BTN = (AppiumBy.ID, "com.app:id/btn_back")
    TITLE = (AppiumBy.ID, "com.app:id/tv_title")

    def tap_back(self): self.click(self.BACK_BTN)
    def get_title(self) -> str: return self.get_text(self.TITLE)

class SettingsPage(BasePage):
    header = ComponentDescriptor(HeaderComponent)  # 宣告

    def go_back(self):
        self.header.tap_back()  # 直接使用
```

### 25. 語意化斷言 + Soft Assert

更好讀的斷言，失敗訊息自動包含上下文：

```python
from core import expect, soft_assert

def test_assertions(self, driver):
    expect(page.get_title()).to_equal("首頁")
    expect(price).to_be_greater_than(0)
    expect(items).to_have_length(5)
    expect(msg).to_contain("成功")
    expect(error).to_be_empty()

    # Soft Assert：收集全部失敗，最後一次報告
    with soft_assert() as sa:
        sa.expect(a).to_equal(1)
        sa.expect(b).to_equal(2)
        sa.expect(c).to_equal(3)
    # ↑ 如果 b 和 c 都失敗，會一次列出兩個錯誤
```

### 26. Element Cache — 元素快取加速

重複查找同一元素會自動走快取，stale 時自動重新查找：

```python
# BasePage 已內建，不用額外設定
# 快取策略：TTL 30 秒、stale 檢查、LRU 淘汰、滑動/click 自動清除

from core import element_cache

element_cache.enabled = False   # 停用快取
element_cache.clear()           # 清空
print(element_cache.stats)      # {"hits": 50, "misses": 10, "hit_rate": 0.83}
```

### 27. 多環境設定繼承

不用每個環境寫完整 config，只覆寫差異：

```bash
pytest --env staging          # 切換環境
TEST_ENV=staging pytest       # 或用環境變數
```

```
config/env/
├── base.json      ← 所有環境共用
├── dev.json       ← 覆蓋 base 的差異
├── staging.json
└── prod.json
```

```python
from core import env

url = env.get("appium_server")                # "http://staging-appium:4723"
retry = env.get("retry_count")                # 3
caps = env.get("capabilities.android")        # {...}
env.set("log_level", "DEBUG")                 # runtime 動態修改
```

### 28. 自訂 Exception 體系

每種失敗都有明確分類，不再只有 `TimeoutException`：

```python
from core import (
    ElementNotFoundError,     # 找不到元素
    ElementNotClickableError, # 無法點擊
    PageNotLoadedError,       # 頁面未載入
    DriverConnectionError,    # Appium Server 連不上
    AppiumFrameworkError,     # catch 全部框架錯誤
)

try:
    page.click(LOGIN_BTN)
except ElementNotFoundError as e:
    print(e.context)  # {"locator": (...), "timeout": 15}
except AppiumFrameworkError:
    # 攔截所有框架錯誤
    pass
```

---

## 完整目錄結構

```
appium/
├── .github/workflows/
│   └── appium-test.yml            # CI/CD pipeline
├── config/
│   ├── config.py                  # 全域設定
│   ├── android_caps.json          # Android capabilities
│   ├── ios_caps.json              # iOS capabilities
│   ├── devices.json               # 多裝置平行測試設定
│   └── env/                       # 多環境設定繼承
│       ├── base.json              # 基底 (所有環境共用)
│       ├── dev.json               # 開發環境
│       └── staging.json           # Staging 環境
├── core/                          # 框架核心
│   ├── __init__.py                # 統一匯出
│   ├── base_page.py               # Page Object 基底 (含 Cache/Middleware)
│   ├── driver_manager.py          # Driver 生命週期 (含 Event)
│   ├── component.py               # 可組合 UI 元件
│   ├── assertions.py              # 語意化斷言 + Soft Assert
│   ├── event_bus.py               # 事件發佈/訂閱
│   ├── plugin_manager.py          # Plugin 系統
│   ├── middleware.py              # 操作攔截 Middleware
│   ├── element_cache.py           # 元素快取
│   ├── env_manager.py             # 多環境設定
│   └── exceptions.py              # Exception 階層體系
├── plugins/                       # 自訂 Plugin (自動掃描)
│   ├── retry_plugin.py            # 操作失敗自動重試
│   ├── timing_plugin.py           # 操作耗時追蹤
│   └── fail_handler_plugin.py     # 失敗現場保全
├── generator/                     # 獨立產生器 (不影響框架)
│   ├── __main__.py                # CLI 入口
│   ├── engine.py                  # 核心引擎
│   ├── schema.py                  # 資料結構定義
│   ├── interactive.py             # 互動式問答
│   ├── config_builder.py          # 設定檔產生
│   ├── page_writer.py             # Page Object 產生
│   ├── test_data_writer.py        # 測試資料產生
│   └── test_writer.py             # 測試案例產生
├── pages/
│   ├── login_page.py              # 登入頁面
│   └── home_page.py               # 首頁
├── tests/
│   ├── test_login.py              # 登入測試
│   ├── test_home.py               # 首頁測試
│   ├── test_login_data_driven.py  # 資料驅動測試
│   └── test_with_decorators.py    # Decorator 範例
├── test_data/
│   └── login_data.json            # 測試資料
├── utils/                         # 工具層 (20+ 模組)
│   ├── logger.py                  # 日誌
│   ├── screenshot.py              # 截圖
│   ├── wait_helper.py             # 等待/重試
│   ├── data_loader.py             # 資料載入
│   ├── data_factory.py            # 隨機資料工廠
│   ├── api_client.py              # REST API
│   ├── decorators.py              # 自訂裝飾器
│   ├── element_helper.py          # 元素探索
│   ├── allure_helper.py           # Allure 報告
│   ├── gesture_helper.py          # 手勢操作
│   ├── app_manager.py             # App 生命週期
│   ├── device_helper.py           # 裝置控制
│   ├── perf_monitor.py            # 效能監控
│   ├── notifier.py                # Slack/Webhook
│   ├── parallel.py                # 多裝置平行
│   ├── image_compare.py           # 視覺回歸
│   ├── webview_helper.py          # WebView 切換
│   ├── log_collector.py           # 裝置 Log
│   ├── accessibility_helper.py    # 無障礙測試
│   ├── biometric_helper.py        # 生物辨識
│   ├── report_plugin.py           # 測試報告
│   └── auto_test_generator.py     # 自動掃描產生器
├── conftest.py                    # pytest fixtures + Plugin 載入
├── pytest.ini
├── requirements.txt
└── .gitignore
```
