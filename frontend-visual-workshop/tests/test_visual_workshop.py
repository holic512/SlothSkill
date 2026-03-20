import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "visual_workshop.py"
SPEC = importlib.util.spec_from_file_location("visual_workshop", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class VisualWorkshopTests(unittest.TestCase):
    def setUp(self):
        self._env_backup = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)

    def test_build_visual_package_maps_asset_types(self):
        package = MODULE.build_visual_package(
            topic="AI 简历助手",
            brand="SlothSkill",
            page_type="landing",
            asset_types=["logo", "cover", "favicon"],
            style_direction="editorial-illustration",
        )

        self.assertEqual([asset["role"] for asset in package.assets], ["logo", "cover", "favicon"])
        self.assertIn("扁平、几何", package.assets[0]["prompt"])
        self.assertIn("横版构图", package.assets[1]["prompt"])
        self.assertIn("16到64像素仍可辨认", package.assets[2]["prompt"])

    def test_generate_missing_key_falls_back_to_local(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            exit_code = MODULE.main(
                [
                    "generate",
                    "--topic",
                    "AI 简历助手",
                    "--brand",
                    "SlothSkill",
                    "--page-type",
                    "landing",
                    "--asset-types",
                    "logo,cover",
                    "--output-dir",
                    tmp_dir,
                ]
            )
            self.assertEqual(exit_code, 0)

            report = Path(tmp_dir) / "report.md"
            package = json.loads((Path(tmp_dir) / "package.json").read_text(encoding="utf-8"))
            self.assertTrue(report.exists())
            self.assertEqual(package["assets"][0]["generation_strategy"], "local-fallback-direct")
            self.assertIn("missing_key", package["assets"][0]["failure_reason"])
            self.assertIn("prompt_version: v1.1", report.read_text(encoding="utf-8"))

    def test_plan_outputs_prompts_and_report_without_assets(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            exit_code = MODULE.main(
                [
                    "plan",
                    "--topic",
                    "AI 简历助手",
                    "--brand",
                    "SlothSkill",
                    "--page-type",
                    "landing",
                    "--asset-types",
                    "hero,feature,empty-state",
                    "--output-dir",
                    tmp_dir,
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertTrue((Path(tmp_dir) / "prompts" / "hero.txt").exists())
            self.assertTrue((Path(tmp_dir) / "report.md").exists())
            self.assertEqual(list((Path(tmp_dir) / "assets").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
