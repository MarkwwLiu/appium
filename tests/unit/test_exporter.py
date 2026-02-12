"""
TestExporter 單元測試

測試匯出器的依賴分析、fixture 解析、檔案複製等功能。
"""

import json
import textwrap
from pathlib import Path

import pytest

from generator.exporter import TestExporter


@pytest.fixture
def tmp_project(tmp_path):
    """建立一個模擬的測試專案結構"""
    project = tmp_path / "project"
    project.mkdir()

    # config/
    config_dir = project / "config"
    config_dir.mkdir()
    (config_dir / "__init__.py").write_text("", encoding="utf-8")
    (config_dir / "config.py").write_text(textwrap.dedent("""\
        import json
        from pathlib import Path

        BASE_DIR = Path(__file__).resolve().parent.parent
        CONFIG_DIR = Path(__file__).resolve().parent

        class Config:
            EXPLICIT_WAIT = 15
            SCREENSHOT_DIR = BASE_DIR / "screenshots"

            @classmethod
            def appium_server_url(cls):
                return "http://127.0.0.1:4723"

            @classmethod
            def load_caps(cls, platform=None):
                return {}
    """), encoding="utf-8")
    (config_dir / "android_caps.json").write_text(
        json.dumps({"platformName": "Android"}), encoding="utf-8"
    )

    # core/
    core_dir = project / "core"
    core_dir.mkdir()
    (core_dir / "__init__.py").write_text("", encoding="utf-8")
    (core_dir / "base_page.py").write_text(textwrap.dedent("""\
        from config.config import Config

        class BasePage:
            def __init__(self, driver, timeout=None):
                self.driver = driver
                self.timeout = timeout or Config.EXPLICIT_WAIT

            def find_element(self, locator):
                pass

            def click(self, locator):
                pass

            def input_text(self, locator, text):
                pass

            def get_text(self, locator):
                return ""

            def is_element_present(self, locator, timeout=3):
                return True
    """), encoding="utf-8")
    (core_dir / "exceptions.py").write_text(textwrap.dedent("""\
        class AppiumFrameworkError(Exception):
            pass
        class ElementNotFoundError(AppiumFrameworkError):
            pass
    """), encoding="utf-8")

    # pages/
    pages_dir = project / "pages"
    pages_dir.mkdir()
    (pages_dir / "__init__.py").write_text(
        "from pages.login_page import LoginPage\n", encoding="utf-8"
    )
    (pages_dir / "login_page.py").write_text(textwrap.dedent("""\
        from core.base_page import BasePage

        class LoginPage(BasePage):
            USERNAME = ("id", "username")
            PASSWORD = ("id", "password")
            LOGIN_BTN = ("id", "login")

            def enter_username(self, text):
                self.input_text(self.USERNAME, text)
                return self

            def enter_password(self, text):
                self.input_text(self.PASSWORD, text)
                return self

            def tap_login(self):
                self.click(self.LOGIN_BTN)

            def login(self, username, password):
                self.enter_username(username)
                self.enter_password(password)
                self.tap_login()

            def is_login_page_displayed(self):
                return self.is_element_present(self.LOGIN_BTN)
    """), encoding="utf-8")

    # utils/
    utils_dir = project / "utils"
    utils_dir.mkdir()
    (utils_dir / "__init__.py").write_text("", encoding="utf-8")
    (utils_dir / "logger.py").write_text(textwrap.dedent("""\
        import logging
        logger = logging.getLogger("test")
    """), encoding="utf-8")
    (utils_dir / "data_loader.py").write_text(textwrap.dedent("""\
        import json
        from pathlib import Path

        DATA_DIR = Path(__file__).resolve().parent.parent / "test_data"

        def load_json(filename):
            with open(DATA_DIR / filename, encoding="utf-8") as f:
                return json.load(f)

        def get_test_ids(data):
            return [d.get("case_id", str(i)) for i, d in enumerate(data)]
    """), encoding="utf-8")

    # test_data/
    data_dir = project / "test_data"
    data_dir.mkdir()
    (data_dir / "login_data.json").write_text(
        json.dumps([
            {"case_id": "TC001", "username": "test", "password": "pass", "expected": "success"},
        ], ensure_ascii=False),
        encoding="utf-8",
    )

    # conftest.py
    (project / "conftest.py").write_text(textwrap.dedent("""\
        import pytest

        from utils.logger import logger


        def pytest_addoption(parser):
            parser.addoption("--platform", default="android")


        @pytest.fixture(scope="session")
        def platform(request):
            return request.config.getoption("--platform")


        @pytest.fixture(scope="function")
        def driver(platform):
            logger.info(f"建立 {platform} driver")
            drv = "mock_driver"
            yield drv
            logger.info("關閉 driver")


        @pytest.fixture
        def api_client():
            from utils.data_loader import load_json
            return {"base_url": "http://localhost"}
    """), encoding="utf-8")

    # tests/
    tests_dir = project / "tests"
    tests_dir.mkdir()
    (tests_dir / "__init__.py").write_text("", encoding="utf-8")

    # 簡單測試檔
    (tests_dir / "test_login.py").write_text(textwrap.dedent("""\
        import pytest
        from pages.login_page import LoginPage

        class TestLogin:
            def test_login_success(self, driver):
                page = LoginPage(driver)
                assert page.is_login_page_displayed()
                page.login("user", "pass")
    """), encoding="utf-8")

    # 資料驅動測試檔
    (tests_dir / "test_login_data.py").write_text(textwrap.dedent("""\
        import pytest
        from pages.login_page import LoginPage
        from utils.data_loader import load_json, get_test_ids

        LOGIN_DATA = load_json("login_data.json")

        class TestLoginData:
            @pytest.mark.parametrize("data", LOGIN_DATA, ids=get_test_ids(LOGIN_DATA))
            def test_login(self, driver, data):
                page = LoginPage(driver)
                page.login(data["username"], data["password"])
    """), encoding="utf-8")

    # 使用多個 fixture 的測試
    (tests_dir / "test_multi_fixture.py").write_text(textwrap.dedent("""\
        import pytest
        from pages.login_page import LoginPage

        class TestMulti:
            def test_with_api(self, driver, api_client):
                page = LoginPage(driver)
                assert page.is_login_page_displayed()
    """), encoding="utf-8")

    return project


class TestExporterAnalyze:
    """測試依賴分析功能"""

    def test_analyze_simple_test(self, tmp_project):
        """分析簡單測試：應偵測到 pages、core、config 依賴"""
        exporter = TestExporter(
            "tests/test_login.py",
            project_root=tmp_project,
        )
        result = exporter.analyze()

        assert result["test_file"] == "tests/test_login.py"
        assert "pages.login_page" in result["local_modules"]
        assert "core.base_page" in result["local_modules"]
        assert "config.config" in result["local_modules"]
        assert "driver" in result["fixture_names"]

    def test_analyze_data_driven_test(self, tmp_project):
        """分析資料驅動測試：應偵測到 utils.data_loader 和資料檔"""
        exporter = TestExporter(
            "tests/test_login_data.py",
            project_root=tmp_project,
        )
        result = exporter.analyze()

        assert "utils.data_loader" in result["local_modules"]
        assert any("login_data.json" in f for f in result["data_files"])

    def test_analyze_multi_fixture(self, tmp_project):
        """分析多 fixture 測試：應偵測到所有 fixture 依賴"""
        exporter = TestExporter(
            "tests/test_multi_fixture.py",
            project_root=tmp_project,
        )
        result = exporter.analyze()

        assert "driver" in result["fixture_names"]
        assert "api_client" in result["fixture_names"]
        # driver 依賴 platform，所以 platform 也應該被解析
        assert "platform" in result["needed_fixtures"]
        assert "driver" in result["needed_fixtures"]
        assert "api_client" in result["needed_fixtures"]

    def test_analyze_third_party(self, tmp_project):
        """偵測第三方套件"""
        exporter = TestExporter(
            "tests/test_login.py",
            project_root=tmp_project,
        )
        result = exporter.analyze()

        # pytest 是第三方
        # logging 是標準庫，不應出現
        assert "logging" not in result["third_party"]

    def test_analyze_nonexistent_file(self, tmp_project):
        """測試檔案不存在時應拋出 FileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            TestExporter("tests/nonexistent.py", project_root=tmp_project)


class TestExporterExport:
    """測試匯出功能"""

    def test_export_simple(self, tmp_project, tmp_path):
        """匯出簡單測試：應產生完整的獨立目錄"""
        output = tmp_path / "exported"
        exporter = TestExporter(
            "tests/test_login.py",
            project_root=tmp_project,
        )
        result = exporter.export(output)

        assert Path(result["output_dir"]) == output
        assert result["summary"]["total_files"] > 0

        # 測試檔案應該存在
        assert (output / "tests" / "test_login.py").exists()
        assert (output / "tests" / "__init__.py").exists()

        # conftest 應該存在
        assert (output / "conftest.py").exists()

        # 配置檔應該存在
        assert (output / "pytest.ini").exists()
        assert (output / "requirements.txt").exists()
        assert (output / "run.sh").exists()

        # Page Object 應該被複製
        assert (output / "pages" / "login_page.py").exists()

        # core/base_page 應該被複製
        assert (output / "core" / "base_page.py").exists()

    def test_export_conftest_minimal(self, tmp_project, tmp_path):
        """匯出的 conftest 應只包含需要的 fixtures"""
        output = tmp_path / "exported"
        exporter = TestExporter(
            "tests/test_login.py",
            project_root=tmp_project,
        )
        exporter.export(output)

        conftest = (output / "conftest.py").read_text(encoding="utf-8")
        # 應包含 driver fixture
        assert "def driver" in conftest
        # 應包含 platform fixture（driver 依賴它）
        assert "def platform" in conftest

    def test_export_conftest_excludes_unused(self, tmp_project, tmp_path):
        """匯出的 conftest 不應包含未使用的 fixtures"""
        output = tmp_path / "exported"
        exporter = TestExporter(
            "tests/test_login.py",
            project_root=tmp_project,
        )
        exporter.export(output)

        conftest = (output / "conftest.py").read_text(encoding="utf-8")
        # test_login.py 不使用 api_client，所以不應出現
        assert "def api_client" not in conftest

    def test_export_with_data_files(self, tmp_project, tmp_path):
        """匯出資料驅動測試時應包含資料檔"""
        output = tmp_path / "exported"
        exporter = TestExporter(
            "tests/test_login_data.py",
            project_root=tmp_project,
        )
        exporter.export(output)

        # 資料檔應被複製
        assert (output / "test_data" / "login_data.json").exists()

    def test_export_requirements(self, tmp_project, tmp_path):
        """requirements.txt 應包含偵測到的依賴"""
        output = tmp_path / "exported"
        exporter = TestExporter(
            "tests/test_login.py",
            project_root=tmp_project,
        )
        exporter.export(output)

        reqs = (output / "requirements.txt").read_text(encoding="utf-8")
        assert "pytest" in reqs

    def test_export_run_sh(self, tmp_project, tmp_path):
        """run.sh 應包含正確的測試檔名"""
        output = tmp_path / "exported"
        exporter = TestExporter(
            "tests/test_login.py",
            project_root=tmp_project,
        )
        exporter.export(output)

        run_sh = (output / "run.sh").read_text(encoding="utf-8")
        assert "test_login.py" in run_sh

    def test_export_caps_copied(self, tmp_project, tmp_path):
        """config 被引用時，caps JSON 應被複製"""
        output = tmp_path / "exported"
        exporter = TestExporter(
            "tests/test_login.py",
            project_root=tmp_project,
        )
        exporter.export(output)

        assert (output / "config" / "android_caps.json").exists()

    def test_export_overwrites_existing(self, tmp_project, tmp_path):
        """重複匯出應覆蓋舊目錄"""
        output = tmp_path / "exported"
        output.mkdir()
        (output / "old_file.txt").write_text("old", encoding="utf-8")

        exporter = TestExporter(
            "tests/test_login.py",
            project_root=tmp_project,
        )
        exporter.export(output)

        assert not (output / "old_file.txt").exists()
        assert (output / "tests" / "test_login.py").exists()

    def test_export_init_files(self, tmp_project, tmp_path):
        """各 package 應有 __init__.py"""
        output = tmp_path / "exported"
        exporter = TestExporter(
            "tests/test_login.py",
            project_root=tmp_project,
        )
        exporter.export(output)

        assert (output / "pages" / "__init__.py").exists()
        assert (output / "core" / "__init__.py").exists()
        assert (output / "tests" / "__init__.py").exists()


class TestExporterFixtureResolution:
    """測試 fixture 依賴解析"""

    def test_transitive_deps(self, tmp_project):
        """fixture 的傳遞依賴應被正確解析"""
        exporter = TestExporter(
            "tests/test_login.py",
            project_root=tmp_project,
        )
        result = exporter.analyze()

        # test_login.py 使用 driver → 依賴 platform
        assert "driver" in result["needed_fixtures"]
        assert "platform" in result["needed_fixtures"]

    def test_multi_fixture_deps(self, tmp_project):
        """多 fixture 的依賴應都被解析"""
        exporter = TestExporter(
            "tests/test_multi_fixture.py",
            project_root=tmp_project,
        )
        result = exporter.analyze()

        assert "driver" in result["needed_fixtures"]
        assert "api_client" in result["needed_fixtures"]
        assert "platform" in result["needed_fixtures"]
