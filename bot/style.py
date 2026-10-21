"""Motore grafico: stile di marca "Riso" per slide di carosello e scene dei Reel.

Lo stile disegna una slide come due livelli: lo sfondo (decorazioni, può
uscire dalla zona sicura) e il primo piano (testo, sempre dentro `safe`).
Così il Reel può animare il primo piano sopra uno sfondo fermo.
"""

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"

# Inchiostri risograph reali (nomi dei colori Riso)
RISO = {
    "fluo_pink": "#FF48B0",
    "blue": "#0078BF",
    "yellow": "#FFE800",
    "teal": "#00838A",
    "orange": "#FF6C2F",
    "purple": "#765BA7",
    "red": "#F15060",
    "green": "#00A95C",
    "black": "#1C1C1C",
}


# ---------------------------------------------------------------- font

_cache: dict = {}


def font(name: str, size: int, **axes) -> ImageFont.FreeTypeFont:
    key = (name, size, tuple(sorted(axes.items())))
    if key not in _cache:
        f = ImageFont.truetype(str(FONTS / f"{name}.ttf"), size)
        if axes:
            order = [a["name"].decode().lower() for a in f.get_variation_axes()]
            values = []
            for a, n in zip(f.get_variation_axes(), order):
                values.append(axes.get(n.split()[0], a["default"]))
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


def text_block(draw, xy, lines, f, size, fill, leading=1.0, anchor="la"):
    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=f, fill=fill, anchor=anchor)
        y += int(size * leading)
    return y


# ---------------------------------------------------------- texture/effetti

def paper(w, h, color, seed, grain=10, fibers=True):
    rng = np.random.default_rng(seed)
    base = np.array(Image.new("RGB", (w, h), color), dtype=np.float32)
    noise = rng.normal(0, grain, (h // 2, w // 2)).astype(np.float32)
    noise = np.array(Image.fromarray(noise).resize((w, h), Image.BILINEAR))
    out = base + noise[..., None]
    if fibers:
        blotch = rng.normal(0, 1, (h // 60 + 1, w // 60 + 1)).astype(np.float32)
        blotch = np.array(Image.fromarray(blotch).resize((w, h), Image.BICUBIC)) * 5
        out += blotch[..., None]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def grain_overlay(img: Image.Image, seed: int, amount=12) -> Image.Image:
    rng = np.random.default_rng(seed + 99)
    arr = np.array(img, dtype=np.float32)
    arr += rng.normal(0, amount, arr.shape[:2])[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def ink(mask: Image.Image, color: str, size) -> Image.Image:
    """Strato d'inchiostro: colore pieno dove la maschera è bianca, bianco altrove."""
    layer = Image.new("RGB", size, "white")
    layer.paste(Image.new("RGB", size, color), (0, 0), mask)
    return layer


def overprint(base: Image.Image, mask: Image.Image, color: str, roughness=0.0, seed=0) -> Image.Image:
    """Stampa sovrapposta (multiply), come due passaggi di inchiostro risograph."""
    if roughness:
        rng = np.random.default_rng(seed)
        m = np.array(mask, dtype=np.float32)
        speck = rng.random(m.shape) > roughness
        m = m * speck
        mask = Image.fromarray(m.astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))
    return ImageChops.multiply(base, ink(mask, color, base.size))


def halftone(w, h, value_fn, cell=18, angle=15) -> Image.Image:
    """Maschera a retino: value_fn(x, y) in [0,1] = intensità del punto."""
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)
    span = int(max(w, h) * 1.5)
    for i in range(-span // cell, span // cell):
        for j in range(-span // cell, span // cell):
            u, v = i * cell, j * cell
            x = w / 2 + u * ca - v * sa
            y = h / 2 + u * sa + v * ca
            if -cell < x < w + cell and -cell < y < h + cell:
                val = value_fn(x, y)
                if val > 0.02:
                    r = cell * 0.62 * math.sqrt(val)
                    d.ellipse([x - r, y - r, x + r, y + r], fill=255)
    return mask


def scribble_line(draw, points, fill, width, seed, jitter=3):
    rng = random.Random(seed)
    pts = []
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        steps = max(2, int(math.hypot(x1 - x0, y1 - y0) / 12))
        for s in range(steps):
            t = s / steps
            pts.append((x0 + (x1 - x0) * t + rng.uniform(-jitter, jitter), y0 + (y1 - y0) * t + rng.uniform(-jitter, jitter)))
    pts.append(points[-1])
    draw.line(pts, fill=fill, width=width, joint="curve")


def rotated_label(text, f, fg, bg, angle, pad=(26, 14)):
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    l, t, r, b = probe.textbbox((0, 0), text, font=f)
    w, h = r - l + pad[0] * 2, b - t + pad[1] * 2
    tag = Image.new("RGBA", (w, h), bg)
    ImageDraw.Draw(tag).text((pad[0] - l, pad[1] - t), text, font=f, fill=fg)
    return tag.rotate(angle, expand=True, resample=Image.BICUBIC)


# ------------------------------------------------------------------ stile

# Scala tipografica (px riferiti a una colonna di testo larga 900px).
# Ogni ruolo ha pochi gradini: per ogni post si sceglie UN gradino per ruolo,
# il più grande in cui stanno tutti i testi di quel ruolo, e lo si usa su
# tutte le slide. Così le grandezze restano coerenti.
TYPE_SCALE = {
    "hook": [176, 150, 128, 110],
    "highlight": [280, 236, 200],
    "title": [96, 82, 70],
    "body": [46, 42, 38],
    "cta": [146, 124, 106],
}
MAST, META, TAG, FOLLOW, TAGLINE = 26, 30, 34, 38, 32
LEADING = {"hook": 0.98, "highlight": 0.92, "title": 1.0, "body": 1.34, "cta": 1.0}
MAX_LINES = {"hook": 5, "highlight": 1, "title": 2, "cta": 5}
GAP = {"after_meta": 56, "after_highlight": 34, "underline": 26, "after_underline": 44}


def _hook_font(s):
    return font("Anton-Regular", s)


def _body_font(s):
    return font("Archivo", s, weight=500)


FONT_FOR = {"hook": _hook_font, "highlight": _hook_font, "title": _hook_font, "cta": _hook_font, "body": _body_font}


class Riso:
    """Zine stampata in risograph: carta, due inchiostri sovrapposti, retino, fuori registro."""

    name = "riso"
    PALETTES = [
        ("blue", "fluo_pink", "#F3EEE4"),
        ("teal", "orange", "#F1ECE2"),
        ("purple", "yellow", "#F4EFE6"),
        ("red", "blue", "#F2EEE6"),
        ("green", "fluo_pink", "#F3EFE5"),
    ]

    def __init__(self, palette: int, seed: int):
        self.palette = palette
        self.seed = seed
        self.sizes: dict = {}
        # spostamento verticale del contenuto delle slide (la testata resta ferma)
        self.content_dy = 0

    # ---------------------------------------------------------- tipografia

    @staticmethod
    def _upper(role, text):
        return text if role == "body" else text.upper()

    def _lines(self, role, text, size, width):
        return wrap(self._upper(role, text), FONT_FOR[role](size), width)

    def _fits(self, role, text, size, width, max_lines):
        f = FONT_FOR[role](size)
        lines = self._lines(role, text, size, width)
        probe = ImageDraw.Draw(Image.new("L", (1, 1)))
        return len(lines) <= max_lines and all(probe.textlength(x, font=f) <= width for x in lines)

    def _fact_layout(self, sizes, safe):
        """Posizioni fisse delle slide di contenuto, uguali per tutto il post."""
        l, t, r, btm = safe
        y_meta = t + 74 + self.content_dy
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
                texts["body"].append(data["body"])
                texts["highlight"].append(data.get("highlight") or f"{data['n']:02d}")
            else:
                texts["cta"].append(data["cta"])

        def first_fit(role, ok):
            for size in steps[role]:
                if all(ok(size, txt) for txt in texts[role]):
                    return size
            return steps[role][-1]

        sizes = {}
        for role in ("hook", "highlight", "title", "cta"):
            sizes[role] = first_fit(role, lambda s, txt, role=role: self._fits(role, txt, s, width, MAX_LINES[role]))

        def body_fits(s, txt):
            _, _, y_title = self._fact_layout(sizes, safe)
            y_body = y_title + 2 * sizes["title"] * LEADING["title"] + GAP["underline"] + GAP["after_underline"]
            return len(self._lines("body", txt, s, width)) * s * LEADING["body"] <= btm - y_body

        # se il testo non sta, si scende prima col corpo, poi col numero in evidenza
        for hl in steps["highlight"]:
            if hl > sizes["highlight"]:
                continue
            sizes["highlight"] = hl
            sizes["body"] = first_fit("body", body_fits)
            if body_fits(sizes["body"], max(texts["body"] or [""], key=len)):
                break
        self.sizes = sizes
        return sizes

    # ------------------------------------------------------------ colori

    def inks(self):
        a, b, p = self.PALETTES[self.palette % len(self.PALETTES)]
        return RISO[a], RISO[b], p

    def accent(self, kind):
        """Colore per dettagli come la barra di avanzamento dei Reel."""
        return RISO["black"] if kind == "cta" else self.inks()[0]

    # ------------------------------------------------------------ disegno

    def slide(self, kind, data, w, h, safe):
        bg = self.background(kind, data, w, h, safe)
        fg = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        getattr(self, kind)(bg, fg, data, w, h, safe)
        return bg, fg

    def background(self, kind, data, w, h, safe):
        a, b, p = self.inks()
        img = paper(w, h, p if kind != "cta" else "#FFFFFF", self.seed)
        rng = random.Random(self.seed + data.get("n", 0))
        if kind == "cta":
            img = overprint(img, Image.new("L", (w, h), 255), b)
        # il retino sta negli angoli, lontano dal testo lungo
        if kind == "cover":
            # dietro al titolo, sotto la testata
            cx, cy, rad = w * rng.uniform(0.8, 0.92), h * rng.uniform(0.48, 0.55), w * rng.uniform(0.4, 0.46)
        else:
            # nell'angolo in basso a destra, sotto al testo
            cx, cy, rad = w * rng.uniform(1.0, 1.08), h * rng.uniform(1.02, 1.08), w * rng.uniform(0.34, 0.4)

        def blob(x, y):
            dist = math.hypot(x - cx, y - cy) / rad
            return max(0.0, 1 - dist) ** 0.8

        img = overprint(img, halftone(w, h, blob, cell=22, angle=rng.choice([15, 30, 45])), b if kind != "cta" else a, roughness=0.06, seed=self.seed)
        if kind == "cover":
            band = Image.new("L", (w, h), 0)
            ImageDraw.Draw(band).rectangle([0, safe[3] - 40, w, h], fill=255)
            grad = halftone(w, h, lambda x, y: max(0, (y - (safe[3] - 140)) / (h - safe[3] + 140)), cell=14, angle=45)
            img = overprint(img, ImageChops.multiply(band, grad), a, roughness=0.08, seed=self.seed + 1)
        return grain_overlay(img, self.seed, 6)

    def _masthead(self, d, data, safe, color):
        l, t, r, _ = safe
        mono = font("SpaceMono-Bold", MAST)
        d.text((l, t), "DID YOU KNOW?", font=mono, fill=color)
        d.text((r, t), f"FACT FILE Nº {data.get('index', 1):04d}", font=mono, fill=color, anchor="ra")
        d.line([l, t + 44, r, t + 44], fill=color, width=3)

    def cover(self, bg, fg, data, w, h, safe):
        a, b, _ = self.inks()
        l, t, r, btm = safe
        d = ImageDraw.Draw(fg)
        self._masthead(d, data, safe, a)
        d.text((l, t + 74), data.get("label", "").upper(), font=font("SpaceMono-Regular", META), fill=a)
        size = self.sizes["hook"]
        f = _hook_font(size)
        lines = self._lines("hook", data["hook"], size, r - l)
        block = len(lines) * size * LEADING["hook"]
        y = t + 74 + META + (btm - 120 - (t + 74 + META) - block) / 2
        # passaggio "fuori registro" del titolo nel secondo inchiostro
        shadow = Image.new("L", (w, h), 0)
        off = max(5, size // 20)
        text_block(ImageDraw.Draw(shadow), (l + off, y + off * 0.8), lines, f, size, 255, LEADING["hook"])
        bg.paste(overprint(bg, shadow, b), (0, 0))
        text_block(d, (l, y), lines, f, size, a, LEADING["hook"])
        tag = rotated_label(data.get("swipe", "Swipe").upper() + " →", font("SpaceMono-Bold", TAG), RISO["black"], RISO["yellow"], 6)
        fg.alpha_composite(tag, (int(r - tag.width), int(btm - tag.height)))

    def fact(self, bg, fg, data, w, h, safe):
        a, b, _ = self.inks()
        l, t, r, btm = safe
        sz = self.sizes
        d = ImageDraw.Draw(fg)
        self._masthead(d, data, safe, a)
        y_meta, y_hl, y_title = self._fact_layout(sz, safe)
        d.text((l, y_meta), f"{data['n']:02d} / {data['total']:02d}", font=font("SpaceMono-Regular", META), fill=a)
        # zona del numero in evidenza: sempre presente (se manca, il numero della slide)
        hl = (data.get("highlight") or "").strip() or f"{data['n']:02d}"
        mask = Image.new("L", (w, h), 0)
        md = ImageDraw.Draw(mask)
        hf = _hook_font(sz["highlight"])
        top_pad = md.textbbox((0, 0), "H", font=hf)[1]
        md.text((l, y_hl - top_pad), hl.upper(), font=hf, fill=255)
        bg.paste(overprint(bg, mask, b, roughness=0.05, seed=self.seed + data["n"]), (0, 0))

        tf = _hook_font(sz["title"])
        tl = self._lines("title", data["title"], sz["title"], r - l)
        y = text_block(d, (l, y_title), tl, tf, sz["title"], a, LEADING["title"]) + GAP["underline"]
        scribble_line(d, [(l, y), (l + 220, y + 4)], b, 8, self.seed + data["n"])
        bl = self._lines("body", data["body"], sz["body"], r - l)
        text_block(d, (l, y + GAP["after_underline"]), bl, _body_font(sz["body"]), sz["body"], RISO["black"], LEADING["body"])

    def cta(self, bg, fg, data, w, h, safe):
        l, t, r, btm = safe
        d = ImageDraw.Draw(fg)
        ink_c = RISO["black"]
        self._masthead(d, data, safe, ink_c)
        size = self.sizes["cta"]
        lines = self._lines("cta", data["cta"], size, r - l)
        text_block(d, (l, t + 74 + META + GAP["after_meta"]), lines, _hook_font(size), size, ink_c, LEADING["cta"])
        d.text((l, btm - 110), f"FOLLOW {data['handle']}".upper(), font=font("SpaceMono-Bold", FOLLOW), fill=ink_c)
        d.text((l, btm - 58), data.get("follow_line", ""), font=font("Archivo", TAGLINE, weight=500), fill=ink_c)


STYLES = {s.name: s for s in (Riso,)}


def flatten(bg: Image.Image, fg: Image.Image) -> Image.Image:
    out = bg.convert("RGBA")
    out.alpha_composite(fg)
    return out.convert("RGB")
