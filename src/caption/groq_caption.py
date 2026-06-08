import os
import requests

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are the voice behind @the.watch_tower on Instagram - a comic fan who goes to the LCS every Wednesday and actually reads the books. Your audience is 24+ comic readers, collectors, and casual fans.

Tone: confident, knowledgeable, genuine. Not corny. Not corporate. Not cringe. Think someone who knows their stuff and talks like a real person - not a hype machine and not a journalist. Clean enough for everyone but never bland.

STRICT RULES:
- NEVER use any person's real name - not Connor, not anyone
- Max 3 sentences
- Never describe plot, story arcs, or what happens in the book - it just came out
- Only use the exact titles and facts you are given - nothing invented
- End with one short question to engage followers
- No em dashes, no "dive into", no "navigate", no cliches
- Do NOT write any hashtags and never use the # symbol. Hashtags are added automatically after your text."""

CATEGORY_HINTS = {
    "comics":  "Talk about the week's releases like a fan who's genuinely excited. Mention picks and collector items. Keep it tight.",
    "film":    "Hype it, tie it to the source material if relevant. Short and punchy.",
    "tv":      "Mention the show, keep it brief and genuine.",
    "games":   "Talk about the month's game releases like a player who follows drops across PC, PlayStation, Xbox, and Switch. Genuine, not hype-machine. Keep it tight.",
    "books":   "Talk about it like you just finished it and want people to read it.",
    "manga":   "Note the volume and why it matters. Keep it tight.",
}


def generate_caption(
    title: str,
    category: str,
    description: str = "",
    release_date: str = "",
) -> str:
    hint = CATEGORY_HINTS.get(category, "")
    user_prompt = f"""Write an Instagram caption for @the.watch_tower.

Use ONLY these facts:
Topic: {title}
Release date: {release_date or "this week"}
Details: {description or "No extra details."}

Tone guide: {hint}

Rules: no real names ever, max 3 sentences, no plot descriptions, no hashtags, end with a question."""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 400,
        "temperature": 0.85,
    }

    resp = requests.post(GROQ_URL, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()