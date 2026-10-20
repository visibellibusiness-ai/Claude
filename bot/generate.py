"""Genera il contenuto e lo stile di un post (carosello) con Claude."""

import json

import anthropic

from bot import config

HEX = {"type": "string", "description": "Colore esadecimale #RRGGBB"}

SCHEMA = {
    "type": "object",
    "properties": {
        "reasoning": {"type": "string", "description": "Why this topic, format and style, based on strategy and data"},
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
                },
                "required": ["title", "body"],
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
                "background": HEX,
                "text": HEX,
                "accent": HEX,
                "cover_label": {"type": "string", "description": "Small label above the hook, max 4 words"},
                "swipe_text": {"type": "string", "description": "Hint on the cover, max 3 words"},
                "follow_line": {"type": "string", "description": "Tagline under 'Follow @handle' on the last slide, max 8 words"},
                "show_numbers": {"type": "boolean", "description": "Show big 01, 02... numbers on content slides"},
            },
            "required": ["background", "text", "accent", "cover_label", "swipe_text", "follow_line", "show_numbers"],
            "additionalProperties": False,
        },
    },
    "required": ["reasoning", "category", "topic", "hook", "slides", "cta", "caption", "hashtags", "sources", "design"],
    "additionalProperties": False,
}

SYSTEM = f"""You run the Instagram page "{config.PAGE_NAME}" ({config.PAGE_HANDLE}) completely on your own.
Niche: {config.NICHE}.
Format: image carousels (1080x1350). You decide topic, angle, tone, length, colors and wording.

Goal: grow the page fast. Maximize reach, saves, shares, comments and follows.

You learn from results: you get your current strategy (written by you after reviewing past
performance) and the stats of recent posts. Follow what works, drop what doesn't, and keep
testing something new now and then so you keep discovering what works best.

Hard rules:
- English only, simple and natural.
- Only real, well-documented, verifiable facts. No myths or invented numbers.
- Readable colors: strong contrast between background and text."""


def _performance_table(history: list[dict]) -> str:
    rows = []
    for h in history[-30:]:
        m = h.get("metrics") or {}
        stats = ", ".join(f"{k}={v}" for k, v in m.items()) or "stats not available yet"
        rows.append(f"- {h['date']} | {h.get('category', '?')} | \"{h.get('hook', h['topic'])}\" | {stats}")
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
