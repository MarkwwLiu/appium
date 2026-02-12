"""
utils.accessibility_helper 單元測試
驗證無障礙 (Accessibility) 測試工具的各項檢查功能。
"""

import pytest
from unittest.mock import MagicMock, patch


def _make_clickable_element(
    content_desc="",
    text="",
    class_name="android.widget.Button",
    resource_id="btn_id",
    bounds="[0,0][100,100]",
):
    """建立模擬的可點擊元素"""
    el = MagicMock()

    def get_attr(name):
        mapping = {
            "contentDescription": content_desc,
            "text": text,
            "className": class_name,
            "resourceId": resource_id,
            "bounds": bounds,
        }
        return mapping.get(name, "")

    el.get_attribute = MagicMock(side_effect=get_attr)
    el.text = text
    return el


def _make_text_element(text="Hello", bounds="[0,0][100,50]"):
    """建立模擬的文字元素"""
    el = MagicMock()

    def get_attr(name):
        if name == "bounds":
            return bounds
        return ""

    el.get_attribute = MagicMock(side_effect=get_attr)
    el.text = text
    return el


@pytest.mark.unit
class TestCheckContentDescriptions:
    """check_content_descriptions — 檢查 content-description"""

    @pytest.mark.unit
    def test_all_elements_have_description_pass(self):
        """所有元素都有 content-description 時 pass"""
        driver = MagicMock()
        el1 = _make_clickable_element(content_desc="按鈕1")
        el2 = _make_clickable_element(content_desc="按鈕2")
        driver.find_elements.return_value = [el1, el2]

        with patch("utils.accessibility_helper.AppiumBy") as mock_by:
            mock_by.XPATH = "xpath"
            from utils.accessibility_helper import AccessibilityHelper

            helper = AccessibilityHelper(driver)
            result = helper.check_content_descriptions()

        assert result["pass"] is True
        assert result["total"] == 2
        assert result["with_desc"] == 2
        assert result["missing_desc"] == []

    @pytest.mark.unit
    def test_elements_with_text_only_pass(self):
        """元素只有 text 沒有 contentDescription 也算通過"""
        driver = MagicMock()
        el = _make_clickable_element(content_desc="", text="點擊")
        driver.find_elements.return_value = [el]

        with patch("utils.accessibility_helper.AppiumBy") as mock_by:
            mock_by.XPATH = "xpath"
            from utils.accessibility_helper import AccessibilityHelper

            helper = AccessibilityHelper(driver)
            result = helper.check_content_descriptions()

        assert result["pass"] is True
        assert result["with_desc"] == 1

    @pytest.mark.unit
    def test_missing_description_fail(self):
        """部分元素缺少 description 時 fail"""
        driver = MagicMock()
        el_ok = _make_clickable_element(content_desc="有描述")
        el_bad = _make_clickable_element(
            content_desc="",
            text="",
            class_name="android.widget.ImageView",
            resource_id="img_no_desc",
            bounds="[10,20][30,40]",
        )
        driver.find_elements.return_value = [el_ok, el_bad]

        with patch("utils.accessibility_helper.AppiumBy") as mock_by:
            mock_by.XPATH = "xpath"
            from utils.accessibility_helper import AccessibilityHelper

            helper = AccessibilityHelper(driver)
            result = helper.check_content_descriptions()

        assert result["pass"] is False
        assert result["total"] == 2
        assert result["with_desc"] == 1
        assert len(result["missing_desc"]) == 1
        assert result["missing_desc"][0]["class"] == "android.widget.ImageView"
        assert result["missing_desc"][0]["resource_id"] == "img_no_desc"

    @pytest.mark.unit
    def test_no_clickable_elements(self):
        """頁面上沒有可點擊元素時通過"""
        driver = MagicMock()
        driver.find_elements.return_value = []

        with patch("utils.accessibility_helper.AppiumBy") as mock_by:
            mock_by.XPATH = "xpath"
            from utils.accessibility_helper import AccessibilityHelper

            helper = AccessibilityHelper(driver)
            result = helper.check_content_descriptions()

        assert result["pass"] is True
        assert result["total"] == 0

    @pytest.mark.unit
    def test_all_missing_descriptions(self):
        """所有元素都缺少描述時 fail"""
        driver = MagicMock()
        el1 = _make_clickable_element(content_desc="", text="")
        el2 = _make_clickable_element(content_desc="", text="")
        driver.find_elements.return_value = [el1, el2]

        with patch("utils.accessibility_helper.AppiumBy") as mock_by:
            mock_by.XPATH = "xpath"
            from utils.accessibility_helper import AccessibilityHelper

            helper = AccessibilityHelper(driver)
            result = helper.check_content_descriptions()

        assert result["pass"] is False
        assert len(result["missing_desc"]) == 2
        assert result["with_desc"] == 0


@pytest.mark.unit
class TestCheckTouchTargetSize:
    """check_touch_target_size — 檢查觸控區域大小"""

    @pytest.mark.unit
    def test_all_elements_large_enough_pass(self):
        """所有元素 >= 48x48 時 pass"""
        driver = MagicMock()
        el1 = _make_clickable_element(bounds="[0,0][48,48]")
        el2 = _make_clickable_element(bounds="[0,0][100,200]")
        driver.find_elements.return_value = [el1, el2]

        with patch("utils.accessibility_helper.AppiumBy") as mock_by:
            mock_by.XPATH = "xpath"
            from utils.accessibility_helper import AccessibilityHelper

            helper = AccessibilityHelper(driver)
            result = helper.check_touch_target_size()

        assert result["pass"] is True
        assert result["total"] == 2
        assert result["pass_count"] == 2
        assert result["too_small"] == []

    @pytest.mark.unit
    def test_some_elements_too_small_fail(self):
        """部分元素小於 48x48 時 fail"""
        driver = MagicMock()
        el_ok = _make_clickable_element(bounds="[0,0][100,100]")
        el_small = _make_clickable_element(
            bounds="[0,0][30,20]",
            class_name="android.widget.ImageButton",
            resource_id="small_btn",
        )
        driver.find_elements.return_value = [el_ok, el_small]

        with patch("utils.accessibility_helper.AppiumBy") as mock_by:
            mock_by.XPATH = "xpath"
            from utils.accessibility_helper import AccessibilityHelper

            helper = AccessibilityHelper(driver)
            result = helper.check_touch_target_size()

        assert result["pass"] is False
        assert result["pass_count"] == 1
        assert len(result["too_small"]) == 1
        assert result["too_small"][0]["width"] == 30
        assert result["too_small"][0]["height"] == 20

    @pytest.mark.unit
    def test_element_width_too_small_only(self):
        """元素寬度不足但高度足夠時也 fail"""
        driver = MagicMock()
        el = _make_clickable_element(bounds="[0,0][30,100]")
        driver.find_elements.return_value = [el]

        with patch("utils.accessibility_helper.AppiumBy") as mock_by:
            mock_by.XPATH = "xpath"
            from utils.accessibility_helper import AccessibilityHelper

            helper = AccessibilityHelper(driver)
            result = helper.check_touch_target_size()

        assert result["pass"] is False
        assert len(result["too_small"]) == 1
        assert result["too_small"][0]["width"] == 30
        assert result["too_small"][0]["height"] == 100

    @pytest.mark.unit
    def test_element_height_too_small_only(self):
        """元素高度不足但寬度足夠時也 fail"""
        driver = MagicMock()
        el = _make_clickable_element(bounds="[0,0][100,30]")
        driver.find_elements.return_value = [el]

        with patch("utils.accessibility_helper.AppiumBy") as mock_by:
            mock_by.XPATH = "xpath"
            from utils.accessibility_helper import AccessibilityHelper

            helper = AccessibilityHelper(driver)
            result = helper.check_touch_target_size()

        assert result["pass"] is False
        assert len(result["too_small"]) == 1

    @pytest.mark.unit
    def test_no_clickable_elements_pass(self):
        """頁面上沒有可點擊元素時通過"""
        driver = MagicMock()
        driver.find_elements.return_value = []

        with patch("utils.accessibility_helper.AppiumBy") as mock_by:
            mock_by.XPATH = "xpath"
            from utils.accessibility_helper import AccessibilityHelper

            helper = AccessibilityHelper(driver)
            result = helper.check_touch_target_size()

        assert result["pass"] is True
        assert result["total"] == 0

    @pytest.mark.unit
    def test_exactly_48x48_passes(self):
        """剛好 48x48 的元素通過檢查"""
        driver = MagicMock()
        el = _make_clickable_element(bounds="[0,0][48,48]")
        driver.find_elements.return_value = [el]

        with patch("utils.accessibility_helper.AppiumBy") as mock_by:
            mock_by.XPATH = "xpath"
            from utils.accessibility_helper import AccessibilityHelper

            helper = AccessibilityHelper(driver)
            result = helper.check_touch_target_size()

        assert result["pass"] is True
        assert result["pass_count"] == 1


@pytest.mark.unit
class TestCheckTextSize:
    """check_text_size — 檢查文字大小"""

    @pytest.mark.unit
    def test_all_text_ok_pass(self):
        """所有文字元素高度足夠時 pass"""
        driver = MagicMock()
        el1 = _make_text_element(text="大文字", bounds="[0,0][200,50]")
        el2 = _make_text_element(text="正常文字", bounds="[0,0][200,40]")
        driver.find_elements.return_value = [el1, el2]

        with patch("utils.accessibility_helper.AppiumBy") as mock_by:
            mock_by.XPATH = "xpath"
            from utils.accessibility_helper import AccessibilityHelper

            helper = AccessibilityHelper(driver)
            result = helper.check_text_size()

        assert result["pass"] is True
        assert result["total"] == 2
        assert result["possibly_too_small"] == []

    @pytest.mark.unit
    def test_some_text_too_small_fail(self):
        """部分文字元素高度不足時 fail"""
        driver = MagicMock()
        el_ok = _make_text_element(text="正常", bounds="[0,0][200,50]")
        el_small = _make_text_element(text="超小字", bounds="[0,0][200,10]")
        driver.find_elements.return_value = [el_ok, el_small]

        with patch("utils.accessibility_helper.AppiumBy") as mock_by:
            mock_by.XPATH = "xpath"
            from utils.accessibility_helper import AccessibilityHelper

            helper = AccessibilityHelper(driver)
            result = helper.check_text_size()

        assert result["pass"] is False
        assert len(result["possibly_too_small"]) == 1
        assert result["possibly_too_small"][0]["height"] == 10

    @pytest.mark.unit
    def test_custom_min_sp(self):
        """使用自訂 min_sp 參數"""
        driver = MagicMock()
        # 高度 30，min_sp=20 時 threshold=40，30<40 → too small
        el = _make_text_element(text="中等", bounds="[0,0][200,30]")
        driver.find_elements.return_value = [el]

        with patch("utils.accessibility_helper.AppiumBy") as mock_by:
            mock_by.XPATH = "xpath"
            from utils.accessibility_helper import AccessibilityHelper

            helper = AccessibilityHelper(driver)
            result = helper.check_text_size(min_sp=20)

        assert result["pass"] is False
        assert len(result["possibly_too_small"]) == 1

    @pytest.mark.unit
    def test_no_text_elements_pass(self):
        """頁面上沒有文字元素時通過"""
        driver = MagicMock()
        driver.find_elements.return_value = []

        with patch("utils.accessibility_helper.AppiumBy") as mock_by:
            mock_by.XPATH = "xpath"
            from utils.accessibility_helper import AccessibilityHelper

            helper = AccessibilityHelper(driver)
            result = helper.check_text_size()

        assert result["pass"] is True
        assert result["total"] == 0

    @pytest.mark.unit
    def test_text_truncated_to_30_chars(self):
        """過長文字被截斷為 30 字元"""
        driver = MagicMock()
        long_text = "A" * 50
        el = _make_text_element(text=long_text, bounds="[0,0][200,10]")
        driver.find_elements.return_value = [el]

        with patch("utils.accessibility_helper.AppiumBy") as mock_by:
            mock_by.XPATH = "xpath"
            from utils.accessibility_helper import AccessibilityHelper

            helper = AccessibilityHelper(driver)
            result = helper.check_text_size()

        assert len(result["possibly_too_small"][0]["text"]) == 30


@pytest.mark.unit
class TestFullAudit:
    """full_audit — 完整無障礙稽核"""

    @pytest.mark.unit
    def test_all_pass_overall_pass(self):
        """所有檢查都通過時 overall_pass 為 True"""
        driver = MagicMock()

        with patch("utils.accessibility_helper.AppiumBy") as mock_by:
            mock_by.XPATH = "xpath"
            from utils.accessibility_helper import AccessibilityHelper

            helper = AccessibilityHelper(driver)

            with patch.object(helper, "check_content_descriptions") as mock_desc, \
                 patch.object(helper, "check_touch_target_size") as mock_touch, \
                 patch.object(helper, "check_text_size") as mock_text:
                mock_desc.return_value = {"pass": True}
                mock_touch.return_value = {"pass": True}
                mock_text.return_value = {"pass": True}

                result = helper.full_audit()

        assert result["overall_pass"] is True
        assert result["content_descriptions"] == {"pass": True}
        assert result["touch_targets"] == {"pass": True}
        assert result["text_size"] == {"pass": True}

    @pytest.mark.unit
    def test_any_fail_overall_fail(self):
        """任一檢查失敗時 overall_pass 為 False"""
        driver = MagicMock()

        with patch("utils.accessibility_helper.AppiumBy") as mock_by:
            mock_by.XPATH = "xpath"
            from utils.accessibility_helper import AccessibilityHelper

            helper = AccessibilityHelper(driver)

            with patch.object(helper, "check_content_descriptions") as mock_desc, \
                 patch.object(helper, "check_touch_target_size") as mock_touch, \
                 patch.object(helper, "check_text_size") as mock_text:
                mock_desc.return_value = {"pass": True}
                mock_touch.return_value = {"pass": False}
                mock_text.return_value = {"pass": True}

                result = helper.full_audit()

        assert result["overall_pass"] is False

    @pytest.mark.unit
    def test_content_description_fail_overall_fail(self):
        """content_descriptions 失敗時 overall_pass 為 False"""
        driver = MagicMock()

        with patch("utils.accessibility_helper.AppiumBy") as mock_by:
            mock_by.XPATH = "xpath"
            from utils.accessibility_helper import AccessibilityHelper

            helper = AccessibilityHelper(driver)

            with patch.object(helper, "check_content_descriptions") as mock_desc, \
                 patch.object(helper, "check_touch_target_size") as mock_touch, \
                 patch.object(helper, "check_text_size") as mock_text:
                mock_desc.return_value = {"pass": False}
                mock_touch.return_value = {"pass": True}
                mock_text.return_value = {"pass": True}

                result = helper.full_audit()

        assert result["overall_pass"] is False

    @pytest.mark.unit
    def test_text_size_fail_overall_fail(self):
        """text_size 失敗時 overall_pass 為 False"""
        driver = MagicMock()

        with patch("utils.accessibility_helper.AppiumBy") as mock_by:
            mock_by.XPATH = "xpath"
            from utils.accessibility_helper import AccessibilityHelper

            helper = AccessibilityHelper(driver)

            with patch.object(helper, "check_content_descriptions") as mock_desc, \
                 patch.object(helper, "check_touch_target_size") as mock_touch, \
                 patch.object(helper, "check_text_size") as mock_text:
                mock_desc.return_value = {"pass": True}
                mock_touch.return_value = {"pass": True}
                mock_text.return_value = {"pass": False}

                result = helper.full_audit()

        assert result["overall_pass"] is False

    @pytest.mark.unit
    def test_all_checks_called(self):
        """full_audit 呼叫所有三個檢查方法"""
        driver = MagicMock()

        with patch("utils.accessibility_helper.AppiumBy") as mock_by:
            mock_by.XPATH = "xpath"
            from utils.accessibility_helper import AccessibilityHelper

            helper = AccessibilityHelper(driver)

            with patch.object(helper, "check_content_descriptions") as mock_desc, \
                 patch.object(helper, "check_touch_target_size") as mock_touch, \
                 patch.object(helper, "check_text_size") as mock_text:
                mock_desc.return_value = {"pass": True}
                mock_touch.return_value = {"pass": True}
                mock_text.return_value = {"pass": True}

                helper.full_audit()

                mock_desc.assert_called_once()
                mock_touch.assert_called_once()
                mock_text.assert_called_once()
