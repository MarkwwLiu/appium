"""
無障礙 (Accessibility) 測試工具
驗證 App 的無障礙標準合規性：content-description、對比度、可點擊區域大小等。
"""

import re

from appium.webdriver.common.appiumby import AppiumBy

from utils.logger import logger


class AccessibilityHelper:
    """App 無障礙合規性檢查"""

    # Android 最小可點擊區域 (dp)，Google 建議 48x48
    MIN_TOUCH_TARGET_DP = 48

    def __init__(self, driver):
        self.driver = driver

    def check_content_descriptions(self) -> dict:
        """
        檢查頁面上可互動元素是否都有 content-description。

        Returns:
            {
                "total": int,
                "with_desc": int,
                "missing_desc": list[dict],
                "pass": bool,
            }
        """
        clickable = self.driver.find_elements(
            AppiumBy.XPATH, '//*[@clickable="true"]'
        )

        missing = []
        with_desc = 0

        for el in clickable:
            desc = el.get_attribute("contentDescription") or ""
            text = el.get_attribute("text") or ""

            if desc or text:
                with_desc += 1
            else:
                missing.append({
                    "class": el.get_attribute("className"),
                    "resource_id": el.get_attribute("resourceId") or "N/A",
                    "bounds": el.get_attribute("bounds"),
                })

        result = {
            "total": len(clickable),
            "with_desc": with_desc,
            "missing_desc": missing,
            "pass": len(missing) == 0,
        }

        if missing:
            logger.warning(
                f"無障礙檢查: {len(missing)}/{len(clickable)} 個可點擊元素"
                f"缺少 content-description"
            )
            for item in missing:
                logger.warning(f"  - {item['class']} ({item['resource_id']})")
        else:
            logger.info("無障礙檢查: 所有可點擊元素都有 content-description")

        return result

    def check_touch_target_size(self) -> dict:
        """
        檢查可點擊元素是否符合最小觸控區域標準 (48x48 dp)。

        Returns:
            {
                "total": int,
                "pass_count": int,
                "too_small": list[dict],
                "pass": bool,
            }
        """
        clickable = self.driver.find_elements(
            AppiumBy.XPATH, '//*[@clickable="true"]'
        )

        too_small = []
        pass_count = 0

        for el in clickable:
            bounds = el.get_attribute("bounds") or ""
            match = re.findall(r"\d+", bounds)
            if len(match) == 4:
                x1, y1, x2, y2 = map(int, match)
                w = x2 - x1
                h = y2 - y1
                if w >= self.MIN_TOUCH_TARGET_DP and h >= self.MIN_TOUCH_TARGET_DP:
                    pass_count += 1
                else:
                    too_small.append({
                        "class": el.get_attribute("className"),
                        "resource_id": el.get_attribute("resourceId") or "N/A",
                        "width": w,
                        "height": h,
                    })

        result = {
            "total": len(clickable),
            "pass_count": pass_count,
            "too_small": too_small,
            "pass": len(too_small) == 0,
        }

        if too_small:
            logger.warning(
                f"觸控區域檢查: {len(too_small)} 個元素小於 "
                f"{self.MIN_TOUCH_TARGET_DP}x{self.MIN_TOUCH_TARGET_DP}"
            )
            for item in too_small:
                logger.warning(
                    f"  - {item['class']} ({item['resource_id']}) "
                    f"= {item['width']}x{item['height']}"
                )
        else:
            logger.info("觸控區域檢查: 全部通過")

        return result

    def check_text_size(self, min_sp: int = 12) -> dict:
        """
        檢查頁面上文字元素的字體大小是否符合最小標準。
        注意：此方法透過元素高度估算，非精確值。

        Returns:
            {
                "total": int,
                "possibly_too_small": list[dict],
                "pass": bool,
            }
        """
        text_elements = self.driver.find_elements(
            AppiumBy.XPATH, '//*[@text!=""]'
        )

        small_texts = []
        for el in text_elements:
            bounds = el.get_attribute("bounds") or ""
            match = re.findall(r"\d+", bounds)
            if len(match) == 4:
                _, y1, _, y2 = map(int, match)
                height = y2 - y1
                # 粗略估算：元素高度小於 min_sp 的 2 倍可能太小
                if height < min_sp * 2:
                    small_texts.append({
                        "text": (el.text or "")[:30],
                        "height": height,
                    })

        result = {
            "total": len(text_elements),
            "possibly_too_small": small_texts,
            "pass": len(small_texts) == 0,
        }
        return result

    def full_audit(self) -> dict:
        """
        完整無障礙稽核，執行所有檢查。

        Returns:
            {
                "content_descriptions": {...},
                "touch_targets": {...},
                "text_size": {...},
                "overall_pass": bool,
            }
        """
        logger.info("===== 開始無障礙稽核 =====")
        desc = self.check_content_descriptions()
        touch = self.check_touch_target_size()
        text = self.check_text_size()

        overall = desc["pass"] and touch["pass"] and text["pass"]
        logger.info(f"===== 無障礙稽核結果: {'PASS' if overall else 'FAIL'} =====")

        return {
            "content_descriptions": desc,
            "touch_targets": touch,
            "text_size": text,
            "overall_pass": overall,
        }
