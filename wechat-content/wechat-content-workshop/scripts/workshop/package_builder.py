from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import textwrap
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .common import ensure_dir, relative_to, sanitize_segment, save_text, to_simple_yaml
from .models import ContentPackage, ImageAsset


DEFAULT_CHANNEL = "公众号"
DEFAULT_CONTENT_TYPE = "文章"
DEFAULT_SERIES = "未分栏"
DEFAULT_TONE = "有温度的观察型"
DEFAULT_CONTENT_ROOT = Path.cwd() / "wechat-content-archive"
DEFAULT_IMAGE_TEST_OUTPUT_DIR = Path.cwd() / "wechat-content-workshop-image-test"

OPENING_SCENES = [
    "昨晚九点多，{region}的风还有点硬，我在路边摊前站了五分钟，才意识到这件事其实早就变了。",
    "前几天傍晚下过一阵小雨，{region}的路面有点发亮，这个话题突然又被我重新想了一遍。",
    "今天早上七点半，楼下刚开门的店还带着一股热气，我边走边想，{topic}这件事真不是一句话能讲完。",
    "周末快到中午的时候，人群慢慢挤进来，声音、气味和脚步都很具体，这时候再聊{topic}，反而比在会议室里更真。",
]

VIEWPOINTS = [
    "我越来越确定，真正打动人的从来不是结论本身，而是结论背后的生活纹理。",
    "很多内容写不好，不是因为观点不够新，而是写的人没有把自己放进现场。",
    "如果只把它当成一个趋势词来看，这个话题会很空；把它放回人的日常里，意思才会慢慢长出来。",
    "我对这件事的态度不算中立，我偏向那些有烟火气、也经得起复看的表达。 ",
]

DETAIL_BANK = {
    "food": ["刚出锅的热气", "塑料袋口打了个结", "收银台边一摞零钱", "摊位上写得有点歪的价签"],
    "city": ["早高峰地铁里压低的铃声", "电动车从身边擦过去的风", "便利店门口亮着的灯箱", "路口红绿灯前停下的人群"],
    "home": ["厨房里没散完的葱油味", "阳台上还没收的衣服", "桌角压着的快递盒", "瓷杯壁上一圈浅浅的茶渍"],
    "work": ["会议结束后还亮着的投影幕布", "被反复修改过的文档标题", "午休时没吃完的外卖", "键盘旁边那瓶快见底的无糖茶"],
}

IMAGE_SIZES = {
    "cover": (900, 383),
    "inline": (800, 600),
}


def load_reference_rules() -> str:
    rules_path = Path(__file__).resolve().parents[2] / "references" / "writing-rules.md"
    return rules_path.read_text(encoding="utf-8")


def hashed_choice(seed_text: str, items: list[str]) -> str:
    if not items:
        return ""
    digest = hashlib.md5(seed_text.encode("utf-8")).hexdigest()
    return items[int(digest[:8], 16) % len(items)]


def infer_detail_bucket(topic: str) -> str:
    lowered = topic.lower()
    if any(word in lowered for word in ["菜", "吃", "早餐", "餐", "咖啡", "面", "茶", "饭"]):
        return "food"
    if any(word in lowered for word in ["城市", "通勤", "地铁", "商场", "街头", "租房"]):
        return "city"
    if any(word in lowered for word in ["家庭", "家", "收纳", "厨房", "孩子"]):
        return "home"
    return "work"


def build_style_notes(args: argparse.Namespace) -> dict:
    return {
        "persona": "像一个长期观察微信内容生态、愿意把生活过细的人",
        "tone": args.tone or DEFAULT_TONE,
        "audience": args.audience or "关心真实表达、愿意认真读完一篇公众号文章的人",
        "region_hint": args.region or "身边城市",
        "channel_priority": [DEFAULT_CHANNEL, "朋友圈", "社群"],
        "writing_rules_excerpt": [
            "开头必须进入具体场景，不做空泛总起",
            "正文至少写出一种真实细节",
            "观点明确，但避免说教和模板连接句",
            "适合微信端阅读，控制段落长度和留白",
        ],
        "reference_rules_path": str(
            Path(__file__).resolve().parents[2] / "references" / "writing-rules.md"
        ),
    }


def generate_outline(topic: str) -> list[str]:
    return [
        f"从一个具体场景切入，说明为什么今天还想聊“{topic}”",
        "把读者常见误区拆开，别让表达停留在概念层",
        "给出作者真正认同的判断与做法",
        "落到微信生态场景，说明这类内容为什么适合公众号",
    ]


def generate_title_candidates(topic: str, region: str, audience: str) -> list[str]:
    return [
        f"{topic}，为什么最近越写越想回到生活里",
        f"在{region}重新看{topic}，我发现公众号最缺的不是技巧",
        f"写给{audience}：{topic}这件事，别再只讲大道理",
    ]


def generate_summary(topic: str, region: str) -> str:
    return (
        f"从{region}的日常场景出发，重新聊聊“{topic}”。这不是一篇拼观点密度的文章，"
        f"而是想把真实生活、微信阅读节奏和作者立场放回同一篇内容里。"
    )


def generate_cover_copy(topic: str) -> str:
    return f"{topic}\n把话写进生活里"


def generate_share_texts(title: str, summary: str) -> dict:
    short = summary[:55].rstrip("，。； ")
    return {
        "公众号": f"{title}\n\n{short}。",
        "朋友圈": f"{title}。这次不聊空话，只聊我真正在生活里碰到的细节。",
        "社群": f"今天整理了一篇新稿《{title}》，适合想把内容写得更真、更有人味的朋友。",
    }


def generate_closing_cta(topic: str) -> str:
    return f"如果你最近也在想“{topic}”这件事，欢迎把你看到的细节留在评论区，我们继续往下聊。"


def build_image_prompts(topic: str, region: str, series: str, inline_count: int) -> list[ImageAsset]:
    cover = ImageAsset(
        role="cover",
        topic=topic,
        prompt=f"微信公众号封面插画，主题是{topic}，地域气质参考{region}，栏目名{series}，清爽留白，中文排版友好，适合横版封面",
        width=IMAGE_SIZES["cover"][0],
        height=IMAGE_SIZES["cover"][1],
    )
    assets = [cover]
    for index in range(1, inline_count + 1):
        assets.append(
            ImageAsset(
                role=f"inline-{index}",
                topic=topic,
                prompt=f"公众号正文插图，第{index}张，主题是{topic}，带有{region}生活感，纪实插画风，适合中文内容配图",
                width=IMAGE_SIZES["inline"][0],
                height=IMAGE_SIZES["inline"][1],
            )
        )
    return assets


def generate_body(topic: str, args: argparse.Namespace) -> str:
    region = args.region or "这座城市"
    audience = args.audience or "总觉得内容越写越像模板的人"
    detail_bucket = infer_detail_bucket(topic)
    seed = f"{topic}|{region}|{audience}|{args.series}|{args.tone}"
    opening = hashed_choice(seed, OPENING_SCENES).format(region=region, topic=topic)
    viewpoint = hashed_choice(seed + "|view", VIEWPOINTS).strip()
    details = random.Random(seed).sample(DETAIL_BANK[detail_bucket], 3)

    body = f"""\
{opening}

很多人聊{topic}，一上来就想找一个漂亮结论，最好还能顺手变成爆款标题。可我这两年越来越不信这种写法。公众号不是答题卡，它更像一张小桌子，读者愿意坐下来，是因为你端上来的东西有温度，也有一点你自己的脾气。

## 先别急着下判断

我想起最近一次真切地意识到这件事，是因为几个很小的细节：{details[0]}，{details[1]}，还有{details[2]}。这些东西看起来不高级，却特别能把人拉回现场。读者不是不知道大道理，读者只是想先确认，你是不是认真看过生活。

对{audience}来说，最容易踩的坑就是把内容写成“正确但没人在意”的样子。字句工整，逻辑也完整，偏偏读完就散了，因为里面没有气味，没有动作，也没有谁真的在场。

## 我更看重什么

{viewpoint}

如果非要给一个写作建议，我会说，先别想着把所有信息装满。先把一个场景写准，把一句真心话说透。比如你为什么偏爱它，你为什么对某种表达开始不耐烦，你在{region}最近看到的变化到底是什么。这样的内容也许不那么“标准”，但更容易留下来。

## 为什么它特别适合公众号

微信阅读有个很现实的特点：大多数人是在通勤、排队、午休、睡前这些缝隙里读文章。这个场景决定了内容不能空，不能绕，也不能全程一种节奏。该短的时候要短，该停顿的时候要停顿，偶尔还得像朋友说话那样，把一句话单独放出来。

所以回到{topic}，我真正想说的是，它不只是一个题目，更像一个入口。入口后面是{region}的生活，是作者自己的判断，也是读者愿不愿意继续相信这篇文章的理由。
"""
    return textwrap.dedent(body).strip() + "\n"


def build_package(args: argparse.Namespace) -> ContentPackage:
    region = args.region or "本地城市"
    audience = args.audience or "认真看微信内容的人"
    series = args.series or DEFAULT_SERIES
    title_candidates = generate_title_candidates(args.topic, region, audience)
    title = title_candidates[0][:64]
    summary = generate_summary(args.topic, region)
    body = generate_body(args.topic, args)
    style_notes = build_style_notes(args)
    image_assets = build_image_prompts(args.topic, region, series, args.inline_image_count)
    image_plan = [asdict(asset) for asset in image_assets]

    return ContentPackage(
        topic=args.topic,
        date=args.date or datetime.now().strftime("%Y-%m-%d"),
        channel=args.channel or DEFAULT_CHANNEL,
        series=series,
        content_type=DEFAULT_CONTENT_TYPE,
        title=title,
        summary=summary,
        body_markdown=body,
        author="",
        need_open_comment=1,
        only_fans_can_comment=0,
        cover_copy=generate_cover_copy(args.topic),
        image_plan=image_plan,
        share_text=generate_share_texts(title, summary),
        closing_cta=generate_closing_cta(args.topic),
        style_notes={
            **style_notes,
            "title_candidates": title_candidates,
            "outline": generate_outline(args.topic),
            "reference_rules_preview": load_reference_rules().splitlines()[:10],
        },
        assets=[],
    )


def build_wechat_markdown(package: ContentPackage, package_dir: Path) -> str:
    cover_asset = next((asset for asset in package.assets if asset["role"] == "cover"), None)
    inline_assets = [asset for asset in package.assets if asset["role"].startswith("inline-")]

    parts = [f"# {package.title}"]
    if cover_asset and cover_asset.get("local_path"):
        cover_path = relative_to(package_dir / "final", Path(cover_asset["local_path"]))
        parts.append(f"![封面图]({cover_path})")
    parts.append(f"> 摘要：{package.summary}")
    parts.append("")

    body_sections = package.body_markdown.strip().split("\n\n")
    inline_iter = iter(inline_assets)
    for block in body_sections:
        parts.append(block)
        asset = next(inline_iter, None)
        if asset and asset.get("local_path"):
            inline_path = relative_to(package_dir / "final", Path(asset["local_path"]))
            parts.append(f"![配图]({inline_path})")
    parts.append("")
    parts.append(package.closing_cta)
    return "\n\n".join(parts).strip() + "\n"


def archive_package(package: ContentPackage, args: argparse.Namespace, materialize_images) -> Path:
    root = Path(args.content_root or DEFAULT_CONTENT_ROOT)
    package_dir = (
        root
        / sanitize_segment(package.topic, "topic")
        / sanitize_segment(package.date, "date")
        / sanitize_segment(package.series, "series")
        / sanitize_segment(package.channel, "channel")
    )
    article_dir = package_dir / "article"
    cover_dir = package_dir / "cover"
    images_dir = package_dir / "images"
    draft_dir = package_dir / "draft"
    final_dir = package_dir / "final"
    meta_dir = package_dir / "meta"

    for directory in [article_dir, cover_dir, images_dir, draft_dir, final_dir, meta_dir]:
        ensure_dir(directory)

    package.assets = materialize_images(package, images_dir, args.skip_images)

    cover_asset = next((asset for asset in package.assets if asset["role"] == "cover"), None)
    if cover_asset and cover_asset.get("local_path"):
        save_text(cover_dir / "cover_asset.txt", cover_asset["local_path"])

    save_text(article_dir / "title.txt", package.title + "\n")
    save_text(article_dir / "title_candidates.md", "\n".join(f"- {item}" for item in package.style_notes["title_candidates"]) + "\n")
    save_text(article_dir / "summary.txt", package.summary + "\n")
    save_text(article_dir / "body.md", package.body_markdown)

    save_text(cover_dir / "cover_copy.txt", package.cover_copy + "\n")
    save_text(
        cover_dir / "cover_prompt.txt",
        next(item["prompt"] for item in package.assets if item["role"] == "cover") + "\n",
    )

    image_plan_md = []
    for asset in package.assets:
        image_plan_md.append(f"## {asset['role']}")
        image_plan_md.append(f"- prompt: {asset['prompt']}")
        image_plan_md.append(f"- status: {asset['status']}")
        image_plan_md.append(f"- source: {asset.get('source', '') or 'N/A'}")
        image_plan_md.append(f"- local_path: {asset.get('local_path', '') or 'N/A'}")
        image_plan_md.append(f"- generation_strategy: {asset.get('generation_strategy', '') or 'N/A'}")
        image_plan_md.append(f"- decision_reason: {asset.get('decision_reason', '') or 'N/A'}")
        image_plan_md.append(f"- failure_reason: {asset.get('failure_reason', '') or 'N/A'}")
        image_plan_md.append("")
    save_text(images_dir / "image_plan.md", "\n".join(image_plan_md).strip() + "\n")

    save_text(draft_dir / "outline.md", "\n".join(f"- {item}" for item in package.style_notes["outline"]) + "\n")
    save_text(draft_dir / "style_notes.md", to_simple_yaml(package.style_notes) + "\n")

    wechat_markdown = build_wechat_markdown(package, package_dir)
    save_text(final_dir / "wechat_article.md", wechat_markdown)
    save_text(final_dir / "closing_cta.txt", package.closing_cta + "\n")
    save_text(final_dir / "share_text.json", json.dumps(package.share_text, ensure_ascii=False, indent=2) + "\n")
    save_text(
        final_dir / "publish_notes.md",
        (
            "主渠道：公众号\n\n"
            "建议先检查封面与摘要，再调用发布器：\n"
            f"`python3 wechat_artical_publisher_skill-main/scripts/wechat_direct_api.py publish --mode draft --package-dir \"{package_dir}\"`\n"
        ),
    )

    package_dict = asdict(package)
    save_text(meta_dir / "package.json", json.dumps(package_dict, ensure_ascii=False, indent=2) + "\n")
    save_text(meta_dir / "package.yaml", to_simple_yaml(package_dict) + "\n")
    return package_dir


def build_image_test_assets(topic: str, region: str, series: str, image_count: int) -> list[ImageAsset]:
    inline_count = max(0, image_count - 1)
    assets = build_image_prompts(topic, region, series, inline_count)
    return assets[: max(1, image_count)]


def run_image_test(topic: str, region: str, series: str, output_dir: Path, image_count: int, materialize_images) -> tuple[Path, list[dict]]:
    ensure_dir(output_dir)
    package = ContentPackage(
        topic=topic,
        date=datetime.now().strftime("%Y-%m-%d"),
        channel=DEFAULT_CHANNEL,
        series=series,
        content_type=DEFAULT_CONTENT_TYPE,
        title=topic,
        summary="",
        body_markdown="",
        author="",
        need_open_comment=1,
        only_fans_can_comment=0,
        cover_copy=generate_cover_copy(topic),
        image_plan=[asdict(asset) for asset in build_image_test_assets(topic, region, series, image_count)],
        share_text={},
        closing_cta="",
        style_notes={},
        assets=[],
    )
    package.assets = materialize_images(package, output_dir, False)

    lines = []
    for asset in package.assets:
        lines.append(f"## {asset['role']}")
        lines.append(f"- source: {asset.get('source', '') or 'N/A'}")
        lines.append(f"- local_path: {asset.get('local_path', '') or 'N/A'}")
        lines.append(f"- generation_strategy: {asset.get('generation_strategy', '') or 'N/A'}")
        lines.append(f"- decision_reason: {asset.get('decision_reason', '') or 'N/A'}")
        lines.append(f"- failure_reason: {asset.get('failure_reason', '') or 'N/A'}")
        lines.append("")
    save_text(output_dir / "image_test_report.md", "\n".join(lines).strip() + "\n")
    save_text(output_dir / "image_test_report.json", json.dumps(package.assets, ensure_ascii=False, indent=2) + "\n")
    return output_dir, package.assets
