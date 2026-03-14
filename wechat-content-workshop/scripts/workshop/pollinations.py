from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import PollinationsConfig, PollinationsQuotaStatus, QuotaDecision


REMOTE_TIMEOUT = 45
DEFAULT_PROXY_URL = "http://127.0.0.1:7890"
DEFAULT_POLLINATIONS_API_BASE = "https://gen.pollinations.ai"
DEFAULT_POLLINATIONS_ACCOUNT_API_BASE = "https://gen.pollinations.ai"
DEFAULT_POLLINATIONS_IMAGE_MODEL = "zimage"


def get_pollinations_config() -> PollinationsConfig:
    return PollinationsConfig(
        api_key=os.environ.get("POLLINATIONS_API_KEY", "").strip(),
        api_base=os.environ.get("POLLINATIONS_API_BASE", DEFAULT_POLLINATIONS_API_BASE).rstrip("/"),
        account_api_base=os.environ.get(
            "POLLINATIONS_ACCOUNT_API_BASE",
            os.environ.get("POLLINATIONS_API_BASE", DEFAULT_POLLINATIONS_ACCOUNT_API_BASE),
        ).rstrip("/"),
        image_model=os.environ.get("POLLINATIONS_IMAGE_MODEL", DEFAULT_POLLINATIONS_IMAGE_MODEL).strip()
        or DEFAULT_POLLINATIONS_IMAGE_MODEL,
    )


def with_pollinations_key(url: str, api_key: str) -> str:
    if not api_key:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}key={urllib.parse.quote(api_key)}"


def build_opener(proxy_url: Optional[str]) -> urllib.request.OpenerDirector:
    if proxy_url:
        return urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
        )
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def auth_headers(api_key: str, accept: Optional[str] = None) -> dict[str, str]:
    headers = {"User-Agent": "Mozilla/5.0"}
    if accept:
        headers["Accept"] = accept
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def read_json_error(exc: urllib.error.HTTPError) -> Optional[dict]:
    try:
        payload = exc.read().decode("utf-8")
    except Exception:
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


def classify_pollinations_error(exc: Exception) -> str:
    message = str(exc)
    for prefix in ["missing_key:", "auth_failed:", "quota_unavailable:", "generation_failed:"]:
        if message.startswith(prefix):
            return message
    if isinstance(exc, urllib.error.HTTPError):
        payload = read_json_error(exc) or {}
        message = (
            payload.get("error", {}).get("message")
            or payload.get("message")
            or exc.reason
            or exc.msg
            or str(exc)
        )
        if exc.code in {401, 403}:
            return f"auth_failed:{message}"
        if exc.code == 402:
            return f"quota_unavailable:{message}"
        return f"generation_failed:http_{exc.code}:{message}"
    if isinstance(exc, urllib.error.URLError):
        reason = exc.reason if isinstance(exc.reason, str) else repr(exc.reason)
        return f"generation_failed:network:{reason}"
    return f"generation_failed:{exc}"


def download_file(
    url: str,
    target: Path,
    proxy_url: Optional[str] = None,
    headers: Optional[dict[str, str]] = None,
) -> None:
    request = urllib.request.Request(
        url,
        headers=headers or {"User-Agent": "Mozilla/5.0"},
        method="GET",
    )
    opener = build_opener(proxy_url)
    with opener.open(request, timeout=REMOTE_TIMEOUT) as response:
        data = response.read()
    target.write_bytes(data)


def fetch_json(
    url: str,
    proxy_url: Optional[str] = None,
    headers: Optional[dict[str, str]] = None,
) -> dict:
    request = urllib.request.Request(
        url,
        headers=headers or {"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
        method="GET",
    )
    opener = build_opener(proxy_url)
    with opener.open(request, timeout=REMOTE_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_pollinations_quota(proxy_candidates: Optional[list[Optional[str]]] = None) -> PollinationsQuotaStatus:
    config = get_pollinations_config()
    if not config.api_key:
        return PollinationsQuotaStatus(
            ok=False,
            lines=[
                "Pollinations 额度: 未配置 POLLINATIONS_API_KEY，图片将自动切换为文字保底图。",
            ],
            errors=["missing_key:POLLINATIONS_API_KEY"],
        )

    proxies = proxy_candidates or [None, DEFAULT_PROXY_URL, None]
    headers = auth_headers(config.api_key, accept="application/json")
    errors: list[str] = []
    key_data = None
    balance_data = None

    for proxy_url in proxies:
        try:
            key_data = fetch_json(
                with_pollinations_key(f"{config.account_api_base}/account/key", config.api_key),
                proxy_url=proxy_url,
                headers=headers,
            )
            break
        except Exception as exc:
            errors.append(classify_pollinations_error(exc))

    for proxy_url in proxies:
        try:
            balance_data = fetch_json(
                with_pollinations_key(f"{config.account_api_base}/account/balance", config.api_key),
                proxy_url=proxy_url,
                headers=headers,
            )
            break
        except Exception as exc:
            errors.append(classify_pollinations_error(exc))

    lines = ["Pollinations 额度状态:"]
    if key_data:
        if "valid" in key_data:
            lines.append(f"- Key 状态: {'可用' if key_data.get('valid') else '不可用'}")
        if key_data.get("type"):
            lines.append(f"- Key 类型: {key_data['type']}")
        if key_data.get("permissions"):
            permissions = ", ".join(str(item) for item in key_data["permissions"])
            lines.append(f"- 权限: {permissions}")
        remaining_budget = key_data.get("remainingBudget")
        if remaining_budget is None:
            remaining_budget = key_data.get("remaining_budget")
        if remaining_budget is not None:
            lines.append(f"- Key 剩余额度: {remaining_budget}")
        expires_at = key_data.get("expiresAt") or key_data.get("expires_at")
        if expires_at:
            lines.append(f"- Key 到期: {expires_at}")

    if balance_data:
        balance = balance_data.get("balance")
        if balance is not None:
            lines.append(f"- 账户余额: {balance}")

    if key_data or balance_data:
        lines.append(f"- 查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return PollinationsQuotaStatus(
            ok=True,
            lines=lines,
            key_data=key_data,
            balance_data=balance_data,
            errors=errors,
        )

    return PollinationsQuotaStatus(
        ok=False,
        lines=[
            "Pollinations 额度: 查询失败，已继续执行内容生成。",
            f"- 原因: {' | '.join(errors) if errors else 'unknown_error'}",
        ],
        errors=errors,
    )


def _numeric_balance(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def decide_quota_strategy(quota_status: PollinationsQuotaStatus) -> QuotaDecision:
    if not quota_status.ok:
        if any(error.startswith("missing_key:") for error in quota_status.errors):
            return QuotaDecision(
                status="missing_key",
                allow_remote_generation=False,
                reason="missing_key",
                summary_lines=["图片策略决策: 未配置 Key，直接切换到本地文字保底图。"],
            )
        if any(error.startswith("auth_failed:") for error in quota_status.errors):
            return QuotaDecision(
                status="auth_failed",
                allow_remote_generation=False,
                reason="auth_failed",
                summary_lines=["图片策略决策: Key 鉴权失败，直接切换到本地文字保底图。"],
            )
        if any(error.startswith("quota_unavailable:") for error in quota_status.errors):
            return QuotaDecision(
                status="quota_insufficient",
                allow_remote_generation=False,
                reason="quota_unavailable",
                summary_lines=["图片策略决策: 额度不可用，直接切换到本地文字保底图。"],
            )
        return QuotaDecision(
            status="quota_check_failed",
            allow_remote_generation=True,
            reason="quota_check_failed",
            summary_lines=["图片策略决策: 额度查询失败，将继续尝试 AI 生图，失败后降级到本地文字保底图。"],
        )

    key_data = quota_status.key_data or {}
    balance_data = quota_status.balance_data or {}

    if key_data.get("valid") is False:
        return QuotaDecision(
            status="auth_failed",
            allow_remote_generation=False,
            reason="invalid_key",
            summary_lines=["图片策略决策: Key 状态不可用，直接切换到本地文字保底图。"],
        )

    remaining_budget = _numeric_balance(key_data.get("remainingBudget"))
    if remaining_budget is None:
        remaining_budget = _numeric_balance(key_data.get("remaining_budget"))
    balance = _numeric_balance(balance_data.get("balance"))
    if (remaining_budget is not None and remaining_budget <= 0) or (balance is not None and balance <= 0):
        return QuotaDecision(
            status="quota_insufficient",
            allow_remote_generation=False,
            reason="quota_insufficient",
            summary_lines=["图片策略决策: 检测到额度不足，直接切换到本地文字保底图。"],
        )

    return QuotaDecision(
        status="allowed",
        allow_remote_generation=True,
        reason="quota_available",
        summary_lines=["图片策略决策: 额度可用，优先尝试 AI 生图，单张失败时自动降级到本地文字保底图。"],
    )
