# 開發流程圖

## AI 協作開發流程

```mermaid
flowchart TD
    START([使用者提出需求]) --> BRANCH[建立 feature 分支]
    BRANCH --> PLAN[規劃需求<br/>拆解任務清單]
    PLAN --> DEV[開發實作<br/>遵守架構三原則]
    DEV --> COMMIT[Commit 變更]
    COMMIT --> CR{AI Code Review<br/>檢查清單全過？}

    CR -->|有問題| DEV
    CR -->|通過| TEST[執行 pytest]

    TEST --> PASS{測試通過？}
    PASS -->|失敗| RETRY{重試次數 < 3？}
    RETRY -->|是| FIX[分析錯誤<br/>修復程式碼] --> TEST
    RETRY -->|否| REPORT[整理錯誤報告<br/>交給使用者]
    REPORT --> USER

    PASS -->|全部通過| SUMMARY[整理變更摘要<br/>修改檔案 + 測試結果]
    SUMMARY --> USER{使用者 Review}

    USER -->|不同意| FEEDBACK[接收回饋] --> DEV
    USER -->|同意| MERGE[Merge to main]
    MERGE --> DONE([完成])

    style START fill:#4caf50,color:#fff
    style DONE fill:#4caf50,color:#fff
    style MERGE fill:#2196f3,color:#fff
    style USER fill:#ff9800,color:#fff
    style CR fill:#9c27b0,color:#fff
    style TEST fill:#f44336,color:#fff
```

## 流程規則

### 不可跳過的步驟

| 步驟 | 說明 | 跳過後果 |
|------|------|----------|
| 開分支 | 每個需求獨立分支 | 程式碼混亂無法回溯 |
| 規劃 | TodoWrite 列出清單 | 遺漏需求、方向錯誤 |
| Code Review | AI 自行檢查品質 | 低品質程式碼流入 |
| 跑測試 | pytest 驗證正確性 | 破壞現有功能 |
| 使用者 Review | 使用者最終決定 | 不符合使用者預期 |

### 重試規則

```mermaid
flowchart LR
    F1[第 1 次失敗] -->|分析 + 修復| R1[重試 1]
    R1 -->|仍失敗| F2[第 2 次失敗]
    F2 -->|換方案 + 修復| R2[重試 2]
    R2 -->|仍失敗| F3[第 3 次失敗]
    F3 -->|整理報告| STOP[交給使用者決定]

    style STOP fill:#f44336,color:#fff
```

- 第 1 次：分析錯誤，直接修復
- 第 2 次：換一個思路或方案
- 第 3 次：最後嘗試，仍失敗就停止
- 超過 3 次：**禁止繼續自行嘗試**，必須整理報告交給使用者

## Merge 條件

以下條件**全部滿足**才能 merge：

1. AI Code Review 檢查清單全部通過
2. `pytest tests/unit/ -v` 全部綠燈
3. 使用者明確表示同意
