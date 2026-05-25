import os
import requests

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are the social media voice for @TheWatchtower_, an Instagram account covering 
DC Comics, Marvel, indie comics, superhero film & TV, manga, and graphic novels.

Tone: passionate, knowledgeable, slightly nerdy but accessible. Not cringe. No emoji overload.
Always end with a call to action and 15-20 relevant hashtags on a new line.
Keep captions under 300 words. Lead with a hook."""

CATEGORY_HINTS = {
    "comics": "Focus on the story arc, creative team, and why fans should pick this up.",
    "film":   "Hype the release, reference source material, and tease what fans can expect.",
    "tv":     "Highlight the show, any notable casting or plot details, and the premiere date.",
    "books":  "Emphasize the reading experience, art style if applicable, and who it's for.",
    "manga":  "Note the volume, publisher, and any anime tie-in if relevant.",
}


def generate_caption(
    title: str,
    category: str,
    description: str = "",
    release_date: str = "",
) -> str:
    hint = CATEGORY_HINTS.get(category, "")
    user_prompt = f"""Generate an Instagram caption for:
Title: {title}
Category: {category}
Release date: {release_date or 'this week'}
Description: {description or 'No description available.'}

{hint}"""

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
        "max_tokens": 600,
        "temperature": 0.85,
    }

    resp = requests.post(GROQ_URL, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()
