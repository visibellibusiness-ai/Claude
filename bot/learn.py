"""Legge le statistiche dei post e fa rivedere la strategia a Claude."""

import os
from datetime import datetime, timedelta, timezone

import anthropic
import requests

from bot import config

GRAPH = "https://graph.facebook.com/v21.0"
METRICS = ["reach", "saved", "shares", "likes", "comments", "total_interactions"]


def _parse_date(stamp: str) -> datetime:
    return datetime.strptime(stamp, "%Y%m%d-%H%M").replace(tzinfo=timezone.utc)


def _insights(media_id: str) -> dict | None:
    token = os.environ["IG_ACCESS_TOKEN"]
    r = requests.get(
        f"{GRAPH}/{media_id}/insights",
        params={"metric": ",".join(METRICS), "access_token": token},
        timeout=30,
    )
    if r.ok:
        return {m["name"]: m["values"][0]["value"] for m in r.json().get("data", [])}
    # senza permesso insights restano comunque like e commenti pubblici
    r = requests.get(
        f"{GRAPH}/{media_id}",
        params={"fields": "like_count,comments_count", "access_token": token},
        timeout=30,
    )
    if r.ok:
        d = r.json()
        return {"likes": d.get("like_count", 0), "comments": d.get("comments_count", 0)}
    print(f"Statistiche non disponibili per {media_id}: {r.text}")
    return None


def _followers() -> int | None:
    r = requests.get(
        f"{GRAPH}/{os.environ['IG_USER_ID']}",
        params={"fields": "followers_count", "access_token": os.environ["IG_ACCESS_TOKEN"]},
        timeout=30,
    )
    return r.json().get("followers_count") if r.ok else None


def update_metrics(history: list[dict]) -> dict:
    """Aggiorna le statistiche dei post abbastanza vecchi, finché sono recenti (ultime 2 settimane)."""
    now = datetime.now(timezone.utc)
    for h in history:
        if "media_id" not in h:
            continue
        age = now - _parse_date(h["date"])
        if timedelta(hours=config.INSIGHTS_MIN_AGE_HOURS) <= age <= timedelta(days=14):
            metrics = _insights(h["media_id"])
            if metrics:
                h["metrics"] = metrics
    return {"date": now.strftime("%Y%m%d-%H%M"), "followers": _followers()}


def should_reflect(state: dict, history: list[dict]) -> bool:
    measured = sum(1 for h in history if h.get("metrics"))
    if measured < 3:
        return False
    last = state.get("last_reflection")
    if not last:
        return True
    return datetime.now(timezone.utc) - _parse_date(last) >= timedelta(days=config.REFLECT_EVERY_DAYS)


def reflect(history: list[dict], strategy: str, followers_log: list[dict]) -> str:
    """Claude analizza i risultati e riscrive la propria strategia."""
    lines = []
    for h in history[-60:]:
        lines.append(
            f"- {h['date']} | {h.get('format', 'carousel')}{' (trial)' if h.get('trial') else ''} | {h.get('category', '?')} | hook: \"{h.get('hook', h['topic'])}\" | "
            f"slides: {h.get('slides', '?')} | design: {h.get('design', {})} | music: {h.get('music') or '-'} | metrics: {h.get('metrics', 'n/a')}"
        )
    followers = "\n".join(f"- {f['date']}: {f['followers']}" for f in followers_log[-30:] if f.get("followers") is not None)
    prompt = (
        f"You run the Instagram page \"{config.PAGE_NAME}\" ({config.NICHE}) autonomously.\n"
        "Review the results below and rewrite your strategy document.\n\n"
        f"## Current strategy\n{strategy or '(none yet)'}\n\n"
        f"## Posts\n" + "\n".join(lines) + "\n\n"
        f"## Followers over time\n{followers or '(n/a)'}\n\n"
        "Write the new strategy in Markdown (max 400 words): what is working (with numbers), "
        "what is not, which formats (carousel vs reel vs trial reel), topics, hooks, lengths, colors "
        "and captions to use more or less, how to split formats, and 1-2 "
        "experiments to run next. Judge mainly saves, shares and reach relative to the average. "
        "Be honest when there is too little data to draw conclusions. Output only the document."
    )
    response = anthropic.Anthropic().beta.messages.create(
        model=config.MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "high"},
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason != "end_turn":
        raise RuntimeError(f"Revisione interrotta: stop_reason={response.stop_reason}")
    return "".join(b.text for b in response.content if b.type == "text").strip()
