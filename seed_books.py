"""
Run this once to seed past books into the database.
Usage: python seed_books.py
"""
import sqlite3
from pathlib import Path

DB_PATH = Path("watchtower.db")

books = [
    # Red Rising Series — Pierce Brown
    ("Red Rising",       "Pierce Brown", 3.5, "2026"),
    ("Golden Son",       "Pierce Brown", 4.5, "2026"),
    ("Morning Star",     "Pierce Brown", 5.0, "2026"),
    ("Iron Gold",        "Pierce Brown", 4.0, "2026"),
    ("Dark Age",         "Pierce Brown", 4.5, "2026"),
    ("Light Bringer",    "Pierce Brown", 5.0, "2026"),

    # A Song of Ice and Fire — George R.R. Martin
    ("A Game of Thrones",    "George R.R. Martin", 4.0, "2026"),
    ("A Clash of Kings",     "George R.R. Martin", 4.0, "2026"),
    ("A Storm of Swords",    "George R.R. Martin", 5.0, "2026"),
    ("A Feast for Crows",    "George R.R. Martin", 3.5, "2026"),
    ("A Dance with Dragons", "George R.R. Martin", 4.5, "2026"),

    # Standalones
    ("Project Hail Mary", "Andy Weir",   4.0, "2026"),
    ("Watchmen",          "Alan Moore",  5.0, "2026"),
]

conn = sqlite3.connect(DB_PATH)
conn.execute("""
    CREATE TABLE IF NOT EXISTS books_read (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        rating REAL NOT NULL,
        date_reviewed TEXT NOT NULL,
        cover_url TEXT
    )
""")

# Clear existing and re-seed cleanly
conn.execute("DELETE FROM books_read")
added = 0
for title, author, rating, year in books:
    conn.execute(
        "INSERT INTO books_read (title, author, rating, date_reviewed, cover_url) "
        "VALUES (?, ?, ?, ?, ?)",
        (title, author, rating, year, "")
    )
    print(f"  + Added: {title} ({rating}/5)")
    added += 1

conn.commit()
conn.close()
print(f"\nDone — {added} books seeded.")