---
name: instagram-images
description: Trovare o creare le immagini dei post di @you.didnot.know - foto con licenza libera da archivi online (con credito alla fonte) oppure immagini generate con il modello open source, scelta della migliore, inserimento nei template Photoshop. Usala ogni volta che si lavora su immagini, copertine, slide, template PSD, crediti fotografici o descrizioni per il generatore di immagini di questo progetto.
---

# Immagini per i post di @you.didnot.know

Codice: `bot/images.py` (ricerca, scelta, download, crediti), `bot/imagegen.py`
(generazione con Segmind Vega), `bot/template.py` (template PSD), `templates/README.md`
(come preparare i template).

## 1. Foto reale o immagine generata?

| Il soggetto è… | Usa |
|---|---|
| una cosa reale e riconoscibile: animale, luogo, oggetto, fenomeno, opera d'arte storica | **foto reale** da archivio (più credibile, più condivisa) |
| spazio, pianeti, missioni | **NASA** per prima (pubblico dominio, qualità altissima) |
| un concetto astratto: tempo, memoria, economia, emozioni | **immagine generata** (metafora visiva) |
| una notizia su persone reali | **mai foto di persone**: oggetto simbolico o luogo, reale o generato |

Per ogni slide prepara sempre **entrambi**: `image_query` (2-4 parole in inglese, il
soggetto concreto, es. `octopus underwater`) e `image_prompt` (la scena per il
generatore). Il sistema prova prima la ricerca e usa la generazione solo se non trova
niente di adatto.

## 2. Licenze ammesse (uso commerciale)

Solo: **CC0, pubblico dominio, CC BY, CC BY-SA, licenza Pexels, licenza Unsplash, NASA**.
Mai: CC BY-NC (non commerciale), CC BY-ND (non modificabile: le ritagliamo e ci
scriviamo sopra), immagini senza licenza chiara, screenshot, immagini di testate.
`bot/images.py` filtra già le licenze; non aggirare il filtro.

## 3. Crediti

- Ogni foto trovata online porta autore, licenza e link (`credit`, `source`).
- I crediti vanno **sempre** nella caption, in fondo, con `credits_line()`:
  `📷 Jane Doe (CC BY 4.0) via wikimedia · NASA/JPL (public domain (NASA)) via nasa`.
- Se il template ha il livello `CREDIT`, il credito va anche sulla slide.
- CC BY-SA: l'immagine modificata resta CC BY-SA; il credito con la licenza basta.
- Le immagini generate non hanno credito.

## 4. Scelta della foto migliore

`pick()` mostra a Claude fino a 8 miniature e chiede la migliore. Scarta: testo
visibile, filigrane, loghi, collage, volti riconoscibili di persone private, contenuti
crudi, soggetto sbagliato, foto sfocate o che non reggono il taglio verticale 4:5.
Se nessuna è adatta restituisce -1: allora si genera.

## 5. Descrizioni per il generatore (`image_prompt`)

- Una sola scena concreta, max 30 parole, in inglese: soggetto + ambiente + luce.
- Oggetti e metafore, **mai persone, volti o mani**, niente testo, niente schermi con
  scritte (il modello inventa lettere finte).
- Lo stile viene aggiunto da `imagegen.STYLE_SUFFIX` (scuro, cinematografico, luci
  ambra): non ripeterlo nella descrizione.
- Buono: `a single golden key balanced on a stack of old coins, thin thread holding it`.
- Cattivo: `economy news concept with charts and people` (astratto, persone, grafici).

## 6. Template Photoshop

- I livelli segnaposto si chiamano `IMAGE`, `TITLE`, `BODY`, `HIGHLIGHT`, `LABEL`,
  `NUMBER`, `HANDLE`, `CREDIT` (vedi `templates/README.md`).
- La foto viene ritagliata per riempire il riquadro di `IMAGE` (taglio leggermente
  sopra il centro, dove di solito sta il soggetto).
- Dopo una modifica ai template, renderizza un post di prova e confrontalo con il PSD
  aperto in Photoshop prima di lasciarlo andare in automatico.

## 7. Verifica prima di pubblicare

- Ogni slide ha un'immagine (trovata o generata) o, in mancanza, il fondo del template.
- La caption contiene i crediti di tutte le foto online.
- Nessuna immagine con persone reali riconoscibili nelle notizie.
