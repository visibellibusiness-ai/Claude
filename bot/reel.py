"""Crea un Reel 1080x1920 (MP4) a partire dalle stesse scene del carosello.

Zone di sicurezza Reels rispettate: niente testo nei primi 300px in alto, negli
ultimi 460px in basso (caption, audio, pulsanti) né nei 150px a destra (icone).
"""

import subprocess
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw

from bot import config
from bot.music import make_track
from bot.render import center_content, make_style, slide_data
from bot.style import flatten

W, H = 1080, 1920
FPS = 30
SAFE = (90, 300, W - 150, H - 460)
ANIM = 0.45  # secondi di entrata del testo


def _duration(kind: str, data: dict) -> float:
    if kind == "cta":
        return 3.5
    text = data.get("hook", "") + " " + data.get("title", "") + " " + data.get("body", "")
    words = len(text.split())
    return max(2.8, min(6.5, 1.5 + words * 0.28)) + (0.5 if kind == "cover" else 0)


def render_reel(post: dict, out_dir: Path, theme_index: int) -> Path:
    style = make_style(post, theme_index)
    items = slide_data(post, theme_index)
    items[0][1]["swipe"] = "Keep watching"  # un video non si scorre
    style.plan(items, SAFE, boost=1.18)
    center_content(style, items, W, H, SAFE)
    scenes = []
    for kind, data in items:
        bg, fg = style.slide(kind, data, W, H, SAFE)
        scenes.append((bg, fg, _duration(kind, data), style.accent(kind)))
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
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-profile:v", "high",
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
            d.rectangle([left, 200, left + int((right - left) * (elapsed + t) / total), 208], fill=accent)
            proc.stdin.write(frame.tobytes())
        elapsed += duration
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg non è riuscito a creare il Reel")
    audio.unlink()

    flatten(scenes[0][0], scenes[0][1]).save(out_dir / "cover.jpg", "JPEG", quality=92)
    return video
