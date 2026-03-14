from __future__ import annotations

import io
import json
import os
import subprocess
import tempfile
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


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


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
        proxy_enabled=_env_flag("POLLINATIONS_PROXY_ENABLED", default=False),
        proxy_url=os.environ.get("POLLINATIONS_PROXY_URL", DEFAULT_PROXY_URL).strip() or DEFAULT_PROXY_URL,
    )


def get_proxy_candidates(config: Optional[PollinationsConfig] = None) -> list[Optional[str]]:
    active_config = config or get_pollinations_config()
    candidates: list[Optional[str]] = [None]
    if active_config.proxy_enabled and active_config.proxy_url:
        candidates.extend([active_config.proxy_url, None])
    return candidates


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


def _curl_request(
    url: str,
    proxy_url: Optional[str] = None,
    headers: Optional[dict[str, str]] = None,
) -> bytes:
    with tempfile.NamedTemporaryFile(delete=False) as body_file:
        body_path = Path(body_file.name)

    command = [
        "curl",
        "--silent",
        "--show-error",
        "--location",
        "--max-time",
        str(REMOTE_TIMEOUT),
        "--output",
        str(body_path),
        "--write-out",
        "%{http_code}",
    ]
    if proxy_url:
        command.extend(["--proxy", proxy_url])
    for key, value in (headers or {}).items():
        command.extend(["-H", f"{key}: {value}"])
    command.append(url)

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        status_code = int((result.stdout or "0").strip() or "0")
        body = body_path.read_bytes()
    finally:
        body_path.unlink(missing_ok=True)

    if result.returncode == 0 and 200 <= status_code < 300:
        return body

    message = (result.stderr or "").strip() or f"HTTP {status_code or 'request_failed'}"
    if status_code >= 400:
        raise urllib.error.HTTPError(url, status_code, message, hdrs=None, fp=io.BytesIO(body))
    raise urllib.error.URLError(message)


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
    data = _curl_request(
        url,
        proxy_url=proxy_url,
        headers=headers or {"User-Agent": "Mozilla/5.0"},
    )
    target.write_bytes(data)


def fetch_json(
    url: str,
    proxy_url: Optional[str] = None,
    headers: Optional[dict[str, str]] = None,
) -> dict:
    payload = _curl_request(
        url,
        proxy_url=proxy_url,
        headers=headers or {"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
    )
    return json.loads(payload.decode("utf-8"))


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

    proxies = proxy_candidates or get_proxy_candidates(config)
    headers = auth_headers(config.api_key, accept="application/json")
    errors: list[str] = []
    balance_data = None

    for proxy_url in proxies:
        try:
            balance_data = fetch_json(
                f"{config.account_api_base}/account/balance",
                proxy_url=proxy_url,
                headers=headers,
            )
            break
        except Exception as exc:
            errors.append(classify_pollinations_error(exc))

    lines = ["Pollinations 余额状态:"]
    if balance_data:
        balance = balance_data.get("balance")
        if balance is not None:
            lines.append(f"- 当前余额: {balance}")

    if balance_data:
        lines.append(f"- 查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return PollinationsQuotaStatus(
            ok=True,
            lines=lines,
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
            allow_remote_generation=True,
            reason="quota_insufficient",
            summary_lines=["图片策略决策: 检测到余额不足，仍会尝试 AI 生图，单张失败时自动降级到本地文字保底图。"],
        )

    return QuotaDecision(
        status="allowed",
        allow_remote_generation=True,
        reason="quota_available",
        summary_lines=["图片策略决策: 额度可用，优先尝试 AI 生图，单张失败时自动降级到本地文字保底图。"],
    )
