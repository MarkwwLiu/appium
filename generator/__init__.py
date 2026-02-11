"""
Appium 測試專案產生器 (Generator)

這是一個獨立模組——以本框架為引擎，根據使用者提供的資訊，
在「指定的外部目錄」自動產生完整的測試專案。

本框架的程式碼不會被改動，所有產出都寫到外部。

用法:
    python -m generator --output ~/my_app_tests

互動模式會問你：
    1. App 資訊 (package, activity, platform)
    2. 要測試哪些頁面
    3. 每個頁面有哪些元素
    4. 輸出目錄

然後一鍵產生：
    ~/my_app_tests/
    ├── config/
    ├── pages/
    ├── tests/
    ├── test_data/
    ├── conftest.py
    ├── pytest.ini
    └── requirements.txt
"""
