import json
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = Path(__file__).resolve().parents[1] / "scripts"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import wechat_direct_api as CLI_MODULE
from publisher import article_loader as LOADER_MODULE
from publisher import publish_service as SERVICE_MODULE
from publisher import wechat_api_client as API_MODULE


class PublisherTests(unittest.TestCase):
    def test_package_dir_loading_uses_package_metadata(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            package_dir = Path(tmp_dir)
            (package_dir / "meta").mkdir()
            (package_dir / "final").mkdir()
            (package_dir / "meta" / "package.json").write_text(
                json.dumps(
                    {
                        "title": "包内标题",
                        "summary": "包内摘要",
                        "author": "包作者",
                        "need_open_comment": 1,
                        "only_fans_can_comment": 0,
                        "assets": [
                            {
                                "role": "cover",
                                "local_path": str(package_dir / "images" / "cover.png"),
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (package_dir / "final" / "wechat_article.md").write_text(
                "# Markdown 标题\n\n正文第一段。\n",
                encoding="utf-8",
            )
            article = LOADER_MODULE.load_article_from_package_dir(package_dir)
            self.assertEqual(article.title, "Markdown 标题")
            self.assertEqual(article.summary, "包内摘要")
            self.assertEqual(article.author, "包作者")
            self.assertEqual(article.need_open_comment, 1)
            self.assertEqual(article.only_fans_can_comment, 0)

    def test_process_markdown_images_replaces_local_paths(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            image_path = root / "demo.png"
            image_path.write_bytes(b"fake")
            original = SERVICE_MODULE.upload_image

            def fake_upload(file_path, access_token):
                self.assertEqual(Path(file_path).resolve(), image_path.resolve())
                self.assertEqual(access_token, "token")
                return "https://mmbiz.qpic.cn/demo.png"

            SERVICE_MODULE.upload_image = fake_upload
            try:
                rendered = SERVICE_MODULE.process_markdown_images("![图](demo.png)", root, "token")
            finally:
                SERVICE_MODULE.upload_image = original

            self.assertIn("https://mmbiz.qpic.cn/demo.png", rendered)
            self.assertNotIn("(demo.png)", rendered)

    def test_build_draft_payload_contains_expected_fields(self):
        payload = API_MODULE.build_draft_payload(
            title="标题",
            content="<p>正文</p>",
            thumb_media_id="thumb123",
            author="作者",
            digest="摘要",
            need_open_comment=1,
            only_fans_can_comment=0,
        )
        article = payload["articles"][0]
        self.assertEqual(article["title"], "标题")
        self.assertEqual(article["thumb_media_id"], "thumb123")
        self.assertEqual(article["author"], "作者")
        self.assertEqual(article["digest"], "摘要")
        self.assertEqual(article["need_open_comment"], 1)
        self.assertEqual(article["only_fans_can_comment"], 0)

    def test_cli_publish_requires_exactly_one_input_mode(self):
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                CLI_MODULE.main(["publish", "--markdown", "a.md", "--package-dir", "pkg"])


if __name__ == "__main__":
    unittest.main()
