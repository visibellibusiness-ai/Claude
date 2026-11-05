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
    tbd: bool = False       # squadre ancora da definire: conta per la completezza della
                            # fase, esclusa dalle grafiche

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
    # nome completo -> cognome ufficiale della piattaforma (se la piattaforma lo espone)
    surnames: dict[str, str] = field(default_factory=dict)

    def by_event(self) -> dict[str, list[Match]]:
        out: dict[str, list[Match]] = {}
        for m in self.matches:
            out.setdefault(m.event, []).append(m)
        return out

    def event_closed(self, event: str) -> bool:
        """Un tabellone è chiuso quando la sua finale ha un vincitore."""
        finals = [m for m in self.matches if m.event == event and m.phase == "finale"]
        return bool(finals) and all(m.finished for m in finals)

    def phase_complete(self, event: str, phase: str) -> bool:
        """Una fase è completa quando tutte le sue partite (anche quelle con squadre
        ancora da definire) hanno un vincitore."""
        phase_matches = [m for m in self.matches if m.event == event and m.phase == phase]
        return bool(phase_matches) and all(m.finished for m in phase_matches)


def new_finished(previous_keys: set[str], snapshot: Snapshot) -> list[Match]:
    """Le partite finite che al giro precedente erano assenti o senza vincitore."""
    return [m for m in snapshot.matches if m.finished and m.key() not in previous_keys]


PARTICLES = {"de", "del", "della", "di", "da", "dos", "das", "do", "van", "von", "der", "den",
             "la", "le", "el", "al", "bin", "ter", "ten"}


def surname(full_name: str, known: dict[str, str] | None = None,
            overrides: dict[str, str] | None = None) -> str:
    """Cognome da mostrare nelle grafiche, in ordine di fiducia:
    1) eccezioni scritte nel config del torneo (`cognomi`);
    2) cognome ufficiale della piattaforma (es. il ticker PPA: "A. Waters");
    3) regola di ripiego: l'ultima parola, con le particelle davanti (van, de, del...).
       Misurata sui Worlds: i nomi di 3 parole sono quasi sempre nome composto asiatico o
       secondo nome (Chao Yi Wang, Hong Kit Wong, Anna Leigh Waters); i doppi cognomi spagnoli
       (Martinez Vich) arrivano dal cognome ufficiale o dalle eccezioni.
    """
    for source in (overrides or {}, known or {}):
        if source.get(full_name):
            return source[full_name]
    parts = full_name.split()
    if len(parts) <= 1:
        return full_name
    i = len(parts) - 1
    while i > 1 and parts[i - 1].lower() in PARTICLES:
        i -= 1
    return " ".join(parts[i:])


def needs_review(full_name: str, known: dict[str, str] | None = None,
                 overrides: dict[str, str] | None = None) -> bool:
    """Nomi con 3 o più parole senza cognome ufficiale né eccezione: da far controllare."""
    if (overrides or {}).get(full_name) or (known or {}).get(full_name):
        return False
    return len(full_name.split()) >= 3
