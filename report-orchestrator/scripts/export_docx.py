#!/usr/bin/env python3
"""Export a Markdown file to DOCX with pandoc when available."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def load_manifest(manifest_path: Path) -> list[dict]:
    if not manifest_path.exists():
        raise SystemExit(f"DOCX template manifest not found: {manifest_path}")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise SystemExit(f"Invalid DOCX template manifest: {manifest_path}")
    return payload


def select_template(templates: list[dict], selector: str | None, style_query: str | None) -> dict:
    if selector:
        normalized = selector.strip().lower()
        for template in templates:
            if normalized in {
                str(template.get("id", "")).lower(),
                str(template.get("file", "")).lower(),
                str(template.get("name", "")).lower(),
            }:
                return template
        raise SystemExit(f"DOCX template not found for selector: {selector}")

    if style_query:
        query = style_query.lower()
        scored: list[tuple[int, dict]] = []
        for template in templates:
            keywords = [str(item).lower() for item in template.get("match_keywords", [])]
            score = sum(1 for keyword in keywords if keyword and keyword in query)
            scored.append((score, template))
        scored.sort(key=lambda item: item[0], reverse=True)
        if scored and scored[0][0] > 0:
            return scored[0][1]

    for template in templates:
        if template.get("default"):
            return template
    return templates[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Markdown to DOCX using pandoc.")
    parser.add_argument("markdown", help="Markdown file to export")
    parser.add_argument("docx", help="Output DOCX path")
    parser.add_argument("--template", help="Template id, file name, or template name")
    parser.add_argument("--style-query", help="Free-form style requirements used to match the best template")
    parser.add_argument("--manifest", help="Path to the DOCX template manifest")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    markdown_path = Path(args.markdown).resolve()
    docx_path = Path(args.docx).resolve()
    pandoc = shutil.which("pandoc")
    manifest_path = (
        Path(args.manifest).resolve()
        if args.manifest
        else (script_dir.parent / "assets" / "docx-templates" / "manifest.json")
    )
    templates = load_manifest(manifest_path)
    selected_template = select_template(templates, args.template, args.style_query)
    reference_doc = manifest_path.parent / selected_template["file"]
    if not reference_doc.exists():
        raise SystemExit(f"DOCX template file not found: {reference_doc}")

    status = {
        "pandoc_available": pandoc is not None,
        "docx_exported": False,
        "markdown": str(markdown_path),
        "docx": str(docx_path),
        "template_manifest": str(manifest_path),
        "template_file": str(reference_doc),
        "template_id": selected_template.get("id"),
        "template_name": selected_template.get("name"),
    }

    if pandoc is None:
        raise SystemExit("Pandoc not found. Please install pandoc before running report-orchestrator.")

    docx_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            pandoc,
            str(markdown_path.name),
            "-f",
            "gfm",
            "-t",
            "docx",
            "--reference-doc",
            str(reference_doc),
            "-o",
            str(docx_path.name),
        ],
        cwd=str(markdown_path.parent),
        capture_output=True,
        text=True,
    )
    if result.returncode == 0 and docx_path.exists():
        status["docx_exported"] = True
        status["message"] = "docx exported"
    else:
        raise SystemExit((result.stderr or result.stdout or "pandoc export failed").strip())
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
