# 使用指南

## 快速開始

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 設定 Appium Server

```bash
# 啟動 Appium
appium --port 4723

# 或用環境變數指定
export APPIUM_HOST=127.0.0.1
export APPIUM_PORT=4723
```

### 3. 設定裝置 Capabilities

編輯 `config/android_caps.json` 或 `config/ios_caps.json`：

```json
{
    "platformName": "Android",
    "appium:automationName": "UiAutomator2",
    "appium:deviceName": "emulator-5554",
    "appium:app": "/path/to/app.apk"
}
```

### 4. 執行測試

```bash
# 跑全部
pytest

# 跑煙霧測試
pytest -m smoke

# 指定平台
pytest --platform android
pytest --platform ios

# 跑 unit test
pytest tests/unit/ -v
```

---

## 常用功能

### 撰寫新測試

```python
# tests/test_xxx.py
import pytest
from pages.login_page import LoginPage

class TestXxx:
    def test_something(self, driver):
        page = LoginPage(driver)
        page.login("user", "pass")
        assert page.is_login_page_displayed()
```

### 新增 Page Object

```python
# pages/xxx_page.py
from appium.webdriver.common.appiumby import AppiumBy
from core.base_page import BasePage

class XxxPage(BasePage):
    SOME_BUTTON = (AppiumBy.ID, "com.app:id/btn")

    def tap_button(self):
        self.click(self.SOME_BUTTON)

    def is_page_displayed(self):
        return self.is_element_present(self.SOME_BUTTON)
```

### 資料驅動測試

```python
from utils.data_loader import load_json, get_test_ids

DATA = load_json("login_data.json")

class TestDataDriven:
    @pytest.mark.parametrize("data", DATA, ids=get_test_ids(DATA))
    def test_login(self, driver, data):
        ...
```

---

## 自動產生測試專案

### 互動模式

```bash
python -m generator
```

### 從 JSON 設定檔

```bash
# 產生範例設定檔
python -m generator --example > app_spec.json

# 編輯後產生
python -m generator --spec app_spec.json --output ./my_tests
```

---

## 匯出獨立測試腳本

將某個測試檔及其所有依賴打包為獨立可執行目錄：

```bash
# 匯出
python -m generator --export tests/test_login.py --output ./exported

# 先預覽依賴（不匯出）
python -m generator --export tests/test_login.py --analyze
```

匯出結果：

```
exported/
├── conftest.py          # 最小化 fixtures
├── pytest.ini
├── requirements.txt
├── run.sh               # 一鍵執行
├── config/
├── core/
├── pages/
├── utils/
└── tests/test_login.py
```

執行匯出的測試：

```bash
cd exported
bash run.sh
# 或手動
pip install -r requirements.txt
pytest
```

---

## 可用的 pytest Fixtures

| Fixture | 說明 |
|---------|------|
| `driver` | Appium WebDriver（每個測試自動建立/銷毀） |
| `platform` | 測試平台 (`android` / `ios`) |
| `expect` | 語意斷言 `expect(val).to_equal(1)` |
| `soft_assert` | 軟斷言（收集所有失敗再一次報告） |
| `gesture` | 手勢操作（滑動、長按、雙擊） |
| `app_manager` | App 管理（安裝、重啟、deep link） |
| `device` | 裝置控制（旋轉、鍵盤、網路） |
| `network_mock` | 網路攔截 |
| `perf_monitor` | 效能監控（CPU、記憶體、電量） |
| `api_client` | REST API 測試 |
| `image_compare` | 視覺回歸測試 |
| `test_cleanup` | 測試後清理 |

完整列表見 `conftest.py`。

---

## 可用的 pytest Markers

```bash
pytest -m smoke        # 煙霧測試
pytest -m regression   # 回歸測試
pytest -m negative     # 反向測試
pytest -m boundary     # 邊界測試
pytest -m android      # Android only
pytest -m ios          # iOS only
pytest -m unit         # 框架 unit test
```

---

## 環境變數

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `APPIUM_HOST` | `127.0.0.1` | Appium Server IP |
| `APPIUM_PORT` | `4723` | Appium Server Port |
| `PLATFORM` | `android` | 預設測試平台 |
| `IMPLICIT_WAIT` | `10` | 隱式等待秒數 |
| `EXPLICIT_WAIT` | `15` | 顯式等待秒數 |
| `LOG_LEVEL` | `INFO` | 日誌等級 |
| `LOG_JSON` | `0` | 設為 `1` 啟用 JSON 結構化日誌 |
