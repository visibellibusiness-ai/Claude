"""Grafiche Story del tool risultati live, nello stile PickleballSpot.

Formato: Instagram Stories 1080x1920. Zone sicure: 250 px in alto e in basso liberi da
elementi essenziali. Colori ufficiali: bianco #FFFFFF, nero #000000, giallo #FFFF00.
Font: Fredoka (assets/fonts/Fredoka.ttf, variabile). Bordo giallo con margine irregolare
"a pennellata", badge giallo con testo nero, gerarchia testo bianco + giallo su fondo scuro.

Logo: se c'è assets/logos/logo-pickleball-spot-all-white-back-trasp.png si usa quello,
altrimenti il wordmark testuale in Fredoka come ripiego provvisorio.
"""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT = ROOT / "assets" / "fonts" / "Fredoka.ttf"
LOGO = ROOT / "assets" / "logos" / "logo-pickleball-spot-all-white-back-trasp.png"

W, H = 1080, 1920
SAFE_TOP, SAFE_BOTTOM = 250, 250
YELLOW = (255, 255, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BORDER = 26          # spessore medio del bordo giallo
INSET = 54           # inizio dell'area contenuto


# etichette delle fasi per le grafiche (torneo internazionale -> inglese)
PHASE_LABELS = {
    "gironi": "GROUP STAGE",
    "trentaduesimi": "ROUND OF 64",
    "sedicesimi": "ROUND OF 32",
    "ottavi": "ROUND OF 16",
    "quarti": "QUARTER-FINALS",
    "semifinali": "SEMI-FINALS",
    "finale": "FINAL",
    "terzo posto": "BRONZE MATCH",
}


def phase_label(phase: str) -> str:
    base = phase.split(" ")[0] if phase.startswith("gironi") else phase
    label = PHASE_LABELS.get(base, phase.upper())
    if phase.startswith("gironi") and phase != "gironi":
        label = f"GROUP {phase.split(' ', 1)[1].upper()}"
    return label


def fredoka(size: int, weight: int = 600) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(str(FONT), size)
    try:
        # assi di Fredoka nell'ordine del font: [wght, wdth]
        font.set_variation_by_axes([weight, 100])
    except OSError:
        pass
    return font


def text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def fit_font(draw: ImageDraw.ImageDraw, text: str, max_width: int, size: int,
             weight: int = 600, min_size: int = 26) -> ImageFont.FreeTypeFont:
    """Il font più grande (fino a size) con cui il testo sta in max_width."""
    while size > min_size:
        font = fredoka(size, weight)
        if text_width(draw, text, font) <= max_width:
            return font
        size -= 2
    return fredoka(min_size, weight)


def grunge_border(img: Image.Image, seed: int = 7) -> None:
    """Cornice gialla con margine interno irregolare, effetto pennellata."""
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W - 1, H - 1], outline=YELLOW, width=BORDER)
    rng = random.Random(seed)
    # pennellate: blob gialli che sporgono dal bordo verso l'interno
    for edge in range(4):
        pos = 0
        while pos < (W if edge in (0, 2) else H):
            pos += rng.randint(26, 90)
            r = rng.randint(4, 16)
            off = BORDER + rng.randint(-6, 8)
            if edge == 0:
                xy = (pos, off)
            elif edge == 2:
                xy = (pos, H - off)
            elif edge == 1:
                xy = (W - off, pos)
            else:
                xy = (off, pos)
            draw.ellipse([xy[0] - r, xy[1] - r, xy[0] + r, xy[1] + r], fill=YELLOW)


def badge(draw: ImageDraw.ImageDraw, text: str, y: int, size: int = 34) -> int:
    """Pillola gialla con testo nero maiuscolo, centrata. Restituisce la y sotto il badge."""
    text = text.upper()
    font = fit_font(draw, text, W - 2 * (INSET + 40), size, weight=600)
    tw = text_width(draw, text, font)
    pad_x, pad_y = 30, 14
    x0 = (W - tw) // 2 - pad_x
    box = draw.textbbox((0, 0), text, font=font)
    th = box[3] - box[1]
    draw.rounded_rectangle([x0, y, x0 + tw + 2 * pad_x, y + th + 2 * pad_y],
                           radius=(th + 2 * pad_y) // 2, fill=YELLOW)
    draw.text(((W - tw) // 2 - box[0], y + pad_y - box[1]), text, font=font, fill=BLACK)
    return y + th + 2 * pad_y


def centered(draw: ImageDraw.ImageDraw, text: str, y: int, size: int, color, weight: int = 600,
             max_width: int = W - 2 * (INSET + 30)) -> int:
    font = fit_font(draw, text, max_width, size, weight)
    box = draw.textbbox((0, 0), text, font=font)
    draw.text(((W - (box[2] - box[0])) // 2 - box[0], y - box[1]), text, font=font, fill=color)
    return y + (box[3] - box[1])


def logo_footer(img: Image.Image) -> None:
    """Logo bianco in basso, dentro la zona sicura."""
    draw = ImageDraw.Draw(img)
    base_y = H - SAFE_BOTTOM - 110
    if LOGO.exists():
        logo = Image.open(LOGO).convert("RGBA")
        ratio = min(420 / logo.width, 90 / logo.height)
        logo = logo.resize((int(logo.width * ratio), int(logo.height * ratio)))
        img.paste(logo, ((W - logo.width) // 2, base_y), logo)
    else:
        y = centered(draw, "PICKLEBALLSPOT", base_y, 52, WHITE, weight=700)
        centered(draw, "@pickleball.spot", y + 8, 30, YELLOW, weight=500)


def new_story() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), BLACK)
    grunge_border(img)
    return img, ImageDraw.Draw(img)


def score_line(score: list[str]) -> str:
    return "  ".join(score)


def handles_line(players: list[str], handles: dict[str, str]) -> str:
    tags = [handles[p] for p in players if p in handles]
    return "  ".join(tags)


def story_match(match, tournament: str, handles: dict[str, str] | None = None) -> Image.Image:
    """Story per una partita finita: vincitori grandi, punteggio, sconfitti, tag."""
    handles = handles or {}
    img, draw = new_story()
    y = badge(draw, f"{match.event} · {phase_label(match.phase)}", SAFE_TOP + 60)

    winner = match.side_a if match.winner == "a" else match.side_b
    loser = match.side_b if match.winner == "a" else match.side_a
    win_score = match.score if match.winner == "a" else [
        "-".join(reversed(g.split("-"))) for g in match.score
    ]

    y = centered(draw, tournament.upper(), y + 70, 36, WHITE, weight=500)
    y += 90
    for name in winner.players:
        y = centered(draw, name, y, 88, YELLOW, weight=700) + 10
    tags = handles_line(winner.players, handles)
    if tags:
        y = centered(draw, tags, y + 2, 34, WHITE, weight=500)
    y = centered(draw, "CHAMPIONS" if match.phase == "finale" else "WIN", y + 46, 44, WHITE, weight=700)
    y = centered(draw, score_line(win_score), y + 24, 100, WHITE, weight=700)
    y = centered(draw, "vs", y + 60, 36, YELLOW, weight=500)
    y += 28
    for name in loser.players:
        y = centered(draw, name, y, 54, WHITE, weight=600) + 6
    tags = handles_line(loser.players, handles)
    if tags:
        centered(draw, tags, y + 2, 30, WHITE, weight=500)

    logo_footer(img)
    return img


MAX_ROWS = 5  # partite per Story di fase: più contenuto ma sempre leggibile


def story_phase(event: str, phase: str, matches: list, tournament: str,
                part: tuple[int, int] = (1, 1)) -> Image.Image:
    """Story con i risultati di una fase (es. tutti i quarti). matches <= MAX_ROWS."""
    img, draw = new_story()
    label = f"{event}" + (f" · {part[0]}/{part[1]}" if part[1] > 1 else "")
    y = badge(draw, label, SAFE_TOP + 40)
    y = centered(draw, tournament.upper(), y + 40, 34, WHITE, weight=500)
    y = centered(draw, phase_label(phase), y + 30, 84, YELLOW, weight=700)
    y += 70

    row_h = (H - SAFE_BOTTOM - 180 - y) // max(len(matches), 1)
    row_h = min(row_h, 260)
    for m in matches:
        winner = m.side_a if m.winner == "a" else m.side_b
        loser = m.side_b if m.winner == "a" else m.side_a
        score = m.score if m.winner == "a" else ["-".join(reversed(g.split("-"))) for g in m.score]
        mid = y + 6
        mid = centered(draw, winner.label(), mid, 46, YELLOW, weight=650) + 4
        mid = centered(draw, f"d. {loser.label()}", mid, 36, WHITE, weight=500) + 4
        centered(draw, score_line(score), mid, 40, WHITE, weight=650)
        y += row_h
        if m is not matches[-1]:
            draw.line([INSET + 120, y - 18, W - INSET - 120, y - 18], fill=YELLOW, width=2)

    logo_footer(img)
    return img
