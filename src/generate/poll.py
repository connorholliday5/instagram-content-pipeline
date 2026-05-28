import os
import requests
import random
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from datetime import date
from typing import Optional

OUTPUT_DIR = Path("output")
SIZE = (1080, 1920)  # Instagram Story dimensions
W, H = SIZE

BG       = (3, 3, 10)
WHITE    = (255, 255, 255)
GRAY_DIM = (75, 75, 90)
GRAY     = (170, 170, 170)
ORANGE   = (255, 140, 0)

# Poll colors — Instagram-style
POLL_A   = (255, 220, 50)   # gold/yellow
POLL_B   = (100, 180, 255)  # blue

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

CATEGORIES = [
    "DC Comics characters or storylines",
    "Marvel Comics characters or storylines",
    "Comic books general",
    "Fantasy books like Game of Thrones or Red Rising",
    "Sci-fi books",
    "Superhero movies",
    "Action or thriller movies",
    "Blockbuster movies",
    "Streaming TV shows",
    "Pop culture general",
    "Would you rather — nerd culture",
    "Hot takes — comics, movies, or TV",
    "Ranking debate — best of a franchise",
    "Overrated or underrated — anything",
]


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


def _stars(canvas: Image.Image):
    rng = random.Random(date.today().toordinal())
    draw = ImageDraw.Draw(canvas)
    for _ in range(200):
        x = rng.randint(0, W-1)
        y = rng.randint(0, H-1)
        r = rng.choice([1,1,1,2])
        a = rng.randint(60, 180)
        draw.ellipse([(x-r,y-r),(x+r,y+r)],
                     fill=(200+rng.randint(0,55), 210+rng.randint(0,45), 255, a))


def _save(canvas: Image.Image, name: str) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"{name}.jpg"
    canvas.convert("RGB").save(path, "JPEG", quality=95)
    return path


def generate_poll_question() -> dict:
    """Generate a poll question using Groq."""
    category = random.choice(CATEGORIES)

    system = """You generate Instagram Story poll questions for @the.watch_tower — a pop culture account covering comics, movies, TV, and books.

Rules:
- Question must be engaging, debatable, and short (max 12 words)
- Option A and Option B must be genuinely contested choices — no obvious answers
- Keep options short — max 4 words each
- No spoilers for recent releases
- Vary the format: comparisons, would-you-rather, hot takes, rankings
- Return ONLY valid JSON, no extra text:
{"question": "...", "option_a": "...", "option_b": "..."}"""

    user = f"Generate a poll about: {category}"

    try:
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}",
                     "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "max_tokens": 150,
                "temperature": 1.0,
            },
            timeout=15
        )
        resp.raise_for_status()
        import json
        raw = resp.json()["choices"][0]["message"]["content"].strip()
        # Strip markdown if present
        raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        return {
            "question": data.get("question", "Who wins?"),
            "option_a": data.get("option_a", "Option A"),
            "option_b": data.get("option_b", "Option B"),
            "category": category,
        }
    except Exception as e:
        return {
            "question": "Batman or Superman — who takes the W?",
            "option_a": "Batman",
            "option_b": "Superman",
            "category": "DC Comics",
        }


def _draw_rounded_rect(draw: ImageDraw.ImageDraw, box: tuple,
                       radius: int, fill: tuple, outline: tuple = None,
                       outline_width: int = 0):
    x1, y1, x2, y2 = box
    draw.rectangle([(x1+radius, y1), (x2-radius, y2)], fill=fill)
    draw.rectangle([(x1, y1+radius), (x2, y2-radius)], fill=fill)
    draw.ellipse([(x1, y1), (x1+radius*2, y1+radius*2)], fill=fill)
    draw.ellipse([(x2-radius*2, y1), (x2, y1+radius*2)], fill=fill)
    draw.ellipse([(x1, y2-radius*2), (x1+radius*2, y2)], fill=fill)
    draw.ellipse([(x2-radius*2, y2-radius*2), (x2, y2)], fill=fill)
    if outline and outline_width:
        draw.arc([(x1, y1), (x1+radius*2, y1+radius*2)], 180, 270, fill=outline, width=outline_width)
        draw.arc([(x2-radius*2, y1), (x2, y1+radius*2)], 270, 360, fill=outline, width=outline_width)
        draw.arc([(x1, y2-radius*2), (x1+radius*2, y2)], 90, 180, fill=outline, width=outline_width)
        draw.arc([(x2-radius*2, y2-radius*2), (x2, y2)], 0, 90, fill=outline, width=outline_width)
        draw.line([(x1+radius, y1), (x2-radius, y1)], fill=outline, width=outline_width)
        draw.line([(x1+radius, y2), (x2-radius, y2)], fill=outline, width=outline_width)
        draw.line([(x1, y1+radius), (x1, y2-radius)], fill=outline, width=outline_width)
        draw.line([(x2, y1+radius), (x2, y2-radius)], fill=outline, width=outline_width)


def build_poll_story(poll: dict, poll_date: date) -> Path:
    """
    Build an Instagram Story poll background.
    No fake buttons — question only. Add Instagram poll sticker on top in the app.
    """
    canvas = Image.new("RGBA", SIZE, BG+(255,))
    _stars(canvas)

    # Subtle vignette
    for region, color in [
        ([(0,0),(W,500)], (0,0,15,100)),
        ([(0,H-500),(W,H)], (0,0,10,140)),
    ]:
        ov = Image.new("RGBA", SIZE, (0,0,0,0))
        od = ImageDraw.Draw(ov)
        od.rectangle([region[0], region[1]], fill=color)
        canvas.alpha_composite(ov)

    draw = ImageDraw.Draw(canvas)
    pad = 70
    cx = W // 2

    # ── Brand header ──
    brand_f = _font("small", 46)
    draw.text((cx, 110), "THE WATCHTOWER",
              font=brand_f, fill=ORANGE+(200,), anchor="mm")
    draw.rectangle([(pad, 145),(W-pad, 148)], fill=ORANGE+(80,))

    # ── Category pill ──
    cat = poll.get("category","").upper()[:28]
    cat_f = _font("small", 34)
    bbox = draw.textbbox((0,0), cat, font=cat_f)
    tw = bbox[2]-bbox[0]
    pill_x1 = cx - tw//2 - 24
    pill_x2 = cx + tw//2 + 24
    ov = Image.new("RGBA", SIZE, (0,0,0,0))
    od = ImageDraw.Draw(ov)
    od.rectangle([(pill_x1, 168),(pill_x2, 210)], fill=ORANGE+(35,))
    canvas.alpha_composite(ov)
    draw = ImageDraw.Draw(canvas)
    draw.text((cx, 189), cat, font=cat_f, fill=ORANGE+(210,), anchor="mm")

    # ── Question — big, centered ──
    question = poll["question"]
    q_font = _font("display", 110)

    words = question.split()
    lines, line = [], ""
    max_w = W - pad*2
    for w in words:
        test = (line+" "+w).strip()
        bbox = draw.textbbox((0,0), test, font=q_font)
        if bbox[2]-bbox[0] > max_w:
            if line: lines.append(line)
            line = w
        else:
            line = test
    if line: lines.append(line)

    q_lh = 124
    q_total = len(lines)*q_lh
    q_top = H//2 - q_total//2 - 60

    for li, ln in enumerate(lines):
        draw.text((cx, q_top + li*q_lh), ln,
                  font=q_font, fill=WHITE, anchor="mm")

    # ── Options hint — small text below question ──
    hint_y = q_top + q_total + 48
    hint_f = _font("bold", 52)

    # Option A
    oa = poll["option_a"].upper()
    ob = poll["option_b"].upper()
    draw.text((cx - 30, hint_y), oa,
              font=hint_f, fill=POLL_A+(220,), anchor="rm")
    div_f = _font("regular", 52)
    draw.text((cx, hint_y), "VS", font=div_f,
              fill=GRAY_DIM+(180,), anchor="mm")
    draw.text((cx + 30, hint_y), ob,
              font=hint_f, fill=POLL_B+(220,), anchor="lm")

    # ── "Add poll sticker above" reminder ──
    remind_f = _font("small", 30)
    draw.text((cx, hint_y+80), "ADD POLL STICKER IN INSTAGRAM",
              font=remind_f, fill=GRAY_DIM+(120,), anchor="mm")

    # ── Footer ──
    draw.rectangle([(pad, H-140),(W-pad, H-137)], fill=ORANGE+(60,))
    df = _font("display", 40)
    draw.text((cx, H-100), poll_date.strftime("%B %d, %Y").upper(),
              font=df, fill=GRAY_DIM+(180,), anchor="mm")
    hf = _font("small", 30)
    draw.text((cx, H-52), "@the.watch_tower",
              font=hf, fill=GRAY_DIM+(120,), anchor="mm")

    return _save(canvas, f"poll_{poll_date.strftime('%Y%m%d')}")