#!/usr/bin/env python3
"""Run the full report post-processing pipeline for report-orchestrator."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path


def slugify(value: str) -> str:
    value = value.strip()
    value = re.sub(r"[\\/:*?\"<>|()\[\]{}]+", "-", value)
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"-{2,}", "-", value)
    return value.strip("-") or "report"


def run_json(command: list[str], cwd: Path) -> dict:
    result = subprocess.run(command, cwd=str(cwd), capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or f"Command failed: {' '.join(command)}")
    return json.loads(result.stdout)


def require_dependency(name: str, install_hint: str) -> None:
    if shutil.which(name) is None:
        raise SystemExit(f"{name} not found. Please install {install_hint} before running report-orchestrator.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render PlantUML and optionally export DOCX.")
    parser.add_argument("source_markdown", help="Generated source markdown path")
    parser.add_argument("--report-name", help="Report name used for output directory")
    parser.add_argument("--output-root", default="docx", help="Root output directory")
    parser.add_argument("--jar", help="PlantUML jar path; defaults to skill-local jar")
    parser.add_argument("--docx-template", help="DOCX template id, file name, or template name")
    parser.add_argument("--style-query", help="Style requirements used to match the best DOCX template")
    parser.add_argument("--docx-manifest", help="Path to the DOCX template manifest")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    source_markdown = Path(args.source_markdown).resolve()
    report_name = slugify(args.report_name or source_markdown.stem.replace(".source", ""))
    output_dir = (Path(args.output_root).resolve() / report_name)
    images_dir = output_dir / "images"
    source_copy = output_dir / "report.source.md"
    final_markdown = output_dir / "report.md"
    docx_path = output_dir / f"{report_name}.docx"
    mapping_json = output_dir / "plantuml-map.json"
    jar_path = Path(args.jar).resolve() if args.jar else (script_dir.parent / "plantuml-1.2026.2.jar")

    require_dependency("java", "Java")
    require_dependency("pandoc", "pandoc")
    if not jar_path.exists():
        raise SystemExit(f"PlantUML jar not found: {jar_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_markdown, source_copy)

    render_status = run_json(
        [
            "python3",
            str(script_dir / "render_plantuml.py"),
            str(source_copy),
            str(images_dir),
            "--jar",
            str(jar_path),
            "--json-out",
            str(mapping_json),
        ],
        cwd=output_dir,
    )
    rewrite_status = run_json(
        [
            "python3",
            str(script_dir / "rewrite_markdown_with_images.py"),
            str(source_copy),
            str(mapping_json),
            str(final_markdown),
        ],
        cwd=output_dir,
    )

    export_status = run_json(
        [
            "python3",
            str(script_dir / "export_docx.py"),
            str(final_markdown),
            str(docx_path),
            *(
                ["--template", args.docx_template]
                if args.docx_template
                else []
            ),
            *(
                ["--style-query", args.style_query]
                if args.style_query
                else []
            ),
            *(
                ["--manifest", args.docx_manifest]
                if args.docx_manifest
                else []
            ),
        ],
        cwd=output_dir,
    )

    summary = {
        "report_name": report_name,
        "output_dir": str(output_dir),
        "source_markdown_path": str(source_copy),
        "final_markdown_path": str(final_markdown),
        "image_dir": str(images_dir),
        "docx_path": str(docx_path),
        "render_status": render_status,
        "rewrite_status": rewrite_status,
        "export_status": export_status,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
