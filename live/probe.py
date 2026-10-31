"""Sonda di sola lettura per le piattaforme risultati dei tornei.

Gira su GitHub Actions (rete aperta) perché la sessione cloud di sviluppo ha i domini
esterni bloccati. Scarica le pagine indicate, capisce se il contenuto è nel markup o
renderizzato in JavaScript, cerca gli endpoint API nei bundle e gli eventuali dati
incorporati (JSON embedded, config Firebase), e salva tutto in `probe_out/` che il
workflow carica come artifact. Nei log stampa solo il riassunto.

Uso: python -m live.probe [url ...]   (senza argomenti usa gli URL di default)
"""

import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

DEFAULT_URLS = [
    "https://www.pickleballengland.org/2026-english-nationals/",
    "https://www.pickleballengland.org/tournaments/",
    "https://www.picklebook.org/a/pbe",
    "https://www.picklebook.org/a/pbe/tournaments/uLh76HpTL8lBGyqN/results/16",
]

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")

OUT = Path("probe_out")

# segnali interessanti dentro HTML e bundle JS
RE_ENDPOINT = re.compile(r"""["'](/api/[^"'\s]{2,120}|https?://[^"'\s]{4,160}(?:api|graphql|firestore|firebaseio|functions)[^"'\s]{0,120})["']""", re.I)
RE_FIREBASE = re.compile(r"""(?:projectId|databaseURL|apiKey|authDomain)["']?\s*[:=]\s*["']([^"']{4,120})["']""")
RE_EMBED = re.compile(r"(__NEXT_DATA__|__NUXT__|__INITIAL_STATE__|window\.__[A-Z_]+__)")
RE_LINK = re.compile(r"""href=["']([^"']+)["']""", re.I)
RE_SCRIPT = re.compile(r"""<script[^>]+src=["']([^"']+)["']""", re.I)


def fetch(url: str, session: requests.Session) -> requests.Response | None:
    try:
        r = session.get(url, timeout=40, headers={"User-Agent": UA})
        return r
    except requests.RequestException as e:
        print(f"  ERRORE rete: {e}")
        return None


def save(name: str, content: bytes) -> Path:
    OUT.mkdir(exist_ok=True)
    path = OUT / name
    path.write_bytes(content)
    return path


def safe_name(url: str) -> str:
    p = urlparse(url)
    tail = re.sub(r"[^A-Za-z0-9._-]+", "_", (p.netloc + p.path).strip("/"))[:120]
    return tail or "root"


def inspect_text(label: str, text: str) -> None:
    endpoints = sorted(set(m.group(1) for m in RE_ENDPOINT.finditer(text)))
    if endpoints:
        print(f"  [{label}] endpoint trovati ({len(endpoints)}):")
        for e in endpoints[:30]:
            print(f"    - {e}")
    firebase = sorted(set(RE_FIREBASE.findall(text)))
    if firebase:
        print(f"  [{label}] config Firebase/simili: {firebase[:10]}")
    embeds = sorted(set(RE_EMBED.findall(text)))
    if embeds:
        print(f"  [{label}] dati incorporati: {embeds}")


def probe_page(url: str, session: requests.Session) -> None:
    print(f"\n=== {url}")
    r = fetch(url, session)
    if r is None:
        return
    ctype = r.headers.get("content-type", "?")
    print(f"  HTTP {r.status_code} | {ctype} | {len(r.content)} byte | url finale: {r.url}")
    body = r.text
    saved = save(safe_name(url) + ".html", r.content)
    print(f"  salvato in {saved}")

    title = re.search(r"<title[^>]*>(.*?)</title>", body, re.S | re.I)
    if title:
        print(f"  titolo: {title.group(1).strip()[:120]}")

    # il contenuto è nel markup o arriva via JavaScript?
    visible = re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", body, flags=re.S)
    words = len(visible.split())
    print(f"  testo visibile nel markup: ~{words} parole {'(probabile SPA: serve JS o API)' if words < 150 else ''}")

    inspect_text("pagina", body)

    # link utili (risultati, tabelloni, picklebook)
    links = sorted(set(RE_LINK.findall(body)))
    interesting = [l for l in links if re.search(r"picklebook|result|draw|bracket|tournament|standing", l, re.I)]
    if interesting:
        print(f"  link interessanti ({len(interesting)}):")
        for l in interesting[:40]:
            print(f"    - {urljoin(url, l)}")

    # bundle JavaScript: dentro ci sono gli endpoint delle SPA
    scripts = [urljoin(url, s) for s in RE_SCRIPT.findall(body)]
    own = [s for s in scripts if urlparse(s).netloc == urlparse(r.url).netloc or urlparse(s).netloc == ""]
    for s in own[:6]:
        rb = fetch(s, session)
        if rb is None or rb.status_code != 200:
            continue
        name = safe_name(s) + ".js"
        save(name, rb.content)
        print(f"  bundle: {s} ({len(rb.content)} byte) -> probe_out/{name}")
        inspect_text(Path(urlparse(s).path).name, rb.text)


def main() -> None:
    urls = sys.argv[1:] or DEFAULT_URLS
    session = requests.Session()
    for url in urls:
        probe_page(url, session)
    print("\nFatto: nessun dato scritto fuori da probe_out/, niente pubblicato.")


if __name__ == "__main__":
    main()
