"""Disegna le slide del carosello come JPEG 1080x1350."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from bot import config

FONT_PATH = Path(__file__).resolve().parent.parent / "assets" / "fonts" / "Montserrat.ttf"
MARGIN = 96


def _font(size: int, weight: str) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(str(FONT_PATH), size)
    font.set_variation_by_name(weight)
    return font


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def _fit(draw, text, weight, max_width, max_height, start, minimum, spacing=1.2):
    """Trova la dimensione di font più grande che fa stare il testo nel box."""
    size = start
    while size > minimum:
        font = _font(size, weight)
        lines = _wrap(draw, text, font, max_width)
        if len(lines) * size * spacing <= max_height:
            return font, lines, size
        size -= 4
    font = _font(minimum, weight)
    return font, _wrap(draw, text, font, max_width), minimum


def _draw_block(draw, lines, font, size, x, y, fill, spacing=1.2):
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += int(size * spacing)
    return y


def _base(theme, index, total):
    img = Image.new("RGB", (config.WIDTH, config.HEIGHT), theme["bg"])
    draw = ImageDraw.Draw(img)
    # barra d'accento in alto e handle in basso
    draw.rectangle([MARGIN, MARGIN, MARGIN + 120, MARGIN + 12], fill=theme["accent"])
    small = _font(30, "SemiBold")
    draw.text((MARGIN, config.HEIGHT - MARGIN - 30), config.PAGE_HANDLE, font=small, fill=theme["fg"])
    counter = f"{index}/{total}"
    w = draw.textlength(counter, font=small)
    draw.text((config.WIDTH - MARGIN - w, config.HEIGHT - MARGIN - 30), counter, font=small, fill=theme["accent"])
    return img, draw


def render_post(post: dict, out_dir: Path, theme_index: int) -> list[Path]:
    theme = config.THEMES[theme_index % len(config.THEMES)]
    out_dir.mkdir(parents=True, exist_ok=True)
    total = len(post["slides"]) + 2
    width = config.WIDTH - 2 * MARGIN
    paths = []

    def save(img, n):
        p = out_dir / f"slide_{n:02d}.jpg"
        img.save(p, "JPEG", quality=92)
        paths.append(p)

    # Copertina
    img, draw = _base(theme, 1, total)
    label = _font(36, "Bold")
    draw.text((MARGIN, MARGIN + 60), "LO SAPEVI?", font=label, fill=theme["accent"])
    font, lines, size = _fit(draw, post["hook"], "Black", width, 760, 120, 64, 1.12)
    y = (config.HEIGHT - len(lines) * size * 1.12) / 2
    _draw_block(draw, lines, font, size, MARGIN, y, theme["fg"], 1.12)
    hint = _font(34, "SemiBold")
    draw.text((MARGIN, config.HEIGHT - MARGIN - 110), "Scorri  →", font=hint, fill=theme["accent"])
    save(img, 1)

    # Slide di contenuto
    for i, slide in enumerate(post["slides"], start=2):
        img, draw = _base(theme, i, total)
        num = _font(150, "Black")
        draw.text((MARGIN, MARGIN + 50), f"{i - 1:02d}", font=num, fill=theme["accent"])
        tfont, tlines, tsize = _fit(draw, slide["title"], "ExtraBold", width, 260, 80, 50, 1.12)
        y = _draw_block(draw, tlines, tfont, tsize, MARGIN, MARGIN + 270, theme["fg"], 1.12)
        bfont, blines, bsize = _fit(draw, slide["body"], "Medium", width, config.HEIGHT - y - 260, 52, 34, 1.4)
        _draw_block(draw, blines, bfont, bsize, MARGIN, y + 50, theme["fg"], 1.4)
        save(img, i)

    # Call to action finale
    img, draw = Image.new("RGB", (config.WIDTH, config.HEIGHT), theme["accent"]), None
    draw = ImageDraw.Draw(img)
    font, lines, size = _fit(draw, post["cta"], "Black", width, 600, 96, 56, 1.15)
    y = (config.HEIGHT - len(lines) * size * 1.15) / 2 - 60
    _draw_block(draw, lines, font, size, MARGIN, y, theme["bg"], 1.15)
    follow = _font(42, "Bold")
    draw.text((MARGIN, config.HEIGHT - MARGIN - 140), f"Segui {config.PAGE_HANDLE}", font=follow, fill=theme["bg"])
    draw.text((MARGIN, config.HEIGHT - MARGIN - 80), "una curiosità nuova ogni giorno", font=_font(32, "Medium"), fill=theme["bg"])
    save(img, total)
    return paths
