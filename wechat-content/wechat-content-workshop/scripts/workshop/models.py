from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ImageAsset:
    role: str
    topic: str
    prompt: str
    local_path: str = ""
    source: str = ""
    width: int = 0
    height: int = 0
    status: str = "planned"
    failure_reason: str = ""
    generation_strategy: str = ""
    decision_reason: str = ""


@dataclass
class ContentPackage:
    topic: str
    date: str
    channel: str
    series: str
    content_type: str
    title: str
    summary: str
    body_markdown: str
    author: str
    need_open_comment: int
    only_fans_can_comment: int
    cover_copy: str
    image_plan: list[dict]
    share_text: dict
    closing_cta: str
    style_notes: dict
    assets: list[dict] = field(default_factory=list)


@dataclass
class PollinationsConfig:
    api_key: str
    api_base: str
    account_api_base: str
    image_model: str
    proxy_enabled: bool
    proxy_url: str


@dataclass
class PollinationsQuotaStatus:
    ok: bool
    lines: list[str]
    key_data: dict | None = None
    balance_data: dict | None = None
    errors: list[str] = field(default_factory=list)


@dataclass
class QuotaDecision:
    status: str
    allow_remote_generation: bool
    reason: str
    summary_lines: list[str]
