#!/usr/bin/env python3
"""
Weekly comic releases → Instagram-ready graphics.

Outputs (by default into ./insta_out):
  - week_cover.png (cover slide)
  - dc_01.png, dc_02.png, ...
  - marvel_01.png, marvel_02.png, ...
  - other_01.png, other_02.png, ...
  - weekly_releases.csv (reference CSV)

If you prefer single images named exactly:
  - dc_this_week.png
  - marvel_this_week.png
  - other_publishers_this_week.png
use --single-page-only to export one page per bucket (first page only) with those names.

Data source: Comic Vine API (non‑commercial; respect rate limits).

Usage examples:
  # current week (Wed→Tue window in America/New_York)
  python weekly_comics_instagram.py

  # force a particular date (any day in the target week)
  python weekly_comics_instagram.py --week 2025-10-02

  # no cover slide, and export first page only with legacy names
  python weekly_comics_instagram.py --no-cover --single-page-only
"""
from __future__ import annotations

import os
import sys
import time
import math
import argparse
import textwrap
from pathlib import Path
from datetime import date, datetime, timedelta

import requests
import pandas as pd
from dateutil.tz import gettz
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ---------- Configuration ----------
API_BASE = "https://www.comicvine.com/api"
USER_AGENT = "weekly-comics-script/1.1 (non-commercial)"
TZ = gettz("America/New_York")
COMIC_WEEK_START_WEEKDAY = 2  # 0=Mon, 1=Tue, 2=Wed
MAX_PER_PAGE = 100            # ComicVine per-page hard limit
SLEEP_BETWEEN_CALLS = 0.35    # be gentle with API

# Canvas size for Instagram portrait
IG_W, IG_H = 1080, 1350

# ---------- Helpers ----------

def load_api_key() -> str:
    # Support dotenv without hard dependency
    api_key = os.environ.get("COMICVINE_API_KEY")
    if not api_key:
        try:
            from dotenv import load_dotenv  # type: ignore
            load_dotenv()
            api_key = os.environ.get("COMICVINE_API_KEY")
        except Exception:
            api_key = os.environ.get("COMICVINE_API_KEY")
    if not api_key:
        sys.exit("⚠️ Could not find COMICVINE_API_KEY in environment or .env file.")
    return api_key


def session_with_retries() -> requests.Session:
    sess = requests.Session()
    sess.headers.update({"User-Agent": USER_AGENT})
    try:
        # Optional retries if urllib3 is available
        from urllib3.util.retry import Retry  # type: ignore
        from requests.adapters import HTTPAdapter
        retry = Retry(total=4, backoff_factor=0.5, status_forcelist=(429, 500, 502, 503, 504))
        sess.mount("https://", HTTPAdapter(max_retries=retry))
    except Exception:
        pass
    return sess


def http_get(sess: requests.Session, api_key: str, path: str, params: dict) -> dict:
    base_params = {"api_key": api_key, "format": "json"}
    base_params.update(params)
    url = f"{API_BASE}{path}"
    r = sess.get(url, params=base_params, timeout=30)
    r.raise_for_status()
    data = r.json()
    if data.get("status_code") != 1:
        raise RuntimeError(f"ComicVine API error: {data.get('error')}")
    return data


def current_comic_week(today: date | None = None) -> tuple[date, date]:
    """Return start/end dates (inclusive) for the current comic week (Wed→Tue)."""
    base = today or datetime.now(TZ).date()
    days_since_wed = (base.weekday() - COMIC_WEEK_START_WEEKDAY) % 7
    week_start = base - timedelta(days=days_since_wed)
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def daterange(d0: date, d1: date):
    d = d0
    while d <= d1:
        yield d
        d += timedelta(days=1)


def fetch_issues_for_day(sess: requests.Session, api_key: str, day: date) -> list[dict]:
    """
    Query per-day store_date for reliability. We only request minimal fields.
    """
    all_rows: list[dict] = []
    offset = 0
    while True:
        params = {
            "filter": f"store_date:{day.isoformat()}",
            "field_list": "id,name,issue_number,store_date,volume,site_detail_url",
            "sort": "name:asc",
            "limit": MAX_PER_PAGE,
            "offset": offset,
        }
        data = http_get(sess, api_key, "/issues/", params)
        results = data.get("results", [])
        for it in results:
            vol = it.get("volume") or {}
            all_rows.append({
                "issue_id": it.get("id"),
                "title": (it.get("name") or "").strip(),
                "issue_number": str(it.get("issue_number")) if it.get("issue_number") is not None else "",
                "store_date": it.get("store_date"),
                "volume_id": vol.get("id"),
                "series": vol.get("name"),
                "url": it.get("site_detail_url"),
            })
        total = data.get("number_of_total_results", 0)
        offset += MAX_PER_PAGE
        if offset >= total:
            break
        time.sleep(SLEEP_BETWEEN_CALLS)
    return all_rows


def fetch_publishers_for_volumes(sess: requests.Session, api_key: str, volume_ids: list[int | None]) -> dict[int, str]:
    """Lookup publisher names for volume IDs in small batches."""
    publishers: dict[int, str] = {}
    ids = [int(vid) for vid in volume_ids if vid]
    if not ids:
        return publishers

    batch_size = 50
    for i in range(0, len(ids), batch_size):
        batch = ids[i:i + batch_size]
        # ComicVine supports id pipe filtering; pagination is usually not needed but keep it safe.
        offset = 0
        while True:
            params = {
                "filter": "id:" + "|".join(str(x) for x in batch),
                "field_list": "id,publisher",
                "limit": MAX_PER_PAGE,
                "offset": offset,
            }
            data = http_get(sess, api_key, "/volumes/", params)
            for vol in data.get("results", []):
                vid = vol.get("id")
                pub = (vol.get("publisher") or {}).get("name")
                if vid and pub and vid not in publishers:
                    publishers[vid] = pub
            total = data.get("number_of_total_results", 0)
            offset += MAX_PER_PAGE
            if offset >= total:
                break
            time.sleep(SLEEP_BETWEEN_CALLS)
        time.sleep(SLEEP_BETWEEN_CALLS)
    return publishers


def make_lines(df: pd.DataFrame) -> list[str]:
    """Build lines like: 'Series #Issue — Title'"""
    lines: list[str] = []
    if df.empty:
        return lines
    for _, row in df.sort_values(["series", "issue_number", "title"], na_position="last").iterrows():
        series = row.get("series") or ""
        num = row.get("issue_number") or ""
        title = row.get("title") or ""
        bit = f"{series} #{num}".strip()
        if title:
            bit = f"{bit} — {title}"
        lines.append(bit.strip(" —"))
    return lines

# ---------- Typography & drawing ----------

def _load_font(path_candidates, size, fallback="arial.ttf"):
    for p in path_candidates:
        try:
            if Path(p).exists():
                return ImageFont.truetype(p, size=size)
        except Exception:
            pass
    try:
        return ImageFont.truetype(fallback, size=size)
    except Exception:
        return ImageFont.load_default()

TITLE_FONT = _load_font([
    "C:/Windows/Fonts/SegoeUI-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
], 70)
SUB_FONT = _load_font([
    "C:/Windows/Fonts/SegoeUI-Semibold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
], 38)
BODY_FONT = _load_font([
    "C:/Windows/Fonts/SegoeUI.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
], 34)
SMALL_FONT = _load_font([
    "C:/Windows/Fonts/SegoeUI.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
], 26)


def _nice_bg(brand: str = "neutral") -> Image.Image:
    """Subtle gradient background with soft vignette; brand ∈ {dc, marvel, other, cover, neutral}."""
    if brand == "dc":
        start, end = (22, 64, 129), (10, 30, 64)
    elif brand == "marvel":
        start, end = (170, 20, 32), (90, 12, 22)
    elif brand == "other":
        start, end = (40, 40, 40), (18, 18, 18)
    elif brand == "cover":
        start, end = (60, 12, 90), (16, 6, 32)
    else:
        start, end = (30, 30, 30), (10, 10, 10)

    img = Image.new("RGB", (IG_W, IG_H), start)
    draw = ImageDraw.Draw(img)
    for y in range(IG_H):
        t = y / (IG_H - 1)
        r = int(start[0] * (1 - t) + end[0] * t)
        g = int(start[1] * (1 - t) + end[1] * t)
        b = int(start[2] * (1 - t) + end[2] * t)
        draw.line([(0, y), (IG_W, y)], fill=(r, g, b))
    vignette = Image.new("L", (IG_W, IG_H), 0)
    gdraw = ImageDraw.Draw(vignette)
    gdraw.ellipse([(-200, -150), (IG_W + 200, IG_H + 250)], fill=255)
    vignette = vignette.filter(ImageFilter.GaussianBlur(160))
    img = Image.composite(img, Image.new("RGB", (IG_W, IG_H), (0, 0, 0)), vignette.point(lambda v: 220 - v // 2))
    return img


def _draw_header(img: Image.Image, title: str, subtitle: str | None) -> int:
    draw = ImageDraw.Draw(img)
    pad = 64
    draw.text((pad, 54), title, fill=(255, 255, 255), font=TITLE_FONT)
    if subtitle:
        w, h, *_ = draw.textbbox((0, 0), subtitle, font=SUB_FONT)
        pill_w = w + 40
        pill_h = h + 20
        pill = Image.new("RGBA", (pill_w, pill_h), (255, 255, 255, 28))
        pill = pill.filter(ImageFilter.GaussianBlur(0.5))
        r = 18
        pill_draw = ImageDraw.Draw(pill)
        pill_draw.rounded_rectangle([0, 0, pill_w - 1, pill_h - 1], r, fill=(255, 255, 255, 48))
        ret_y = 54 + TITLE_FONT.size + 18
        img.paste(pill, (pad, ret_y), pill)
        draw.text((pad + 20, ret_y + 10), subtitle, fill=(245, 245, 245), font=SUB_FONT)
        return ret_y + pill_h + 20
    return 54 + TITLE_FONT.size + 24


def _wrap_issue_lines(lines: list[str], max_chars: int = 40) -> list[str]:
    wrapped: list[str] = []
    for ln in lines:
        ln = ln.replace("—", "-")
        ws = textwrap.wrap(ln, width=max_chars)
        wrapped.extend(ws if ws else [""])
    return wrapped


def _paginate_columns(lines: list[str], cols: int, row_height: int, top_y: int, bottom_margin: int = 80):
    """Return (pages, rows_per_col). Each page is a list[ column_lines ]."""
    usable_h = IG_H - top_y - bottom_margin
    rows_per_col = max(1, usable_h // row_height)
    lines_per_page = rows_per_col * cols

    pages = []
    for i in range(0, len(lines), lines_per_page):
        chunk = lines[i : i + lines_per_page]
        cols_data = []
        for c in range(cols):
            start = c * rows_per_col
            end = start + rows_per_col
            cols_data.append(chunk[start:end])
        pages.append(cols_data)
    if not pages:
        pages = [[[] for _ in range(cols)]]
    return pages, rows_per_col


def _draw_list(img: Image.Image, pages_cols: list[list[str]], start_y: int, cols: int):
    draw = ImageDraw.Draw(img)
    pad_x = 64
    gutter = 48
    col_w = (IG_W - pad_x * 2 - gutter * (cols - 1)) // cols
    y_step = 46

    for col_idx, col_lines in enumerate(pages_cols):
        x = pad_x + col_idx * (col_w + gutter)
        y = start_y
        for ln in col_lines:
            draw.text((x, y), f"• {ln}", fill=(240, 240, 240), font=BODY_FONT)
            y += y_step


def render_instagram_pages(
    lines: list[str],
    week_label: str,
    brand: str,
    title: str,
    prefix_filename: str,
    outdir: str,
    include_cover: bool = False,
    single_page_only: bool = False,
):
    Path(outdir).mkdir(parents=True, exist_ok=True)
    wrapped = _wrap_issue_lines(lines, max_chars=40)

    # Measure header to compute pagination
    dummy = _nice_bg(brand)
    top_y = _draw_header(dummy, title, week_label) + 24
    pages_cols, _ = _paginate_columns(wrapped, cols=2, row_height=46, top_y=top_y)

    saved: list[str] = []

    # Optional cover slide
    if include_cover:
        cover = _nice_bg("cover")
        _draw_header(cover, "This Week in Comics", week_label)
        d0 = ImageDraw.Draw(cover)
        # Big three tags
        tags = ["DC", "MARVEL", "EVERYTHING ELSE"]
        y = IG_H // 2 - 40
        for t in tags:
            tw, th, *_ = d0.textbbox((0, 0), t, font=TITLE_FONT)
            chip = Image.new("RGBA", (tw + 60, th + 36), (255, 255, 255, 22))
            chip_draw = ImageDraw.Draw(chip)
            chip_draw.rounded_rectangle([0, 0, chip.size[0] - 1, chip.size[1] - 1], 28, fill=(255, 255, 255, 36))
            x = (IG_W - chip.size[0]) // 2
            cover.paste(chip, (x, y), chip)
            d0.text((x + 30, y + 18), t, fill=(245, 245, 245), font=TITLE_FONT)
            y += chip.size[1] + 32
        d0.text((64, IG_H - 80), "© Non-commercial • Data: Comic Vine", fill=(200, 200, 200), font=SMALL_FONT)
        fp = Path(outdir) / "week_cover.png"
        cover.save(fp)
        saved.append(str(fp))

    # Content pages
    num_pages = 1 if single_page_only else len(pages_cols)
    for idx, cols in enumerate(pages_cols[:num_pages], start=1):
        img = _nice_bg(brand)
        body_top = _draw_header(img, title, week_label) + 24
        _draw_list(img, cols, start_y=body_top, cols=len(cols))
        d = ImageDraw.Draw(img)
        d.text((64, IG_H - 80), "© Non-commercial • Data: Comic Vine", fill=(200, 200, 200), font=SMALL_FONT)
        name = f"{prefix_filename}_{idx:02d}.png"
        fp = Path(outdir) / name
        img.save(fp)
        saved.append(str(fp))

    return saved


# ---------- Main flow ----------

def run(for_date: date | None, no_cover: bool, single_page_only: bool, outdir: str):
    api_key = load_api_key()
    sess = session_with_retries()

    week_start, week_end = current_comic_week(for_date)
    week_label = f"{week_start.strftime('%b %d, %Y')} – {week_end.strftime('%b %d, %Y')}"
    print(f"Comic week: {week_start} → {week_end} (Wed→Tue window)")

    # 1) Gather all issues per day in the window
    rows: list[dict] = []
    for d in daterange(week_start, week_end):
        day_rows = fetch_issues_for_day(sess, api_key, d)
        if day_rows:
            rows.extend(day_rows)
        time.sleep(SLEEP_BETWEEN_CALLS)

    if not rows:
        print("No issues found for this week.")
        return

    df = pd.DataFrame(rows)

    # 2) Fill publishers by looking up the volumes in batches
    pubs = fetch_publishers_for_volumes(sess, api_key, df["volume_id"].dropna().unique().tolist())
    df["publisher"] = df["volume_id"].map(pubs).fillna("Unknown")

    # 3) Split into DC, Marvel, Other
    lower_pub = df["publisher"].astype(str).str.lower()
    dc_df = df[lower_pub.str.contains(r"\bdc\b|dc comics")]
    marvel_df = df[lower_pub.str.contains(r"\bmarvel\b")]
    other_df = df[~df.index.isin(dc_df.index.union(marvel_df.index))]

    Path(outdir).mkdir(parents=True, exist_ok=True)
    saved_files: list[str] = []

    # Optional overall cover first
    if not no_cover:
        saved_files += render_instagram_pages(
            [], week_label,
            brand="cover",
            title="This Week in Comics",
            prefix_filename="week",
            outdir=outdir,
            include_cover=True,
            single_page_only=True,
        )

    # DC
    saved_files += render_instagram_pages(
        make_lines(dc_df), week_label,
        brand="dc",
        title="DC • New Releases",
        prefix_filename="dc",
        outdir=outdir,
        include_cover=False,
        single_page_only=single_page_only,
    )

    # Marvel
    saved_files += render_instagram_pages(
        make_lines(marvel_df), week_label,
        brand="marvel",
        title="Marvel • New Releases",
        prefix_filename="marvel",
        outdir=outdir,
        include_cover=False,
        single_page_only=single_page_only,
    )

    # Everything Else
    saved_files += render_instagram_pages(
        make_lines(other_df), week_label,
        brand="other",
        title="Everything Else",
        prefix_filename="other",
        outdir=outdir,
        include_cover=False,
        single_page_only=single_page_only,
    )

    # 4) CSV for reference
    csv_path = Path(outdir) / "weekly_releases.csv"
    df.sort_values(["publisher", "series", "issue_number"], na_position="last").to_csv(csv_path, index=False)

    # Legacy single-file names if requested
    if single_page_only:
        # Copy first pages to legacy names for convenience
        mapping = {
            "dc_01.png": "dc_this_week.png",
            "marvel_01.png": "marvel_this_week.png",
            "other_01.png": "other_publishers_this_week.png",
        }
        for src, dest in mapping.items():
            s = Path(outdir) / src
            if s.exists():
                (Path(outdir) / dest).write_bytes(s.read_bytes())

    print("Saved files:")
    for fp in saved_files:
        print(" -", fp)
    print("Also saved:", csv_path)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Render weekly comic releases to Instagram-ready images.")
    p.add_argument("--week", type=str, default=None, help="Any date YYYY-MM-DD within the target week. Defaults to today.")
    p.add_argument("--no-cover", action="store_true", help="Do not render a cover slide.")
    p.add_argument("--single-page-only", action="store_true", help="Export only the first page for each bucket and create legacy names.")
    p.add_argument("--outdir", type=str, default="insta_out", help="Output directory.")
    args = p.parse_args(argv)

    for_date = None
    if args.week:
        try:
            for_date = datetime.strptime(args.week, "%Y-%m-%d").date()
        except ValueError:
            sys.exit("--week must be in YYYY-MM-DD format")
    return for_date, args.no_cover, args.single_page_only, args.outdir


if __name__ == "__main__":
    for_date, no_cover, single_page_only, outdir = parse_args()
    run(for_date, no_cover, single_page_only, outdir)


# add to your project: post_instagram.py
import os, time, requests

GRAPH = "https://graph.facebook.com/v21.0"  # or latest
IG_USER_ID = os.environ["IG_USER_ID"]
IG_TOKEN   = os.environ["IG_ACCESS_TOKEN"]

def ig_create_image_container(image_url, caption=""):
    r = requests.post(
        f"{GRAPH}/{IG_USER_ID}/media",
        params={"access_token": IG_TOKEN},
        data={"image_url": image_url, "caption": caption}
    )
    r.raise_for_status()
    return r.json()["id"]  # creation_id

def ig_publish(creation_id):
    r = requests.post(
        f"{GRAPH}/{IG_USER_ID}/media_publish",
        params={"access_token": IG_TOKEN},
        data={"creation_id": creation_id}
    )
    r.raise_for_status()
    return r.json()

def post_single(image_url, caption):
    cid = ig_create_image_container(image_url, caption)
    return ig_publish(cid)
