"""Motore grafico: stile di marca "Mystery" per slide di carosello e scene dei Reel.

Scuro e cinematografico, in coppia con la musica "mystery": fondo quasi nero con
una luce soffusa e grana da pellicola, titoli serif chiari, un solo colore
d'accento, etichette da "fascicolo". Prima di tutto la leggibilità: contrasto
alto e una scala tipografica fissa.

Lo stile disegna una slide come due livelli: lo sfondo (può uscire dalla zona
sicura) e il primo piano con tutto il testo (sempre dentro `safe`), così il
Reel può animare il testo sopra uno sfondo fermo.
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from bot import config

FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"


# ---------------------------------------------------------------- font

_cache: dict = {}


def font(name: str, size: int, **axes) -> ImageFont.FreeTypeFont:
    key = (name, size, tuple(sorted(axes.items())))
    if key not in _cache:
        f = ImageFont.truetype(str(FONTS / f"{name}.ttf"), size)
        if axes:
            values = []
            for a in f.get_variation_axes():
                values.append(axes.get(a["name"].decode().lower().split()[0], a["default"]))
            f.set_variation_by_axes(values)
        _cache[key] = f
    return _cache[key]


def wrap(text: str, f, max_w: int) -> list[str]:
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    lines, line = [], ""
    for word in text.split():
        cand = f"{line} {word}".strip()
        if probe.textlength(cand, font=f) <= max_w or not line:
            line = cand
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def text_block(draw, xy, lines, f, size, fill, leading=1.0):
    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=f, fill=fill)
        y += int(size * leading)
    return y


def spaced(draw, xy, text, f, fill, tracking=0.12, anchor_right=False):
    """Testo con spaziatura tra le lettere (etichette in maiuscolo)."""
    gap = f.size * tracking
    width = sum(draw.textlength(c, font=f) for c in text) + gap * (len(text) - 1)
    x, y = xy
    if anchor_right:
        x -= width
    for c in text:
        draw.text((x, y), c, font=f, fill=fill)
        x += draw.textlength(c, font=f) + gap
    return width


# ------------------------------------------------------------- sfondo

def _hex(c: str) -> np.ndarray:
    c = c.lstrip("#")
    return np.array([int(c[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


def darkroom(w, h, base, glow, seed, light=(0.25, 0.22)):
    """Fondo scuro con una luce soffusa, vignettatura e grana da pellicola."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    lx, ly = light[0] * w, light[1] * h
    d = np.sqrt(((xx - lx) / w) ** 2 + ((yy - ly) / h) ** 2)
    spot = np.exp(-(d / 0.42) ** 2)
    vign = np.clip(1 - 0.55 * (np.sqrt(((xx - w / 2) / w) ** 2 + ((yy - h / 2) / h) ** 2) / 0.7) ** 2, 0, 1)
    img = _hex(base)[None, None, :] + (_hex(glow) - _hex(base))[None, None, :] * (0.16 * spot)[..., None]
    img *= (0.75 + 0.25 * vign)[..., None]
    img += rng.normal(0, 5.5, (h, w))[..., None]
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


# ----------------------------------------------------------- tipografia

# Scala tipografica (px riferiti a una colonna di testo larga 900px).
# Ogni ruolo ha pochi gradini: per ogni post si sceglie UN gradino per ruolo,
# il più grande in cui stanno tutti i testi di quel ruolo, e lo si usa su
# tutte le slide. Così le grandezze restano coerenti.
TYPE_SCALE = {
    "hook": [210, 184, 160, 140],
    "highlight": [300, 256, 220],
    "title": [124, 108, 94],
    "body": [54, 50, 46],
    "cta": [150, 130, 114],
}
LABEL, META, FOLLOW, TAGLINE = 28, 32, 40, 36
LEADING = {"hook": 1.0, "highlight": 0.95, "title": 1.02, "body": 1.38, "cta": 1.02}
MAX_LINES = {"hook": 5, "highlight": 1, "title": 2, "cta": 5}
POINT_GAP = {"label": 10, "between": 28}
GAP = {"after_meta": 60, "after_highlight": 36, "rule": 34, "after_rule": 40}


def _serif(s):
    return font("InstrumentSerif-Regular", s)


def _serif_italic(s):
    return font("InstrumentSerif-Italic", s)


def _body(s):
    return font("Archivo", s, weight=470)


def _mono(s):
    return font("SpaceMono-Regular", s)


FONT_FOR = {"hook": _serif, "highlight": _serif_italic, "title": _serif, "cta": _serif, "body": _body}


class Mystery:
    """Fascicolo notturno: fondo scuro, serif chiaro, un accento caldo o freddo."""

    name = "mystery"
    # (fondo, luce, testo, testo secondario, accento)
    PALETTES = [
        ("#0B0C10", "#3A3F52", "#F4F0E8", "#DAD5CB", "#E6B65C"),  # ambra
        ("#091014", "#28434A", "#F0F5F4", "#D0DADA", "#6FD6C9"),  # acqua
        ("#100D14", "#43324F", "#F6F0F5", "#DCD2DC", "#D99BCB"),  # orchidea
        ("#0D0D0B", "#3E3A2C", "#F4F2E8", "#DAD7CA", "#D4DB78"),  # lime
        ("#0E0B0B", "#4A2E28", "#F6EFEB", "#DDD2CD", "#EE7A5E"),  # brace
    ]

    def __init__(self, palette: int, seed: int):
        self.palette = palette
        self.seed = seed
        self.sizes: dict = {}
        # spostamento verticale del contenuto delle slide (la testata resta ferma)
        self.content_dy = 0

    def colors(self):
        return self.PALETTES[self.palette % len(self.PALETTES)]

    def accent(self, kind) -> str:
        """Colore per dettagli come la barra di avanzamento dei Reel."""
        return self.colors()[4]

    # ---------------------------------------------------------- tipografia

    def _lines(self, role, text, size, width):
        return wrap(text, FONT_FOR[role](size), width)

    def _fits(self, role, text, size, width, max_lines):
        f = FONT_FOR[role](size)
        lines = self._lines(role, text, size, width)
        probe = ImageDraw.Draw(Image.new("L", (1, 1)))
        return len(lines) <= max_lines and all(probe.textlength(x, font=f) <= width for x in lines)

    def _body_height(self, data, size, width):
        """Altezza del corpo: testo semplice o righe con etichetta (rubrica news)."""
        if data.get("points"):
            return sum(
                META + POINT_GAP["label"] + len(self._lines("body", txt, size, width)) * size * LEADING["body"]
                for _, txt in data["points"]
            ) + POINT_GAP["between"] * (len(data["points"]) - 1)
        return len(self._lines("body", data["body"], size, width)) * size * LEADING["body"]

    def _fact_layout(self, sizes, safe):
        """Posizioni fisse delle slide di contenuto, uguali per tutto il post."""
        l, t, r, btm = safe
        y_meta = t + 70 + self.content_dy
        y_hl = y_meta + META + GAP["after_meta"]
        y_title = y_hl + int(sizes["highlight"] * LEADING["highlight"]) + GAP["after_highlight"]
        return y_meta, y_hl, y_title

    def plan(self, scenes, safe, boost=1.0):
        """Sceglie un gradino per ruolo valido per tutte le scene del post.
        boost ingrandisce tutta la scala (per i Reel, visti a tutto schermo)."""
        l, t, r, btm = safe
        width = r - l
        k = width / 900 * boost
        steps = {role: [int(v * k) for v in vals] for role, vals in TYPE_SCALE.items()}
        texts = {role: [] for role in TYPE_SCALE}
        for kind, data in scenes:
            if kind == "cover":
                texts["hook"].append(data["hook"])
            elif kind == "fact":
                texts["title"].append(data["title"])
                texts["body"].append(data)
                texts["highlight"].append(data.get("highlight") or f"{data['n']:02d}")
            else:
                texts["cta"].append(data["cta"])

        def first_fit(role, ok):
            for size in steps[role]:
                if all(ok(size, txt) for txt in texts[role]):
                    return size
            return steps[role][-1]

        # altezza disponibile per titolo di copertina e chiusura (vedi cover() e cta())
        room = {
            "hook": (btm - 170) - (t + 70 + META) - 40,
            "cta": (btm - 170) - (t + 70 + META + GAP["after_meta"]),
        }

        def ok(role, s, txt):
            if not self._fits(role, txt, s, width, MAX_LINES[role]):
                return False
            if role in room:
                return len(self._lines(role, txt, s, width)) * s * LEADING[role] <= room[role]
            return True

        sizes = {}
        for role in ("hook", "highlight", "title", "cta"):
            sizes[role] = first_fit(role, lambda s, txt, role=role: ok(role, s, txt))

        def body_fits(s, data):
            _, _, y_title = self._fact_layout(sizes, safe)
            y_body = y_title + 2 * sizes["title"] * LEADING["title"] + GAP["rule"] + GAP["after_rule"]
            return self._body_height(data, s, width) <= btm - y_body

        # se il testo non sta, si scende prima col corpo, poi col numero in evidenza,
        # infine col titolo: sempre per tutte le slide insieme
        def settle():
            for title in [x for x in steps["title"] if x <= sizes["title"]]:
                sizes["title"] = title
                for hl in [x for x in steps["highlight"] if x <= sizes["highlight"]]:
                    sizes["highlight"] = hl
                    sizes["body"] = first_fit("body", body_fits)
                    if all(body_fits(sizes["body"], data) for data in texts["body"]):
                        return

        settle()
        self.sizes = sizes
        return sizes

    # ------------------------------------------------------------ disegno

    def slide(self, kind, data, w, h, safe):
        base, glow, *_ = self.colors()
        light = {"cover": (0.3, 0.3), "fact": (0.2, 0.25), "cta": (0.7, 0.35)}[kind]
        bg = darkroom(w, h, base, glow, self.seed + data.get("n", 0), light)
        fg = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        getattr(self, kind)(fg, data, safe)
        return bg, fg

    def _masthead(self, d, data, safe):
        _, _, text, muted, acc = self.colors()
        l, t, r, _ = safe
        spaced(d, (l, t), config.PAGE_NAME.upper(), _mono(LABEL), muted)
        spaced(d, (r, t), f"CASE Nº {data.get('index', 1):04d}", _mono(LABEL), acc, anchor_right=True)
        d.line([l, t + 44, r, t + 44], fill=muted + "55", width=2)

    def cover(self, fg, data, safe):
        _, _, text, muted, acc = self.colors()
        l, t, r, btm = safe
        d = ImageDraw.Draw(fg)
        self._masthead(d, data, safe)
        spaced(d, (l, t + 70), data.get("label", "").upper(), _mono(META), acc)
        size = self.sizes["hook"]
        lines = self._lines("hook", data["hook"], size, r - l)
        block = len(lines) * size * LEADING["hook"]
        y = t + 70 + META + (btm - 170 - (t + 70 + META) - block) / 2
        # l'ultima riga in corsivo e nel colore d'accento: la "rivelazione"
        for i, line in enumerate(lines):
            last = i == len(lines) - 1
            d.text((l, y), line, font=_serif_italic(size) if last else _serif(size), fill=acc if last else text)
            y += int(size * LEADING["hook"])
        d.line([l, btm - 18, l + 80, btm - 18], fill=acc, width=3)
        spaced(d, (l + 104, btm - 34), data.get("swipe", "Swipe").upper() + "  →", _mono(META), text)

    def fact(self, fg, data, safe):
        _, _, text, muted, acc = self.colors()
        l, t, r, btm = safe
        sz = self.sizes
        d = ImageDraw.Draw(fg)
        self._masthead(d, data, safe)
        y_meta, y_hl, y_title = self._fact_layout(sz, safe)
        spaced(d, (l, y_meta), f"FILE {data['n']:02d} / {data['total']:02d}", _mono(META), muted)
        if data.get("label"):
            spaced(d, (r, y_meta), data["label"], _mono(META), acc, anchor_right=True)
        # zona del numero in evidenza: sempre presente (se manca, il numero della slide)
        hl = (data.get("highlight") or "").strip() or f"{data['n']:02d}"
        hf = _serif_italic(sz["highlight"])
        top_pad = d.textbbox((0, 0), "H", font=hf)[1]
        d.text((l - 4, y_hl - top_pad), hl, font=hf, fill=acc)
        tl = self._lines("title", data["title"], sz["title"], r - l)
        y = text_block(d, (l, y_title), tl, _serif(sz["title"]), sz["title"], text, LEADING["title"]) + GAP["rule"]
        d.line([l, y, l + 80, y], fill=acc, width=3)
        y += GAP["after_rule"]
        if data.get("points"):
            # rubrica news: etichetta piccola + una frase, per ogni punto
            for label, txt in data["points"]:
                spaced(d, (l, y), label, _mono(META), acc)
                y += META + POINT_GAP["label"]
                bl = self._lines("body", txt, sz["body"], r - l)
                y = text_block(d, (l, y), bl, _body(sz["body"]), sz["body"], text, LEADING["body"]) + POINT_GAP["between"]
        else:
            bl = self._lines("body", data["body"], sz["body"], r - l)
            text_block(d, (l, y), bl, _body(sz["body"]), sz["body"], muted, LEADING["body"])

    def cta(self, fg, data, safe):
        _, _, text, muted, acc = self.colors()
        l, t, r, btm = safe
        d = ImageDraw.Draw(fg)
        self._masthead(d, data, safe)
        size = self.sizes["cta"]
        lines = self._lines("cta", data["cta"], size, r - l)
        y = t + 70 + META + GAP["after_meta"]
        for i, line in enumerate(lines):
            last = i == len(lines) - 1
            d.text((l, y), line, font=_serif_italic(size) if last else _serif(size), fill=acc if last else text)
            y += int(size * LEADING["cta"])
        d.line([l, btm - 140, l + 80, btm - 140], fill=acc, width=3)
        spaced(d, (l, btm - 110), f"FOLLOW {data['handle']}".upper(), _mono(FOLLOW), text, tracking=0.06)
        d.text((l, btm - 58), data.get("follow_line", ""), font=_body(TAGLINE), fill=muted)


STYLES = {s.name: s for s in (Mystery,)}


def flatten(bg: Image.Image, fg: Image.Image) -> Image.Image:
    out = bg.convert("RGBA")
    out.alpha_composite(fg)
    return out.convert("RGB")
