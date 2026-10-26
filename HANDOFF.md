# Passaggio di consegne: progetto @you.didnot.know

Dalla sessione cloud "INSTAGRAM AUTO" (session_01TKCwrzgTNNVppxeUhjKGUT) alla sessione
locale sul Mac di Andrea "Instagram @you.didnot.know". Aggiornato al 26 ottobre 2026.

## Il progetto in breve

Pagina Instagram in inglese **@you.didnot.know** ("You Did Not Know"), completamente
automatica: Andrea non vuole fare niente, Claude crea e pubblica tutto e impara dai
risultati. Lingua con Andrea: italiano.

- **Codice**: repo GitHub `visibellibusiness-ai/Claude`, branch `claude/instagram-auto-page-8qv9gl`
  (è l'unico branch; i workflow programmati girano da lì). Repo ancora **privato**.
- **Guida completa**: `README.md`. Rubrica news: `news/README.md`. Template: `templates/README.md`.
  Skill immagini: `.claude/skills/instagram-images/SKILL.md`.

## Cosa fa il sistema (GitHub Actions, `.github/workflows/post.yml`)

- **12:35 UTC rubrica news**: Claude cerca sul web le 5 notizie del giorno (2+ fonti
  autorevoli, la 5ª leggera, neutrale), scrive "what happened / why it matters / for you",
  crea carosello + Reel di ~20 s, pubblica (Reel come Trial Reel). `bot/news.py`.
- **17:40 e 23:40 UTC curiosità**: Claude sceglie argomento, formato (carosello/Reel/Trial
  Reel), testi, palette. `bot/generate.py`.
- **Apprendimento**: `bot/learn.py` legge le statistiche Instagram; una volta a settimana
  Claude riscrive la strategia in `posts/strategy.md`.
- **Grafica attuale**: stile "Mystery" (`bot/style.py`): fondo scuro cinematografico, serif
  Instrument Serif, testo Archivo, etichette Space Mono, accento ambra, scala tipografica
  fissa (stessa grandezza per ruolo su tutte le slide). Reel con zone sicure rispettate.
- **Musica Reel**: generatore proprio `bot/music.py`, preset "mystery" (4 variazioni).
- **Immagini**: copertina generata con Segmind Vega (Apache 2.0) su CPU (`bot/imagegen.py`).
  Con i template PSD: una foto per slide da Openverse / Wikimedia / NASA (Pexels e Unsplash
  se ci sono le chiavi), scelta da Claude con la vista, oppure generata; crediti in caption
  (`bot/images.py`).
- **Template Photoshop** (`bot/template.py`): se in `templates/` ci sono `cover.psd`,
  `slide.psd`, `end.psd`, il carosello usa quella grafica e cambia solo i livelli
  `IMAGE, TITLE, BODY, HIGHLIGHT, LABEL, NUMBER, HANDLE, CREDIT`. Le grandezze dei testi
  vengono allineate a `end.psd` in automatico (`ALIGN_SIZES_TO = "end"`).
- Senza chiavi configurate il giro si salta senza errori.

## Decisioni già prese con Andrea

- Nome: You Did Not Know, handle `@you.didnot.know`, nome visualizzato `You Did Not Know | Facts`.
- Bio scelta (88 caratteri):
  `Facts you didn't know. Until now. 🗂️` / `New file every day · checked sources` / `Save & share ↓`
- Stile Mystery (scartati Riso "troppo trash e poco leggibile", Museum, Tabloid). Musica mystery.
- Testi grandi e coerenti tra le slide: è una richiesta esplicita di Andrea.
- Immagine profilo: `assets/profile/avatar_nome.jpg` (consigliata) o `avatar_domanda.jpg`.
  Copertina Facebook: `assets/profile/facebook_cover.jpg`.
- News integrate nella stessa pagina, in inglese, pubblicazione automatica (niente email,
  niente Canva: Andrea non vuole verificare nulla).
- Modello di riferimento indicato da Andrea: profilo Instagram **@insegnocose**
  (https://www.instagram.com/insegnocose) — non ancora analizzato.

## Da fare (in ordine)

1. **Template Photoshop** (sul Mac, con l'uso del computer). Andrea ha già creato
   `cover.psd`, `slide.psd`, `end.psd` con `templates/crea_template.jsx`.
   - Allineare le grandezze dei testi di cover e slide a quelle di `end.psd`
     (`TITLE, BODY, LABEL, HANDLE`; `NUMBER, CREDIT, HIGHLIGHT` restano). C'è lo script
     `templates/allinea_font.jsx` che lo fa; poi allargare le caselle se un testo esce.
   - Non rinominare i livelli in maiuscolo.
   - Caricare i tre PSD nel repo in `templates/` sul branch `claude/instagram-auto-page-8qv9gl`
     (o su Google Drive in una cartella "templates").
   - Font dei template: `templates/fonts/` (Instrument Serif, Archivo-Regular, Space Mono).
2. **Analizzare @insegnocose** con il browser di Andrea (è loggato): struttura dei
   caroselli, gancio della copertina, quantità di testo, grafica, CTA. Salvare l'analisi
   (es. `docs/insegnocose.md` nel repo) e adattare template e prompt (`bot/generate.py`,
   `bot/news.py`) a quel modello.
3. **Post di prova con i template veri**: renderizzarlo (`python -m bot.main create --post-file ...`
   oppure il workflow) e confrontarlo con Photoshop: verificare in particolare i testi
   (lettura degli stili dai livelli di testo non ancora testata su un PSD reale).
4. **Configurazione delle chiavi** (solo Andrea può, guidarlo; passi dettagliati nel README,
   sezione "Configurazione una tantum"): account Creator, Pagina Facebook collegata, app
   Meta con caso d'uso Instagram + Facebook login, token della Pagina che non scade,
   chiave Anthropic, Secrets GitHub `ANTHROPIC_API_KEY`, `IG_USER_ID`, `IG_ACCESS_TOKEN`
   (facoltativi `PEXELS_API_KEY`, `UNSPLASH_ACCESS_KEY`), repo da rendere pubblico.
5. **Primo post dal vivo**: Actions → "Pubblica post Instagram" → Run workflow
   (`facts` o `news`), poi controllare i log e sistemare eventuali errori dell'API.

## Limiti noti

- Pubblicazione, lettura statistiche, ricerca web delle news e scelta foto con Claude
  sono stati provati solo con API simulate: vanno verificati dal vivo con le chiavi.
- Il Reel resta nello stile Mystery (i template PSD sono 4:5).
- Registrazione come testata giornalistica: da verificare con un legale.
