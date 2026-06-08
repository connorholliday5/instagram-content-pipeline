# TheWatchtower_ — Social Media Content Engine

![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white)
![Pillow](https://img.shields.io/badge/Pillow-Image%20Generation-green)
![Groq](https://img.shields.io/badge/Groq-LLaMA%203.3--70B-orange)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

An automated Instagram content pipeline for [@the.watch\_tower](https://instagram.com/the.watch_tower) — a pop culture account covering comics, movies, TV, and books. Generates production-quality carousel slides, AI-assisted captions, story polls, and a weekly content plan. Built as a portfolio signal for production LLM and automation work.

---

## iPhone App

Every command below can be driven from an iPhone instead of a terminal. The app pairs with a local FastAPI server, streams pipeline output, lets you approve/edit/regenerate each step, and saves finished slides straight to Photos for posting.
iPhone (Expo Go) -- HTTP --> FastAPI (port 8001) -- subprocess --> python -m app stage <cmd>

| Folder | Component |
|---|---|
| `api/` | FastAPI server wrapping each command as a state machine |
| `mobile/` | React Native (Expo SDK 54) app |
| `src/content/*_stages.py` | Pure stage functions extracted from each CLI command |

The CLI is unchanged. The app is purely additive.

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
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                        CLI Entry Point                          â”‚
â”‚                      python -m app <cmd>                        â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
             â”‚                   â”‚              â”‚
    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
    â”‚  Data Ingest  â”‚   â”‚ Slide Builder â”‚  â”‚  Caption Engine  â”‚
    â”‚               â”‚   â”‚               â”‚  â”‚                  â”‚
    â”‚ Metron API    â”‚   â”‚ Pillow/PIL    â”‚  â”‚ Groq LLaMA 3.3   â”‚
    â”‚ TMDB API      â”‚   â”‚ BebasNeue     â”‚  â”‚ 70B              â”‚
    â”‚ Open Library  â”‚   â”‚ Oswald fonts  â”‚  â”‚                  â”‚
    â””â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”˜   â””â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
             â”‚                   â”‚              â”‚
             â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                          â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                          â”‚   Output     â”‚
                          â”‚              â”‚
                          â”‚ JPG Slides   â”‚
                          â”‚ Caption text â”‚
                          â”‚ Poll slides  â”‚
                          â”‚ Weekly plan  â”‚
                          â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”˜
                                 â”‚
                    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                    â”‚    Cloudinary CDN       â”‚
                    â”‚  (image hosting for     â”‚
                    â”‚   Instagram API)        â”‚
                    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## Content Modules

### ðŸ“š Weekly Comic Book Day (New Comic Book Day)
4-slide carousel generated every Wednesday from live Metron API data.

| Slide | Content |
|---|---|
| 1 | Cover â€” Watchtower station illustration, date |
| 2 | Top 10 most anticipated releases â€” color-coded by publisher |
| 3 | Watchtower's Picks â€” your selected issues |
| 4 | Collector's Corner â€” #1 issues, ratio variants, key releases |

Publisher color coding: DC (blue), Marvel (red), Image (orange), Dark Horse (green), IDW (yellow)

### ðŸŽ¬ Monthly Movies
4-slide carousel on the 1st of each month from TMDB.

| Slide | Content |
|---|---|
| 1 | Cover |
| 2 | Top 10 most anticipated by TMDB popularity score |
| 3 | Your picks |
| 4 | Top 3 highest grossing last month with revenue |

### ðŸ“º Monthly TV
4-slide carousel on the 1st of each month from TMDB.

| Slide | Content |
|---|---|
| 1 | Cover |
| 2 | Top 10 shows premiering this month |
| 3 | Your picks |
| 4 | Most popular last month â€” TMDB rating + vote count |

### ðŸ“– Book Review
4-slide carousel posted as read. AI-assisted review drafting.

| Slide | Content |
|---|---|
| 1 | Book cover art + "BOOK REVIEW" title |
| 2 | Cover, rating (0-5 in 0.5 steps), AI-drafted review |
| 3 | 2026 Reading List â€” all books read with ratings |
| 4 | Next read |

### ðŸ—³ï¸ Daily Story Poll
Instagram Story background (1080Ã—1920). Add Instagram's native poll sticker on top.

### ðŸ“… Weekly Ideation
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
| AI captions | Groq â€” LLaMA 3.3-70B |
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
- [Bebas Neue](https://fonts.google.com/specimen/Bebas+Neue) â†’ `BebasNeue-Regular.ttf`
- [Oswald](https://fonts.google.com/specimen/Oswald) â†’ `Oswald-Bold.ttf`, `Oswald-Regular.ttf`

### 4. Configure environment
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```

### 5. Initialize database
```bash
python -m app initdb
python seed_books.py  # optional â€” seed past reads
```

### 6. Run from terminal
```bash
python -m app run        # dry run
python -m app run --live # post live
```

### 7. Or run from the iPhone

Three terminals:

```bash
# Terminal 1 — API
cd api
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install fastapi "uvicorn[standard]"
uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# Terminal 2 — Mobile
cd mobile
npm install
npx expo start
```

Scan the QR code with the iPhone Camera (Expo Go must be installed). In the app's Settings screen, set the server URL to `http://<your-pc-ip>:8001`.

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
â”œâ”€â”€ app/
â”‚   â””â”€â”€ __main__.py          # Entry point
â”œâ”€â”€ assets/
â”‚   â””â”€â”€ fonts/               # Bebas Neue, Oswald
â”œâ”€â”€ output/                  # Generated slides
â”‚   â””â”€â”€ weekly_plans/        # Saved content plans + poll JSON
â”œâ”€â”€ src/
â”‚   â”œâ”€â”€ caption/
â”‚   â”‚   â””â”€â”€ groq_caption.py  # Groq LLaMA caption generation
â”‚   â”œâ”€â”€ content/
â”‚   â”‚   â””â”€â”€ ideate.py        # Weekly content ideation engine
â”‚   â”œâ”€â”€ create/
â”‚   â”‚   â””â”€â”€ review.py        # Book review CLI
â”‚   â”œâ”€â”€ db/
â”‚   â”‚   â””â”€â”€ models.py        # SQLite models
â”‚   â”œâ”€â”€ generate/
â”‚   â”‚   â”œâ”€â”€ carousel.py      # Comics slide builder
â”‚   â”‚   â”œâ”€â”€ movies_carousel.py
â”‚   â”‚   â”œâ”€â”€ tv_carousel.py
â”‚   â”‚   â”œâ”€â”€ book_review.py
â”‚   â”‚   â””â”€â”€ poll.py          # Story poll builder
â”‚   â”œâ”€â”€ ingest/
â”‚   â”‚   â”œâ”€â”€ metron.py        # Metron comic data
â”‚   â”‚   â””â”€â”€ tmdb.py          # TMDB movie/TV data
â”‚   â”œâ”€â”€ post/
â”‚   â”‚   â”œâ”€â”€ carousel_post.py # Instagram posting
â”‚   â”‚   â””â”€â”€ upload.py        # Cloudinary upload
â”‚   â””â”€â”€ cli.py               # Click CLI commands
â”œâ”€â”€ .env.example
â”œâ”€â”€ requirements.txt
â”œâ”€â”€ seed_books.py
â””â”€â”€ watchtower.db
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
- [ ] DC Lore Model â€” fine-tuned LLaMA 3 for DM Q&A

---

## Portfolio Notes

This project demonstrates:
- **Production LLM integration** â€” Groq LLaMA 3.3-70B for caption generation and poll question generation with structured prompting
- **Multi-API orchestration** â€” Metron, TMDB, Open Library, Cloudinary, Meta Graph API
- **Programmatic image generation** â€” Pillow-based slide builder with custom typography, publisher color coding, cover art fetching
- **CLI tooling** â€” Click + Rich for interactive terminal workflows
- **SQLite data persistence** â€” reading list tracking across sessions
- **Modular architecture** â€” each content pillar is independently runnable

---

*Built by [@connorholliday5](https://github.com/connorholliday5)*


