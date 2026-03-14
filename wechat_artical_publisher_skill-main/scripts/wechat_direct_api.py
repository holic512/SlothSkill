#!/usr/bin/env python3
"""
WeChat Direct API Publisher - 微信公众号直连版发布工具

直接调用微信官方API实现：
- Access Token 获取与缓存
- 图片上传至微信素材库
- 草稿创建

要求：
- IP必须在微信公众号后台白名单中
- 需要 WECHAT_APPID 和 WECHAT_APPSECRET 环境变量
"""

import argparse
import json
import mimetypes
import os
import re
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Optional, Tuple
from uuid import uuid4


# ============================================================================
# 配置
# ============================================================================

API_BASE_URL = "https://api.weixin.qq.com"
TOKEN_CACHE_FILE = ".token_cache.json"

# 支持的图片格式
SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}


# ============================================================================
# 环境变量加载
# ============================================================================

def load_env_file(env_path: Optional[str] = None) -> None:
    """
    从 .env 文件加载环境变量。
    
    Args:
        env_path: .env 文件路径。如果未提供，会在当前目录及父目录中搜索。
    """
    if env_path:
        env_file = Path(env_path)
    else:
        # 在当前目录和父目录中搜索 .env 文件
        current = Path(__file__).parent
        env_file = None
        for _ in range(5):  # 最多向上搜索5层
            candidate = current / ".env"
            if candidate.exists():
                env_file = candidate
                break
            # 也检查 scripts 目录的父目录
            parent_candidate = current.parent / ".env"
            if parent_candidate.exists():
                env_file = parent_candidate
                break
            current = current.parent

    if env_file and env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and value:
                        os.environ.setdefault(key, value)


def get_credentials() -> Tuple[str, str]:
    """
    获取微信公众号凭证。
    
    Returns:
        (appid, appsecret) 元组
        
    Raises:
        SystemExit: 如果凭证未配置
    """
    load_env_file()
    
    appid = os.environ.get("WECHAT_APPID")
    appsecret = os.environ.get("WECHAT_APPSECRET")
    
    if not appid or not appsecret:
        print("Error: 微信凭证未配置", file=sys.stderr)
        print("请在 .env 文件中设置以下变量:", file=sys.stderr)
        print("  WECHAT_APPID=你的AppID", file=sys.stderr)
        print("  WECHAT_APPSECRET=你的AppSecret", file=sys.stderr)
        sys.exit(1)
    
    return appid, appsecret


# ============================================================================
# Access Token 管理
# ============================================================================

def get_token_cache_path() -> Path:
    """获取 token 缓存文件路径"""
    return Path(__file__).parent / TOKEN_CACHE_FILE


def load_cached_token() -> Optional[dict]:
    """
    从缓存加载 access_token。
    
    Returns:
        缓存数据 (含 access_token 和 expire_time)，或 None
    """
    cache_path = get_token_cache_path()
    if not cache_path.exists():
        return None
    
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # 检查是否过期 (提前5分钟刷新)
            if data.get("expire_time", 0) > time.time() + 300:
                return data
    except (json.JSONDecodeError, IOError):
        pass
    
    return None


def save_token_cache(access_token: str, expires_in: int) -> None:
    """
    保存 access_token 到缓存。
    
    Args:
        access_token: 访问令牌
        expires_in: 有效期（秒）
    """
    cache_path = get_token_cache_path()
    data = {
        "access_token": access_token,
        "expire_time": time.time() + expires_in,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def fetch_access_token(appid: str, appsecret: str) -> str:
    """
    从微信API获取新的 access_token。
    
    Args:
        appid: 公众号 AppID
        appsecret: 公众号 AppSecret
        
    Returns:
        access_token 字符串
        
    Raises:
        SystemExit: API调用失败
    """
    url = (
        f"{API_BASE_URL}/cgi-bin/token"
        f"?grant_type=client_credential"
        f"&appid={appid}"
        f"&secret={appsecret}"
    )
    
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as e:
        print(f"Error: 网络错误 - {e.reason}", file=sys.stderr)
        sys.exit(1)
    
    if "errcode" in data and data["errcode"] != 0:
        print(f"Error: 获取 access_token 失败", file=sys.stderr)
        print(f"  错误码: {data.get('errcode')}", file=sys.stderr)
        print(f"  错误信息: {data.get('errmsg')}", file=sys.stderr)
        
        # 常见错误提示
        errcode = data.get("errcode")
        if errcode == 40164:
            print("\n提示: IP 未在白名单中。请在微信公众号后台添加当前IP到白名单。", file=sys.stderr)
        elif errcode == 40001:
            print("\n提示: AppSecret 错误。请检查 WECHAT_APPSECRET 配置。", file=sys.stderr)
        elif errcode == 40013:
            print("\n提示: AppID 错误。请检查 WECHAT_APPID 配置。", file=sys.stderr)
        
        sys.exit(1)
    
    access_token = data.get("access_token")
    expires_in = data.get("expires_in", 7200)
    
    # 缓存 token
    save_token_cache(access_token, expires_in)
    
    print(f"✓ 成功获取 access_token (有效期 {expires_in // 60} 分钟)")
    return access_token


def get_access_token() -> str:
    """
    获取 access_token（优先使用缓存）。
    
    Returns:
        access_token 字符串
    """
    # 尝试从缓存读取
    cached = load_cached_token()
    if cached:
        print("✓ 使用缓存的 access_token")
        return cached["access_token"]
    
    # 获取新 token
    appid, appsecret = get_credentials()
    return fetch_access_token(appid, appsecret)


# ============================================================================
# 图片上传
# ============================================================================

def create_multipart_formdata(file_path: Path) -> Tuple[bytes, str]:
    """
    创建 multipart/form-data 请求体。
    
    Args:
        file_path: 图片文件路径
        
    Returns:
        (body_bytes, content_type) 元组
    """
    boundary = f"----WebKitFormBoundary{uuid4().hex[:16]}"
    
    # 获取文件的 MIME 类型
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if not mime_type:
        mime_type = "image/jpeg"
    
    # 构建 multipart body
    lines = []
    lines.append(f"--{boundary}".encode())
    lines.append(
        f'Content-Disposition: form-data; name="media"; filename="{file_path.name}"'.encode()
    )
    lines.append(f"Content-Type: {mime_type}".encode())
    lines.append(b"")
    
    with open(file_path, "rb") as f:
        file_data = f.read()
    
    lines.append(file_data)
    lines.append(f"--{boundary}--".encode())
    
    body = b"\r\n".join(lines)
    content_type = f"multipart/form-data; boundary={boundary}"
    
    return body, content_type


def upload_image(file_path: str, access_token: str) -> str:
    """
    上传图片到微信素材库（用于图文消息）。
    
    调用接口: /cgi-bin/media/uploadimg
    
    Args:
        file_path: 本地图片路径
        access_token: 访问令牌
        
    Returns:
        微信图片 URL (mmbiz.qpic.cn 域名)
        
    Raises:
        SystemExit: 上传失败
    """
    path = Path(file_path)
    
    if not path.exists():
        print(f"Error: 文件不存在 - {file_path}", file=sys.stderr)
        sys.exit(1)
    
    if path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        print(f"Error: 不支持的图片格式 - {path.suffix}", file=sys.stderr)
        print(f"  支持的格式: {', '.join(SUPPORTED_IMAGE_EXTENSIONS)}", file=sys.stderr)
        sys.exit(1)
    
    url = f"{API_BASE_URL}/cgi-bin/media/uploadimg?access_token={access_token}"
    
    body, content_type = create_multipart_formdata(path)
    
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": content_type},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        print(f"Error: HTTP {e.code} - {error_body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: 网络错误 - {e.reason}", file=sys.stderr)
        sys.exit(1)
    
    if "errcode" in data and data["errcode"] != 0:
        print(f"Error: 图片上传失败", file=sys.stderr)
        print(f"  错误码: {data.get('errcode')}", file=sys.stderr)
        print(f"  错误信息: {data.get('errmsg')}", file=sys.stderr)
        sys.exit(1)
    
    wechat_url = data.get("url")
    if not wechat_url:
        print("Error: 上传成功但未返回URL", file=sys.stderr)
        print(f"  返回数据: {data}", file=sys.stderr)
        sys.exit(1)
    
    print(f"✓ 图片上传成功: {path.name}")
    return wechat_url


def upload_thumb_material(file_path: str, access_token: str) -> str:
    """
    上传封面图片到微信永久素材库，获取 media_id。
    
    调用接口: /cgi-bin/material/add_material?type=thumb
    
    Args:
        file_path: 本地图片路径
        access_token: 访问令牌
        
    Returns:
        media_id 字符串
        
    Raises:
        SystemExit: 上传失败
    """
    path = Path(file_path)
    
    if not path.exists():
        print(f"Error: 封面文件不存在 - {file_path}", file=sys.stderr)
        sys.exit(1)
    
    url = f"{API_BASE_URL}/cgi-bin/material/add_material?access_token={access_token}&type=thumb"
    
    body, content_type = create_multipart_formdata(path)
    
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": content_type},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        print(f"Error: HTTP {e.code} - {error_body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: 网络错误 - {e.reason}", file=sys.stderr)
        sys.exit(1)
    
    if "errcode" in data and data["errcode"] != 0:
        print(f"Error: 封面图片上传失败", file=sys.stderr)
        print(f"  错误码: {data.get('errcode')}", file=sys.stderr)
        print(f"  错误信息: {data.get('errmsg')}", file=sys.stderr)
        sys.exit(1)
    
    media_id = data.get("media_id")
    if not media_id:
        print("Error: 上传成功但未返回 media_id", file=sys.stderr)
        print(f"  返回数据: {data}", file=sys.stderr)
        sys.exit(1)
    
    print(f"✓ 封面图片上传成功: {path.name} -> {media_id[:20]}...")
    return media_id


# ============================================================================
# Markdown 处理
# ============================================================================

def find_images_in_markdown(content: str, base_path: Path) -> list:
    """
    在 Markdown 内容中查找图片引用。
    
    Args:
        content: Markdown 内容
        base_path: Markdown 文件所在目录
        
    Returns:
        [(原始路径, 绝对路径, 是否为本地文件), ...] 列表
    """
    images = []
    
    # 匹配 Markdown 图片语法: ![alt](path)
    md_pattern = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')
    
    for match in md_pattern.finditer(content):
        img_path = match.group(1)
        
        # 跳过已是网络URL的图片
        if img_path.startswith(("http://", "https://", "data:")):
            images.append((img_path, img_path, False))
            continue
        
        # 解析本地路径
        if os.path.isabs(img_path):
            abs_path = Path(img_path)
        else:
            abs_path = base_path / img_path
        
        if abs_path.exists():
            images.append((img_path, str(abs_path.absolute()), True))
        else:
            print(f"Warning: 图片不存在 - {img_path}", file=sys.stderr)
            images.append((img_path, img_path, False))
    
    return images


def process_markdown_images(content: str, base_path: Path, access_token: str) -> str:
    """
    处理 Markdown 中的本地图片：上传并替换为微信URL。
    
    Args:
        content: Markdown 内容
        base_path: Markdown 文件所在目录
        access_token: 访问令牌
        
    Returns:
        处理后的 Markdown 内容
    """
    images = find_images_in_markdown(content, base_path)
    local_images = [(orig, abs_path) for orig, abs_path, is_local in images if is_local]
    
    if not local_images:
        print("ℹ 没有本地图片需要上传")
        return content
    
    print(f"\n正在上传 {len(local_images)} 张本地图片...")
    
    # 上传所有本地图片
    url_mapping = {}
    for i, (orig_path, abs_path) in enumerate(local_images, 1):
        print(f"  [{i}/{len(local_images)}] ", end="")
        wechat_url = upload_image(abs_path, access_token)
        url_mapping[orig_path] = wechat_url
    
    # 替换内容中的图片路径
    result = content
    for orig_path, wechat_url in url_mapping.items():
        # 使用正则精确替换，避免误替换
        pattern = re.compile(
            r'(!\[[^\]]*\]\()' + re.escape(orig_path) + r'(\))',
            re.MULTILINE
        )
        result = pattern.sub(r'\1' + wechat_url + r'\2', result)
    
    print(f"✓ 所有图片已上传并替换为微信URL\n")
    return result


# ============================================================================
# 草稿创建
# ============================================================================

def parse_markdown_file(file_path: str) -> dict:
    """
    解析 Markdown 文件，提取标题、摘要和内容。
    
    Args:
        file_path: Markdown 文件路径
        
    Returns:
        {title, content, summary, cover_image, source_path}
    """
    path = Path(file_path)
    
    if not path.exists():
        print(f"Error: 文件不存在 - {file_path}", file=sys.stderr)
        sys.exit(1)
    
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    lines = content.strip().split("\n")
    
    # 提取标题 (第一个 H1)
    title = "Untitled"
    content_start = 0
    
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            content_start = idx + 1
            break
    
    # 内容（不含标题）
    content_lines = lines[content_start:]
    markdown_content = "\n".join(content_lines).strip()
    
    # 提取第一张图片作为封面
    cover_image = None
    img_match = re.search(r'!\[[^\]]*\]\(([^)]+)\)', markdown_content)
    if img_match:
        cover_image = img_match.group(1)
    
    # 提取摘要（第一段非标题文本）
    summary = None
    for line in content_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith(("#", "!", ">", "-", "*", "`", "|")):
            summary = stripped[:120]
            break
    
    return {
        "title": title[:64],  # 微信限制64字符
        "content": markdown_content,
        "summary": summary,
        "cover_image": cover_image,
        "source_path": path
    }


def markdown_to_html(content: str) -> str:
    """
    将 Markdown 转换为简单的 HTML。
    
    注意：这是一个简化的转换器，对于复杂 Markdown 可能需要使用专业库。
    
    Args:
        content: Markdown 内容
        
    Returns:
        HTML 内容
    """
    html = content
    
    # 代码块 (```...```)
    html = re.sub(
        r'```(\w*)\n(.*?)```',
        r'<pre><code>\2</code></pre>',
        html,
        flags=re.DOTALL
    )
    
    # 行内代码 (`...`)
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
    
    # 粗体 (**...**)
    html = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', html)
    
    # 斜体 (*...*)
    html = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', html)
    
    # 标题
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    
    # 图片
    html = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1">', html)
    
    # 链接
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)
    
    # 引用块
    html = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)
    
    # 分隔线
    html = re.sub(r'^---+$', r'<hr>', html, flags=re.MULTILINE)
    
    # 段落（将连续的非空行包裹在 <p> 中）
    paragraphs = []
    current_para = []
    
    for line in html.split('\n'):
        stripped = line.strip()
        
        # 如果是块级标签，直接添加
        if re.match(r'^<(h[1-6]|pre|blockquote|hr|ul|ol|li|div|img)', stripped):
            if current_para:
                paragraphs.append('<p>' + ' '.join(current_para) + '</p>')
                current_para = []
            paragraphs.append(stripped)
        elif stripped:
            current_para.append(stripped)
        else:
            if current_para:
                paragraphs.append('<p>' + ' '.join(current_para) + '</p>')
                current_para = []
    
    if current_para:
        paragraphs.append('<p>' + ' '.join(current_para) + '</p>')
    
    return '\n'.join(paragraphs)


# ============================================================================
# bm.md 精美渲染
# ============================================================================

BMMD_API_URL = "https://bm.md/api/markdown/render"
BMMD_STYLE = "green-simple"

# 相对于脚本位置的 custom.css 路径
CUSTOM_CSS_PATH = Path(__file__).parent.parent / "styles" / "custom.css"


def load_custom_css() -> str:
    """
    加载自定义 CSS 样式文件。
    
    Returns:
        CSS 字符串，如果文件不存在则返回空字符串
    """
    if CUSTOM_CSS_PATH.exists():
        with open(CUSTOM_CSS_PATH, "r", encoding="utf-8") as f:
            return f.read()
    else:
        print(f"Warning: 未找到 custom.css，将使用默认样式", file=sys.stderr)
        return ""


def render_with_bmmd(markdown_content: str, use_fallback: bool = True) -> str:
    """
    使用 bm.md API 将 Markdown 渲染为精美的 HTML。
    
    Args:
        markdown_content: Markdown 内容
        use_fallback: 如果 API 调用失败，是否使用本地简单转换
        
    Returns:
        渲染后的 HTML 内容
    """
    custom_css = load_custom_css()
    
    payload = {
        "markdown": markdown_content,
        "markdownStyle": BMMD_STYLE,
        "platform": "wechat",
        "enableFootnoteLinks": True,
        "openLinksInNewWindow": True,
        "customCss": custom_css
    }
    
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    
    request = urllib.request.Request(
        BMMD_API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        },
        method="POST"
    )
    
    try:
        print("调用 bm.md API 渲染精美格式...")
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
            
        # 从API响应中提取渲染后的HTML内容
        result = data.get("html") or data.get("content") or data.get("result")
        
        if result:
            print("✓ bm.md 渲染成功")
            # 后处理：将列表转换为段落以解决微信移动端bug
            result = convert_lists_to_paragraphs(result)
            return result
        else:
            print("Warning: bm.md 返回空结果", file=sys.stderr)
            if use_fallback:
                print("使用本地简单转换作为后备...")
                return markdown_to_html(markdown_content)
            return markdown_content
            
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        print(f"Warning: bm.md API 错误 HTTP {e.code}: {error_body[:200]}", file=sys.stderr)
        if use_fallback:
            print("使用本地简单转换作为后备...")
            return markdown_to_html(markdown_content)
        raise
        
    except urllib.error.URLError as e:
        print(f"Warning: bm.md 网络错误: {e.reason}", file=sys.stderr)
        if use_fallback:
            print("使用本地简单转换作为后备...")
            return markdown_to_html(markdown_content)
        raise
        
    except Exception as e:
        print(f"Warning: bm.md 渲染失败: {e}", file=sys.stderr)
        if use_fallback:
            print("使用本地简单转换作为后备...")
            return markdown_to_html(markdown_content)
        raise


def convert_lists_to_paragraphs(html: str) -> str:
    """
    将HTML中的有序/无序列表转换为带手动序号的段落。
    
    微信公众号移动端对 <ol>/<ul> 列表渲染有bug，序号会显示异常。
    解决方案是将列表项转换为普通段落，手动添加序号文本。
    
    Args:
        html: 原始HTML内容
        
    Returns:
        转换后的HTML
    """
    result = html
    
    # 处理有序列表 <ol>...</ol>
    ol_pattern = re.compile(r'<ol[^>]*>(.*?)</ol>', re.DOTALL | re.IGNORECASE)
    
    def replace_ol(match):
        ol_content = match.group(1)
        # 提取所有 <li> 项
        li_pattern = re.compile(r'<li[^>]*>(.*?)</li>', re.DOTALL | re.IGNORECASE)
        items = li_pattern.findall(ol_content)
        
        paragraphs = []
        for idx, item in enumerate(items, 1):
            # 移除内部的 span 标签但保留内容
            clean_item = item.strip()
            # 添加手动序号
            para = f'<p style="margin: 5px 0 10px; line-height: 1.75em;"><span style="color: #2bae85; font-weight: bold;">{idx}. </span>{clean_item}</p>'
            paragraphs.append(para)
        
        return '\n'.join(paragraphs)
    
    result = ol_pattern.sub(replace_ol, result)
    
    # 处理无序列表 <ul>...</ul>
    ul_pattern = re.compile(r'<ul[^>]*>(.*?)</ul>', re.DOTALL | re.IGNORECASE)
    
    def replace_ul(match):
        ul_content = match.group(1)
        # 提取所有 <li> 项
        li_pattern = re.compile(r'<li[^>]*>(.*?)</li>', re.DOTALL | re.IGNORECASE)
        items = li_pattern.findall(ul_content)
        
        paragraphs = []
        for item in items:
            clean_item = item.strip()
            # 使用圆点作为项目符号
            para = f'<p style="margin: 5px 0 10px; line-height: 1.75em;"><span style="color: #2bae85; font-weight: bold;">• </span>{clean_item}</p>'
            paragraphs.append(para)
        
        return '\n'.join(paragraphs)
    
    result = ul_pattern.sub(replace_ul, result)
    
    print("✓ 列表已转换为段落格式 (微信移动端兼容)")
    return result


def create_draft(
    title: str,
    content: str,
    access_token: str,
    thumb_media_id: Optional[str] = None,
    author: str = "",
    digest: str = "",
) -> dict:
    """
    创建微信草稿。
    
    调用接口: /cgi-bin/draft/add
    
    Args:
        title: 文章标题
        content: HTML 内容
        access_token: 访问令牌
        thumb_media_id: 封面图片 media_id（可选）
        author: 作者
        digest: 摘要
        
    Returns:
        API 响应数据
    """
    url = f"{API_BASE_URL}/cgi-bin/draft/add?access_token={access_token}"
    
    article = {
        "title": title,
        "content": content,
        "content_source_url": "",
        "need_open_comment": 0,
        "only_fans_can_comment": 0,
    }
    
    if author:
        article["author"] = author
    if digest:
        article["digest"] = digest
    if thumb_media_id:
        article["thumb_media_id"] = thumb_media_id
    
    payload = {"articles": [article]}
    
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        print(f"Error: HTTP {e.code} - {error_body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: 网络错误 - {e.reason}", file=sys.stderr)
        sys.exit(1)
    
    if "errcode" in data and data["errcode"] != 0:
        print(f"Error: 创建草稿失败", file=sys.stderr)
        print(f"  错误码: {data.get('errcode')}", file=sys.stderr)
        print(f"  错误信息: {data.get('errmsg')}", file=sys.stderr)
        sys.exit(1)
    
    return data


# ============================================================================
# 主流程
# ============================================================================

def cmd_test_token(args):
    """测试 access_token 获取"""
    print("=" * 50)
    print("测试 Access Token 获取")
    print("=" * 50)
    
    token = get_access_token()
    print(f"\nAccess Token: {token[:20]}...{token[-10:]}")
    print("\n✓ Token 获取成功！")


def cmd_upload_image(args):
    """上传图片"""
    print("=" * 50)
    print("上传图片到微信素材库")
    print("=" * 50)
    
    token = get_access_token()
    wechat_url = upload_image(args.image, token)
    
    print(f"\n微信图片URL: {wechat_url}")


def cmd_publish(args):
    """发布文章到草稿箱"""
    print("=" * 50)
    print("发布文章到微信草稿箱")
    print("=" * 50)
    
    # 获取 token
    token = get_access_token()
    
    # 解析 Markdown
    print(f"\n解析文件: {args.markdown}")
    article = parse_markdown_file(args.markdown)
    
    print(f"  标题: {article['title']}")
    print(f"  摘要: {article['summary'][:50]}..." if article['summary'] else "  摘要: (无)")
    
    # 处理图片
    processed_content = process_markdown_images(
        article['content'],
        article['source_path'].parent,
        token
    )

    # 修复：移除可能被误判为 frontmatter 的分隔符 (---)
    # bm.md 可能会将首尾的 --- 之间的内容视为元数据并隐藏
    processed_content = re.sub(r'^\s*---\s*$', '', processed_content, flags=re.MULTILINE)
    
    # 上传封面图片（如果有）
    thumb_media_id = None
    cover_image = article.get('cover_image')
    if cover_image and not cover_image.startswith(('http://', 'https://')):
        # 本地封面图片，需要上传
        cover_path = article['source_path'].parent / cover_image
        if cover_path.exists():
            print(f"\n上传封面图片...")
            thumb_media_id = upload_thumb_material(str(cover_path), token)
        else:
            print(f"Warning: 封面图片不存在 - {cover_image}", file=sys.stderr)
    
    # 转换为精美 HTML (使用 bm.md API)
    html_content = render_with_bmmd(processed_content)
    
    # 创建草稿
    print("正在创建草稿...")
    result = create_draft(
        title=article['title'],
        content=html_content,
        access_token=token,
        thumb_media_id=thumb_media_id,
        digest=article['summary'] or ""
    )
    
    print("\n" + "=" * 50)
    print("✓ 发布成功！")
    print("=" * 50)
    print(f"  Media ID: {result.get('media_id', 'N/A')}")
    print("\n请登录微信公众平台查看草稿箱。")
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="微信公众号直连发布工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # test-token 命令
    parser_token = subparsers.add_parser("test-token", help="测试 access_token 获取")
    parser_token.set_defaults(func=cmd_test_token)
    
    # upload-image 命令
    parser_upload = subparsers.add_parser("upload-image", help="上传图片到微信素材库")
    parser_upload.add_argument("image", help="图片文件路径")
    parser_upload.set_defaults(func=cmd_upload_image)
    
    # publish 命令
    parser_publish = subparsers.add_parser("publish", help="发布文章到草稿箱")
    parser_publish.add_argument("--markdown", "-m", required=True, help="Markdown 文件路径")
    parser_publish.set_defaults(func=cmd_publish)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == "__main__":
    main()
