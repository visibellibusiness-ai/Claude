"""Ciclo completo: genera → disegna → pubblica → registra nello storico.

Uso:
  python -m bot.main create      # genera e disegna, salva posts/pending.json
  python -m bot.main publish     # pubblica il post in pending.json (richiede i secret)
"""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from bot import config
from bot.generate import generate_post
from bot.render import render_post

ROOT = Path(__file__).resolve().parent.parent
HISTORY = ROOT / "posts" / "history.json"
PENDING = ROOT / "posts" / "pending.json"
QUEUE = ROOT / "posts" / "queue"


def load_history() -> list[dict]:
    return json.loads(HISTORY.read_text()) if HISTORY.exists() else []


def build_caption(post: dict) -> str:
    tags = " ".join("#" + t.lstrip("#").replace(" ", "") for t in post["hashtags"])
    return f"{post['caption']}\n\n{tags}"


def create(post_file: str | None) -> None:
    history = load_history()
    n = len(history)
    category = config.CATEGORIES[n % len(config.CATEGORIES)]

    queued = sorted(QUEUE.glob("*.json")) if QUEUE.exists() else []
    if post_file:
        post = json.loads(Path(post_file).read_text())
    elif queued:
        # i post messi a mano in posts/queue/ hanno la precedenza
        post = json.loads(queued[0].read_text())
        queued[0].unlink()
    else:
        post = generate_post(category, [h["topic"] for h in history])

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    rel_dir = Path("posts") / stamp
    out_dir = ROOT / rel_dir
    paths = render_post(post, out_dir, theme_index=n)
    (out_dir / "post.json").write_text(json.dumps(post, ensure_ascii=False, indent=2))
    caption = build_caption(post)
    PENDING.write_text(json.dumps({
        "date": stamp,
        "topic": post["topic"],
        "category": category,
        "images": [f"{rel_dir.as_posix()}/{p.name}" for p in paths],
        "caption": caption,
    }, ensure_ascii=False, indent=2))
    print(f"Categoria: {category}\nTopic: {post['topic']}\nSlide: {len(paths)} in {rel_dir}\n\n{caption}")


def publish() -> None:
    from bot.publish import publish_carousel

    pending = json.loads(PENDING.read_text())
    # Le immagini devono essere raggiungibili pubblicamente: il workflow le
    # committa nel repo prima di questo passo (vedi .github/workflows/post.yml).
    base = os.environ["MEDIA_BASE_URL"].rstrip("/")
    urls = [f"{base}/{path}" for path in pending["images"]]
    media_id = publish_carousel(urls, pending["caption"])

    history = load_history()
    history.append({
        "date": pending["date"],
        "topic": pending["topic"],
        "category": pending["category"],
        "media_id": media_id,
    })
    HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=2))
    PENDING.unlink()
    print(f"Pubblicato: media_id={media_id}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["create", "publish"])
    parser.add_argument("--post-file", help="usa un JSON già pronto invece di chiamare Claude")
    args = parser.parse_args()
    if args.command == "create":
        create(args.post_file)
    else:
        publish()


if __name__ == "__main__":
    main()
