import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from datetime import date

OUTPUT_DIR = Path("output")
SIZE = (1080, 1350)
BG_DARK = "#0a0a1a"
RED = "#e63946"
WHITE = "#ffffff"
GRAY = "#cccccc"
GOLD = "#f4a261"


def _font(size: int, bold: bool = False):
    try:
        font_dir = Path("assets/fonts")
        candidates = list(font_dir.glob("*Bold*.ttf" if bold else "*.ttf"))
        if candidates:
            return ImageFont.truetype(str(candidates[0]), size)
    except Exception:
        pass
    return ImageFont.load_default()


def _fetch_image(url: str):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content)).convert("RGBA")
    except Exception:
        return None


def _base_canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    canvas = Image.new("RGB", SIZE, BG_DARK)
    draw = ImageDraw.Draw(canvas)
    return canvas, draw


def _save(canvas: Image.Image, name: str) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"{name}.jpg"
    canvas.convert("RGB").save(path, "JPEG", quality=95)
    return path


def _watermark(draw: ImageDraw.ImageDraw):
    font = _font(28)
    draw.text((40, SIZE[1] - 55), "@TheWatchtower_", font=font, fill=RED)


def _wrap_text(text: str, font, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def build_cover_slide(week_date: date) -> Path:
    canvas, draw = _base_canvas()

    draw.rectangle([(0, 0), (SIZE[0], 8)], fill=RED)

    font_logo = _font(52, bold=True)
    draw.text((40, 40), "THE WATCHTOWER_", font=font_logo, fill=RED)

    font_title = _font(110, bold=True)
    draw.text((40, 420), "NEW", font=font_title, fill=WHITE)
    draw.text((40, 540), "COMICS", font=font_title, fill=WHITE)
    draw.text((40, 660), "THIS", font=font_title, fill=RED)
    draw.text((40, 780), "WEEK", font=font_title, fill=RED)

    font_date = _font(48)
    date_str = week_date.strftime("%B %d, %Y")
    draw.text((40, 920), date_str, font=font_date, fill=GRAY)

    draw.rectangle([(0, SIZE[1] - 8), (SIZE[0], SIZE[1])], fill=RED)

    _watermark(draw)
    return _save(canvas, "slide_01_cover")


def build_list_slide(comics: list[dict], slide_num: int, total_count: int) -> Path:
    canvas, draw = _base_canvas()

    draw.rectangle([(0, 0), (SIZE[0], 8)], fill=RED)

    font_header = _font(44, bold=True)
    draw.text((40, 30), "THIS WEEK'S RELEASES", font=font_header, fill=RED)
    draw.text((40, 90), f"{total_count} NEW ISSUES", font=_font(32), fill=GRAY)
    draw.rectangle([(0, 148), (SIZE[0], 154)], fill=RED)

    y = 175
    font_title = _font(34, bold=True)
    font_sub = _font(26)
    line_gap = 90

    for comic in comics:
        if y > SIZE[1] - 120:
            break
        title = comic.get("name") or comic.get("volume", {}).get("name", "Unknown")
        publisher = comic.get("volume", {}).get("publisher", {}).get("name", "")
        date_str = comic.get("store_date", "")

        draw.ellipse([(40, y + 10), (52, y + 22)], fill=RED)
        draw.text((68, y), title[:42], font=font_title, fill=WHITE)
        draw.text((68, y + 42), f"{publisher}  •  {date_str}", font=font_sub, fill=GRAY)
        y += line_gap

    _watermark(draw)
    return _save(canvas, f"slide_0{slide_num}_list")


def build_pick_slide(comic_title: str, cover_url: str | None, publisher: str, slide_num: int) -> Path:
    canvas, draw = _base_canvas()

    if cover_url:
        cover = _fetch_image(cover_url)
        if cover:
            cover_h = int(SIZE[1] * 0.62)
            cover = cover.resize((SIZE[0], cover_h), Image.Resampling.LANCZOS)
            canvas.paste(cover, (0, 0), cover if cover.mode == "RGBA" else None)

    strip_top = int(SIZE[1] * 0.55)
    overlay = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    for y in range(strip_top, SIZE[1]):
        alpha = int(220 * ((y - strip_top) / (SIZE[1] - strip_top)) ** 0.6)
        overlay_draw.line([(0, y), (SIZE[0], y)], fill=(10, 10, 26, alpha))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(canvas)

    draw.rectangle([(0, strip_top), (SIZE[0], strip_top + 6)], fill=RED)

    font_label = _font(30, bold=True)
    label = "CONNOR'S PICK"
    draw.rectangle([(40, strip_top + 20), (40 + len(label) * 18, strip_top + 58)], fill=RED)
    draw.text((52, strip_top + 22), label, font=font_label, fill=WHITE)

    font_title = _font(64, bold=True)
    lines = _wrap_text(comic_title, font_title, SIZE[0] - 80, draw)
    y = strip_top + 75
    for line in lines[:2]:
        draw.text((40, y), line, font=font_title, fill=WHITE)
        y += 72

    draw.text((40, y + 10), publisher, font=_font(36), fill=GRAY)

    _watermark(draw)
    return _save(canvas, f"slide_0{slide_num}_pick_{comic_title[:20].replace(' ', '_')}")


def build_variant_slide(variants: list[dict]) -> Path:
    canvas, draw = _base_canvas()

    draw.rectangle([(0, 0), (SIZE[0], 8)], fill=GOLD)

    font_header = _font(52, bold=True)
    draw.text((40, 30), "RARE VARIANTS", font=font_header, fill=GOLD)
    draw.text((40, 96), "THIS WEEK", font=_font(38), fill=GRAY)
    draw.rectangle([(0, 154), (SIZE[0], 160)], fill=GOLD)

    covers = [v for v in variants if v.get("cover_url")][:2]
    if covers:
        cover_w = (SIZE[0] - 120) // 2
        cover_h = int(cover_w * 1.5)
        x_positions = [40, 40 + cover_w + 40]
        for i, variant in enumerate(covers):
            img = _fetch_image(variant["cover_url"])
            if img:
                img = img.resize((cover_w, cover_h), Image.Resampling.LANCZOS)
                canvas.paste(img, (x_positions[i], 180))
            draw = ImageDraw.Draw(canvas)
            draw.text(
                (x_positions[i], 180 + cover_h + 10),
                variant["title"][:28],
                font=_font(28, bold=True),
                fill=WHITE
            )
            draw.text(
                (x_positions[i], 180 + cover_h + 46),
                variant.get("publisher", ""),
                font=_font(24),
                fill=GRAY
            )

    y = 200 + int(((SIZE[0] - 120) // 2) * 1.5) + 80 if covers else 180
    font_v = _font(32, bold=True)
    font_vs = _font(26)
    for variant in variants[2:]:
        if y > SIZE[1] - 100:
            break
        draw.text((40, y), variant["title"][:44], font=font_v, fill=WHITE)
        draw.text((40, y + 38), variant.get("publisher", ""), font=font_vs, fill=GRAY)
        y += 85

    _watermark(draw)
    return _save(canvas, "slide_06_variants")


def build_reprint_slide(reprints: list[dict], slide_num: int) -> Path:
    canvas, draw = _base_canvas()

    draw.rectangle([(0, 0), (SIZE[0], 8)], fill=GOLD)

    font_header = _font(44, bold=True)
    draw.text((40, 30), "REPRINTS & COLLECTED", font=font_header, fill=GOLD)
    draw.text((40, 90), "EDITIONS THIS WEEK", font=_font(36), fill=GRAY)
    draw.rectangle([(0, 148), (SIZE[0], 154)], fill=GOLD)

    y = 175
    font_title = _font(34, bold=True)
    font_sub = _font(26)
    line_gap = 95

    for reprint in reprints:
        if y > SIZE[1] - 120:
            break
        title = reprint.get("name", "Unknown")
        publisher = reprint.get("publisher", "")
        store_date = reprint.get("store_date", "")

        draw.ellipse([(40, y + 10), (52, y + 22)], fill=GOLD)
        draw.text((68, y), title[:42], font=font_title, fill=WHITE)
        draw.text((68, y + 44), f"{publisher}  •  {store_date}", font=font_sub, fill=GRAY)
        y += line_gap

    _watermark(draw)
    return _save(canvas, f"slide_0{slide_num}_reprints")