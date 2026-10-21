"""Impostazioni di base. Stile, argomenti e formato li decide Claude e li
affina in base alle prestazioni (vedi posts/strategy.md)."""

PAGE_NAME = "Did You Know?"
PAGE_HANDLE = "@didyouknow.daily.facts"  # aggiorna con l'handle reale dell'account

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
# Stile di marca (bot/style.py): "riso", "museum" o "tabloid".
# Claude sceglie solo la palette (5 varianti) dentro lo stile.
BRAND_STYLE = "riso"
# Generi musicali dei Reel (bot/music.py) tra cui Claude può scegliere
MUSIC_PRESETS = ["mystery"]

# Ogni quanti giorni Claude rivede la strategia in base ai risultati
REFLECT_EVERY_DAYS = 7
# Dopo quante ore dalla pubblicazione le statistiche sono abbastanza stabili
INSIGHTS_MIN_AGE_HOURS = 48
