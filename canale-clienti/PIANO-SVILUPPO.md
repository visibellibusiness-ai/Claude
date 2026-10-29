# Canale clienti — Piano di sviluppo

Nome provvisorio: **canale-clienti** (nome prodotto ancora da decidere).

## Principio

Prima lo strumento per me (Andrea), con i miei clienti reali. Si costruisce solo quello che risolve il problema di oggi: **i clienti non mi scrivono più su WhatsApp con richieste di lavoro, e ogni richiesta ha uno stato e scala il monte ore.** Tutto il resto si aggiunge dopo, ma lo schema dati nasce già predisposto per più utenti (team e sostituti).

## Release 0.1 — "Uso personale" (funzioni base)

### Flusso
1. Ogni cliente ha un **link personale** (PWA, nessun account, nessun download). Il link lo mando io una volta sola.
2. Il cliente scrive o registra un vocale nel link.
3. **Conferma immediata di ricezione** al cliente: "Richiesta ricevuta. Ti rispondo entro X ore" (X dipende dalla mia disponibilità dichiarata e dal tipo di rapporto del cliente).
4. L'AI trascrive (se vocale) e prepara una bozza: riassunto, stima tempo, valore.
5. Io vedo la richiesta nella mia coda, confermo o correggo la stima con un tocco.
6. Il cliente vede lo **stato** e decide.

### Stati della richiesta (il "accettano o meno")
`ricevuta` → `in valutazione` → `proposta inviata` → **`accettata`** / **`rifiutata`** → `in lavorazione` → `completata`
Ramo extra: `rifiutata` → il cliente può fissare una call (slot Google Calendar).
Le richieste sotto soglia (es. ≤ 30 min e dentro il monte ore) possono saltare l'approvazione: `auto-approvata`.

### Monte ore
- Scheda cliente: tipo accordo (monte ore / progetto / a chiamata), ore mensili, tariffa extra.
- Scatto minimo 30 min (configurabile a 15).
- Scalare dal saldo solo quando la richiesta passa a `completata` (o `accettata`, da decidere — vedi domande).
- Saldo visibile al cliente nel suo link, con avviso al 75%.
- Report mensile automatico (PDF o pagina) come prova del lavoro svolto.

### Fuori dalla 0.1 (volutamente)
- Più utenti / team / reparti / sostituti e instradamento a cascata
- Pagamenti, fatturazione, pacchetti prepagati, emergenze a pagamento
- Commissioni piattaforma, report avanzati
- Collegamento diretto API WhatsApp (vedi "WhatsApp" sotto)

### Schema dati (già pronto per il futuro)
| Tabella | Campi principali |
|---|---|
| `workspace` | id, nome (oggi: il mio) |
| `user` | id, workspace_id, ruolo (`owner` ora; `member`, `substitute` poi) |
| `client` | id, workspace_id, nome, token_link, accordo, ore_mensili, tariffa_extra, sla_ore |
| `request` | id, client_id, assegnato_a (user_id, oggi sempre io), testo, audio_url, trascrizione, riassunto, stima_min, valore, stato, creato_il |
| `ledger` | id, client_id, request_id, minuti (+/−), tipo (`incluso`, `extra`, `rettifica`), mese |
| `availability` | user_id, fasce orarie, tempo di risposta dichiarato |

Il `ledger` è un registro di movimenti (non un campo "saldo"): il saldo si calcola, ogni scalata è tracciabile, il report mensile è una query.

### Stack consigliato (semplice e ospitabile da solo)
- **App**: Next.js (PWA) + Postgres (Supabase o Neon). Un solo progetto, poco da gestire.
- **Trascrizione**: OpenAI `gpt-4o-mini-transcribe` (circa 0,003 $/min) oppure Whisper; costo trascurabile per uso personale.
- **Riassunto e bozza preventivo**: Claude API (modello Haiku/Sonnet), output JSON strutturato.
- **Notifiche a me**: email + digest a orari fissi; push web come aggiunta.
- **Calendario**: Google Calendar API (slot liberi per la call).
- **Hosting**: Vercel o simile.

## WhatsApp: come tenerlo fuori senza rischi

1. **Subito, zero codice**: nell'app WhatsApp Business uso *messaggio di assenza* e *messaggio di benvenuto*: "Le richieste di lavoro vanno qui: [link]. Qui rispondo solo a questioni personali." È già l'80% dell'effetto "riprendo il mio WhatsApp".
2. **Dopo la 0.1 funzionante**: collegamento all'API ufficiale (Cloud API) con la modalità **coexistence**, che permette di usare lo stesso numero sia sull'app Business sia sull'API. Requisiti: numero già sull'app WhatsApp Business (versione 2.24.17+), un account Meta Business, alcuni giorni di attività; da verificare nella documentazione Meta prima di partire.
3. **Costi API**: Meta fattura per messaggio sui soli template approvati; i messaggi liberi dentro la finestra di 24 ore sono gratuiti. Un blog di terze parti segnala cambi di fatturazione dal 1 ottobre 2026: **da verificare sulla pagina ufficiale prima di calcolare i costi**.
4. Mai connessioni non ufficiali (rischio ban del numero).

## Piano a tappe

| Fase | Contenuto | Esito |
|---|---|---|
| **A. Fondamenta** | Repo, DB, schema, deploy, accesso mio | App online con login solo per me |
| **B. Link cliente** | Pagina cliente per testo e vocale, conferma di ricezione con "entro X ore" | Un cliente può inviare e vede la conferma |
| **C. Coda mia** | Elenco richieste, trascrizione AI, bozza, conferma con un tocco | Posso gestire le richieste |
| **D. Stati e approvazione** | Proposta al cliente, accetta/rifiuta, link call | Ciclo completo |
| **E. Monte ore** | Ledger, scatto minimo, saldo visibile, avviso 75%, auto-approvazione | Monte ore reale |
| **F. Report** | Report mensile automatico | Prova del lavoro |
| **Pilota** | 3–5 clienti reali per 4 settimane | Dati per decidere il passo dopo |

Dopo il pilota, in ordine: coexistence WhatsApp → sostituti con cascata → team e reparti.

## Domande da chiudere prima di scrivere codice
1. **Quando si scala il monte ore**: all'accettazione della stima o a lavoro completato (con tempo reale)? Consiglio: prenotare la stima all'accettazione e rettificare a fine lavoro.
2. **Tempo di risposta "X ore"**: un valore fisso per cliente, oppure calcolato dalle mie fasce di disponibilità (fuori orario → "domattina")? Consiglio: dalle fasce, con valore base per cliente.
3. **Quali clienti pilota** e che accordo ha già ciascuno (monte ore, a chiamata, progetto).
4. **Lingua dell'interfaccia cliente**: solo italiano, o già inglese?
5. Il vincolo "Stati Uniti" nel messaggio: l'ho letto come **"stati" (accetta/rifiuta)** — se intendevi altro (mercato USA), dimmelo.

## Materiali e concorrenti trovati

- **Plutio**: portale clienti, ore per retainer, fatture ricorrenti (≈19 $/mese). Gestionale completo, ma non separa il canale di richiesta. https://www.plutio.com/freelancer-magazine/best-software-for-retainer-clients
- **Retallio**: portale live per retainer, saldo ore visibile, avviso quando ci si avvicina al limite. https://www.producthunt.com/products/retallio
- **Clientrol**: il più vicino al concept: cliente vede il tempo residuo, può comprare ore extra, toggle di approvazione, blocco richieste a ore finite. https://slashdot.org/software/p/Clientrol/
- **Differenziatori da non perdere**: richiesta vocale con trascrizione e preventivo AI, valore mostrato anche sulle ore incluse, conferma di ricezione con tempo di risposta, e (in futuro) rete di sostituti.
- **WhatsApp Business Platform – prezzi** (documentazione Meta): https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing
- **Coexistence – guida 360dialog**: https://docs.360dialog.com/docs/hub/embedded-signup/whatsapp-coexistence
- **Prezzi trascrizione OpenAI** (fonti secondarie, da verificare): https://diyai.io/ai-tools/speech-to-text/openai-whisper-api-pricing-2026/

Nota: i dati sui prezzi vengono da pagine di terze parti, tranne la documentazione Meta; vanno confermati sulle pagine ufficiali prima di decisioni economiche.
