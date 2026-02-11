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
┌─────────────────────────────────────────────────┐
│                   pytest 測試層                   │
│            tests/test_login.py ...               │
├─────────────────────────────────────────────────┤
│                Page Object 層                     │
│     pages/login_page.py, pages/home_page.py      │
├─────────────────────────────────────────────────┤
│                   核心層 (core/)                   │
│     BasePage (通用操作)  │  DriverManager (生命週期)│
├─────────────────────────────────────────────────┤
│                  工具層 (utils/)                   │
│      Logger  │  Screenshot  │  Wait Helper        │
├─────────────────────────────────────────────────┤
│                  設定層 (config/)                  │
│       Config  │  android_caps  │  ios_caps        │
├─────────────────────────────────────────────────┤
│              Appium Python Client                 │
│                  Appium Server                    │
└─────────────────────────────────────────────────┘
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

## 擴充方向

當框架使用成熟後，可以往以下方向擴充：

| 方向 | 說明 |
|------|------|
| **資料驅動測試** | 搭配 `pytest.mark.parametrize` 或 CSV/JSON 測試資料 |
| **多裝置平行測試** | 搭配 `pytest-xdist` 在多台裝置上平行執行 |
| **API + UI 混合測試** | 用 API 建立測試資料，UI 驗證顯示 |
| **Allure 報告** | 搭配 `allure-pytest` 產生更豐富的測試報告 |
| **Docker 化** | 將 Appium Server + Android Emulator 容器化 |
