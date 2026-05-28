# TheWatchtower_ — Social Media Content Engine

![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white)
![Pillow](https://img.shields.io/badge/Pillow-Image%20Generation-green)
![Groq](https://img.shields.io/badge/Groq-LLaMA%203.3--70B-orange)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

An automated Instagram content pipeline for [@the.watch\_tower](https://instagram.com/the.watch_tower) — a pop culture account covering comics, movies, TV, and books. Generates production-quality carousel slides, AI-assisted captions, story polls, and a weekly content plan. Built as a portfolio signal for production LLM and automation work.

---

## What It Does

| Command | Description | Cadence |
|---|---|---|
| `python -m app run` | Weekly New Comic Book Day carousel | Every Wednesday |
| `python -m app movies` | Monthly top 10 anticipated movies + highest grossing | 1st of month |
| `python -m app tv` | Monthly top 10 TV premieres + most popular last month | 1st of month |
| `python -m app review` | Book review carousel with AI-assisted caption | As read |
| `python -m app poll` | Daily story poll background for Instagram | Daily |
| `python -m app ideate` | Weekly content plan — 7 polls + schedule | Every Monday |
| `python -m app initdb` | Initialize SQLite database | One-time |

---

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI Entry Point                          │
│                      python -m app <cmd>                        │
└────────────┬───────────────────┬──────────────┬────────────────┘
             │                   │              │
    ┌────────▼──────┐   ┌────────▼──────┐  ┌───▼──────────────┐
    │  Data Ingest  │   │ Slide Builder │  │  Caption Engine  │
    │               │   │               │  │                  │
    │ Metron API    │   │ Pillow/PIL    │  │ Groq LLaMA 3.3   │
    │ TMDB API      │   │ BebasNeue     │  │ 70B              │
    │ Open Library  │   │ Oswald fonts  │  │                  │
    └────────┬──────┘   └────────┬──────┘  └───┬──────────────┘
             │                   │              │
             └───────────────────▼──────────────┘
                          ┌──────────────┐
                          │   Output     │
                          │              │
                          │ JPG Slides   │
                          │ Caption text │
                          │ Poll slides  │
                          │ Weekly plan  │
                          └──────┬───────┘
                                 │
                    ┌────────────▼────────────┐
                    │    Cloudinary CDN       │
                    │  (image hosting for     │
                    │   Instagram API)        │
                    └─────────────────────────┘
```

---

## Content Modules

### 📚 Weekly Comic Book Day (New Comic Book Day)
4-slide carousel generated every Wednesday from live Metron API data.

| Slide | Content |
|---|---|
| 1 | Cover — Watchtower station illustration, date |
| 2 | Top 10 most anticipated releases — color-coded by publisher |
| 3 | Watchtower's Picks — your selected issues |
| 4 | Collector's Corner — #1 issues, ratio variants, key releases |

Publisher color coding: DC (blue), Marvel (red), Image (orange), Dark Horse (green), IDW (yellow)

### 🎬 Monthly Movies
4-slide carousel on the 1st of each month from TMDB.

| Slide | Content |
|---|---|
| 1 | Cover |
| 2 | Top 10 most anticipated by TMDB popularity score |
| 3 | Your picks |
| 4 | Top 3 highest grossing last month with revenue |

### 📺 Monthly TV
4-slide carousel on the 1st of each month from TMDB.

| Slide | Content |
|---|---|
| 1 | Cover |
| 2 | Top 10 shows premiering this month |
| 3 | Your picks |
| 4 | Most popular last month — TMDB rating + vote count |

### 📖 Book Review
4-slide carousel posted as read. AI-assisted review drafting.

| Slide | Content |
|---|---|
| 1 | Book cover art + "BOOK REVIEW" title |
| 2 | Cover, rating (0-5 in 0.5 steps), AI-drafted review |
| 3 | 2026 Reading List — all books read with ratings |
| 4 | Next read |

### 🗳️ Daily Story Poll
Instagram Story background (1080×1920). Add Instagram's native poll sticker on top.

### 📅 Weekly Ideation
Run every Monday. Generates:
- Wednesday comic preview from Metron
- 7 daily poll questions in one batch
- 1st-of-month reminders for movies + TV
- Saves `weekly_plan.txt` and all 7 poll slides

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.13 |
| Image generation | Pillow (PIL) |
| Comic data | Metron API |
| Movie/TV data | TMDB API |
| Book covers | Open Library API |
| AI captions | Groq — LLaMA 3.3-70B |
| Image hosting | Cloudinary |
| Database | SQLite |
| CLI | Click + Rich |
| Fonts | Bebas Neue, Oswald |

---

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/connorholliday5/instagram-content-pipeline
cd instagram-content-pipeline
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Add fonts
Download and place in `assets/fonts/`:
- [Bebas Neue](https://fonts.google.com/specimen/Bebas+Neue) → `BebasNeue-Regular.ttf`
- [Oswald](https://fonts.google.com/specimen/Oswald) → `Oswald-Bold.ttf`, `Oswald-Regular.ttf`

### 4. Configure environment
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```

### 5. Initialize database
```bash
python -m app initdb
python seed_books.py  # optional — seed past reads
```

### 6. Run
```bash
python -m app run        # dry run
python -m app run --live # post live
```

---

## Environment Variables

See `.env.example` for all required keys.

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | [Groq Console](https://console.groq.com) |
| `TMDB_API_KEY` | [TMDB API](https://www.themoviedb.org/settings/api) |
| `METRON_USERNAME` | [Metron](https://metron.cloud) account |
| `METRON_PASSWORD` | Metron password |
| `CLOUDINARY_CLOUD_NAME` | [Cloudinary](https://cloudinary.com) |
| `CLOUDINARY_API_KEY` | Cloudinary API key |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret |
| `INSTAGRAM_BUSINESS_ACCOUNT_ID` | Instagram Business account ID |
| `META_PAGE_ACCESS_TOKEN` | Meta Graph API token |
| `META_APP_ID` | Meta App ID |
| `META_APP_SECRET` | Meta App secret |

---

## Project Structure

```
WatchTower/
├── app/
│   └── __main__.py          # Entry point
├── assets/
│   └── fonts/               # Bebas Neue, Oswald
├── output/                  # Generated slides
│   └── weekly_plans/        # Saved content plans + poll JSON
├── src/
│   ├── caption/
│   │   └── groq_caption.py  # Groq LLaMA caption generation
│   ├── content/
│   │   └── ideate.py        # Weekly content ideation engine
│   ├── create/
│   │   └── review.py        # Book review CLI
│   ├── db/
│   │   └── models.py        # SQLite models
│   ├── generate/
│   │   ├── carousel.py      # Comics slide builder
│   │   ├── movies_carousel.py
│   │   ├── tv_carousel.py
│   │   ├── book_review.py
│   │   └── poll.py          # Story poll builder
│   ├── ingest/
│   │   ├── metron.py        # Metron comic data
│   │   └── tmdb.py          # TMDB movie/TV data
│   ├── post/
│   │   ├── carousel_post.py # Instagram posting
│   │   └── upload.py        # Cloudinary upload
│   └── cli.py               # Click CLI commands
├── .env.example
├── requirements.txt
├── seed_books.py
└── watchtower.db
```

---

## Roadmap

- [x] Weekly comic carousel (New Comic Book Day)
- [x] Monthly movies carousel
- [x] Monthly TV carousel
- [x] Book review carousel with AI drafting
- [x] Daily story poll generator
- [x] Weekly content ideation engine
- [ ] Instagram posting automation
- [ ] Engagement bot (pending Meta app review)
- [ ] DC Lore Model — fine-tuned LLaMA 3 for DM Q&A

---

## Portfolio Notes

This project demonstrates:
- **Production LLM integration** — Groq LLaMA 3.3-70B for caption generation and poll question generation with structured prompting
- **Multi-API orchestration** — Metron, TMDB, Open Library, Cloudinary, Meta Graph API
- **Programmatic image generation** — Pillow-based slide builder with custom typography, publisher color coding, cover art fetching
- **CLI tooling** — Click + Rich for interactive terminal workflows
- **SQLite data persistence** — reading list tracking across sessions
- **Modular architecture** — each content pillar is independently runnable

---

*Built by [@connorholliday5](https://github.com/connorholliday5)*