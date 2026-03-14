#!/usr/bin/env python3
"""Render PlantUML blocks from a Markdown file into PNG images."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


BLOCK_RE = re.compile(r"```plantuml\s*\n(.*?)\n```", re.DOTALL)


@dataclass
class PlantUMLBlock:
    index: int
    code: str
    title: str


def extract_title(markdown: str, start: int, end: int, index: int) -> str:
    before = markdown[:start].splitlines()
    after = markdown[end:].splitlines()
    candidates = []
    for lines in (after, list(reversed(before))):
        for raw in lines:
            text = raw.strip().strip("*").strip()
            if not text:
                continue
            candidates.append(text)
            break
    for text in candidates:
        if text.startswith("图"):
            return text
    return f"PlantUML 图{index:03d}"


def collect_blocks(markdown: str) -> list[PlantUMLBlock]:
    blocks: list[PlantUMLBlock] = []
    for idx, match in enumerate(BLOCK_RE.finditer(markdown), start=1):
        title = extract_title(markdown, match.start(), match.end(), idx)
        blocks.append(PlantUMLBlock(index=idx, code=match.group(1).strip(), title=title))
    return blocks


def resolve_dot_executable() -> str | None:
    candidates = [
        shutil.which("dot"),
        "/opt/homebrew/bin/dot",
        "/usr/local/bin/dot",
        "/opt/local/bin/dot",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate).resolve())
    return None


def render_block(block: PlantUMLBlock, jar_path: Path, images_dir: Path, dot_path: str) -> dict:
    output_name = f"plantuml-{block.index:03d}.png"
    output_path = images_dir / output_name
    with tempfile.TemporaryDirectory(prefix="report-orchestrator-plantuml-") as tmp:
        tmpdir = Path(tmp)
        source_path = tmpdir / f"plantuml-{block.index:03d}.puml"
        source_path.write_text(block.code + "\n", encoding="utf-8")
        command = [
            "java",
            "-Djava.awt.headless=true",
            "-jar",
            str(jar_path),
            "-charset",
            "UTF-8",
            "-tpng",
            str(source_path),
        ]
        env = os.environ.copy()
        env["GRAPHVIZ_DOT"] = dot_path
        result = subprocess.run(command, capture_output=True, text=True, env=env)
        generated = source_path.with_suffix(".png")
        if result.returncode != 0 or not generated.exists():
            return {
                "index": block.index,
                "title": block.title,
                "status": "failed",
                "image_path": None,
                "error": (result.stderr or result.stdout or "PlantUML rendering failed").strip(),
            }
        shutil.move(str(generated), output_path)
    return {
        "index": block.index,
        "title": block.title,
        "status": "rendered",
        "image_path": output_name,
        "error": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Render PlantUML blocks from Markdown.")
    parser.add_argument("markdown", help="Source Markdown path")
    parser.add_argument("images_dir", help="Output images directory")
    parser.add_argument("--jar", required=True, help="Path to plantuml jar")
    parser.add_argument("--json-out", help="Optional JSON mapping output path")
    args = parser.parse_args()

    markdown_path = Path(args.markdown).resolve()
    images_dir = Path(args.images_dir).resolve()
    jar_path = Path(args.jar).resolve()

    status = {
        "java_available": shutil.which("java") is not None,
        "plantuml_jar_found": jar_path.exists(),
        "graphviz_dot": resolve_dot_executable(),
        "rendered_image_count": 0,
        "blocks": [],
        "markdown": str(markdown_path),
        "images_dir": str(images_dir),
    }

    if not markdown_path.exists():
        raise SystemExit(f"Markdown not found: {markdown_path}")

    markdown = markdown_path.read_text(encoding="utf-8")
    blocks = collect_blocks(markdown)

    if not status["java_available"]:
        raise SystemExit("Java not found. Please install Java before running report-orchestrator.")
    if not status["plantuml_jar_found"]:
        raise SystemExit(f"PlantUML jar not found: {jar_path}")
    if not status["graphviz_dot"]:
        raise SystemExit(
            "Graphviz dot not found. Please install Graphviz and ensure the `dot` executable is available in PATH."
        )

    images_dir.mkdir(parents=True, exist_ok=True)
    for block in blocks:
        item = render_block(block, jar_path, images_dir, status["graphviz_dot"])
        status["blocks"].append(item)
        if item["status"] == "rendered":
            status["rendered_image_count"] += 1
        else:
            raise SystemExit(
                f"PlantUML render failed for block {block.index}: {item['error'] or 'unknown error'}"
            )

    output = json.dumps(status, ensure_ascii=False, indent=2)
    if args.json_out:
        Path(args.json_out).resolve().write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
