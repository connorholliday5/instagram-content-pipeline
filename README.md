# TheWatchtower_ — Social Media Content Engine

![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white)
![Pillow](https://img.shields.io/badge/Pillow-Image%20Generation-green)
![Groq](https://img.shields.io/badge/Groq-LLaMA%203.3--70B-orange)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

An automated Instagram content pipeline for [@the.watch\_tower](https://instagram.com/the.watch_tower), a pop culture account covering comics, movies, TV, games, and books. Generates production-quality carousel slides, AI-assisted captions, story polls, and a weekly content plan. Built as a portfolio signal for production LLM and automation work.

---

## Two ways to run it

Every command can be driven from a terminal or from an iPhone. The phone app pairs with a local FastAPI server, streams pipeline output, and lets you approve, edit, or regenerate each step before posting.

```
iPhone (Expo Go) -- HTTP --> FastAPI (port 8001) -- subprocess --> python -m app stage <cmd> <stage>
```

| Folder | Component |
|---|---|
| `src/cli.py` | Click CLI, one interactive command per content type |
| `src/content/*_stages.py` | Pure stage functions (headless, JSON state) shared by the app |
| `api/` | FastAPI server wrapping each command as a state machine |
| `mobile/` | React Native (Expo SDK 54) app |

The CLI and the app run the same underlying logic. When changing a pipeline, both the CLI flow and the matching `*_stages.py` flow need to stay in sync.

---

## What it does

| Command | Description | Cadence |
|---|---|---|
| `python -m app run` | New Comic Book Day carousel | Posted Monday, about Wednesday's releases |
| `python -m app movies` | Monthly top 10 anticipated movies + highest grossing | 1st of month |
| `python -m app tv` | Monthly top 10 TV premieres + most popular last month | 1st of month |
| `python -m app games` | Monthly top 10 game releases + most played on Steam | 1st of month |
| `python -m app review` | Book review carousel with AI-assisted caption | As read |
| `python -m app poll` | Daily story poll background for Instagram | Daily |
| `python -m app ideate` | Weekly content plan | Weekly |
| `python -m app initdb` | Initialize SQLite database | One-time |

---

## Comics pipeline (New Comic Book Day)

The flagship weekly carousel. It is posted on Monday but is about the **upcoming Wednesday's** releases, so followers can plan their pull list ahead of time.

Release data comes from **League of Comic Geeks** via the `comicgeeks` library, which is forward-looking and works anonymously. **ComicVine** is a fallback source only (it does not reliably carry future-week data). All dates are anchored to the upcoming Wednesday street date.

| Slide | Content |
|---|---|
| 1 | Cover — Watchtower station illustration, upcoming Wednesday date |
| 2 | Top 10 new releases, color-coded by publisher |
| 3 | Watchtower's Picks — your selected issues |
| 4 | Collector's Corner — flagship #1s, key issues, milestones |

Ranking and filtering:

- Top 10 is ranked by a franchise/character prominence scorer (`MARQUEE_SCORES`). Community pull-count ranking is not used because it requires authentication that the public endpoint blocks.
- US/English market only: just the five color-coded publishers (DC, Marvel, Image, Dark Horse, IDW) are kept. Foreign editions and digital-only lines (Infinity Comics, etc.) are dropped.
- Collector's Corner surfaces genuine key issues: variant/key keywords, milestone numbering, and `#1`s gated behind a marquee threshold so minor or licensed launches do not qualify. It is deduped against the top 10.

Publisher color coding: DC (blue), Marvel (red), Image (orange), Dark Horse (green), IDW (yellow).

---

## Other content modules

### Monthly Movies
4-slide carousel from TMDB: cover, top 10 anticipated, your picks, top 3 highest grossing last month with revenue.

### Monthly TV
4-slide carousel from TMDB: cover, top 10 premiering this month, your picks, most popular last month with rating and vote count. US/English bias applied.

### Monthly Games
4-slide carousel from RAWG (releases) and Steam (live player counts): cover, top 10 releases, your picks, most played.

### Book Review
4-slide carousel posted as read, with AI-assisted review drafting and a running reading list tracked in SQLite.

### Daily Story Poll
Instagram Story background (1080x1920). Add Instagram's native poll sticker on top.

### Weekly Ideation
Generates a weekly content plan: an upcoming-Wednesday comic preview, a batch of daily poll questions, and monthly reminders.

---

## Architecture

```
                 +-------------------------------+
                 |        Entry points           |
                 |  CLI  python -m app <cmd>      |
                 |  App  FastAPI stage runner     |
                 +--------------+----------------+
                                |
         +----------------------+----------------------+
         |                      |                      |
   +-----v------+        +------v------+        +------v-------+
   | Data ingest|        | Slide build |        | Caption gen  |
   |            |        |             |        |              |
   | LCG / CV   |        | Pillow/PIL  |        | Groq LLaMA   |
   | TMDB       |        | Bebas Neue  |        | 3.3 70B      |
   | RAWG/Steam |        | Oswald      |        |              |
   | OpenLibrary|        |             |        |              |
   +-----+------+        +------+------+        +------+-------+
         |                      |                      |
         +----------------------+----------------------+
                                |
                          +-----v------+
                          |   Output   |
                          | JPG slides |
                          | Captions   |
                          | Poll/plans |
                          +-----+------+
                                |
                         +------v-------+
                         | Cloudinary   |
                         +--------------+
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Language | Python 3.13 |
| Image generation | Pillow (PIL) |
| Comic data | League of Comic Geeks (`comicgeeks`), ComicVine (fallback) |
| Movie/TV data | TMDB API |
| Game data | RAWG API, Steam |
| Book covers | Open Library API |
| AI captions | Groq, LLaMA 3.3 70B |
| Image hosting | Cloudinary |
| Database | SQLite |
| CLI | Click + Rich |
| API / app | FastAPI, React Native (Expo SDK 54) |
| Fonts | Bebas Neue, Oswald |

---

## Setup

```bash
git clone https://github.com/connorholliday5/instagram-content-pipeline
cd instagram-content-pipeline
pip install -r requirements.txt
```

Place fonts in `assets/fonts/`: `BebasNeue-Regular.ttf`, `Oswald-Bold.ttf`, `Oswald-Regular.ttf`.

Copy `.env.example` to `.env` and fill in your keys, then initialize the database:

```bash
python -m app initdb
python -m app run        # dry run
python -m app run --live # post live
```

To run from the iPhone, start two terminals from the project root:

```powershell
# Terminal 1 - API
uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload

# Terminal 2 - Mobile
cd mobile
$env:REACT_NATIVE_PACKAGER_HOSTNAME="<your-pc-ip>"
npx expo start
```

Scan the QR code with the iPhone Camera (Expo Go installed). In the app, set the server URL to `http://<your-pc-ip>:8001`.

---

## Environment variables

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Groq Console |
| `TMDB_API_KEY` | TMDB API |
| `COMICVINE_API_KEY` | ComicVine API (fallback comic source) |
| `RAWG_API_KEY` | RAWG API (game releases) |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary |
| `CLOUDINARY_API_KEY` | Cloudinary API key |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret |
| `INSTAGRAM_BUSINESS_ACCOUNT_ID` | Instagram Business account ID |
| `META_PAGE_ACCESS_TOKEN` | Meta Graph API token |
| `META_APP_ID` | Meta App ID |
| `META_APP_SECRET` | Meta App secret |

Note: `LCG_CI_SESSION` is intentionally left unset. League of Comic Geeks is used anonymously; a session cookie is not required and an invalid one causes request failures.

---

## Project structure

```
WatchTower/
├── app/                     # python -m app entry point
├── api/
│   └── main.py              # FastAPI state-machine server
├── mobile/                  # React Native (Expo) app
├── assets/fonts/            # Bebas Neue, Oswald
├── output/                  # Generated slides
│   └── pipelines/           # Per-run JSON state
├── src/
│   ├── caption/
│   │   └── groq_caption.py
│   ├── content/             # Headless stage functions + ideation
│   │   ├── run_stages.py
│   │   ├── movies_stages.py
│   │   ├── tv_stages.py
│   │   ├── games_stages.py
│   │   ├── review_stages.py
│   │   ├── poll_stages.py
│   │   └── ideate.py
│   ├── create/
│   │   └── review.py
│   ├── db/
│   │   └── models.py
│   ├── generate/
│   │   ├── comics_carousel.py
│   │   ├── movies_carousel.py
│   │   ├── tv_carousel.py
│   │   ├── games_carousel.py
│   │   └── poll.py
│   ├── ingest/
│   │   ├── comicvine.py     # LCG primary + ComicVine fallback
│   │   ├── tmdb.py
│   │   ├── rawg.py
│   │   └── steam.py
│   ├── post/
│   │   └── carousel_post.py
│   └── cli.py
├── .env.example
├── requirements.txt
└── watchtower.db
```

---

## Roadmap

- [x] Weekly comic carousel (New Comic Book Day)
- [x] Monthly movies, TV, and games carousels
- [x] Book review carousel with AI drafting
- [x] Daily story poll generator
- [x] Weekly content ideation engine
- [x] FastAPI server + iPhone app
- [ ] Instagram posting automation
- [ ] Engagement bot (pending Meta app review)
- [ ] DC Lore Model, fine-tuned LLaMA 3 for DM Q&A

---

## Portfolio notes

This project demonstrates production LLM integration (Groq LLaMA 3.3 70B for captions and poll questions with structured prompting), multi-API orchestration (League of Comic Geeks, ComicVine, TMDB, RAWG, Steam, Open Library, Cloudinary, Meta Graph API), programmatic image generation (Pillow slide builder with custom typography, publisher color coding, and cover fetching), a shared CLI and FastAPI/React Native architecture, and SQLite persistence.

---

*Built by [@connorholliday5](https://github.com/connorholliday5)*