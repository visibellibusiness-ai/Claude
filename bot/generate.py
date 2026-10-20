"""Genera il contenuto di un post (carosello) con Claude."""

import json

import anthropic

from bot import config

SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {"type": "string", "description": "Short topic label, used to avoid repeats"},
        "hook": {"type": "string", "description": "Cover slide headline, max 9 words, irresistible"},
        "slides": {
            "type": "array",
            "description": "5 to 7 slides, each one fact or one step of the story",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Max 6 words"},
                    "body": {"type": "string", "description": "Max 32 words, short sentences"},
                },
                "required": ["title", "body"],
                "additionalProperties": False,
            },
        },
        "cta": {"type": "string", "description": "Last slide: ask to save/share/comment, max 14 words"},
        "caption": {"type": "string", "description": "Instagram caption, 60-120 words, ending with a question for comments"},
        "hashtags": {"type": "array", "items": {"type": "string"}, "description": "8-12 relevant English hashtags, without #"},
        "sources": {"type": "array", "items": {"type": "string"}, "description": "Authoritative sources backing the facts"},
    },
    "required": ["topic", "hook", "slides", "cta", "caption", "hashtags", "sources"],
    "additionalProperties": False,
}

SYSTEM = f"""You are the content creator for the Instagram page "{config.PAGE_NAME}".
Niche: {config.NICHE}.

Goal: maximize saves, shares and comments, the signals Instagram's algorithm rewards most.

Rules:
- Write everything in natural, simple English (many readers are non-native speakers).
- Use only real, well-documented, verifiable facts. No myths, urban legends or made-up
  numbers. If a figure is approximate, say so ("about").
- The cover slide is a hook that sparks instant curiosity (e.g. "Your body does this
  every night without you knowing").
- Every following slide gives a concrete payoff and makes people want to keep swiping.
- Direct and conversational, short sentences, never encyclopedic.
- No emoji on slides; at most 3 in the caption.
- The caption ends with a simple question that is easy to answer in the comments."""


def generate_post(category: str, recent_topics: list[str]) -> dict:
    client = anthropic.Anthropic()
    avoid = "\n".join(f"- {t}" for t in recent_topics[-60:]) or "(none)"
    prompt = (
        f"Create a new carousel for the category: {category}.\n\n"
        f"Topics already published, do NOT repeat:\n{avoid}"
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
