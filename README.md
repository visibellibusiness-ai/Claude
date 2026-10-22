# Pagina Instagram automatica: "You Did Not Know" (@you.didnot.know)

Pagina in inglese di curiosità verificate (corpo umano, animali, spazio, storia, psicologia…)
che si gestisce da sola: **ogni giorno una rubrica news** (carosello + Reel con le 5
notizie del giorno) e **due post di curiosità** (caroselli o Reel, anche Trial Reel),
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

GitHub Actions esegue `.github/workflows/post.yml` ogni giorno alle 12:35 UTC per la
rubrica news (vedi `news/README.md`) e alle 17:40 e 23:40 UTC per le curiosità:

1. `bot/learn.py` legge le statistiche dei post usciti (copertura, salvataggi,
   condivisioni, like, commenti, follower). Una volta a settimana Claude le analizza
   e riscrive la propria strategia in `posts/strategy.md`.
2. `bot/generate.py`: Claude decide **tutto** del post successivo (formato,
   argomento, taglio, numero di slide, testi, caption, hashtag, colori, etichette), seguendo
   la sua strategia e i dati, e provando ogni tanto qualcosa di nuovo.
3. `bot/render.py` disegna le slide 1080×1350 (carosello); `bot/reel.py` crea il
   Reel 1080×1920 con testo animato e musica generata da `bot/music.py` (niente
   problemi di copyright). La grafica segue lo stile di marca definito in
   `bot/style.py` (stile "Mystery": fondo scuro cinematografico, titoli serif,
   un colore d'accento, scala tipografica fissa), in coppia con la musica
   "mystery" (quattro variazioni). Claude sceglie la palette e i numeri o le
   parole da mettere in grande.
   La copertina ha un'immagine generata sul server con **Segmind Vega** (modello
   open source, licenza Apache 2.0) a partire da una descrizione scritta da Claude:
   oggetti e metafore simboliche, mai persone. Il modello resta salvato tra un giro
   e l'altro; se la generazione fallisce, il post esce con la copertina tipografica.
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
3. **Crea l'app Meta** (da computer, su developers.facebook.com). Le voci possono
   apparire in inglese o in italiano: le trovi scritte in entrambe le lingue.
   1. Entra con il tuo Facebook e premi **Inizia / Get Started**: accetta le
      condizioni e conferma email o telefono (solo la prima volta).
   2. In alto a destra **Le mie app / My Apps** → **Crea app / Create App**.
   3. *Dettagli dell'app*: nome `You Did Not Know Bot`, la tua email → **Avanti**.
   4. *Casi d'uso*: scegli **Gestisci messaggi e contenuti su Instagram /
      Manage messaging & content on Instagram** → **Avanti**.
   5. *Business*: scegli **Non voglio collegare un portfolio aziendale per ora /
      I don't want to connect a business portfolio yet** → **Avanti**.
   6. *Requisiti* e *Panoramica*: **Avanti** → **Vai alla dashboard / Go to dashboard**
      (può chiederti la password di Facebook).
   7. Nella dashboard: **Casi d'uso / Use cases** → sul caso Instagram premi
      **Personalizza / Customize** → scegli **Configurazione API con accesso tramite
      Facebook / API setup with Facebook login**.
   8. Nella lista dei permessi controlla che ci siano `instagram_basic`,
      `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`,
      `business_management`, e aggiungi `instagram_manage_insights` (**Aggiungi / Add**).
   L'app può restare in modalità sviluppo: sei l'amministratore, quindi non serve la
   revisione di Meta né la verifica aziendale.
4. **Genera il token** su developers.facebook.com/tools/explorer (*Graph API Explorer*).
   1. A destra, in **Meta App**, scegli `You Did Not Know Bot`; in **User or Page**
      scegli **Get User Access Token**.
   2. In **Permissions** aggiungi uno per uno: `instagram_basic`,
      `instagram_content_publish`, `instagram_manage_insights`, `pages_show_list`,
      `pages_read_engagement`, `business_management`.
   3. Premi **Generate Access Token**: nella finestra continua con il tuo profilo,
      seleziona la Pagina **You Did Not Know** e l'account **@you.didnot.know**,
      lascia attivi tutti i permessi → **Salva / Save**.
   4. Rendilo di lunga durata: premi la **i** blu accanto al token → **Open in Access
      Token Tool** → in fondo **Extend Access Token** → copia il nuovo token.
5. **Prendi i due valori finali**, sempre nel Graph API Explorer:
   1. Incolla il token appena esteso nel campo **Access Token**.
   2. Nella barra della richiesta (accanto a **GET**) scrivi
      `me/accounts?fields=name,access_token,instagram_business_account` → **Submit**.
   3. Nella risposta, nel blocco della Pagina "You Did Not Know", copia:
      - il numero `id` dentro `instagram_business_account` → è **IG_USER_ID**;
      - il valore `access_token` della Pagina (lungo, inizia con `EAA`) → è
        **IG_ACCESS_TOKEN**.
   4. Controllo: su developers.facebook.com/tools/debug/accesstoken incolla
      IG_ACCESS_TOKEN → **Debug**: alla voce **Expires / Scadenza** deve esserci
      **Never / Mai**. Così non dovrai mai rinnovarlo.
6. Crea una **chiave API Anthropic** su console.anthropic.com.
7. Nel repo GitHub: Settings → Secrets and variables → Actions → aggiungi
   `ANTHROPIC_API_KEY`, `IG_USER_ID`, `IG_ACCESS_TOKEN`.
8. **Rendi pubblico il repo** (Settings → General → Change visibility): Instagram
   deve poter scaricare le immagini da `raw.githubusercontent.com`.
9. Fatto. Il workflow parte da solo agli orari previsti; per il primo post subito vai
   su Actions → "Pubblica post Instagram" → Run workflow (scegli `facts` o `news`).

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

Immagine del profilo: `assets/profile/avatar_nome.jpg` oppure `avatar_domanda.jpg` (1080×1080, stile Mystery).

Copertina della Pagina Facebook: `assets/profile/facebook_cover.jpg` (1640×924; il testo
sta nella fascia centrale, visibile sia da computer sia da telefono).

## Impostazioni di base

- Nome e handle della pagina, stile grafico (`BRAND_STYLE`) e musica
  (`MUSIC_PRESETS`): `bot/config.py`
- Orari di pubblicazione: `cron` in `.github/workflows/post.yml` (orari in UTC)

## Costi indicativi

- GitHub Actions: gratis per i repo pubblici (con l'immagine di copertina ogni giro
  dura qualche minuto in più).
- API Claude: pochi centesimi per post.
- Instagram API: gratis.
