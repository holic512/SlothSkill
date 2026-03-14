import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "content_workshop.py"
SPEC = importlib.util.spec_from_file_location("content_workshop_image_generation", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ImageGenerationFlowTests(unittest.TestCase):
    def setUp(self):
        self._env_backup = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env_backup)

    def test_missing_key_falls_back_without_calling_remote(self):
        package = MODULE.ContentPackage(
            topic="测试主题",
            date="2026-03-14",
            channel="公众号",
            series="未分栏",
            content_type="文章",
            title="标题",
            summary="摘要",
            body_markdown="正文",
            author="",
            need_open_comment=1,
            only_fans_can_comment=0,
            cover_copy="封面",
            image_plan=[
                {
                    "role": "cover",
                    "topic": "测试主题",
                    "prompt": "封面提示词",
                    "width": 900,
                    "height": 383,
                }
            ],
            share_text={},
            closing_cta="",
            style_notes={},
        )
        decision = MODULE.QuotaDecision(
            status="missing_key",
            allow_remote_generation=False,
            reason="missing_key",
            summary_lines=[],
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            called = {"remote": 0}

            def remote_source(asset, target, proxy_url=None):
                called["remote"] += 1
                raise AssertionError("should not call remote source")

            assets = MODULE.materialize_images(
                package,
                Path(tmp_dir),
                skip_images=False,
                quota_decision=decision,
                sources=[remote_source],
            )
            self.assertTrue(Path(assets[0]["local_path"]).exists())

        self.assertEqual(called["remote"], 0)
        self.assertEqual(assets[0]["generation_strategy"], "local-fallback-direct")
        self.assertEqual(assets[0]["decision_reason"], "missing_key")
        self.assertIn("missing_key", assets[0]["failure_reason"])

    def test_quota_insufficient_falls_back_directly(self):
        package = MODULE.ContentPackage(
            topic="测试主题",
            date="2026-03-14",
            channel="公众号",
            series="未分栏",
            content_type="文章",
            title="标题",
            summary="摘要",
            body_markdown="正文",
            author="",
            need_open_comment=1,
            only_fans_can_comment=0,
            cover_copy="封面",
            image_plan=[
                {
                    "role": "cover",
                    "topic": "测试主题",
                    "prompt": "封面提示词",
                    "width": 900,
                    "height": 383,
                }
            ],
            share_text={},
            closing_cta="",
            style_notes={},
        )
        decision = MODULE.QuotaDecision(
            status="quota_insufficient",
            allow_remote_generation=False,
            reason="quota_insufficient",
            summary_lines=[],
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            assets = MODULE.materialize_images(package, Path(tmp_dir), False, decision, sources=[])

        self.assertEqual(assets[0]["generation_strategy"], "local-fallback-direct")
        self.assertEqual(assets[0]["decision_reason"], "quota_insufficient")
        self.assertIn("quota_unavailable", assets[0]["failure_reason"])

    def test_allowed_uses_remote_generation(self):
        package = MODULE.ContentPackage(
            topic="测试主题",
            date="2026-03-14",
            channel="公众号",
            series="未分栏",
            content_type="文章",
            title="标题",
            summary="摘要",
            body_markdown="正文",
            author="",
            need_open_comment=1,
            only_fans_can_comment=0,
            cover_copy="封面",
            image_plan=[
                {
                    "role": "cover",
                    "topic": "测试主题",
                    "prompt": "封面提示词",
                    "width": 900,
                    "height": 383,
                }
            ],
            share_text={},
            closing_cta="",
            style_notes={},
        )
        decision = MODULE.QuotaDecision(
            status="allowed",
            allow_remote_generation=True,
            reason="quota_available",
            summary_lines=[],
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            def remote_source(asset, target, proxy_url=None):
                target.write_bytes(b"remote")
                return True, "pollinations[zimage]"

            assets = MODULE.materialize_images(
                package,
                Path(tmp_dir),
                False,
                decision,
                sources=[remote_source],
            )

        self.assertEqual(assets[0]["generation_strategy"], "remote-ai")
        self.assertEqual(assets[0]["decision_reason"], "allowed")
        self.assertEqual(assets[0]["source"], "pollinations[zimage]:direct")

    def test_quota_check_failed_still_attempts_remote_then_falls_back(self):
        package = MODULE.ContentPackage(
            topic="测试主题",
            date="2026-03-14",
            channel="公众号",
            series="未分栏",
            content_type="文章",
            title="标题",
            summary="摘要",
            body_markdown="正文",
            author="",
            need_open_comment=1,
            only_fans_can_comment=0,
            cover_copy="封面",
            image_plan=[
                {
                    "role": "cover",
                    "topic": "测试主题",
                    "prompt": "封面提示词",
                    "width": 900,
                    "height": 383,
                }
            ],
            share_text={},
            closing_cta="",
            style_notes={},
        )
        decision = MODULE.QuotaDecision(
            status="quota_check_failed",
            allow_remote_generation=True,
            reason="quota_check_failed",
            summary_lines=[],
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            attempts = {"count": 0}

            def remote_source(asset, target, proxy_url=None):
                attempts["count"] += 1
                raise RuntimeError("network unavailable")

            assets = MODULE.materialize_images(
                package,
                Path(tmp_dir),
                False,
                decision,
                sources=[remote_source],
            )
            self.assertTrue(Path(assets[0]["local_path"]).exists())

        self.assertGreaterEqual(attempts["count"], 1)
        self.assertEqual(assets[0]["generation_strategy"], "remote-then-local-fallback")
        self.assertEqual(assets[0]["decision_reason"], "quota_check_failed")
        self.assertIn("generation_failed", assets[0]["failure_reason"])


if __name__ == "__main__":
    unittest.main()
