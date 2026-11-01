"""Slide del post celebrativo di fine tabellone, formato feed 1080x1440 (3:4).

Struttura (scheda progetto + indicazioni di Andrea):
- slide 1: la foto del vincitore/podio a tutta slide, titolo e categoria
- slide centrali: il cammino del tabellone (Round of 16 -> quarti -> semifinali ->
  finale), più slide se serve: la leggibilità viene prima di tutto
- ultima slide: la stessa foto trattata (overlay scuro più forte), "CONGRATS",
  categoria e vincitori: il pattern che i giocatori ricondividono

Stile carosello PickleballSpot: bordo giallo a pennellata costante, badge giallo,
testo bianco + giallo su overlay scuro, Fredoka.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from live import render
from live.render import BLACK, WHITE, YELLOW, phase_label

W, H = 1080, 1440
MARGIN = 40  # zona sicura feed: 50 px, il contenuto parte oltre


def _canvas(photo: Path | None = None, darkness: int = 120) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), BLACK)
    if photo and photo.exists():
        ph = Image.open(photo).convert("RGB")
        scale = max(W / ph.width, H / ph.height)
        ph = ph.resize((round(ph.width * scale), round(ph.height * scale)))
        img.paste(ph, ((W - ph.width) // 2, (H - ph.height) // 2))
        overlay = Image.new("L", (W, H), darkness)
        img = Image.composite(Image.new("RGB", (W, H), BLACK), img, overlay)
    # stessa cornice gialla delle Stories, adattata al 3:4 dalla misura dell'immagine
    render.grunge_border(img)
    return img, ImageDraw.Draw(img)


def _centered(draw, text, y, size, color, weight=600, max_width=W - 2 * (MARGIN + 40)):
    font = render.fit_font(draw, text, max_width, size, weight)
    box = draw.textbbox((0, 0), text, font=font)
    draw.text(((W - (box[2] - box[0])) // 2 - box[0], y - box[1]), text, font=font, fill=color)
    return y + (box[3] - box[1])


def _badge(draw, text, y):
    # badge in alto a sinistra come nel template carosello ufficiale
    text = text.upper()
    font = render.fit_font(draw, text, W - 2 * (MARGIN + 60), 30, weight=600)
    box = draw.textbbox((0, 0), text, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    pad_x, pad_y = 24, 12
    x0 = MARGIN + 40
    draw.rounded_rectangle([x0, y, x0 + tw + 2 * pad_x, y + th + 2 * pad_y],
                           radius=(th + 2 * pad_y) // 2, fill=YELLOW)
    draw.text((x0 + pad_x - box[0], y + pad_y - box[1]), text, font=font, fill=BLACK)
    return y + th + 2 * pad_y


def _logo(img: Image.Image, y: int | None = None) -> None:
    draw = ImageDraw.Draw(img)
    base_y = y if y is not None else H - 150
    if render.LOGO.exists():
        logo = Image.open(render.LOGO).convert("RGBA")
        ratio = min(380 / logo.width, 80 / logo.height)
        logo = logo.resize((int(logo.width * ratio), int(logo.height * ratio)))
        img.paste(logo, ((W - logo.width) // 2, base_y), logo)
    else:
        yy = _centered(draw, "PICKLEBALLSPOT", base_y, 44, WHITE, weight=700)
        _centered(draw, "@pickleball.spot", yy + 6, 26, YELLOW, weight=500)


def cover(photo: Path, event: str, tournament: str, winners: list[str]) -> Image.Image:
    img, draw = _canvas(photo, darkness=95)
    y = _badge(draw, "CHAMPIONS", MARGIN + 60)
    y = _centered(draw, tournament.upper(), y + 26, 34, WHITE, weight=500)
    y = H - 420
    for name in winners:
        y = _centered(draw, name, y, 76, YELLOW, weight=700) + 8
    _centered(draw, event.upper(), y + 14, 36, WHITE, weight=600)
    _logo(img)
    return img


def phase_slide(event: str, phase: str, matches: list, tournament: str,
                part: tuple[int, int] = (1, 1)) -> Image.Image:
    img, draw = _canvas()
    label = "THE ROAD TO GOLD" + (f" · {part[0]}/{part[1]}" if part[1] > 1 else "")
    y = _badge(draw, label, MARGIN + 60)
    y = _centered(draw, phase_label(phase), y + 30, 64, YELLOW, weight=700)
    y += 40

    available = H - 170 - y
    row_h = min(available // max(len(matches), 1), 230)
    y += max(0, (available - row_h * len(matches)) // 2)
    for m in matches:
        winner = m.side_a if m.winner == "a" else m.side_b
        loser = m.side_b if m.winner == "a" else m.side_a
        score = m.score if m.winner == "a" else ["-".join(reversed(g.split("-"))) for g in m.score]
        mid = y + 4
        mid = _centered(draw, winner.label(), mid, 40, YELLOW, weight=650) + 2
        mid = _centered(draw, f"d. {loser.label()}", mid, 32, WHITE, weight=500) + 2
        _centered(draw, "  ".join(score), mid, 34, WHITE, weight=650)
        y += row_h
        if m is not matches[-1]:
            draw.line([MARGIN + 160, y - 14, W - MARGIN - 160, y - 14], fill=YELLOW, width=2)
    _logo(img)
    return img


def congrats(photo: Path, event: str, tournament: str, winners: list[str]) -> Image.Image:
    """L'ultima slide: foto trattata, CONGRATS, categoria e vincitori."""
    img, draw = _canvas(photo, darkness=165)
    y = _badge(draw, tournament, MARGIN + 60)
    y = _centered(draw, "CONGRATS", H // 2 - 220, 120, YELLOW, weight=700)
    y = _centered(draw, event.upper(), y + 36, 40, WHITE, weight=600)
    y += 50
    for name in winners:
        y = _centered(draw, name, y, 64, WHITE, weight=700) + 8
    _centered(draw, "WINNERS", y + 16, 36, YELLOW, weight=600)
    _logo(img)
    return img


def build_carousel(photo: Path, event: str, tournament: str, matches: list,
                   phases: list[str]) -> list[Image.Image]:
    """Tutte le slide del post: cover, fasi in ordine di gioco, congrats.

    matches: le partite dell'evento (solo tabellone, finite, squadre note).
    phases: le fasi da raccontare, in ordine (es. ottavi, quarti, semifinali, finale).
    Massimo Instagram: 20 slide; se si sfora si parte dalla fase successiva.
    """
    final = next(m for m in matches if m.phase == "finale")
    winners = (final.side_a if final.winner == "a" else final.side_b).players

    def slides_for(selected: list[str]) -> list[Image.Image]:
        out = []
        for phase in selected:
            rows = [m for m in matches if m.phase == phase]
            if not rows:
                continue
            n_parts = -(-len(rows) // render.MAX_ROWS)
            size = -(-len(rows) // n_parts)
            chunks = [rows[i:i + size] for i in range(0, len(rows), size)]
            for n, chunk in enumerate(chunks, start=1):
                out.append(phase_slide(event, phase, chunk, tournament, part=(n, len(chunks))))
        return out

    middle = slides_for(phases)
    while len(middle) > 18 and len(phases) > 1:  # 20 slide con cover e congrats
        phases = phases[1:]
        middle = slides_for(phases)
    return [cover(photo, event, tournament, winners)] + middle + [congrats(photo, event, tournament, winners)]
