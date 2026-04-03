#!/usr/bin/env python3
"""Render PlantUML from Markdown blocks or standalone .puml files."""

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
from typing import Literal


BLOCK_RE = re.compile(r"```plantuml\s*\n(.*?)\n```", re.DOTALL)
ALLOWED_FORMATS = {"png", "svg", "pdf", "txt", "utxt"}


@dataclass
class PlantUMLBlock:
    index: int
    code: str
    title: str
    stem: str


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
        if text.lower().startswith("figure") or text.startswith("图"):
            return text
    return f"PlantUML Figure {index:03d}"


def collect_blocks(markdown: str) -> list[PlantUMLBlock]:
    blocks: list[PlantUMLBlock] = []
    for idx, match in enumerate(BLOCK_RE.finditer(markdown), start=1):
        title = extract_title(markdown, match.start(), match.end(), idx)
        stem = f"plantuml-{idx:03d}-{slugify(title)}"
        blocks.append(PlantUMLBlock(index=idx, code=match.group(1).strip(), title=title, stem=stem))
    return blocks


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or "diagram"


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


def resolve_input_kind(path: Path, requested: str) -> Literal["markdown", "puml"]:
    if requested != "auto":
        return requested  # type: ignore[return-value]
    if path.suffix.lower() == ".md":
        return "markdown"
    if path.suffix.lower() in {".puml", ".pu", ".uml", ".iuml"}:
        return "puml"
    raise SystemExit(f"Unable to infer input type from suffix: {path}")


def parse_formats(raw: str) -> list[str]:
    formats = [item.strip().lower() for item in raw.split(",") if item.strip()]
    if not formats:
        raise SystemExit("At least one output format is required.")
    unsupported = [fmt for fmt in formats if fmt not in ALLOWED_FORMATS]
    if unsupported:
        raise SystemExit(f"Unsupported format(s): {', '.join(unsupported)}")
    return formats


def run_plantuml(command: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, env=env)


def render_source(
    source_name: str,
    source_code: str,
    jar_path: Path,
    images_dir: Path,
    dot_path: str,
    formats: list[str],
) -> dict:
    image_paths: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="plantuml-professional-diagrams-") as tmp:
        tmpdir = Path(tmp)
        source_path = tmpdir / source_name
        source_path.write_text(source_code.rstrip() + "\n", encoding="utf-8")
        env = os.environ.copy()
        env["GRAPHVIZ_DOT"] = dot_path

        syntax_result = run_plantuml(
            [
                "java",
                "-Djava.awt.headless=true",
                "-jar",
                str(jar_path),
                "--check-syntax",
                str(source_path),
            ],
            env,
        )
        if syntax_result.returncode != 0:
            return {
                "status": "failed",
                "image_paths": {},
                "preferred_format": None,
                "error": (syntax_result.stderr or syntax_result.stdout or "PlantUML syntax check failed").strip(),
            }

        for fmt in formats:
            result = run_plantuml(
                [
                    "java",
                    "-Djava.awt.headless=true",
                    "-jar",
                    str(jar_path),
                    "--charset",
                    "UTF-8",
                    "--threads",
                    "auto",
                    "--disable-metadata",
                    "--format",
                    fmt,
                    "--output-dir",
                    str(tmpdir),
                    str(source_path),
                ],
                env,
            )
            generated = source_path.with_suffix(f".{fmt}")
            if result.returncode != 0 or not generated.exists():
                return {
                    "status": "failed",
                    "image_paths": image_paths,
                    "preferred_format": formats[0] if image_paths else None,
                    "error": (result.stderr or result.stdout or f"PlantUML rendering failed for {fmt}").strip(),
                }
            final_name = f"{Path(source_name).stem}.{fmt}"
            final_path = images_dir / final_name
            shutil.move(str(generated), final_path)
            image_paths[fmt] = final_name
    return {
        "status": "rendered",
        "image_paths": image_paths,
        "preferred_format": formats[0],
        "error": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Render PlantUML from Markdown blocks or .puml files.")
    parser.add_argument("source", help="Source Markdown or .puml path")
    parser.add_argument("images_dir", help="Output images directory")
    parser.add_argument("--jar", required=True, help="Path to plantuml jar")
    parser.add_argument(
        "--input-kind",
        choices=["auto", "markdown", "puml"],
        default="auto",
        help="Interpret the source as Markdown or standalone PlantUML",
    )
    parser.add_argument(
        "--formats",
        default="svg",
        help="Comma-separated output formats. Supported: png, svg, pdf, txt, utxt",
    )
    parser.add_argument("--json-out", help="Optional JSON mapping output path")
    args = parser.parse_args()

    source_path = Path(args.source).resolve()
    images_dir = Path(args.images_dir).resolve()
    jar_path = Path(args.jar).resolve()
    formats = parse_formats(args.formats)

    status = {
        "java_available": shutil.which("java") is not None,
        "plantuml_jar_found": jar_path.exists(),
        "graphviz_dot": resolve_dot_executable(),
        "rendered_image_count": 0,
        "blocks": [],
        "source": str(source_path),
        "input_kind": None,
        "formats": formats,
        "images_dir": str(images_dir),
    }

    if not source_path.exists():
        raise SystemExit(f"Source not found: {source_path}")

    if not status["java_available"]:
        raise SystemExit("Java not found. Please install Java before running plantuml-professional-diagrams.")
    if not status["plantuml_jar_found"]:
        raise SystemExit(f"PlantUML jar not found: {jar_path}")
    if not status["graphviz_dot"]:
        raise SystemExit(
            "Graphviz dot not found. Please install Graphviz and ensure the `dot` executable is available in PATH."
        )

    input_kind = resolve_input_kind(source_path, args.input_kind)
    status["input_kind"] = input_kind
    images_dir.mkdir(parents=True, exist_ok=True)

    if input_kind == "markdown":
        markdown = source_path.read_text(encoding="utf-8")
        blocks = collect_blocks(markdown)
        if not blocks:
            raise SystemExit(f"No ```plantuml``` blocks found in {source_path}")
        for block in blocks:
            item = render_source(
                f"{block.stem}.puml",
                block.code,
                jar_path,
                images_dir,
                status["graphviz_dot"],
                formats,
            )
            item.update(
                {
                    "index": block.index,
                    "title": block.title,
                    "markdown_image_path": item["image_paths"].get(item["preferred_format"]) if item["preferred_format"] else None,
                    "source_name": f"{block.stem}.puml",
                }
            )
            status["blocks"].append(item)
            if item["status"] == "rendered":
                status["rendered_image_count"] += 1
            else:
                raise SystemExit(
                    f"PlantUML render failed for block {block.index}: {item['error'] or 'unknown error'}"
                )
    else:
        item = render_source(
            source_path.name,
            source_path.read_text(encoding="utf-8"),
            jar_path,
            images_dir,
            status["graphviz_dot"],
            formats,
        )
        item.update(
            {
                "index": 1,
                "title": source_path.stem,
                "markdown_image_path": item["image_paths"].get(item["preferred_format"]) if item["preferred_format"] else None,
                "source_name": source_path.name,
            }
        )
        status["blocks"].append(item)
        if item["status"] == "rendered":
            status["rendered_image_count"] = 1
        else:
            raise SystemExit(f"PlantUML render failed for {source_path.name}: {item['error'] or 'unknown error'}")

    output = json.dumps(status, ensure_ascii=False, indent=2)
    if args.json_out:
        Path(args.json_out).resolve().write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
