# TheWatchtower_

Automated Instagram content pipeline for DC, Marvel, indie comics, superhero film & TV, manga, and graphic novels.

## Setup

```powershell
# Rename folder first
Rename-Item "Comic_Book_Releases" "the_watchtower"

# Install dependencies
pip install -r requirements.txt

# Copy and fill in credentials
cp .env.example .env
```

## Usage

```powershell
# Dry run (safe, no posting)
python -m app run

# Live post to Instagram
python -m app run --live

# Start Wednesday scheduler
python -m app schedule

# Init DB
python -m app initdb
```

## API Keys Required

| Service | Where |
|---|---|
| Anthropic | platform.anthropic.com |
| ComicVine | comicvine.gamespot.com/api |
| TMDB | themoviedb.org/settings/api |
| Meta Graph API | developers.facebook.com |

## Project Structure

```
src/
  ingest/      # Data fetching (ComicVine, TMDB, Open Library)
  generate/    # Image generation (Pillow)
  caption/     # Claude AI captions
  post/        # Instagram Graph API
  scheduler/   # APScheduler weekly cadence
  db/          # SQLite via Peewee
  cli.py       # CLI entrypoint
```
