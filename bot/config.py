"""Impostazioni di base. Stile, argomenti e formato li decide Claude e li
affina in base alle prestazioni (vedi posts/strategy.md)."""

PAGE_NAME = "You Did Not Know"
PAGE_HANDLE = "@you.didnot.know"

NICHE = (
    "surprising, verified facts about science, the human body, animals, history, "
    "space, psychology and the world, for an international English-speaking audience aged 18-45"
)

# Solo spunti iniziali: Claude è libero di uscirne se i dati lo suggeriscono
STARTING_IDEAS = [
    "human body",
    "animals",
    "space",
    "history",
    "psychology",
    "everyday science",
    "geography and strange places",
    "food",
    "technology",
    "oceans",
]

MODEL = "claude-opus-5-5"

# Grafica carosello (formato 4:5 consigliato da Instagram per il feed)
WIDTH, HEIGHT = 1080, 1350
# Stile di marca (bot/style.py): "mystery", in coppia con la musica.
# Claude sceglie solo la palette (5 varianti) dentro lo stile.
BRAND_STYLE = "mystery"
# Generi musicali dei Reel (bot/music.py): ogni Reel ne usa uno diverso dagli ultimi due (vedi main.pick_music)
# Esperimento sui Reel (9/11/2026): tre versioni a rotazione per capire cosa abbassa il tasso di salto.
# Il Trial Reel non è disponibile (Instagram: "Trial Reel Not Enough Followers"), quindi escono come Reel normali.
# Per spegnere l'esperimento basta mettere VARIANT_EXPERIMENT = False.
VARIANT_EXPERIMENT = True
VARIANTS = ["short", "answer", "direct"]


def next_variant(history: list) -> str:
    """La versione che tocca al prossimo Reel: si ruota tra quelle già usate (campo "variant" nello storico)."""
    used = sum(1 for h in history if h.get("variant"))
    return VARIANTS[used % len(VARIANTS)]


MUSIC_PRESETS = ["mystery", "lofi", "documentary"]  # curious_pop e chill_house esistono in music.py ma Andrea li ha bocciati (30/10/2026)
# Immagine di copertina generata con un modello open source (bot/imagegen.py)
COVER_ART = True

# Ogni quanti giorni Claude rivede la strategia in base ai risultati
REFLECT_EVERY_DAYS = 7
# Dopo quante ore dalla pubblicazione le statistiche sono abbastanza stabili
INSIGHTS_MIN_AGE_HOURS = 48
