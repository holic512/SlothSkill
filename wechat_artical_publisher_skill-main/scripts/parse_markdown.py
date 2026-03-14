#!/usr/bin/env python3
"""Compatibility wrapper around the shared article loader."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from publisher.article_loader import extract_images_with_block_index, load_article_from_markdown
from publisher.publish_service import markdown_to_html


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse Markdown for WeChat article publishing.")
    parser.add_argument("markdown_file", help="Markdown 文件路径")
    parser.add_argument("--output", choices=["json", "html"], default="json")
    args = parser.parse_args()

    article = load_article_from_markdown(args.markdown_file)
    images, clean_markdown, total_blocks = extract_images_with_block_index(
        article.body_markdown,
        article.source_path.parent if article.source_path else Path.cwd(),
    )

    if args.output == "html":
        print(markdown_to_html(clean_markdown))
        return

    print(
        json.dumps(
            {
                "title": article.title,
                "cover_image": article.cover_image,
                "content_images": images,
                "html": markdown_to_html(clean_markdown),
                "total_blocks": total_blocks,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
