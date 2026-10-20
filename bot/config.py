"""Impostazioni della pagina. Cambia qui nicchia, nome e stile."""

PAGE_NAME = "Did You Know?"
PAGE_HANDLE = "@didyouknow.daily.facts"  # aggiorna con l'handle reale dell'account

NICHE = (
    "surprising, verified facts about science, the human body, animals, history, "
    "space, psychology and the world, for an international English-speaking audience aged 18-45"
)

# Rotazione delle categorie: una diversa a ogni post per varietà
CATEGORIES = [
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
THEMES = [
    {"bg": "#0E1116", "fg": "#FFFFFF", "accent": "#FFD23F"},
    {"bg": "#111827", "fg": "#F9FAFB", "accent": "#34D399"},
    {"bg": "#1A1033", "fg": "#FFFFFF", "accent": "#FF6B9A"},
    {"bg": "#0B1D2E", "fg": "#FFFFFF", "accent": "#4FC3F7"},
    {"bg": "#1E1410", "fg": "#FFF7ED", "accent": "#FB923C"},
]
