"""
utils.biometric_helper 單元測試
驗證 BiometricHelper 的生物辨識模擬功能：Touch ID / Face ID / 指紋辨識。
"""

import pytest
from unittest.mock import MagicMock, patch, call


def _make_driver(platform_name: str) -> MagicMock:
    """建立帶有指定 platformName 的模擬 driver"""
    driver = MagicMock()
    driver.capabilities = {"platformName": platform_name}
    return driver


@pytest.mark.unit
class TestBiometricHelperInit:
    """BiometricHelper 初始化"""

    @pytest.mark.unit
    def test_init_ios_platform(self):
        """iOS 平台初始化正確設定 _platform"""
        driver = _make_driver("iOS")
        from utils.biometric_helper import BiometricHelper
        helper = BiometricHelper(driver)
        assert helper._platform == "ios"
        assert helper.driver is driver

    @pytest.mark.unit
    def test_init_android_platform(self):
        """Android 平台初始化正確設定 _platform"""
        driver = _make_driver("Android")
        from utils.biometric_helper import BiometricHelper
        helper = BiometricHelper(driver)
        assert helper._platform == "android"
        assert helper.driver is driver

    @pytest.mark.unit
    def test_init_empty_platform(self):
        """缺少 platformName 時預設為空字串"""
        driver = MagicMock()
        driver.capabilities = {}
        from utils.biometric_helper import BiometricHelper
        helper = BiometricHelper(driver)
        assert helper._platform == ""

    @pytest.mark.unit
    def test_init_mixed_case_platform(self):
        """platformName 大小寫混合應正確轉為小寫"""
        driver = _make_driver("IOS")
        from utils.biometric_helper import BiometricHelper
        helper = BiometricHelper(driver)
        assert helper._platform == "ios"


@pytest.mark.unit
class TestIosEnrollBiometric:
    """ios_enroll_biometric 方法"""

    @pytest.mark.unit
    def test_ios_enroll_biometric_calls_execute_script(self):
        """iOS 平台呼叫 execute_script 註冊生物辨識"""
        driver = _make_driver("iOS")
        from utils.biometric_helper import BiometricHelper
        helper = BiometricHelper(driver)
        helper.ios_enroll_biometric()
        driver.execute_script.assert_called_once_with(
            "mobile: enrollBiometric", {"isEnabled": True}
        )

    @pytest.mark.unit
    def test_ios_enroll_biometric_non_ios_skips(self):
        """非 iOS 平台不呼叫 execute_script"""
        driver = _make_driver("Android")
        from utils.biometric_helper import BiometricHelper
        helper = BiometricHelper(driver)
        helper.ios_enroll_biometric()
        driver.execute_script.assert_not_called()


@pytest.mark.unit
class TestIosMatchBiometric:
    """ios_match_biometric 方法"""

    @pytest.mark.unit
    def test_ios_match_biometric_calls_execute_script(self):
        """iOS 平台呼叫 execute_script 模擬 Touch ID 成功"""
        driver = _make_driver("iOS")
        from utils.biometric_helper import BiometricHelper
        helper = BiometricHelper(driver)
        helper.ios_match_biometric()
        driver.execute_script.assert_called_once_with(
            "mobile: sendBiometricMatch", {"type": "touchId", "match": True}
        )

    @pytest.mark.unit
    def test_ios_match_biometric_non_ios_returns(self):
        """非 iOS 平台直接返回，不呼叫 execute_script"""
        driver = _make_driver("Android")
        from utils.biometric_helper import BiometricHelper
        helper = BiometricHelper(driver)
        helper.ios_match_biometric()
        driver.execute_script.assert_not_called()


@pytest.mark.unit
class TestIosNoMatchBiometric:
    """ios_no_match_biometric 方法"""

    @pytest.mark.unit
    def test_ios_no_match_biometric_calls_execute_script(self):
        """iOS 平台呼叫 execute_script 模擬 Touch ID 失敗"""
        driver = _make_driver("iOS")
        from utils.biometric_helper import BiometricHelper
        helper = BiometricHelper(driver)
        helper.ios_no_match_biometric()
        driver.execute_script.assert_called_once_with(
            "mobile: sendBiometricMatch", {"type": "touchId", "match": False}
        )

    @pytest.mark.unit
    def test_ios_no_match_biometric_non_ios_returns(self):
        """非 iOS 平台直接返回"""
        driver = _make_driver("Android")
        from utils.biometric_helper import BiometricHelper
        helper = BiometricHelper(driver)
        helper.ios_no_match_biometric()
        driver.execute_script.assert_not_called()


@pytest.mark.unit
class TestIosFaceIdMatch:
    """ios_face_id_match 方法"""

    @pytest.mark.unit
    def test_ios_face_id_match_calls_execute_script(self):
        """iOS 平台呼叫 execute_script 模擬 Face ID 成功"""
        driver = _make_driver("iOS")
        from utils.biometric_helper import BiometricHelper
        helper = BiometricHelper(driver)
        helper.ios_face_id_match()
        driver.execute_script.assert_called_once_with(
            "mobile: sendBiometricMatch", {"type": "faceId", "match": True}
        )

    @pytest.mark.unit
    def test_ios_face_id_match_non_ios_returns(self):
        """非 iOS 平台直接返回"""
        driver = _make_driver("Android")
        from utils.biometric_helper import BiometricHelper
        helper = BiometricHelper(driver)
        helper.ios_face_id_match()
        driver.execute_script.assert_not_called()


@pytest.mark.unit
class TestIosFaceIdNoMatch:
    """ios_face_id_no_match 方法"""

    @pytest.mark.unit
    def test_ios_face_id_no_match_calls_execute_script(self):
        """iOS 平台呼叫 execute_script 模擬 Face ID 失敗"""
        driver = _make_driver("iOS")
        from utils.biometric_helper import BiometricHelper
        helper = BiometricHelper(driver)
        helper.ios_face_id_no_match()
        driver.execute_script.assert_called_once_with(
            "mobile: sendBiometricMatch", {"type": "faceId", "match": False}
        )

    @pytest.mark.unit
    def test_ios_face_id_no_match_non_ios_returns(self):
        """非 iOS 平台直接返回"""
        driver = _make_driver("Android")
        from utils.biometric_helper import BiometricHelper
        helper = BiometricHelper(driver)
        helper.ios_face_id_no_match()
        driver.execute_script.assert_not_called()


@pytest.mark.unit
class TestAndroidFingerprintMatch:
    """android_fingerprint_match 方法"""

    @pytest.mark.unit
    def test_android_fingerprint_match_calls_finger_print(self):
        """Android 平台呼叫 finger_print 模擬指紋辨識"""
        driver = _make_driver("Android")
        from utils.biometric_helper import BiometricHelper
        helper = BiometricHelper(driver)
        helper.android_fingerprint_match(finger_id=3)
        driver.finger_print.assert_called_once_with(3)

    @pytest.mark.unit
    def test_android_fingerprint_match_default_finger_id(self):
        """預設 finger_id 為 1"""
        driver = _make_driver("Android")
        from utils.biometric_helper import BiometricHelper
        helper = BiometricHelper(driver)
        helper.android_fingerprint_match()
        driver.finger_print.assert_called_once_with(1)

    @pytest.mark.unit
    def test_android_fingerprint_match_non_android_skips(self):
        """非 Android 平台不呼叫 finger_print"""
        driver = _make_driver("iOS")
        from utils.biometric_helper import BiometricHelper
        helper = BiometricHelper(driver)
        helper.android_fingerprint_match()
        driver.finger_print.assert_not_called()


@pytest.mark.unit
class TestSimulateAuthSuccess:
    """simulate_auth_success 方法"""

    @pytest.mark.unit
    def test_simulate_auth_success_ios(self):
        """iOS 平台呼叫 ios_match_biometric"""
        driver = _make_driver("iOS")
        from utils.biometric_helper import BiometricHelper
        helper = BiometricHelper(driver)
        helper.simulate_auth_success()
        driver.execute_script.assert_called_once_with(
            "mobile: sendBiometricMatch", {"type": "touchId", "match": True}
        )

    @pytest.mark.unit
    def test_simulate_auth_success_android(self):
        """Android 平台呼叫 android_fingerprint_match"""
        driver = _make_driver("Android")
        from utils.biometric_helper import BiometricHelper
        helper = BiometricHelper(driver)
        helper.simulate_auth_success()
        driver.finger_print.assert_called_once_with(1)

    @pytest.mark.unit
    def test_simulate_auth_success_unknown_platform(self):
        """未知平台不呼叫任何 driver 方法"""
        driver = _make_driver("windows")
        from utils.biometric_helper import BiometricHelper
        helper = BiometricHelper(driver)
        helper.simulate_auth_success()
        driver.execute_script.assert_not_called()
        driver.finger_print.assert_not_called()


@pytest.mark.unit
class TestSimulateAuthFailure:
    """simulate_auth_failure 方法"""

    @pytest.mark.unit
    def test_simulate_auth_failure_ios(self):
        """iOS 平台呼叫 ios_no_match_biometric"""
        driver = _make_driver("iOS")
        from utils.biometric_helper import BiometricHelper
        helper = BiometricHelper(driver)
        helper.simulate_auth_failure()
        driver.execute_script.assert_called_once_with(
            "mobile: sendBiometricMatch", {"type": "touchId", "match": False}
        )

    @pytest.mark.unit
    def test_simulate_auth_failure_android(self):
        """Android 平台呼叫 finger_print(99) 模擬失敗"""
        driver = _make_driver("Android")
        from utils.biometric_helper import BiometricHelper
        helper = BiometricHelper(driver)
        helper.simulate_auth_failure()
        driver.finger_print.assert_called_once_with(99)

    @pytest.mark.unit
    def test_simulate_auth_failure_unknown_platform(self):
        """未知平台不呼叫任何 driver 方法"""
        driver = _make_driver("windows")
        from utils.biometric_helper import BiometricHelper
        helper = BiometricHelper(driver)
        helper.simulate_auth_failure()
        driver.execute_script.assert_not_called()
        driver.finger_print.assert_not_called()
