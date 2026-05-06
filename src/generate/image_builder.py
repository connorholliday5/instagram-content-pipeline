import os
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

OUTPUT_DIR = Path("output")
ASSETS_DIR = Path("assets")
SIZE = (1080, 1350)  # Instagram portrait

CATEGORY_COLORS = {
    "comics": ("#0a0a1a", "#e63946"),   # dark bg, DC red
    "film":   ("#0a0a1a", "#f4a261"),   # dark bg, gold
    "tv":     ("#0a0a1a", "#457b9d"),   # dark bg, blue
    "books":  ("#0a0a1a", "#2d6a4f"),   # dark bg, green
    "manga":  ("#0a0a1a", "#9b5de5"),   # dark bg, purple
}


def _load_cover(url: str) -> Image.Image | None:
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content)).convert("RGBA")
    except Exception:
        return None


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    font_dir = ASSETS_DIR / "fonts"
    candidates = list(font_dir.glob("*Bold*.ttf" if bold else "*.ttf"))
    if candidates:
        return ImageFont.truetype(str(candidates[0]), size)
    return ImageFont.load_default()


def build_image(
    title: str,
    category: str,
    cover_url: str | None = None,
    subtitle: str | None = None,
    label: str | None = None,
) -> Path:
    """Generate a 1080x1350 Instagram-ready image. Returns path to saved file."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    bg_color, accent = CATEGORY_COLORS.get(category, ("#0a0a1a", "#e63946"))
    canvas = Image.new("RGB", SIZE, bg_color)
    draw = ImageDraw.Draw(canvas)

    # Cover image (top 65% of canvas)
    if cover_url:
        cover = _load_cover(cover_url)
        if cover:
            cover_h = int(SIZE[1] * 0.65)
            cover = cover.resize((SIZE[0], cover_h), Image.LANCZOS)
            canvas.paste(cover, (0, 0), cover if cover.mode == "RGBA" else None)

    # Gradient overlay bottom strip
    strip_top = int(SIZE[1] * 0.55)
    for y in range(strip_top, SIZE[1]):
        alpha = int(255 * ((y - strip_top) / (SIZE[1] - strip_top)) ** 0.5)
        draw.line([(0, y), (SIZE[0], y)], fill=bg_color + f"{alpha:02x}" if isinstance(bg_color, str) else bg_color)

    # Accent bar
    draw.rectangle([(0, strip_top), (SIZE[0], strip_top + 6)], fill=accent)

    # Label pill (e.g. "NEW THIS WEEK")
    if label:
        font_sm = _get_font(28, bold=True)
        draw.rectangle([(40, strip_top + 30), (40 + len(label) * 17, strip_top + 65)], fill=accent)
        draw.text((52, strip_top + 32), label.upper(), font=font_sm, fill="#ffffff")

    # Title
    font_title = _get_font(72, bold=True)
    draw.text((40, strip_top + 90), title, font=font_title, fill="#ffffff")

    # Subtitle
    if subtitle:
        font_sub = _get_font(40)
        draw.text((40, strip_top + 180), subtitle, font=font_sub, fill="#cccccc")

    # Watermark
    font_wm = _get_font(30)
    draw.text((40, SIZE[1] - 60), "@TheWatchtower_", font=font_wm, fill=accent)

    # Save
    safe_title = "".join(c for c in title if c.isalnum() or c in " _-")[:40].strip()
    out_path = OUTPUT_DIR / f"{category}_{safe_title.replace(' ', '_')}.jpg"
    canvas.convert("RGB").save(out_path, "JPEG", quality=95)
    return out_path
