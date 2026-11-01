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
        state = json.loads(path.read_text())
    else:
        state = {}
    state.setdefault("published_matches", [])
    state.setdefault("published_phases", [])
    state.setdefault("published_posts", [])
    # le voci vecchie della coda erano stringhe (solo Story): si normalizzano
    state["queue"] = [q if isinstance(q, dict) else {"tipo": "story", "file": q}
                      for q in state.get("queue", [])]
    return state


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
    queue: list[dict] = []

    def save_img(img, name: str) -> str:
        out.mkdir(parents=True, exist_ok=True)
        path = out / name
        img.save(path)
        return str(path.relative_to(ROOT))

    def enqueue(img, name: str) -> None:
        rel = save_img(img, name)
        queue.append({"tipo": "story", "file": rel})
        print(f"  Story pronta: {rel}")

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

    # 3. post celebrativo: tabellone chiuso + foto del vincitore arrivata
    #    (live/foto/<slug evento>.jpg|png, la passa Andrea o il gestore)
    import re as _re
    for event, matches in snap.by_event().items():
        if event in state["published_posts"] or not snap.event_closed(event):
            continue
        event_slug = _re.sub(r"[^a-z0-9]+", "-", event.lower()).strip("-")[:40]
        photo = next((p for ext in ("jpg", "jpeg", "png")
                      for p in [ROOT / "live" / "foto" / f"{event_slug}.{ext}"] if p.exists()), None)
        if photo is None:
            print(f"  Tabellone chiuso, in attesa della foto: live/foto/{event_slug}.jpg -> post {event}")
            continue
        from live import render_post
        rows = [m for m in matches if m.finished and not m.tbd and not m.phase.startswith("gironi")
                and not m.phase.startswith("consolation")]
        phases = [p for p in ["trentaduesimi", "sedicesimi", "ottavi", "quarti", "semifinali", "finale"]
                  if any(m.phase == p for m in rows)]
        slides = render_post.build_carousel(photo, event, config["tournament"], rows, phases)
        files = [save_img(s, f"post-{event_slug}-{n:02d}.png") for n, s in enumerate(slides, start=1)]
        final = next(m for m in rows if m.phase == "finale")
        winners = (final.side_a if final.winner == "a" else final.side_b).players
        tags = " ".join(handles.get(p, "") for p in winners).strip()
        caption = (f"CONGRATS {' & '.join(winners)} 🏆 {event} champions at the {config['tournament']}!"
                   + (f"\n{tags}" if tags else "")
                   + "\n\nThe road to gold, bracket by bracket 👇"
                   + "\n\n#pickleball #pickleballspot")
        queue.append({"tipo": "carousel", "files": files, "caption": caption})
        state["published_posts"].append(event)
        print(f"  Post celebrativo pronto: {event} ({len(files)} slide)")

    state["published_matches"] = sorted(published)
    state["published_phases"] = sorted(done_phases)
    state["queue"] = state.get("queue", []) + queue
    save_state(slug, state)
    print(f"In coda per la pubblicazione: {len(queue)} contenuti (totale coda: {len(state['queue'])})")


def _limite_pubblicazione() -> None:
    """Stampa il contatore ufficiale dell'API (quota sulle 24 ore)."""
    import requests as _rq

    try:
        r = _rq.get(f"https://graph.instagram.com/v26.0/{os.environ['IG_USER_ID']}/content_publishing_limit",
                    params={"fields": "quota_usage,config", "access_token": os.environ["IG_ACCESS_TOKEN"]},
                    timeout=30)
        print(f"content_publishing_limit: HTTP {r.status_code} {r.text[:300]}")
    except Exception as e:
        print(f"content_publishing_limit non leggibile: {e}")


def publish() -> None:
    """Pubblica la coda. Variabili per la modalità prova (test su un altro account):

    LIVE_PROVA=1   la coda resta intatta (lo stato torna utile per l'account vero)
    LIVE_LIMITE=n  pubblica al massimo n contenuti (0 o assente = tutti)
    LIVE_SALTA=n   salta i primi n contenuti della coda
    """
    from bot.publish import publish_carousel, publish_story

    prova = os.environ.get("LIVE_PROVA") == "1"
    limite = int(os.environ.get("LIVE_LIMITE", "0") or 0)
    salta = int(os.environ.get("LIVE_SALTA", "0") or 0)

    config = load_config()
    slug = config["slug"]
    state = load_state(slug)
    base = os.environ["MEDIA_BASE_URL"].rstrip("/")
    _limite_pubblicazione()
    coda = state.get("queue", [])[salta:]
    if limite:
        coda = coda[:limite]
    print(f"Da pubblicare in questo giro: {len(coda)} contenuti (prova: {prova})")
    remaining: list[dict] = []
    for item in coda:
        try:
            if item["tipo"] == "carousel":
                media_id = publish_carousel([f"{base}/{rel}" for rel in item["files"]],
                                            item.get("caption", ""), ai=False)
                print(f"Post pubblicato: {len(item['files'])} slide -> {media_id}")
            else:
                media_id = publish_story(f"{base}/{item['file']}", ai=False)
                print(f"Story pubblicata: {item['file']} -> {media_id}")
        except Exception as e:  # la coda resta: si riprova al giro dopo
            print(f"::warning::Contenuto rimasto in coda ({item}): {e}")
            remaining.append(item)
    _limite_pubblicazione()
    if prova:
        print("Modalità prova: coda e stato lasciati come prima.")
        return
    state["queue"] = state.get("queue", [])[:salta] + remaining + state.get("queue", [])[salta + len(coda):]
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
