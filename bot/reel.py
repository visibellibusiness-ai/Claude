"""Crea un Reel 1080x1920 (MP4) a partire dalle stesse slide del carosello.

Zone di sicurezza Reels rispettate: niente testo nei primi 250px in alto, negli
ultimi 420px in basso (caption, audio, pulsanti) né nei 150px a destra (icone).
"""

import subprocess
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw

from bot import config
from bot.music import make_track
from bot.render import _draw_block, _fit, _font, _theme

W, H = 1080, 1920
FPS = 30
LEFT, RIGHT = 90, W - 150
TOP, BOTTOM = 300, H - 460
TEXT_W = RIGHT - LEFT
ANIM = 0.45  # secondi di entrata del testo


def _scene_duration(*texts: str) -> float:
    words = sum(len(t.split()) for t in texts)
    return max(2.8, min(6.5, 1.5 + words * 0.28))


def _layer(draw_fn) -> Image.Image:
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer))
    return layer


def _scenes(post: dict, theme: dict, design: dict):
    """Restituisce (sfondo, livello testo, durata) per ogni scena."""
    bg = Image.new("RGB", (W, H), theme["bg"])
    scenes = []

    def cover(d):
        d.text((LEFT, TOP), design.get("cover_label", config.PAGE_NAME).upper(), font=_font(44, "Bold"), fill=theme["accent"])
        font, lines, size = _fit(d, post["hook"], "Black", TEXT_W, 900, 130, 70, 1.12)
        y = TOP + 120 + (BOTTOM - TOP - 120 - len(lines) * size * 1.12) / 2
        _draw_block(d, lines, font, size, LEFT, y, theme["fg"], 1.12)

    scenes.append((bg, _layer(cover), _scene_duration(post["hook"]) + 0.5))

    for i, slide in enumerate(post["slides"], start=1):
        def content(d, i=i, slide=slide):
            top = TOP
            if design.get("show_numbers", True):
                d.text((LEFT, TOP - 20), f"{i:02d}", font=_font(170, "Black"), fill=theme["accent"])
                top = TOP + 220
            tfont, tlines, tsize = _fit(d, slide["title"], "ExtraBold", TEXT_W, 330, 92, 56, 1.12)
            y = _draw_block(d, tlines, tfont, tsize, LEFT, top, theme["fg"], 1.12)
            bfont, blines, bsize = _fit(d, slide["body"], "Medium", TEXT_W, BOTTOM - y - 60, 60, 38, 1.38)
            _draw_block(d, blines, bfont, bsize, LEFT, y + 60, theme["fg"], 1.38)

        scenes.append((bg, _layer(content), _scene_duration(slide["title"], slide["body"])))

    end_bg = Image.new("RGB", (W, H), theme["accent"])

    def end(d):
        font, lines, size = _fit(d, post["cta"], "Black", TEXT_W, 700, 110, 60, 1.15)
        _draw_block(d, lines, font, size, LEFT, TOP + 150, theme["bg"], 1.15)
        d.text((LEFT, BOTTOM - 150), f"Follow {config.PAGE_HANDLE}", font=_font(48, "Bold"), fill=theme["bg"])
        d.text((LEFT, BOTTOM - 80), design.get("follow_line", "a new mind-blowing fact every day"), font=_font(36, "Medium"), fill=theme["bg"])

    scenes.append((end_bg, _layer(end), 3.5))
    return scenes


def render_reel(post: dict, out_dir: Path, theme_index: int) -> Path:
    design = post.get("design", {})
    theme = _theme(design, theme_index)
    post["design_used"] = theme
    scenes = _scenes(post, theme, design)
    total = sum(d for _, _, d in scenes)
    out_dir.mkdir(parents=True, exist_ok=True)
    audio = make_track(out_dir / "music.wav", total, seed=theme_index)
    video = out_dir / "reel.mp4"

    cmd = [
        imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", str(audio),
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-profile:v", "high",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        "-shortest", "-movflags", "+faststart", str(video),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    elapsed = 0.0
    for n, (bg, layer, duration) in enumerate(scenes):
        frames = int(duration * FPS)
        static = None
        for f in range(frames):
            t = f / FPS
            if t >= ANIM and static is not None:
                frame = static
            else:
                p = min(1.0, t / ANIM)
                ease = 1 - (1 - p) ** 3
                frame = bg.copy()
                faded = layer.copy()
                faded.putalpha(layer.getchannel("A").point(lambda a, e=ease: int(a * e)))
                frame.paste(faded, (0, int(50 * (1 - ease))), faded)
                if p >= 1.0:
                    static = frame
            frame = frame.copy()
            # barra di avanzamento (decorativa, nella zona alta)
            d = ImageDraw.Draw(frame)
            progress = (elapsed + t) / total
            color = theme["bg"] if n == len(scenes) - 1 else theme["accent"]
            d.rectangle([LEFT, 200, LEFT + int((RIGHT - LEFT) * progress), 208], fill=color)
            proc.stdin.write(frame.tobytes())
        elapsed += duration
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg non è riuscito a creare il Reel")
    audio.unlink()

    cover_frame = scenes[0][0].copy()
    cover_frame.paste(scenes[0][1], (0, 0), scenes[0][1])
    cover_frame.save(out_dir / "cover.jpg", "JPEG", quality=92)
    return video
