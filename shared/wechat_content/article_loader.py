from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .common import parse_frontmatter, parse_yes_no


@dataclass
class ArticleDocument:
    title: str
    body_markdown: str
    summary: str
    author: str
    need_open_comment: Optional[int]
    only_fans_can_comment: Optional[int]
    cover_image: Optional[str]
    assets: list[dict[str, Any]] = field(default_factory=list)
    source_path: Optional[Path] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    package_dir: Optional[Path] = None


def split_into_blocks(markdown: str) -> list[str]:
    blocks = []
    current_block = []
    in_code_block = False
    code_block_lines = []

    for line in markdown.split("\n"):
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_code_block:
                in_code_block = False
                if code_block_lines:
                    blocks.append("___CODE_BLOCK_START___" + "\n".join(code_block_lines) + "___CODE_BLOCK_END___")
                code_block_lines = []
            else:
                if current_block:
                    blocks.append("\n".join(current_block))
                    current_block = []
                in_code_block = True
            continue

        if in_code_block:
            code_block_lines.append(line)
            continue

        if not stripped:
            if current_block:
                blocks.append("\n".join(current_block))
                current_block = []
            continue

        if stripped.startswith(("#", ">")):
            if current_block:
                blocks.append("\n".join(current_block))
                current_block = []
            blocks.append(stripped)
            continue

        if re.match(r"^!\[.*\]\(.*\)$", stripped):
            if current_block:
                blocks.append("\n".join(current_block))
                current_block = []
            blocks.append(stripped)
            continue

        current_block.append(line)

    if current_block:
        blocks.append("\n".join(current_block))
    if code_block_lines:
        blocks.append("___CODE_BLOCK_START___" + "\n".join(code_block_lines) + "___CODE_BLOCK_END___")
    return blocks


def extract_images_with_block_index(markdown: str, base_path: Path) -> tuple[list[dict[str, Any]], str, int]:
    blocks = split_into_blocks(markdown)
    images = []
    clean_blocks = []
    img_pattern = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)$")

    for block in blocks:
        match = img_pattern.match(block.strip())
        if not match:
            clean_blocks.append(block)
            continue
        img_path = match.group(2)
        full_path = str((base_path / img_path).resolve()) if not os.path.isabs(img_path) else img_path
        after_text = ""
        if clean_blocks:
            lines = [line for line in clean_blocks[-1].strip().split("\n") if line.strip()]
            after_text = lines[-1][:80] if lines else ""
        images.append(
            {
                "path": full_path,
                "alt": match.group(1),
                "block_index": len(clean_blocks),
                "after_text": after_text,
            }
        )

    clean_markdown = "\n\n".join(clean_blocks)
    return images, clean_markdown, len(clean_blocks)


def find_images_in_markdown(content: str, base_path: Path) -> list[tuple[str, str, bool]]:
    images: list[tuple[str, str, bool]] = []
    md_pattern = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
    for match in md_pattern.finditer(content):
        img_path = match.group(1)
        if img_path.startswith(("http://", "https://", "data:")):
            images.append((img_path, img_path, False))
            continue
        abs_path = Path(img_path) if os.path.isabs(img_path) else base_path / img_path
        if abs_path.exists():
            images.append((img_path, str(abs_path.resolve()), True))
        else:
            images.append((img_path, img_path, False))
    return images


def extract_title(markdown: str) -> tuple[str, str]:
    lines = markdown.strip().split("\n")
    title = "Untitled"
    title_line_idx = None

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            title_line_idx = idx
            break
        if stripped.startswith("## "):
            title = stripped[3:].strip()
            break
        if not stripped.startswith("!["):
            title = stripped[:100]
            break

    if title_line_idx is not None:
        lines.pop(title_line_idx)
        markdown = "\n".join(lines)
    return title[:64], markdown


def infer_summary(markdown_body: str) -> str:
    for line in markdown_body.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith(("#", "!", ">", "-", "*", "`", "|")):
            return stripped[:120]
    return ""


def resolve_cover_image(markdown_body: str, assets: list[dict[str, Any]]) -> Optional[str]:
    asset_cover = next((asset.get("local_path") for asset in assets if asset.get("role") == "cover" and asset.get("local_path")), None)
    if asset_cover:
        return asset_cover
    match = re.search(r"!\[[^\]]*\]\(([^)]+)\)", markdown_body)
    return match.group(1) if match else None


def article_from_markdown_text(
    raw_content: str,
    source_path: Path,
    *,
    package_metadata: Optional[dict[str, Any]] = None,
    markdown_metadata: Optional[dict[str, Any]] = None,
) -> ArticleDocument:
    frontmatter, content = parse_frontmatter(raw_content)
    metadata = {**(package_metadata or {}), **frontmatter, **(markdown_metadata or {})}
    title, markdown_body = extract_title(content)
    summary = str(metadata.get("summary") or metadata.get("digest") or infer_summary(markdown_body))
    author = str(metadata.get("author") or metadata.get("作者") or metadata.get("author_name") or "").strip()
    need_open_comment = parse_yes_no(metadata.get("need_open_comment"), None)
    if need_open_comment is None:
        need_open_comment = parse_yes_no(metadata.get("open_comment"), None)
    only_fans_can_comment = parse_yes_no(metadata.get("only_fans_can_comment"), None)
    if only_fans_can_comment is None:
        only_fans_can_comment = parse_yes_no(metadata.get("fans_only_comment"), None)
    assets = list(metadata.get("assets") or [])
    cover_image = str(metadata.get("cover_image") or resolve_cover_image(markdown_body, assets) or "") or None
    return ArticleDocument(
        title=title,
        body_markdown=markdown_body.strip(),
        summary=summary,
        author=author,
        need_open_comment=need_open_comment,
        only_fans_can_comment=only_fans_can_comment,
        cover_image=cover_image,
        assets=assets,
        source_path=source_path,
        metadata=metadata,
    )


def load_article_from_markdown(markdown_path: str | Path) -> ArticleDocument:
    path = Path(markdown_path).resolve()
    raw_content = path.read_text(encoding="utf-8")
    return article_from_markdown_text(raw_content, path)


def load_article_from_package_dir(package_dir: str | Path) -> ArticleDocument:
    root = Path(package_dir).resolve()
    meta_path = root / "meta" / "package.json"
    markdown_path = root / "final" / "wechat_article.md"
    if not meta_path.exists():
        raise FileNotFoundError(f"未找到内容包元数据: {meta_path}")
    if not markdown_path.exists():
        raise FileNotFoundError(f"未找到内容包成稿: {markdown_path}")

    package_data = json.loads(meta_path.read_text(encoding="utf-8"))
    metadata = {
        "summary": package_data.get("summary", ""),
        "author": package_data.get("author", ""),
        "need_open_comment": package_data.get("need_open_comment"),
        "only_fans_can_comment": package_data.get("only_fans_can_comment"),
        "assets": package_data.get("assets", []),
        "cover_image": package_data.get("cover_image", ""),
        "title": package_data.get("title", ""),
    }
    article = article_from_markdown_text(
        markdown_path.read_text(encoding="utf-8"),
        markdown_path,
        package_metadata=metadata,
    )
    article.package_dir = root
    if not article.title and package_data.get("title"):
        article.title = str(package_data["title"])[:64]
    return article


def load_article(markdown: Optional[str] = None, package_dir: Optional[str] = None) -> ArticleDocument:
    if bool(markdown) == bool(package_dir):
        raise ValueError("必须且只能提供 markdown 或 package_dir 其中之一")
    if package_dir:
        return load_article_from_package_dir(package_dir)
    assert markdown is not None
    return load_article_from_markdown(markdown)
