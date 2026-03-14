from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Optional


def parse_yes_no(value: Any, default: Optional[int] = None) -> Optional[int]:
    if value is None:
        return default
    if isinstance(value, bool):
        return 1 if value else 0

    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on", "open", "enabled"}:
        return 1
    if text in {"0", "false", "no", "n", "off", "close", "closed", "disabled"}:
        return 0
    return default


def parse_frontmatter(raw_content: str) -> tuple[dict[str, Any], str]:
    if not raw_content.startswith("---"):
        return {}, raw_content

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?", raw_content, flags=re.DOTALL)
    if not match:
        return {}, raw_content

    metadata: dict[str, Any] = {}
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"').strip("'")

    return metadata, raw_content[match.end() :]


def candidate_env_paths(start_dir: Path, script_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    current = start_dir.resolve()
    for path in [current, *current.parents]:
        candidates.append(path / ".env")

    skill_dir = script_dir.parent
    for path in [script_dir, skill_dir]:
        env_path = path / ".env"
        if env_path not in candidates:
            candidates.append(env_path)
    return candidates


def load_dotenv(script_path: Path, env_path: Optional[Path] = None, start_dir: Optional[Path] = None) -> Optional[Path]:
    script_dir = script_path.resolve().parent
    search_roots = [env_path] if env_path else candidate_env_paths(start_dir or Path.cwd(), script_dir)
    for candidate in search_roots:
        if candidate is None or not candidate.exists():
            continue
        for raw_line in candidate.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if key:
                os.environ.setdefault(key, value)
        return candidate
    return None
