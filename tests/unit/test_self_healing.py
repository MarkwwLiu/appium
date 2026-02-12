"""
core/self_healing.py 單元測試

驗證 HealRecord、SelfHealer 的關鍵字提取、候選策略產生、歷史管理。
不依賴真實 Appium driver，僅測試純邏輯部分。
"""

import pytest

from core.self_healing import HealRecord, SelfHealer


@pytest.fixture(autouse=True)
def clear_history():
    """每個測試前清空歷史"""
    SelfHealer.clear_history()
    yield
    SelfHealer.clear_history()


@pytest.mark.unit
class TestHealRecord:
    """HealRecord 資料結構"""

    @pytest.mark.unit
    def test_suggestion_format(self):
        """suggestion 包含修復後的 locator"""
        record = HealRecord(
            original_locator=("id", "old_btn"),
            healed_locator=("xpath", '//*[@text="Login"]'),
            strategy="text_match",
            page_context=".MainActivity",
        )
        s = record.suggestion
        assert "xpath" in s
        assert "Login" in s
        assert "text_match" in s

    @pytest.mark.unit
    def test_timestamp_auto_set(self):
        """timestamp 自動設定"""
        record = HealRecord(
            original_locator=("id", "x"),
            healed_locator=("id", "y"),
            strategy="test",
            page_context="",
        )
        assert record.timestamp > 0


@pytest.mark.unit
class TestSelfHealerKeywords:
    """關鍵字提取"""

    @pytest.mark.unit
    def test_extract_from_android_id(self):
        """從 Android resource-id 提取關鍵字"""
        healer = SelfHealer.__new__(SelfHealer)
        keywords = healer._extract_keywords("com.example.app:id/btn_login")
        assert "login" in keywords

    @pytest.mark.unit
    def test_extract_from_short_name(self):
        """短名稱直接當關鍵字"""
        healer = SelfHealer.__new__(SelfHealer)
        keywords = healer._extract_keywords("Login")
        assert "login" in keywords

    @pytest.mark.unit
    def test_filter_stopwords(self):
        """過濾掉太短或通用的詞"""
        healer = SelfHealer.__new__(SelfHealer)
        keywords = healer._extract_keywords("com.app:id/btn_tv_submit_form")
        # btn, tv 是 stopwords，應被過濾
        assert "btn" not in keywords
        assert "submit" in keywords
        assert "form" in keywords


@pytest.mark.unit
class TestSelfHealerCandidates:
    """候選策略產生"""

    @pytest.mark.unit
    def test_generate_from_text(self):
        """從 page source 的 text 屬性產生候選"""
        healer = SelfHealer.__new__(SelfHealer)
        page_source = '''<hierarchy>
            <android.widget.Button text="Login" resource-id="" />
        </hierarchy>'''
        candidates = healer._generate_candidates(
            ("id", "com.app:id/btn_login"), page_source
        )
        strategies = [c[0] for c in candidates]
        assert "text_match" in strategies

    @pytest.mark.unit
    def test_generate_from_content_desc(self):
        """從 content-desc 產生候選"""
        healer = SelfHealer.__new__(SelfHealer)
        page_source = '''<hierarchy>
            <android.widget.Button content-desc="Login Button" />
        </hierarchy>'''
        candidates = healer._generate_candidates(
            ("id", "com.app:id/login_action"), page_source
        )
        strategies = [c[0] for c in candidates]
        assert "content_desc" in strategies

    @pytest.mark.unit
    def test_invalid_xml_returns_empty(self):
        """XML 解析失敗回傳空列表"""
        healer = SelfHealer.__new__(SelfHealer)
        candidates = healer._generate_candidates(
            ("id", "test"), "not valid xml <<<"
        )
        assert candidates == []

    @pytest.mark.unit
    def test_deduplicate_candidates(self):
        """候選結果去重"""
        healer = SelfHealer.__new__(SelfHealer)
        page_source = '''<hierarchy>
            <android.widget.Button text="Submit" resource-id="" />
            <android.widget.Button text="Submit" resource-id="" />
        </hierarchy>'''
        candidates = healer._generate_candidates(
            ("id", "com.app:id/btn_submit"), page_source
        )
        # 相同的候選應去重
        locators = [c[1] for c in candidates]
        assert len(locators) == len(set(locators))


@pytest.mark.unit
class TestSelfHealerHistory:
    """歷史管理"""

    @pytest.mark.unit
    def test_append_history(self):
        """可新增歷史記錄"""
        record = HealRecord(("id", "a"), ("id", "b"), "test", "")
        SelfHealer._append_history(record)
        assert len(SelfHealer._heal_history) == 1

    @pytest.mark.unit
    def test_history_capacity_limit(self):
        """歷史超過上限自動裁切"""
        for i in range(SelfHealer._max_history + 50):
            record = HealRecord(("id", f"a{i}"), ("id", f"b{i}"), "test", "")
            SelfHealer._append_history(record)
        assert len(SelfHealer._heal_history) <= SelfHealer._max_history

    @pytest.mark.unit
    def test_clear_history(self):
        """clear_history 清空"""
        SelfHealer._append_history(
            HealRecord(("id", "a"), ("id", "b"), "test", "")
        )
        SelfHealer.clear_history()
        assert len(SelfHealer._heal_history) == 0

    @pytest.mark.unit
    def test_get_report_empty(self):
        """無記錄時報告為無"""
        assert "無" in SelfHealer.get_report()

    @pytest.mark.unit
    def test_get_report_with_records(self):
        """有記錄時報告包含策略和 locator"""
        SelfHealer._append_history(
            HealRecord(("id", "old"), ("xpath", "//new"), "text_match", ".Main")
        )
        report = SelfHealer.get_report()
        assert "text_match" in report
        assert "old" in report
