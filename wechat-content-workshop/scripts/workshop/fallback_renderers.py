from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import tempfile
import zlib
from pathlib import Path
from typing import Optional

from .models import ImageAsset

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = None
    ImageDraw = None
    ImageFont = None


FONT_CANDIDATES = {
    "Darwin": [
        ("Hiragino Sans GB W6", "/System/Library/Fonts/Hiragino Sans GB.ttc"),
        ("PingFang SC", "/System/Library/PrivateFrameworks/FontServices.framework/Resources/Reserved/PingFangUI.ttc"),
        ("Songti SC", "/System/Library/Fonts/Supplemental/Songti.ttc"),
        ("Heiti SC", "/System/Library/Fonts/STHeiti Medium.ttc"),
        ("Arial Unicode MS", "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    ],
    "Windows": [
        ("Microsoft YaHei", r"C:\Windows\Fonts\msyh.ttc"),
        ("SimHei", r"C:\Windows\Fonts\simhei.ttf"),
        ("SimSun", r"C:\Windows\Fonts\simsun.ttc"),
        ("Arial Unicode MS", r"C:\Windows\Fonts\ARIALUNI.TTF"),
    ],
    "Linux": [
        ("Noto Sans CJK SC", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        ("Source Han Sans SC", "/usr/share/fonts/opentype/source-han-sans/SourceHanSansSC-Regular.otf"),
        ("WenQuanYi Micro Hei", "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
        ("WenQuanYi Zen Hei", "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
    ],
}

ASCII_FONT_5X7 = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01111", "10000", "10000", "10111", "10001", "10001", "01110"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00110", "01000", "10000", "11111"],
    ":": ["00000", "00100", "00100", "00000", "00100", "00100", "00000"],
    "-": ["00000", "00000", "00000", "01110", "00000", "00000", "00000"],
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
}


def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    length = len(data).to_bytes(4, "big")
    crc = zlib.crc32(chunk_type + data).to_bytes(4, "big")
    return length + chunk_type + data + crc


def write_simple_png(target: Path, width: int, height: int, prompt: str, role: str) -> None:
    width = max(32, width)
    height = max(32, height)
    digest = hashlib.md5(f"{prompt}|{role}".encode("utf-8")).digest()
    base = (digest[0], digest[1], digest[2])
    accent = (digest[5], digest[6], digest[7])

    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            mix = (x * 255) // max(1, width - 1)
            band = 0 if (x // max(1, width // 6)) % 2 == 0 else 1
            color_a = base if band == 0 else accent
            color_b = accent if band == 0 else base
            r = (color_a[0] * (255 - mix) + color_b[0] * mix) // 255
            g = (color_a[1] * (255 - mix) + color_b[1] * mix) // 255
            b = (color_a[2] * (255 - mix) + color_b[2] * mix) // 255
            if y > height * 0.72:
                r = min(255, r + 18)
                g = min(255, g + 18)
                b = min(255, b + 18)
            row.extend((r, g, b))
        rows.append(bytes(row))

    raw = b"".join(rows)
    compressed = zlib.compress(raw, level=9)
    ihdr = (
        width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"\x08\x02\x00\x00\x00"
    )
    png = b"\x89PNG\r\n\x1a\n"
    png += png_chunk(b"IHDR", ihdr)
    png += png_chunk(b"IDAT", compressed)
    png += png_chunk(b"IEND", b"")
    target.write_bytes(png)


def set_pixel(pixels: bytearray, width: int, height: int, x: int, y: int, color: tuple[int, int, int]) -> None:
    if 0 <= x < width and 0 <= y < height:
        idx = (y * width + x) * 3
        pixels[idx : idx + 3] = bytes(color)


def fill_rect(
    pixels: bytearray,
    width: int,
    height: int,
    x: int,
    y: int,
    rect_width: int,
    rect_height: int,
    color: tuple[int, int, int],
) -> None:
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(width, x + rect_width)
    y1 = min(height, y + rect_height)
    for yy in range(y0, y1):
        row_start = (yy * width + x0) * 3
        row_end = (yy * width + x1) * 3
        pixels[row_start:row_end] = bytes(color) * (x1 - x0)


def draw_ascii_text(
    pixels: bytearray,
    width: int,
    height: int,
    x: int,
    y: int,
    text: str,
    scale: int,
    color: tuple[int, int, int],
) -> None:
    cursor_x = x
    for char in text.upper():
        glyph = ASCII_FONT_5X7.get(char, ASCII_FONT_5X7[" "])
        for row_index, row in enumerate(glyph):
            for col_index, bit in enumerate(row):
                if bit == "1":
                    fill_rect(
                        pixels,
                        width,
                        height,
                        cursor_x + col_index * scale,
                        y + row_index * scale,
                        scale,
                        scale,
                        color,
                    )
        cursor_x += 6 * scale


def draw_character_tile(
    pixels: bytearray,
    width: int,
    height: int,
    x: int,
    y: int,
    tile_size: int,
    accent: tuple[int, int, int],
) -> None:
    fill_rect(pixels, width, height, x, y, tile_size, tile_size, (255, 255, 255))
    border = 2 if tile_size >= 16 else 1
    fill_rect(pixels, width, height, x, y, tile_size, border, accent)
    fill_rect(pixels, width, height, x, y + tile_size - border, tile_size, border, accent)
    fill_rect(pixels, width, height, x, y, border, tile_size, accent)
    fill_rect(pixels, width, height, x + tile_size - border, y, border, tile_size, accent)
    inner = (x + tile_size // 2, y + tile_size // 2)
    fill_rect(pixels, width, height, x + tile_size // 4, inner[1] - border, tile_size // 2, border, accent)
    fill_rect(pixels, width, height, inner[0] - border, y + tile_size // 4, border, tile_size // 2, accent)


def draw_topic_tiles(
    pixels: bytearray,
    width: int,
    height: int,
    topic: str,
    role: str,
) -> None:
    accent = (34, 92, 78) if role == "cover" else (43, 96, 128)
    topic_chars = [char for char in topic if char.strip()]
    if not topic_chars:
        topic_chars = list("TOPIC")
    tile_size = 24 if role == "cover" else 18
    gap = 10 if role == "cover" else 8
    max_cols = max(8, min(len(topic_chars), 18 if role == "cover" else 16))
    rows = [topic_chars[index : index + max_cols] for index in range(0, len(topic_chars), max_cols)][:2]
    start_y = 110 if role == "cover" else 120
    for row_index, row in enumerate(rows):
        row_width = len(row) * tile_size + max(0, len(row) - 1) * gap
        start_x = max(48, (width - row_width) // 2)
        y = start_y + row_index * (tile_size + 18)
        for col_index, char in enumerate(row):
            x = start_x + col_index * (tile_size + gap)
            if ord(char) < 128 and char.upper() in ASCII_FONT_5X7:
                fill_rect(pixels, width, height, x, y, tile_size, tile_size, (255, 255, 255))
                draw_ascii_text(
                    pixels,
                    width,
                    height,
                    x + 4,
                    y + 4,
                    char.upper(),
                    max(2, tile_size // 8),
                    accent,
                )
            else:
                draw_character_tile(pixels, width, height, x, y, tile_size, accent)


def find_available_font() -> tuple[Optional[str], Optional[str]]:
    system_name = platform.system()
    for font_name, font_path in FONT_CANDIDATES.get(system_name, []):
        if Path(font_path).exists():
            return font_name, font_path

    if system_name == "Linux":
        for family in ["Noto Sans CJK SC", "Source Han Sans SC", "WenQuanYi Micro Hei", "WenQuanYi Zen Hei"]:
            try:
                completed = subprocess.run(
                    ["fc-match", "-f", "%{family}|%{file}\n", family],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if completed.returncode == 0 and completed.stdout.strip():
                    family_name, file_path = completed.stdout.strip().split("|", 1)
                    if Path(file_path).exists():
                        return family_name, file_path
            except FileNotFoundError:
                break

    return None, None


def render_text_card_with_swift(asset: ImageAsset, target: Path, font_name: str, font_path: str) -> str:
    accent = (34 / 255.0, 92 / 255.0, 78 / 255.0) if asset.role == "cover" else (43 / 255.0, 96 / 255.0, 128 / 255.0)
    soft = (232 / 255.0, 239 / 255.0, 235 / 255.0) if asset.role == "cover" else (232 / 255.0, 238 / 255.0, 244 / 255.0)
    role_label = "公众号封面预览" if asset.role == "cover" else f"正文配图 {asset.role}"
    subtitle = "图片生成失败，已切换为文字保底图"
    topic = asset.topic[:28]
    title_size = 42 if asset.role == "cover" else 34
    subtitle_size = 20 if asset.role == "cover" else 18
    label_size = 18

    swift_code = f"""
import AppKit
import CoreText
import Foundation

let fontURL = URL(fileURLWithPath: {json.dumps(font_path)})
CTFontManagerRegisterFontsForURL(fontURL as CFURL, .process, nil)

func bestFont(size: CGFloat, weight: NSFont.Weight) -> NSFont {{
    let candidates = [{json.dumps(font_name)}, "PingFang SC", "Hiragino Sans GB", "Songti SC", "Heiti SC", "Arial Unicode MS", "Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Source Han Sans SC"]
    for name in candidates {{
        if let font = NSFont(name: name, size: size) {{
            return font
        }}
    }}
    return NSFont.systemFont(ofSize: size, weight: weight)
}}

let width = {asset.width}
let height = {asset.height}
let outputURL = URL(fileURLWithPath: {json.dumps(str(target))})
let image = NSImage(size: NSSize(width: width, height: height))
image.lockFocus()

NSColor.white.setFill()
NSBezierPath(rect: NSRect(x: 0, y: 0, width: width, height: height)).fill()
NSColor(calibratedRed: {accent[0]}, green: {accent[1]}, blue: {accent[2]}, alpha: 1).setFill()
NSBezierPath(rect: NSRect(x: 0, y: height - 14, width: width, height: 14)).fill()
NSColor(calibratedRed: {soft[0]}, green: {soft[1]}, blue: {soft[2]}, alpha: 1).setFill()
NSBezierPath(rect: NSRect(x: 48, y: 54, width: width - 96, height: height - 108)).fill()
NSColor.white.setFill()
NSBezierPath(rect: NSRect(x: 56, y: 62, width: width - 112, height: height - 124)).fill()
NSColor(calibratedRed: {soft[0]}, green: {soft[1]}, blue: {soft[2]}, alpha: 1).setFill()
NSBezierPath(rect: NSRect(x: 56, y: 70, width: width - 112, height: 1)).fill()

let leftParagraph = NSMutableParagraphStyle()
leftParagraph.alignment = .left
leftParagraph.lineBreakMode = .byWordWrapping

let titleParagraph = NSMutableParagraphStyle()
titleParagraph.alignment = .center
titleParagraph.lineBreakMode = .byWordWrapping

let labelAttrs: [NSAttributedString.Key: Any] = [
    .font: bestFont(size: {label_size}, weight: .semibold),
    .foregroundColor: NSColor(calibratedWhite: 0.18, alpha: 1),
    .paragraphStyle: leftParagraph
]
let titleAttrs: [NSAttributedString.Key: Any] = [
    .font: bestFont(size: {title_size}, weight: .bold),
    .foregroundColor: NSColor(calibratedWhite: 0.14, alpha: 1),
    .paragraphStyle: titleParagraph
]
let subtitleAttrs: [NSAttributedString.Key: Any] = [
    .font: bestFont(size: {subtitle_size}, weight: .regular),
    .foregroundColor: NSColor(calibratedWhite: 0.45, alpha: 1),
    .paragraphStyle: titleParagraph
]
let footerAttrs: [NSAttributedString.Key: Any] = [
    .font: bestFont(size: 16, weight: .regular),
    .foregroundColor: NSColor(calibratedWhite: 0.5, alpha: 1),
    .paragraphStyle: leftParagraph
]

NSAttributedString(string: {json.dumps(role_label)}, attributes: labelAttrs).draw(in: NSRect(x: 72, y: height - 64, width: width - 144, height: 28))
NSAttributedString(string: {json.dumps(topic)}, attributes: titleAttrs).draw(in: NSRect(x: 110, y: height / 2 - 10, width: width - 220, height: 120))
NSAttributedString(string: {json.dumps(subtitle)}, attributes: subtitleAttrs).draw(in: NSRect(x: 110, y: 92, width: width - 220, height: 60))
NSAttributedString(string: "Font: {font_name}", attributes: footerAttrs).draw(in: NSRect(x: 72, y: 30, width: width - 144, height: 24))

image.unlockFocus()

guard let tiff = image.tiffRepresentation,
      let rep = NSBitmapImageRep(data: tiff),
      let png = rep.representation(using: .png, properties: [:]) else {{
    fputs("failed to render png\\n", stderr)
    exit(1)
}}
try png.write(to: outputURL)
"""
    with tempfile.TemporaryDirectory(prefix="swift-module-cache-") as cache_dir:
        env = os.environ.copy()
        env["CLANG_MODULE_CACHE_PATH"] = cache_dir
        env["SWIFT_MODULECACHE_PATH"] = cache_dir
        completed = subprocess.run(
            ["swift", "-"],
            input=swift_code,
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "swift image renderer failed")
    return f"local-text-card:{font_name}"


def wrap_text_for_font(text: str, font, max_width: int, draw) -> list[str]:
    characters = [char for char in text if char]
    if not characters:
        return [""]

    lines = []
    current = ""
    for char in characters:
        candidate = current + char
        bbox = draw.textbbox((0, 0), candidate, font=font)
        text_width = bbox[2] - bbox[0]
        if text_width <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = char
    if current:
        lines.append(current)
    return lines


def render_text_card_with_pillow(asset: ImageAsset, target: Path, font_name: str, font_path: str) -> str:
    if Image is None or ImageDraw is None or ImageFont is None:
        raise RuntimeError("Pillow not available.")

    width = asset.width
    height = asset.height
    accent = "#225c4e" if asset.role == "cover" else "#2b6080"
    soft = "#e8efeb" if asset.role == "cover" else "#e8eef4"
    title_font = ImageFont.truetype(font_path, 42 if asset.role == "cover" else 34)
    subtitle_font = ImageFont.truetype(font_path, 20 if asset.role == "cover" else 18)
    label_font = ImageFont.truetype(font_path, 18)
    footer_font = ImageFont.truetype(font_path, 15)

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width, 14), fill=accent)
    draw.rounded_rectangle((48, 54, width - 48, height - 54), radius=20, fill=soft)
    draw.rounded_rectangle((56, 62, width - 56, height - 62), radius=18, fill="white")
    draw.line((56, height - 102, width - 56, height - 102), fill=soft, width=2)

    role_label = "公众号封面预览" if asset.role == "cover" else f"正文配图 {asset.role}"
    subtitle = "图片生成失败，已切换为系统字体文字保底图"
    title_lines = wrap_text_for_font(asset.topic, title_font, width - 240, draw)[:2]
    subtitle_lines = wrap_text_for_font(subtitle, subtitle_font, width - 220, draw)[:2]

    draw.text((72, 28), role_label, fill="#22302b", font=label_font)

    title_y = 110 if asset.role == "cover" else 150
    for line in title_lines:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        line_width = bbox[2] - bbox[0]
        draw.text(((width - line_width) / 2, title_y), line, fill="#222222", font=title_font)
        title_y += (bbox[3] - bbox[1]) + 16

    subtitle_y = height - 92
    for index, line in enumerate(subtitle_lines):
        bbox = draw.textbbox((0, 0), line, font=subtitle_font)
        line_width = bbox[2] - bbox[0]
        draw.text(((width - line_width) / 2, subtitle_y + index * 28), line, fill="#6b7470", font=subtitle_font)

    footer_left = f"字体: {font_name}"
    footer_right = "AUTO FALLBACK"
    draw.text((72, height - 54), footer_left, fill="#7b8580", font=footer_font)
    right_bbox = draw.textbbox((0, 0), footer_right, font=footer_font)
    draw.text((width - 72 - (right_bbox[2] - right_bbox[0]), height - 54), footer_right, fill=accent, font=footer_font)

    image.save(target, format="PNG")
    return f"local-text-card:{font_name}"


def render_text_card_png(asset: ImageAsset, target: Path) -> str:
    font_name, font_path = find_available_font()
    if font_name and font_path and Image is not None:
        try:
            return render_text_card_with_pillow(asset, target, font_name, font_path)
        except Exception:
            pass

    if platform.system() == "Darwin" and font_name and font_path:
        try:
            return render_text_card_with_swift(asset, target, font_name, font_path)
        except Exception:
            pass

    width = asset.width
    height = asset.height
    pixels = bytearray([255, 255, 255] * width * height)
    accent = (34, 92, 78) if asset.role == "cover" else (43, 96, 128)
    soft = (232, 239, 235) if asset.role == "cover" else (232, 238, 244)
    text_dark = (34, 34, 34)
    text_muted = (110, 118, 115)

    fill_rect(pixels, width, height, 0, 0, width, height, (255, 255, 255))
    fill_rect(pixels, width, height, 0, 0, width, 14, accent)
    fill_rect(pixels, width, height, 48, 54, width - 96, height - 108, soft)
    fill_rect(pixels, width, height, 56, 62, width - 112, height - 124, (255, 255, 255))
    fill_rect(pixels, width, height, 56, height - 104, width - 112, 2, soft)

    role_label = "WECHAT COVER" if asset.role == "cover" else asset.role.upper().replace("_", "-")
    footer_label = "TEXT FALLBACK CARD"
    draw_ascii_text(pixels, width, height, 72, 34, role_label, 3, text_dark)
    draw_ascii_text(pixels, width, height, 72, height - 72, footer_label, 2, text_muted)
    draw_ascii_text(pixels, width, height, width - 230, height - 72, "AUTO DRAWN", 2, accent)
    draw_topic_tiles(pixels, width, height, asset.topic, asset.role)

    raw_rows = []
    for y in range(height):
        start = y * width * 3
        raw_rows.append(b"\x00" + bytes(pixels[start : start + width * 3]))
    compressed = zlib.compress(b"".join(raw_rows), level=9)
    ihdr = (
        width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"\x08\x02\x00\x00\x00"
    )
    png = b"\x89PNG\r\n\x1a\n"
    png += png_chunk(b"IHDR", ihdr)
    png += png_chunk(b"IDAT", compressed)
    png += png_chunk(b"IEND", b"")
    target.write_bytes(png)
    return "local-text-card"
