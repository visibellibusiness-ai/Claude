"""Ciclo completo: genera → disegna → pubblica → registra nello storico.

Uso:
  python -m bot.main learn       # aggiorna statistiche e, se è ora, la strategia
  python -m bot.main create      # genera e disegna, salva posts/pending.json
  python -m bot.main publish     # pubblica il post in pending.json (richiede i secret)
"""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from bot.generate import generate_post
from bot.reel import render_reel
from bot.render import render_post

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


def create(post_file: str | None) -> None:
    history = load_history()
    n = len(history)
    strategy = STRATEGY.read_text() if STRATEGY.exists() else ""

    queued = sorted(QUEUE.glob("*.json")) if QUEUE.exists() else []
    if post_file:
        post = json.loads(Path(post_file).read_text())
    elif queued:
        # i post messi a mano in posts/queue/ hanno la precedenza
        post = json.loads(queued[0].read_text())
        queued[0].unlink()
    else:
        post = generate_post(history, strategy)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    rel_dir = Path("posts") / stamp
    out_dir = ROOT / rel_dir
    fmt = post.get("format", "carousel")
    if fmt == "reel":
        render_reel(post, out_dir, theme_index=n)
        paths = [out_dir / "cover.jpg"]
    else:
        paths = render_post(post, out_dir, theme_index=n)
    (out_dir / "post.json").write_text(json.dumps(post, ensure_ascii=False, indent=2))
    caption = build_caption(post)
    PENDING.write_text(json.dumps({
        "date": stamp,
        "format": fmt,
        "trial": fmt == "reel" and post.get("trial", False),
        "theme_index": n,
        "topic": post["topic"],
        "category": post.get("category", "?"),
        "hook": post["hook"],
        "slides": len(post["slides"]),
        "design": post.get("design_used") or post.get("design", {}),
        "images": [f"{rel_dir.as_posix()}/{p.name}" for p in paths],
        "caption": caption,
    }, ensure_ascii=False, indent=2))
    print(f"Formato: {fmt}\nCategoria: {post.get('category', '?')}\nTopic: {post['topic']}\nSlide: {len(paths)} in {rel_dir}\n\n{caption}")


def publish() -> None:
    from bot.publish import publish_carousel, publish_reel

    pending = json.loads(PENDING.read_text())
    fmt = pending.get("format", "carousel")
    trial = False
    if fmt == "reel":
        # il video non è nel repo: se manca (giro precedente fallito) lo ricrea
        out_dir = ROOT / Path(pending["images"][0]).parent
        video = out_dir / "reel.mp4"
        if not video.exists():
            post = json.loads((out_dir / "post.json").read_text())
            render_reel(post, out_dir, theme_index=pending.get("theme_index", 0))
        media_id, trial = publish_reel(video, pending["caption"], pending.get("trial", False))
    else:
        # Le immagini devono essere raggiungibili pubblicamente: il workflow le
        # committa nel repo prima di questo passo (vedi .github/workflows/post.yml).
        base = os.environ["MEDIA_BASE_URL"].rstrip("/")
        urls = [f"{base}/{path}" for path in pending["images"]]
        media_id = publish_carousel(urls, pending["caption"])

    history = load_history()
    history.append({
        "date": pending["date"],
        "topic": pending["topic"],
        "format": fmt,
        "trial": trial,
        "category": pending["category"],
        "hook": pending["hook"],
        "slides": pending["slides"],
        "design": pending["design"],
        "media_id": media_id,
    })
    HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=2))
    PENDING.unlink()
    print(f"Pubblicato: media_id={media_id}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["learn", "create", "publish"])
    parser.add_argument("--post-file", help="usa un JSON già pronto invece di chiamare Claude")
    args = parser.parse_args()
    if args.command == "learn":
        learn()
    elif args.command == "create":
        create(args.post_file)
    else:
        publish()


if __name__ == "__main__":
    main()
