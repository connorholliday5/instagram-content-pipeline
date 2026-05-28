import os
import subprocess
import tempfile
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from datetime import date
from typing import Optional
import random, math

OUTPUT_DIR = Path("output")
SIZE = (1080, 1350)
W, H = SIZE

BG       = (3, 3, 10)
WHITE    = (255, 255, 255)
GRAY_DIM = (75, 75, 90)
GOLD     = (255, 215, 0)
GOLD     = (255, 215, 0)
GRAY     = (170, 170, 170)
GRAY_DIM = (75, 75, 90)

# Book accent — warm gold/amber
ACCENT = (210, 160, 30)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _font(name: str, size: int):
    font_dir = Path("assets/fonts")
    candidates = {
        "bold":    ["Oswald-Bold.ttf"],
        "regular": ["Oswald-Regular.ttf"],
        "display": ["BebasNeue-Regular.ttf", "Oswald-Bold.ttf"],
        "small":   ["Oswald-Regular.ttf"],
    }
    for fname in candidates.get(name, []):
        p = font_dir / fname
        if p.exists():
            return ImageFont.truetype(str(p), size)
    all_fonts = list(font_dir.glob("*.ttf"))
    if all_fonts:
        bold = [f for f in all_fonts if "Bold" in f.name]
        return ImageFont.truetype(str(bold[0] if (bold and name in ("bold","display")) else all_fonts[0]), size)
    return ImageFont.load_default()


def _fetch_image(url: str) -> Optional[Image.Image]:
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=12)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content)).convert("RGB")
    except Exception:
        return None


def _save(canvas: Image.Image, name: str) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"{name}.jpg"
    canvas.convert("RGB").save(path, "JPEG", quality=95)
    return path


def _stars(canvas: Image.Image):
    rng = random.Random(55)
    draw = ImageDraw.Draw(canvas)
    for _ in range(280):
        x = rng.randint(0, W-1)
        y = rng.randint(0, H-1)
        r = rng.choice([1,1,1,2])
        a = rng.randint(60, 200)
        draw.ellipse([(x-r,y-r),(x+r,y+r)],
                     fill=(210+rng.randint(0,45), 190+rng.randint(0,45), 150+rng.randint(0,55), a))


def _base() -> Image.Image:
    canvas = Image.new("RGBA", SIZE, BG+(255,))
    _stars(canvas)
    ov = Image.new("RGBA", SIZE, (0,0,0,0))
    d = ImageDraw.Draw(ov)
    d.ellipse([(-300,-300),(W+300,700)], fill=(20,12,0,40))
    d.ellipse([(-200,700),(W+200,H+200)], fill=(15,8,0,50))
    canvas.alpha_composite(ov)
    return canvas


def _header(canvas: Image.Image, title: str) -> int:
    ov = Image.new("RGBA", SIZE, (0,0,0,0))
    od = ImageDraw.Draw(ov)
    od.rectangle([(0,0),(W,168)], fill=(3,3,10,245))
    canvas.alpha_composite(ov)
    draw = ImageDraw.Draw(canvas)
    bf = _font("small", 34)
    draw.text((W//2, 30), "THE WATCHTOWER",
              font=bf, fill=ACCENT+(180,), anchor="mm")
    tf = _font("display", 92)
    draw.text((W//2, 108), title, font=tf, fill=WHITE, anchor="mm")
    rule_y = 158
    draw.rectangle([(50,rule_y),(W-50,rule_y+3)], fill=ACCENT+(120,))
    return rule_y + 3


def _footer(canvas: Image.Image, date_str: str = ""):
    fy = H - 72
    ov = Image.new("RGBA", SIZE, (0,0,0,0))
    od = ImageDraw.Draw(ov)
    od.rectangle([(0,fy),(W,H)], fill=(3,3,10,230))
    canvas.alpha_composite(ov)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([(0,fy),(W,fy+3)], fill=ACCENT+(80,))
    if date_str:
        df = _font("display", 36)
        draw.text((W-32, fy+36), date_str, font=df, fill=GRAY_DIM+(180,), anchor="rm")
    hf = _font("small", 22)
    draw.text((W-32, H-14), "@the.watch_tower",
              font=hf, fill=GRAY_DIM+(80,), anchor="rm")


def _render_stars(rating: float) -> str:
    """Convert 0-5 float rating to font-safe star string."""
    full = int(rating)
    has_half = (rating - full) >= 0.5
    empty = 5 - full - (1 if has_half else 0)
    result = "[" * full
    if has_half:
        result += "|"
    result += "." * empty
    return result


def _render_stars_text(rating: float) -> str:
    """Render rating as readable text for caption use."""
    full = int(rating)
    half = 1 if (rating - full) >= 0.5 else 0
    empty = 5 - full - half
    return "★" * full + "½" * half + "☆" * empty


def _draw_station(canvas: Image.Image, top_y: int, scale: float = 0.65):
    """Smaller station for cover slide."""
    draw = ImageDraw.Draw(canvas)
    cx = W // 2
    def s(v): return int(v * scale)

    C1=(38,40,54); C2=(28,30,42); C3=(18,20,30)
    PANEL=(14,16,24); EDGE=(65,68,88)

    rings = [
        (top_y+s(120), s(140), s(36)),
        (top_y+s(228), s(158), s(42)),
        (top_y+s(320), s(132), s(34)),
        (top_y+s(398), s(110), s(28)),
    ]

    for gy, gr, grv in rings:
        for add, alpha in [(80,4),(50,10),(25,18)]:
            ov = Image.new("RGBA", SIZE, (0,0,0,0))
            od = ImageDraw.Draw(ov)
            od.ellipse([(cx-gr-add,gy-grv-add//3),(cx+gr+add,gy+grv+add//3)],
                       fill=(210,160,30,alpha))
            canvas.alpha_composite(ov)
    draw = ImageDraw.Draw(canvas)

    def box(x1,y1,x2,y2,fill):
        x1,y1,x2,y2=int(x1),int(y1),int(x2),int(y2)
        draw.rectangle([(x1,y1),(x2,y2)],fill=fill)
        draw.line([(x1,y1),(x2,y1)],fill=EDGE,width=1)

    def panels(x1,y1,x2,h,n=2,gap=3):
        x1,y1,x2,h=int(x1),int(y1),int(x2),int(h)
        pw=(x2-x1-gap*(n-1))//n
        for i in range(n):
            px=x1+i*(pw+gap)
            draw.rectangle([(px,y1),(px+pw,y1+h)],fill=PANEL)

    def ring(gy,gr,grv,width):
        draw.ellipse([(cx-gr-3,gy-grv-3),(cx+gr+3,gy+grv+3)],fill=C3)
        draw.ellipse([(cx-gr,gy-grv),(cx+gr,gy+grv)],outline=ACCENT,width=width)
        draw.ellipse([(cx-gr+7,gy-grv+3),(cx+gr-7,gy+grv-3)],
                     outline=(150,110,20,130),width=2)
        ov=Image.new("RGBA",SIZE,(0,0,0,0)); od=ImageDraw.Draw(ov)
        od.ellipse([(cx-gr,gy-grv),(cx+gr,gy+grv)],fill=(210,160,30,20))
        canvas.alpha_composite(ov)
        return ImageDraw.Draw(canvas)

    draw.line([(cx,top_y),(cx,top_y-s(40))],fill=(180,200,255,180),width=s(3))
    draw.ellipse([(cx-s(6),top_y-s(46)),(cx+s(6),top_y-s(34))],fill=ACCENT)
    draw.ellipse([(cx-s(50),top_y-s(8)),(cx+s(50),top_y+s(16))],fill=C1)
    box(cx-s(50),top_y,cx+s(50),top_y+s(20),C1)
    box(cx-s(24),top_y+s(20),cx+s(24),top_y+s(66),C2)
    for wy in [top_y+s(26),top_y+s(40),top_y+s(54)]:
        panels(cx-s(18),wy,cx+s(18),s(9))
    draw = ring(*rings[0], width=s(5))
    box(cx-s(56),top_y+s(104),cx+s(56),top_y+s(124),C1)
    draw = ring(*rings[1], width=s(6))
    box(cx-s(90),top_y+s(196),cx+s(90),top_y+s(240),C1)
    rng=random.Random(999)
    for wy in [top_y+s(204),top_y+s(216),top_y+s(228)]:
        draw.rectangle([(cx-s(78),wy),(cx+s(78),wy+s(7))],fill=C3)
        for i in range(4):
            wx=cx-s(72)+i*s(36)
            draw.rectangle([(wx,wy+1),(wx+s(28),wy+s(5))],
                           fill=(48,38,8) if rng.random()>0.4 else PANEL)
    for sign in [-1,1]:
        mx1=cx+sign*s(90); mx2=cx+sign*s(182)
        draw.rectangle([(min(mx1,mx2),top_y+s(198)),(max(mx1,mx2),top_y+s(238))],fill=C2)
    draw = ring(*rings[2], width=s(5))
    box(cx-s(32),top_y+s(278),cx+s(32),top_y+s(316),C2)
    box(cx-s(64),top_y+s(316),cx+s(64),top_y+s(348),C1)
    draw = ring(*rings[3], width=s(4))
    box(cx-s(26),top_y+s(348),cx+s(26),top_y+s(380),C2)
    draw.ellipse([(cx-s(18),top_y+s(372)),(cx+s(18),top_y+s(386))],fill=C3)


# ─────────────────────────────────────────────────────────
# SLIDE 1 — COVER
# ─────────────────────────────────────────────────────────
def build_book_cover(title: str, author: str, cover_url: str,
                     review_date: date) -> Path:
    canvas = _base()

    # Station small at top
    station_top = 30
    _draw_station(canvas, station_top, scale=0.62)
    station_bottom = station_top + int(390 * 0.62)

    # Book cover art centered below station
    cover_top = station_bottom + 20
    cover_h = int(H * 0.42)
    cover_w = int(cover_h * 0.66)
    cover_x = (W - cover_w) // 2

    img = _fetch_image(cover_url)
    if img:
        img = img.resize((cover_w, cover_h), Image.Resampling.LANCZOS)
        # Subtle shadow
        shadow = Image.new("RGBA", SIZE, (0,0,0,0))
        sd = ImageDraw.Draw(shadow)
        for offset in range(12, 0, -1):
            sd.rectangle(
                [(cover_x+offset, cover_top+offset),
                 (cover_x+cover_w+offset, cover_top+cover_h+offset)],
                fill=(0,0,0,10)
            )
        canvas.alpha_composite(shadow)
        canvas.paste(img, (cover_x, cover_top))

        # Gold border around cover
        draw = ImageDraw.Draw(canvas)
        draw.rectangle(
            [(cover_x-3, cover_top-3),
             (cover_x+cover_w+3, cover_top+cover_h+3)],
            outline=ACCENT, width=3
        )
    else:
        # Placeholder
        draw = ImageDraw.Draw(canvas)
        draw.rectangle([(cover_x, cover_top),(cover_x+cover_w, cover_top+cover_h)],
                       fill=(20,15,5))
        pf = _font("bold", 40)
        draw.text((cover_x+cover_w//2, cover_top+cover_h//2),
                  title[:20], font=pf, fill=ACCENT, anchor="mm")

    # Fade below cover into text
    text_top = cover_top + cover_h + 20
    fade = Image.new("RGBA", SIZE, (0,0,0,0))
    fd = ImageDraw.Draw(fade)
    for y in range(text_top - 40, H):
        t = min(1.0, (y-(text_top-40))/200)
        fd.line([(0,y),(W,y)], fill=(3,3,10,int(200*t**0.5)))
    canvas.alpha_composite(fade)

    draw = ImageDraw.Draw(canvas)

    # BOOK REVIEW header
    hf = _font("display", 110)
    draw.text((W//2, text_top + 60), "BOOK REVIEW",
              font=hf, fill=WHITE, anchor="mm")

    # Title + author
    tf = _font("bold", 44)
    draw.text((W//2, text_top + 130), title[:28].upper(),
              font=tf, fill=ACCENT+(220,), anchor="mm")

    af = _font("regular", 34)
    draw.text((W//2, text_top + 176), f"by {author}",
              font=af, fill=GRAY_DIM+(200,), anchor="mm")

    # Date + handle
    df = _font("display", 36)
    draw.text((W//2, H - 90), review_date.strftime("%B %d, %Y").upper(),
              font=df, fill=GRAY_DIM+(150,), anchor="mm")

    _footer(canvas)
    return _save(canvas, "book_01_cover")


# ─────────────────────────────────────────────────────────
# SLIDE 2 — REVIEW
# ─────────────────────────────────────────────────────────
def build_book_review(title: str, author: str, rating: float,
                      cover_url: str, review_text: str,
                      review_date: date) -> Path:
    canvas = _base()
    header_bottom = _header(canvas, "THE VERDICT")
    draw = ImageDraw.Draw(canvas)

    pad = 40
    gt = header_bottom + 20

    # Book cover — left column
    cover_w = int(W * 0.38)
    cover_h = int(cover_w * 1.52)
    cover_x = pad
    cover_y = gt + 20

    img = _fetch_image(cover_url)
    if img:
        img = img.resize((cover_w, cover_h), Image.Resampling.LANCZOS)
        canvas.paste(img, (cover_x, cover_y))
        draw.rectangle(
            [(cover_x-3, cover_y-3),
             (cover_x+cover_w+3, cover_y+cover_h+3)],
            outline=ACCENT, width=3
        )

    # Right column — title, author, stars, review
    rx = cover_x + cover_w + 30
    rw = W - rx - pad
    ry = cover_y

    # Title
    tf = _font("display", 68)
    # Wrap title
    title_words = title.split()
    title_lines, line = [], ""
    for w in title_words:
        test = (line+" "+w).strip()
        bbox = draw.textbbox((0,0), test, font=tf)
        if bbox[2]-bbox[0] > rw:
            if line: title_lines.append(line)
            line = w
        else:
            line = test
    if line: title_lines.append(line)

    for li, ln in enumerate(title_lines[:3]):
        draw.text((rx, ry + li*72), ln, font=tf, fill=WHITE)

    title_h = len(title_lines[:3]) * 72
    ry += title_h + 10

    # Author
    af = _font("regular", 32)
    draw.text((rx, ry), f"by {author}", font=af, fill=GRAY_DIM+(200,))
    ry += 44

    # Divider
    draw.rectangle([(rx, ry),(rx+rw, ry+2)], fill=ACCENT+(80,))
    ry += 14

    # Stars
    # Stars — drawn as dots
    _draw_rating_dots(draw, rating, cx=rx + 80, cy=ry + 16, dot_size=18, gap=6)
    ry += 48

    # Rating number
    rf = _font("bold", 28)
    draw.text((rx, ry), f"{rating}/5", font=rf, fill=ACCENT+(200,))
    ry += 40

    # Review text — below cover if needed
    review_top = max(cover_y + cover_h + 30, ry + 20)
    review_top = cover_y + cover_h + 30

    draw.rectangle([(pad, review_top - 8),(W - pad, review_top - 5)],
                   fill=ACCENT+(60,))

    review_font = _font("regular", 30)
    # Wrap review text
    words = review_text.split()
    lines, line = [], ""
    max_w = W - pad*2
    for w in words:
        test = (line+" "+w).strip()
        bbox = draw.textbbox((0,0), test, font=review_font)
        if bbox[2]-bbox[0] > max_w:
            if line: lines.append(line)
            line = w
        else:
            line = test
    if line: lines.append(line)

    lh = 38
    for li, ln in enumerate(lines[:8]):
        draw.text((pad, review_top + 10 + li*lh), ln,
                  font=review_font, fill=GRAY+(200,))

    _footer(canvas, review_date.strftime("%B %d, %Y").upper())
    return _save(canvas, "book_02_review")


# ─────────────────────────────────────────────────────────
# SLIDE 3 — BOOKS READ IN 2026
# ─────────────────────────────────────────────────────────
def _draw_rating_dots(draw: ImageDraw.ImageDraw, rating: float,
                       cx: int, cy: int, dot_size: int = 10, gap: int = 5):
    """Draw rating as filled/half/empty dots — works with any font."""
    total_w = 5 * dot_size + 4 * gap
    x = cx - total_w // 2
    full = int(rating)
    has_half = (rating - full) >= 0.5

    for i in range(5):
        x1 = x + i * (dot_size + gap)
        x2 = x1 + dot_size
        y1 = cy - dot_size // 2
        y2 = cy + dot_size // 2

        if i < full:
            # Full — solid gold
            draw.rectangle([(x1, y1), (x2, y2)], fill=GOLD)
        elif i == full and has_half:
            # Half — left half gold, right half dim
            mid = x1 + dot_size // 2
            draw.rectangle([(x1, y1), (mid, y2)], fill=GOLD)
            draw.rectangle([(mid, y1), (x2, y2)], fill=GRAY_DIM)
        else:
            # Empty — dim outline
            draw.rectangle([(x1, y1), (x2, y2)], outline=GRAY_DIM, width=1)


def build_books_read(books: list, review_date: date) -> Path:
    """
    books: list of dicts from DB.
    Displayed as a ranked list with dot ratings.
    """
    canvas = _base()
    header_bottom = _header(canvas, "2026 READING LIST")
    draw = ImageDraw.Draw(canvas)

    sf = _font("small", 28)
    draw.text((W//2, header_bottom+20),
              f"{len(books)} BOOK{'S' if len(books) != 1 else ''} READ SO FAR",
              font=sf, fill=ACCENT+(150,), anchor="mm")

    gt = header_bottom + 52
    gb = H - 78
    pad = 36
    max_items = min(len(books), 14)
    item_h = (gb - gt) // max(max_items, 1)
    item_h = min(item_h, 82)

    for idx, book in enumerate(books[:max_items]):
        y = gt + idx * item_h
        if y + item_h > gb:
            break

        # Alternate row tint
        if idx % 2 == 0:
            ov = Image.new("RGBA", SIZE, (0,0,0,0))
            od = ImageDraw.Draw(ov)
            od.rectangle([(pad-10, y),(W-pad+10, y+item_h-4)],
                         fill=(20,15,5,30))
            canvas.alpha_composite(ov)
            draw = ImageDraw.Draw(canvas)

        # Number
        nf = _font("display", 34)
        draw.text((pad, y+item_h//2), f"{idx+1}.",
                  font=nf, fill=ACCENT+(180,), anchor="lm")

        # Title
        tf = _font("bold", 30)
        title_text = book["title"][:26]
        draw.text((pad+52, y+8), title_text, font=tf, fill=WHITE)

        # Author + year
        af = _font("regular", 22)
        year = str(book.get("date_reviewed", "2026"))[:4]
        draw.text((pad+52, y+42), f"by {book['author']} · {year}",
                  font=af, fill=GRAY_DIM+(180,))

        # Rating dots right side
        _draw_rating_dots(draw, book["rating"],
                         cx=W-pad-52, cy=y+item_h//2,
                         dot_size=12, gap=5)

    _footer(canvas, review_date.strftime("%B %d, %Y").upper())
    return _save(canvas, "book_03_reading_list")


# ─────────────────────────────────────────────────────────
# SLIDE 4 — NEXT READ
# ─────────────────────────────────────────────────────────
def build_next_read(title: str, author: str, cover_url: str,
                    review_date: date) -> Path:
    canvas = _base()
    header_bottom = _header(canvas, "NEXT ON THE LIST")
    draw = ImageDraw.Draw(canvas)

    # Cover centered
    cover_h = int(H * 0.52)
    cover_w = int(cover_h * 0.66)
    cover_x = (W - cover_w) // 2
    cover_y = header_bottom + 30

    img = _fetch_image(cover_url)
    if img:
        # Shadow
        shadow = Image.new("RGBA", SIZE, (0,0,0,0))
        sd = ImageDraw.Draw(shadow)
        for offset in range(16, 0, -1):
            sd.rectangle(
                [(cover_x+offset, cover_y+offset),
                 (cover_x+cover_w+offset, cover_y+cover_h+offset)],
                fill=(0,0,0,8)
            )
        canvas.alpha_composite(shadow)
        img = img.resize((cover_w, cover_h), Image.Resampling.LANCZOS)
        canvas.paste(img, (cover_x, cover_y))
        draw = ImageDraw.Draw(canvas)
        draw.rectangle(
            [(cover_x-4, cover_y-4),
             (cover_x+cover_w+4, cover_y+cover_h+4)],
            outline=ACCENT, width=4
        )
    else:
        draw.rectangle([(cover_x, cover_y),(cover_x+cover_w, cover_y+cover_h)],
                       fill=(20,15,5))
        pf = _font("bold", 40)
        draw.text((cover_x+cover_w//2, cover_y+cover_h//2),
                  title[:20], font=pf, fill=ACCENT, anchor="mm")

    # Text below cover
    text_y = cover_y + cover_h + 36

    # Decorative line
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([(W//2-150, text_y),(W//2+150, text_y+3)], fill=ACCENT+(80,))
    text_y += 20

    tf = _font("display", 80)
    draw.text((W//2, text_y + 48), title[:22].upper(),
              font=tf, fill=WHITE, anchor="mm")

    af = _font("regular", 36)
    draw.text((W//2, text_y + 106), f"by {author}",
              font=af, fill=ACCENT+(200,), anchor="mm")

    # "Coming next" tag
    tag_f = _font("small", 26)
    tag_y = text_y + 148
    tag_text = "READING NEXT"
    bbox = draw.textbbox((0,0), tag_text, font=tag_f)
    tw = bbox[2]-bbox[0]
    ov = Image.new("RGBA", SIZE, (0,0,0,0))
    od = ImageDraw.Draw(ov)
    od.rectangle([(W//2-tw//2-16, tag_y-4),(W//2+tw//2+16, tag_y+30)],
                 fill=ACCENT+(40,), outline=ACCENT+(180,), width=2)
    canvas.alpha_composite(ov)
    draw = ImageDraw.Draw(canvas)
    draw.text((W//2, tag_y+13), tag_text,
              font=tag_f, fill=ACCENT+(230,), anchor="mm")

    _footer(canvas, review_date.strftime("%B %d, %Y").upper())
    return _save(canvas, "book_04_next_read")