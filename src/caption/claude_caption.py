import os
import anthropic

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are the social media voice for @TheWatchtower_, an Instagram account covering 
DC Comics, Marvel, indie comics, superhero film & TV, manga, and graphic novels.

Tone: passionate, knowledgeable, slightly nerdy but accessible. Not cringe. No emojis overload.
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

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text.strip()
