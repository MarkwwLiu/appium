# CLAUDE.md — AI 開發規範

本文件定義 AI 協作開發的完整規範。所有 AI 行為必須遵守此規範。

---

## 一、分支與開發流程

### 1. 每個需求必須開新分支

```
分支命名: feature/<簡短描述>  或  fix/<簡短描述>
範例:     feature/add-export   fix/driver-timeout
```

- **禁止**直接在 `main` 上開發
- 一個分支 = 一個需求，不混合多個不相關的變更

### 2. 開發流程（嚴格順序）

```
需求 → 開分支 → 規劃 → 開發 → Code Review → 測試 → 使用者 Review → Merge
```

**詳細步驟：**

1. **開分支** — `git checkout -b feature/xxx`
2. **規劃需求** — 用 TodoWrite 列出任務清單，拆解為可執行步驟
3. **開發** — 遵守架構原則（見第二節），每完成一步就 commit
4. **AI 自行 Code Review** — 檢查程式碼品質（見第三節）
5. **AI 自行跑測試** — `pytest tests/unit/ -v`，失敗就修，最多重試 3 次
6. **提交使用者 Review** — 把結果整理清楚交給使用者
7. **使用者決定**：
   - ✅ 同意 → merge to main
   - ❌ 不同意 → 回到步驟 3 繼續修改，再跑步驟 4-6

**循環直到使用者同意為止，不可自行決定跳過任何步驟。**

---

## 二、架構原則

所有程式碼必須遵守三大原則：

### 維護性 (Maintainability)
- 單一職責：一個模組/類別只做一件事
- 錯誤處理：使用框架自訂 Exception（`core/exceptions.py`）
- 設定集中：所有設定走 `config/config.py`，不硬編碼

### 擴充性 (Extensibility)
- Page Object Pattern：所有頁面繼承 `BasePage`
- Plugin 機制：擴展功能透過 `plugins/` 目錄
- Event Bus：模組間通訊用事件，不直接耦合
- Middleware：操作攔截用 middleware chain

### 可讀性 (Readability)
- 函式/類別用中文 docstring 說明用途
- 變數命名清楚，不用縮寫
- 保持模組職責分明，參考現有目錄結構

---

## 三、Code Review 檢查清單

AI 提交使用者 Review 前，必須自行完成以下檢查：

- [ ] 沒有引入安全漏洞（注入、硬編碼密碼等）
- [ ] 沒有破壞現有功能（所有 unit test 通過）
- [ ] 遵守現有 import 風格（絕對路徑 import）
- [ ] 新功能有對應的 unit test
- [ ] 沒有多餘的 print / debug 程式碼
- [ ] commit message 清楚描述「做了什麼」和「為什麼」

---

## 四、測試規範

### 測試環境

- 預設使用**模擬器（Emulator / Simulator）** 執行測試
- Android 用 AVD emulator，iOS 用 Xcode Simulator
- 不依賴實體裝置

### 自動測試要求

- 每個新功能/修改**必須**有對應的 unit test
- 測試檔案放在 `tests/unit/test_<模組名>.py`
- 測試命名：`test_<功能>_<情境>`

### AI 實作測試的規則

1. AI 需要自行決定：
   - 需要哪些測試案例（正向/反向/邊界）
   - 每個案例需要的測試數量
   - 測試需要的資料與情境
2. 開發完成後執行 `pytest tests/unit/ -v`
3. 如果有失敗：
   - 自行分析錯誤原因
   - 自行修復程式碼或測試
   - 重新執行
4. **最多重試 3 次**，3 次後仍失敗則：
   - 整理錯誤報告
   - 列出已嘗試的修復方案
   - 交給使用者決定，**不可自行跳過，不可向使用者求助**
5. 測試通過後，接續正常流程（Code Review → 使用者 Review）

### 測試執行指令

```bash
# 跑全部 unit test
pytest tests/unit/ -v

# 跑特定測試
pytest tests/unit/test_exporter.py -v

# 跑帶覆蓋率
pytest tests/unit/ -v --cov=core --cov=utils --cov=generator
```

---

## 五、Commit 規範

```
<類型>：<簡短描述>

<詳細說明（選填）>
```

**類型：**
- `feat`：新功能
- `fix`：修 bug
- `test`：新增/修改測試
- `refactor`：重構（不改變功能）
- `docs`：文件

**範例：**
```
feat：新增測試案例匯出器

- 使用 AST 解析 import 依賴鏈
- 自動產生最小化 conftest.py
- 支援 --export CLI 指令
```

---

## 六、目錄結構（不可隨意新增頂層目錄）

```
appium/
├── config/         # 設定與 capabilities
├── core/           # 框架核心（BasePage、Driver、Cache、Event 等）
├── pages/          # Page Object 定義
├── tests/          # 測試案例
│   └── unit/       # 單元測試
├── utils/          # 工具模組
├── plugins/        # Plugin 擴展
├── generator/      # 測試專案產生器 + 匯出器
├── scanner/        # App 掃描器
├── test_data/      # 測試資料 (JSON/CSV/YAML)
├── docs/           # 文件（架構圖、流程圖、使用指南）
├── conftest.py     # 全域 pytest fixtures
├── pytest.ini      # pytest 設定
└── CLAUDE.md       # 本文件（AI 開發規範）
```

---

## 七、與使用者溝通格式

每次提交 Review 時，使用以下格式：

```
## 變更摘要
- 做了什麼（條列）

## 修改的檔案
- 檔案路徑：簡短說明

## 測試結果
- X 個測試通過 / Y 個失敗
- 覆蓋率（如果有跑）

## 待使用者確認
- 需要使用者決定的事項（如果有）
```
