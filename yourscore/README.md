# Your Score

Referti di partita **firmati da tutti i giocatori** su un tablet a bordo campo, **certificati** e
consegnati a **qualsiasi piattaforma di tornei** (OpenPlay, RAQT, gestionali di circolo, federazioni)
con una API REST e i webhook.

La piattaforma continua a fare quello che sa fare (iscrizioni, tabelloni, classifiche, rating).
Your Score fa una cosa sola: trasforma il risultato del campo in un referto firmato, verificabile
e già pronto da importare.

```
Piattaforma tornei ──(1) partite e campi──▶ Your Score ──▶ tablet del campo
        ▲                                      │            (punteggio + firme)
        └────(3) referto certificato ◀─────────┘◀──(2) referto firmato
                  via webhook
```

## Avvio rapido

Serve Node.js 20 o superiore, nessuna dipendenza da installare.

```bash
npm run demo     # avvia il server con un torneo di prova e stampa i link dei tablet
npm test         # test automatici: flusso completo, firme, manomissione, sicurezza
npm start        # server vuoto (porta 8080, dati in ./data)
npm run create-platform -- "Nome piattaforma"   # crea una piattaforma e stampa la sua API key
```

Variabili d'ambiente: `PORT`, `YS_DATA_DIR` (dove salvare dati e chiave di firma),
`YS_BASE_URL` (indirizzo pubblico, usato nei link dei tablet e di verifica).

## Come si integra una piattaforma

Il contratto completo è in [`public/openapi.yaml`](public/openapi.yaml) (servito anche su `/openapi.yaml`).
La piattaforma usa sempre **i propri ID** per eventi, partite e giocatori: non deve salvare nulla di
Your Score, e ripetere una chiamata non crea doppioni.

### 1. Carica il torneo (una chiamata per evento, una per il tabellone)

```bash
curl -X PUT $YS/v1/events/T-2026-ROMA -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"name":"Open di Roma","format":"pickleball_11"}'

curl -X POST $YS/v1/events/T-2026-ROMA/matches/batch -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" -d '{"matches":[
    {"external_id":"M1","court":"1","round":"Girone A","teams":[
      {"players":[{"external_id":"dupr-123","name":"Mario Rossi"},{"external_id":"dupr-456","name":"Luca Bianchi"}]},
      {"players":[{"external_id":"dupr-789","name":"Anna Verdi"},{"external_id":"dupr-012","name":"Sara Neri"}]}]}
  ]}'
```

Quando il tabellone avanza (nuovo turno, campo cambiato) la piattaforma richiama la stessa API:
le partite si aggiornano.

### 2. Crea i link dei tablet

```bash
curl -X POST $YS/v1/events/T-2026-ROMA/devices -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" -d '{"court":"1"}'
# → { "tablet_url": "https://…/court/#token=dt_…" }
```

- **Con `court`**: il tablet fisso del campo 1 vede solo le partite del campo 1.
- **Senza `court`**: il tablet dell'arbitro vede tutte le partite e sceglie quella che arbitra.

Il link si apre sul tablet (o si mostra come QR code all'organizzatore). Un tablet perso si revoca
con `DELETE /v1/devices/{id}`.

### 3. Ricevi i referti

**Webhook (consigliato).** Si registra un indirizzo una volta sola:

```bash
curl -X POST $YS/v1/webhooks -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" -d '{"url":"https://piattaforma.example/yourscore"}'
# → { "secret": "whsec_…" }   (mostrato una sola volta)
```

A ogni referto arriva un POST con `type` = `scoresheet.certified`, `scoresheet.disputed`
(il risultato va al tavolo) o `scoresheet.voided` (referto annullato per correzione).
Dentro `data.scoresheet` ci sono gli ID della piattaforma (`event.external_id`,
`match.external_id`, `winner_player_external_ids`) e il punteggio, quindi aggiornare il tabellone
è immediato. Verifica della firma del webhook in Node:

```js
const [t, v1] = req.headers['yourscore-signature'].split(',').map(x => x.split('=')[1]);
const expected = crypto.createHmac('sha256', WEBHOOK_SECRET).update(`${t}.${rawBody}`).digest('hex');
const ok = crypto.timingSafeEqual(Buffer.from(v1), Buffer.from(expected)) && Date.now() / 1000 - t < 300;
```

**Polling (in alternativa).** `GET /v1/scoresheets?event=T-2026-ROMA&since=<data>` restituisce i
referti nuovi o modificati, in ordine.

### 4. (Facoltativo) Dentro l'app della piattaforma

Il tablet è una pagina web: la piattaforma può aprirlo dentro la propria app (WebView) col proprio
marchio, oppure costruire un'interfaccia sua usando gli endpoint `/v1/device/*`.

**Lavoro stimato per una piattaforma: 4 chiamate API e un endpoint che riceve il webhook.**

## OpenPlay e RAQT

Le API pubbliche di OpenPlay e RAQT non sono documentate. Da questo ambiente non è stato possibile
consultare i loro siti, quindi **nessuna integrazione con le loro API è stata scritta o simulata**.
Quello che si sa di RAQT viene dalla ricerca di mercato (`reports/Ricerca di mercato Your Score.md`):
app per organizzatori con tabelloni, punteggio live e collegamento DUPR; una "Web API" annunciata per
iscrizioni e pagamenti; nessun accesso documentato in scrittura ai risultati.

Due strade possibili con ciascuna:

| | **A. La piattaforma chiama Your Score** (consigliata) | **B. Your Score chiama la piattaforma** |
|---|---|---|
| Chi scrive il codice | Gli sviluppatori della piattaforma (4 chiamate + webhook) | Noi: un "connettore" per quella piattaforma |
| Cosa serve da loro | Solo la decisione di integrarsi | Un'API che legga partite e campi e accetti i risultati in scrittura |
| Vantaggio | Standard unico per tutti, zero manutenzione per piattaforma | Partono senza toccare il loro codice |

Domande da fare a OpenPlay e RAQT al primo incontro:
1. Avete un'API (o un'esportazione) delle **partite programmate con campo e orario**?
2. Potete **ricevere un webhook** e aggiornare il tabellone col risultato? In alternativa, avete un
   endpoint per **scrivere il risultato** di una partita?
3. Gli ID dei giocatori sono stabili? Usate il **DUPR ID**?
4. Come gestite oggi le **contestazioni** e le correzioni dei risultati?
5. Accettereste di aprire il tablet Your Score **dentro la vostra app** col vostro marchio?

## Sicurezza, certificazione e privacy

- **Referto a prova di manomissione.** Al momento della certificazione si calcola l'impronta
  SHA-256 del contenuto (partita, punteggio, impronte delle firme, tablet, ora) e la si firma con una
  chiave Ed25519 del server. Ogni referto include anche l'impronta del precedente della stessa
  piattaforma (catena): cancellare o modificare un referto spezza la catena.
  `GET /verify/{id}` mostra a chiunque se il referto è integro; `GET /v1/public-key` permette
  di verificarlo anche senza fidarsi del server.
- **Firme senza dati biometrici.** Il tablet salva solo l'immagine del tratto, ridotta, senza
  pressione né velocità: resta un dato personale ordinario e non un dato biometrico (GDPR art. 9).
- **Minimo indispensabile.** Le immagini delle firme non escono mai nei webhook né nella pagina di
  verifica pubblica: solo la loro impronta. La piattaforma proprietaria può leggerle con
  `GET /v1/scoresheets/{id}/signatures`.
- **Accessi separati.** Ogni piattaforma vede solo i propri dati; API key e token dei tablet sono
  salvati solo come impronta; i token dei tablet viaggiano nell'ancora dell'URL e non finiscono nei log.
- **Rete che cade.** Il tablet conserva il referto e lo invia appena torna la connessione; l'invio
  ripetuto non crea doppioni.

## Limiti di questo prototipo

- I dati sono in un file JSON: per la produzione va usato un database (PostgreSQL).
- La chiave di firma è un file: in produzione va in un servizio di custodia chiavi (KMS/HSM).
- Mancano la **marca temporale qualificata** e il **sigillo elettronico qualificato** di un
  prestatore eIDAS, indicati dalla ricerca legale per dare pieno valore probatorio: vanno aggiunti
  dopo il parere di un avvocato.
- Non ci sono ancora il pannello per l'organizzatore, l'inserimento vocale del punteggio e il QR code
  dei link.
- Le regole di punteggio coprono i formati più comuni (`GET /v1/formats`); altri si aggiungono in
  `src/rules.js`.
