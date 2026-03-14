from __future__ import annotations

import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional, Tuple
from uuid import uuid4

from shared.wechat_content.common import load_dotenv, parse_yes_no


API_BASE_URL = "https://api.weixin.qq.com"
TOKEN_CACHE_FILE = ".token_cache.json"
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp"}


def load_env_file(script_path: Path, env_path: Optional[str] = None) -> None:
    load_dotenv(script_path, env_path=Path(env_path) if env_path else None)


def get_env_default_article_settings(script_path: Path) -> dict[str, Any]:
    load_env_file(script_path)
    return {
        "author": os.environ.get("WECHAT_AUTHOR", "").strip(),
        "need_open_comment": parse_yes_no(os.environ.get("WECHAT_NEED_OPEN_COMMENT"), 0),
        "only_fans_can_comment": parse_yes_no(os.environ.get("WECHAT_ONLY_FANS_CAN_COMMENT"), 0),
    }


def get_credentials(script_path: Path) -> Tuple[str, str]:
    load_env_file(script_path)
    appid = os.environ.get("WECHAT_APPID")
    appsecret = os.environ.get("WECHAT_APPSECRET")
    if not appid or not appsecret:
        print("Error: 微信凭证未配置", file=sys.stderr)
        print("请在 .env 文件中设置以下变量:", file=sys.stderr)
        print("  WECHAT_APPID=你的AppID", file=sys.stderr)
        print("  WECHAT_APPSECRET=你的AppSecret", file=sys.stderr)
        sys.exit(1)
    return appid, appsecret


def get_token_cache_path(script_path: Path) -> Path:
    return script_path.resolve().parent / TOKEN_CACHE_FILE


def load_cached_token(script_path: Path) -> Optional[dict]:
    cache_path = get_token_cache_path(script_path)
    if not cache_path.exists():
        return None
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        if data.get("expire_time", 0) > time.time() + 300:
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return None


def save_token_cache(script_path: Path, access_token: str, expires_in: int) -> None:
    cache_path = get_token_cache_path(script_path)
    cache_path.write_text(
        json.dumps(
            {
                "access_token": access_token,
                "expire_time": time.time() + expires_in,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def fetch_access_token(appid: str, appsecret: str, script_path: Path) -> str:
    url = (
        f"{API_BASE_URL}/cgi-bin/token"
        f"?grant_type=client_credential"
        f"&appid={appid}"
        f"&secret={appsecret}"
    )
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        print(f"Error: 网络错误 - {exc.reason}", file=sys.stderr)
        sys.exit(1)
    if "errcode" in data and data["errcode"] != 0:
        print("Error: 获取 access_token 失败", file=sys.stderr)
        print(f"  错误码: {data.get('errcode')}", file=sys.stderr)
        print(f"  错误信息: {data.get('errmsg')}", file=sys.stderr)
        sys.exit(1)

    access_token = data.get("access_token")
    expires_in = data.get("expires_in", 7200)
    save_token_cache(script_path, access_token, expires_in)
    print(f"✓ 成功获取 access_token (有效期 {expires_in // 60} 分钟)")
    return access_token


def get_access_token(script_path: Path) -> str:
    cached = load_cached_token(script_path)
    if cached:
        print("✓ 使用缓存的 access_token")
        return cached["access_token"]
    appid, appsecret = get_credentials(script_path)
    return fetch_access_token(appid, appsecret, script_path)


def call_wechat_api(
    endpoint: str,
    access_token: str,
    payload: Optional[dict[str, Any]] = None,
    *,
    method: str = "POST",
    timeout: int = 120,
) -> dict[str, Any]:
    url = f"{API_BASE_URL}{endpoint}?access_token={access_token}"
    body = None
    headers = {}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8") if exc.fp else ""
        print(f"Error: HTTP {exc.code} - {error_body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"Error: 网络错误 - {exc.reason}", file=sys.stderr)
        sys.exit(1)
    if "errcode" in data and data["errcode"] != 0:
        print("Error: 微信接口调用失败", file=sys.stderr)
        print(f"  接口: {endpoint}", file=sys.stderr)
        print(f"  错误码: {data.get('errcode')}", file=sys.stderr)
        print(f"  错误信息: {data.get('errmsg')}", file=sys.stderr)
        sys.exit(1)
    return data


def create_multipart_formdata(file_path: Path) -> Tuple[bytes, str]:
    boundary = f"----WebKitFormBoundary{uuid4().hex[:16]}"
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if not mime_type:
        mime_type = "image/jpeg"
    body = b"\r\n".join(
        [
            f"--{boundary}".encode(),
            f'Content-Disposition: form-data; name="media"; filename="{file_path.name}"'.encode(),
            f"Content-Type: {mime_type}".encode(),
            b"",
            file_path.read_bytes(),
            f"--{boundary}--".encode(),
        ]
    )
    return body, f"multipart/form-data; boundary={boundary}"


def upload_image(file_path: str, access_token: str) -> str:
    path = Path(file_path)
    if not path.exists():
        print(f"Error: 文件不存在 - {file_path}", file=sys.stderr)
        sys.exit(1)
    if path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        print(f"Error: 不支持的图片格式 - {path.suffix}", file=sys.stderr)
        sys.exit(1)
    body, content_type = create_multipart_formdata(path)
    request = urllib.request.Request(
        f"{API_BASE_URL}/cgi-bin/media/uploadimg?access_token={access_token}",
        data=body,
        headers={"Content-Type": content_type},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8") if exc.fp else ""
        print(f"Error: HTTP {exc.code} - {error_body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"Error: 网络错误 - {exc.reason}", file=sys.stderr)
        sys.exit(1)
    if "errcode" in data and data["errcode"] != 0:
        print("Error: 图片上传失败", file=sys.stderr)
        print(f"  错误码: {data.get('errcode')}", file=sys.stderr)
        print(f"  错误信息: {data.get('errmsg')}", file=sys.stderr)
        sys.exit(1)
    if not data.get("url"):
        print("Error: 上传成功但未返回URL", file=sys.stderr)
        sys.exit(1)
    print(f"✓ 图片上传成功: {path.name}")
    return data["url"]


def upload_thumb_material(file_path: str, access_token: str) -> str:
    path = Path(file_path)
    if not path.exists():
        print(f"Error: 封面文件不存在 - {file_path}", file=sys.stderr)
        sys.exit(1)
    body, content_type = create_multipart_formdata(path)
    request = urllib.request.Request(
        f"{API_BASE_URL}/cgi-bin/material/add_material?access_token={access_token}&type=thumb",
        data=body,
        headers={"Content-Type": content_type},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8") if exc.fp else ""
        print(f"Error: HTTP {exc.code} - {error_body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"Error: 网络错误 - {exc.reason}", file=sys.stderr)
        sys.exit(1)
    if "errcode" in data and data["errcode"] != 0:
        print("Error: 封面图片上传失败", file=sys.stderr)
        print(f"  错误码: {data.get('errcode')}", file=sys.stderr)
        print(f"  错误信息: {data.get('errmsg')}", file=sys.stderr)
        sys.exit(1)
    if not data.get("media_id"):
        print("Error: 上传成功但未返回 media_id", file=sys.stderr)
        sys.exit(1)
    print(f"✓ 封面图片上传成功: {path.name} -> {data['media_id'][:20]}...")
    return data["media_id"]


def build_draft_payload(
    *,
    title: str,
    content: str,
    thumb_media_id: Optional[str] = None,
    author: str = "",
    digest: str = "",
    need_open_comment: int = 0,
    only_fans_can_comment: int = 0,
) -> dict[str, Any]:
    article = {
        "title": title,
        "content": content,
        "content_source_url": "",
        "need_open_comment": need_open_comment,
        "only_fans_can_comment": only_fans_can_comment,
    }
    if author:
        article["author"] = author
    if digest:
        article["digest"] = digest
    if thumb_media_id:
        article["thumb_media_id"] = thumb_media_id
    return {"articles": [article]}


def create_draft(
    title: str,
    content: str,
    access_token: str,
    thumb_media_id: Optional[str] = None,
    author: str = "",
    digest: str = "",
    need_open_comment: int = 0,
    only_fans_can_comment: int = 0,
) -> dict[str, Any]:
    return call_wechat_api(
        "/cgi-bin/draft/add",
        access_token,
        build_draft_payload(
            title=title,
            content=content,
            thumb_media_id=thumb_media_id,
            author=author,
            digest=digest,
            need_open_comment=need_open_comment,
            only_fans_can_comment=only_fans_can_comment,
        ),
    )


def submit_freepublish(media_id: str, access_token: str) -> dict[str, Any]:
    return call_wechat_api("/cgi-bin/freepublish/submit", access_token, {"media_id": media_id})


def get_freepublish_status(publish_id: str, access_token: str) -> dict[str, Any]:
    return call_wechat_api("/cgi-bin/freepublish/get", access_token, {"publish_id": publish_id})


def batch_get_freepublish(access_token: str, offset: int = 0, count: int = 20) -> dict[str, Any]:
    return call_wechat_api(
        "/cgi-bin/freepublish/batchget",
        access_token,
        {"offset": offset, "count": count, "no_content": 0},
    )
