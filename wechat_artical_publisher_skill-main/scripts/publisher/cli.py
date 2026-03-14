from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .article_loader import load_article
from .publish_service import (
    DEFAULT_POLL_INTERVAL,
    DEFAULT_POLL_TIMEOUT,
    format_publish_status,
    prompt_publish_mode,
    publish_article,
    resolve_publish_settings,
)
from .wechat_api_client import batch_get_freepublish, get_access_token, upload_image


DEFAULT_PUBLISH_MODE = "draft"
ENTRYPOINT_PATH = Path(__file__).resolve().parents[1] / "wechat_direct_api.py"


def cmd_test_token(args: argparse.Namespace) -> None:
    print("=" * 50)
    print("测试 Access Token 获取")
    print("=" * 50)
    token = get_access_token(ENTRYPOINT_PATH)
    print(f"\nAccess Token: {token[:20]}...{token[-10:]}")
    print("\n✓ Token 获取成功！")


def cmd_upload_image(args: argparse.Namespace) -> None:
    print("=" * 50)
    print("上传图片到微信素材库")
    print("=" * 50)
    token = get_access_token(ENTRYPOINT_PATH)
    print(f"\n微信图片URL: {upload_image(args.image, token)}")


def cmd_publish(args: argparse.Namespace) -> dict[str, Any]:
    print("=" * 50)
    print("发布文章到微信公众号")
    print("=" * 50)
    mode = args.mode
    if mode == "ask":
        mode = prompt_publish_mode(DEFAULT_PUBLISH_MODE)
    token = get_access_token(ENTRYPOINT_PATH)
    article = load_article(markdown=args.markdown, package_dir=args.package_dir)
    settings = resolve_publish_settings(
        article,
        ENTRYPOINT_PATH,
        cli_author=args.author or "",
        cli_need_open_comment=args.need_open_comment,
        cli_only_fans_can_comment=args.only_fans_can_comment,
    )

    print(f"\n标题: {article.title}")
    print(f"摘要: {article.summary[:50]}..." if article.summary else "摘要: (无)")
    print(f"作者: {settings['author'] or '(未设置)'}")
    print(f"打开评论: {'是' if settings['need_open_comment'] else '否'}")
    print(f"仅粉丝评论: {'是' if settings['only_fans_can_comment'] else '否'}")
    print(f"发布模式: {'直接发布' if mode == 'publish' else '发送到草稿'}")

    result = publish_article(
        article,
        token,
        ENTRYPOINT_PATH,
        mode=mode,
        author=settings["author"],
        need_open_comment=settings["need_open_comment"],
        only_fans_can_comment=settings["only_fans_can_comment"],
        poll_interval=args.poll_interval,
        poll_timeout=args.poll_timeout,
    )
    print("\n" + "=" * 50)
    if mode == "draft":
        print("✓ 草稿创建成功！")
        print("=" * 50)
        print(f"  Media ID: {result.get('media_id', 'N/A')}")
        print("\n请登录微信公众平台查看草稿箱。")
    else:
        print("发布状态汇总")
        print("=" * 50)
        print(format_publish_status(result.get("status", result)))
    return result


def cmd_history(args: argparse.Namespace) -> dict[str, Any]:
    print("=" * 50)
    print("查询公众号已发布文章")
    print("=" * 50)
    token = get_access_token(ENTRYPOINT_PATH)
    result = batch_get_freepublish(token, offset=args.offset, count=args.count)
    items = result.get("item", [])
    total_count = result.get("total_count", len(items))
    print(f"总数: {total_count}")
    print(f"当前返回: {len(items)}")
    if not items:
        print("暂无已发布记录。")
        return result
    for idx, item in enumerate(items, 1):
        article = item.get("article", {}) if isinstance(item, dict) else {}
        print(f"\n[{idx}] {article.get('title') or item.get('title') or 'Untitled'}")
        print(f"  article_id: {item.get('article_id', 'N/A')}")
        print(f"  update_time: {item.get('update_time', 'N/A')}")
        if article.get("link"):
            print(f"  link: {article['link']}")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="微信公众号直连发布工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    parser_token = subparsers.add_parser("test-token", help="测试 access_token 获取")
    parser_token.set_defaults(func=cmd_test_token)

    parser_upload = subparsers.add_parser("upload-image", help="上传图片到微信素材库")
    parser_upload.add_argument("image", help="图片文件路径")
    parser_upload.set_defaults(func=cmd_upload_image)

    parser_publish = subparsers.add_parser("publish", help="发布文章到草稿箱或直接发布")
    parser_publish.add_argument("--markdown", "-m", help="Markdown 文件路径")
    parser_publish.add_argument("--package-dir", help="标准内容包目录")
    parser_publish.add_argument("--mode", choices=["ask", "draft", "publish"], default="ask")
    parser_publish.add_argument("--author", default="", help="覆盖文章作者")
    parser_publish.add_argument("--need-open-comment", choices=["0", "1"], help="是否打开评论")
    parser_publish.add_argument("--only-fans-can-comment", choices=["0", "1"], help="是否仅粉丝可评论")
    parser_publish.add_argument("--poll-interval", type=int, default=DEFAULT_POLL_INTERVAL)
    parser_publish.add_argument("--poll-timeout", type=int, default=DEFAULT_POLL_TIMEOUT)
    parser_publish.set_defaults(func=cmd_publish)

    parser_history = subparsers.add_parser("history", help="查询已发布文章列表")
    parser_history.add_argument("--offset", type=int, default=0, help="分页起始偏移")
    parser_history.add_argument("--count", type=int, default=20, help="返回条数")
    parser_history.set_defaults(func=cmd_history)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1
    if args.command == "publish" and bool(args.markdown) == bool(args.package_dir):
        parser.error("publish 命令必须且只能提供 --markdown 或 --package-dir 其中之一")
    args.func(args)
    return 0
