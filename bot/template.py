"""Template Photoshop: la grafica la disegna Andrea, il sistema cambia testi e immagini.

Convenzione (vedi templates/README.md): nei file PSD i livelli da sostituire hanno
nomi fissi, con o senza parentesi graffe ("TITLE" oppure "{{TITLE}}"):
- IMAGE: un rettangolo o un'immagine segnaposto, riempito con la foto della slide;
- TITLE, BODY, HIGHLIGHT, LABEL, NUMBER, HANDLE, CREDIT: livelli di testo. Il testo
  nuovo prende font, dimensione, colore, interlinea e allineamento del livello e si
  riduce da solo se non entra nel riquadro (meglio usare caselle di testo).
- "TITLE box" (opzionale): un rettangolo che definisce a mano il riquadro di un testo.
Tutti gli altri livelli restano esattamente come disegnati.

Impaginazione: i testi grandi (HIGHLIGHT, TITLE, BODY) vicini fra loro nel template
formano una pila ancorata in basso: testi corti non lasciano buchi e la distanza fra i
blocchi resta quella disegnata. Il riquadro del template dice quante righe ci stanno
(altezza della casella diviso interlinea): oltre quel limite il testo si rimpicciolisce.
Se il primo testo di una pila è da solo, TITLE e HIGHLIGHT restano ancorati in basso
nella loro casella e BODY in alto. Con BOTTOM_ALIGN = False tutti i testi partono
dall'alto della casella come prima.
"""

import re
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from psd_tools import PSDImage

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"
FONTS = TEMPLATES / "fonts"
FALLBACK_FONT = ROOT / "assets" / "fonts" / "Archivo.ttf"
SLOTS = {"IMAGE", "TITLE", "BODY", "HIGHLIGHT", "LABEL", "NUMBER", "HANDLE", "CREDIT"}
STACK = ("HIGHLIGHT", "TITLE", "BODY")  # testi che si impilano dal basso
STACK_MAX_GAP = 80  # px: oltre questa distanza fra due caselle i testi non fanno pila
BOTTOM_ALIGN = True


def _slot(name: str) -> tuple[str | None, bool]:
    """Nome del segnaposto e se è un riquadro ("TITLE box")."""
    clean = re.sub(r"[{}]", "", name).strip().upper()
    if clean.endswith(" BOX") and clean[:-4] in SLOTS:
        return clean[:-4], True
    return (clean, False) if clean in SLOTS else (None, False)


@lru_cache(maxsize=None)
def _font_files() -> dict[str, Path]:
    """Font dei template indicizzati per nome PostScript e per nome file."""
    from fontTools.ttLib import TTFont

    index = {}
    for path in list(FONTS.glob("*.ttf")) + list(FONTS.glob("*.otf")):
        index[path.stem.lower().replace(" ", "")] = path
        try:
            names = TTFont(path, lazy=True)["name"]
            ps = names.getDebugName(6)
            if ps:
                index[ps.lower()] = path
        except Exception:
            pass
    return index


def _font(postscript: str | None, size: float) -> ImageFont.FreeTypeFont:
    files = _font_files()
    key = (postscript or "").lower().replace(" ", "")
    path = files.get(key)
    if path is None:
        print(f"Font '{postscript}' non trovato in templates/fonts: uso quello di riserva")
        path = FALLBACK_FONT
    return ImageFont.truetype(str(path), max(8, round(size)))


class TextSlot:
    def __init__(self, layer):
        ts = layer.typesetting
        run = ts.runs[0].style if len(ts.runs) else ts.default_style
        para = ts.paragraphs[0].style if len(ts.paragraphs) else ts.default_paragraph_style
        scale = abs(layer.transform[3]) or 1.0
        self.font_name = run.font.postscript_name if run.font else None
        self.size = run.font_size * scale
        argb = run.fill_color or (1, 0, 0, 0)
        self.color = tuple(round(c * 255) for c in argb[1:4]) + (round(argb[0] * 255),)
        self.leading = (run.leading * scale / self.size) if not run.auto_leading and run.leading else 1.2
        self.tracking = run.tracking / 1000
        self.align = {0: "left", 1: "right", 2: "center"}.get(int(para.justification), "left")
        self.box = self._box(layer)
        self.uppercase = layer.text.isupper()

    @staticmethod
    def _box(layer):
        """Riquadro del testo: casella di testo se c'è, altrimenti l'ingombro del livello."""
        try:
            shapes = layer.engine_dict["Rendered"]["Shapes"]["Children"]
            x0, y0, x1, y1 = [float(v) for v in shapes[0]["Cookie"]["Photoshop"]["BoxBounds"]]
            xx, _, _, yy, tx, ty = layer.transform
            if x1 - x0 > 1 and y1 - y0 > 1:
                return (tx + x0 * xx, ty + y0 * yy, tx + x1 * xx, ty + y1 * yy)
        except Exception:
            pass
        return layer.bbox

    @property
    def capacity(self) -> int:
        """Righe che stanno nella casella alla grandezza disegnata."""
        height = self.box[3] - self.box[1]
        return max(1, int(height * 1.02 // (self.size * self.leading)))

    def layout(self, text: str) -> dict:
        """Righe, grandezza e altezza del testo (si rimpicciolisce se non entra)."""
        if self.uppercase:
            text = text.upper()
        x0, y0, x1, y1 = self.box
        width, height = x1 - x0, y1 - y0
        size = self.size
        while True:
            font = _font(self.font_name, size)
            track = self.tracking * size
            lines = _wrap(text, font, width, track)
            line_h = size * self.leading
            if len(lines) * line_h <= height * 1.02 or size <= self.size * 0.45:
                break
            size *= 0.94
        return {"lines": lines, "font": font, "size": size, "track": track,
                "line_h": line_h, "height": len(lines) * line_h}

    def draw(self, canvas: Image.Image, text: str, top: float | None = None, info: dict | None = None) -> None:
        info = info or self.layout(text)
        x0, y0, x1, y1 = self.box
        width = x1 - x0
        font, track, line_h = info["font"], info["track"], info["line_h"]
        layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        # come in Photoshop: la prima riga ha la cima delle lettere alte sul bordo superiore
        baseline = (y0 if top is None else top) - font.getbbox("Hdl", anchor="ls")[1]
        for line in info["lines"]:
            w = _line_width(d, line, font, track)
            x = x0 if self.align == "left" else (x1 - w if self.align == "right" else x0 + (width - w) / 2)
            if track:
                for ch in line:
                    d.text((x, baseline), ch, font=font, fill=self.color, anchor="ls")
                    x += d.textlength(ch, font=font) + track
            else:
                d.text((x, baseline), line, font=font, fill=self.color, anchor="ls")
            baseline += line_h
        canvas.alpha_composite(layer)


def _line_width(draw, text: str, font, track: float = 0.0) -> float:
    return draw.textlength(text, font=font) + track * len(text)


def _wrap(text: str, font, width: float, track: float = 0.0) -> list[str]:
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    out = []
    for para in text.split("\n"):
        line = ""
        for word in para.split():
            cand = f"{line} {word}".strip()
            if _line_width(probe, cand, font, track) <= width or not line:
                line = cand
            else:
                out.append(line)
                line = word
        out.append(line)
    return out


def _cover_fit(img: Image.Image, w: int, h: int) -> Image.Image:
    scale = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left, top = (img.width - w) // 2, (img.height - h) // 3  # un po' più in alto del centro
    return img.crop((left, top, left + w, top + h))


class PsdTemplate:
    def __init__(self, path: Path):
        self.path = Path(path)
        psd = PSDImage.open(self.path)
        self.size = psd.size
        self.texts: dict[str, TextSlot] = {}
        self.image_box = None
        boxes: dict[str, tuple] = {}
        slots = set()
        for layer in psd.descendants():
            name, is_box = _slot(layer.name)
            if not name:
                continue
            slots.add(id(layer))
            if is_box:
                boxes[name] = layer.bbox
            elif name == "IMAGE":
                self.image_box = layer.bbox
                image_layer = layer
            elif layer.kind == "type":
                self.texts[name] = TextSlot(layer)
        for name, box in boxes.items():
            if name in self.texts:
                self.texts[name].box = box

        # La foto va nello stesso punto della pila del segnaposto: i livelli sotto
        # formano lo sfondo, quelli sopra (sfumature, cornici, loghi) vanno sopra la foto.
        # (si usano gli oggetti livello: gli id dei livelli non sono sempre univoci)
        order = [id(l) for l in psd.descendants() if not l.is_group()]
        cut = order.index(id(image_layer)) if self.image_box else len(order)
        below, above = set(order[:cut]), set(order[cut + 1:])

        def keep(group):
            return lambda l: l.is_visible() and id(l) not in slots and (l.is_group() or id(l) in group)

        self.below = psd.composite(force=True, layer_filter=keep(below)).convert("RGBA")
        self.above = (
            psd.composite(force=True, color=0.0, alpha=0.0, layer_filter=keep(above)).convert("RGBA")
            if above else None
        )

    def render(self, texts: dict[str, str], image: str | Path | None = None) -> Image.Image:
        canvas = self.below.copy()
        if self.image_box and image:
            x0, y0, x1, y1 = self.image_box
            photo = _cover_fit(Image.open(image).convert("RGBA"), x1 - x0, y1 - y0)
            canvas.alpha_composite(photo, (x0, y0))
        if self.above is not None:
            canvas.alpha_composite(self.above)
        tops = self._stack(texts) if BOTTOM_ALIGN else {}
        for name, slot in self.texts.items():
            value = texts.get(name)
            if value:
                info, top = tops.get(name, (None, None))
                slot.draw(canvas, value, top, info)
        return canvas.convert("RGB")

    def _stack(self, texts: dict[str, str]) -> dict[str, tuple[dict, float]]:
        """Posizione verticale dei testi grandi, ancorati in basso (vedi il docstring)."""
        slots = sorted((n for n in STACK if n in self.texts), key=lambda n: self.texts[n].box[1])
        if not slots:
            return {}
        nominal = {n: self.texts[n].box[1] + self.texts[n].capacity * self.texts[n].size * self.texts[n].leading for n in slots}
        # gruppi di testi vicini nel template
        groups, gaps = [[slots[0]]], {}
        for upper, lower in zip(slots, slots[1:]):
            gap = self.texts[lower].box[1] - nominal[upper]
            if gap <= STACK_MAX_GAP:
                groups[-1].append(lower)
                gaps[(upper, lower)] = gap
            else:
                groups.append([lower])
        out = {}
        for group in groups:
            lower_top = None
            for name in reversed(group):
                slot = self.texts[name]
                if len(group) == 1 and name == "BODY":
                    value = texts.get(name)
                    if value:
                        out[name] = (slot.layout(value), slot.box[1])
                    continue
                bottom = nominal[name] if lower_top is None else lower_top - gaps[(name, group[group.index(name) + 1])]
                value = texts.get(name)
                if value:
                    info = slot.layout(value)
                    lower_top = bottom - info["height"]
                    out[name] = (info, lower_top)
                else:
                    lower_top = bottom
        return out


# Il template da cui copiare le grandezze dei testi (None = ognuno tiene le sue)
ALIGN_SIZES_TO = "end"


def align_sizes(templates: dict[str, "PsdTemplate"], reference: str) -> None:
    """Stessa grandezza e interlinea per i testi con lo stesso nome in tutti i template."""
    ref = templates.get(reference)
    if not ref:
        return
    for name, tpl in templates.items():
        if tpl is ref:
            continue
        for slot, text_slot in tpl.texts.items():
            if slot in ref.texts:
                text_slot.size = ref.texts[slot].size
                text_slot.leading = ref.texts[slot].leading


def available() -> dict[str, PsdTemplate]:
    """Template presenti: cover.psd, slide.psd e (facoltativo) end.psd."""
    found = {}
    for kind in ("cover", "slide", "end"):
        path = TEMPLATES / f"{kind}.psd"
        if path.exists():
            found[kind] = PsdTemplate(path)
    if ALIGN_SIZES_TO:
        align_sizes(found, ALIGN_SIZES_TO)
    return found
