"""Template Photoshop: la grafica la disegna Andrea, il sistema cambia testi e immagini.

Convenzione (vedi templates/README.md): nei file PSD i livelli da sostituire hanno
nomi fissi, con o senza parentesi graffe ("TITLE" oppure "{{TITLE}}"):
- IMAGE: un rettangolo o un'immagine segnaposto, riempito con la foto della slide;
- TITLE, BODY, HIGHLIGHT, LABEL, NUMBER, HANDLE, CREDIT: livelli di testo. Il testo
  nuovo prende font, dimensione, colore, interlinea e allineamento del livello e si
  riduce da solo se non entra nel riquadro (meglio usare caselle di testo).
- "TITLE box" (opzionale): un rettangolo che definisce a mano il riquadro di un testo.
Tutti gli altri livelli restano esattamente come disegnati.
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

    def draw(self, canvas: Image.Image, text: str) -> None:
        if self.uppercase:
            text = text.upper()
        x0, y0, x1, y1 = self.box
        width, height = x1 - x0, y1 - y0
        size = self.size
        while True:
            font = _font(self.font_name, size)
            lines = _wrap(text, font, width)
            line_h = size * self.leading
            if len(lines) * line_h <= height * 1.02 or size <= self.size * 0.45:
                break
            size *= 0.94
        layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        y = y0
        for line in lines:
            w = d.textlength(line, font=font)
            x = x0 if self.align == "left" else (x1 - w if self.align == "right" else x0 + (width - w) / 2)
            d.text((x, y), line, font=font, fill=self.color)
            y += line_h
        canvas.alpha_composite(layer)


def _wrap(text: str, font, width: float) -> list[str]:
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    out = []
    for para in text.split("\n"):
        line = ""
        for word in para.split():
            cand = f"{line} {word}".strip()
            if probe.textlength(cand, font=font) <= width or not line:
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
        for name, slot in self.texts.items():
            value = texts.get(name)
            if value:
                slot.draw(canvas, value)
        return canvas.convert("RGB")


def available() -> dict[str, PsdTemplate]:
    """Template presenti: cover.psd, slide.psd e (facoltativo) end.psd."""
    found = {}
    for kind in ("cover", "slide", "end"):
        path = TEMPLATES / f"{kind}.psd"
        if path.exists():
            found[kind] = PsdTemplate(path)
    return found
