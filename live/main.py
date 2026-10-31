"""Il giro del tool risultati live: scraping -> confronto con lo stato -> grafiche -> coda.

Due comandi, come il bot di @you.didnot.know (prima si generano e si committano le
immagini, che devono stare a un indirizzo pubblico, poi si pubblica):

  python -m live.main run       scraping, grafiche nuove in posts/live/, stato aggiornato
  python -m live.main publish   pubblica su Instagram le Story in coda (bot/publish.py)

Configurazione del torneo in live/torneo.json:
  adapter, base_url, tournament, slug, events (filtro nomi, [] = tutti),
  match_stories (fasi con una Story per partita finita),
  phase_stories (fasi con la Story riassuntiva quando la fase si chiude),
  handles (mappa "Nome Cognome" -> "@handle" per i tag).
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from live import render
from live.adapters import get_adapter
from live.model import new_finished

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "live" / "torneo.json"
STATE_DIR = ROOT / "live" / "state"
OUT_DIR = ROOT / "posts" / "live"


def load_config() -> dict:
    return json.loads(CONFIG.read_text())


def state_path(slug: str) -> Path:
    return STATE_DIR / f"{slug}.json"


def load_state(slug: str) -> dict:
    path = state_path(slug)
    if path.exists():
        return json.loads(path.read_text())
    return {"published_matches": [], "published_phases": [], "queue": []}


def save_state(slug: str, state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state_path(slug).write_text(json.dumps(state, indent=1, ensure_ascii=False))


def run() -> None:
    config = load_config()
    slug = config["slug"]
    adapter = get_adapter(config["adapter"])
    snap = adapter.snapshot(
        config["base_url"],
        events=config.get("events") or None,
        tournament=config["tournament"],
    )
    print(f"Snapshot: {len(snap.matches)} partite" )

    state = load_state(slug)
    published = set(state["published_matches"])
    done_phases = set(state["published_phases"])
    handles = config.get("handles", {})

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    out = OUT_DIR / slug / stamp
    queue: list[str] = []

    def enqueue(img, name: str) -> None:
        out.mkdir(parents=True, exist_ok=True)
        path = out / name
        img.save(path)
        queue.append(str(path.relative_to(ROOT)))
        print(f"  Story pronta: {path.relative_to(ROOT)}")

    # 1. una Story per ogni partita appena finita delle fasi scelte
    match_phases = config.get("match_stories", [])
    for i, match in enumerate(new_finished(published, snap)):
        if match.tbd or match.phase not in match_phases:
            continue
        enqueue(render.story_match(match, config["tournament"], handles),
                f"match-{i:03d}-{match.phase.replace(' ', '_')}.png")
        published.add(match.key())

    # 2. la Story riassuntiva quando una fase si chiude (spezzata se serve: leggibilità)
    phase_phases = config.get("phase_stories", [])
    for event, matches in snap.by_event().items():
        for phase in phase_phases:
            key = f"{event}|{phase}"
            if key in done_phases or not snap.phase_complete(event, phase):
                continue
            rows = [m for m in matches if m.phase == phase and m.finished and not m.tbd]
            if not rows:
                continue
            # spezzata in parti bilanciate (6 partite -> 3+3, non 5+1): leggibilità prima di tutto
            n_parts = -(-len(rows) // render.MAX_ROWS)
            size = -(-len(rows) // n_parts)
            chunks = [rows[i:i + size] for i in range(0, len(rows), size)]
            event_slug = re.sub(r"[^a-z0-9]+", "-", event.lower()).strip("-")[:40]
            for n, chunk in enumerate(chunks, start=1):
                enqueue(render.story_phase(event, phase, chunk, config["tournament"],
                                           part=(n, len(chunks))),
                        f"fase-{event_slug}-{phase.replace(' ', '_')}-{n}.png")
            done_phases.add(key)

    state["published_matches"] = sorted(published)
    state["published_phases"] = sorted(done_phases)
    state["queue"] = state.get("queue", []) + queue
    save_state(slug, state)
    print(f"In coda per la pubblicazione: {len(queue)} Story (totale coda: {len(state['queue'])})")


def publish() -> None:
    from bot.publish import publish_story

    config = load_config()
    slug = config["slug"]
    state = load_state(slug)
    base = os.environ["MEDIA_BASE_URL"].rstrip("/")
    remaining: list[str] = []
    for rel in state.get("queue", []):
        url = f"{base}/{rel}"
        try:
            media_id = publish_story(url, ai=True)
            print(f"Story pubblicata: {rel} -> {media_id}")
        except Exception as e:  # la coda resta: si riprova al giro dopo
            print(f"::warning::Story rimasta in coda ({rel}): {e}")
            remaining.append(rel)
    state["queue"] = remaining
    save_state(slug, state)


def main() -> None:
    command = sys.argv[1] if len(sys.argv) > 1 else "run"
    if command == "run":
        run()
    elif command == "publish":
        publish()
    else:
        raise SystemExit(f"Comando sconosciuto: {command}")


if __name__ == "__main__":
    main()
