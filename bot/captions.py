"""Didascalia del carosello: il testo di ogni slide, ciascuno con i crediti della sua foto."""

# Instagram accetta 2200 caratteri: si resta un po' sotto per sicurezza
LIMIT = 2150


def slide_body(data: dict) -> str:
    """Il testo che la slide mostra sotto il titolo (lo stesso del disegno, vedi render._slide_texts)."""
    if data.get("points"):
        # sulle slide con foto bastano le prime due frasi (cosa e perché): il resto va nel Reel
        return " ".join(txt for _, txt in data["points"][:2])
    return data["body"]


def _first_sentence(text: str) -> str:
    for end in (". ", "! ", "? "):
        if end in text:
            return text.split(end)[0] + end.strip()
    return text


def _photo_line(credit: str | None, generated: bool, compact: bool) -> str:
    if credit:
        # in forma breve si toglie solo l'archivio ("via wikimedia"): autore e licenza restano
        return "📷 " + (credit.rsplit(" via ", 1)[0] if compact else credit)
    return "🎨 AI-generated image" if generated else ""


def _blocks(post: dict, compact: bool, first_sentence: bool) -> list[str]:
    total = len(post["slides"])
    blocks = []
    cover = [f"Cover: {post['hook']}", _photo_line(post.get("cover_credit"), post.get("cover_generated", False), compact)]
    blocks.append("\n".join(line for line in cover if line))
    for n, s in enumerate(post["slides"], start=1):
        head = f"{n}/{total} {s['title']}" + (f" ({s['highlight']})" if s.get("highlight") else "")
        body = slide_body(s)
        lines = [head, _first_sentence(body) if first_sentence else body, _photo_line(s.get("credit"), s.get("generated", False), compact)]
        blocks.append("\n".join(line for line in lines if line))
    return blocks


def build(post: dict, tags: str, limit: int = LIMIT) -> str | None:
    """Didascalia del carosello: introduzione, poi per ogni slide il suo testo e la sua foto, poi gli hashtag.
    Se non sta nel limite si accorcia a gradini: crediti senza archivio, introduzione ridotta, una sola frase
    per slide. Restituisce None se nemmeno così ci sta (si usa allora la didascalia di prima)."""
    intro_lines = post.get("caption_plain", post["caption"]).strip().split("\n")
    attempts = [(False, 0, False), (True, 0, False)]
    attempts += [(True, d, False) for d in range(1, len(intro_lines))]
    attempts += [(True, max(len(intro_lines) - 1, 0), True)]
    for compact, drop, first_sentence in attempts:
        lines = list(intro_lines)
        for _ in range(drop):
            while lines and not lines[0].strip():
                lines.pop(0)
            if lines:
                lines.pop(0)
        intro = "\n".join(lines).strip()
        parts = ([intro] if intro else []) + ["\n\n".join(_blocks(post, compact, first_sentence))] + [tags]
        caption = "\n\n".join(parts)
        if len(caption) <= limit:
            return caption
    return None


def per_slide(post: dict) -> list[str]:
    """Una didascalia per ogni immagine del carosello (copertina, slide, ultima slide), con il testo
    della slide e il credito della sua foto. Serve alle "didascalie multiple" di Instagram."""
    total = len(post["slides"])
    cover = [post["hook"], _photo_line(post.get("cover_credit"), post.get("cover_generated", False), False)]
    out = ["\n".join(line for line in cover if line)]
    for n, s in enumerate(post["slides"], start=1):
        head = f"{n}/{total} {s['title']}" + (f" ({s['highlight']})" if s.get("highlight") else "")
        lines = [head, slide_body(s), _photo_line(s.get("credit"), s.get("generated", False), False)]
        out.append("\n".join(line for line in lines if line))
    out.append(post["cta"])
    return out
