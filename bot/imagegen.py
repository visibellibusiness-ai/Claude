"""Generazione di immagini con modelli open source, su CPU (server di GitHub).

Modelli supportati (licenze che permettono l'uso commerciale):
- "vega": Segmind Vega + VegaRT (Apache 2.0), 4 passaggi, fino a 1024px.
- "sd-turbo": Stability SD-Turbo, 1-4 passaggi a 512px (più veloce, meno dettagli).
"""

import time
from pathlib import Path

import torch

STYLE_SUFFIX = (
    ", symbolic editorial illustration, dark cinematic background, moody low-key lighting, "
    "warm amber highlights, subtle film grain, minimal composition, large empty dark space at the top, "
    "no text, no letters, no logos, no people"
)
NEGATIVE = "text, letters, watermark, logo, signature, people, faces, hands, photo of a person, blurry, lowres"

_pipes: dict = {}


def _pipe(model: str):
    if model in _pipes:
        return _pipes[model]
    torch.set_num_threads(max(1, torch.get_num_threads()))
    if model == "vega":
        from diffusers import LCMScheduler, StableDiffusionXLPipeline

        pipe = StableDiffusionXLPipeline.from_pretrained("segmind/Segmind-Vega", torch_dtype=torch.float32)
        pipe.load_lora_weights("segmind/Segmind-VegaRT")
        pipe.fuse_lora()
        pipe.scheduler = LCMScheduler.from_config(pipe.scheduler.config)
    elif model == "sd-turbo":
        from diffusers import AutoPipelineForText2Image

        pipe = AutoPipelineForText2Image.from_pretrained("stabilityai/sd-turbo", torch_dtype=torch.float32)
    else:
        raise ValueError(model)
    pipe.set_progress_bar_config(disable=True)
    _pipes[model] = pipe
    return pipe


def generate(prompt: str, out: Path, model: str = "vega", width: int = 768, height: int = 960, seed: int = 0) -> dict:
    """Genera un'immagine e restituisce i tempi (secondi)."""
    t0 = time.time()
    pipe = _pipe(model)
    t1 = time.time()
    g = torch.Generator().manual_seed(seed)
    full = prompt + STYLE_SUFFIX
    if model == "vega":
        image = pipe(full, negative_prompt=NEGATIVE, num_inference_steps=4, guidance_scale=0,
                     width=width, height=height, generator=g).images[0]
    else:
        image = pipe(full, num_inference_steps=2, guidance_scale=0.0, width=512, height=512, generator=g).images[0]
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out, quality=92)
    return {"load_s": round(t1 - t0, 1), "gen_s": round(time.time() - t1, 1)}
