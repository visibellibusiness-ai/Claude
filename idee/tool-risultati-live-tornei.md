# Tool risultati live: scheda progetto (da sviluppare in una chat dedicata)

Idea di Andrea (31 ottobre 2026). Obiettivo: coprire i tornei sui canali
PickleballSpot con risultati aggiornati in automatico, e insieme collaudare il
servizio "risultati live con AI" da vendere ai circoli (vedi
`offerte/pickleballspot-circoli.md`). Primo uso: il prossimo torneo PPA.

## Multi-piattaforma per progetto

Il tool NON è legato al PPA: gli si indica il torneo e la piattaforma, e lui fa
lo scraping lì. Architettura ad adapter: un modulo di lettura per piattaforma,
che restituisce i risultati in un formato comune; il resto (template, Stories,
post, trigger fine tabellone) è identico per tutte.

Piattaforme da supportare (con prove su ciascuna):

1. **PPA** (ppatour.com) — il primo collaudo
2. **"React"** — nome da confermare con Andrea (trascrizione vocale ambigua:
   Rankedin? R2 Sports? altro?)
3. **OpenPlay** (openplay.cloud) — qui meglio ancora via feed/API appena esiste
   (fase 2 di `offerte/openplay-integrazione.md`)
4. **Pickleball Global** — se fattibile (usata anche per iscrizioni di tappe
   italiane)
5. **FITP / TPRA** (tpra.fitp.it, risultati su tpra.it) — la piattaforma dei
   tornei amatoriali federali: dal 2025 iscrizioni e tornei pickleball FITP
   passano da lì (iscrizioni anche via app MyFITP). Nota collegata: il rating
   ufficiale FITP per il pickleball è DUPR — una fonte dati in più per grafiche
   (es. rating dei finalisti)
6. Altre piattaforme in seguito: l'architettura ad adapter rende ogni aggiunta
   un modulo nuovo, senza toccare il resto

## Cosa fa il tool

1. **Ogni ~30 minuti** fa lo scraping della pagina risultati del torneo sul sito
   del PPA (ppatour.com).
2. **Storie con i risultati aggiornati**: genera le grafiche sui template
   PickleballSpot e pubblica Stories con i punteggi, **taggando i giocatori**
   (serve una mappa nome giocatore → handle Instagram).
3. **Trigger fine tabellone**: quando un tabellone si chiude (es. doppio misto),
   genera un post dedicato:
   - Slide 1: la **foto del vincitore** (la passa Andrea al momento — unico input
     manuale previsto)
   - Slide successive: il cammino del tabellone scrollando — quarti (4 risultati),
     semifinali, finale
4. Tutto il resto è automatico una volta impostato il template.

## Note tecniche per la chat di sviluppo

- **Template prima di tutto**: le grafiche (Story risultati, slide tabellone,
  slide vincitore) vanno disegnate una volta nello stile PickleballSpot
  (skill pickleballspot-brand + instagram-vertical-safety per le zone sicure).
- **Scraping PPA**: pagina tabelloni/risultati del torneo; attenzione a eventuali
  rendering JavaScript (usare browser headless se serve). Frequenza 30 minuti.
- **Pubblicazione**: account Instagram di PickleballSpot via API Graph (stessa
  tecnica del bot di @you.didnot.know in questo repo: `bot/publish.py` è il
  riferimento). Nota: i tag nelle Stories via API hanno limiti — verificare cosa
  è possibile (sticker di menzione via API non sempre disponibile; in alternativa
  menzione testuale).
- **Trigger fine tabellone**: si deduce dallo scraping (finale con punteggio =
  tabellone chiuso).
- **Input manuale**: solo la foto del vincitore, passata da Andrea in chat o in
  una cartella Drive osservata.
- **Riuso**: lo stesso motore, cambiando sorgente dati (OpenPlay invece dello
  scraping PPA) e template (stile del circolo), è il prodotto da vendere ai
  circoli. Progettarlo quindi con sorgente dati e stile come moduli separati.

## Prerequisiti oggi mancanti

- Rete della sessione cloud aperta (ppatour.com e instagram.com oggi bloccati)
  oppure esecuzione via GitHub Actions come il bot esistente
- Credenziali Instagram dell'account PickleballSpot (token Graph API)
- Mappa giocatori → handle Instagram per i tag
