# Pagina Instagram automatica: "You Did Not Know" (@you.didnot.know)

Pagina in inglese di curiosità verificate (corpo umano, animali, spazio, storia, psicologia…)
che si gestisce da sola: **due post al giorno**, caroselli o Reel (anche Trial Reel),
generati, disegnati e pubblicati senza intervento umano.

## Perché questa nicchia

- **I caroselli di curiosità generano tanti salvataggi e condivisioni**, i segnali
  che l'algoritmo di Instagram premia di più per arrivare a chi non ti segue.
- **Non serve un volto né riprese**: tutto si produce in automatico.
- **I contenuti non finiscono mai**: Claude sceglie argomenti sempre nuovi e
  tiene uno storico di quelli già usati, così i post non si ripetono.
- **Pubblico ampio e internazionale** (18-45, in inglese) e argomenti adatti ai brand, utile se in
  futuro vuoi monetizzare.

## Come funziona

Ogni giorno alle 13:40 e alle 23:40 UTC (pomeriggio in Europa / mattina e sera negli USA) GitHub Actions esegue
`.github/workflows/post.yml`:

1. `bot/learn.py` legge le statistiche dei post usciti (copertura, salvataggi,
   condivisioni, like, commenti, follower). Una volta a settimana Claude le analizza
   e riscrive la propria strategia in `posts/strategy.md`.
2. `bot/generate.py`: Claude decide **tutto** del post successivo (formato,
   argomento, taglio, numero di slide, testi, caption, hashtag, colori, etichette), seguendo
   la sua strategia e i dati, e provando ogni tanto qualcosa di nuovo.
3. `bot/render.py` disegna le slide 1080×1350 (carosello); `bot/reel.py` crea il
   Reel 1080×1920 con testo animato e musica generata da `bot/music.py` (niente
   problemi di copyright). La grafica segue lo stile di marca definito in
   `bot/style.py` (stile "Riso", con scala tipografica fissa); Claude sceglie la
   palette e i numeri o le parole da mettere in grande. Musica: "mystery" con
   quattro variazioni.
4. Le immagini vengono committate nel repo, così hanno un indirizzo pubblico.
5. `bot/publish.py` pubblica con l'API ufficiale di Instagram. I Reel vengono
   caricati direttamente; i Trial Reel li vede prima solo chi non ti segue, e
   Instagram li condivide con i follower se vanno bene.
6. `posts/history.json` registra ogni post con stile e risultati.

Lo stile grafico è fisso; argomenti, formati e testi li sceglie Claude, che all'inizio
sperimenta e poi si concentra su quello che rende di più. In `posts/strategy.md` puoi
leggere cosa ha imparato.

I file JSON in `posts/queue/` escono per primi: c'è già il primo post pronto.

## Configurazione una tantum (circa 20 minuti, poi non tocchi più niente)

Questi passaggi richiedono il tuo telefono e i tuoi account, quindi vanno fatti a mano.

1. **Crea l'account Instagram** (`@you.didnot.know`), poi in
   Impostazioni → Tipo di account passa a **Account professionale → Creator**.
   Metti foto profilo e bio (sotto trovi una proposta).
2. **Crea una Pagina Facebook** e collegala all'account Instagram
   (Instagram → Impostazioni → Centro gestione account).
3. **Crea un'app Meta** su developers.facebook.com → Le mie app → Crea app →
   tipo "Business". Aggiungi il prodotto **Instagram** (API con login di Facebook).
4. Da **Graph API Explorer** genera un token con i permessi
   `instagram_basic`, `instagram_content_publish`, `instagram_manage_insights`, `pages_show_list`,
   `pages_read_engagement`, `business_management`, poi convertilo in
   **token di lunga durata** (Strumenti → Debug token di accesso → Estendi).
5. Con il token di lunga durata, in Graph API Explorer esegui
   `me/accounts?fields=name,access_token,instagram_business_account` e copia:
   - l'`id` dentro `instagram_business_account` → è `IG_USER_ID`;
   - l'`access_token` della Pagina → è `IG_ACCESS_TOKEN`. Ottenuto da un token
     di lunga durata, **non scade** (verificalo nel Debug token: "Scade: mai").
6. Crea una **chiave API Anthropic** su console.anthropic.com.
7. Nel repo GitHub: Settings → Secrets and variables → Actions → aggiungi
   `ANTHROPIC_API_KEY`, `IG_USER_ID`, `IG_ACCESS_TOKEN`.
8. **Rendi pubblico il repo** (Settings → General → Change visibility): Instagram
   deve poter scaricare le immagini da `raw.githubusercontent.com`.
9. Unisci questo branch nel branch principale. Da lì il workflow parte da solo;
   per il primo post subito vai su Actions → "Pubblica post Instagram" → Run workflow.

Se usi il token utente invece di quello della Pagina, scade dopo circa 60 giorni
e va rinnovato nel secret `IG_ACCESS_TOKEN`.

### Bio consigliata

Nome visualizzato: `You Did Not Know | Facts`

```
Facts you didn't know. Until now. 🗂️
New file every day · checked sources
Save & share ↓
```

(88 caratteri: il limite di Instagram è 150, a capo compresi; il nome
visualizzato ne ha 24 su 30.)

Immagine del profilo: `assets/profile/avatar_blu_rosa.jpg` (1080×1080, come le copertine Riso).

## Impostazioni di base

- Nome e handle della pagina, stile grafico (`BRAND_STYLE`) e generi musicali
  ammessi (`MUSIC_PRESETS`): `bot/config.py`
- Orari di pubblicazione: `cron` in `.github/workflows/post.yml` (orari in UTC)

## Costi indicativi

- GitHub Actions: gratis per i repo pubblici.
- API Claude: pochi centesimi per post.
- Instagram API: gratis.
