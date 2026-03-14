import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "content_workshop.py"
SPEC = importlib.util.spec_from_file_location("content_workshop", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ContentWorkshopCliTests(unittest.TestCase):
    def setUp(self):
        self._env_backup = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)

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
            self.assertIn("generation_strategy", package_json["assets"][0])
            self.assertIn("decision_reason", package_json["assets"][0])

    def test_load_dotenv_from_current_directory(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_path = Path(tmp_dir) / ".env"
            env_path.write_text("POLLINATIONS_API_KEY=sk_from_current\n", encoding="utf-8")
            os.environ.pop("POLLINATIONS_API_KEY", None)

            loaded = MODULE.load_dotenv(start_dir=Path(tmp_dir))

            self.assertEqual(loaded.resolve(), env_path.resolve())
            self.assertEqual(os.environ.get("POLLINATIONS_API_KEY"), "sk_from_current")

    def test_load_dotenv_from_parent_directory(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            child = root / "nested" / "deeper"
            child.mkdir(parents=True)
            env_path = root / ".env"
            env_path.write_text("POLLINATIONS_API_KEY=sk_from_parent\n", encoding="utf-8")
            os.environ.pop("POLLINATIONS_API_KEY", None)

            loaded = MODULE.load_dotenv(start_dir=child)

            self.assertEqual(loaded.resolve(), env_path.resolve())
            self.assertEqual(os.environ.get("POLLINATIONS_API_KEY"), "sk_from_parent")

    def test_explicit_environment_variable_wins_over_dotenv(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_path = Path(tmp_dir) / ".env"
            env_path.write_text("POLLINATIONS_API_KEY=sk_from_file\n", encoding="utf-8")
            os.environ["POLLINATIONS_API_KEY"] = "sk_from_env"

            MODULE.load_dotenv(start_dir=Path(tmp_dir))

            self.assertEqual(os.environ.get("POLLINATIONS_API_KEY"), "sk_from_env")

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

    def test_generate_prints_quota_summary_and_strategy(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with mock.patch.object(
                MODULE,
                "fetch_pollinations_quota",
                return_value=MODULE.PollinationsQuotaStatus(
                    ok=True,
                    lines=[
                        "Pollinations 额度状态:",
                        "- Key 状态: 可用",
                        "- 账户余额: 42.5",
                    ],
                    key_data={"valid": True},
                    balance_data={"balance": 42.5},
                ),
            ):
                buffer = io.StringIO()
                with mock.patch("sys.stdout", buffer):
                    result = MODULE.main(
                        [
                            "generate",
                            "--topic",
                            "为什么老街区总能留住人",
                            "--content-root",
                            tmp_dir,
                            "--skip-images",
                        ]
                    )

            self.assertEqual(result, 0)
            output = buffer.getvalue()
            self.assertIn("Pollinations 额度状态:", output)
            self.assertIn("账户余额: 42.5", output)
            self.assertIn("图片策略决策: 额度可用", output)

    def test_test_image_prints_generation_strategy(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_materialize = MODULE.materialize_images

            def fake_materialize(package, images_dir, skip_images, quota_decision, sources=None):
                target = Path(images_dir) / "01-cover.png"
                target.write_bytes(b"fake")
                return [
                    {
                        "role": "cover",
                        "topic": package.topic,
                        "prompt": "fake prompt",
                        "local_path": str(target),
                        "source": "pollinations[zimage]:direct",
                        "width": 900,
                        "height": 383,
                        "status": "generated",
                        "failure_reason": "",
                        "generation_strategy": "remote-ai",
                        "decision_reason": "allowed",
                    }
                ]

            MODULE.materialize_images = fake_materialize
            try:
                buffer = io.StringIO()
                with mock.patch("sys.stdout", buffer):
                    result = MODULE.main(
                        [
                            "test-image",
                            "--topic",
                            "只测图片输出",
                            "--output-dir",
                            tmp_dir,
                            "--image-count",
                            "1",
                        ]
                    )
                self.assertEqual(result, 0)
                self.assertIn("generation_strategy=remote-ai", buffer.getvalue())
                self.assertTrue((Path(tmp_dir) / "image_test_report.md").exists())
            finally:
                MODULE.materialize_images = original_materialize


if __name__ == "__main__":
    unittest.main()
