"""
scanner — 智慧頁面掃描 + 自動測試產生

流程：
    連線模擬器 → 掃描頁面 → 智慧分析元素語意 →
    自動操作 → 重新掃描 → 記錄頁面轉場 →
    輸出完整測試（Page Object + 測試資料 + 測試案例 + 流程圖）

擴充功能：
    FlowNavigator — 根據轉場圖自動導航到指定頁面
    HtmlReportGenerator — 產出豐富的 HTML 報告（含截圖、Mermaid 流程圖）

所有產出寫到外部目錄，不影響框架。
"""
