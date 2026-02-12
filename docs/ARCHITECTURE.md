# 架構圖

## 系統分層架構

```mermaid
graph TB
    subgraph 測試層 ["測試層 (tests/)"]
        T1[test_login.py]
        T2[test_home.py]
        T3[test_data_driven.py]
        T4[unit tests]
    end

    subgraph 頁面層 ["頁面層 (pages/)"]
        P1[LoginPage]
        P2[HomePage]
        P3[自訂 Page...]
    end

    subgraph 核心層 ["核心層 (core/)"]
        BP[BasePage<br/>元素操作基底]
        DM[DriverManager<br/>Driver 生命週期]
        MW[Middleware<br/>操作攔截鏈]
        EC[ElementCache<br/>元素快取]
        EB[EventBus<br/>事件通訊]
        SH[SelfHealer<br/>Locator 自動修復]
        RC[Recovery<br/>異常自動恢復]
        PM[PluginManager<br/>Plugin 載入]
        EX[Exceptions<br/>自訂例外]
        RD[ResultDB<br/>結果記錄]
        PV[PageValidator<br/>頁面狀態驗證]
    end

    subgraph 工具層 ["工具層 (utils/)"]
        UL[Logger<br/>日誌]
        UD[DataLoader<br/>資料載入]
        UG[GestureHelper<br/>手勢操作]
        UW[WaitHelper<br/>等待/重試]
        US[Screenshot<br/>截圖]
        UE[ElementHelper<br/>元素輔助]
        UP[PerfMonitor<br/>效能監控]
        UN[NetworkMock<br/>網路攔截]
        UA[其他工具...]
    end

    subgraph 設定層 ["設定層 (config/)"]
        CF[Config<br/>全域設定]
        CP[capabilities JSON<br/>裝置設定]
    end

    subgraph 產生器 ["產生器 (generator/)"]
        GE[Engine<br/>產生引擎]
        GW[TestWriter<br/>測試產生]
        GP[PageWriter<br/>Page 產生]
        GX[Exporter<br/>匯出器]
    end

    subgraph 外部 ["外部依賴"]
        AP[Appium Server]
        SE[Selenium WebDriver]
        PY[pytest]
    end

    %% 連線
    T1 & T2 & T3 --> P1 & P2
    P1 & P2 & P3 --> BP
    BP --> DM
    BP --> MW
    BP --> EC
    BP --> EX
    DM --> CF
    DM --> AP
    DM --> SE
    MW --> SH
    RC --> DM
    PM --> EB
    T1 & T2 & T3 --> PY
    BP --> UL
    BP --> US
    GE --> GW & GP & GX

    style 測試層 fill:#e1f5fe
    style 頁面層 fill:#f3e5f5
    style 核心層 fill:#fff3e0
    style 工具層 fill:#e8f5e9
    style 設定層 fill:#fce4ec
    style 產生器 fill:#f1f8e9
    style 外部 fill:#eceff1
```

## 模組職責一覽

| 層級 | 目錄 | 職責 |
|------|------|------|
| **測試層** | `tests/` | 撰寫測試案例，呼叫 Page Object |
| **頁面層** | `pages/` | 定義每個畫面的元素定位與操作 |
| **核心層** | `core/` | 框架引擎：Driver、Cache、Event、Middleware、Recovery |
| **工具層** | `utils/` | 通用工具：截圖、手勢、等待、資料載入、效能監控 |
| **設定層** | `config/` | 設定管理、capabilities 定義 |
| **產生器** | `generator/` | 自動產生測試專案、匯出獨立腳本 |
| **Plugin** | `plugins/` | 可插拔擴展：失敗處理、重試、計時 |
| **掃描器** | `scanner/` | App UI 自動掃描與分析 |

## 資料流向

```mermaid
graph LR
    A[pytest 啟動] --> B[conftest.py<br/>建立 Driver]
    B --> C[測試案例<br/>呼叫 Page Object]
    C --> D[BasePage<br/>Middleware 攔截]
    D --> E[ElementCache<br/>查快取]
    E -->|miss| F[WebDriver<br/>實際操作]
    E -->|hit| G[回傳快取元素]
    F --> G
    G --> H[測試斷言]
    H -->|失敗| I[截圖 + Recovery]
    H -->|通過| J[ResultDB 記錄]
    I --> J
```
