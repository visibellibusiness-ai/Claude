"""Ciclo completo: genera → disegna → pubblica → registra nello storico.

Uso:
    python -m bot.main learn     # aggiorna statistiche e, se è ora, la strategia
    python -m bot.main create    # genera e disegna, salva posts/pending.json
    python -m bot.main publish   # pubblica il post in pending.json (richiede i secret)
    aggiungi --series news per la rubrica news quotidiana
"""

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bot import config
from bot.generate import generate_post
from bot.reel import render_reel
from bot.render import render_post, render_story, render_with_templates

ROOT = Path(__file__).resolve().parent.parent
HISTORY = ROOT / "posts" / "history.json"
PENDING = ROOT / "posts" / "pending.json"
QUEUE = ROOT / "posts" / "queue"
STRATEGY = ROOT / "posts" / "strategy.md"
STATE = ROOT / "posts" / "state.json"


def load_history() -> list[dict]:
    return json.loads(HISTORY.read_text()) if HISTORY.exists() else []


def load_state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {"followers_log": []}


def learn() -> None:
    from bot.learn import reflect, should_reflect, update_metrics

    history, state = load_history(), load_state()
    snapshot = update_metrics(history)
    state["followers_log"].append(snapshot)
    HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=2))
    print(f"Statistiche aggiornate. Follower: {snapshot['followers']}")
    if should_reflect(state, history):
        strategy = STRATEGY.read_text() if STRATEGY.exists() else ""
        STRATEGY.write_text(reflect(history, strategy, state["followers_log"]) + "\n")
        state["last_reflection"] = snapshot["date"]
        print("Strategia aggiornata in posts/strategy.md")
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def build_caption(post: dict) -> str:
    tags = " ".join("#" + t.lstrip("#").replace(" ", "") for t in post["hashtags"])
    return f"{post['caption']}\n\n{tags}"


def load_templates() -> dict:
    """I template PSD in templates/, se ci sono: altrimenti si usa lo stile Mystery."""
    try:
        from bot.template import available

        return available()
    except Exception as e:  # un template illeggibile non deve fermare la pubblicazione
        print(f"Template non utilizzabili, uso lo stile predefinito: {e}")
        return {}


def _preset(rel: str | None, credit: str | None) -> dict | None:
    """Foto già scelta e salvata nel repo (percorso relativo alla radice, per esempio
    posts/queue/foto.jpg): in quel caso non si cerca niente online."""
    if rel and (ROOT / rel).exists():
        return {"path": str(ROOT / rel), "credit": credit}
    return None


def attach_images(post: dict, out_dir: Path) -> None:
    """Un'immagine per copertina e slide (foto con licenza libera o generata) e crediti in caption."""
    from bot.images import credits_line, get_image

    out_dir.mkdir(parents=True, exist_ok=True)
    space = post.get("category", "").lower() in ("space", "spazio")
    cover = _preset(post.get("cover_image"), post.get("cover_credit")) or get_image(post.get("image_query", ""), post.get("image_prompt", ""), post["hook"], out_dir / "img_cover.jpg", space)
    if cover:
        post["cover_image"], post["cover_credit"] = cover["path"], cover["credit"]
    results = [cover]
    for i, s in enumerate(post["slides"], start=1):
        r = _preset(s.get("image"), s.get("credit")) or get_image(s.get("image_query", ""), s.get("image_prompt", ""), f"{s['title']}. {s['body']}", out_dir / f"img_{i:02d}.jpg", space)
        if r:
            s["image"], s["credit"] = r["path"], r["credit"]
        results.append(r)
    # dichiarazione AI: vale per il post se almeno un'immagine è generata, per la Story se lo è la copertina
    post["ai_generated"] = any(r and r.get("generated") for r in results)
    post["cover_ai_generated"] = bool(cover and cover.get("generated"))
    line = credits_line(results)
    if line:
        post["caption"] = f"{post['caption']}\n\n{line}"


def pending_path(series: str) -> Path:
    # ogni serie ha il suo post in attesa: le news vecchie non bloccano le curiosità
    return PENDING if series == "facts" else ROOT / "posts" / f"pending_{series}.json"


def create(post_file: str | None, series: str = "facts") -> None:
    pending = pending_path(series)
    if pending.exists():
        age = datetime.now(timezone.utc) - datetime.strptime(json.loads(pending.read_text())["date"], "%Y%m%d-%H%M").replace(tzinfo=timezone.utc)
        if series == "news" and age > timedelta(hours=12):
            print("Rubrica news in attesa da troppo tempo: la sostituisco con quella di oggi")
            pending.unlink()
        else:
            print(f"C'è già un post in attesa ({pending.name}): lo pubblico invece di crearne uno nuovo")
            return

    history = load_history()
    n = len(history)
    strategy = STRATEGY.read_text() if STRATEGY.exists() else ""

    queued = sorted(QUEUE.glob("*.json")) if QUEUE.exists() and series == "facts" else []
    if post_file:
        post = json.loads(Path(post_file).read_text())
    elif series == "news":
        from bot.news import generate_news

        post = generate_news(history)
    elif queued:
        # i post messi a mano in posts/queue/ hanno la precedenza
        post = json.loads(queued[0].read_text())
        queued[0].unlink()
    else:
        post = generate_post(history, strategy)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    rel_dir = Path("posts") / stamp
    out_dir = ROOT / rel_dir
    fmt = "news" if series == "news" else post.get("format", "carousel")
    templates = load_templates()
    if templates:
        attach_images(post, out_dir)
    elif config.COVER_ART and post.get("image_prompt") and not post.get("cover_image"):
        try:
            from bot.imagegen import generate

            art = out_dir / "cover_art.jpg"
            print("Immagine di copertina:", generate(post["image_prompt"], art))
            post["cover_image"] = str(art)
            post["ai_generated"] = post["cover_ai_generated"] = True
        except Exception as e:  # senza immagine il post esce con la copertina tipografica
            print(f"Immagine di copertina non generata: {e}")
    if fmt == "reel":
        render_reel(post, out_dir, theme_index=n)
        paths = [out_dir / "cover.jpg"]
    else:
        paths = render_with_templates(post, out_dir, templates) if templates else render_post(post, out_dir, theme_index=n)
        if fmt == "news":
            # la rubrica esce sia come carosello sia come Reel con le stesse notizie
            render_reel(post, out_dir / "reel", theme_index=n)
    story = None
    try:
        story = render_story(post, out_dir, templates, series)
    except Exception as e:  # la Story è un extra: se non si disegna, il post esce lo stesso
        print(f"Story non disegnata: {e}")
    (out_dir / "post.json").write_text(json.dumps(post, ensure_ascii=False, indent=2))
    caption = build_caption(post)
    pending.write_text(json.dumps({
        "date": stamp,
        "series": series,
        "format": fmt,
        "trial": fmt in ("reel", "news") and post.get("trial", False),
        "music": post.get("music_used"),
        "theme_index": n,
        "topic": post["topic"],
        "category": post.get("category", "?"),
        "hook": post["hook"],
        "slides": len(post["slides"]),
        "design": post.get("design_used") or post.get("design", {}),
        "images": [f"{rel_dir.as_posix()}/{p.name}" for p in paths],
        "story": f"{rel_dir.as_posix()}/{story.name}" if story else None,
        "ai": bool(post.get("ai_generated")),
        "story_ai": bool(post.get("cover_ai_generated")),
        "caption": caption,
    }, ensure_ascii=False, indent=2))
    print(f"Formato: {fmt}\nCategoria: {post.get('category', '?')}\nTopic: {post['topic']}\nSlide: {len(paths)} in {rel_dir}\n\n{caption}")


def _video(pending: dict, sub: str = "") -> Path:
    """Il video non è nel repo: se manca (giro precedente fallito) lo ricrea."""
    out_dir = ROOT / Path(pending["images"][0]).parent
    video = out_dir / sub / "reel.mp4"
    if not video.exists():
        post = json.loads((out_dir / "post.json").read_text())
        render_reel(post, video.parent, theme_index=pending.get("theme_index", 0))
    return video


def _video_url(video: Path) -> str:
    """Indirizzo pubblico del video: con l'accesso Instagram il video non si carica a pezzi,
    lo scarica Instagram. Il workflow lo mette sul branch "media" (VIDEO_BASE_URL)."""
    base = os.environ["VIDEO_BASE_URL"].rstrip("/")
    return f"{base}/{video.relative_to(ROOT).as_posix()}"


def publish(series: str = "facts") -> None:
    from bot.publish import publish_carousel, publish_reel, publish_story

    path = pending_path(series)
    if not path.exists():
        print("Nessun post in attesa")
        return
    pending = json.loads(path.read_text())
    fmt = pending.get("format", "carousel")
    entries = []
    if fmt == "reel":
        media_id, trial = publish_reel(_video_url(_video(pending)), pending["caption"], pending.get("trial", False), pending.get("ai", False))
        entries.append(("reel", media_id, trial))
    else:
        # Le immagini devono essere raggiungibili pubblicamente: il workflow le
        # committa nel repo prima di questo passo (vedi .github/workflows/post.yml).
        base = os.environ["MEDIA_BASE_URL"].rstrip("/")
        urls = [f"{base}/{p}" for p in pending["images"]]
        entries.append(("carousel", publish_carousel(urls, pending["caption"], pending.get("ai", False)), False))
        if fmt == "news":
            try:
                media_id, trial = publish_reel(_video_url(_video(pending, "reel")), pending["caption"], pending.get("trial", False), pending.get("ai", False))
                entries.append(("reel", media_id, trial))
            except Exception as e:  # il carosello è già uscito: non va ripubblicato
                print(f"Reel della rubrica non pubblicato: {e}")

    history = load_history()
    for kind, media_id, trial in entries:
        history.append({
            "date": pending["date"],
            "series": pending.get("series", "facts"),
            "topic": pending["topic"],
            "format": kind,
            "trial": trial,
            "music": pending.get("music") if kind == "reel" else None,
            "category": pending["category"],
            "hook": pending["hook"],
            "slides": pending["slides"],
            "design": pending["design"],
            "media_id": media_id,
        })
        print(f"Pubblicato ({kind}): media_id={media_id}")
    HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=2))
    path.unlink()
    if pending.get("story"):
        # dopo il post e senza mai fermarlo: se la Story non esce, il post c'è già
        try:
            base = os.environ["MEDIA_BASE_URL"].rstrip("/")
            story_id = publish_story(f"{base}/{pending['story']}", pending.get("story_ai", False))
            print(f"Pubblicata Story: media_id={story_id}")
        except Exception as e:
            print(f"Story non pubblicata: {e}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["learn", "create", "publish"])
    parser.add_argument("--post-file", help="usa un JSON già pronto invece di chiamare Claude")
    parser.add_argument("--series", choices=["facts", "news"], default="facts", help="curiosità o rubrica news")
    args = parser.parse_args()
    if args.command == "learn":
        learn()
    elif args.command == "create":
        create(args.post_file, args.series)
    else:
        publish(args.series)


if __name__ == "__main__":
    main()
