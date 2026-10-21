"""Motore grafico: stili di marca per slide di carosello e scene dei Reel.

Ogni stile disegna una slide come due livelli: lo sfondo (decorazioni, può
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


def fit(text, make_font, max_w, max_h, start, minimum, leading=1.0):
    """Font più grande con cui il testo sta nel box. make_font(size) -> font."""
    size = start
    while True:
        f = make_font(size)
        lines = wrap(text, f, max_w)
        probe = ImageDraw.Draw(Image.new("L", (1, 1)))
        too_wide = any(probe.textlength(l, font=f) > max_w for l in lines)
        if (len(lines) * size * leading <= max_h and not too_wide) or size <= minimum:
            return f, lines, size
        size -= 3


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


# ------------------------------------------------------------------ stili

class Style:
    name = "base"

    def __init__(self, palette: int, seed: int):
        self.palette = palette
        self.seed = seed

    def accent(self, kind) -> str:
        """Colore per dettagli come la barra di avanzamento dei Reel."""
        raise NotImplementedError

    def slide(self, kind, data, w, h, safe):
        bg = self.background(kind, data, w, h, safe)
        fg = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        getattr(self, kind)(bg, fg, data, w, h, safe)
        return bg, fg


class Riso(Style):
    """Zine stampata in risograph: carta, due inchiostri sovrapposti, retino, fuori registro."""

    name = "riso"
    PALETTES = [
        ("blue", "fluo_pink", "#F3EEE4"),
        ("teal", "orange", "#F1ECE2"),
        ("purple", "yellow", "#F4EFE6"),
        ("red", "blue", "#F2EEE6"),
        ("green", "fluo_pink", "#F3EFE5"),
    ]

    def accent(self, kind):
        return RISO["black"] if kind == "cta" else self.inks()[0]

    def inks(self):
        a, b, p = self.PALETTES[self.palette % len(self.PALETTES)]
        return RISO[a], RISO[b], p

    def background(self, kind, data, w, h, safe):
        a, b, p = self.inks()
        img = paper(w, h, p if kind != "cta" else "#FFFFFF", self.seed)
        rng = random.Random(self.seed + data.get("n", 0))
        if kind == "cta":
            img = overprint(img, Image.new("L", (w, h), 255), b)
        # il retino sta negli angoli, lontano dal testo lungo
        if kind == "cover":
            cx, cy, rad = w * rng.uniform(0.7, 0.9), h * rng.uniform(0.18, 0.3), w * rng.uniform(0.42, 0.55)
        elif kind == "fact":
            cx, cy, rad = w * rng.uniform(0.85, 1.0), h * rng.uniform(0.95, 1.05), w * rng.uniform(0.4, 0.5)
        else:
            cx, cy, rad = w * rng.uniform(0.9, 1.05), h * rng.uniform(-0.05, 0.05), w * rng.uniform(0.45, 0.55)

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
        mono = font("SpaceMono-Bold", 26)
        d.text((l, t), "DID YOU KNOW?", font=mono, fill=color)
        d.text((r, t), f"FACT FILE Nº {data.get('index', 1):04d}", font=mono, fill=color, anchor="ra")
        d.line([l, t + 44, r, t + 44], fill=color, width=3)

    def cover(self, bg, fg, data, w, h, safe):
        a, b, _ = self.inks()
        l, t, r, btm = safe
        d = ImageDraw.Draw(fg)
        self._masthead(d, data, safe, a)
        d.text((l, t + 74), data.get("label", "").upper(), font=font("SpaceMono-Regular", 30), fill=a)
        f, lines, size = fit(data["hook"].upper(), lambda s: font("Anton-Regular", s), r - l, (btm - t) * 0.62, 220, 90, 0.98)
        y = t + 150 + ((btm - t) * 0.62 - len(lines) * size * 0.98) / 2
        # passaggio "fuori registro" del titolo nel secondo inchiostro
        shadow = Image.new("L", (w, h), 0)
        text_block(ImageDraw.Draw(shadow), (l + 9, y + 7), lines, f, size, 255, 0.98)
        bg.paste(overprint(bg, shadow, b), (0, 0))
        text_block(d, (l, y), lines, f, size, a, 0.98)
        tag = rotated_label(data.get("swipe", "SWIPE") + " →", font("SpaceMono-Bold", 34), RISO["black"], RISO["yellow"], 6)
        fg.alpha_composite(tag, (int(r - tag.width), int(btm - tag.height)))

    def fact(self, bg, fg, data, w, h, safe):
        a, b, _ = self.inks()
        l, t, r, btm = safe
        d = ImageDraw.Draw(fg)
        self._masthead(d, data, safe, a)
        d.text((l, t + 74), f"{data['n']:02d} / {data['total']:02d}", font=font("SpaceMono-Regular", 30), fill=a)
        y = t + 140
        hl = data.get("highlight", "").strip()
        if hl:
            hf, hlines, hs = fit(hl.upper(), lambda s: font("Anton-Regular", s), r - l, (btm - t) * 0.34, 330, 120, 0.95)
            mask = Image.new("L", (w, h), 0)
            text_block(ImageDraw.Draw(mask), (l, y), hlines, hf, hs, 255, 0.95)
            bg.paste(overprint(bg, mask, b, roughness=0.05, seed=self.seed + data["n"]), (0, 0))
            y += int(len(hlines) * hs * 0.95) + 70
        else:
            y += 40
        tf, tl, ts = fit(data["title"].upper(), lambda s: font("Anton-Regular", s), r - l, 300, 110, 60, 1.0)
        y = text_block(d, (l, y), tl, tf, ts, a, 1.0) + 26
        scribble_line(d, [(l, y), (l + 220, y + 4)], b, 8, self.seed + data["n"])
        bf, bl, bs = fit(data["body"], lambda s: font("Archivo", s, weight=500), r - l, btm - y - 60, 52, 32, 1.32)
        text_block(d, (l, y + 40), bl, bf, bs, RISO["black"], 1.32)

    def cta(self, bg, fg, data, w, h, safe):
        a, b, _ = self.inks()
        l, t, r, btm = safe
        d = ImageDraw.Draw(fg)
        self._masthead(d, data, safe, RISO["black"])
        f, lines, size = fit(data["cta"].upper(), lambda s: font("Anton-Regular", s), r - l, (btm - t) * 0.55, 170, 70, 1.0)
        y = text_block(d, (l, t + 160), lines, f, size, RISO["black"], 1.0)
        d.text((l, btm - 120), f"FOLLOW {data['handle']}".upper(), font=font("SpaceMono-Bold", 38), fill=RISO["black"])
        d.text((l, btm - 64), data.get("follow_line", ""), font=font("Archivo", 34, weight=500), fill=RISO["black"])


class Museum(Style):
    """Rivista editoriale / scheda da museo: serif elegante, catalogazione, un solo accento."""

    name = "museum"
    PALETTES = [
        ("#F1EBDD", "#161412", "#E2412B"),
        ("#EDEAE2", "#121417", "#2D5BFF"),
        ("#F3EDE0", "#1A1714", "#1F7A4D"),
        ("#151413", "#F2ECE0", "#F2B33D"),
        ("#EFE7D9", "#1B1A17", "#B33A8C"),
    ]

    def colors(self):
        return self.PALETTES[self.palette % len(self.PALETTES)]

    def accent(self, kind):
        p, _, acc = self.colors()
        return p if kind == "cta" else acc

    def background(self, kind, data, w, h, safe):
        p, ink_c, acc = self.colors()
        img = paper(w, h, p if kind != "cta" else acc, self.seed, grain=7)
        d = ImageDraw.Draw(img)
        l, t, r, btm = safe
        line_c = ink_c if kind != "cta" else p
        # segni di taglio negli angoli e griglia puntinata leggera
        for (x, y, sx, sy) in [(40, 40, 1, 1), (w - 40, 40, -1, 1), (40, h - 40, 1, -1), (w - 40, h - 40, -1, -1)]:
            d.line([x, y, x + 40 * sx, y], fill=line_c, width=2)
            d.line([x, y, x, y + 40 * sy], fill=line_c, width=2)
        if kind == "fact":
            for gx in range(l, r + 1, 48):
                for gy in range(int(h * 0.12), int(h * 0.88), 48):
                    d.point((gx, gy), fill=line_c)
        return grain_overlay(img, self.seed, 4)

    def _header(self, d, data, safe, color, right):
        l, t, r, _ = safe
        mono = font("SpaceMono-Regular", 24)
        d.text((l, t), "DID YOU KNOW? — FIELD NOTES", font=mono, fill=color)
        d.text((r, t), right, font=mono, fill=color, anchor="ra")
        d.line([l, t + 40, r, t + 40], fill=color, width=2)

    def cover(self, bg, fg, data, w, h, safe):
        p, ink_c, acc = self.colors()
        l, t, r, btm = safe
        d = ImageDraw.Draw(fg)
        self._header(d, data, safe, ink_c, f"Nº {data.get('index', 1):03d}")
        d.text((l, t + 80), data.get("label", "").upper(), font=font("SpaceMono-Bold", 28), fill=acc)
        f, lines, size = fit(data["hook"], lambda s: font("InstrumentSerif-Regular", s), r - l, (btm - t) * 0.6, 200, 80, 0.92)
        y = btm - 190 - len(lines) * size * 0.92
        last = len(lines) - 1
        for i, line in enumerate(lines):
            # l'ultima riga in corsivo e colore d'accento: il tocco editoriale
            ff = font("InstrumentSerif-Italic", size) if i == last else f
            d.text((l, y), line, font=ff, fill=acc if i == last else ink_c)
            y += int(size * 0.92)
        d.line([l, btm - 110, r, btm - 110], fill=ink_c, width=2)
        d.text((l, btm - 80), data.get("swipe", "Swipe") + "  →", font=font("SpaceMono-Bold", 30), fill=ink_c)
        d.text((r, btm - 80), data.get("category", "").upper(), font=font("SpaceMono-Regular", 26), fill=ink_c, anchor="ra")

    def fact(self, bg, fg, data, w, h, safe):
        p, ink_c, acc = self.colors()
        l, t, r, btm = safe
        d = ImageDraw.Draw(fg)
        self._header(d, data, safe, ink_c, f"{data['n']:02d} / {data['total']:02d}")
        y = t + 90
        hl = data.get("highlight", "").strip()
        if hl:
            hf, hlines, hs = fit(hl, lambda s: font("InstrumentSerif-Italic", s), r - l, (btm - t) * 0.34, 340, 120, 0.9)
            y = text_block(d, (l - 6, y), hlines, hf, hs, acc, 0.9) + 20
        tf, tl, ts = fit(data["title"], lambda s: font("InstrumentSerif-Regular", s), r - l, 280, 104, 56, 0.98)
        y = text_block(d, (l, y), tl, tf, ts, ink_c, 0.98) + 30
        d.line([l, y, l + 120, y], fill=acc, width=5)
        bf, bl, bs = fit(data["body"], lambda s: font("Archivo", s, weight=450, width=96), r - l, btm - y - 60, 50, 32, 1.36)
        text_block(d, (l, y + 40), bl, bf, bs, ink_c, 1.36)

    def cta(self, bg, fg, data, w, h, safe):
        p, ink_c, acc = self.colors()
        l, t, r, btm = safe
        d = ImageDraw.Draw(fg)
        self._header(d, data, safe, p, "END OF FILE")
        f, lines, size = fit(data["cta"], lambda s: font("InstrumentSerif-Regular", s), r - l, (btm - t) * 0.6, 170, 70, 0.95)
        text_block(d, (l, t + 140), lines, f, size, p, 0.95)
        d.line([l, btm - 150, r, btm - 150], fill=p, width=2)
        d.text((l, btm - 120), f"Follow {data['handle']}", font=font("SpaceMono-Bold", 36), fill=p)
        d.text((l, btm - 66), data.get("follow_line", ""), font=font("InstrumentSerif-Italic", 40), fill=p)


class Tabloid(Style):
    """Tabloid ad alto contrasto: nero, giallo acido, nastro che scorre, titoli enormi."""

    name = "tabloid"
    PALETTES = [
        ("#0D0D0D", "#F4F1EA", "#E6FF2E"),
        ("#0D0D0D", "#F4F1EA", "#FF5C38"),
        ("#101014", "#F4F1EA", "#7CF3FF"),
        ("#E6FF2E", "#0D0D0D", "#0D0D0D"),
        ("#0D0D0D", "#F4F1EA", "#FF4FD8"),
    ]

    def colors(self):
        return self.PALETTES[self.palette % len(self.PALETTES)]

    def accent(self, kind):
        bgc, _, acc = self.colors()
        return bgc if kind == "cta" else acc

    def background(self, kind, data, w, h, safe):
        bgc, txt, acc = self.colors()
        if kind == "cta":
            bgc, txt = acc, bgc
        img = paper(w, h, bgc, self.seed, grain=5, fibers=False)
        if kind != "cta":
            # nastro inclinato con la scritta ripetuta, in alto (decorativo)
            tape = Image.new("RGBA", (w * 2, 92), acc)
            td = ImageDraw.Draw(tape)
            f = font("BricolageGrotesque", 44, weight=800, width=75)
            x = 0
            while x < w * 2:
                td.text((x, 18), "DID YOU KNOW? / ", font=f, fill=bgc)
                x += int(td.textlength("DID YOU KNOW? / ", font=f))
            tape = tape.rotate(-4 if kind == "cover" else 3, expand=True, resample=Image.BICUBIC)
            img.paste(tape, (-w // 2, int(safe[1] * 0.25) - 20), tape)
        return grain_overlay(img, self.seed, 5)

    def cover(self, bg, fg, data, w, h, safe):
        bgc, txt, acc = self.colors()
        l, t, r, btm = safe
        d = ImageDraw.Draw(fg)
        d.ellipse([l, t + 100, l + 22, t + 122], fill=acc)
        d.text((l + 38, t + 90), data.get("label", "").upper(), font=font("SpaceMono-Bold", 30), fill=acc)
        f, lines, size = fit(data["hook"].upper(), lambda s: font("BricolageGrotesque", s, weight=800, width=75), r - l, (btm - t) * 0.66, 210, 80, 0.9)
        y = t + 160
        for i, line in enumerate(lines):
            if i == len(lines) - 1:
                tw = d.textlength(line, font=f)
                d.rectangle([l - 10, y + size * 0.08, l + tw + 14, y + size * 0.98], fill=acc)
                d.text((l, y), line, font=f, fill=bgc)
            else:
                d.text((l, y), line, font=f, fill=txt)
            y += int(size * 0.9)
        d.text((l, btm - 50), data.get("swipe", "SWIPE").upper() + " →", font=font("SpaceMono-Bold", 32), fill=txt)

    def fact(self, bg, fg, data, w, h, safe):
        bgc, txt, acc = self.colors()
        l, t, r, btm = safe
        d = ImageDraw.Draw(fg)
        d.text((l, t + 90), f"#{data['n']:02d}", font=font("SpaceMono-Bold", 30), fill=acc)
        d.text((r, t + 90), f"{data['n']}/{data['total']}", font=font("SpaceMono-Regular", 30), fill=txt, anchor="ra")
        y = t + 150
        hl = data.get("highlight", "").strip()
        if hl:
            hf, hlines, hs = fit(hl.upper(), lambda s: font("BricolageGrotesque", s, weight=800, width=75), r - l, (btm - t) * 0.36, 360, 120, 0.88)
            y = text_block(d, (l, y), hlines, hf, hs, acc, 0.88) + 24
        tf, tl, ts = fit(data["title"].upper(), lambda s: font("BricolageGrotesque", s, weight=800, width=80), r - l, 280, 96, 54, 0.95)
        y = text_block(d, (l, y), tl, tf, ts, txt, 0.95) + 34
        bf, bl, bs = fit(data["body"], lambda s: font("Archivo", s, weight=500), r - l, btm - y - 50, 50, 32, 1.34)
        text_block(d, (l, y), bl, bf, bs, txt, 1.34)

    def cta(self, bg, fg, data, w, h, safe):
        bgc, txt, acc = self.colors()
        l, t, r, btm = safe
        d = ImageDraw.Draw(fg)
        f, lines, size = fit(data["cta"].upper(), lambda s: font("BricolageGrotesque", s, weight=800, width=75), r - l, (btm - t) * 0.6, 190, 70, 0.9)
        text_block(d, (l, t + 120), lines, f, size, bgc, 0.9)
        d.text((l, btm - 120), f"FOLLOW {data['handle']}".upper(), font=font("SpaceMono-Bold", 38), fill=bgc)
        d.text((l, btm - 64), data.get("follow_line", ""), font=font("Archivo", 34, weight=600), fill=bgc)


STYLES = {s.name: s for s in (Riso, Museum, Tabloid)}


def flatten(bg: Image.Image, fg: Image.Image) -> Image.Image:
    out = bg.convert("RGBA")
    out.alpha_composite(fg)
    return out.convert("RGB")
