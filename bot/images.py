"""Immagini delle slide: foto con licenza libera trovate online, oppure generate.

Ordine: 1) cerca su archivi con licenze che permettono l'uso commerciale
(Openverse, Wikimedia Commons, NASA, e Pexels/Unsplash se ci sono le chiavi);
2) Claude guarda i candidati e sceglie il più adatto, scartando foto con scritte,
filigrane, volti riconoscibili o bassa qualità; 3) se nessuno va bene, genera
l'immagine con il modello open source (bot/imagegen.py).
Ogni immagine trovata online porta con sé autore, licenza e link: finiscono nei
crediti della caption.

La foto riempie tutta la slide (4:5) e il testo sta nella metà bassa su una sfumatura
scura: il soggetto deve stare nella parte alta, e la foto deve avere abbastanza pixel
per non risultare sfocata dopo l'ingrandimento (vedi MAX_UPSCALE).
"""

import base64
import html
import io
import json
import os
import re
from pathlib import Path

import anthropic
import requests
from PIL import Image

from bot import config

UA = "YouDidNotKnowBot/1.0 (https://github.com/visibellibusiness-ai/Claude)"
TIMEOUT = 25
# licenze accettate: libere, uso commerciale consentito, al massimo con attribuzione
WIKI_OK = re.compile(r"^(cc0|public domain|pd|cc by(-sa)? \d(\.\d)?)", re.I)
# ingrandimento massimo accettato per riempire la slide: oltre, la foto esce sfocata
MAX_UPSCALE = 1.7
# quanti candidati provare prima di passare all'immagine generata
MAX_TRIES = 4


def _get(url, **params):
    r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=TIMEOUT)
    r.raise_for_status()
    return r


def openverse(query: str, n: int = 8) -> list[dict]:
    data = _get("https://api.openverse.org/v1/images/", q=query, license_type="commercial",
                mature="false", page_size=n).json()
    out = []
    for r in data.get("results", []):
        if (r.get("width") or 0) < 800:
            continue
        lic = f"CC {r['license'].upper()} {r.get('license_version') or ''}".strip()
        if r["license"] in ("cc0", "pdm"):
            lic = "CC0 / public domain"
        out.append({
            "provider": "openverse", "url": r["url"], "thumb": r.get("thumbnail") or r["url"],
            "author": r.get("creator") or "unknown", "license": lic,
            "source": r.get("foreign_landing_url") or r["url"], "title": r.get("title") or "",
        })
    return out


def wikimedia(query: str, n: int = 8) -> list[dict]:
    data = _get("https://commons.wikimedia.org/w/api.php", action="query", format="json",
                generator="search", gsrsearch=f"{query} filetype:bitmap", gsrnamespace=6,
                gsrlimit=n, prop="imageinfo", iiprop="url|size|extmetadata", iiurlwidth=1600).json()
    out = []
    for page in (data.get("query", {}).get("pages") or {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        lic = meta.get("LicenseShortName", {}).get("value", "")
        if not WIKI_OK.match(lic) or (info.get("width") or 0) < 800:
            continue
        author = re.sub(r"<[^>]+>", "", html.unescape(meta.get("Artist", {}).get("value", "unknown"))).strip()
        out.append({
            "provider": "wikimedia", "url": info.get("thumburl") or info["url"],
            "thumb": info.get("thumburl") or info["url"], "author": author[:80] or "unknown",
            "license": lic, "source": info.get("descriptionurl", ""), "title": page.get("title", ""),
        })
    return out


def nasa(query: str, n: int = 8) -> list[dict]:
    data = _get("https://images-api.nasa.gov/search", q=query, media_type="image").json()
    out = []
    for item in data.get("collection", {}).get("items", [])[:n]:
        meta, links = item["data"][0], item.get("links") or [{}]
        thumb = links[0].get("href", "")
        if not thumb:
            continue
        out.append({
            "provider": "nasa", "url": thumb.replace("~thumb", "~large"), "thumb": thumb,
            # non tutte le immagini NASA hanno la versione "large": si provano le altre
            "fallback_urls": [thumb.replace("~thumb", "~orig"), thumb.replace("~thumb", "~medium")],
            "author": meta.get("center") and f"NASA/{meta['center']}" or "NASA",
            "license": "public domain (NASA)", "title": meta.get("title", ""),
            "source": f"https://images.nasa.gov/details/{meta.get('nasa_id', '')}",
        })
    return out


def pexels(query: str, n: int = 8) -> list[dict]:
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return []
    r = requests.get("https://api.pexels.com/v1/search", params={"query": query, "per_page": n},
                     headers={"Authorization": key, "User-Agent": UA}, timeout=TIMEOUT)
    r.raise_for_status()
    return [{
        "provider": "pexels", "url": p["src"]["large2x"], "thumb": p["src"]["medium"],
        "author": p.get("photographer", "unknown"), "license": "Pexels license",
        "source": p.get("url", ""), "title": p.get("alt", ""),
    } for p in r.json().get("photos", [])]


def unsplash(query: str, n: int = 8) -> list[dict]:
    key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if not key:
        return []
    r = requests.get("https://api.unsplash.com/search/photos", params={"query": query, "per_page": n},
                     headers={"Authorization": f"Client-ID {key}", "User-Agent": UA}, timeout=TIMEOUT)
    r.raise_for_status()
    # "full" e non "regular" (1080 px di larghezza): serve più risoluzione per riempire la slide
    return [{
        "provider": "unsplash", "url": p["urls"]["full"], "thumb": p["urls"]["small"],
        "author": p["user"]["name"], "license": "Unsplash license",
        "source": p["links"]["html"], "title": p.get("alt_description") or "",
    } for p in r.json().get("results", [])]


PROVIDERS = [pexels, unsplash, openverse, wikimedia, nasa]


def search(query: str, space: bool = False) -> list[dict]:
    providers = [nasa] + [p for p in PROVIDERS if p is not nasa] if space else PROVIDERS
    found = []
    for provider in providers:
        try:
            found += provider(query)
        except Exception as e:  # un archivio irraggiungibile non blocca gli altri
            print(f"Ricerca immagini su {provider.__name__} non riuscita: {e}")
    return found


def _thumb_b64(url: str) -> str | None:
    try:
        img = Image.open(io.BytesIO(_get(url).content)).convert("RGB")
        img.thumbnail((512, 512))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=80)
        return base64.standard_b64encode(buf.getvalue()).decode()
    except Exception:
        return None


PICK_SCHEMA = {
    "type": "object",
    "properties": {
        "index": {"type": "integer", "description": "Number of the best image, or -1 if none is good enough"},
        "reason": {"type": "string"},
    },
    "required": ["index", "reason"],
    "additionalProperties": False,
}


def pick(candidates: list[dict], context: str, limit: int = 8) -> dict | None:
    """Claude guarda le miniature e sceglie quella giusta per la slide."""
    shown, content = [], []
    for c in candidates:
        if len(shown) >= limit:
            break
        b64 = _thumb_b64(c["thumb"])
        if not b64:
            continue
        shown.append(c)
        content += [
            {"type": "text", "text": f"Image {len(shown) - 1}: {c['title'][:120]}"},
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
        ]
    if not shown:
        return None
    content.append({"type": "text", "text": (
        f"Slide content: {context}\n\n"
        "Pick the single best image for this Instagram slide. The photo fills the whole portrait "
        "frame (4:5), and the lower 40% of the frame is covered by a dark gradient and big white "
        "text. So the main subject must sit in the upper 60% of the image, and the bottom part "
        "should be calm (sky, ground, water, dark background) because it will be under the text. "
        "It must clearly show the subject, be sharp and well composed, and still look striking when "
        "cropped to a portrait frame. Prefer clear light-versus-dark contrast. Reject images with "
        "visible text, watermarks, logos, collages, recognizable faces of private people, graphic or "
        "disturbing content, a subject that does not match, a subject that is tiny or sits low in "
        "the frame, or a blurry, noisy or heavily compressed look. Return -1 if none is good enough."
    )})
    response = anthropic.Anthropic().messages.create(
        model=config.MODEL,
        max_tokens=2000,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": PICK_SCHEMA}},
        messages=[{"role": "user", "content": content}],
    )
    if response.stop_reason != "end_turn":
        return None
    choice = json.loads(next(b.text for b in response.content if b.type == "text"))
    i = choice.get("index", -1)
    return shown[i] if 0 <= i < len(shown) else None


def _enough(size: tuple[int, int]) -> bool:
    """Bastano i pixel per riempire la slide senza ingrandire troppo?"""
    return max(config.WIDTH / size[0], config.HEIGHT / size[1]) <= MAX_UPSCALE


def download(c: dict, out: Path) -> Path:
    """Scarica la foto: prova gli indirizzi in ordine e tiene il primo abbastanza grande
    (o, se nessuno lo è, il più grande). Gli archivi non hanno sempre tutte le versioni."""
    best, last_error = None, None
    for url in [c["url"], *c.get("fallback_urls", [])]:
        try:
            img = Image.open(io.BytesIO(_get(url).content)).convert("RGB")
        except Exception as e:
            last_error = e
            continue
        if best is None or img.width * img.height > best.width * best.height:
            best = img
        if _enough(img.size):
            break
    if best is None:
        raise last_error or RuntimeError("download non riuscito")
    out.parent.mkdir(parents=True, exist_ok=True)
    best.save(out, "JPEG", quality=92)
    return out


def sharp_enough(path: Path) -> bool:
    """La foto salvata ha abbastanza pixel per riempire la slide?"""
    with Image.open(path) as img:
        return _enough(img.size)


def get_image(query: str, prompt: str, context: str, out: Path, space: bool = False) -> dict | None:
    """Restituisce {"path", "credit"} oppure None. Per le immagini generate credit è None e generated è True."""
    if query:
        try:
            candidates = search(query, space)
            for _ in range(MAX_TRIES):
                chosen = pick(candidates, context)
                if not chosen:
                    break
                candidates = [c for c in candidates if c is not chosen]
                try:
                    path = download(chosen, out)
                except Exception as e:  # archivio che blocca lo scarico: si passa al prossimo candidato
                    print(f"Scarico non riuscito ({chosen['provider']}: {chosen['title'][:60]}): {e}")
                    continue
                if sharp_enough(path):
                    return {"path": str(path), "credit": f"{chosen['author']} ({chosen['license']}) via {chosen['provider']}",
                            "source": chosen["source"]}
                print(f"Foto troppo piccola per riempire la slide ({chosen['provider']}: {chosen['title'][:60]}): provo un'altra")
        except Exception as e:
            print(f"Immagine online non trovata per '{query}': {e}")
    if prompt and config.COVER_ART:
        try:
            from bot.imagegen import generate

            generate(prompt, out)
            return {"path": str(out), "credit": None, "source": None, "generated": True}
        except Exception as e:
            print(f"Immagine non generata: {e}")
    return None


def credits_line(results: list[dict | None]) -> str:
    """Riga dei crediti per la caption, senza doppioni."""
    seen = []
    for r in results:
        if r and r.get("credit") and r["credit"] not in seen:
            seen.append(r["credit"])
    return ("📷 " + " · ".join(seen)) if seen else ""
