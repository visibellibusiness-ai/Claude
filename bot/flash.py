"""Reel "risposta lampo" (formato scelto da Andrea il 26/11/2026).

Domanda grande al fotogramma 0 (fa anche da copertina), poi la domanda rimpicciolisce in alto e
un blocco pieno entra a tendina con la risposta, poi un dettaglio, poi si torna alla domanda
grande: l'ultimo fotogramma è uguale al primo, così il video riparte senza stacco.

Impianto: fondo piatto scuro in alto con i testi, foto vera del soggetto in basso a tutta
larghezza; nessun testo sopra la foto, nessuna sfumatura (regole grafiche di Andrea).
Misure provate il 26/11/2026 sul Reel di prova "brain freeze": testi tra x 180 e x 900 (blocco
centrato su x 540, la domanda larga al massimo 696 px), tra y 240 e y 1250; maiuscole della
domanda di 110 px (leggibili nella griglia del profilo), della risposta di 41 px (circa 15 pt);
interlinea della domanda 120%, 64 px d'aria sopra e sotto il testo nel blocco.
"""

import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from bot import config
from bot.music import make_track

W, H, FPS = 1080, 1920, 30
X0, X1 = 180, 900
TOP = 240
READ_WPS = 3.0
SETTLE = 0.6
SMALL = 0.5        # scala della domanda quando sale in alto
MOVE = 0.45        # secondi del cambio di scala
FONT = Path(__file__).resolve().parent.parent / "assets" / "fonts" / "Archivo.ttf"
# (fondo, testo, accento, testo sull'accento): le 5 palette dello stile "mystery" (bot/style.py)
PALETTES = [
    ("#0B0C10", "#F4F0E8", "#E6B65C", "#0B0C10"),
    ("#091014", "#F0F5F4", "#6FD6C9", "#091014"),
    ("#100D14", "#F6F0F5", "#D99BCB", "#100D14"),
    ("#0D0D0B", "#F4F2E8", "#D4DB78", "#0D0D0B"),
    ("#0E0B0B", "#F6EFEB", "#EE7A5E", "#0E0B0B"),
]


def _rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def _font(size, wght, wdth=100):
    f = ImageFont.truetype(str(FONT), size)
    f.set_variation_by_axes([wght, wdth])
    return f


def _wrap(text, f, width):
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    lines, line = [], ""
    for w in text.split():
        cand = f"{line} {w}".strip()
        if d.textlength(cand, font=f) <= width or not line:
            line = cand
        else:
            lines.append(line)
            line = w
    return lines + [line] if line else lines


def _ink(line, f, size):
    """Bordi sinistro e destro dell'inchiostro vero della riga (getbbox non segue sempre gli
    assi del font variabile: si misura disegnando)."""
    im = Image.new("L", (int(f.getlength(line)) + 3 * size, 2 * size), 0)
    ImageDraw.Draw(im).text((size, 0), line, font=f, fill=255)
    box = im.getbbox()
    return box[0] - size, box[2] - size


def _text_image(text, size, wght, wdth, color, width, leading):
    """Blocco di testo centrato riga per riga sull'inchiostro, righe bilanciate (mai una parola
    sola sull'ultima riga quando si può evitare)."""
    f = _font(size, wght, wdth)
    lines = _wrap(text, f, width)
    best, best_score = lines, 0.0
    for w in range(width, int(width * 0.55), -8):
        cand = _wrap(text, f, w)
        if len(cand) != len(lines):
            break
        lens = [f.getlength(c) for c in cand]
        score = min(lens) / max(lens)
        if score > best_score:
            best, best_score = cand, score
    lines = best
    step = round(size * leading)
    asc, desc = f.getmetrics()
    im = Image.new("RGBA", (width, step * (len(lines) - 1) + asc + desc), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    widest = 0
    for i, ln in enumerate(lines):
        left, right = _ink(ln, f, size)
        widest = max(widest, right - left)
        d.text(((width - (right - left)) / 2 - left, i * step), ln, font=f, fill=color)
    box = im.getbbox()
    return im.crop((0, box[1], width, box[3])), lines, widest


def _question(text, color, width, max_h):
    for size in range(168, 100, -4):
        im, lines, widest = _text_image(text, size, 820, 76, color, width, 1.2)
        if im.height <= max_h and widest <= width:
            return im, size, lines
    raise ValueError(f"domanda troppo lunga per il formato risposta lampo: {text!r}")


def _ease(p):
    p = min(1.0, max(0.0, p))
    return 1 - (1 - p) ** 3


def _photo(post: dict) -> tuple[str, bool]:
    """La foto del soggetto: la prima foto vera delle schede, altrimenti la copertina."""
    for s in post.get("slides", []):
        if s.get("image") and not s.get("generated") and Path(s["image"]).exists():
            return s["image"], False
    cover = post.get("cover_image")
    if cover and Path(cover).exists():
        return cover, bool(post.get("cover_generated") or post.get("cover_ai_generated"))
    raise ValueError("nessuna foto disponibile per il formato risposta lampo")


def render_flash(post: dict, out_dir: Path, theme_index: int) -> Path:
    texts = post.get("flash") or {}
    if not all(texts.get(k) for k in ("question", "answer", "detail")):
        raise ValueError("testi della risposta lampo mancanti (question, answer, detail)")
    pal = PALETTES[int(post.get("design", {}).get("palette", theme_index)) % len(PALETTES)]
    bg, fg, acc, on_acc = (_rgb(c) for c in pal)
    photo_path, photo_ai = _photo(post)
    post["ai_generated"] = photo_ai  # nel Reel c'è solo questa foto: l'etichetta AI segue lei

    width = X1 - X0
    q_big, q_size, q_lines = _question(texts["question"], fg, width - 24, 800)
    pad_x, pad_y, a_size = 40, 64, 60
    answers = []
    for key in ("answer", "detail"):
        im, lines, _ = _text_image(texts[key], a_size, 520, 100, on_acc, width - 2 * pad_x, 1.3)
        answers.append((im, len(texts[key].split())))

    q_small_h = round(q_big.height * SMALL)
    block_h = max(a.height for a, _ in answers) + 2 * pad_y
    gap = 48
    strip_top = max(TOP + q_small_h + gap + block_h + gap, TOP + q_big.height + 64)
    if strip_top > 1250:
        raise ValueError("testi della risposta lampo troppo lunghi: il blocco supera y 1250")
    big_y = TOP + (strip_top - 64 - TOP - q_big.height) // 2
    block_y = TOP + q_small_h + (strip_top - TOP - q_small_h - block_h) // 2

    im = Image.open(photo_path).convert("RGB")
    strip_h = H - strip_top
    s = max(W * 1.08 / im.width, strip_h * 1.08 / im.height)
    master = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)

    def photo_view(p):
        k = 1.07 - 0.06 * p
        ww, wh = W * k, strip_h * k
        cx = master.width / 2
        cy = min(max(master.height * 0.45, wh / 2), master.height - wh / 2)
        x0, y0 = max(0.0, cx - ww / 2), max(0.0, cy - wh / 2)
        return master.resize((W, strip_h), Image.BILINEAR,
                             box=(x0, y0, min(master.width, x0 + ww), min(master.height, y0 + wh)))

    t_q = 0.4 + len(texts["question"].split()) / READ_WPS
    reads = [SETTLE + n / READ_WPS for _, n in answers]
    t_a0 = t_q + MOVE - 0.1
    t_d0 = t_a0 + 0.32 + reads[0]
    t_end = t_d0 + 0.32 + reads[1]
    total = t_end + 0.2 + MOVE + 0.45
    frames = round(total * FPS)
    print(f"Reel risposta lampo: domanda corpo {q_size} ({len(q_lines)} righe), {total:.1f} s, foto "
          f"{'generata' if photo_ai else 'vera'}: {Path(photo_path).name}")

    out_dir.mkdir(parents=True, exist_ok=True)
    preset = post.get("music") if post.get("music") in config.MUSIC_PRESETS else config.MUSIC_PRESETS[theme_index % len(config.MUSIC_PRESETS)]
    post["music_used"] = preset
    audio = make_track(out_dir / "music.wav", total, seed=theme_index, preset=preset)
    video = out_dir / "reel.mp4"
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", str(audio), "-c:v", "libx264", "-preset", "medium",
           "-crf", "20", "-pix_fmt", "yuv420p", "-profile:v", "high", "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
           "-shortest", "-movflags", "+faststart", str(video)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fi in range(frames):
        t = fi / FPS
        frame = Image.new("RGB", (W, H), bg)
        frame.paste(photo_view(float(np.sin(np.pi * t / total))), (0, strip_top))  # avanti e indietro: anello
        m = _ease((t - t_q) / MOVE) * (1 - _ease((t - (t_end + 0.2)) / MOVE))
        k = 1 - (1 - SMALL) * m
        qw, qh = round(q_big.width * k), round(q_big.height * k)
        q = q_big if k == 1 else q_big.resize((qw, qh), Image.LANCZOS)
        frame.paste(q, (X0 + (width - qw) // 2, round(big_y + (TOP - big_y) * m)), q)
        if t_a0 <= t < t_end + 0.2:
            bw = round(width * _ease((t - t_a0) / 0.32) * (1 - _ease((t - t_end) / 0.2)))
            if bw > 0:
                ImageDraw.Draw(frame).rectangle([X0, block_y, X0 + bw, block_y + block_h - 1], fill=acc)
                idx = 0 if t < t_d0 else 1
                start = t_a0 + 0.12 if idx == 0 else t_d0
                p_in = _ease((t - start) / 0.24)
                p_out = _ease((t - (t_d0 - 0.16)) / 0.16) if idx == 0 else _ease((t - t_end) / 0.16)
                alpha = p_in * (1 - p_out)
                if alpha > 0 and bw > pad_x:
                    a = answers[idx][0]
                    layer = a.copy()
                    layer.putalpha(layer.getchannel("A").point(lambda v, al=alpha: int(v * al)))
                    ty = pad_y + (block_h - 2 * pad_y - a.height) // 2 + round(22 * (1 - p_in))
                    clip = Image.new("RGBA", (bw, block_h), (0, 0, 0, 0))
                    clip.alpha_composite(layer.crop((0, 0, min(bw - pad_x, a.width), a.height)), (pad_x, ty))
                    frame.paste(clip, (X0, block_y), clip)
        proc.stdin.write(frame.tobytes())
        if fi == 0:
            frame.save(out_dir / "cover.jpg", "JPEG", quality=92)  # il fotogramma 0 è la copertina
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg non è riuscito a creare il Reel risposta lampo")
    audio.unlink()
    post["reel_fx"] = {"format": "flash", "seconds": round(total, 2), "question_size": q_size}
    return video
