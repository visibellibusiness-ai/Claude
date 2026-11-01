# Tool avvisi dirette del weekend: scheda progetto (da sviluppare in una chat dedicata)

Idea di Andrea (1 novembre 2026). Obiettivo: un tool che resta sempre
aggiornato sui tornei di pickleball del fine settimana e, quando Andrea è a casa
(niente trasferta), lo avverte delle semifinali e delle finali in diretta,
con il link allo streaming già pronto da aprire.

## Cosa fa il tool

1. **Calendario tornei sempre aggiornato**: ogni settimana trova i tornei del
   fine settimana in arrivo sui circuiti che seguiamo e per ciascuno ricava il
   programma di semifinali e finali (giorno, orario, fuso orario) e dove vanno in
   diretta.
2. **Controllo trasferta**: prima di avvisare, verifica sul calendario Google di
   Andrea se nel weekend è in trasferta. Se è in trasferta, resta in silenzio.
   Se è a casa, prepara gli avvisi.
3. **Avviso con link allo streaming**: per ogni semifinale e finale in diretta,
   manda ad Andrea un avviso con il link diretto allo streaming (PickleballTV,
   YouTube, o quello che usa il circuito), in orario italiano, poco prima
   dell'inizio.
4. Vale per **tutti i circuiti che seguiamo**: per ognuno la stessa cosa, con la
   sua fonte di streaming.

## Circuiti da coprire

Come detto da Andrea: PPA, APP, MLP "e tutti i tornei che seguiamo".

- **PPA Tour** (ppatour.com)
- **APP Tour** (apptour.org)
- **MLP, Major League Pickleball** (majorleaguepickleball.net)
- **"RTA"**: nome da confermare con Andrea (trascrizione vocale ambigua). Da
  chiedere nella chat di sviluppo prima di implementare l'adapter.
- Altri circuiti che PickleballSpot segue (es. PPA Tour Europe, tornei FITP in
  Italia): confermare la lista con Andrea all'avvio.

Per ogni circuito vanno verificati dal vivo, senza assumere: dove pubblica il
programma delle dirette, su quale piattaforma trasmette semifinali e finali, se
il link è stabile (canale) o cambia per ogni torneo (evento specifico), e se
serve un abbonamento (da segnalare nell'avviso).

## Decisioni da prendere con Andrea all'avvio della chat

1. **Canale dell'avviso**: email, notifica push dell'app Claude, evento sul
   calendario Google con promemoria, o una combinazione. Proposta: evento sul
   calendario con promemoria 30 minuti prima + email con il link.
2. **Anticipo dell'avviso**: quanti minuti prima dell'inizio.
3. **Regola "sono in trasferta"**: come riconoscerla sul calendario (parola
   chiave nel titolo, evento di più giorni fuori città, calendario dedicato).
4. **Orari notturni**: i tornei americani in Italia finiscono spesso di notte.
   Avvisare sempre, oppure solo in una fascia oraria scelta da Andrea.
5. **Quali categorie**: tutte le finali (singolo, doppio, misto), solo alcune, o
   anche le semifinali di tutte.

## Note tecniche per la chat di sviluppo

- **Architettura ad adapter**, come il tool risultati live
  (`idee/tool-risultati-live-tornei.md`, codice in `live/`): un modulo per
  circuito che restituisce un formato comune (torneo, fase, categoria, data e
  ora UTC, link streaming, piattaforma); il resto (controllo calendario,
  avvisi) è identico per tutti.
- **Esecuzione periodica**: due strade possibili, da valutare nella chat.
  1. Attività programmate di Claude (cloud): un giro settimanale (es. giovedì)
     che cerca sul web i tornei del weekend, legge il calendario Google tramite
     il connettore e programma gli avvisi; oppure un giro giornaliero nel
     weekend. Vantaggio: ricerca web e connettori Google già disponibili.
  2. GitHub Actions, come `.github/workflows/live-tornei.yml`: script Python
     che legge i siti dei circuiti. Attenzione: nella sessione cloud i domini
     esterni sono bloccati (vedi `live/README.md`, sezione sviluppo con la rete
     chiusa), quindi lo scraping va studiato con la sonda o in locale.
- **Fuso orario**: tutti gli orari vanno convertiti in Europe/Rome; i siti
  americani pubblicano in ET o PT, da verificare caso per caso.
- **Link streaming**: preferire il link all'evento specifico; in mancanza, il
  canale del circuito. Mettere nell'avviso anche la piattaforma e se serve un
  abbonamento.
- **Memoria**: tenere traccia degli avvisi già mandati (niente doppioni) e dei
  tornei già analizzati, in un file di stato come `live/state/`.
- **Lingua**: avvisi ad Andrea in italiano.

## Prerequisiti

- Accesso al calendario Google di Andrea (connettore Google Calendar) per il
  controllo trasferta.
- Canale di avviso scelto (connettore Gmail per email, oppure calendario).
- Verifica dal vivo di programmi e piattaforme streaming di ogni circuito.
