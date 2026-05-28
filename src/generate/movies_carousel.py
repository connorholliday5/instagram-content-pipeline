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
ORANGE   = (255, 140, 0)
WHITE    = (255, 255, 255)
GRAY     = (170, 170, 170)
GRAY_DIM = (75, 75, 90)
GOLD     = (255, 215, 0)
GREEN    = (0, 200, 100)
RED      = (220, 30, 30)

# Movie accent color — cinematic red/gold
ACCENT   = (200, 30, 30)


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


def _fetch_poster(url: str) -> Optional[Image.Image]:
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
    rng = random.Random(99)
    draw = ImageDraw.Draw(canvas)
    for _ in range(280):
        x = rng.randint(0, W-1)
        y = rng.randint(0, H-1)
        r = rng.choice([1,1,1,2])
        a = rng.randint(60, 200)
        draw.ellipse([(x-r,y-r),(x+r,y+r)],
                     fill=(200+rng.randint(0,55), 200+rng.randint(0,45), 220+rng.randint(0,35), a))


def _base() -> Image.Image:
    canvas = Image.new("RGBA", SIZE, BG+(255,))
    _stars(canvas)
    # Cinematic dark vignette
    ov = Image.new("RGBA", SIZE, (0,0,0,0))
    d = ImageDraw.Draw(ov)
    d.ellipse([(-200,-200),(W+200,600)], fill=(0,0,0,60))
    d.ellipse([(-200,750),(W+200,H+200)], fill=(0,0,0,80))
    canvas.alpha_composite(ov)
    return canvas


def _header(canvas: Image.Image, title: str, subtitle: str = "") -> int:
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


def _footer(canvas: Image.Image, date_str: str):
    fy = H - 72
    ov = Image.new("RGBA", SIZE, (0,0,0,0))
    od = ImageDraw.Draw(ov)
    od.rectangle([(0,fy),(W,H)], fill=(3,3,10,230))
    canvas.alpha_composite(ov)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([(0,fy),(W,fy+3)], fill=ACCENT+(80,))
    df = _font("display", 36)
    draw.text((W-32, fy+36), date_str, font=df, fill=GRAY_DIM+(180,), anchor="rm")
    hf = _font("small", 22)
    draw.text((W-32, H-14), "@the.watch_tower",
              font=hf, fill=GRAY_DIM+(80,), anchor="rm")


def _place_poster(canvas: Image.Image, url: Optional[str],
                  box: tuple, border_color: tuple,
                  num: int = 0, label: str = ""):
    x1, y1, x2, y2 = [int(v) for v in box]
    bw = 4
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([(x1,y1),(x2,y2)], outline=border_color[:3], width=bw)

    iw = x2-x1-bw*2
    ih = y2-y1-bw*2
    ix, iy = x1+bw, y1+bw

    img = _fetch_poster(url) if url else None
    if img:
        ow, oh = img.size
        target_ratio = iw / ih
        src_ratio = ow / oh
        if src_ratio > target_ratio:
            new_w = int(oh * target_ratio)
            left = (ow - new_w) // 2
            img = img.crop((left, 0, left+new_w, oh))
        else:
            new_h = int(ow / target_ratio)
            img = img.crop((0, 0, ow, new_h))
        img = img.resize((iw, ih), Image.Resampling.LANCZOS)
        canvas.paste(img, (ix, iy))
    else:
        ph = Image.new("RGB", (iw, ih), (15, 10, 20))
        ph_draw = ImageDraw.Draw(ph)
        pf = _font("bold", max(20, iw//10))
        words = label.split()
        lines, line = [], ""
        for w in words:
            test = (line+" "+w).strip()
            if ph_draw.textbbox((0,0),test,font=pf)[2] > iw-10:
                if line: lines.append(line)
                line = w
            else:
                line = test
        if line: lines.append(line)
        lh = max(24, iw//10) + 4
        sy = (ih - len(lines)*lh) // 2
        for li, ln in enumerate(lines):
            ph_draw.text((iw//2, sy+li*lh), ln, font=pf,
                         fill=(80,60,80), anchor="mm")
        canvas.paste(ph, (ix, iy))

    if num:
        bs = 44
        draw.rectangle([(x1+bw+3,y1+bw+3),(x1+bw+3+bs,y1+bw+3+bs)], fill=(0,0,0))
        nf = _font("display", bs-8)
        draw.text((x1+bw+3+bs//2, y1+bw+3+bs//2), str(num),
                  font=nf, fill=WHITE, anchor="mm")


def _pill_overlay(canvas: Image.Image, box: tuple, text: str,
                  color: tuple, subfont_size: int = 28):
    x1, y1, x2, y2 = [int(v) for v in box]
    draw = ImageDraw.Draw(canvas)
    cx = (x1+x2)//2
    rf = _font("bold", subfont_size)
    bbox = draw.textbbox((0,0), text, font=rf)
    tw = bbox[2]-bbox[0]
    pill_h = subfont_size + 10
    pill_y = y2 - pill_h - 14
    px1 = cx - tw//2 - 14
    px2 = cx + tw//2 + 14

    ov = Image.new("RGBA", SIZE, (0,0,0,0))
    od = ImageDraw.Draw(ov)
    od.rectangle([(x1+4, pill_y-8),(x2-4, y2-4)], fill=(0,0,0,185))
    canvas.alpha_composite(ov)

    ov2 = Image.new("RGBA", SIZE, (0,0,0,0))
    od2 = ImageDraw.Draw(ov2)
    od2.rectangle([(px1, pill_y),(px2, pill_y+pill_h)],
                  fill=color+(55,), outline=color+(220,), width=2)
    canvas.alpha_composite(ov2)

    draw = ImageDraw.Draw(canvas)
    draw.text((cx, pill_y+pill_h//2), text,
              font=rf, fill=color+(240,), anchor="mm")


def _draw_station(canvas: Image.Image, top_y: int, scale: float = 0.88):
    """Reuse same station from comics carousel."""
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
        for add, alpha in [(100,4),(65,10),(35,18),(10,28)]:
            ov = Image.new("RGBA", SIZE, (0,0,0,0))
            od = ImageDraw.Draw(ov)
            od.ellipse([(cx-gr-add,gy-grv-add//3),(cx+gr+add,gy+grv+add//3)],
                       fill=(255,120,0,alpha))
            canvas.alpha_composite(ov)
    draw = ImageDraw.Draw(canvas)

    def box(x1,y1,x2,y2,fill,edge=True):
        x1,y1,x2,y2=int(x1),int(y1),int(x2),int(y2)
        draw.rectangle([(x1,y1),(x2,y2)],fill=fill)
        if edge:
            draw.line([(x1,y1),(x2,y1)],fill=EDGE,width=1)
            draw.line([(x1,y1),(x1,y2)],fill=EDGE,width=1)

    def panels(x1,y1,x2,h,n=3,gap=3):
        x1,y1,x2,h=int(x1),int(y1),int(x2),int(h)
        pw=(x2-x1-gap*(n-1))//n
        for i in range(n):
            px=x1+i*(pw+gap)
            draw.rectangle([(px,y1),(px+pw,y1+h)],fill=PANEL)

    def ring(gy,gr,grv,width,alpha_fill=25):
        draw.ellipse([(cx-gr-4,gy-grv-4),(cx+gr+4,gy+grv+4)],fill=C3)
        draw.ellipse([(cx-gr,gy-grv),(cx+gr,gy+grv)],outline=ORANGE,width=width)
        draw.ellipse([(cx-gr+9,gy-grv+4),(cx+gr-9,gy+grv-4)],outline=(200,100,0,140),width=2)
        ov=Image.new("RGBA",SIZE,(0,0,0,0)); od=ImageDraw.Draw(ov)
        od.ellipse([(cx-gr,gy-grv),(cx+gr,gy+grv)],fill=(255,120,0,alpha_fill))
        canvas.alpha_composite(ov)
        d=ImageDraw.Draw(canvas)
        for deg in range(0,360,45):
            a=deg*math.pi/180
            bx=int(cx+gr*math.cos(a)); by=int(gy+int(grv*0.6)*math.sin(a))
            d.ellipse([(bx-3,by-3),(bx+3,by+3)],fill=EDGE)
        return ImageDraw.Draw(canvas)

    draw.line([(cx,top_y),(cx,top_y-s(52))],fill=(180,200,255,200),width=s(4))
    draw.line([(cx-s(20),top_y-s(28)),(cx+s(20),top_y-s(28))],fill=(150,165,200,180),width=s(3))
    draw.ellipse([(cx-s(8),top_y-s(60)),(cx+s(8),top_y-s(44))],fill=(255,150,0))

    draw.ellipse([(cx-s(62),top_y-s(10)),(cx+s(62),top_y+s(20))],fill=C1)
    box(cx-s(62),top_y,cx+s(62),top_y+s(26),C1)
    box(cx-s(30),top_y+s(26),cx+s(30),top_y+s(86),C2)
    for wy in [top_y+s(34),top_y+s(52),top_y+s(70)]:
        panels(cx-s(24),wy,cx+s(24),s(12),n=2)

    draw = ring(*rings[0], width=s(7), alpha_fill=30)
    box(cx-s(70),top_y+s(128),cx+s(70),top_y+s(160),C1)
    panels(cx-s(58),top_y+s(138),cx+s(58),s(13),n=4,gap=4)

    draw = ring(*rings[1], width=s(8), alpha_fill=32)
    box(cx-s(118),top_y+s(238),cx+s(118),top_y+s(306),C1)
    rng=random.Random(999)
    for wy in [top_y+s(248),top_y+s(263),top_y+s(278),top_y+s(293)]:
        draw.rectangle([(cx-s(102),wy),(cx+s(102),wy+s(9))],fill=C3)
        for i in range(5):
            wx=cx-s(96)+i*s(42)
            lit=rng.random()>0.35
            draw.rectangle([(wx,wy+1),(wx+s(34),wy+s(7))],
                           fill=(48,68,108) if lit else PANEL)
    for sign in [-1,1]:
        mx1=cx+sign*s(118); mx2=cx+sign*s(238)
        my1=int(top_y+s(242)); my2=int(top_y+s(300))
        draw.rectangle([(min(mx1,mx2),my1),(max(mx1,mx2),my2)],fill=C2)

    draw = ring(*rings[2], width=s(6), alpha_fill=22)
    box(cx-s(42),top_y+s(306),cx+s(42),top_y+s(370),C2)
    box(cx-s(84),top_y+s(370),cx+s(84),top_y+s(416),C1)

    draw = ring(*rings[3], width=s(5), alpha_fill=15)
    box(cx-s(34),top_y+s(416),cx+s(34),top_y+s(458),C2)
    draw.ellipse([(cx-s(24),top_y+s(448)),(cx+s(24),top_y+s(466))],fill=C3)


# ─────────────────────────────────────────────────────────
# SLIDE 1 — COVER
# ─────────────────────────────────────────────────────────
def build_movies_cover(month_date: date) -> Path:
    canvas = _base()
    station_top = 35
    _draw_station(canvas, station_top, scale=0.88)

    fade_start = station_top + int(470 * 0.88)
    fade = Image.new("RGBA", SIZE, (0,0,0,0))
    fd = ImageDraw.Draw(fade)
    for y in range(fade_start - 60, H):
        t = min(1.0, (y-(fade_start-60))/320)
        fd.line([(0,y),(W,y)], fill=(3,3,10,int(180*t**0.6)))
    canvas.alpha_composite(fade)

    draw = ImageDraw.Draw(canvas)
    text_area_top = fade_start - 40
    text_area_h = H - text_area_top - 40
    text_mid = text_area_top + text_area_h // 2

    hf = _font("display", 158)
    line_h = 158
    total_h = line_h*2 + 20 + 60 + 14 + 40
    block_top = text_mid - total_h//2

    draw.text((W//2, block_top+line_h//2), "MOVIES",
              font=hf, fill=WHITE, anchor="mm")
    draw.text((W//2, block_top+line_h+16+line_h//2), "THIS MONTH",
              font=hf, fill=WHITE, anchor="mm")

    df = _font("display", 72)
    date_y = block_top + line_h*2 + 40
    draw.text((W//2, date_y), month_date.strftime("%B %Y").upper(),
              font=df, fill=ACCENT+(210,), anchor="mm")

    bf = _font("small", 34)
    draw.text((W//2, date_y+54), "THE WATCHTOWER",
              font=bf, fill=GRAY_DIM+(200,), anchor="mm")

    hf2 = _font("small", 22)
    draw.text((W-36, H-16), "@the.watch_tower",
              font=hf2, fill=GRAY_DIM+(80,), anchor="rm")

    return _save(canvas, "movie_01_cover")


# ─────────────────────────────────────────────────────────
# SLIDE 2 — TOP 10 ANTICIPATED
# ─────────────────────────────────────────────────────────
def build_movies_top10(movies: list, month_date: date,
                       get_title, get_poster_url) -> Path:
    canvas = _base()
    header_bottom = _header(canvas, "TOP 10 MOST ANTICIPATED")

    pad = 10
    gt = header_bottom + 14
    gb = H - 78

    # 4 cols x 3 rows = 12 cells, use 10 — gives portrait ratio ~0.74
    cols, rows = 4, 3
    cw = (W - pad*(cols+1)) // cols
    ch = (gb - gt - pad*(rows-1)) // rows

    for idx in range(10):
        col = idx % cols
        row = idx // cols
        # Last row has only 2 items — center them
        if row == 2:
            items_in_last_row = 10 - (cols * (rows-1))  # = 2
            total_w = items_in_last_row * cw + (items_in_last_row-1) * pad
            start_x = (W - total_w) // 2
            col_in_last = idx - cols*(rows-1)
            x1 = start_x + col_in_last*(cw+pad)
        else:
            x1 = pad + col*(cw+pad)
        y1 = gt + row*(ch+pad)
        if idx < len(movies):
            movie = movies[idx]
            _place_poster(canvas, get_poster_url(movie),
                         (x1, y1, x1+cw, y1+ch),
                         ACCENT, idx+1, get_title(movie))

    _footer(canvas, month_date.strftime("%B %Y").upper())
    return _save(canvas, "movie_02_top10")


# ─────────────────────────────────────────────────────────
# SLIDE 3 — YOUR PICKS
# ─────────────────────────────────────────────────────────
def build_movies_picks(picks: list, month_date: date,
                       get_title, get_poster_url) -> Path:
    canvas = _base()
    header_bottom = _header(canvas, "WATCHTOWER'S PICKS OF THE MONTH")
    draw = ImageDraw.Draw(canvas)

    pad = 10
    gt = header_bottom + 14
    gb = H - 78
    n = len(picks)

    if n == 0:
        mf = _font("bold", 72)
        draw.text((W//2, H//2), "NO PICKS THIS MONTH",
                  font=mf, fill=GRAY_DIM+(180,), anchor="mm")
    elif n == 1:
        # Single — centered portrait
        cw = int(W * 0.52)
        x1 = (W - cw) // 2
        _place_poster(canvas, get_poster_url(picks[0]),
                     (x1, gt, x1+cw, gb), ACCENT, 1, get_title(picks[0]))
    elif n == 2:
        # Two side by side portrait
        cw = (W - pad*3) // 2
        ch = gb - gt
        for idx, movie in enumerate(picks):
            x1 = pad + idx*(cw+pad)
            _place_poster(canvas, get_poster_url(movie),
                         (x1, gt, x1+cw, gt+ch),
                         ACCENT, idx+1, get_title(movie))
    elif n <= 4:
        # 2 cols, up to 2 rows — portrait cells
        cols = 2
        rows = (n+1)//2
        cw = (W - pad*(cols+1)) // cols
        ch = (gb - gt - pad*(rows-1)) // rows
        for idx, movie in enumerate(picks):
            col = idx % cols
            row = idx // cols
            x1 = pad + col*(cw+pad)
            y1 = gt + row*(ch+pad)
            if n % 2 == 1 and idx == n-1:
                x1 = (W - cw) // 2
            _place_poster(canvas, get_poster_url(movie),
                         (x1, y1, x1+cw, y1+ch),
                         ACCENT, idx+1, get_title(movie))
    elif n <= 6:
        # 3 cols, up to 2 rows
        cols = 3
        rows = (n+cols-1)//cols
        cw = (W - pad*(cols+1)) // cols
        ch = (gb - gt - pad*(rows-1)) // rows
        for idx, movie in enumerate(picks):
            col = idx % cols
            row = idx // cols
            items_in_row = min(cols, n - row*cols)
            if items_in_row < cols:
                total_w = items_in_row*cw + (items_in_row-1)*pad
                x1 = (W - total_w)//2 + (idx % cols)*(cw+pad)
            else:
                x1 = pad + col*(cw+pad)
            y1 = gt + row*(ch+pad)
            _place_poster(canvas, get_poster_url(movie),
                         (x1, y1, x1+cw, y1+ch),
                         ACCENT, idx+1, get_title(movie))
    else:
        # 4 cols x 3 rows max — same as top 10 grid
        cols = 4
        rows = (n+cols-1)//cols
        cw = (W - pad*(cols+1)) // cols
        ch = (gb - gt - pad*(rows-1)) // rows
        for idx, movie in enumerate(picks):
            col = idx % cols
            row = idx // cols
            items_in_row = min(cols, n - row*cols)
            if items_in_row < cols:
                total_w = items_in_row*cw + (items_in_row-1)*pad
                x1 = (W - total_w)//2 + (idx % items_in_row)*(cw+pad)
            else:
                x1 = pad + col*(cw+pad)
            y1 = gt + row*(ch+pad)
            _place_poster(canvas, get_poster_url(movie),
                         (x1, y1, x1+cw, y1+ch),
                         ACCENT, idx+1, get_title(movie))

    _footer(canvas, month_date.strftime("%B %Y").upper())
    return _save(canvas, "movie_03_picks")


# ─────────────────────────────────────────────────────────
# SLIDE 4 — HIGHEST GROSSING LAST MONTH
# ─────────────────────────────────────────────────────────
def build_movies_grossing(movies: list, month_date: date,
                          get_title, get_poster_url, get_revenue,
                          format_revenue) -> Path:
    canvas = _base()

    # Get last month name for header
    from calendar import month_name
    first_this = month_date.replace(day=1)
    from datetime import timedelta
    last_prev = first_this - timedelta(days=1)
    prev_month_name = last_prev.strftime("%B %Y").upper()

    header_bottom = _header(canvas, "HIGHEST GROSSING LAST MONTH")
    draw = ImageDraw.Draw(canvas)

    sf = _font("small", 30)
    draw.text((W//2, header_bottom+22), prev_month_name,
              font=sf, fill=GOLD+(160,), anchor="mm")

    pad = 20
    gt = header_bottom + 52
    gb = H - 78
    movies = movies[:3]
    n = max(len(movies), 1)
    cw = (W - pad*(n+1)) // n
    ch = gb - gt

    for idx, movie in enumerate(movies):
        x1 = pad + idx*(cw+pad)
        y1 = gt

        # Rank badge color
        rank_colors = [GOLD, (192,192,192), (205,127,50)]  # gold, silver, bronze
        border_color = rank_colors[idx] if idx < len(rank_colors) else GRAY_DIM

        _place_poster(canvas, get_poster_url(movie),
                     (x1, y1, x1+cw, y1+ch),
                     border_color, idx+1, get_title(movie))

        # Revenue pill overlay
        rev = get_revenue(movie)
        if rev > 0:
            rev_str = format_revenue(rev)
            _pill_overlay(canvas, (x1, y1, x1+cw, y1+ch),
                         rev_str, border_color, subfont_size=30)

    _footer(canvas, month_date.strftime("%B %Y").upper())
    return _save(canvas, "movie_04_grossing")