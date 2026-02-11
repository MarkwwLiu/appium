"""
手勢操作工具
封裝 Appium 的進階手勢：長按、雙擊、拖放、縮放等。
"""

from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput

from utils.logger import logger


class GestureHelper:
    """進階手勢操作"""

    def __init__(self, driver):
        self.driver = driver

    def long_press(self, element, duration_ms: int = 1500) -> None:
        """長按元素"""
        logger.info(f"長按元素: {element.text or element.tag_name} ({duration_ms}ms)")
        actions = ActionChains(self.driver)
        actions.click_and_hold(element).pause(duration_ms / 1000).release().perform()

    def long_press_at(self, x: int, y: int, duration_ms: int = 1500) -> None:
        """長按座標"""
        logger.info(f"長按座標 ({x}, {y}) ({duration_ms}ms)")
        finger = PointerInput(interaction.POINTER_TOUCH, "finger")
        actions = ActionBuilder(self.driver, mouse=finger)
        actions.pointer_action.move_to_location(x, y)
        actions.pointer_action.pointer_down()
        actions.pointer_action.pause(duration_ms / 1000)
        actions.pointer_action.pointer_up()
        actions.perform()

    def double_tap(self, element) -> None:
        """雙擊元素"""
        logger.info(f"雙擊元素: {element.text or element.tag_name}")
        actions = ActionChains(self.driver)
        actions.double_click(element).perform()

    def drag_and_drop(self, source, target) -> None:
        """從 source 元素拖曳到 target 元素"""
        logger.info("執行拖放操作")
        actions = ActionChains(self.driver)
        actions.drag_and_drop(source, target).perform()

    def drag_by_offset(self, element, x_offset: int, y_offset: int) -> None:
        """拖曳元素到指定偏移量"""
        logger.info(f"拖曳偏移 ({x_offset}, {y_offset})")
        actions = ActionChains(self.driver)
        actions.drag_and_drop_by_offset(element, x_offset, y_offset).perform()

    def pinch(self, element=None, scale: float = 0.5) -> None:
        """
        縮小手勢 (雙指向內捏合)。
        若未指定 element，則在畫面中央操作。
        """
        logger.info(f"縮小手勢 (scale={scale})")
        center_x, center_y = self._get_center(element)
        offset = int(min(center_x, center_y) * 0.3)

        finger1 = PointerInput(interaction.POINTER_TOUCH, "finger1")
        finger2 = PointerInput(interaction.POINTER_TOUCH, "finger2")

        actions1 = ActionBuilder(self.driver, mouse=finger1)
        actions1.pointer_action.move_to_location(center_x - offset, center_y)
        actions1.pointer_action.pointer_down()
        actions1.pointer_action.move_to_location(center_x - int(offset * scale), center_y)
        actions1.pointer_action.pointer_up()

        actions2 = ActionBuilder(self.driver, mouse=finger2)
        actions2.pointer_action.move_to_location(center_x + offset, center_y)
        actions2.pointer_action.pointer_down()
        actions2.pointer_action.move_to_location(center_x + int(offset * scale), center_y)
        actions2.pointer_action.pointer_up()

        actions1.perform()
        actions2.perform()

    def zoom(self, element=None, scale: float = 2.0) -> None:
        """
        放大手勢 (雙指向外展開)。
        若未指定 element，則在畫面中央操作。
        """
        logger.info(f"放大手勢 (scale={scale})")
        center_x, center_y = self._get_center(element)
        start_offset = int(min(center_x, center_y) * 0.1)
        end_offset = int(start_offset * scale)

        finger1 = PointerInput(interaction.POINTER_TOUCH, "finger1")
        finger2 = PointerInput(interaction.POINTER_TOUCH, "finger2")

        actions1 = ActionBuilder(self.driver, mouse=finger1)
        actions1.pointer_action.move_to_location(center_x - start_offset, center_y)
        actions1.pointer_action.pointer_down()
        actions1.pointer_action.move_to_location(center_x - end_offset, center_y)
        actions1.pointer_action.pointer_up()

        actions2 = ActionBuilder(self.driver, mouse=finger2)
        actions2.pointer_action.move_to_location(center_x + start_offset, center_y)
        actions2.pointer_action.pointer_down()
        actions2.pointer_action.move_to_location(center_x + end_offset, center_y)
        actions2.pointer_action.pointer_up()

        actions1.perform()
        actions2.perform()

    def scroll_to_text(self, text: str, max_scrolls: int = 5) -> bool:
        """
        向下滑動直到找到指定文字。

        Returns:
            是否找到該文字
        """
        logger.info(f"滑動搜尋文字: '{text}'")
        for i in range(max_scrolls):
            elements = self.driver.find_elements(
                AppiumBy.XPATH, f'//*[contains(@text, "{text}")]'
            )
            if elements:
                logger.info(f"第 {i + 1} 次滑動後找到文字")
                return True
            size = self.driver.get_window_size()
            self.driver.swipe(
                size["width"] // 2,
                int(size["height"] * 0.7),
                size["width"] // 2,
                int(size["height"] * 0.3),
                600,
            )
        logger.warning(f"滑動 {max_scrolls} 次仍未找到文字: '{text}'")
        return False

    def tap_at(self, x: int, y: int) -> None:
        """點擊指定座標"""
        logger.info(f"點擊座標 ({x}, {y})")
        finger = PointerInput(interaction.POINTER_TOUCH, "finger")
        actions = ActionBuilder(self.driver, mouse=finger)
        actions.pointer_action.move_to_location(x, y)
        actions.pointer_action.pointer_down()
        actions.pointer_action.pause(0.1)
        actions.pointer_action.pointer_up()
        actions.perform()

    def _get_center(self, element=None) -> tuple[int, int]:
        """取得元素或螢幕中心座標"""
        if element:
            rect = element.rect
            return rect["x"] + rect["width"] // 2, rect["y"] + rect["height"] // 2
        size = self.driver.get_window_size()
        return size["width"] // 2, size["height"] // 2
