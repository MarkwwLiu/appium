"""
core/self_healing.py 單元測試

驗證 HealRecord、SelfHealer 的關鍵字提取、候選策略產生、歷史管理。
不依賴真實 Appium driver，僅測試純邏輯部分。
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from core.self_healing import HealRecord, SelfHealer, SelfHealingMiddleware


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


# ── 新增測試類別 ──


@pytest.mark.unit
class TestSelfHealerFindElement:
    """SelfHealer.find_element 方法"""

    @pytest.mark.unit
    @patch("selenium.webdriver.support.ui.WebDriverWait")
    def test_original_locator_succeeds(self, MockWait):
        """原始 locator 成功 → 直接回傳元素"""
        driver = MagicMock()
        healer = SelfHealer(driver)

        mock_element = MagicMock()
        MockWait.return_value.until.return_value = mock_element

        result = healer.find_element(("id", "btn_login"), timeout=3.0)
        assert result is mock_element
        MockWait.return_value.until.assert_called_once()

    @pytest.mark.unit
    @patch("selenium.webdriver.support.ui.WebDriverWait")
    def test_original_fails_heal_succeeds(self, MockWait):
        """原始 locator 失敗 → 候選找到 → 修復成功"""
        driver = MagicMock()
        healer = SelfHealer(driver)

        # WebDriverWait.until 第一次（原始 locator）拋例外
        MockWait.return_value.until.side_effect = Exception("not found")

        # page_source 提供 XML 讓 _generate_candidates 產生候選
        driver.page_source = '''<hierarchy>
            <android.widget.Button text="Login" resource-id="" />
        </hierarchy>'''

        # driver.find_element 回傳 mock element（候選策略找到）
        mock_element = MagicMock()
        mock_element.is_displayed.return_value = True
        driver.find_element.return_value = mock_element

        # mock _get_page_context
        driver.current_activity = ".MainActivity"

        result = healer.find_element(("id", "com.app:id/btn_login"), timeout=2.0)
        assert result is mock_element

    @pytest.mark.unit
    @patch("selenium.webdriver.support.ui.WebDriverWait")
    def test_original_fails_heal_fails_raises(self, MockWait):
        """原始 locator 失敗 → 候選全部失敗 → 拋出例外"""
        driver = MagicMock()
        healer = SelfHealer(driver)

        MockWait.return_value.until.side_effect = Exception("original not found")

        driver.page_source = '''<hierarchy>
            <android.widget.Button text="Unrelated" />
        </hierarchy>'''

        # driver.find_element 也失敗（候選全部找不到）
        driver.find_element.side_effect = Exception("candidate not found")
        driver.current_activity = ".TestActivity"

        # Python 3 刪除 except ... as e 的變數，
        # 因此 raise original_error 可能導致 UnboundLocalError
        with pytest.raises(Exception):
            healer.find_element(("id", "com.app:id/btn_login"), timeout=2.0)

    @pytest.mark.unit
    @patch("selenium.webdriver.support.ui.WebDriverWait")
    def test_original_fails_page_source_fails_raises(self, MockWait):
        """原始 locator 失敗 → page_source 取得失敗 → 拋出例外"""
        driver = MagicMock()
        healer = SelfHealer(driver)

        MockWait.return_value.until.side_effect = Exception("element not found")

        type(driver).page_source = PropertyMock(
            side_effect=Exception("page source failed")
        )

        # page_source 失敗時嘗試 raise original_error，
        # Python 3 except as 會在區塊結束後刪除變數
        with pytest.raises(Exception):
            healer.find_element(("id", "some_id"), timeout=2.0)


@pytest.mark.unit
class TestSelfHealingMiddleware:
    """SelfHealingMiddleware"""

    @pytest.mark.unit
    def test_next_fn_succeeds(self):
        """next_fn 成功 → 直接回傳結果"""
        middleware = SelfHealingMiddleware()
        context = MagicMock()

        result = middleware(context, lambda: "success_result")
        assert result == "success_result"

    @pytest.mark.unit
    def test_non_element_error_reraises(self):
        """非元素相關錯誤 → 直接拋出"""
        middleware = SelfHealingMiddleware()
        context = MagicMock()

        def raise_value_error():
            raise ValueError("some other error")

        with pytest.raises(ValueError, match="some other error"):
            middleware(context, raise_value_error)

    @pytest.mark.unit
    @patch("core.self_healing.SelfHealer")
    def test_no_such_element_healer_click(self, MockHealerClass):
        """NoSuchElement → healer 修復 → action=click → element.click()"""
        middleware = SelfHealingMiddleware()
        middleware._healer_cache = {}

        mock_element = MagicMock()
        mock_healer = MagicMock()
        mock_healer.find_element.return_value = mock_element
        MockHealerClass.return_value = mock_healer

        driver = MagicMock()
        context = MagicMock()
        context.driver = driver
        context.locator = ("id", "btn_submit")
        context.action = "click"
        context.kwargs = {}

        class NoSuchElementException(Exception):
            pass

        def raise_no_such():
            raise NoSuchElementException("element not found")

        result = middleware(context, raise_no_such)
        assert result is mock_element
        mock_element.click.assert_called_once()
        mock_healer.find_element.assert_called_once_with(
            ("id", "btn_submit"), timeout=2.0
        )

    @pytest.mark.unit
    @patch("core.self_healing.SelfHealer")
    def test_timeout_exception_healer_input_text(self, MockHealerClass):
        """TimeoutException → healer 修復 → action=input_text → clear + send_keys"""
        middleware = SelfHealingMiddleware()
        middleware._healer_cache = {}

        mock_element = MagicMock()
        mock_healer = MagicMock()
        mock_healer.find_element.return_value = mock_element
        MockHealerClass.return_value = mock_healer

        driver = MagicMock()
        context = MagicMock()
        context.driver = driver
        context.locator = ("id", "input_name")
        context.action = "input_text"
        context.kwargs = {"text": "hello world"}

        class TimeoutException(Exception):
            pass

        def raise_timeout():
            raise TimeoutException("timeout")

        result = middleware(context, raise_timeout)
        assert result is mock_element
        mock_element.clear.assert_called_once()
        mock_element.send_keys.assert_called_once_with("hello world")

    @pytest.mark.unit
    @patch("core.self_healing.SelfHealer")
    def test_action_get_text(self, MockHealerClass):
        """action=get_text → 回傳 element.text"""
        middleware = SelfHealingMiddleware()
        middleware._healer_cache = {}

        mock_element = MagicMock()
        mock_element.text = "Hello Text"
        mock_healer = MagicMock()
        mock_healer.find_element.return_value = mock_element
        MockHealerClass.return_value = mock_healer

        driver = MagicMock()
        context = MagicMock()
        context.driver = driver
        context.locator = ("id", "tv_title")
        context.action = "get_text"
        context.kwargs = {}

        class NoSuchElementException(Exception):
            pass

        def raise_no_such():
            raise NoSuchElementException("not found")

        result = middleware(context, raise_no_such)
        assert result == "Hello Text"

    @pytest.mark.unit
    def test_no_driver_on_context_reraises(self):
        """context 沒有 driver → 直接拋出"""
        middleware = SelfHealingMiddleware()

        context = MagicMock()
        context.driver = None
        context.locator = ("id", "btn")

        class NoSuchElementException(Exception):
            pass

        def raise_no_such():
            raise NoSuchElementException("not found")

        with pytest.raises(NoSuchElementException):
            middleware(context, raise_no_such)

    @pytest.mark.unit
    def test_no_locator_on_context_reraises(self):
        """context 沒有 locator → 直接拋出"""
        middleware = SelfHealingMiddleware()

        context = MagicMock()
        context.driver = MagicMock()
        context.locator = None

        class NoSuchElementException(Exception):
            pass

        def raise_no_such():
            raise NoSuchElementException("not found")

        with pytest.raises(NoSuchElementException):
            middleware(context, raise_no_such)


@pytest.mark.unit
class TestGetPageContext:
    """SelfHealer._get_page_context"""

    @pytest.mark.unit
    def test_current_activity_returns_value(self):
        """driver.current_activity 回傳值"""
        driver = MagicMock()
        driver.current_activity = ".MainActivity"
        healer = SelfHealer(driver)

        result = healer._get_page_context()
        assert result == ".MainActivity"

    @pytest.mark.unit
    def test_current_activity_raises_returns_empty(self):
        """driver.current_activity 拋例外 → 回傳空字串"""
        driver = MagicMock()
        type(driver).current_activity = PropertyMock(
            side_effect=Exception("not available")
        )
        healer = SelfHealer(driver)

        result = healer._get_page_context()
        assert result == ""
