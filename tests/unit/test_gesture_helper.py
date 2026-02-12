"""
utils.gesture_helper 單元測試
驗證 GestureHelper 的各種手勢操作：長按、雙擊、拖放、縮放、滑動搜尋、座標點擊等。
"""

import pytest
from unittest.mock import MagicMock, patch, call

from utils.gesture_helper import GestureHelper


@pytest.fixture
def mock_driver():
    """建立模擬 driver"""
    driver = MagicMock()
    driver.get_window_size.return_value = {"width": 1080, "height": 1920}
    return driver


@pytest.fixture
def gesture(mock_driver):
    """建立 GestureHelper 實例"""
    return GestureHelper(mock_driver)


@pytest.mark.unit
class TestLongPress:
    """long_press 方法"""

    @pytest.mark.unit
    @patch("utils.gesture_helper.ActionChains")
    def test_long_press_element(self, mock_action_chains_cls, gesture):
        """長按元素：呼叫 ActionChains 的 click_and_hold、pause、release、perform"""
        element = MagicMock()
        element.text = "Submit"
        element.tag_name = "button"

        mock_chain = MagicMock()
        mock_action_chains_cls.return_value = mock_chain
        mock_chain.click_and_hold.return_value = mock_chain
        mock_chain.pause.return_value = mock_chain
        mock_chain.release.return_value = mock_chain

        gesture.long_press(element, duration_ms=2000)

        mock_action_chains_cls.assert_called_once_with(gesture.driver)
        mock_chain.click_and_hold.assert_called_once_with(element)
        mock_chain.pause.assert_called_once_with(2.0)
        mock_chain.release.assert_called_once()
        mock_chain.perform.assert_called_once()

    @pytest.mark.unit
    @patch("utils.gesture_helper.ActionChains")
    def test_long_press_default_duration(self, mock_action_chains_cls, gesture):
        """長按元素使用預設時長 1500ms"""
        element = MagicMock()
        element.text = "Hold"
        element.tag_name = "div"

        mock_chain = MagicMock()
        mock_action_chains_cls.return_value = mock_chain
        mock_chain.click_and_hold.return_value = mock_chain
        mock_chain.pause.return_value = mock_chain
        mock_chain.release.return_value = mock_chain

        gesture.long_press(element)

        mock_chain.pause.assert_called_once_with(1.5)


@pytest.mark.unit
class TestLongPressAt:
    """long_press_at 方法"""

    @pytest.mark.unit
    @patch("utils.gesture_helper.ActionBuilder")
    @patch("utils.gesture_helper.PointerInput")
    def test_long_press_at_coordinates(self, mock_pointer_cls, mock_builder_cls, gesture):
        """長按座標：建立 PointerInput 與 ActionBuilder，執行 move、down、pause、up"""
        mock_finger = MagicMock()
        mock_pointer_cls.return_value = mock_finger

        mock_builder = MagicMock()
        mock_builder_cls.return_value = mock_builder

        gesture.long_press_at(500, 800, duration_ms=2000)

        mock_pointer_cls.assert_called_once()
        mock_builder_cls.assert_called_once_with(gesture.driver, mouse=mock_finger)
        mock_builder.pointer_action.move_to_location.assert_called_once_with(500, 800)
        mock_builder.pointer_action.pointer_down.assert_called_once()
        mock_builder.pointer_action.pause.assert_called_once_with(2.0)
        mock_builder.pointer_action.pointer_up.assert_called_once()
        mock_builder.perform.assert_called_once()


@pytest.mark.unit
class TestDoubleTap:
    """double_tap 方法"""

    @pytest.mark.unit
    @patch("utils.gesture_helper.ActionChains")
    def test_double_tap_element(self, mock_action_chains_cls, gesture):
        """雙擊元素：呼叫 ActionChains 的 double_click 與 perform"""
        element = MagicMock()
        element.text = "Item"
        element.tag_name = "div"

        mock_chain = MagicMock()
        mock_action_chains_cls.return_value = mock_chain
        mock_chain.double_click.return_value = mock_chain

        gesture.double_tap(element)

        mock_action_chains_cls.assert_called_once_with(gesture.driver)
        mock_chain.double_click.assert_called_once_with(element)
        mock_chain.perform.assert_called_once()


@pytest.mark.unit
class TestDragAndDrop:
    """drag_and_drop 方法"""

    @pytest.mark.unit
    @patch("utils.gesture_helper.ActionChains")
    def test_drag_and_drop(self, mock_action_chains_cls, gesture):
        """拖放操作：呼叫 ActionChains 的 drag_and_drop 與 perform"""
        source = MagicMock()
        target = MagicMock()

        mock_chain = MagicMock()
        mock_action_chains_cls.return_value = mock_chain
        mock_chain.drag_and_drop.return_value = mock_chain

        gesture.drag_and_drop(source, target)

        mock_chain.drag_and_drop.assert_called_once_with(source, target)
        mock_chain.perform.assert_called_once()


@pytest.mark.unit
class TestDragByOffset:
    """drag_by_offset 方法"""

    @pytest.mark.unit
    @patch("utils.gesture_helper.ActionChains")
    def test_drag_by_offset(self, mock_action_chains_cls, gesture):
        """拖曳偏移：呼叫 ActionChains 的 drag_and_drop_by_offset 與 perform"""
        element = MagicMock()

        mock_chain = MagicMock()
        mock_action_chains_cls.return_value = mock_chain
        mock_chain.drag_and_drop_by_offset.return_value = mock_chain

        gesture.drag_by_offset(element, 100, -50)

        mock_chain.drag_and_drop_by_offset.assert_called_once_with(element, 100, -50)
        mock_chain.perform.assert_called_once()


@pytest.mark.unit
class TestPinch:
    """pinch 方法"""

    @pytest.mark.unit
    @patch("utils.gesture_helper.ActionBuilder")
    @patch("utils.gesture_helper.PointerInput")
    def test_pinch_with_element(self, mock_pointer_cls, mock_builder_cls, gesture):
        """有指定元素時，以元素中心進行縮小手勢"""
        element = MagicMock()
        element.rect = {"x": 100, "y": 200, "width": 400, "height": 300}

        mock_builder1 = MagicMock()
        mock_builder2 = MagicMock()
        mock_builder_cls.side_effect = [mock_builder1, mock_builder2]

        gesture.pinch(element=element, scale=0.5)

        assert mock_builder_cls.call_count == 2
        mock_builder1.perform.assert_called_once()
        mock_builder2.perform.assert_called_once()

    @pytest.mark.unit
    @patch("utils.gesture_helper.ActionBuilder")
    @patch("utils.gesture_helper.PointerInput")
    def test_pinch_without_element(self, mock_pointer_cls, mock_builder_cls, gesture):
        """未指定元素時，以畫面中央進行縮小手勢"""
        mock_builder1 = MagicMock()
        mock_builder2 = MagicMock()
        mock_builder_cls.side_effect = [mock_builder1, mock_builder2]

        gesture.pinch(element=None, scale=0.5)

        assert mock_builder_cls.call_count == 2
        mock_builder1.perform.assert_called_once()
        mock_builder2.perform.assert_called_once()


@pytest.mark.unit
class TestZoom:
    """zoom 方法"""

    @pytest.mark.unit
    @patch("utils.gesture_helper.ActionBuilder")
    @patch("utils.gesture_helper.PointerInput")
    def test_zoom_with_element(self, mock_pointer_cls, mock_builder_cls, gesture):
        """有指定元素時，以元素中心進行放大手勢"""
        element = MagicMock()
        element.rect = {"x": 100, "y": 200, "width": 400, "height": 300}

        mock_builder1 = MagicMock()
        mock_builder2 = MagicMock()
        mock_builder_cls.side_effect = [mock_builder1, mock_builder2]

        gesture.zoom(element=element, scale=2.0)

        assert mock_builder_cls.call_count == 2
        mock_builder1.perform.assert_called_once()
        mock_builder2.perform.assert_called_once()

    @pytest.mark.unit
    @patch("utils.gesture_helper.ActionBuilder")
    @patch("utils.gesture_helper.PointerInput")
    def test_zoom_without_element(self, mock_pointer_cls, mock_builder_cls, gesture):
        """未指定元素時，以畫面中央進行放大手勢"""
        mock_builder1 = MagicMock()
        mock_builder2 = MagicMock()
        mock_builder_cls.side_effect = [mock_builder1, mock_builder2]

        gesture.zoom(element=None, scale=2.0)

        assert mock_builder_cls.call_count == 2
        mock_builder1.perform.assert_called_once()
        mock_builder2.perform.assert_called_once()


@pytest.mark.unit
class TestScrollToText:
    """scroll_to_text 方法"""

    @pytest.mark.unit
    def test_found_immediately(self, gesture, mock_driver):
        """第一次就找到文字"""
        mock_element = MagicMock()
        mock_driver.find_elements.return_value = [mock_element]

        result = gesture.scroll_to_text("Settings")

        assert result is True
        mock_driver.swipe.assert_not_called()

    @pytest.mark.unit
    def test_found_after_scrolls(self, gesture, mock_driver):
        """滑動幾次後找到文字"""
        mock_element = MagicMock()
        # 前兩次找不到，第三次找到
        mock_driver.find_elements.side_effect = [[], [], [mock_element]]

        result = gesture.scroll_to_text("Settings", max_scrolls=5)

        assert result is True
        assert mock_driver.swipe.call_count == 2

    @pytest.mark.unit
    def test_not_found(self, gesture, mock_driver):
        """滑動到上限仍未找到"""
        mock_driver.find_elements.return_value = []

        result = gesture.scroll_to_text("NonExistent", max_scrolls=3)

        assert result is False
        assert mock_driver.swipe.call_count == 3


@pytest.mark.unit
class TestTapAt:
    """tap_at 方法"""

    @pytest.mark.unit
    @patch("utils.gesture_helper.ActionBuilder")
    @patch("utils.gesture_helper.PointerInput")
    def test_tap_at_coordinates(self, mock_pointer_cls, mock_builder_cls, gesture):
        """點擊座標：建立 PointerInput 與 ActionBuilder"""
        mock_finger = MagicMock()
        mock_pointer_cls.return_value = mock_finger

        mock_builder = MagicMock()
        mock_builder_cls.return_value = mock_builder

        gesture.tap_at(300, 600)

        mock_builder.pointer_action.move_to_location.assert_called_once_with(300, 600)
        mock_builder.pointer_action.pointer_down.assert_called_once()
        mock_builder.pointer_action.pause.assert_called_once_with(0.1)
        mock_builder.pointer_action.pointer_up.assert_called_once()
        mock_builder.perform.assert_called_once()


@pytest.mark.unit
class TestGetCenter:
    """_get_center 方法"""

    @pytest.mark.unit
    def test_get_center_with_element(self, gesture):
        """有元素時回傳元素中心座標"""
        element = MagicMock()
        element.rect = {"x": 100, "y": 200, "width": 400, "height": 300}

        center_x, center_y = gesture._get_center(element)

        assert center_x == 100 + 400 // 2  # 300
        assert center_y == 200 + 300 // 2  # 350

    @pytest.mark.unit
    def test_get_center_without_element(self, gesture, mock_driver):
        """無元素時回傳畫面中心座標"""
        center_x, center_y = gesture._get_center(None)

        assert center_x == 1080 // 2  # 540
        assert center_y == 1920 // 2  # 960
