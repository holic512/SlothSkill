#!/usr/bin/env python3
"""WeChat content workshop CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from workshop.common import load_dotenv as _load_dotenv
from workshop.fallback_renderers import (
    Image,
    ImageDraw,
    ImageFont,
    find_available_font,
    render_text_card_png,
    write_simple_png,
)
from workshop.image_generation import IMAGE_SOURCES, materialize_images, source_pollinations
from workshop.models import ContentPackage, ImageAsset, PollinationsConfig, PollinationsQuotaStatus, QuotaDecision
from workshop.package_builder import (
    DEFAULT_CHANNEL,
    DEFAULT_CONTENT_ROOT,
    DEFAULT_IMAGE_TEST_OUTPUT_DIR,
    DEFAULT_SERIES,
    DEFAULT_TONE,
    archive_package,
    build_image_prompts,
    build_package,
    build_wechat_markdown,
    generate_cover_copy,
    run_image_test,
)
from workshop.pollinations import (
    DEFAULT_POLLINATIONS_ACCOUNT_API_BASE,
    DEFAULT_POLLINATIONS_API_BASE,
    DEFAULT_POLLINATIONS_IMAGE_MODEL,
    auth_headers,
    classify_pollinations_error,
    decide_quota_strategy,
    download_file,
    fetch_json,
    fetch_pollinations_quota,
    get_proxy_candidates,
    get_pollinations_config,
    read_json_error,
    with_pollinations_key,
)


def load_dotenv(env_path: Optional[Path] = None, start_dir: Optional[Path] = None) -> Optional[Path]:
    return _load_dotenv(Path(__file__), env_path=env_path, start_dir=start_dir)


def cmd_generate(args: argparse.Namespace) -> int:
    quota_status = fetch_pollinations_quota()
    quota_decision = decide_quota_strategy(quota_status)
    for line in quota_status.lines:
        print(line)
    for line in quota_decision.summary_lines:
        print(line)
    package = build_package(args)
    package_dir = archive_package(
        package,
        args,
        materialize_images=lambda pkg, img_dir, skip_images=False: materialize_images(
            pkg, img_dir, skip_images, quota_decision
        ),
    )
    print(f"内容包已生成: {package_dir}")
    print(f"公众号成稿: {package_dir / 'final' / 'wechat_article.md'}")
    print(
        "下一步发布命令: "
        f"python3 wechat_artical_publisher_skill-main/scripts/wechat_direct_api.py publish --mode draft --package-dir \"{package_dir}\""
    )
    return 0


def cmd_test_image(args: argparse.Namespace) -> int:
    quota_status = fetch_pollinations_quota()
    quota_decision = decide_quota_strategy(quota_status)
    for line in quota_status.lines:
        print(line)
    for line in quota_decision.summary_lines:
        print(line)

    output_dir = Path(args.output_dir or DEFAULT_IMAGE_TEST_OUTPUT_DIR).resolve()
    _, assets = run_image_test(
        topic=args.topic,
        region=args.region or "本地城市",
        series=args.series or DEFAULT_SERIES,
        output_dir=output_dir,
        image_count=args.image_count,
        materialize_images=lambda pkg, img_dir, skip_images=False: materialize_images(
            pkg, img_dir, skip_images, quota_decision
        ),
    )
    print(f"图片测试目录: {output_dir}")
    for asset in assets:
        print(f"- {asset['role']}: {asset.get('local_path', '')}")
        print(f"  source={asset.get('source', '') or 'N/A'}")
        print(f"  generation_strategy={asset.get('generation_strategy', '') or 'N/A'}")
        if asset.get("failure_reason"):
            print(f"  failure_reason={asset['failure_reason']}")
    print(f"测试报告: {output_dir / 'image_test_report.md'}")
    return 0


def cmd_export_markdown(args: argparse.Namespace) -> int:
    package_dir = Path(args.package_dir).resolve()
    meta_path = package_dir / "meta" / "package.json"
    if not meta_path.exists():
        print(f"Error: 未找到内容包元数据 - {meta_path}", file=sys.stderr)
        return 1

    package_data = json.loads(meta_path.read_text(encoding="utf-8"))
    package = ContentPackage(**{key: package_data[key] for key in ContentPackage.__dataclass_fields__})
    markdown = build_wechat_markdown(package, package_dir)
    output_path = package_dir / "final" / "wechat_article.md"
    output_path.write_text(markdown, encoding="utf-8")
    print(f"已导出公众号成稿: {output_path}")
    return 0


def cmd_publish_draft(args: argparse.Namespace) -> int:
    package_dir = Path(args.package_dir).resolve()
    markdown_path = package_dir / "final" / "wechat_article.md"
    if not markdown_path.exists():
        print(f"Error: 未找到公众号成稿 - {markdown_path}", file=sys.stderr)
        return 1
    print("publish-draft 已降级为兼容提示命令；内容工坊不再直接调用发布器。")
    print(
        "请执行: "
        f"python3 wechat_artical_publisher_skill-main/scripts/wechat_direct_api.py publish --mode draft --package-dir \"{package_dir}\""
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate WeChat-ready content packages.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate a new content package")
    generate.add_argument("--topic", required=True, help="Core topic for the article")
    generate.add_argument("--audience", default="", help="Target audience hint")
    generate.add_argument("--region", default="", help="Region or city hint")
    generate.add_argument("--series", default=DEFAULT_SERIES, help="Series or column name")
    generate.add_argument("--tone", default=DEFAULT_TONE, help="Writing tone")
    generate.add_argument("--channel", default=DEFAULT_CHANNEL, help="Primary channel")
    generate.add_argument("--date", default="", help="Archive date in YYYY-MM-DD format")
    generate.add_argument("--content-root", default=str(DEFAULT_CONTENT_ROOT), help="Archive root path")
    generate.add_argument("--inline-image-count", type=int, default=2, help="Number of inline images")
    generate.add_argument("--skip-images", action="store_true", help="Skip remote image generation")
    generate.set_defaults(func=cmd_generate)

    test_image = subparsers.add_parser("test-image", help="Generate images only into a visible local directory")
    test_image.add_argument("--topic", required=True, help="Core topic for image generation")
    test_image.add_argument("--region", default="", help="Region or city hint")
    test_image.add_argument("--series", default=DEFAULT_SERIES, help="Series or column name")
    test_image.add_argument(
        "--output-dir",
        default=str(DEFAULT_IMAGE_TEST_OUTPUT_DIR),
        help="Directory to write generated images and a small report",
    )
    test_image.add_argument("--image-count", type=int, default=2, help="How many images to generate, cover included")
    test_image.set_defaults(func=cmd_test_image)

    export_md = subparsers.add_parser("export-markdown", help="Rebuild WeChat-ready markdown for a package")
    export_md.add_argument("--package-dir", required=True, help="Existing package directory")
    export_md.set_defaults(func=cmd_export_markdown)

    publish = subparsers.add_parser("publish-draft", help="Publish package markdown through existing WeChat publisher")
    publish.add_argument("--package-dir", required=True, help="Existing package directory")
    publish.set_defaults(func=cmd_publish_draft)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
