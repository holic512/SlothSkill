from __future__ import annotations

import urllib.parse
from dataclasses import asdict
from pathlib import Path
from typing import Callable, Optional

from .common import ensure_dir
from .fallback_renderers import render_text_card_png, write_simple_png
from .models import ContentPackage, ImageAsset, QuotaDecision
from .pollinations import (
    DEFAULT_PROXY_URL,
    classify_pollinations_error,
    download_file,
    get_pollinations_config,
    with_pollinations_key,
)


def source_pollinations(asset: ImageAsset, target: Path, proxy_url: Optional[str] = None) -> tuple[bool, str]:
    config = get_pollinations_config()
    if not config.api_key:
        raise RuntimeError("missing_key:POLLINATIONS_API_KEY")
    prompt = urllib.parse.quote(asset.prompt)
    url = (
        f"{config.api_base}/image/{prompt}"
        f"?width={asset.width}&height={asset.height}&seed=42&nologo=true"
        f"&model={urllib.parse.quote(config.image_model)}"
    )
    download_file(
        with_pollinations_key(url, config.api_key),
        target,
        proxy_url=proxy_url,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    return True, f"pollinations[{config.image_model}]"


IMAGE_SOURCES: list[Callable[[ImageAsset, Path, Optional[str]], tuple[bool, str]]] = [source_pollinations]


def attempt_remote_sources(
    sources: list[Callable[[ImageAsset, Path, Optional[str]], tuple[bool, str]]],
    asset: ImageAsset,
    target: Path,
    proxy_candidates: list[Optional[str]],
) -> tuple[bool, str, str]:
    failures = []
    for source in sources:
        for proxy_url in proxy_candidates:
            proxy_label = proxy_url or "direct"
            try:
                _, source_name = source(asset, target, proxy_url)
                via = "proxy-7890" if proxy_url else "direct"
                return True, f"{source_name}:{via}", ""
            except Exception as exc:
                failures.append(f"{source.__name__}@{proxy_label}: {classify_pollinations_error(exc)}")
    return False, "", " | ".join(failures)


def fallback_to_local(asset: ImageAsset, target: Path, failure_reason: str, strategy: str, decision_reason: str) -> dict:
    try:
        asset.source = render_text_card_png(asset, target)
    except Exception as exc:
        write_simple_png(target, asset.width, asset.height, asset.prompt, asset.role)
        asset.source = "local-simple-png"
        failure_reason = " | ".join(item for item in [failure_reason, f"text-card-render: {exc}"] if item)
    asset.local_path = str(target)
    asset.status = "generated"
    asset.generation_strategy = strategy
    asset.decision_reason = decision_reason
    asset.failure_reason = failure_reason
    return asdict(asset)


def materialize_images(
    package: ContentPackage,
    images_dir: Path,
    skip_images: bool,
    quota_decision: QuotaDecision,
    sources: Optional[list[Callable[[ImageAsset, Path, Optional[str]], tuple[bool, str]]]] = None,
) -> list[dict]:
    ensure_dir(images_dir)
    results = []
    active_sources = sources or IMAGE_SOURCES

    for index, plan in enumerate(package.image_plan, start=1):
        asset = ImageAsset(**plan)
        target = images_dir / f"{index:02d}-{asset.role}.png"

        if skip_images:
            asset.status = "skipped"
            asset.failure_reason = "image generation skipped by option"
            asset.generation_strategy = "skipped"
            asset.decision_reason = "skip_images"
            results.append(asdict(asset))
            continue

        if not quota_decision.allow_remote_generation:
            reason_map = {
                "missing_key": "missing_key:POLLINATIONS_API_KEY",
                "auth_failed": "auth_failed:quota_precheck",
                "quota_insufficient": "quota_unavailable:quota_precheck",
            }
            failure_reason = reason_map.get(quota_decision.status, quota_decision.reason)
            results.append(
                fallback_to_local(
                    asset,
                    target,
                    failure_reason,
                    strategy="local-fallback-direct",
                    decision_reason=quota_decision.status,
                )
            )
            continue

        proxy_candidates = [None, DEFAULT_PROXY_URL, None]
        success, source_name, failure_reason = attempt_remote_sources(
            active_sources,
            asset,
            target,
            proxy_candidates,
        )
        if success:
            asset.local_path = str(target)
            asset.source = source_name
            asset.status = "generated"
            asset.generation_strategy = "remote-ai"
            asset.decision_reason = quota_decision.status
            results.append(asdict(asset))
            continue

        results.append(
            fallback_to_local(
                asset,
                target,
                failure_reason,
                strategy="remote-then-local-fallback",
                decision_reason=quota_decision.status,
            )
        )

    return results
