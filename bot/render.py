"""Disegna le slide del carosello come JPEG 1080x1350 con lo stile di marca."""

from pathlib import Path

from bot import config
from bot.style import STYLES, flatten

MARGIN = 90


def make_style(post: dict, index: int):
    design = post.get("design", {})
    name = config.BRAND_STYLE
    palette = design.get("palette", index)
    post["design_used"] = {"style": name, "palette": palette}
    return STYLES[name](palette=palette, seed=index * 7 + 3)


def slide_data(post: dict, index: int) -> list[tuple[str, dict]]:
    """Le scene di un post, comuni a carosello e Reel."""
    design = post.get("design", {})
    total = len(post["slides"])
    scenes = [("cover", {
        "hook": post["hook"],
        "label": design.get("cover_label", post.get("category", "")),
        "swipe": design.get("swipe_text", "Swipe"),
        "category": post.get("category", ""),
        "index": index + 1,
        "image": post.get("cover_image"),
    })]
    for n, s in enumerate(post["slides"], start=1):
        scenes.append(("fact", {
            "n": n, "total": total, "title": s["title"], "body": s["body"],
            "highlight": s.get("highlight", ""), "index": index + 1,
            "label": s.get("label", ""), "points": s.get("points"),
        }))
    scenes.append(("cta", {
        "cta": post["cta"], "handle": config.PAGE_HANDLE, "index": index + 1,
        "follow_line": design.get("follow_line", "a new mind-blowing fact every day"),
    }))
    return scenes


def center_content(style, scenes, w, h, safe) -> None:
    """Sposta il contenuto di tutte le slide della stessa quantità, così il blocco
    più alto risulta centrato e le posizioni restano identiche tra le slide."""
    style.content_dy = 0
    facts = [style.slide(k, d, w, h, safe)[1] for k, d in scenes if k == "fact"]
    if facts:
        lowest = max(fg.getchannel("A").getbbox()[3] for fg in facts)
        style.content_dy = max(0, int((safe[3] - lowest) * 0.5))


def render_post(post: dict, out_dir: Path, theme_index: int) -> list[Path]:
    style = make_style(post, theme_index)
    out_dir.mkdir(parents=True, exist_ok=True)
    safe = (MARGIN, MARGIN, config.WIDTH - MARGIN, config.HEIGHT - MARGIN)
    scenes = slide_data(post, theme_index)
    style.plan(scenes, safe)
    center_content(style, scenes, config.WIDTH, config.HEIGHT, safe)
    paths = []
    for i, (kind, data) in enumerate(scenes, start=1):
        img = flatten(*style.slide(kind, data, config.WIDTH, config.HEIGHT, safe))
        p = out_dir / f"slide_{i:02d}.jpg"
        img.save(p, "JPEG", quality=92)
        paths.append(p)
    return paths


def _slide_texts(kind: str, data: dict, credit: str | None) -> dict:
    """Testi per i livelli segnaposto dei template Photoshop."""
    base = {"HANDLE": config.PAGE_HANDLE, "CREDIT": f"Photo: {credit}" if credit else ""}
    if kind == "cover":
        return {**base, "TITLE": data["hook"], "LABEL": data.get("label", "")}
    if kind == "fact":
        body = data["body"]
        if data.get("points"):
            body = "\n".join(f"{label.title()}: {txt}" for label, txt in data["points"])
        return {**base, "TITLE": data["title"], "BODY": body, "HIGHLIGHT": data.get("highlight", ""),
                "LABEL": data.get("label", ""), "NUMBER": f"{data['n']:02d}/{data['total']:02d}"}
    return {**base, "TITLE": data["cta"], "BODY": data.get("follow_line", "")}


def render_with_templates(post: dict, out_dir: Path, templates: dict) -> list[Path]:
    """Carosello con i template PSD di Andrea: cambiano solo testi e immagini."""
    out_dir.mkdir(parents=True, exist_ok=True)
    scenes = slide_data(post, 0)
    images = [post.get("cover_image")] + [s.get("image") for s in post["slides"]] + [None]
    credits = [post.get("cover_credit")] + [s.get("credit") for s in post["slides"]] + [None]
    paths = []
    for i, ((kind, data), image, credit) in enumerate(zip(scenes, images, credits), start=1):
        name = {"cover": "cover", "fact": "slide"}.get(kind, "end")
        tpl = templates.get(name) or templates["slide"]
        img = tpl.render(_slide_texts(kind, data, credit), image)
        p = out_dir / f"slide_{i:02d}.jpg"
        img.save(p, "JPEG", quality=92)
        paths.append(p)
    post["design_used"] = {"style": "template"}
    return paths
