"""Formato dati comune dei risultati: ogni adapter di piattaforma restituisce questi oggetti.

Il resto del motore (grafiche, Stories, post, trigger fine tabellone) lavora solo su
questo formato e ignora da quale piattaforma arrivano i dati.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# fasi in ordine di gioco: servono per ordinare le Stories e capire quando un tabellone chiude
PHASES = ["gironi", "trentaduesimi", "sedicesimi", "ottavi", "quarti", "semifinali", "finale"]


@dataclass
class Team:
    """Un lato del campo: 1 nome (singolo) o 2 (doppio)."""

    players: list[str]

    def label(self) -> str:
        return " / ".join(self.players)


@dataclass
class Match:
    """Una partita nel formato comune.

    score: lista di game dal punto di vista di side_a, es. ["11-7", "9-11", "11-5"].
    winner: "a", "b" oppure "" se la partita è ancora da giocare o in corso.
    """

    event: str              # categoria/tabellone, es. "Open doppio misto"
    phase: str              # una delle PHASES (o il nome che usa la piattaforma, normalizzato)
    side_a: Team
    side_b: Team
    score: list[str] = field(default_factory=list)
    winner: str = ""
    match_id: str = ""      # id della piattaforma se c'è, altrimenti derivato dai nomi

    @property
    def finished(self) -> bool:
        return self.winner in ("a", "b")

    def key(self) -> str:
        """Chiave stabile per riconoscere la stessa partita tra uno scraping e l'altro."""
        if self.match_id:
            return f"{self.event}|{self.match_id}"
        names = sorted(self.side_a.players + self.side_b.players)
        return f"{self.event}|{self.phase}|{'|'.join(names)}"


@dataclass
class Snapshot:
    """Lo stato del torneo a un giro di scraping: tutte le partite di tutti i tabelloni."""

    tournament: str
    matches: list[Match] = field(default_factory=list)

    def by_event(self) -> dict[str, list[Match]]:
        out: dict[str, list[Match]] = {}
        for m in self.matches:
            out.setdefault(m.event, []).append(m)
        return out

    def event_closed(self, event: str) -> bool:
        """Un tabellone è chiuso quando la sua finale ha un vincitore."""
        finals = [m for m in self.matches if m.event == event and m.phase == "finale"]
        return bool(finals) and all(m.finished for m in finals)


def new_finished(previous_keys: set[str], snapshot: Snapshot) -> list[Match]:
    """Le partite finite che al giro precedente erano assenti o senza vincitore."""
    return [m for m in snapshot.matches if m.finished and m.key() not in previous_keys]
