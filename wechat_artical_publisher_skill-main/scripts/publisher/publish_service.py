from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional

from shared.wechat_content.article_loader import ArticleDocument, find_images_in_markdown

from .wechat_api_client import (
    build_draft_payload,
    create_draft,
    get_env_default_article_settings,
    get_freepublish_status,
    submit_freepublish,
    upload_image,
    upload_thumb_material,
)


DEFAULT_POLL_INTERVAL = 5
DEFAULT_POLL_TIMEOUT = 180
BMMD_API_URL = "https://bm.md/api/markdown/render"


def resolve_publish_settings(
    article: ArticleDocument,
    script_path: Path,
    *,
    cli_author: str = "",
    cli_need_open_comment: Optional[str] = None,
    cli_only_fans_can_comment: Optional[str] = None,
) -> dict[str, Any]:
    env_defaults = get_env_default_article_settings(script_path)
    return {
        "author": (cli_author or article.author or env_defaults["author"]).strip(),
        "need_open_comment": _resolve_int(cli_need_open_comment, article.need_open_comment, env_defaults["need_open_comment"]),
        "only_fans_can_comment": _resolve_int(
            cli_only_fans_can_comment,
            article.only_fans_can_comment,
            env_defaults["only_fans_can_comment"],
        ),
    }


def _resolve_int(cli_value: Optional[str], article_value: Optional[int], env_value: Optional[int]) -> int:
    if cli_value is not None:
        return int(cli_value)
    if article_value is not None:
        return article_value
    if env_value is not None:
        return env_value
    return 0


def markdown_to_html(content: str) -> str:
    html = content
    html = re.sub(r"```(\w*)\n(.*?)```", r"<pre><code>\2</code></pre>", html, flags=re.DOTALL)
    html = re.sub(r"`([^`]+)`", r"<code>\1</code>", html)
    html = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", html)
    html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)
    html = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img src="\2" alt="\1">', html)
    html = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', html)
    html = re.sub(r"^> (.+)$", r"<blockquote>\1</blockquote>", html, flags=re.MULTILINE)
    html = re.sub(r"^---+$", r"<hr>", html, flags=re.MULTILINE)
    paragraphs = []
    current_para = []
    for line in html.split("\n"):
        stripped = line.strip()
        if re.match(r"^<(h[1-6]|pre|blockquote|hr|ul|ol|li|div|img)", stripped):
            if current_para:
                paragraphs.append("<p>" + " ".join(current_para) + "</p>")
                current_para = []
            paragraphs.append(stripped)
        elif stripped:
            current_para.append(stripped)
        else:
            if current_para:
                paragraphs.append("<p>" + " ".join(current_para) + "</p>")
                current_para = []
    if current_para:
        paragraphs.append("<p>" + " ".join(current_para) + "</p>")
    return "\n".join(paragraphs)


def load_custom_css(script_path: Path) -> str:
    css_path = script_path.resolve().parent.parent / "styles" / "custom.css"
    if css_path.exists():
        return css_path.read_text(encoding="utf-8")
    print("Warning: 未找到 custom.css，将使用默认样式", file=sys.stderr)
    return ""


def render_with_bmmd(markdown_content: str, script_path: Path, use_fallback: bool = True) -> str:
    payload = {
        "markdown": markdown_content,
        "markdownStyle": "green-simple",
        "platform": "wechat",
        "enableFootnoteLinks": True,
        "openLinksInNewWindow": True,
        "customCss": load_custom_css(script_path),
    }
    request = urllib.request.Request(
        BMMD_API_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
        method="POST",
    )
    try:
        print("调用 bm.md API 渲染精美格式...")
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
        result = data.get("html") or data.get("content") or data.get("result")
        if result:
            print("✓ bm.md 渲染成功")
            return convert_lists_to_paragraphs(result)
    except (urllib.error.HTTPError, urllib.error.URLError, ValueError, TimeoutError) as exc:
        print(f"Warning: bm.md 渲染失败: {exc}", file=sys.stderr)
    if use_fallback:
        print("使用本地简单转换作为后备...")
        return markdown_to_html(markdown_content)
    return markdown_content


def convert_lists_to_paragraphs(html: str) -> str:
    def replace_ol(match):
        items = re.findall(r"<li[^>]*>(.*?)</li>", match.group(1), flags=re.DOTALL | re.IGNORECASE)
        return "\n".join(
            f'<p style="margin: 5px 0 10px; line-height: 1.75em;"><span style="color: #2bae85; font-weight: bold;">{idx}. </span>{item.strip()}</p>'
            for idx, item in enumerate(items, 1)
        )

    def replace_ul(match):
        items = re.findall(r"<li[^>]*>(.*?)</li>", match.group(1), flags=re.DOTALL | re.IGNORECASE)
        return "\n".join(
            f'<p style="margin: 5px 0 10px; line-height: 1.75em;"><span style="color: #2bae85; font-weight: bold;">• </span>{item.strip()}</p>'
            for item in items
        )

    html = re.sub(r"<ol[^>]*>(.*?)</ol>", replace_ol, html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<ul[^>]*>(.*?)</ul>", replace_ul, html, flags=re.DOTALL | re.IGNORECASE)
    print("✓ 列表已转换为段落格式 (微信移动端兼容)")
    return html


def process_markdown_images(content: str, base_path: Path, access_token: str) -> str:
    images = find_images_in_markdown(content, base_path)
    local_images = [(orig, abs_path) for orig, abs_path, is_local in images if is_local]
    if not local_images:
        print("ℹ 没有本地图片需要上传")
        return content
    print(f"\n正在上传 {len(local_images)} 张本地图片...")
    result = content
    for index, (orig_path, abs_path) in enumerate(local_images, 1):
        print(f"  [{index}/{len(local_images)}] ", end="")
        wechat_url = upload_image(abs_path, access_token)
        result = re.sub(r"(!\[[^\]]*\]\()" + re.escape(orig_path) + r"(\))", r"\1" + wechat_url + r"\2", result)
    print("✓ 所有图片已上传并替换为微信URL\n")
    return result


def resolve_cover_path(article: ArticleDocument) -> Optional[Path]:
    if not article.cover_image:
        return None
    cover_path = Path(article.cover_image)
    if cover_path.is_absolute():
        return cover_path if cover_path.exists() else None
    if article.package_dir:
        candidate = article.package_dir / "final" / cover_path
        if candidate.exists():
            return candidate.resolve()
    if article.source_path:
        candidate = article.source_path.parent / cover_path
        if candidate.exists():
            return candidate.resolve()
    return None


def format_publish_status(status_data: dict[str, Any]) -> str:
    status_desc = {
        0: "成功",
        1: "发布中",
        2: "原创失败",
        3: "常规失败",
        4: "平台审核中",
        5: "平台审核拒绝",
        6: "已撤回",
    }.get(status_data.get("publish_status"), f"未知状态({status_data.get('publish_status')})")
    parts = [f"发布状态: {status_desc}"]
    for key in ("publish_id", "article_id", "article_detail", "fail_idx", "errmsg"):
        value = status_data.get(key)
        if value not in (None, "", []):
            parts.append(f"{key}: {value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)}")
    return "\n".join(parts)


def wait_for_publish_result(
    publish_id: str,
    access_token: str,
    interval: int = DEFAULT_POLL_INTERVAL,
    timeout: int = DEFAULT_POLL_TIMEOUT,
) -> dict[str, Any]:
    deadline = time.time() + timeout
    latest: dict[str, Any] = {}
    while time.time() < deadline:
        latest = get_freepublish_status(publish_id, access_token)
        print(format_publish_status(latest))
        if latest.get("publish_status") in {0, 2, 3, 5, 6}:
            return latest
        print(f"等待 {interval} 秒后继续查询...")
        time.sleep(interval)
    print("Warning: 发布状态轮询超时，请稍后手动查询。", file=sys.stderr)
    return latest


def prompt_publish_mode(default_mode: str) -> str:
    if not sys.stdin.isatty():
        print(f"ℹ 非交互环境，默认使用 {default_mode} 模式")
        return default_mode
    print("请选择发布方式：")
    print("  1. 发送到草稿")
    print("  2. 直接发布")
    while True:
        choice = input("输入 1 或 2: ").strip()
        if choice == "1":
            return "draft"
        if choice == "2":
            return "publish"
        print("输入无效，请重新输入。")


def publish_article(
    article: ArticleDocument,
    access_token: str,
    script_path: Path,
    *,
    mode: str,
    author: str,
    need_open_comment: int,
    only_fans_can_comment: int,
    poll_interval: int,
    poll_timeout: int,
) -> dict[str, Any]:
    assert article.source_path is not None
    processed_content = process_markdown_images(article.body_markdown, article.source_path.parent, access_token)
    processed_content = re.sub(r"^\s*---\s*$", "", processed_content, flags=re.MULTILINE)
    thumb_media_id = None
    cover_path = resolve_cover_path(article)
    if cover_path is not None:
        print("\n上传封面图片...")
        thumb_media_id = upload_thumb_material(str(cover_path), access_token)

    html_content = render_with_bmmd(processed_content, script_path)
    print("正在创建草稿...")
    result = create_draft(
        title=article.title,
        content=html_content,
        access_token=access_token,
        thumb_media_id=thumb_media_id,
        author=author,
        digest=article.summary or "",
        need_open_comment=need_open_comment,
        only_fans_can_comment=only_fans_can_comment,
    )
    if mode == "draft":
        return result
    media_id = result.get("media_id", "")
    if not media_id:
        print("Error: 草稿已创建，但未返回 media_id，无法继续发布。", file=sys.stderr)
        sys.exit(1)
    print("\n正在提交发布任务...")
    publish_result = submit_freepublish(media_id, access_token)
    publish_id = publish_result.get("publish_id")
    print(f"  Publish ID: {publish_id or 'N/A'}")
    if not publish_id:
        return publish_result
    print("\n开始轮询发布状态...")
    return {
        "draft": result,
        "submit": publish_result,
        "status": wait_for_publish_result(publish_id, access_token, interval=poll_interval, timeout=poll_timeout),
    }


__all__ = [
    "DEFAULT_POLL_INTERVAL",
    "DEFAULT_POLL_TIMEOUT",
    "build_draft_payload",
    "convert_lists_to_paragraphs",
    "format_publish_status",
    "markdown_to_html",
    "process_markdown_images",
    "prompt_publish_mode",
    "publish_article",
    "render_with_bmmd",
    "resolve_publish_settings",
]
