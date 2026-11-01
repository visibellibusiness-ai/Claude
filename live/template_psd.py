"""Template Photoshop del tool risultati live.

Stessa tecnica del bot (`bot/template.py`): la grafica la disegna Andrea in
Photoshop, il tool sostituisce solo i livelli di testo, che mantengono font,
corpo, colore, interlinea e allineamento del file. I template vivono in
`live/templates/`:

  story-match.psd    Story partita finita (1080x1920)
  story-phase.psd    Story risultati di fase (1080x1920)
  post-cover.psd     Cover del post celebrativo (1080x1440)
  post-phase.psd     Slide del cammino (1080x1440)
  post-congrats.psd  Slide finale Congrats (1080x1440)

Livelli riconosciuti (nome esatto, con o senza {{...}}; i testi su più righe
vanno in caselle di testo):
  BADGE        pillola contesto (categoria · fase)
  TOURNAMENT   nome del torneo
  PHASE        nome della fase (QUARTER-FINALS...)
  WINNERS      vincitori, un nome per riga
  TAGS         handle Instagram dei vincitori
  LABEL        "WIN" / "CHAMPIONS" / "WINNERS"
  SCORE        punteggio
  LOSERS       sconfitti, un nome per riga
  ROW1..ROW5   una partita per riquadro nelle slide di fase
               (3 righe: vincitori / "d. sconfitti" / punteggio)
  EVENT        nome della categoria
  TITLE        titolo grande ("CONGRATS")
  IMAGE        rettangolo riempito con la foto (cover e congrats)
Ogni altro livello resta come disegnato. I font dei template vanno in
`templates/fonts/` (c'è già la cartella del bot: Fredoka inclusa da qui).

Senza il PSD corrispondente si usa il renderer Pillow di live/render.py.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "live" / "templates"

SLOTS = {"BADGE", "TOURNAMENT", "PHASE", "WINNERS", "TAGS", "LABEL", "SCORE", "LOSERS",
         "ROW1", "ROW2", "ROW3", "ROW4", "ROW5", "EVENT", "TITLE", "IMAGE"}


@lru_cache(maxsize=None)
def load(name: str):
    """Il template PSD se esiste e si legge, altrimenti None (ripiego Pillow)."""
    path = TEMPLATES / f"{name}.psd"
    if not path.exists():
        return None
    try:
        import bot.template as bt
    except ImportError as e:  # psd-tools assente: si usa il ripiego Pillow
        print(f"::warning::Template {path.name} presente ma psd-tools manca ({e}): uso il ripiego")
        return None
    old_slots = bt.SLOTS
    bt.SLOTS = SLOTS  # _slot() legge il set del modulo del bot
    try:
        return bt.PsdTemplate(path)
    except Exception as e:
        print(f"::warning::Template {path.name} non utilizzabile, uso il ripiego: {e}")
        return None
    finally:
        bt.SLOTS = old_slots


def render(name: str, texts: dict[str, str], image: Path | None = None):
    """Immagine dal template, o None se il template manca."""
    tpl = load(name)
    if tpl is None:
        return None
    return tpl.render(texts, image)
