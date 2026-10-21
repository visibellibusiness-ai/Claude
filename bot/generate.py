"""Genera il contenuto e lo stile di un post (carosello) con Claude."""

import json

import anthropic

from bot import config

SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {"type": "string", "description": "Why this topic, format and style, based on strategy and data"},
        "format": {"type": "string", "enum": ["carousel", "reel"], "description": "Carousel (swipeable images) or Reel (short video made from the same slides, with music)"},
        "music": {"type": "string", "enum": config.MUSIC_PRESETS, "description": "Reels only: background music genre. Ignored for carousels"},
        "trial": {"type": "boolean", "description": "Reels only: publish as Trial Reel (shown first to non-followers, auto-shared to followers if it performs well). Ignored for carousels"},
        "category": {"type": "string", "description": "Short category label (e.g. space, human body)"},
        "topic": {"type": "string", "description": "Short topic label, used to avoid repeats"},
        "hook": {"type": "string", "description": "Cover slide headline, max 10 words"},
        "slides": {
            "type": "array",
            "description": "3 to 9 content slides",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Max 7 words"},
                    "body": {"type": "string", "description": "Max 40 words"},
                    "highlight": {"type": "string", "description": "Optional striking number or word shown huge (e.g. '+1 cm', '8 min', '90%'), max 8 characters; empty string if none"},
                },
                "required": ["title", "body", "highlight"],
                "additionalProperties": False,
            },
        },
        "cta": {"type": "string", "description": "Last slide text, max 14 words"},
        "caption": {"type": "string", "description": "Instagram caption"},
        "hashtags": {"type": "array", "items": {"type": "string"}, "description": "Hashtags without #"},
        "sources": {"type": "array", "items": {"type": "string"}, "description": "Authoritative sources backing the facts"},
        "design": {
            "type": "object",
            "properties": {
                "palette": {"type": "integer", "description": "Color variant of the brand style, 0 to 4"},
                "cover_label": {"type": "string", "description": "Small label above the hook, max 4 words"},
                "swipe_text": {"type": "string", "description": "Hint on the cover, max 3 words"},
                "follow_line": {"type": "string", "description": "Tagline under 'Follow @handle' on the last slide, max 8 words"},
            },
            "required": ["palette", "cover_label", "swipe_text", "follow_line"],
            "additionalProperties": False,
        },
    },
    "required": ["reasoning", "format", "music", "trial", "category", "topic", "hook", "slides", "cta", "caption", "hashtags", "sources", "design"],
    "additionalProperties": False,
}

SYSTEM = f"""You run the Instagram page "{config.PAGE_NAME}" ({config.PAGE_HANDLE}) completely on your own.
Niche: {config.NICHE}.
Formats you can choose for each post:
- carousel: swipeable images (1080x1350). Usually strongest for saves and shares.
- reel: a short vertical video built from the same slides, with text animations and music.
  Usually strongest for reaching new people. Keep reels short: 3-6 slides, short texts,
  because each slide stays on screen for a few seconds based on its length.
- Reels can be Trial Reels: shown first only to non-followers and automatically shared with
  followers if they perform well. Ideal for risky experiments without hurting the profile.
The page has a fixed visual brand style; you pick one of its 5 color palettes per post,
the small labels, and a short "highlight" (a striking number or word shown huge) per slide
when it makes the fact hit harder. For reels you also pick the music genre.
You decide format, topic, angle, tone, length, palette, music and wording.

Goal: grow the page fast. Maximize reach, saves, shares, comments and follows.

You learn from results: you get your current strategy (written by you after reviewing past
performance) and the stats of recent posts. Follow what works, drop what doesn't, and keep
testing something new now and then so you keep discovering what works best.

Hard rules:
- English only, simple and natural.
- Only real, well-documented, verifiable facts. No myths or invented numbers.
"""


def _performance_table(history: list[dict]) -> str:
    rows = []
    for h in history[-30:]:
        m = h.get("metrics") or {}
        stats = ", ".join(f"{k}={v}" for k, v in m.items()) or "stats not available yet"
        kind = h.get("format", "carousel") + (" (trial)" if h.get("trial") else "")
        if h.get("music"):
            kind += f", music={h['music']}"
        if h.get("design"):
            kind += f", palette={h['design'].get('palette')}"
        rows.append(f"- {h['date']} | {kind} | {h.get('category', '?')} | \"{h.get('hook', h['topic'])}\" | {stats}")
    return "\n".join(rows) or "(no posts yet)"


def generate_post(history: list[dict], strategy: str) -> dict:
    client = anthropic.Anthropic()
    avoid = "\n".join(f"- {h['topic']}" for h in history[-80:]) or "(none)"
    prompt = (
        f"## Your current strategy\n{strategy or '(none yet: this is the start, experiment freely)'}\n\n"
        f"## Recent posts and stats\n{_performance_table(history)}\n\n"
        f"## Starting ideas (optional)\n{', '.join(config.STARTING_IDEAS)}\n\n"
        f"## Topics already published, do NOT repeat\n{avoid}\n\n"
        "Create the next post."
    )
    response = client.beta.messages.create(
        model=config.MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={
            "effort": "high",
            "format": {"type": "json_schema", "schema": SCHEMA},
        },
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason != "end_turn":
        raise RuntimeError(f"Generazione interrotta: stop_reason={response.stop_reason}")
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)
