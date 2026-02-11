"""
Generator Engine (核心引擎)
串接所有 writer，一次產生完整的測試專案。

使用方式：
    1. 程式化呼叫：
        engine = GeneratorEngine(spec)
        engine.generate()

    2. 從 JSON 設定檔：
        engine = GeneratorEngine.from_json("app_spec.json")
        engine.generate()

    3. CLI 互動模式：
        python -m generator
"""

import json
from pathlib import Path

from generator.schema import AppSpec
from generator.config_builder import ConfigBuilder
from generator.page_writer import PageWriter
from generator.test_data_writer import TestDataWriter
from generator.test_writer import TestWriter


class GeneratorEngine:
    """測試專案產生引擎"""

    def __init__(self, spec: AppSpec):
        self.spec = spec
        if not spec.output_dir:
            raise ValueError("必須指定 output_dir")
        self.output = Path(spec.output_dir).resolve()

    @classmethod
    def from_json(cls, json_path: str) -> "GeneratorEngine":
        """從 JSON 設定檔建立"""
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        spec = AppSpec.from_dict(data)
        return cls(spec)

    def generate(self) -> dict:
        """
        產生完整測試專案。

        Returns:
            {"output_dir": str, "files": list[str], "summary": dict}
        """
        print(f"\n{'='*60}")
        print(f"  Appium 測試專案產生器")
        print(f"  App:    {self.spec.app_name}")
        print(f"  輸出:   {self.output}")
        print(f"  頁面:   {len(self.spec.pages)} 個")
        print(f"{'='*60}\n")

        self.output.mkdir(parents=True, exist_ok=True)
        created_files: list[str] = []

        # 1. 設定檔
        print("[1/4] 產生設定檔...")
        config_builder = ConfigBuilder(self.spec, self.output)
        for f in config_builder.build_all():
            created_files.append(str(f.relative_to(self.output)))
            print(f"  ✓ {f.relative_to(self.output)}")

        # 確保 config/__init__.py
        config_init = self.output / "config" / "__init__.py"
        if not config_init.exists():
            config_init.write_text("", encoding="utf-8")
            created_files.append("config/__init__.py")

        # 2. Page Objects
        print("\n[2/4] 產生 Page Objects...")
        page_writer = PageWriter(self.output)
        for page in self.spec.pages:
            f = page_writer.write(page)
            created_files.append(str(f.relative_to(self.output)))
            print(f"  ✓ {f.relative_to(self.output)}  ({len(page.elements)} 元素)")

        # 3. 測試資料
        print("\n[3/4] 產生測試資料...")
        data_writer = TestDataWriter(self.output)
        total_cases = 0
        for page in self.spec.pages:
            f = data_writer.write(page)
            with open(f, encoding="utf-8") as fp:
                cases = json.load(fp)
            total_cases += len(cases)
            created_files.append(str(f.relative_to(self.output)))
            print(f"  ✓ {f.relative_to(self.output)}  ({len(cases)} 組資料)")

        # 4. 測試案例 + conftest
        print("\n[4/4] 產生測試案例...")
        test_writer = TestWriter(self.spec, self.output)
        f = test_writer.write_conftest()
        created_files.append(str(f.relative_to(self.output)))
        print(f"  ✓ {f.relative_to(self.output)}")

        for page in self.spec.pages:
            f = test_writer.write_test(page)
            created_files.append(str(f.relative_to(self.output)))
            print(f"  ✓ {f.relative_to(self.output)}")

        # 儲存規格檔 (方便下次更新)
        spec_path = self.output / "app_spec.json"
        with open(spec_path, "w", encoding="utf-8") as f:
            json.dump(self.spec.to_dict(), f, ensure_ascii=False, indent=4)
        created_files.append("app_spec.json")

        # 摘要
        summary = {
            "pages": len(self.spec.pages),
            "total_elements": sum(len(p.elements) for p in self.spec.pages),
            "total_test_data": total_cases,
            "total_files": len(created_files),
        }

        print(f"\n{'='*60}")
        print(f"  產生完成！")
        print(f"  目錄:     {self.output}")
        print(f"  檔案數:   {summary['total_files']}")
        print(f"  頁面數:   {summary['pages']}")
        print(f"  元素數:   {summary['total_elements']}")
        print(f"  測試資料: {summary['total_test_data']} 組")
        print(f"")
        print(f"  下一步:")
        print(f"    cd {self.output}")
        print(f"    pip install -r requirements.txt")
        print(f"    pytest -m smoke     # 先跑冒煙")
        print(f"    pytest              # 跑全部")
        print(f"{'='*60}\n")

        return {
            "output_dir": str(self.output),
            "files": created_files,
            "summary": summary,
        }
