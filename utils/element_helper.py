"""
元素探索工具
在開發/除錯階段使用，可快速 dump 頁面結構與搜尋元素。
"""

import re

from appium.webdriver.common.appiumby import AppiumBy

from utils.logger import logger


class ElementHelper:
    """輔助在開發階段快速定位元素"""

    def __init__(self, driver):
        self.driver = driver

    def dump_page(self, save_to: str | None = None) -> str:
        """
        匯出頁面 XML 結構。
        可選擇儲存到檔案。
        """
        source = self.driver.page_source
        if save_to:
            with open(save_to, "w", encoding="utf-8") as f:
                f.write(source)
            logger.info(f"頁面結構已儲存至: {save_to}")
        return source

    def find_by_text(self, text: str, partial: bool = False) -> list:
        """依照文字內容搜尋元素"""
        if partial:
            xpath = f'//*[contains(@text, "{text}")]'
        else:
            xpath = f'//*[@text="{text}"]'
        elements = self.driver.find_elements(AppiumBy.XPATH, xpath)
        logger.info(f"搜尋文字 '{text}' 找到 {len(elements)} 個元素")
        return elements

    def find_by_content_desc(self, desc: str) -> list:
        """依照 content-description 搜尋"""
        elements = self.driver.find_elements(AppiumBy.ACCESSIBILITY_ID, desc)
        logger.info(f"搜尋 content-desc '{desc}' 找到 {len(elements)} 個元素")
        return elements

    def find_clickable_elements(self) -> list:
        """找出頁面上所有可點擊的元素"""
        elements = self.driver.find_elements(
            AppiumBy.XPATH, '//*[@clickable="true"]'
        )
        logger.info(f"找到 {len(elements)} 個可點擊元素")
        for i, el in enumerate(elements):
            logger.info(
                f"  [{i}] class={el.get_attribute('className')} "
                f"text={el.get_attribute('text')} "
                f"resource-id={el.get_attribute('resourceId')}"
            )
        return elements

    def find_all_ids(self) -> list[str]:
        """提取頁面中所有 resource-id"""
        source = self.driver.page_source
        ids = re.findall(r'resource-id="([^"]+)"', source)
        unique_ids = sorted(set(ids))
        logger.info(f"頁面共有 {len(unique_ids)} 個 unique resource-id")
        for rid in unique_ids:
            logger.info(f"  - {rid}")
        return unique_ids
