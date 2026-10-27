"""Prova del Reel senza pubblicare niente.

Prende foto vere (stessa ricerca e stessa scelta del bot), disegna un Reel per ciascuna con
`render_reel`, misura il tempo e la leggibilità e scrive in prova_out/: per ogni caso un
montaggio dei fotogrammi e, alla fine, rapporto.txt. Non usa le chiavi di Instagram.
Serve a controllare il Reel sul server di GitHub (vedi .github/workflows/prova-reel.yml).

Uso: python -m bot.prova_reel
"""

import contextlib
import io
import re
import subprocess
import sys
import time
from pathlib import Path

import imageio_ffmpeg
from PIL import Image

from bot import images
from bot.reel import render_reel

OUT = Path("prova_out")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# (nome, ricerca foto, titolo): una foto scura, una molto chiara, una di montagna
CASES = [
    ("polpo", "octopus underwater", "5 things octopuses do that seem impossible"),
    ("sabbia", "white sand beach", "5 things about white sand beaches"),
    ("neve", "snowy mountain sunny", "5 things about snow"),
]
SLIDES = [
    {"title": "Three hearts", "body": "Two hearts pump blood through the gills. The third pumps it to the rest of the body.", "highlight": "3"},
    {"title": "Blue blood", "body": "Their blood carries oxygen with copper-based hemocyanin instead of iron, which turns it blue.", "highlight": "Blue"},
    {"title": "Arms that think", "body": "About two-thirds of an octopus's neurons are in its arms, not its brain.", "highlight": "2/3"},
    {"title": "They taste by touch", "body": "Their suckers are packed with chemical receptors, so octopuses taste whatever they touch.", "highlight": "Taste"},
    {"title": "Masters of disguise", "body": "Octopuses change colour and skin texture in a fraction of a second to match their surroundings.", "highlight": "1/4s"},
]


def frame(video: Path, second: int, out: Path) -> None:
    subprocess.run([FFMPEG, "-loglevel", "error", "-y", "-ss", str(second), "-i", str(video), "-frames:v", "1", str(out)], check=True)


def duration(video: Path) -> float:
    err = subprocess.run([FFMPEG, "-hide_banner", "-i", str(video)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def run_case(name: str, query: str, hook: str) -> dict:
    folder = OUT / name
    folder.mkdir(parents=True, exist_ok=True)
    found = images.get_image(query, "", hook, folder / "photo.jpg")
    if not found:
        return {"name": name, "ok": False, "note": f"nessuna foto trovata per '{query}'"}
    post = {"hook": hook, "category": "animals", "series": "facts", "music": "mystery", "cta": "Follow for a new fact every day",
            "cover_image": found["path"], "slides": SLIDES}
    log = io.StringIO()
    started = time.time()
    with contextlib.redirect_stdout(log):
        video = render_reel(post, folder, theme_index=4)
    elapsed = time.time() - started
    seconds = duration(video)
    shots = []
    for i, s in enumerate((2, int(seconds * 0.3), int(seconds * 0.6), int(seconds * 0.9))):
        shot = folder / f"f{i}.jpg"
        frame(video, s, shot)
        shots.append(Image.open(shot).convert("RGB").resize((360, 640)))
    montage = Image.new("RGB", (360 * len(shots), 640))
    for i, im in enumerate(shots):
        montage.paste(im, (360 * i, 0))
    montage.save(OUT / f"{name}.jpg", quality=88)
    scenes = log.getvalue().strip().splitlines()
    return {"name": name, "ok": not any("SOTTO SOGLIA" in line for line in scenes), "photo": found["credit"],
            "render_s": round(elapsed), "video_s": round(seconds, 1), "mb": round(video.stat().st_size / 1e6, 1), "scenes": scenes}


def main() -> int:
    OUT.mkdir(exist_ok=True)
    results = [run_case(*case) for case in CASES]
    lines = []
    for r in results:
        lines.append(f"== {r['name']}: {'OK' if r['ok'] else 'DA GUARDARE'}")
        if "scenes" not in r:
            lines.append(f"   {r['note']}")
            continue
        lines.append(f"   foto: {r['photo']}")
        lines.append(f"   render {r['render_s']} s, video {r['video_s']} s, {r['mb']} MB")
        lines += [f"   {line}" for line in r["scenes"]]
    (OUT / "rapporto.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
