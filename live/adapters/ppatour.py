"""Adapter PPA Tour (ppatour.com, ppatour.com Europe e PPA Challenger): JSON pubblico dei punteggi.

Il sito del tour legge i risultati da un endpoint JSON senza chiavi:
- {site}/api/scores/?event={id}   tutte le partite di tutte le categorie, con stato e game

Uso: snapshot(base_url, events=None, fetch=None, tournament="") -> Snapshot
base_url: "https://www.ppatour.com/api/scores/?event=<uuid evento>"
  (l'uuid si legge nella pagina dell'evento, campo eventId; vale anche per
  europe.ppatour.com e per i Challenger). Sull'evento Worlds 2026:
  ad262b1f-ea62-4dcc-af59-69732a97107c
events: filtro sui nomi categoria (sottostringhe, case-insensitive); None = tutte.
fetch: funzione url -> testo JSON, sostituibile nei test con i dati salvati.
"""

from __future__ import annotations

import json
from collections.abc import Callable

from live.model import Match, Snapshot, Team

# etichetta del round sul sito PPA -> fase del formato comune
PHASE_MAP = {
    "round 128": "sessantaquattresimi",
    "round 64": "trentaduesimi",
    "round 32": "sedicesimi",
    "round 16": "ottavi",
    "quarter finals": "quarti",
    "quarterfinals": "quarti",
    "semi finals": "semifinali",
    "semifinals": "semifinali",
    "final": "finale",
    "finals": "finale",
    "gold medal match": "finale",
    "bronze medal match": "terzo posto",
    "bronze": "terzo posto",
    "third place": "terzo posto",
}


def default_fetch(url: str) -> str:
    import requests

    r = requests.get(url, timeout=40, headers={"User-Agent": "Mozilla/5.0 (PickleballSpot live)"})
    r.raise_for_status()
    return r.text


def _score(team_a: dict, team_b: dict) -> list[str]:
    """Game dal punto di vista di side_a. Il sito riempie i game non giocati con 0 o null."""
    out = []
    for a, b in zip(team_a.get("games", []), team_b.get("games", [])):
        if a is None or b is None or (a == 0 and b == 0):
            continue
        out.append(f"{a}-{b}")
    return out


def to_matches(data: dict, events: list[str] | None = None) -> list[Match]:
    wanted = [w.lower() for w in events] if events else None
    out: list[Match] = []
    for m in data.get("matches", []):
        division = m.get("division", "")
        if wanted and not any(w in division.lower() for w in wanted):
            continue
        teams = m.get("teams", [])
        if len(teams) != 2:
            continue
        a, b = teams
        names_a = [n for n in a.get("players", []) if n]
        names_b = [n for n in b.get("players", []) if n]
        tbd = not names_a or not names_b or any(
            n.upper() in ("BYE", "TBD", "PENDING") for n in names_a + names_b)
        if tbd:
            names_a = names_a or ["TBD"]
            names_b = names_b or ["TBD"]
        winner = ""
        if m.get("status") == "final" and not tbd:
            winner = "a" if a.get("winner") else "b" if b.get("winner") else ""
        label = m.get("roundLabel", "").strip().lower()
        out.append(
            Match(
                event=division,
                phase=PHASE_MAP.get(label, label),
                side_a=Team(players=names_a),
                side_b=Team(players=names_b),
                score=[] if tbd else _score(a, b),
                winner=winner,
                match_id=str(m.get("id", "")),
                tbd=tbd,
            )
        )
    return out


def snapshot(base_url: str, events: list[str] | None = None,
             fetch: Callable[[str], str] | None = None,
             tournament: str = "") -> Snapshot:
    fetch = fetch or default_fetch
    data = json.loads(fetch(base_url))
    return Snapshot(tournament=tournament or data.get("tournamentId", ""),
                    matches=to_matches(data, events))
