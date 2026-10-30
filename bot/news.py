"""Rubrica news quotidiana: Claude cerca le notizie del giorno sul web e scrive
carosello e Reel con le 5 storie principali (la quinta sempre leggera)."""

import json
from datetime import datetime, timezone

import anthropic

from bot import config

CATEGORIES = ["politics", "economy", "world", "technology", "sport", "culture", "science", "curiosity"]

RESEARCH_SYSTEM = f"""You are the news editor of the Instagram page "{config.PAGE_NAME}" ({config.PAGE_HANDLE}),
an English-language page for an international audience. Every day it publishes a short
brief of the main news, for busy people who want to know what happened in seconds.

Research rules:
- Use web search. Only news from the last 24-36 hours; check publication times.
- Pick 5 stories. Stories 1-4: the most important and widely relevant for an
  international audience. Story 5: always a light, good or curious story.
- Every fact must be confirmed by at least 2 reputable, independent sources (Reuters,
  AP, BBC, Bloomberg, Financial Times, The Guardian, NYT, Al Jazeera, official sources).
  No rumours, single-source claims or unconfirmed breaking reports.
- Strictly neutral on politics: facts and stated positions only, no loaded words.
- No graphic details; treat tragedies with care.

Output: research notes for each story with the confirmed facts, numbers, dates, and
the source names and URLs. Plain text."""

SCHEMA = {
    "type": "object",
    "properties": {
        "hook": {"type": "string", "description": "Cover headline about story 1, max 7 words and about 45 characters (3 lines of big type), makes people stop scrolling"},
        "stories": {
            "type": "array",
            "description": "Exactly 5 stories; the 5th is light, good or curious",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": CATEGORIES},
                    "headline": {"type": "string", "description": "Max 5 words and 32 characters (2 lines of big type)"},
                    "highlight": {"type": "string", "description": "Striking number or word from the story shown huge (e.g. '+0.25%', '3 days', 'Mars'), max 6 characters; empty string if none"},
                    "image_query": {"type": "string", "description": "2-4 English words to search a real, freely licensed photo of the concrete subject (e.g. 'octopus underwater', 'saturn rings'); empty string if the subject is abstract or a real person"},
                    "image_prompt": {"type": "string", "description": "Scene for an AI image model if no photo fits: concrete symbolic objects or a visual metaphor, max 30 words. Never people, faces or hands, no text, no logos, no screens with writing"},
                    "what": {"type": "string", "description": "What happened: one sentence, max 10 words"},
                    "why": {"type": "string", "description": "Why it matters: one sentence, max 10 words"},
                    "for_you": {"type": "string", "description": "What changes for you: one sentence, max 14 words, concrete and honest. Shown in videos and in the caption; photo slides show only 'what' and 'why'"},
                    "sources": {"type": "array", "items": {"type": "string"}, "description": "At least 2 source URLs"},
                },
                "required": ["category", "headline", "highlight", "image_query", "image_prompt", "what", "why", "for_you", "sources"],
                "additionalProperties": False,
            },
        },
        "reel_hook": {"type": "string", "description": "2-second reel opening, max 7 words"},
        "cta": {"type": "string", "description": "Last slide, max 8 words and about 40 characters, invites to follow for the daily brief"},
        "caption": {"type": "string", "description": "3-6 short lines summing up the stories with one emoji each and, for the most useful stories, what it means for the reader; then one short question for comments; then a call to follow for the daily brief"},
        "hashtags": {"type": "array", "items": {"type": "string"}, "description": "8-12 hashtags, lowercase, without #"},
        "image_prompt": {"type": "string", "description": "Cover image for an AI image model: one concrete scene of symbolic objects or a visual metaphor for story 1, max 30 words. Never people, faces or hands, no text, no logos, no screens with writing"},
        "palette": {"type": "integer", "description": "Color variant of the brand style, 0 to 4"},
    },
    "required": ["hook", "stories", "reel_hook", "cta", "caption", "hashtags", "palette", "image_prompt"],
    "additionalProperties": False,
}

WRITE_SYSTEM = f"""You write the daily news brief of the Instagram page "{config.PAGE_NAME}" ({config.PAGE_HANDLE}).
Tone: a well-informed friend explaining the news at the bar: clear, direct, plain English,
short sentences. Strictly neutral on politics. Use only facts from the research notes, and
keep every number, name and date exactly as confirmed there. Respect the limits: the
design uses big type in fixed boxes, anything longer gets shrunk and looks worse. Cover
headline about 45 characters, story headlines 32 characters, and "what" plus "why"
together about 120 characters, because each photo slide shows only those two sentences.
Count characters. When in doubt, cut. The cover headline should create curiosity about
one concrete subject, not summarize the day."""


def _client():
    return anthropic.Anthropic()


def research() -> str:
    """Prima fase: ricerca sul web con fonti verificate."""
    today = datetime.now(timezone.utc).strftime("%A %d %B %Y")
    messages = [{"role": "user", "content": f"Today is {today} (UTC). Research today's 5 stories."}]
    for _ in range(6):
        response = _client().beta.messages.create(
            model=config.MODEL,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "high"},
            system=RESEARCH_SYSTEM,
            tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 20}],
            messages=messages,
        )
        if response.stop_reason == "pause_turn":
            # la ricerca sul server ha raggiunto il limite di passi: si riprende da dove era
            messages = messages[:1] + [{"role": "assistant", "content": response.content}]
            continue
        if response.stop_reason != "end_turn":
            raise RuntimeError(f"Ricerca interrotta: stop_reason={response.stop_reason}")
        notes = "".join(b.text for b in response.content if b.type == "text").strip()
        if not notes:
            raise RuntimeError("Ricerca senza risultati")
        return notes
    raise RuntimeError("Ricerca ancora in pausa dopo troppi tentativi")


def write(notes: str, history: list[dict]) -> dict:
    """Seconda fase: testi del carosello e del Reel, in formato strutturato."""
    recent = "\n".join(f"- {h['date']}: {h.get('hook', h['topic'])}" for h in history[-10:] if h.get("series") == "news")
    response = _client().beta.messages.create(
        model=config.MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA}},
        system=WRITE_SYSTEM,
        messages=[{"role": "user", "content": (
            f"## Research notes\n{notes}\n\n"
            f"## Recent daily briefs (do not repeat the same angle)\n{recent or '(none)'}\n\n"
            "Write today's brief."
        )}],
    )
    if response.stop_reason != "end_turn":
        raise RuntimeError(f"Scrittura interrotta: stop_reason={response.stop_reason}")
    return json.loads(next(b.text for b in response.content if b.type == "text"))


def to_post(brief: dict) -> dict:
    """Converte il brief nel formato dei post (stesse slide per carosello e Reel)."""
    date = datetime.now(timezone.utc).strftime("%d %b %Y").upper()
    return {
        "series": "news",
        "format": "carousel",
        "category": "news",
        "topic": "Daily news " + datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "hook": brief["hook"],
        "reel_hook": brief["reel_hook"],
        "slides": [
            {
                "title": s["headline"],
                "highlight": s["highlight"],
                "image_query": s.get("image_query", ""),
                "image_prompt": s.get("image_prompt", ""),
                "label": s["category"].upper(),
                "points": [["WHAT HAPPENED", s["what"]], ["WHY IT MATTERS", s["why"]], ["FOR YOU", s["for_you"]]],
                "body": " ".join([s["what"], s["why"], s["for_you"]]),
            }
            for s in brief["stories"][:5]
        ],
        "cta": brief["cta"],
        "caption": brief["caption"],
        "hashtags": brief["hashtags"],
        "sources": [u for s in brief["stories"] for u in s["sources"]],
        "design": {
            "palette": brief.get("palette", 0),
            "cover_label": f"Today's file · {date}",
            "swipe_text": "Swipe",
            "follow_line": "the news in 30 seconds, every day",
        },
        "image_query": brief["stories"][0].get("image_query", "") if brief.get("stories") else "",
        "image_prompt": brief.get("image_prompt", ""),
        "music": None,  # lo sceglie main.pick_music, diverso dagli ultimi Reel
        "trial": True,
    }


def generate_news(history: list[dict]) -> dict:
    return to_post(write(research(), history))
