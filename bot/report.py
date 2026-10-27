"""Rapporto sulle statistiche: solo numeri letti dall'API, nessuna interpretazione.

Si basa sui tassi (azioni diviso account raggiunti) e non sui totali, perché Instagram dice
di guardare le percentuali di spettatori che mettono like o inviano il post (Mosseri, serie
sul ranking, parte 4) e perché un post visto da pochi non si confronta con uno visto da molti.
Scrive posts/report.md a ogni giro di `learn`.
"""

from datetime import datetime, timedelta, timezone

# Sotto questa copertura un tasso è troppo instabile per trarre conclusioni. È una soglia
# nostra di prudenza, non un numero di Instagram.
MIN_REACH = 10
# I dati possono arrivare con fino a 48 ore di ritardo (documentazione API Insights)
FRESH_HOURS = 48


def _num(x):
    return x if isinstance(x, (int, float)) else None


def rate(numerator, denominator):
    n, d = _num(numerator), _num(denominator)
    if n is None or not d:
        return None
    return n / d


def pct(x, digits: int = 1) -> str:
    """Percentuale con la virgola decimale, come si scrive in italiano."""
    return "n/d" if x is None else f"{x * 100:.{digits}f}".replace(".", ",") + "%"


def it_int(x) -> str:
    """Numero intero all'italiana: il punto separa le migliaia (11.764)."""
    return f"{x:,}".replace(",", ".") if isinstance(x, int) else ("n/d" if x is None else str(x))


def day_it(iso: str) -> str:
    """2026-10-27 -> 27/10/2026"""
    return datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m/%Y")


def stamp_it(stamp: str) -> str:
    """20261027-1242 -> 27/10/2026 12:42"""
    return datetime.strptime(stamp, "%Y%m%d-%H%M").strftime("%d/%m/%Y %H:%M")


def post_rates(metrics: dict | None) -> dict:
    """Tassi di un post a partire dalle sue metriche. Ogni valore è None se manca il dato."""
    m = metrics or {}
    reach = m.get("reach")
    return {
        "reach": reach,
        "views": m.get("views"),
        "saves": rate(m.get("saved"), reach),
        "shares": rate(m.get("shares"), reach),
        "likes": rate(m.get("likes"), reach),
        "comments": rate(m.get("comments"), reach),
        "interactions": rate(m.get("total_interactions"), reach),
        "profile_visits": rate(m.get("profile_visits"), reach),
        "follows": m.get("follows"),
        "views_per_reach": rate(m.get("views"), reach),
    }


def rates_text(metrics: dict | None) -> str:
    """Tassi di un post in una riga, per la richiesta di revisione della strategia."""
    if not metrics:
        return "no data yet"
    r = post_rates(metrics)
    parts = [f"reach {r['reach']}", f"views {r['views']}"]
    for key, label in (("saves", "saves"), ("shares", "shares"), ("likes", "likes"),
                       ("comments", "comments"), ("profile_visits", "profile visits")):
        if r[key] is not None:
            parts.append(f"{label}/reach {r[key] * 100:.1f}%")
    if metrics.get("follows") is not None:
        parts.append(f"follows {metrics['follows']}")
    for key in ("ig_reels_avg_watch_time", "reels_skip_rate"):
        if key in metrics:
            parts.append(f"{key} {metrics[key]}")
    if isinstance(r["reach"], (int, float)) and r["reach"] < MIN_REACH:
        parts.append(f"(reach under {MIN_REACH}: too small to trust)")
    return ", ".join(parts)


def account_summary(account_log: list[dict], today) -> dict:
    """Totali degli ultimi 7 giorni dal registro giornaliero dell'account."""
    days = [e for e in account_log if e["date"] > (today - timedelta(days=7)).isoformat()]
    views = sum(_num((e.get("views") or {}).get("total")) or 0 for e in days)
    views_non = sum(_num((e.get("views") or {}).get("NON_FOLLOWER")) or 0 for e in days)
    return {"days": days, "views": views, "views_non_followers": views_non,
            "share_non": rate(views_non, views)}


def build_report(history: list[dict], state: dict, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    followers_log = [f for f in state.get("followers_log", []) if f.get("followers") is not None]
    followers = followers_log[-1]["followers"] if followers_log else "n/d"
    lines = [
        "# Rapporto statistiche @you.didnot.know",
        "",
        f"Aggiornato il {now.strftime('%d/%m/%Y alle %H:%M')} UTC. Follower: {followers}.",
        "Solo numeri letti dall'API di Instagram. I dati possono arrivare con fino a 48 ore di "
        "ritardo e alcune metriche sono ancora \"in sviluppo\" per Instagram.",
        "",
        "## Account, ultimi 7 giorni",
        "",
    ]
    summary = account_summary(state.get("account_log", []), now.date())
    if not summary["days"]:
        lines.append("Nessun dato giornaliero salvato.")
    else:
        lines += [
            f"- Visualizzazioni: {summary['views']}, di cui da non follower {summary['views_non_followers']} "
            f"({pct(summary['share_non'], 0)}).",
            "",
            "| Giorno | Copertura | Non follower | Visualizzazioni | Non follower | Interazioni | Salvataggi |",
            "|---|---|---|---|---|---|---|",
        ]
        for e in reversed(summary["days"]):
            reach, views = e.get("reach") or {}, e.get("views") or {}
            lines.append(
                f"| {day_it(e['date'])} | {reach.get('total', 'n/d')} | {reach.get('NON_FOLLOWER', 0) if reach else 'n/d'} | "
                f"{views.get('total', 'n/d')} | {views.get('NON_FOLLOWER', 0) if views else 'n/d'} | "
                f"{(e.get('total_interactions') or {}).get('total', 'n/d')} | {(e.get('saves') or {}).get('total', 'n/d')} |"
            )
        lines += ["", "La copertura di giorni diversi non si somma: lo stesso account può essere contato più volte."]

    lines += ["", "## Post con statistiche (ultimi 14 giorni)", ""]
    rows = []
    for h in history:
        if not h.get("metrics") or "media_id" not in h:
            continue
        posted = datetime.strptime(h["date"], "%Y%m%d-%H%M").replace(tzinfo=timezone.utc)
        if now - posted > timedelta(days=14):
            continue
        r = post_rates(h["metrics"])
        notes = []
        if isinstance(r["reach"], (int, float)) and r["reach"] < MIN_REACH:
            notes.append(f"copertura sotto {MIN_REACH}")
        if now - posted < timedelta(hours=FRESH_HOURS):
            notes.append("dato recente")
        rows.append((h, r, "; ".join(notes)))
    if not rows:
        lines.append("Ancora nessun post con statistiche: il bot le legge dopo 48 ore dalla pubblicazione.")
    else:
        lines += [
            "| Data | Tipo | Titolo | Copertura | Visual. | Salvat./cop. | Condiv./cop. | Like/cop. | Visite profilo/cop. | Note |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ]
        for h, r, notes in sorted(rows, key=lambda x: x[0]["date"], reverse=True):
            lines.append(
                f"| {stamp_it(h['date'])} | {h.get('format', 'carousel')} | {h.get('hook', h.get('topic', ''))[:40]} | "
                f"{r['reach'] if r['reach'] is not None else 'n/d'} | {r['views'] if r['views'] is not None else 'n/d'} | "
                f"{pct(r['saves'])} | {pct(r['shares'])} | {pct(r['likes'])} | {pct(r['profile_visits'])} | {notes} |"
            )
        reels = [(h, r) for h, r, _ in rows if h.get("format") == "reel"]
        if reels:
            lines += ["", "### Reel", "",
                      "Tempo medio di visione e tasso di salto sono mostrati come li dà l'API: le unità non sono confermate, "
                      "quindi si confrontano solo tra Reel e non come valori assoluti.", "",
                      "| Data | Titolo | Tempo medio di visione | Tasso di salto |", "|---|---|---|---|"]
            for h, _ in reels:
                m = h["metrics"]
                lines.append(f"| {stamp_it(h['date'])} | {h.get('hook', '')[:40]} | {it_int(m.get('ig_reels_avg_watch_time'))} | "
                             f"{it_int(m.get('reels_skip_rate'))} |")
        lines += ["", "### Per formato", "", "| Formato | Post | Copertura totale | Salvat./cop. | Condiv./cop. |", "|---|---|---|---|---|"]
        by_format: dict[str, list] = {}
        for h, r, _ in rows:
            by_format.setdefault(h.get("format", "carousel"), []).append(h["metrics"])
        for fmt, ms in sorted(by_format.items()):
            reach = sum(_num(m.get("reach")) or 0 for m in ms)
            lines.append(f"| {fmt} | {len(ms)} | {reach} | {pct(rate(sum(_num(m.get('saved')) or 0 for m in ms), reach))} | "
                         f"{pct(rate(sum(_num(m.get('shares')) or 0 for m in ms), reach))} |")
        lines += ["", f"Un tasso con una copertura sotto {MIN_REACH} account non permette conclusioni: è una soglia di prudenza nostra, "
                      "non un numero di Instagram."]
    return "\n".join(lines) + "\n"
