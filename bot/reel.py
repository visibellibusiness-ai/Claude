"""Crea un Reel 1080x1920 (MP4) a partire dalle stesse scene del carosello.

La foto del soggetto copre tutto lo schermo per tutta la durata, con uno zoom lento, e sotto
il testo c'è una velatura scura calcolata scena per scena finché il contrasto è sufficiente
(vedi `_veil`). Senza foto si torna al fondo scuro di prima.

Zone di sicurezza Reels rispettate: niente testo nei primi 300px in alto, negli
ultimi 460px in basso (caption, audio, pulsanti) né nei 150px a destra (icone).
"""

import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from bot import config
from bot.music import make_track
from bot.render import center_content, make_style, slide_data
from bot.style import _mono, flatten, spaced

W, H = 1080, 1920
FPS = 30
SAFE = (90, 300, W - 150, H - 460)
ANIM = 0.45  # secondi di entrata del testo
ZOOM = 0.10  # ingrandimento della foto da inizio a fine Reel

# Contrasto minimo del testo sulla foto (WCAG): il 10% di pixel di testo messo peggio deve
# arrivare almeno a 5 e la mediana almeno a 6 (il colore d'accento su nero non supera circa 7). Il controllo si fa a inizio e a fine zoom.
MIN_P10, MIN_MEDIAN = 5.0, 6.0


def _duration(kind: str, data: dict, fast: bool = False) -> float:
    if kind == "cta":
        return 2.5 if fast else 3.5
    text = data.get("hook", "") + " " + data.get("title", "") + " " + data.get("body", "")
    words = len(text.split())
    if fast:  # rubrica news: circa 20 secondi in tutto
        return max(2.4, min(3.8, 1.2 + words * 0.13))
    return max(2.8, min(6.5, 1.5 + words * 0.28)) + (0.5 if kind == "cover" else 0)


# ------------------------------------------------------------------ foto

def _master(path) -> Image.Image:
    """Foto adattata a coprire lo schermo con il margine per lo zoom."""
    im = Image.open(path).convert("RGB")
    s = max(W * (1 + ZOOM) / im.width, H * (1 + ZOOM) / im.height)
    return im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)


def _view(master: Image.Image, progress: float) -> Image.Image:
    """Inquadratura a metà dello zoom: la finestra si stringe da (1+ZOOM) a 1 volte lo schermo."""
    k = 1 + ZOOM * (1 - progress)
    ww, wh = W * k, H * k
    cx, cy = master.width / 2, master.height / 2
    return master.resize((W, H), Image.BILINEAR, box=(cx - ww / 2, cy - wh / 2, cx + ww / 2, cy + wh / 2))


# ------------------------------------------------------------- leggibilità

def _luminance(rgb: np.ndarray) -> np.ndarray:
    c = rgb.astype(np.float32) / 255
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return lin @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)


def _local_mask(fg: Image.Image) -> np.ndarray:
    """Dove c'è testo: un alone attorno alle lettere (la foto resta visibile tra un blocco e
    l'altro) più una fascia leggera a tutta larghezza che lo raccorda, così su foto chiare
    non restano macchie scure isolate."""
    alpha = fg.getchannel("A")
    # ogni blocco da 8 px con un po' di testo vale 1: le righe sottili della testata non devono sbiadire
    small = alpha.resize((W // 8, H // 8), Image.BOX).point(lambda v: 255 if v > 2 else 0)
    halo = small.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(7))
    halo = np.asarray(halo.resize((W, H), Image.BILINEAR), dtype=np.float32) / 255
    rows = (np.asarray(alpha) > 8).any(axis=1).astype(np.uint8) * 255
    strip = Image.fromarray(np.repeat(rows[:, None], 9, axis=1))
    strip = strip.filter(ImageFilter.MaxFilter(121)).filter(ImageFilter.GaussianBlur(40))
    band = np.repeat((np.asarray(strip, dtype=np.float32)[:, 4] / 255)[:, None], W, axis=1)
    return np.maximum(halo, 0.45 * band)


def _veil(local: np.ndarray, strength: float) -> Image.Image:
    """Moltiplicatore di luminosità: velatura di base per tutta la foto e, dove c'è testo,
    una velatura in più che cresce con `strength`."""
    y = np.linspace(0, 1, H, dtype=np.float32)
    base = np.interp(y, [0, 0.10, 0.19, 0.30, 0.40, 0.75, 1.0], [0.55, 0.38, 0.40, 0.18, 0.16, 0.42, 0.58])[:, None]
    dark = 1 - (1 - base) * (1 - strength * np.clip(local * 1.6, 0, 1))
    return Image.fromarray(((1 - dark) * 255).astype(np.uint8)).convert("RGB")


def _contrast(master: Image.Image, veil: Image.Image, fg: Image.Image) -> tuple[float, float]:
    """(10° percentile, mediana) del contrasto dei pixel di testo, al punto peggiore dello zoom
    e della fascia: ogni fascia di 100 px con testo conta da sola, così testata ed etichette
    piccole non si perdono dietro al corpo del testo."""
    text = np.asarray(fg.getchannel("A")) > 200
    if not text.any():
        return 99.0, 99.0
    rows = np.nonzero(text)[0]
    text_lum = _luminance(np.asarray(fg.convert("RGB"))[text])
    worst = (99.0, 99.0)
    for progress in (0.0, 1.0):
        bg = np.asarray(ImageChops.multiply(_view(master, progress), veil))[text]
        ratio = (text_lum + 0.05) / (_luminance(bg) + 0.05)
        ratio = np.maximum(ratio, 1 / ratio)
        for band in np.unique(rows // 100):
            r = ratio[rows // 100 == band]
            if len(r) >= 150:
                worst = (min(worst[0], float(np.percentile(r, 10))), min(worst[1], float(np.median(r))))
    return worst


def _readable(master: Image.Image, fg: Image.Image) -> tuple[Image.Image, float, float]:
    """Velatura più leggera che porta il testo sopra le soglie di contrasto."""
    local = _local_mask(fg)
    strength = 0.45
    while True:
        veil = _veil(local, strength)
        p10, median = _contrast(master, veil, fg)
        if (p10 >= MIN_P10 and median >= MIN_MEDIAN) or strength >= 0.95:
            return veil, p10, median
        strength = min(0.95, strength + 0.05)


def _with_shadow(fg: Image.Image) -> Image.Image:
    """Ombra morbida sotto le lettere, che aiuta dove la foto è chiara."""
    shade = fg.getchannel("A").filter(ImageFilter.GaussianBlur(7)).point(lambda a: min(255, int(a * 0.9)))
    layer = Image.new("RGBA", fg.size, (0, 0, 0, 0))
    layer.putalpha(shade)
    layer.alpha_composite(fg)
    return layer


# ---------------------------------------------------------------- Reel

def render_reel(post: dict, out_dir: Path, theme_index: int) -> Path:
    style = make_style(post, theme_index)
    items = slide_data(post, theme_index)
    items[0][1]["swipe"] = "Keep watching"  # un video non si scorre
    news = post.get("series") == "news"
    if news:
        # Reel news: apertura di 2 secondi e, per ogni notizia, solo "cosa è successo"
        items[0][1]["hook"] = post.get("reel_hook") or post["hook"]
        for kind, data in items:
            if kind == "fact" and data.get("points"):
                data["points"] = data["points"][:1]
                data["body"] = data["points"][0][1]
    style.plan(items, SAFE, boost=1.18)
    center_content(style, items, W, H, SAFE)

    photo_path = post.get("cover_image")
    master = _master(photo_path) if photo_path and Path(photo_path).exists() else None
    if master:
        # riferimento fisso su ogni scheda, a destra di "FILE 01 / 05": di cosa parla il Reel
        topic = (post.get("design", {}).get("cover_label") or post.get("category", "")).upper()[:22]
        for kind, data in items:
            if kind == "fact" and topic and not data.get("label"):
                data["label"] = topic

    scenes = []
    for n, (kind, data) in enumerate(items, start=1):
        bg, fg = style.slide(kind, data, W, H, SAFE)
        if master:
            veil, p10, median = _readable(master, fg)
            ok = p10 >= MIN_P10 and median >= MIN_MEDIAN
            print(f"Reel, leggibilità scena {n} ({kind}): contrasto peggiore {p10:.1f}:1, mediano {median:.1f}:1"
                  + ("" if ok else " (SOTTO SOGLIA con la velatura al massimo)"))
            bg, fg = veil, _with_shadow(fg)
        scenes.append((bg, fg, _duration(kind, data, fast=news), style.accent(kind)))
    total = sum(s[2] for s in scenes)

    out_dir.mkdir(parents=True, exist_ok=True)
    preset = post.get("music") if post.get("music") in config.MUSIC_PRESETS else config.MUSIC_PRESETS[theme_index % len(config.MUSIC_PRESETS)]
    post["music_used"] = preset
    audio = make_track(out_dir / "music.wav", total, seed=theme_index, preset=preset)
    video = out_dir / "reel.mp4"

    cmd = [
        imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", str(audio),
        "-c:v", "libx264", "-preset", "medium", "-crf", "24", "-pix_fmt", "yuv420p", "-profile:v", "high",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        "-shortest", "-movflags", "+faststart", str(video),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    elapsed = 0.0
    left, right = SAFE[0], SAFE[2]
    for bg, fg, duration, accent in scenes:
        static = None
        for f in range(int(duration * FPS)):
            t = f / FPS
            progress = (elapsed + t) / total
            if master:
                # la foto si muove piano: la scena si ricompone a ogni fotogramma
                base = ImageChops.multiply(_view(master, progress), bg).convert("RGBA")
                p = min(1.0, t / ANIM)
                ease = 1 - (1 - p) ** 3
                layer = fg
                if p < 1.0:
                    faded = fg.copy()
                    faded.putalpha(fg.getchannel("A").point(lambda a, e=ease: int(a * e)))
                    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    layer.alpha_composite(faded, (0, int(50 * (1 - ease))))
                base.alpha_composite(layer)
                frame = base.convert("RGB")
            else:
                if static is None:
                    p = min(1.0, t / ANIM)
                    ease = 1 - (1 - p) ** 3
                    faded = fg.copy()
                    faded.putalpha(fg.getchannel("A").point(lambda a, e=ease: int(a * e)))
                    moved = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    moved.alpha_composite(faded, (0, int(50 * (1 - ease))))
                    frame = flatten(bg, moved)
                    if p >= 1.0:
                        static = frame
                frame = (static if static is not None else frame).copy()
            # barra di avanzamento (decorativa, nella zona alta)
            d = ImageDraw.Draw(frame)
            if master:
                d.rectangle([left, 200, right, 208], fill=(70, 70, 70))
            d.rectangle([left, 200, left + int((right - left) * (elapsed + t) / total), 208], fill=accent)
            proc.stdin.write(frame.tobytes())
        elapsed += duration
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg non è riuscito a creare il Reel")
    audio.unlink()

    cover_bg = scenes[0][0]
    if master:
        still = ImageChops.multiply(_view(master, 0.0), cover_bg).convert("RGBA")
        still.alpha_composite(scenes[0][1])
        still.convert("RGB").save(out_dir / "cover.jpg", "JPEG", quality=92)
    else:
        flatten(cover_bg, scenes[0][1]).save(out_dir / "cover.jpg", "JPEG", quality=92)
    return video
