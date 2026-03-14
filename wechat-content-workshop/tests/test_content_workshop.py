import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "content_workshop.py"
SPEC = importlib.util.spec_from_file_location("content_workshop", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ContentWorkshopTests(unittest.TestCase):
    def test_generate_package_creates_required_outputs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = MODULE.main(
                [
                    "generate",
                    "--topic",
                    "为什么越来越多人重新爱上菜市场",
                    "--series",
                    "城市观察",
                    "--region",
                    "杭州",
                    "--audience",
                    "在大城市打拼的年轻上班族",
                    "--content-root",
                    tmp_dir,
                    "--skip-images",
                ]
            )
            self.assertEqual(result, 0)

            package_dir = (
                Path(tmp_dir)
                / "为什么越来越多人重新爱上菜市场"
                / "2026-03-14"
                / "城市观察"
                / "公众号"
            )
            self.assertTrue((package_dir / "article" / "body.md").exists())
            self.assertTrue((package_dir / "cover" / "cover_copy.txt").exists())
            self.assertTrue((package_dir / "images" / "image_plan.md").exists())
            self.assertTrue((package_dir / "final" / "wechat_article.md").exists())
            self.assertTrue((package_dir / "meta" / "package.json").exists())

            package_json = json.loads((package_dir / "meta" / "package.json").read_text(encoding="utf-8"))
            self.assertEqual(package_json["channel"], "公众号")
            self.assertIn("share_text", package_json)
            self.assertGreaterEqual(len(package_json["assets"]), 1)

    def test_export_markdown_rebuilds_final_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            MODULE.main(
                [
                    "generate",
                    "--topic",
                    "通勤路上的早餐摊为什么更像城市体温",
                    "--series",
                    "街头记录",
                    "--region",
                    "成都",
                    "--content-root",
                    tmp_dir,
                    "--skip-images",
                ]
            )
            package_dir = (
                Path(tmp_dir)
                / "通勤路上的早餐摊为什么更像城市体温"
                / "2026-03-14"
                / "街头记录"
                / "公众号"
            )
            output_path = package_dir / "final" / "wechat_article.md"
            output_path.unlink()

            result = MODULE.main(["export-markdown", "--package-dir", str(package_dir)])
            self.assertEqual(result, 0)
            rebuilt = output_path.read_text(encoding="utf-8")
            self.assertIn("# ", rebuilt)
            self.assertIn("摘要：", rebuilt)

    def test_image_generation_failure_falls_back_without_blocking_package(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_sources = MODULE.IMAGE_SOURCES

            def always_fail(asset, target, proxy_url=None):
                raise RuntimeError("network unavailable")

            MODULE.IMAGE_SOURCES = [always_fail]
            try:
                result = MODULE.main(
                    [
                        "generate",
                        "--topic",
                        "社区面包店为什么又热起来了",
                        "--series",
                        "街角小事",
                        "--region",
                        "苏州",
                        "--content-root",
                        tmp_dir,
                    ]
                )
                self.assertEqual(result, 0)
                package_dir = (
                    Path(tmp_dir)
                    / "社区面包店为什么又热起来了"
                    / "2026-03-14"
                    / "街角小事"
                    / "公众号"
                )
                package_json = json.loads((package_dir / "meta" / "package.json").read_text(encoding="utf-8"))
                statuses = {asset["status"] for asset in package_json["assets"]}
                self.assertEqual(statuses, {"generated"})
                self.assertTrue(all(asset["source"] == "local-generated" for asset in package_json["assets"]))
                self.assertTrue(all(Path(asset["local_path"]).exists() for asset in package_json["assets"]))
            finally:
                MODULE.IMAGE_SOURCES = original_sources


if __name__ == "__main__":
    unittest.main()
