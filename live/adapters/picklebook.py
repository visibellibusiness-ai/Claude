"""Adapter Picklebook (picklebook.org) — la piattaforma di Pickleball England.

Le pagine sono renderizzate lato server (niente browser headless):
- /a/{org}/tournaments/{id}/results                       indice degli eventi (categorie)
- /a/{org}/tournaments/{id}/results/{evento}              pagina evento, con i link ai gironi
- /a/{org}/tournaments/{id}/results/{evento}/group/{g}    girone: classifica + matrice partite
- /a/{org}/tournaments/{id}/results/{evento}/knockouts/top    tabellone, con i dati in un
  JSON incorporato: const content = {rounds, matches, contestants}

Uso: snapshot(base_url, events=None, fetch=None) -> Snapshot
base_url es. "https://www.picklebook.org/a/pbe/tournaments/bYC3Jqgwq7JKJKwJ"
events: filtro opzionale sui nomi evento (sottostringhe, case-insensitive); None = tutti.
fetch: funzione url -> html, sostituibile nei test con le pagine salvate.
"""

from __future__ import annotations

import html as htmllib
import json
import re
from collections.abc import Callable

from live.model import Match, Snapshot, Team

# nome del round su Picklebook -> fase del formato comune
# ("Round of 16" = 16 squadre in tabellone, cioè gli ottavi di finale)
PHASE_MAP = {
    "round of 64": "trentaduesimi",
    "round of 32": "sedicesimi",
    "round of 16": "ottavi",
    "quarter-finals": "quarti",
    "semi-finals": "semifinali",
    "final": "finale",
}

RE_EVENT_LINK = re.compile(r"""<a[^>]+href="[^"]*/results/(\d+)"[^>]*>(.*?)</a>""", re.S)
RE_GROUP_LINK = re.compile(r"""href="[^"]*/results/\d+/group/(\d+)" """.strip())
RE_CONTENT = re.compile(r"const content = (\{.*)", re.S)
RE_BADGE = re.compile(r"""<span class="badge[^"]*">\s*([WL])\s*([\d\s\-,]+?)\s*</span>""")


def clean(text: str) -> str:
    return htmllib.unescape(re.sub(r"<[^>]+>|\s+", " ", text)).strip()


def default_fetch(url: str) -> str:
    import requests

    r = requests.get(url, timeout=40, headers={"User-Agent": "Mozilla/5.0 (PickleballSpot live)"})
    r.raise_for_status()
    return r.text


def list_events(base_url: str, fetch: Callable[[str], str]) -> dict[str, str]:
    """{id evento: nome} dall'indice dei risultati."""
    page = fetch(f"{base_url}/results")
    events: dict[str, str] = {}
    for event_id, label in RE_EVENT_LINK.findall(page):
        name = clean(label)
        if name:
            events[event_id] = name
    return events


def _embedded_content(page: str) -> dict | None:
    m = RE_CONTENT.search(page)
    if m is None:
        return None
    s = m.group(1)
    depth = 0
    for i, ch in enumerate(s):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(s[: i + 1])
    return None


def _team(contestants: dict, cid: str) -> Team | None:
    """Da "c_11093" ai nomi; None per BYE/PENDING/assenti."""
    entry = contestants.get(cid)
    if entry is None:
        return None
    titles = [clean(p.get("title", "")) for p in entry.get("players", [])]
    names = [n for t in titles for n in re.split(r"\s*&\s*", t) if n]
    if not names or any(n.upper() in ("BYE", "PENDING", "TBD") for n in names):
        return None
    return Team(players=names)


def knockout_matches(page: str, event: str, bracket: str = "top") -> list[Match]:
    """Le partite del tabellone dal JSON incorporato nella pagina knockouts."""
    data = _embedded_content(page)
    if not data:
        return []
    rounds = [r.get("name", "") for r in data.get("rounds", [])]
    contestants = data.get("contestants", {})
    out: list[Match] = []
    for m in data.get("matches", []):
        meta = m.get("metadata", {})
        if meta.get("hasBye"):
            continue
        sides = m.get("sides", [])
        if len(sides) != 2:
            continue
        team_a = _team(contestants, sides[0].get("contestantId", ""))
        team_b = _team(contestants, sides[1].get("contestantId", ""))
        tbd = team_a is None or team_b is None
        if tbd:
            # partita futura con squadre da definire: entra nello snapshot solo per
            # il conteggio di completezza della fase
            team_a = team_a or Team(players=["TBD"])
            team_b = team_b or Team(players=["TBD"])
        games_a = [s.get("mainScore", "") for s in sides[0].get("scores", [])]
        games_b = [s.get("mainScore", "") for s in sides[1].get("scores", [])]
        # un game non giocato arriva come "-" o vuoto: si tengono solo i game con due numeri
        score = [f"{a}-{b}" for a, b in zip(games_a, games_b)
                 if str(a).strip().isdigit() and str(b).strip().isdigit()]
        winner = ""
        if sides[0].get("isWinner"):
            winner = "a"
        elif sides[1].get("isWinner"):
            winner = "b"
        round_name = rounds[m["roundIndex"]] if m.get("roundIndex", -1) < len(rounds) else ""
        phase = PHASE_MAP.get(round_name.strip().lower(), round_name.strip().lower())
        if m.get("isBronzeMatch"):
            phase = "terzo posto"
        if bracket != "top":
            phase = f"{bracket}:{phase}"
        out.append(
            Match(
                event=event,
                phase=phase,
                side_a=team_a,
                side_b=team_b,
                score=score,
                winner="" if tbd else winner,
                match_id=str(meta.get("matchId", "")),
                tbd=tbd,
            )
        )
    return out


def group_matches(page: str, event: str) -> list[Match]:
    """Le partite giocate di un girone, dalla matrice squadra x squadra.

    Ogni cella giocata ha un badge "W 11 - 4" o "L 4 - 11" dal punto di vista della riga.
    Si tengono solo le celle W: ogni partita compare due volte nella matrice (W da un lato,
    L dall'altro) e così si evita il doppione, con il vincitore sempre su side_a.
    """
    section = page.split(">Matches<", 1)
    if len(section) != 2:
        return []
    table_m = re.search(r"<table.*?</table>", section[1], re.S)
    if table_m is None:
        return []
    table = table_m.group(0)
    group_m = re.search(r">\s*Group\s+([^<]{1,20})<", page)
    group_name = clean(group_m.group(1)) if group_m else ""
    phase = f"gironi{' ' + group_name if group_name else ''}"

    head = re.search(r"<thead>(.*?)</thead>", table, re.S)
    if head is None:
        return []
    columns = [clean(c) for c in re.findall(r"<th[^>]*>(.*?)</th>", head.group(1), re.S)]
    columns = [c for c in columns if c]  # la prima colonna è vuota

    out: list[Match] = []
    for row in re.findall(r"<tr>(.*?)</tr>", re.search(r"<tbody>(.*?)</tbody>", table, re.S).group(1), re.S):
        row_head = re.search(r"<th[^>]*>(.*?)</th>", row, re.S)
        if row_head is None:
            continue
        row_team = clean(row_head.group(1))
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        for col_index, cell in enumerate(cells):
            if col_index >= len(columns):
                break
            badge = RE_BADGE.search(cell)
            if badge is None or badge.group(1) != "W":
                continue
            col_team = columns[col_index]
            if col_team == row_team:
                continue
            games = []
            for g in badge.group(2).split(","):
                nums = re.findall(r"\d+", g)
                if len(nums) == 2:
                    games.append(f"{nums[0]}-{nums[1]}")
            out.append(
                Match(
                    event=event,
                    phase=phase,
                    side_a=Team(players=re.split(r"\s*&\s*", row_team)),
                    side_b=Team(players=re.split(r"\s*&\s*", col_team)),
                    score=games,
                    winner="a",
                )
            )
    return out


def snapshot(base_url: str, events: list[str] | None = None,
             fetch: Callable[[str], str] | None = None,
             tournament: str = "") -> Snapshot:
    """Legge tutto il torneo (o i soli eventi filtrati) nel formato comune."""
    fetch = fetch or default_fetch
    chosen = list_events(base_url, fetch)
    if events:
        wanted = [w.lower() for w in events]
        chosen = {i: n for i, n in chosen.items() if any(w in n.lower() for w in wanted)}
    snap = Snapshot(tournament=tournament or base_url.rsplit("/", 1)[-1])
    for event_id, name in chosen.items():
        event_page = fetch(f"{base_url}/results/{event_id}")
        for group_id in sorted(set(re.findall(r"/results/\d+/group/(\d+)", event_page))):
            group_page = fetch(f"{base_url}/results/{event_id}/group/{group_id}")
            snap.matches.extend(group_matches(group_page, name))
        for bracket in ("top", "consolation"):
            if f"/results/{event_id}/knockouts/{bracket}" in event_page:
                ko_page = fetch(f"{base_url}/results/{event_id}/knockouts/{bracket}")
                snap.matches.extend(knockout_matches(ko_page, name, bracket))
    return snap
