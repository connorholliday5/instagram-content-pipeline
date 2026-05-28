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

PUBLISHER_COLORS = {
    "dc":         (0, 102, 255),
    "marvel":     (204, 0, 0),
    "image":      (255, 102, 0),
    "dark horse": (0, 170, 68),
    "idw":        (255, 204, 0),
    "default":    (120, 120, 120),
}

PUBLISHER_MAP = {
    "dc comics":         "dc",
    "marvel":            "marvel",
    "image comics":      "image",
    "dark horse comics": "dark horse",
    "idw publishing":    "idw",
}


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


def _fetch_cover(url: str) -> Optional[Image.Image]:
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
    rng = random.Random(42)
    draw = ImageDraw.Draw(canvas)
    for _ in range(320):
        x = rng.randint(0, W-1)
        y = rng.randint(0, H-1)
        r = rng.choice([1,1,1,2])
        a = rng.randint(80, 220)
        draw.ellipse([(x-r,y-r),(x+r,y+r)],
                     fill=(200+rng.randint(0,55), 210+rng.randint(0,45), 255, a))


def _nebula(canvas: Image.Image):
    ov = Image.new("RGBA", SIZE, (0,0,0,0))
    d = ImageDraw.Draw(ov)
    d.ellipse([(0,0),(680,560)], fill=(10,20,80,18))
    d.ellipse([(600,30),(W,540)], fill=(20,10,60,12))
    canvas.alpha_composite(ov)


def _base() -> Image.Image:
    canvas = Image.new("RGBA", SIZE, BG+(255,))
    _stars(canvas)
    _nebula(canvas)
    return canvas


def _pub_key(publisher: str) -> str:
    return PUBLISHER_MAP.get(publisher.lower().strip(), "default")


def _pub_color(publisher: str) -> tuple:
    return PUBLISHER_COLORS.get(_pub_key(publisher), PUBLISHER_COLORS["default"])


def _header(canvas: Image.Image, title: str) -> int:
    ov = Image.new("RGBA", SIZE, (0,0,0,0))
    od = ImageDraw.Draw(ov)
    od.rectangle([(0,0),(W,162)], fill=(3,3,10,242))
    canvas.alpha_composite(ov)
    draw = ImageDraw.Draw(canvas)
    bf = _font("small", 34)
    draw.text((W//2, 32), "THE WATCHTOWER",
              font=bf, fill=ORANGE+(180,), anchor="mm")
    tf = _font("display", 96)
    draw.text((W//2, 112), title, font=tf, fill=WHITE, anchor="mm")
    rule_y = 158
    draw.rectangle([(50,rule_y),(W-50,rule_y+3)], fill=ORANGE+(100,))
    return rule_y + 3


def _footer(canvas: Image.Image, date_str: str, show_legend: bool = True):
    fy = H - 72
    ov = Image.new("RGBA", SIZE, (0,0,0,0))
    od = ImageDraw.Draw(ov)
    od.rectangle([(0,fy),(W,H)], fill=(3,3,10,210))
    canvas.alpha_composite(ov)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([(0,fy),(W,fy+3)], fill=ORANGE+(80,))

    if show_legend:
        items = [("DC","dc"),("MARVEL","marvel"),("IMAGE","image"),
                 ("DARK HORSE","dark horse"),("IDW","idw")]
        x = 28
        dot = 13
        lf = _font("small", 24)
        for label, key in items:
            color = PUBLISHER_COLORS[key]
            cy = fy + 28
            draw.ellipse([(x,cy),(x+dot,cy+dot)], fill=color)
            draw.text((x+dot+6, cy-1), label, font=lf, fill=GRAY_DIM)
            bw = draw.textbbox((0,0),label,font=lf)[2]
            x += dot + 8 + bw + 16

    df = _font("display", 36)
    draw.text((W-32, fy+36), date_str, font=df, fill=GRAY_DIM+(180,), anchor="rm")
    hf = _font("small", 22)
    draw.text((W-32, H-14), "@the.watch_tower",
              font=hf, fill=GRAY_DIM+(80,), anchor="rm")


def _place_cover(canvas: Image.Image, cover_url: Optional[str],
                 box: tuple, border_color: tuple,
                 num: int = 0, label: str = ""):
    x1, y1, x2, y2 = [int(v) for v in box]
    bw = 4
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([(x1,y1),(x2,y2)], outline=border_color[:3], width=bw)

    iw = x2-x1-bw*2
    ih = y2-y1-bw*2
    ix, iy = x1+bw, y1+bw

    img = _fetch_cover(cover_url) if cover_url else None
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
        ph = Image.new("RGB", (iw, ih), (12,12,22))
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
                         fill=(70,70,90), anchor="mm")
        canvas.paste(ph, (ix, iy))

    if num:
        bs = 42
        draw.rectangle([(x1+bw+3,y1+bw+3),(x1+bw+3+bs,y1+bw+3+bs)], fill=(0,0,0))
        nf = _font("display", bs-8)
        draw.text((x1+bw+3+bs//2, y1+bw+3+bs//2), str(num),
                  font=nf, fill=WHITE, anchor="mm")


REASON_DESCRIPTIONS = {
    "#1 ISSUE":         "Great jumping-on point",
    "FACSIMILE":        "Classic issue reprinted",
    "FACSIMILE EDITION":"Classic issue reprinted",
    "ANNIVERSARY":      "Milestone issue",
    "ANNIVERSARY ISSUE":"Milestone issue",
    "OMNIBUS":          "Complete collection",
    "OMNIBUS RELEASE":  "Complete collection",
    "COMPENDIUM":       "Massive value collection",
    "FIRST APPEARANCE": "Key character debut",
    "SPECIAL EDITION":  "Exclusive release",
    "1:100 RATIO":      "Very rare — 1 per 100",
    "1:50 RATIO":       "Rare — 1 per 50 ordered",
    "1:25 RATIO":       "Limited — ask your LCS",
    "1:10 RATIO":       "Incentive variant",
    "FOIL VARIANT":     "Special cover treatment",
    "GOLD FOIL":        "Premium foil cover",
    "VIRGIN COVER":     "No logo — collector fave",
    "CONNECTING CVR":   "Part of a set",
    "SKETCH COVER":     "Art-focused variant",
    "VARIANT":          "Ask your LCS for details",
}


def _overlay_pill(canvas: Image.Image, box: tuple, reason: str, color: tuple):
    """Draw reason pill + description as overlay inside the bottom of the cover."""
    x1, y1, x2, y2 = [int(v) for v in box]
    draw = ImageDraw.Draw(canvas)
    cx_pill = (x1 + x2) // 2

    rf = _font("bold", 26)
    df = _font("regular", 22)
    desc = REASON_DESCRIPTIONS.get(reason, "")

    bbox = draw.textbbox((0,0), reason, font=rf)
    tw = bbox[2] - bbox[0]
    px1 = cx_pill - tw//2 - 14
    px2 = cx_pill + tw//2 + 14
    pill_h = 32

    strip_h = pill_h + (30 if desc else 0) + 20
    strip_y = y2 - strip_h - 6
    pill_y = strip_y + 8

    # Dark strip
    ov = Image.new("RGBA", SIZE, (0,0,0,0))
    od = ImageDraw.Draw(ov)
    od.rectangle([(x1+4, strip_y),(x2-4, y2-4)], fill=(0,0,0,185))
    canvas.alpha_composite(ov)

    # Pill background
    ov2 = Image.new("RGBA", SIZE, (0,0,0,0))
    od2 = ImageDraw.Draw(ov2)
    od2.rectangle([(px1, pill_y),(px2, pill_y+pill_h)],
                  fill=color+(55,), outline=color+(220,), width=2)
    canvas.alpha_composite(ov2)

    draw = ImageDraw.Draw(canvas)
    draw.text((cx_pill, pill_y + pill_h//2), reason,
              font=rf, fill=color+(240,), anchor="mm")

    if desc:
        draw.text((cx_pill, pill_y + pill_h + 14), desc,
                  font=df, fill=(210,210,210,200), anchor="mm")


def _draw_station(canvas: Image.Image, top_y: int, scale: float = 0.88):
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
            od.ellipse([(cx-gr-add, gy-grv-add//3),(cx+gr+add, gy+grv+add//3)],
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
        draw.ellipse([(cx-gr,gy-grv),(cx+gr,gy+grv)],
                     outline=ORANGE,width=width)
        draw.ellipse([(cx-gr+9,gy-grv+4),(cx+gr-9,gy+grv-4)],
                     outline=(200,100,0,140),width=2)
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
    ov=Image.new("RGBA",SIZE,(0,0,0,0)); od=ImageDraw.Draw(ov)
    od.ellipse([(cx-s(22),top_y-s(74)),(cx+s(22),top_y-s(30))],fill=(255,120,0,40))
    canvas.alpha_composite(ov); draw=ImageDraw.Draw(canvas)

    draw.ellipse([(cx-s(62),top_y-s(10)),(cx+s(62),top_y+s(20))],fill=C1)
    box(cx-s(62),top_y,cx+s(62),top_y+s(26),C1)
    for i in range(3):
        lx=cx-s(40)+i*s(40)
        draw.line([(lx,top_y-s(8)),(lx,top_y+s(26))],fill=PANEL,width=1)

    box(cx-s(30),top_y+s(26),cx+s(30),top_y+s(86),C2)
    for wy in [top_y+s(34),top_y+s(52),top_y+s(70)]:
        panels(cx-s(24),wy,cx+s(24),s(12),n=2)

    draw = ring(*rings[0], width=s(7), alpha_fill=30)
    box(cx-s(70),top_y+s(128),cx+s(70),top_y+s(160),C1)
    panels(cx-s(58),top_y+s(138),cx+s(58),s(13),n=4,gap=4)
    for rx in [cx-s(62),cx-s(44),cx+s(44),cx+s(62)]:
        draw.ellipse([(rx-3,top_y+s(131)),(rx+3,top_y+s(137))],fill=EDGE)
    for sign in [-1,1]:
        s1=cx+sign*s(70); s2=cx+sign*s(120)
        draw.rectangle([(min(s1,s2),top_y+s(138)),(max(s1,s2),top_y+s(150))],fill=C3)
        p1=cx+sign*s(120); p2=cx+sign*s(158)
        draw.rectangle([(min(p1,p2),top_y+s(132)),(max(p1,p2),top_y+s(156))],fill=C2)
        panels(min(p1,p2)+3,top_y+s(138),max(p1,p2)-3,s(10),n=2)

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
    for rx in range(cx-s(108),cx+s(112),s(20)):
        draw.ellipse([(rx-2,top_y+s(240)),(rx+2,top_y+s(244))],fill=EDGE)
        draw.ellipse([(rx-2,top_y+s(302)),(rx+2,top_y+s(306))],fill=EDGE)
    for sign in [-1,1]:
        mx1=cx+sign*s(118); mx2=cx+sign*s(238)
        my1=int(top_y+s(242)); my2=int(top_y+s(300))
        draw.rectangle([(min(mx1,mx2),my1),(max(mx1,mx2),my2)],fill=C2)
        draw.line([(min(mx1,mx2),my1),(max(mx1,mx2),my1)],fill=EDGE,width=2)
        panels(min(mx1,mx2)+4,my1+8,max(mx1,mx2)-4,s(12),n=2,gap=3)
        panels(min(mx1,mx2)+4,my1+26,max(mx1,mx2)-4,s(12),n=2,gap=3)
        panels(min(mx1,mx2)+4,my1+44,max(mx1,mx2)-4,s(12),n=2,gap=3)
        for ci in range(3):
            cy2=my1+8+ci*s(17)
            draw.rectangle([(min(mx1,mx2)+4,cy2),(max(mx1,mx2)-4,cy2+s(13))],fill=(16,26,60))

    draw = ring(*rings[2], width=s(6), alpha_fill=22)
    box(cx-s(42),top_y+s(306),cx+s(42),top_y+s(370),C2)
    for wy in [top_y+s(316),top_y+s(334),top_y+s(352)]:
        panels(cx-s(34),wy,cx+s(34),s(11),n=2)
    box(cx-s(84),top_y+s(370),cx+s(84),top_y+s(416),C1)
    for wy in [top_y+s(378),top_y+s(392),top_y+s(406)]:
        draw.rectangle([(cx-s(70),wy),(cx+s(70),wy+s(8))],fill=C3)

    draw = ring(*rings[3], width=s(5), alpha_fill=15)
    box(cx-s(34),top_y+s(416),cx+s(34),top_y+s(458),C2)
    draw.ellipse([(cx-s(24),top_y+s(448)),(cx+s(24),top_y+s(466))],fill=C3)


# ─────────────────────────────────────────────────────────
# SLIDE 1 — COVER
# ─────────────────────────────────────────────────────────
def build_cover_slide(week_date: date) -> Path:
    canvas = _base()  # stars full canvas

    # Nebula
    ov=Image.new("RGBA",SIZE,(0,0,0,0)); od=ImageDraw.Draw(ov)
    od.ellipse([(0,0),(680,560)],fill=(10,20,80,18))
    od.ellipse([(600,30),(W,540)],fill=(20,10,60,12))
    canvas.alpha_composite(ov)

    station_top = 35
    _draw_station(canvas, station_top, scale=0.88)

    # Subtle fade only behind text area
    station_bottom = station_top + int(470 * 0.88)
    fade = Image.new("RGBA", SIZE, (0,0,0,0))
    fd = ImageDraw.Draw(fade)
    for y in range(station_bottom - 60, H):
        t = min(1.0, (y-(station_bottom-60))/320)
        fd.line([(0,y),(W,y)], fill=(3,3,10,int(180*t**0.6)))
    canvas.alpha_composite(fade)

    draw = ImageDraw.Draw(canvas)
    text_area_top = station_bottom - 40
    text_area_h = H - text_area_top - 40
    text_mid = text_area_top + text_area_h // 2

    hf = _font("display", 158)
    line_h = 158
    total_h = line_h*2 + 20 + 60 + 14 + 40
    block_top = text_mid - total_h//2

    draw.text((W//2, block_top+line_h//2), "NEW COMIC", font=hf, fill=WHITE, anchor="mm")
    draw.text((W//2, block_top+line_h+16+line_h//2), "BOOK DAY", font=hf, fill=WHITE, anchor="mm")

    df = _font("display", 72)
    date_y = block_top + line_h*2 + 40
    draw.text((W//2, date_y), week_date.strftime("%B %d, %Y").upper(),
              font=df, fill=ORANGE+(210,), anchor="mm")

    bf = _font("small", 34)
    draw.text((W//2, date_y+54), "THE WATCHTOWER",
              font=bf, fill=GRAY_DIM+(200,), anchor="mm")

    hf2 = _font("small", 22)
    draw.text((W-36, H-16), "@the.watch_tower",
              font=hf2, fill=GRAY_DIM+(80,), anchor="rm")

    return _save(canvas, "slide_01_cover")


# ─────────────────────────────────────────────────────────
# SLIDE 2 — TOP 10
# ─────────────────────────────────────────────────────────
def build_top10_slide(issues: list, week_date: date,
                      get_title, get_cover_url, get_publisher) -> Path:
    canvas = _base()
    header_bottom = _header(canvas, "TOP 10 NEW COMICS THIS WEEK")

    pad = 10
    gt = header_bottom + 14
    gb = H - 78

    # Top row: #1 wide (portrait) + #2
    # Top row: 2 equal portrait cells
    top_h = int((gb - gt) * 0.50)
    mid = W // 2 - pad // 2
    c1 = (pad, gt, mid, gt + top_h)
    c2 = (mid + pad, gt, W - pad, gt + top_h)

    for i, box in enumerate([c1, c2]):
        if i < len(issues):
            issue = issues[i]
            color = _pub_color(get_publisher(issue))
            title = get_title(issue)
            _place_cover(canvas, get_cover_url(issue), box, color, i+1, title)
            # Title label overlay on both top covers
            d = ImageDraw.Draw(canvas)
            lf = _font("bold", 28)
            ly = int(box[3]) - 48
            d.rectangle([(int(box[0]), ly), (int(box[2]), int(box[3]))],
                         fill=(0, 0, 0, 185))
            d.text((int(box[0]) + 10, ly + 8), title[:22], font=lf, fill=WHITE)

    # Bottom 8 covers — 4 columns x 2 rows for portrait orientation
    bt = gt + top_h + pad
    bot_h = gb - bt
    cols, rows = 4, 2
    cw = (W - pad*(cols+1)) // cols
    ch = (bot_h - pad*(rows-1)) // rows

    for idx in range(8):
        col = idx % cols
        row = idx // cols
        x1 = pad + col*(cw+pad)
        y1 = bt + row*(ch+pad)
        ii = idx + 2
        if ii < len(issues):
            issue = issues[ii]
            color = _pub_color(get_publisher(issue))
            _place_cover(canvas, get_cover_url(issue),
                         (x1, y1, x1+cw, y1+ch),
                         color, ii+1, get_title(issue))

    _footer(canvas, week_date.strftime("%b %d, %Y").upper(), show_legend=True)
    return _save(canvas, "slide_02_top10")


# ─────────────────────────────────────────────────────────
# SLIDE 3 — PICKS
# ─────────────────────────────────────────────────────────
def build_picks_slide(picks: list, week_date: date,
                      get_title, get_cover_url, get_publisher) -> Path:
    canvas = _base()
    header_bottom = _header(canvas, "WATCHTOWER'S PICKS OF THE WEEK")
    draw = ImageDraw.Draw(canvas)

    pad = 10
    gt = header_bottom + 14
    gb = H - 78
    n = len(picks)

    if n == 0:
        mf = _font("bold", 72)
        draw.text((W//2, H//2), "NO PICKS THIS WEEK",
                  font=mf, fill=GRAY_DIM+(180,), anchor="mm")
    elif n == 1:
        cw = int(W*0.6)
        x1 = (W-cw)//2
        color = _pub_color(get_publisher(picks[0]))
        _place_cover(canvas, get_cover_url(picks[0]),
                     (x1, gt, x1+cw, gb), color, 1, get_title(picks[0]))
    else:
        cols = 2
        rows = (n+1)//2
        cw = (W-pad*(cols+1))//cols
        ch = (gb-gt-pad*(rows-1))//rows
        for idx, issue in enumerate(picks):
            col = idx%cols
            row = idx//cols
            x1 = pad+col*(cw+pad)
            y1 = gt+row*(ch+pad)
            if n%2==1 and idx==n-1:
                x1 = (W-cw)//2
            color = _pub_color(get_publisher(issue))
            _place_cover(canvas, get_cover_url(issue),
                         (x1, y1, x1+cw, y1+ch),
                         color, idx+1, get_title(issue))

    _footer(canvas, week_date.strftime("%b %d, %Y").upper(), show_legend=False)
    return _save(canvas, "slide_03_picks")


# ─────────────────────────────────────────────────────────
# SLIDE 4 — COLLECTOR'S CORNER
# ─────────────────────────────────────────────────────────
def build_collectors_slide(items: list, week_date: date) -> Path:
    canvas = _base()
    header_bottom = _header(canvas, "COLLECTOR'S CORNER")

    draw = ImageDraw.Draw(canvas)
    sf = _font("small", 30)
    draw.text((W//2, header_bottom+22),
              "KEY ISSUES & RARE VARIANTS THIS WEEK",
              font=sf, fill=ORANGE+(140,), anchor="mm")

    pad = 14
    gt = header_bottom + 50
    gb = H - 78
    items = items[:4]
    n = len(items)

    if n == 0:
        mf = _font("bold", 60)
        draw.text((W//2, H//2), "NOTHING THIS WEEK",
                  font=mf, fill=GRAY_DIM+(180,), anchor="mm")
    else:
        cols = min(n, 2)
        rows = (n+cols-1)//cols
        cw = (W-pad*(cols+1))//cols
        ch = (gb-gt-pad*(rows-1))//rows

        for idx, item in enumerate(items):
            col = idx%cols
            row = idx//cols
            x1 = pad+col*(cw+pad)
            y1 = gt+row*(ch+pad)

            if n%2==1 and idx==n-1:
                x1 = (W-cw)//2

            reason = item.get("reason","")
            if any(kw in reason for kw in ["RATIO","FOIL","VIRGIN","VARIANT","SKETCH"]):
                border_color = GOLD
            elif reason in ("#1 ISSUE","FIRST APPEARANCE","FACSIMILE"):
                border_color = (0, 200, 100)
            else:
                border_color = ORANGE

            box = (x1, y1, x1+cw, y1+ch)
            _place_cover(canvas, item.get("cover_url"),
                         box, border_color, 0, item.get("title",""))

            # Reason pill overlaid inside bottom of cover
            _overlay_pill(canvas, box, reason, border_color)

    _footer(canvas, week_date.strftime("%b %d, %Y").upper(), show_legend=False)
    return _save(canvas, "slide_04_collectors")