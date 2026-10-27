"""Pubblica caroselli e Reel con l'API Instagram con Instagram Login (graph.instagram.com).

Non serve una Pagina Facebook: il token è un token utente Instagram, valido 60 giorni e
rinnovato da .github/workflows/rinnovo-token.yml. Immagini e video devono avere un
indirizzo pubblico: è Instagram a scaricarli (vedi MEDIA_BASE_URL e VIDEO_BASE_URL
in .github/workflows/post.yml).
"""

import json
import os
import time

import requests

GRAPH = "https://graph.instagram.com/v26.0"


def _post(path: str, **params) -> dict:
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    r = requests.post(f"{GRAPH}/{path}", data=params, timeout=60)
    if not r.ok:
        raise RuntimeError(f"Errore Graph API {r.status_code}: {r.text}")
    return r.json()


def _create(user_id: str, ai: bool, **params) -> dict:
    """Crea il container. Con ai=True dichiara che il contenuto è stato creato con l'AI
    (is_ai_generated). Se Instagram rifiuta il container si riprova senza dichiarazione, come
    prima, ma con un avviso ben visibile nel log del giro."""
    if ai:
        try:
            return _post(f"{user_id}/media", is_ai_generated="true", **params)
        except RuntimeError as e:
            print(f"::warning::Container con dichiarazione AI non accettato, riprovo senza dichiarazione: {e}")
    return _post(f"{user_id}/media", **params)


def _wait_ready(container_id: str, timeout: int = 600) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = requests.get(
            f"{GRAPH}/{container_id}",
            params={"fields": "status_code", "access_token": os.environ["IG_ACCESS_TOKEN"]},
            timeout=30,
        )
        status = r.json().get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError(f"Container {container_id} in errore: {r.text}")
        time.sleep(5)
    raise TimeoutError(f"Container {container_id} non pronto dopo {timeout}s")


def publish_carousel(image_urls: list[str], caption: str, ai: bool = False) -> str:
    user_id = os.environ["IG_USER_ID"]
    children = []
    for url in image_urls:
        child = _post(f"{user_id}/media", image_url=url, is_carousel_item="true")
        children.append(child["id"])
    for child in children:
        _wait_ready(child)
    # la dichiarazione AI non è ammessa sui singoli elementi: va sul carosello intero
    carousel = _create(
        user_id,
        ai,
        media_type="CAROUSEL",
        children=",".join(children),
        caption=caption,
    )
    _wait_ready(carousel["id"])
    result = _post(f"{user_id}/media_publish", creation_id=carousel["id"])
    return result["id"]


def publish_reel(video_url: str, caption: str, trial: bool, ai: bool = False) -> tuple[str, bool]:
    """Pubblica un Reel dal suo indirizzo pubblico. Con trial=True è un Trial Reel: lo vede
    prima solo chi non ti segue e Instagram lo condivide con i follower se va bene."""
    user_id = os.environ["IG_USER_ID"]
    params = {"media_type": "REELS", "video_url": video_url, "caption": caption}
    if trial:
        params["trial_params"] = json.dumps({"graduation_strategy": "SS_PERFORMANCE"})
    else:
        params["share_to_feed"] = "true"
    try:
        container = _create(user_id, ai, **params)
    except RuntimeError as e:
        if not trial:
            raise
        print(f"Trial Reel non disponibile, pubblico come Reel normale: {e}")
        params.pop("trial_params")
        params["share_to_feed"] = "true"
        trial = False
        container = _create(user_id, ai, **params)
    _wait_ready(container["id"])
    result = _post(f"{user_id}/media_publish", creation_id=container["id"])
    return result["id"], trial


def publish_story(image_url: str, ai: bool = False) -> str:
    """Story con una sola immagine 9:16 (dura 24 ore). Via API non si possono mettere
    link, adesivi o musica: solo l'immagine."""
    user_id = os.environ["IG_USER_ID"]
    container = _create(user_id, ai, media_type="STORIES", image_url=image_url)
    _wait_ready(container["id"])
    return _post(f"{user_id}/media_publish", creation_id=container["id"])["id"]
