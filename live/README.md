# Tool risultati live tornei

Scraping periodico dei risultati di un torneo, grafiche Story nello stile
PickleballSpot e pubblicazione su Instagram (@pickleball.spot). Collaudo:
2026 English Nationals su Picklebook. Scheda progetto:
`idee/tool-risultati-live-tornei.md`.

## Come gira

`.github/workflows/live-tornei.yml`, ogni 30 minuti (al minuto 7 e 37):

1. `python -m live.main run` — scraping della piattaforma, confronto con lo
   stato, grafiche nuove in `posts/live/<slug>/<timestamp>/`
2. commit+push delle immagini (devono stare a un indirizzo pubblico: Instagram
   le scarica da `raw.githubusercontent.com`, come il bot di @you.didnot.know)
3. `python -m live.main publish` — pubblica le Story in coda via Graph API
   (`bot/publish.py`), poi committa la coda aggiornata

Il giro programmato parte solo se `live/torneo.json` ha `"attivo": true`.
Il lancio manuale (workflow_dispatch) parte sempre; con `solo_grafiche: true`
genera senza pubblicare.

## Configurazione: `live/torneo.json`

- `adapter`: per ora `picklebook`; ogni piattaforma nuova è un modulo in
  `live/adapters/` che restituisce il formato comune di `live/model.py`
- `base_url`: la pagina del torneo sulla piattaforma
- `events`: filtro sui nomi delle categorie (sottostringhe, `[]` = tutte)
- `match_stories`: fasi con una Story per ogni partita finita
- `phase_stories`: fasi con la Story riassuntiva quando la fase si chiude
  (spezzata in più Story bilanciate se le partite sono tante: leggibilità prima
  di tutto)
- `handles`: mappa `"Nome Cognome" -> "@handle"` per i tag in grafica (le
  Story via API accettano solo l'immagine: niente sticker di menzione)

## Stato e coda

`live/state/<slug>.json`: partite e fasi già uscite (niente doppioni tra i
giri) e coda delle Story generate ma ancora da pubblicare. Se una
pubblicazione fallisce, la Story resta in coda e si riprova al giro dopo.

## Chiavi (secrets del repo)

- `PBS_IG_USER_ID`, `PBS_IG_ACCESS_TOKEN`: account Instagram di PickleballSpot
  (token Instagram Login, come il bot esistente). Senza chiavi il giro genera
  e accoda, con un avviso nel log, e la pubblicazione resta ferma.

## Sviluppo con la rete chiusa

La sessione cloud ha i domini esterni bloccati: lo scraping si studia con
`.github/workflows/live-probe.yml` (sonda di sola lettura che naviga le pagine
risultati e le pubblica sul branch `probe`), poi si sviluppa in locale sulle
pagine vere. `live/probe.py`.

## Ancora da fare

- Logo ufficiale in `assets/logos/` (oggi ripiego testuale in Fredoka)
- Story vincitore con la foto di Andrea/del gestore + post celebrativo di fine
  torneo (copertina podio, fasi, slide finale "Congrats" ricondivisibile)
- Canale di ingresso foto (cartella Drive osservata)
- Mappa giocatori → handle
- Adapter: PPA, OpenPlay, FITP/TPRA, Pickleball Global, piattaforma "React"
