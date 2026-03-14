from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Optional


def sanitize_segment(value: str, fallback: str) -> str:
    value = value.strip() or fallback
    value = re.sub(r"[\\/:*?\"<>|]+", "-", value)
    value = re.sub(r"\s+", "-", value)
    return value[:60] or fallback


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


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def to_simple_yaml(data, indent: int = 0) -> str:
    prefix = "  " * indent
    if isinstance(data, dict):
        lines = []
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.append(to_simple_yaml(value, indent + 1))
            else:
                serialized = json.dumps(value, ensure_ascii=False)
                lines.append(f"{prefix}{key}: {serialized}")
        return "\n".join(lines)
    if isinstance(data, list):
        lines = []
        for value in data:
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}-")
                lines.append(to_simple_yaml(value, indent + 1))
            else:
                serialized = json.dumps(value, ensure_ascii=False)
                lines.append(f"{prefix}- {serialized}")
        return "\n".join(lines)
    return f"{prefix}{json.dumps(data, ensure_ascii=False)}"


def relative_to(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)
