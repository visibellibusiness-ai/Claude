"""Genera il contenuto di un post (carosello) con Claude."""

import json

import anthropic

from bot import config

SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {"type": "string", "description": "Argomento breve, usato per evitare ripetizioni"},
        "hook": {"type": "string", "description": "Titolo della prima slide, max 9 parole, irresistibile"},
        "slides": {
            "type": "array",
            "description": "Da 5 a 7 slide, ognuna una curiosità o un passaggio della storia",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Max 6 parole"},
                    "body": {"type": "string", "description": "Max 32 parole, frasi corte"},
                },
                "required": ["title", "body"],
                "additionalProperties": False,
            },
        },
        "cta": {"type": "string", "description": "Ultima slide: invito a salvare/condividere/commentare, max 14 parole"},
        "caption": {"type": "string", "description": "Caption Instagram 60-120 parole, con domanda finale per i commenti"},
        "hashtags": {"type": "array", "items": {"type": "string"}, "description": "8-12 hashtag italiani pertinenti, senza #"},
        "sources": {"type": "array", "items": {"type": "string"}, "description": "Fonti autorevoli a supporto dei fatti"},
    },
    "required": ["topic", "hook", "slides", "cta", "caption", "hashtags", "sources"],
    "additionalProperties": False,
}

SYSTEM = f"""Sei il content creator della pagina Instagram italiana "{config.PAGE_NAME}".
Nicchia: {config.NICHE}.

Obiettivo: massimizzare salvataggi, condivisioni e commenti, che sono i segnali che
l'algoritmo di Instagram premia di più.

Regole:
- Usa solo fatti reali, ben documentati e verificabili. Niente miti, leggende metropolitane
  o numeri inventati. Se un dato è approssimativo, dillo ("circa").
- La prima slide è un gancio che crea curiosità immediata (es. "Il tuo corpo fa questo
  ogni notte senza che tu lo sappia").
- Ogni slide successiva dà una ricompensa concreta e fa venir voglia di scorrere.
- Italiano naturale, diretto, frasi brevi, zero tono da enciclopedia.
- Niente emoji nelle slide; nella caption al massimo 3.
- La caption chiude con una domanda semplice a cui è facile rispondere nei commenti."""


def generate_post(category: str, recent_topics: list[str]) -> dict:
    client = anthropic.Anthropic()
    avoid = "\n".join(f"- {t}" for t in recent_topics[-60:]) or "(nessuno)"
    prompt = (
        f"Crea un nuovo carosello sulla categoria: {category}.\n\n"
        f"Argomenti già pubblicati, da NON ripetere:\n{avoid}"
    )
    response = client.beta.messages.create(
        model=config.MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={
            "effort": "high",
            "format": {"type": "json_schema", "schema": SCHEMA},
        },
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason != "end_turn":
        raise RuntimeError(f"Generazione interrotta: stop_reason={response.stop_reason}")
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)
