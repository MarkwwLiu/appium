"""
生物辨識模擬工具
模擬 Touch ID / Face ID / 指紋辨識，用於測試生物驗證流程。
"""

from utils.logger import logger


class BiometricHelper:
    """模擬生物辨識（指紋 / Face ID）"""

    def __init__(self, driver):
        self.driver = driver
        self._platform = driver.capabilities.get("platformName", "").lower()

    # ── iOS: Touch ID / Face ID ──

    def ios_enroll_biometric(self) -> None:
        """iOS: 註冊生物辨識（模擬器需先啟用）"""
        if self._platform != "ios":
            logger.warning("ios_enroll_biometric 僅支援 iOS")
            return
        logger.info("[iOS] 註冊生物辨識")
        self.driver.execute_script("mobile: enrollBiometric", {"isEnabled": True})

    def ios_match_biometric(self) -> None:
        """iOS: 模擬生物辨識成功"""
        if self._platform != "ios":
            return
        logger.info("[iOS] 模擬生物辨識成功 (match)")
        self.driver.execute_script("mobile: sendBiometricMatch", {"type": "touchId", "match": True})

    def ios_no_match_biometric(self) -> None:
        """iOS: 模擬生物辨識失敗"""
        if self._platform != "ios":
            return
        logger.info("[iOS] 模擬生物辨識失敗 (no match)")
        self.driver.execute_script("mobile: sendBiometricMatch", {"type": "touchId", "match": False})

    def ios_face_id_match(self) -> None:
        """iOS: 模擬 Face ID 成功"""
        if self._platform != "ios":
            return
        logger.info("[iOS] 模擬 Face ID 成功")
        self.driver.execute_script("mobile: sendBiometricMatch", {"type": "faceId", "match": True})

    def ios_face_id_no_match(self) -> None:
        """iOS: 模擬 Face ID 失敗"""
        if self._platform != "ios":
            return
        logger.info("[iOS] 模擬 Face ID 失敗")
        self.driver.execute_script("mobile: sendBiometricMatch", {"type": "faceId", "match": False})

    # ── Android: 指紋辨識 ──

    def android_fingerprint_match(self, finger_id: int = 1) -> None:
        """
        Android: 模擬指紋辨識成功。

        Args:
            finger_id: 指紋 ID (1-10)
        """
        if self._platform != "android":
            logger.warning("android_fingerprint 僅支援 Android")
            return
        logger.info(f"[Android] 模擬指紋辨識成功 (finger_id={finger_id})")
        self.driver.finger_print(finger_id)

    # ── 跨平台便捷方法 ──

    def simulate_auth_success(self) -> None:
        """模擬生物辨識成功（自動判斷平台）"""
        if self._platform == "ios":
            self.ios_match_biometric()
        elif self._platform == "android":
            self.android_fingerprint_match()
        else:
            logger.warning(f"不支援的平台: {self._platform}")

    def simulate_auth_failure(self) -> None:
        """模擬生物辨識失敗（自動判斷平台）"""
        if self._platform == "ios":
            self.ios_no_match_biometric()
        elif self._platform == "android":
            logger.info("[Android] 模擬指紋失敗（使用無效 finger_id）")
            # Android 模擬器無直接失敗 API，可用不存在的 finger_id
            self.driver.finger_print(99)
        else:
            logger.warning(f"不支援的平台: {self._platform}")
