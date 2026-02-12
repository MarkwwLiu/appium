"""
測試案例匯出器 (Test Case Exporter)

將指定的測試檔案及其所有依賴（Page Objects、工具、設定、fixtures）
打包匯出為一個獨立可執行的「拋棄式腳本」目錄。

匯出後的目錄結構：
    exported_test/
    ├── conftest.py          # 最小化 fixtures（僅包含該測試需要的）
    ├── pytest.ini
    ├── requirements.txt
    ├── run.sh               # 一鍵執行腳本
    ├── config/
    │   ├── __init__.py
    │   └── config.py        # 獨立設定
    ├── core/                # 僅包含被引用的核心模組
    ├── pages/               # 僅包含被引用的 Page Objects
    ├── utils/               # 僅包含被引用的工具
    ├── test_data/           # 若有引用到的測試資料
    └── tests/
        ├── __init__.py
        └── test_xxx.py      # 目標測試檔案

用法：
    # CLI
    python -m generator --export tests/test_login.py --output ./exported

    # 程式化呼叫
    from generator.exporter import TestExporter
    exporter = TestExporter("tests/test_login.py")
    exporter.export("./exported")
"""

import ast
import json
import re
import shutil
from pathlib import Path
from textwrap import dedent


# 框架根目錄
_FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent

# 框架內部套件名稱（用來判斷是 local import 還是 third-party）
_LOCAL_PACKAGES = {"core", "pages", "utils", "config", "plugins", "generator", "scanner"}

# 第三方套件對應 pip 套件名
_PIP_MAPPING = {
    "appium": "Appium-Python-Client>=4.0.0",
    "selenium": "selenium>=4.20.0",
    "pytest": "pytest>=8.0.0",
    "allure": "allure-pytest>=2.13.0",
    "allure_commons": "allure-pytest>=2.13.0",
    "yaml": "PyYAML>=6.0",
    "requests": "requests>=2.31.0",
    "PIL": "Pillow>=10.0.0",
    "cv2": "opencv-python>=4.8.0",
}


class TestExporter:
    """
    測試案例匯出器

    分析一個測試檔案的所有依賴，然後將所有相關檔案
    複製到獨立目錄，產生可直接執行的獨立測試包。
    """

    def __init__(self, test_file: str, project_root: str | Path | None = None):
        """
        Args:
            test_file: 目標測試檔案路徑（相對於專案根目錄或絕對路徑）
            project_root: 專案根目錄（預設為框架根目錄）
        """
        self.project_root = Path(project_root or _FRAMEWORK_ROOT).resolve()
        test_path = Path(test_file)
        if not test_path.is_absolute():
            test_path = self.project_root / test_path
        self.test_file = test_path.resolve()

        if not self.test_file.exists():
            raise FileNotFoundError(f"找不到測試檔案: {self.test_file}")

        # 收集結果
        self._local_modules: set[str] = set()   # 需要複製的 local 模組
        self._third_party: set[str] = set()      # 第三方套件 top-level 名稱
        self._fixture_names: set[str] = set()    # 測試用到的 fixture 名稱
        self._data_files: set[Path] = set()      # 引用到的資料檔案
        self._visited: set[str] = set()          # 已掃描的模組（避免迴圈）

    def export(self, output_dir: str | Path) -> dict:
        """
        執行匯出。

        Args:
            output_dir: 匯出目標目錄

        Returns:
            {"output_dir": str, "files": list[str], "summary": dict}
        """
        output = Path(output_dir).resolve()
        if output.exists():
            shutil.rmtree(output)
        output.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*60}")
        print(f"  測試案例匯出器 (Test Exporter)")
        print(f"  來源: {self.test_file.relative_to(self.project_root)}")
        print(f"  輸出: {output}")
        print(f"{'='*60}\n")

        # 1. 分析依賴
        print("[1/5] 分析依賴...")
        self._analyze_file(self.test_file)
        print(f"  找到 {len(self._local_modules)} 個本地模組")
        print(f"  找到 {len(self._third_party)} 個第三方套件")
        print(f"  找到 {len(self._fixture_names)} 個 fixture 參數")

        # 2. 分析 conftest fixtures
        print("\n[2/5] 分析 conftest fixtures...")
        fixture_map = self._parse_conftest_fixtures()
        needed_fixtures = self._resolve_fixtures(fixture_map)
        print(f"  需要 {len(needed_fixtures)} 個 fixtures")

        # 3. 複製檔案
        print("\n[3/5] 複製檔案...")
        created_files = self._copy_files(output, needed_fixtures, fixture_map)

        # 4. 產生配置檔
        print("\n[4/5] 產生配置檔...")
        created_files.extend(self._generate_configs(output))

        # 5. 偵測並複製資料檔案
        print("\n[5/5] 複製資料檔案...")
        created_files.extend(self._copy_data_files(output))

        summary = {
            "local_modules": len(self._local_modules),
            "third_party": len(self._third_party),
            "fixtures": len(needed_fixtures),
            "total_files": len(created_files),
        }

        print(f"\n{'='*60}")
        print(f"  匯出完成！")
        print(f"  目錄:       {output}")
        print(f"  檔案數:     {summary['total_files']}")
        print(f"  本地模組:   {summary['local_modules']}")
        print(f"  第三方套件: {summary['third_party']}")
        print(f"  Fixtures:   {summary['fixtures']}")
        print(f"")
        print(f"  使用方式:")
        print(f"    cd {output}")
        print(f"    pip install -r requirements.txt")
        print(f"    pytest")
        print(f"    # 或 bash run.sh")
        print(f"{'='*60}\n")

        return {
            "output_dir": str(output),
            "files": created_files,
            "summary": summary,
        }

    # ── 依賴分析 ──

    def _analyze_file(self, filepath: Path) -> None:
        """遞迴解析檔案的 import，分類為 local / third-party"""
        rel = self._get_module_name(filepath)
        if rel in self._visited:
            return
        self._visited.add(rel)

        try:
            source = filepath.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(filepath))
        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"  警告: 無法解析 {filepath}: {e}")
            return

        # 提取 fixture 名稱（從測試函式參數）
        self._extract_fixture_params(tree)

        # 偵測資料檔案引用
        self._detect_data_files(source, filepath)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._classify_import(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self._classify_import(node.module)

    def _classify_import(self, module_name: str) -> None:
        """分類 import：local 還是 third-party"""
        top_level = module_name.split(".")[0]

        if top_level in _LOCAL_PACKAGES:
            self._local_modules.add(module_name)
            # 遞迴分析此模組的依賴
            mod_path = self._module_to_path(module_name)
            if mod_path and mod_path.exists():
                self._analyze_file(mod_path)
        elif top_level not in {"os", "sys", "json", "time", "re", "typing",
                                "pathlib", "dataclasses", "enum", "abc",
                                "functools", "collections", "copy", "math",
                                "datetime", "hashlib", "threading", "signal",
                                "subprocess", "urllib", "csv", "io",
                                "contextlib", "inspect", "sqlite3",
                                "traceback", "textwrap", "shutil",
                                "tempfile", "unittest", "logging",
                                "__future__", "itertools", "operator",
                                "string", "struct", "socket", "uuid",
                                "importlib", "pkgutil", "types", "weakref",
                                "warnings", "numbers", "decimal", "fractions",
                                "random", "statistics", "glob", "fnmatch",
                                "configparser", "argparse", "gettext",
                                "pprint", "difflib", "html", "xml",
                                "http", "email", "base64", "binascii",
                                "platform", "multiprocessing", "concurrent",
                                "asyncio", "queue", "sched", "array"}:
            self._third_party.add(top_level)

    def _module_to_path(self, module_name: str) -> Path | None:
        """將模組名轉為檔案路徑"""
        parts = module_name.split(".")
        # 嘗試 package (目錄 + __init__.py)
        pkg_path = self.project_root / Path(*parts) / "__init__.py"
        if pkg_path.exists():
            return pkg_path
        # 嘗試 module (.py 檔)
        mod_path = self.project_root / Path(*parts[:-1]) / f"{parts[-1]}.py" if len(parts) > 1 else self.project_root / f"{parts[0]}.py"
        if mod_path.exists():
            return mod_path
        # 嘗試整個 path 當成 package
        mod_path2 = self.project_root / Path(*parts).with_suffix(".py")
        if mod_path2.exists():
            return mod_path2
        return None

    def _get_module_name(self, filepath: Path) -> str:
        """將檔案路徑轉為模組名"""
        try:
            rel = filepath.relative_to(self.project_root)
            parts = list(rel.parts)
            if parts[-1] == "__init__.py":
                parts = parts[:-1]
            elif parts[-1].endswith(".py"):
                parts[-1] = parts[-1][:-3]
            return ".".join(parts)
        except ValueError:
            return str(filepath)

    def _extract_fixture_params(self, tree: ast.AST) -> None:
        """從測試函式的參數中提取 fixture 名稱"""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("test_"):
                    for arg in node.args.args:
                        name = arg.arg
                        if name != "self":
                            self._fixture_names.add(name)

    def _detect_data_files(self, source: str, filepath: Path) -> None:
        """偵測程式碼中引用的資料檔案"""
        # 匹配 load_json("xxx.json"), load_data("xxx"), open("xxx.json") 等
        patterns = [
            r'load_json\(["\']([^"\']+)["\']\)',
            r'load_csv\(["\']([^"\']+)["\']\)',
            r'load_yaml\(["\']([^"\']+)["\']\)',
            r'load_data\(["\']([^"\']+)["\']\)',
            r'_load_data\(["\']([^"\']+)["\']\)',
            r'open\(["\']([^"\']+\.(?:json|csv|yaml|yml))["\']\)',
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, source):
                data_file = match.group(1)
                # 搜尋可能的資料檔位置
                candidates = [
                    self.project_root / "test_data" / data_file,
                    self.project_root / data_file,
                    filepath.parent / data_file,
                    filepath.parent.parent / "test_data" / data_file,
                ]
                for c in candidates:
                    if c.exists():
                        self._data_files.add(c.resolve())
                        break

    # ── Conftest 分析 ──

    def _parse_conftest_fixtures(self) -> dict[str, dict]:
        """
        解析 conftest.py，提取所有 fixture 定義。

        Returns:
            {fixture_name: {"source": str, "deps": set[str], "imports": set[str]}}
        """
        conftest_path = self.project_root / "conftest.py"
        if not conftest_path.exists():
            return {}

        source = conftest_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(conftest_path))
        lines = source.splitlines()

        fixtures: dict[str, dict] = {}

        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue

            # 檢查是否有 @pytest.fixture 裝飾器
            is_fixture = False
            for deco in node.decorator_list:
                if isinstance(deco, ast.Attribute):
                    if isinstance(deco.value, ast.Name) and deco.value.id == "pytest" and deco.attr == "fixture":
                        is_fixture = True
                elif isinstance(deco, ast.Call):
                    func = deco.func
                    if isinstance(func, ast.Attribute):
                        if isinstance(func.value, ast.Name) and func.value.id == "pytest" and func.attr == "fixture":
                            is_fixture = True
                elif isinstance(deco, ast.Name) and deco.id == "fixture":
                    is_fixture = True
            if not is_fixture:
                continue

            fixture_name = node.name

            # 提取依賴（此 fixture 的參數 = 其他 fixture）
            deps = set()
            for arg in node.args.args:
                if arg.arg not in ("self", "request"):
                    deps.add(arg.arg)

            # 提取此 fixture 函式的原始碼
            start_line = node.lineno - 1
            # 包含裝飾器
            if node.decorator_list:
                start_line = node.decorator_list[0].lineno - 1
            end_line = node.end_lineno if hasattr(node, "end_lineno") else start_line + 1
            fixture_source = "\n".join(lines[start_line:end_line])

            # 提取函式內的 import
            fixture_imports = set()
            for child in ast.walk(node):
                if isinstance(child, ast.Import):
                    for alias in child.names:
                        fixture_imports.add(alias.name)
                elif isinstance(child, ast.ImportFrom):
                    if child.module:
                        # 完整 import 語句重建
                        names = ", ".join(
                            (f"{a.name} as {a.asname}" if a.asname else a.name)
                            for a in child.names
                        )
                        fixture_imports.add(f"from {child.module} import {names}")

            fixtures[fixture_name] = {
                "source": fixture_source,
                "deps": deps,
                "imports": fixture_imports,
            }

        return fixtures

    def _resolve_fixtures(self, fixture_map: dict[str, dict]) -> dict[str, dict]:
        """
        根據測試需要的 fixture 名稱，遞迴解析所有依賴的 fixtures。

        Returns:
            僅包含需要的 fixtures 的子集
        """
        needed: dict[str, dict] = {}
        queue = list(self._fixture_names)
        visited = set()

        while queue:
            name = queue.pop(0)
            if name in visited:
                continue
            visited.add(name)
            if name in fixture_map:
                needed[name] = fixture_map[name]
                # 加入此 fixture 的依賴
                for dep in fixture_map[name]["deps"]:
                    if dep not in visited:
                        queue.append(dep)
                # 分析 fixture 中的 import 引用
                for imp in fixture_map[name]["imports"]:
                    if imp.startswith("from "):
                        # "from utils.xxx import YYY" → 取 module 部分
                        mod = imp.split("from ")[1].split(" import ")[0].strip()
                        self._classify_import(mod)

        return needed

    # ── 檔案複製 ──

    def _copy_files(self, output: Path, needed_fixtures: dict,
                    fixture_map: dict) -> list[str]:
        """複製所有需要的檔案到輸出目錄"""
        created: list[str] = []

        # 複製測試檔案
        tests_dir = output / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        (tests_dir / "__init__.py").write_text("", encoding="utf-8")
        created.append("tests/__init__.py")

        test_dest = tests_dir / self.test_file.name
        shutil.copy2(self.test_file, test_dest)
        created.append(f"tests/{self.test_file.name}")
        print(f"  ✓ tests/{self.test_file.name}")

        # 複製 local 模組
        copied_packages: set[str] = set()
        for module_name in sorted(self._local_modules):
            files = self._get_module_files(module_name)
            for src_file in files:
                rel = src_file.relative_to(self.project_root)
                dest = output / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                if not dest.exists():
                    shutil.copy2(src_file, dest)
                    created.append(str(rel))
                    print(f"  ✓ {rel}")

                # 確保 __init__.py 存在
                pkg = str(rel.parts[0])
                if pkg not in copied_packages:
                    copied_packages.add(pkg)
                    init_path = output / pkg / "__init__.py"
                    if not init_path.exists():
                        init_path.parent.mkdir(parents=True, exist_ok=True)
                        init_path.write_text("", encoding="utf-8")
                        created.append(f"{pkg}/__init__.py")

        # 產生最小 conftest.py
        conftest_code = self._build_minimal_conftest(needed_fixtures, fixture_map)
        conftest_path = output / "conftest.py"
        conftest_path.write_text(conftest_code, encoding="utf-8")
        created.append("conftest.py")
        print(f"  ✓ conftest.py (最小化)")

        return created

    def _get_module_files(self, module_name: str) -> list[Path]:
        """取得模組對應的所有檔案（含 __init__.py）"""
        files = []
        parts = module_name.split(".")

        # 模組本身的 .py 檔
        mod_path = self._module_to_path(module_name)
        if mod_path and mod_path.exists():
            files.append(mod_path)

        # 如果是 sub-module (如 core.base_page)，確保 package __init__.py
        if len(parts) > 1:
            pkg_init = self.project_root / parts[0] / "__init__.py"
            if pkg_init.exists():
                files.append(pkg_init)

        return files

    def _build_minimal_conftest(self, needed_fixtures: dict,
                                fixture_map: dict) -> str:
        """產生最小化的 conftest.py"""
        parts = []

        # Header
        parts.append('"""')
        parts.append(f"conftest.py — 自動匯出")
        parts.append(f"僅包含 {self.test_file.name} 需要的 fixtures")
        parts.append('"""')
        parts.append("")

        # 收集所有 import
        top_imports = {"import pytest"}
        fixture_local_imports: list[str] = []

        for name, info in needed_fixtures.items():
            for imp in info["imports"]:
                if imp.startswith("from "):
                    fixture_local_imports.append(imp)
                else:
                    top_imports.add(f"import {imp}")

        # 也需要這些 top-level import 因為 conftest 可能用到
        # 收集所有 fixture source 合併成一個大字串方便搜尋
        all_fixture_source = "\n".join(
            info["source"] for info in needed_fixtures.values()
        )
        conftest_path = self.project_root / "conftest.py"
        if conftest_path.exists():
            source = conftest_path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            # 取得最頂層的 import（非函式內）
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        used_name = alias.asname or alias.name
                        if used_name in all_fixture_source:
                            top_imports.add(f"import {alias.name}")
                elif isinstance(node, ast.ImportFrom) and node.module:
                    # 檢查此 import 中是否有任何名稱被 fixture 引用
                    used_names = []
                    for alias in node.names:
                        used_name = alias.asname or alias.name
                        if used_name in all_fixture_source:
                            used_names.append(alias)
                    if used_names:
                        names = ", ".join(
                            (f"{a.name} as {a.asname}" if a.asname else a.name)
                            for a in used_names
                        )
                        top_imports.add(f"from {node.module} import {names}")

        # 寫 import 區塊
        stdlib_imports = sorted(i for i in top_imports if not i.startswith("from "))
        local_imports = sorted(i for i in top_imports if i.startswith("from "))
        local_imports.extend(sorted(set(fixture_local_imports)))

        for imp in stdlib_imports:
            parts.append(imp)
        if stdlib_imports and local_imports:
            parts.append("")
        for imp in local_imports:
            parts.append(imp)
        parts.append("")
        parts.append("")

        # 寫 hooks（pytest_addoption 如果需要 --platform / --env）
        needs_platform = "platform" in needed_fixtures
        needs_env = "test_env" in needed_fixtures

        if needs_platform or needs_env:
            parts.append("def pytest_addoption(parser):")
            parts.append('    """命令列參數"""')
            if needs_platform:
                parts.append("    parser.addoption(")
                parts.append('        "--platform",')
                parts.append('        action="store",')
                parts.append('        default="android",')
                parts.append('        choices=["android", "ios"],')
                parts.append('        help="測試平台",')
                parts.append("    )")
            if needs_env:
                parts.append("    parser.addoption(")
                parts.append('        "--env",')
                parts.append('        action="store",')
                parts.append('        default="dev",')
                parts.append('        help="測試環境",')
                parts.append("    )")
            parts.append("")
            parts.append("")

        # 寫 fixtures（按依賴順序）
        ordered = self._topological_sort(needed_fixtures)
        for name in ordered:
            info = needed_fixtures[name]
            parts.append(info["source"])
            parts.append("")
            parts.append("")

        # 失敗截圖 hook
        if "driver" in needed_fixtures:
            parts.append("@pytest.hookimpl(tryfirst=True, hookwrapper=True)")
            parts.append("def pytest_runtest_makereport(item, call):")
            parts.append('    """測試失敗時自動截圖"""')
            parts.append("    outcome = yield")
            parts.append("    report = outcome.get_result()")
            parts.append('    if report.when == "call" and report.failed:')
            parts.append('        driver = item.funcargs.get("driver")')
            parts.append("        if driver:")
            parts.append("            from pathlib import Path")
            parts.append('            ss_dir = Path("screenshots")')
            parts.append("            ss_dir.mkdir(exist_ok=True)")
            parts.append('            path = ss_dir / f"FAIL_{item.name}.png"')
            parts.append("            driver.save_screenshot(str(path))")
            parts.append("")

        return "\n".join(parts)

    def _is_import_needed(self, module_name: str, needed_fixtures: dict) -> bool:
        """判斷一個 top-level import 是否被 needed fixtures 引用"""
        # 檢查所有 fixture source 中是否提到此模組的元素
        top_level = module_name.split(".")[0]
        for info in needed_fixtures.values():
            if module_name in info["source"] or top_level in info["source"]:
                return True
        return False

    def _topological_sort(self, fixtures: dict[str, dict]) -> list[str]:
        """依賴排序：被依賴的在前面"""
        result = []
        visited = set()

        def visit(name: str):
            if name in visited or name not in fixtures:
                return
            visited.add(name)
            for dep in fixtures[name]["deps"]:
                visit(dep)
            result.append(name)

        for name in fixtures:
            visit(name)
        return result

    # ── 配置檔產生 ──

    def _generate_configs(self, output: Path) -> list[str]:
        """產生 pytest.ini, requirements.txt, run.sh"""
        created = []

        # pytest.ini
        pytest_ini = output / "pytest.ini"
        pytest_ini.write_text(dedent("""\
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
                security: 安全性測試
        """), encoding="utf-8")
        created.append("pytest.ini")
        print(f"  ✓ pytest.ini")

        # requirements.txt
        reqs = ["# 自動匯出 — 依賴清單", ""]
        # 固定需要
        reqs.append("pytest>=8.0.0")
        # 根據偵測到的 third-party 加入（去重，以套件名為 key）
        added = {"pytest"}
        for pkg in sorted(self._third_party):
            if pkg in added:
                continue
            added.add(pkg)
            pip_name = _PIP_MAPPING.get(pkg, pkg)
            reqs.append(pip_name)
        req_path = output / "requirements.txt"
        req_path.write_text("\n".join(reqs) + "\n", encoding="utf-8")
        created.append("requirements.txt")
        print(f"  ✓ requirements.txt")

        # run.sh
        test_name = self.test_file.name
        run_sh = output / "run.sh"
        run_sh.write_text(dedent(f"""\
            #!/bin/bash
            # 一鍵執行匯出的測試
            set -e

            # 安裝依賴（如果需要）
            if [ ! -d ".venv" ]; then
                echo "建立虛擬環境..."
                python3 -m venv .venv
                source .venv/bin/activate
                pip install -r requirements.txt
            else
                source .venv/bin/activate
            fi

            # 執行測試
            echo "執行測試: {test_name}"
            pytest tests/{test_name} -v "$@"
        """), encoding="utf-8")
        run_sh.chmod(0o755)
        created.append("run.sh")
        print(f"  ✓ run.sh")

        # 複製 capabilities 設定檔（如果 config 模組被引用）
        if any(m.startswith("config") for m in self._local_modules):
            config_dir = output / "config"
            config_dir.mkdir(parents=True, exist_ok=True)
            for caps_file in (self.project_root / "config").glob("*_caps.json"):
                dest = config_dir / caps_file.name
                if not dest.exists():
                    shutil.copy2(caps_file, dest)
                    created.append(f"config/{caps_file.name}")
                    print(f"  ✓ config/{caps_file.name}")

        return created

    def _copy_data_files(self, output: Path) -> list[str]:
        """複製資料檔案"""
        created = []
        for data_file in sorted(self._data_files):
            try:
                rel = data_file.relative_to(self.project_root)
            except ValueError:
                continue
            dest = output / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                shutil.copy2(data_file, dest)
                created.append(str(rel))
                print(f"  ✓ {rel}")
        return created

    # ── 公開工具方法 ──

    def analyze(self) -> dict:
        """
        僅分析依賴，不匯出。用於預覽。

        Returns:
            {"test_file": str, "local_modules": list, "third_party": list,
             "fixture_names": list, "data_files": list}
        """
        self._analyze_file(self.test_file)
        fixture_map = self._parse_conftest_fixtures()
        needed_fixtures = self._resolve_fixtures(fixture_map)

        return {
            "test_file": str(self.test_file.relative_to(self.project_root)),
            "local_modules": sorted(self._local_modules),
            "third_party": sorted(self._third_party),
            "fixture_names": sorted(self._fixture_names),
            "needed_fixtures": sorted(needed_fixtures.keys()),
            "data_files": [
                str(f.relative_to(self.project_root)) for f in sorted(self._data_files)
            ],
        }
