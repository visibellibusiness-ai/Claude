"""Pubblica un carosello tramite Instagram Graph API (Content Publishing)."""

import os
import time

import requests

GRAPH = "https://graph.facebook.com/v21.0"


def _post(path: str, **params) -> dict:
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    r = requests.post(f"{GRAPH}/{path}", data=params, timeout=60)
    if not r.ok:
        raise RuntimeError(f"Errore Graph API {r.status_code}: {r.text}")
    return r.json()


def _wait_ready(container_id: str, timeout: int = 300) -> None:
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


def publish_carousel(image_urls: list[str], caption: str) -> str:
    user_id = os.environ["IG_USER_ID"]
    children = []
    for url in image_urls:
        child = _post(f"{user_id}/media", image_url=url, is_carousel_item="true")
        children.append(child["id"])
    for child in children:
        _wait_ready(child)
    carousel = _post(
        f"{user_id}/media",
        media_type="CAROUSEL",
        children=",".join(children),
        caption=caption,
    )
    _wait_ready(carousel["id"])
    result = _post(f"{user_id}/media_publish", creation_id=carousel["id"])
    return result["id"]
