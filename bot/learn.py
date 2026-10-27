"""Legge le statistiche dei post e fa rivedere la strategia a Claude."""

import os
from datetime import date, datetime, timedelta, timezone

import anthropic
import requests

from bot import config

# API Instagram con Instagram Login: servono i permessi instagram_business_basic e
# instagram_business_manage_insights nel token
GRAPH = "https://graph.instagram.com/v26.0"
# Metriche che l'API ha restituito nella prova del 27/10/2026 (bot/probe.py). "reposts" non è
# supportata sui singoli post. Il tempo medio di visione e il tasso di salto dei Reel si salvano
# così come arrivano: le unità non sono confermate.
REELS_METRICS = ["reach", "views", "likes", "comments", "shares", "saved", "total_interactions",
                 "ig_reels_avg_watch_time", "ig_reels_video_view_total_time", "reels_skip_rate"]
FEED_METRICS = ["reach", "views", "likes", "comments", "shares", "saved", "total_interactions",
                "follows", "profile_visits", "profile_activity"]


def _parse_date(stamp: str) -> datetime:
    return datetime.strptime(stamp, "%Y%m%d-%H%M").replace(tzinfo=timezone.utc)


def _read_metrics(media_id: str, metrics: list[str], token: str) -> dict | None:
    r = requests.get(f"{GRAPH}/{media_id}/insights", params={"metric": ",".join(metrics), "access_token": token}, timeout=30)
    if not r.ok:
        return None
    return {m["name"]: m["values"][0]["value"] for m in r.json().get("data", []) if m.get("values")}


def _insights(media_id: str, kind: str = "carousel") -> dict | None:
    """Metriche del post secondo il suo tipo. Se una non esiste per quel tipo l'API rifiuta
    l'intera richiesta: allora si chiedono una per una e si tengono quelle che rispondono."""
    token = os.environ["IG_ACCESS_TOKEN"]
    wanted = REELS_METRICS if kind == "reel" else FEED_METRICS
    found = _read_metrics(media_id, wanted, token)
    if found is None:
        found = {}
        for metric in wanted:
            one = _read_metrics(media_id, [metric], token)
            if one:
                found.update(one)
    if found:
        return found
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


# Copertura dell'account al giorno, divisa tra follower e non follower. L'API conserva i dati
# dell'account solo 90 giorni e li può correggere per 48 ore: a ogni giro si rileggono gli
# ultimi giorni e si sovrascrivono, i più vecchi restano come salvati in posts/state.json.
ACCOUNT_REREAD_DAYS = 4  # oggi (parziale) e i 3 giorni precedenti
ACCOUNT_LOG_MAX = 400
# (nome nel log, metrica, suddivisione). "follow_type" dà FOLLOWER / NON_FOLLOWER / UNKNOWN.
ACCOUNT_METRICS = [
    ("reach", "reach", "follow_type"),
    ("reach_by_product", "reach", "media_product_type"),
    ("views", "views", "follow_type"),
    ("views_by_product", "views", "media_product_type"),
    ("accounts_engaged", "accounts_engaged", None),
    ("total_interactions", "total_interactions", None),
    ("likes", "likes", None),
    ("comments", "comments", None),
    ("saves", "saves", None),
    ("shares", "shares", None),
]


def _account_metric(user_id: str, metric: str, breakdown: str | None, since: int, until: int) -> dict | None:
    """Un valore dell'account: {"total": n, "NON_FOLLOWER": n, ...}. None se l'API non lo dà."""
    params = {"metric": metric, "period": "day", "metric_type": "total_value", "since": since,
              "until": until, "access_token": os.environ["IG_ACCESS_TOKEN"]}
    if breakdown:
        params["breakdown"] = breakdown
    r = requests.get(f"{GRAPH}/{user_id}/insights", params=params, timeout=30)
    if not r.ok:
        print(f"Account: {metric}{'/' + breakdown if breakdown else ''} non disponibile: {r.text[:160]}")
        return None
    data = r.json().get("data", [])
    if not data:
        return None  # insieme vuoto: dato non ancora disponibile, non zero
    total = data[0].get("total_value", {})
    out = {"total": total.get("value")}
    for b in total.get("breakdowns", []):
        for res in b.get("results", []):
            out[res["dimension_values"][0]] = res["value"]
    return out


def account_day(user_id: str, day: date) -> dict:
    """Statistiche dell'account per un giorno UTC (dalle 00:00 alle 23:59:59)."""
    since = int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp())
    entry = {"date": day.isoformat()}
    for name, metric, breakdown in ACCOUNT_METRICS:
        entry[name] = _account_metric(user_id, metric, breakdown, since, since + 86399)
    return entry


def update_account_log(state: dict, today: date | None = None) -> list[dict]:
    """Aggiorna state["account_log"] con gli ultimi giorni. Non sovrascrive un giorno già salvato
    con uno vuoto. Restituisce le voci rilette."""
    user_id = os.environ["IG_USER_ID"]
    today = today or datetime.now(timezone.utc).date()
    log = {e["date"]: e for e in state.get("account_log", [])}
    fresh = []
    for back in range(ACCOUNT_REREAD_DAYS):
        entry = account_day(user_id, today - timedelta(days=back))
        fresh.append(entry)
        if any(v is not None for k, v in entry.items() if k != "date"):
            log[entry["date"]] = entry
    state["account_log"] = [log[k] for k in sorted(log)][-ACCOUNT_LOG_MAX:]
    return fresh


def _followers() -> int | None:
    r = requests.get(
        f"{GRAPH}/me",
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
            metrics = _insights(h["media_id"], h.get("format", "carousel"))
            if metrics:
                h["metrics"] = metrics
    return {"date": now.strftime("%Y%m%d-%H%M"), "followers": _followers()}


# Prima di riscrivere la strategia servono abbastanza post misurati: con 3 o 4 post i tassi
# sono rumore (scelta nostra di prudenza, non un numero di Instagram).
MIN_POSTS_TO_REFLECT = 10


def should_reflect(state: dict, history: list[dict]) -> bool:
    measured = sum(1 for h in history if h.get("metrics"))
    if measured < MIN_POSTS_TO_REFLECT:
        return False
    last = state.get("last_reflection")
    if not last:
        return True
    return datetime.now(timezone.utc) - _parse_date(last) >= timedelta(days=config.REFLECT_EVERY_DAYS)


def reflect(history: list[dict], strategy: str, followers_log: list[dict], account_log: list[dict] | None = None) -> str:
    """Claude analizza i risultati e riscrive la propria strategia, giudicando sui tassi."""
    from bot.report import MIN_REACH, rates_text

    lines = []
    for h in history[-60:]:
        lines.append(
            f"- {h['date']} | {h.get('format', 'carousel')}{' (trial)' if h.get('trial') else ''} | {h.get('category', '?')} | hook: \"{h.get('hook', h['topic'])}\" | "
            f"slides: {h.get('slides', '?')} | design: {h.get('design', {})} | music: {h.get('music') or '-'} | results: {rates_text(h.get('metrics'))}"
        )
    account = []
    for e in (account_log or [])[-28:]:
        reach, views = e.get("reach") or {}, e.get("views") or {}
        account.append(f"- {e['date']}: reach {reach.get('total', 'n/a')} (non-followers {reach.get('NON_FOLLOWER', 0)}), "
                       f"views {views.get('total', 'n/a')} (non-followers {views.get('NON_FOLLOWER', 0)}), "
                       f"saves {(e.get('saves') or {}).get('total', 'n/a')}")
    followers = "\n".join(f"- {f['date']}: {f['followers']}" for f in followers_log[-30:] if f.get("followers") is not None)
    prompt = (
        f"You run the Instagram page \"{config.PAGE_NAME}\" ({config.NICHE}) autonomously.\n"
        "Review the results below and rewrite your strategy document.\n\n"
        f"## Current strategy\n{strategy or '(none yet)'}\n\n"
        f"## Posts\n" + "\n".join(lines) + "\n\n"
        f"## Followers over time\n{followers or '(n/a)'}\n\n"
        f"## Account reach per day, split followers / non-followers\n" + ("\n".join(account) or "(n/a)") + "\n\n"
        "Write the new strategy in Markdown (max 400 words): what is working (with numbers), "
        "what is not, which formats (carousel vs reel vs trial reel), topics, hooks, lengths, colors "
        "and captions to use more or less, how to split formats, and 1-2 "
        "experiments to run next.\n"
        "How to judge: use RATES, never raw totals. Compare saves, shares, likes and profile visits per account "
        "reached, and for Reels the skip rate and average watch time (their units are not confirmed, so compare "
        "only between Reels). While the page has fewer than 100 followers, the share of reach and views that "
        "comes from non-followers is the main growth indicator. Data younger than 48 hours may be incomplete. "
        f"A post with fewer than {MIN_REACH} accounts reached cannot support a conclusion: say so instead of "
        "drawing one, and keep the current strategy mostly unchanged when the data is that thin. "
        "Do not invent causes: report what the numbers show, label hypotheses as hypotheses, and state clearly "
        "when there is too little data. Output only the document."
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
