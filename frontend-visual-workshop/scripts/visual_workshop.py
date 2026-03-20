#!/usr/bin/env python3
"""Generate planned or materialized visual assets for frontend projects."""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import zlib
from dataclasses import asdict, dataclass, field
from datetime import datetime
from hashlib import md5
from pathlib import Path
from typing import Optional


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
DEFAULT_OUTPUT_ROOT = SKILL_DIR / "output"
DEFAULT_PAGE_TYPE = "landing"
DEFAULT_STYLE_DIRECTION = "editorial-illustration"
DEFAULT_IMAGE_MODEL = "zimage"
DEFAULT_API_BASE = "https://gen.pollinations.ai"
DEFAULT_PROXY_URL = "http://127.0.0.1:7890"
REMOTE_TIMEOUT = 45
PROMPT_VERSION = "v1.1"
NEGATIVE_CONSTRAINTS = (
    "避免多手多指、乱码文字、水印、复杂背景、过度3D、廉价科技蓝紫渐变、"
    "无意义漂浮元素、过饱和霓虹色、密集小字。"
)

ASSET_SPECS = {
    "logo": {
        "width": 1024,
        "height": 1024,
        "usage_context": "品牌主标识，后续可裁切到导航栏、启动页和分享卡片",
        "purpose": "品牌 logo",
        "composition": "主体居中，轮廓明确，适合透明底二次处理",
        "style_limit": "扁平、几何、矢量感，不直接在图里生成文字",
        "title_space": "不需要文案区",
    },
    "favicon": {
        "width": 256,
        "height": 256,
        "usage_context": "浏览器标签、桌面快捷方式、小尺寸入口图标",
        "purpose": "favicon / app icon",
        "composition": "单元素图形，中心构图，16到64像素仍可辨认",
        "style_limit": "高对比、少细节、不放文字",
        "title_space": "不需要文案区",
    },
    "hero": {
        "width": 1536,
        "height": 1024,
        "usage_context": "首页 hero 区域，可与标题、副标题和 CTA 同屏",
        "purpose": "首页 hero 图",
        "composition": "保留一侧标题留白，视觉重心明确，不遮挡中文标题区域",
        "style_limit": "编辑感插画或高级图形感，不做空洞装饰",
        "title_space": "左侧或右侧预留约三分之一空白",
    },
    "feature": {
        "width": 1280,
        "height": 960,
        "usage_context": "功能解释模块或产品能力介绍卡片",
        "purpose": "功能说明插图",
        "composition": "突出一个动作或一个功能关系，层次清楚",
        "style_limit": "结构清晰，避免堆满 UI 假界面",
        "title_space": "局部留白，支持短标题覆盖",
    },
    "empty-state": {
        "width": 960,
        "height": 960,
        "usage_context": "空状态、加载失败、暂无内容等界面反馈",
        "purpose": "空状态插图",
        "composition": "主体简洁，留出提示文案位置，视觉负担低",
        "style_limit": "友好、安静、克制，不喧宾夺主",
        "title_space": "底部或侧边预留提示文案区",
    },
    "cover": {
        "width": 1200,
        "height": 630,
        "usage_context": "文章封面、社交分享预览图、项目卡片头图",
        "purpose": "横版封面图",
        "composition": "横版构图，大面积留白，安全裁切区域内保持主体",
        "style_limit": "清爽、编辑化、中文标题友好",
        "title_space": "左上或右下留标题区，避免主体冲突",
    },
}


@dataclass
class QuotaDecision:
    status: str
    allow_remote_generation: bool
    reason: str
    summary_lines: list[str]


@dataclass
class VisualAsset:
    role: str
    topic: str
    prompt: str
    width: int
    height: int
    style_direction: str
    usage_context: str
    brand: str = ""
    page_type: str = ""
    negative_prompt: str = NEGATIVE_CONSTRAINTS
    local_path: str = ""
    source: str = ""
    status: str = "planned"
    failure_reason: str = ""
    generation_strategy: str = ""
    decision_reason: str = ""


@dataclass
class VisualPackage:
    topic: str
    brand: str
    page_type: str
    style_direction: str
    asset_types: list[str]
    assets: list[dict]
    decision_notes: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def relative_to(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def sanitize_segment(value: str, fallback: str) -> str:
    value = value.strip() or fallback
    value = re.sub(r"[\\/:*?\"<>|]+", "-", value)
    value = re.sub(r"\s+", "-", value)
    return value[:60] or fallback


def load_dotenv(env_path: Optional[Path] = None, start_dir: Optional[Path] = None) -> Optional[Path]:
    candidates = []
    if env_path:
        candidates.append(env_path)
    current = (start_dir or Path.cwd()).resolve()
    for path in [current, *current.parents]:
        candidates.append(path / ".env")
    for path in [SKILL_DIR, SCRIPT_DIR]:
        candidates.append(path / ".env")

    seen = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen or not resolved.exists():
            continue
        seen.add(resolved)
        for line in resolved.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))
        return resolved
    return None


def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    length = len(data).to_bytes(4, "big")
    crc = zlib.crc32(chunk_type + data).to_bytes(4, "big")
    return length + chunk_type + data + crc


def write_simple_png(target: Path, width: int, height: int, prompt: str, role: str) -> None:
    width = max(32, width)
    height = max(32, height)
    digest = md5(f"{prompt}|{role}".encode("utf-8")).digest()
    base = (digest[0], digest[1], digest[2])
    accent = (digest[5], digest[6], digest[7])
    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            mix = (x * 255) // max(1, width - 1)
            color_a = base if (x // max(1, width // 6)) % 2 == 0 else accent
            color_b = accent if color_a == base else base
            r = (color_a[0] * (255 - mix) + color_b[0] * mix) // 255
            g = (color_a[1] * (255 - mix) + color_b[1] * mix) // 255
            b = (color_a[2] * (255 - mix) + color_b[2] * mix) // 255
            row.extend((r, g, b))
        rows.append(bytes(row))
    raw = b"".join(rows)
    png = b"\x89PNG\r\n\x1a\n"
    png += png_chunk(
        b"IHDR",
        width.to_bytes(4, "big") + height.to_bytes(4, "big") + b"\x08\x02\x00\x00\x00",
    )
    png += png_chunk(b"IDAT", zlib.compress(raw, level=9))
    png += png_chunk(b"IEND", b"")
    target.write_bytes(png)


def get_proxy_candidates() -> list[Optional[str]]:
    enabled = os.environ.get("POLLINATIONS_PROXY_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}
    proxy_url = os.environ.get("POLLINATIONS_PROXY_URL", DEFAULT_PROXY_URL).strip() or DEFAULT_PROXY_URL
    return [None, proxy_url] if enabled else [None]


def auth_headers(api_key: str, accept: Optional[str] = None) -> dict[str, str]:
    headers = {"User-Agent": "Mozilla/5.0"}
    if accept:
        headers["Accept"] = accept
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def request_bytes(url: str, proxy_url: Optional[str], headers: dict[str, str]) -> bytes:
    request = urllib.request.Request(url, headers=headers)
    handlers = [urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})] if proxy_url else [urllib.request.ProxyHandler({})]
    opener = urllib.request.build_opener(*handlers)
    with opener.open(request, timeout=REMOTE_TIMEOUT) as response:
        return response.read()


def fetch_json(url: str, proxy_url: Optional[str], headers: dict[str, str]) -> dict:
    payload = request_bytes(url, proxy_url, headers)
    return json.loads(payload.decode("utf-8"))


def download_file(url: str, target: Path, proxy_url: Optional[str], headers: dict[str, str]) -> None:
    target.write_bytes(request_bytes(url, proxy_url, headers))


def classify_remote_error(exc: Exception) -> str:
    message = str(exc)
    if message.startswith(("missing_key:", "auth_failed:", "quota_unavailable:", "generation_failed:")):
        return message
    if isinstance(exc, urllib.error.HTTPError):
        if exc.code in {401, 403}:
            return f"auth_failed:http_{exc.code}"
        if exc.code == 402:
            return f"quota_unavailable:http_{exc.code}"
        return f"generation_failed:http_{exc.code}"
    if isinstance(exc, urllib.error.URLError):
        return f"generation_failed:network:{exc.reason}"
    return f"generation_failed:{exc}"


def fetch_quota_decision() -> QuotaDecision:
    api_key = os.environ.get("POLLINATIONS_API_KEY", "").strip()
    api_base = os.environ.get("POLLINATIONS_ACCOUNT_API_BASE", DEFAULT_API_BASE).rstrip("/")
    if not api_key:
        return QuotaDecision(
            status="missing_key",
            allow_remote_generation=False,
            reason="missing_key",
            summary_lines=["图片策略决策: 未配置 Pollinations Key，直接切换到本地保底图。"],
        )

    errors = []
    headers = auth_headers(api_key, accept="application/json")
    for proxy_url in get_proxy_candidates():
        try:
            payload = fetch_json(f"{api_base}/account/balance", proxy_url, headers)
            balance = payload.get("balance")
            balance_value = float(balance) if balance is not None else 0.0
            if balance_value > 0:
                return QuotaDecision(
                    status="allowed",
                    allow_remote_generation=True,
                    reason="quota_available",
                    summary_lines=[f"图片策略决策: Pollinations 余额可用 ({balance})."],
                )
            return QuotaDecision(
                status="quota_insufficient",
                allow_remote_generation=True,
                reason="quota_insufficient",
                summary_lines=["图片策略决策: 余额不足，仍尝试远程生成，失败后回退本地。"],
            )
        except Exception as exc:
            errors.append(classify_remote_error(exc))

    if any(error.startswith("auth_failed:") for error in errors):
        return QuotaDecision(
            status="auth_failed",
            allow_remote_generation=False,
            reason="auth_failed",
            summary_lines=["图片策略决策: Key 鉴权失败，直接切换到本地保底图。"],
        )
    return QuotaDecision(
        status="quota_check_failed",
        allow_remote_generation=True,
        reason="quota_check_failed",
        summary_lines=["图片策略决策: 额度查询失败，继续尝试远程生成，失败后回退本地。"],
    )


def source_pollinations(asset: dict, target: Path, proxy_url: Optional[str]) -> str:
    api_key = os.environ.get("POLLINATIONS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("missing_key:POLLINATIONS_API_KEY")
    api_base = os.environ.get("POLLINATIONS_API_BASE", DEFAULT_API_BASE).rstrip("/")
    model = os.environ.get("POLLINATIONS_IMAGE_MODEL", DEFAULT_IMAGE_MODEL).strip() or DEFAULT_IMAGE_MODEL
    prompt = urllib.parse.quote(asset["prompt"])
    url = (
        f"{api_base}/image/{prompt}"
        f"?width={asset['width']}&height={asset['height']}&seed=42&nologo=true"
        f"&model={urllib.parse.quote(model)}&key={urllib.parse.quote(api_key)}"
    )
    download_file(url, target, proxy_url, auth_headers(api_key))
    return f"pollinations[{model}]"


def fallback_to_local(asset: dict, target: Path, failure_reason: str, strategy: str, decision_reason: str) -> dict:
    write_simple_png(target, asset["width"], asset["height"], asset["prompt"], asset["role"])
    result = dict(asset)
    result["local_path"] = str(target)
    result["source"] = "local-simple-png"
    result["status"] = "generated"
    result["failure_reason"] = failure_reason
    result["generation_strategy"] = strategy
    result["decision_reason"] = decision_reason
    return result


def materialize_assets(package: VisualPackage, output_dir: Path, skip_images: bool) -> VisualPackage:
    ensure_dir(output_dir / "assets")
    decision = fetch_quota_decision()
    for line in decision.summary_lines:
        print(line)

    rendered_assets = []
    proxy_candidates = get_proxy_candidates()
    for index, asset in enumerate(package.assets, start=1):
        target = output_dir / "assets" / f"{index:02d}-{asset['role']}.png"
        if skip_images:
            skipped = dict(asset)
            skipped["status"] = "skipped"
            skipped["failure_reason"] = "image generation skipped by option"
            skipped["generation_strategy"] = "skipped"
            skipped["decision_reason"] = "skip_images"
            rendered_assets.append(skipped)
            continue

        if not decision.allow_remote_generation:
            failure_reason = "missing_key:POLLINATIONS_API_KEY" if decision.status == "missing_key" else decision.reason
            rendered_assets.append(fallback_to_local(asset, target, failure_reason, "local-fallback-direct", decision.status))
            continue

        failures = []
        rendered = None
        for proxy_url in proxy_candidates:
            try:
                source = source_pollinations(asset, target, proxy_url)
                rendered = dict(asset)
                rendered["local_path"] = str(target)
                rendered["source"] = f"{source}:{'proxy' if proxy_url else 'direct'}"
                rendered["status"] = "generated"
                rendered["generation_strategy"] = "remote-ai"
                rendered["decision_reason"] = decision.status
                break
            except Exception as exc:
                failures.append(classify_remote_error(exc))

        if rendered is not None:
            rendered_assets.append(rendered)
            continue

        rendered_assets.append(
            fallback_to_local(
                asset,
                target,
                " | ".join(failures) if failures else "generation_failed:unknown",
                "remote-then-local-fallback",
                decision.status,
            )
        )

    package.assets = rendered_assets
    package.decision_notes.extend([f"quota_status={decision.status}", f"quota_reason={decision.reason}"])
    return package


def parse_asset_types(raw: str) -> list[str]:
    items = []
    for item in raw.split(","):
        key = item.strip().lower()
        if not key:
            continue
        if key not in ASSET_SPECS:
            raise ValueError(f"unsupported asset type: {key}")
        if key not in items:
            items.append(key)
    if not items:
        raise ValueError("at least one asset type is required")
    return items


def build_prompt(asset_type: str, topic: str, brand: str, page_type: str, style_direction: str) -> str:
    spec = ASSET_SPECS[asset_type]
    return (
        f"用途：{spec['purpose']}。"
        f"场景：围绕“{topic}”的{page_type}页面，品牌气质参考{brand or '未指定品牌'}。"
        f"构图要求：{spec['composition']}。"
        f"文案留白：{spec['title_space']}。"
        f"风格方向：{style_direction}，{spec['style_limit']}。"
        f"输出尺寸：{spec['width']}x{spec['height']}。"
        f"中文内容要求：适合中文标题覆盖，重点区域不要堆元素，局部对比清晰。"
        f"负向约束：{NEGATIVE_CONSTRAINTS}"
    )


def build_decision_notes(asset_types: list[str], page_type: str) -> list[str]:
    notes = [
        "只有当前端缺少必要视觉承载时才生成资产，不为了丰富而生图。",
        f"当前页面类型按 {page_type} 处理，优先生成直接影响理解和表达的资产。",
    ]
    if "logo" in asset_types or "favicon" in asset_types:
        notes.append("品牌资产优先识别度和小尺寸可读性，默认不在图中生成文字。")
    if "cover" in asset_types:
        notes.append("横版封面必须保留标题覆盖区和安全裁切。")
    return notes


def build_visual_package(topic: str, brand: str, page_type: str, asset_types: list[str], style_direction: str) -> VisualPackage:
    assets = []
    for asset_type in asset_types:
        spec = ASSET_SPECS[asset_type]
        assets.append(
            asdict(
                VisualAsset(
                    role=asset_type,
                    topic=topic,
                    prompt=build_prompt(asset_type, topic, brand, page_type, style_direction),
                    width=spec["width"],
                    height=spec["height"],
                    style_direction=style_direction,
                    usage_context=spec["usage_context"],
                    brand=brand,
                    page_type=page_type,
                )
            )
        )
    return VisualPackage(
        topic=topic,
        brand=brand,
        page_type=page_type,
        style_direction=style_direction,
        asset_types=asset_types,
        assets=assets,
        decision_notes=build_decision_notes(asset_types, page_type),
    )


def build_output_dir(args: argparse.Namespace) -> Path:
    if args.output_dir:
        return Path(args.output_dir).resolve()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return (DEFAULT_OUTPUT_ROOT / f"{stamp}-{sanitize_segment(args.topic, 'topic')}").resolve()


def write_prompt_files(package: VisualPackage, prompts_dir: Path) -> None:
    ensure_dir(prompts_dir)
    for asset in package.assets:
        save_text(prompts_dir / f"{asset['role']}.txt", asset["prompt"].strip() + "\n")


def write_package_json(package: VisualPackage, output_dir: Path) -> None:
    save_text(output_dir / "package.json", json.dumps(asdict(package), ensure_ascii=False, indent=2) + "\n")


def build_report(package: VisualPackage) -> str:
    lines = [
        "# Visual Asset Report",
        "",
        f"- topic: {package.topic}",
        f"- brand: {package.brand or 'N/A'}",
        f"- page_type: {package.page_type}",
        f"- style_direction: {package.style_direction}",
        f"- prompt_version: {PROMPT_VERSION}",
        f"- created_at: {package.created_at}",
        "",
        "## Decision Notes",
        "",
    ]
    lines.extend([f"- {note}" for note in package.decision_notes])
    lines.extend(["", "## Assets", ""])
    for asset in package.assets:
        lines.extend(
            [
                f"### {asset['role']}",
                f"- usage_context: {asset['usage_context']}",
                f"- size: {asset['width']}x{asset['height']}",
                f"- status: {asset['status']}",
                f"- source: {asset.get('source', '') or 'N/A'}",
                f"- generation_strategy: {asset.get('generation_strategy', '') or 'N/A'}",
                f"- decision_reason: {asset.get('decision_reason', '') or 'N/A'}",
                f"- failure_reason: {asset.get('failure_reason', '') or 'N/A'}",
                f"- local_path: {asset.get('local_path', '') or 'N/A'}",
                "",
                "Prompt:",
                "",
                "```text",
                asset["prompt"].strip(),
                "```",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def persist_package(package: VisualPackage, output_dir: Path) -> None:
    ensure_dir(output_dir)
    ensure_dir(output_dir / "assets")
    write_prompt_files(package, output_dir / "prompts")
    write_package_json(package, output_dir)
    save_text(output_dir / "report.md", build_report(package))


def cmd_plan(args: argparse.Namespace) -> int:
    package = build_visual_package(args.topic, args.brand, args.page_type, parse_asset_types(args.asset_types), args.style_direction)
    output_dir = build_output_dir(args)
    persist_package(package, output_dir)
    print(f"视觉资产计划已生成: {output_dir}")
    print(f"提示词目录: {output_dir / 'prompts'}")
    print(f"报告文件: {output_dir / 'report.md'}")
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    package = build_visual_package(args.topic, args.brand, args.page_type, parse_asset_types(args.asset_types), args.style_direction)
    output_dir = build_output_dir(args)
    package = materialize_assets(package, output_dir, skip_images=args.skip_images)
    persist_package(package, output_dir)
    print(f"视觉资产已输出: {output_dir}")
    for asset in package.assets:
        label = relative_to(output_dir, Path(asset["local_path"])) if asset.get("local_path") else "N/A"
        print(f"- {asset['role']}: {label}")
    print(f"报告文件: {output_dir / 'report.md'}")
    return 0


def cmd_test_image(args: argparse.Namespace) -> int:
    args.skip_images = False
    return cmd_generate(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate frontend visual assets with prompt tuning and fallback rendering.")
    parser.add_argument("--env-file", default="", help="Optional .env file path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common_arguments(target: argparse.ArgumentParser) -> None:
        target.add_argument("--topic", required=True, help="Core topic or product name")
        target.add_argument("--brand", default="", help="Brand name or style anchor")
        target.add_argument("--page-type", default=DEFAULT_PAGE_TYPE, help="Page type such as landing, article, dashboard")
        target.add_argument("--asset-types", required=True, help="Comma separated asset types: logo,favicon,hero,feature,empty-state,cover")
        target.add_argument("--style-direction", default=DEFAULT_STYLE_DIRECTION, help="Overall visual direction")
        target.add_argument("--output-dir", default="", help="Directory for assets, prompts, and report")

    plan_parser = subparsers.add_parser("plan", help="Generate plan, prompts, and report without rendering images")
    add_common_arguments(plan_parser)
    plan_parser.set_defaults(func=cmd_plan)

    generate_parser = subparsers.add_parser("generate", help="Generate prompts and render image assets")
    add_common_arguments(generate_parser)
    generate_parser.add_argument("--skip-images", action="store_true", help="Skip image rendering and keep prompt package only")
    generate_parser.set_defaults(func=cmd_generate)

    test_parser = subparsers.add_parser("test-image", help="Render a small set of chosen asset types")
    add_common_arguments(test_parser)
    test_parser.set_defaults(func=cmd_test_image)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    load_dotenv(Path(args.env_file).resolve() if args.env_file else None, Path.cwd())
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
