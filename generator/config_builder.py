"""
Config Builder
根據 AppSpec 產生測試專案的設定檔：
- config/config.py
- config/android_caps.json / ios_caps.json
- pytest.ini
- requirements.txt
- .gitignore
"""

import json
from pathlib import Path

from generator.schema import AppSpec, Platform


class ConfigBuilder:
    """產生設定檔到目標目錄"""

    def __init__(self, spec: AppSpec, output_dir: Path):
        self.spec = spec
        self.output = output_dir

    def build_all(self) -> list[Path]:
        """產生所有設定檔，回傳已建立的檔案路徑"""
        created = []
        created.append(self._write_caps())
        created.append(self._write_config_py())
        created.append(self._write_pytest_ini())
        created.append(self._write_requirements())
        created.append(self._write_gitignore())
        return created

    def _write_caps(self) -> Path:
        """產生 capabilities JSON"""
        config_dir = self.output / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        if self.spec.platform == Platform.ANDROID:
            caps = {
                "platformName": "Android",
                "appium:automationName": "UiAutomator2",
                "appium:deviceName": self.spec.device_name,
                "appium:appPackage": self.spec.package_name,
                "appium:appActivity": self.spec.activity_name,
                "appium:noReset": False,
                "appium:autoGrantPermissions": True,
            }
            if self.spec.app_path:
                caps["appium:app"] = self.spec.app_path
            path = config_dir / "android_caps.json"
        else:
            caps = {
                "platformName": "iOS",
                "appium:automationName": "XCUITest",
                "appium:deviceName": self.spec.device_name,
                "appium:bundleId": self.spec.bundle_id,
                "appium:noReset": False,
            }
            if self.spec.app_path:
                caps["appium:app"] = self.spec.app_path
            path = config_dir / "ios_caps.json"

        path.write_text(json.dumps(caps, indent=4, ensure_ascii=False), encoding="utf-8")
        return path

    def _write_config_py(self) -> Path:
        """產生 config.py"""
        config_dir = self.output / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        server_url = self.spec.appium_server
        platform = self.spec.platform.value

        code = f'''\
"""測試專案設定 — 由 generator 自動產生"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
REPORT_DIR = BASE_DIR / "reports"
SCREENSHOT_DIR = BASE_DIR / "screenshots"
LOG_DIR = BASE_DIR / "logs"

APPIUM_SERVER = "{server_url}"
DEFAULT_PLATFORM = "{platform}"

# 自動建立目錄
for d in [REPORT_DIR, SCREENSHOT_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def load_caps(platform: str = DEFAULT_PLATFORM) -> dict:
    """載入 capabilities"""
    caps_file = CONFIG_DIR / f"{{platform}}_caps.json"
    with open(caps_file, encoding="utf-8") as f:
        return json.load(f)
'''
        path = config_dir / "config.py"
        path.write_text(code, encoding="utf-8")
        return path

    def _write_pytest_ini(self) -> Path:
        """產生 pytest.ini"""
        content = f"""\
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
markers =
    smoke: 冒煙測試
    regression: 回歸測試
    negative: 反向測試
    boundary: 邊界測試
"""
        path = self.output / "pytest.ini"
        path.write_text(content, encoding="utf-8")
        return path

    def _write_requirements(self) -> Path:
        """產生 requirements.txt"""
        content = f"""\
# {self.spec.app_name} 測試專案依賴
# 自動產生 — 請根據需要調整版本

Appium-Python-Client>=4.0.0
pytest>=8.0.0
pytest-html>=4.0.0
selenium>=4.20.0
requests>=2.31.0

# 選裝
# Pillow>=10.0.0          # 視覺回歸測試
# allure-pytest>=2.13.0   # Allure 報告
# pytest-xdist>=3.5.0     # 平行測試
"""
        path = self.output / "requirements.txt"
        path.write_text(content, encoding="utf-8")
        return path

    def _write_gitignore(self) -> Path:
        """產生 .gitignore"""
        content = """\
__pycache__/
*.pyc
.pytest_cache/
reports/
screenshots/
logs/
*.log
.env
.venv/
"""
        path = self.output / ".gitignore"
        path.write_text(content, encoding="utf-8")
        return path
