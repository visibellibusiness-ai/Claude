# Integrazione OpenPlay ↔ PickleballSpot: cosa chiedere agli sviluppatori

Contesto: OpenPlay (openplay.cloud) è un'app di prenotazione campi e gestione
tornei. Roma Pickleball (pilota del progetto siti) è socio di OpenPlay e Andrea è
in contatto diretto con gli sviluppatori. Obiettivo: prenotare il pickleball da
dentro PickleballSpot e i mini-siti dei circoli, con commissione per i clienti
procurati.

Richieste in 3 fasi, dalla più semplice: la fase 1 basta per lanciare.

## Fase 1 — per lanciare subito (pilota Roma Pickleball)

1. **Deep link stabile per circolo.** Un URL fisso per ogni circolo su OpenPlay
   (es. `openplay.cloud/club/<id>`) che apra direttamente la sua pagina di
   prenotazione. Serve documentato e stabile nel tempo: ci costruiamo i bottoni
   "Prenota" su schede e mini-siti.
2. **Widget di prenotazione incorporabile.** Un embed (iframe o script JS) del
   flusso di prenotazione di un singolo circolo, da inserire nei mini-siti:
   parametrizzato per circolo, responsive (mobile first), con colori/logo
   personalizzabili per il brand del circolo. Se già esiste, basta la
   documentazione; se non esiste, è la richiesta di sviluppo più importante.
3. **Tracciamento referral.** Un parametro di riferimento (es. `?ref=pbs`) sui
   link di attivazione circoli e un report (anche manuale, mensile) dei circoli
   attivati tramite PickleballSpot: è la base del calcolo della commissione.
4. **Asset di brand.** Logo e mini-guida d'uso del marchio OpenPlay per il
   "powered by" su piattaforma e mini-siti (e viceversa, se vogliono mostrare
   PickleballSpot come partner).

## Fase 2 — per rendere la piattaforma viva

5. **API in lettura: disponibilità campi.** Endpoint che dato un circolo
   restituisce campi e slot liberi (es. prossime 24-48 ore). Con questa,
   PickleballSpot mostra "oggi 3 slot liberi" direttamente sulla scheda del
   circolo: nessuna directory concorrente ce l'ha.
   Dettagli da chiedere: autenticazione (API key), limiti di chiamate, formato
   (JSON), ambiente di prova.
6. **API/feed tornei.** Elenco tornei per circolo (nome, data, livello, link di
   iscrizione). PickleballSpot può diventare IL calendario tornei pickleball
   d'Italia, aggregando tutti i circoli OpenPlay: fortissimo per il traffico e
   per i contenuti (news, newsletter, social).
7. **Webhook nuova prenotazione/iscrizione** (opzionale): notifica quando una
   prenotazione arriva da un link/widget PickleballSpot, per misurare il valore
   generato e rendicontare la commissione senza report manuali.

## Fase 3 — solo a volumi alti

8. **API in scrittura: prenotazione nativa.** Creare la prenotazione da dentro
   PickleballSpot (utente, slot, pagamento). Da valutare solo quando il traffico
   la giustifica: implica gestione pagamenti, account utente e accordi GDPR da
   responsabile del trattamento. Non chiederla ora: basta sapere se la loro
   architettura la renderebbe possibile in futuro.

## Punti contrattuali da chiudere in parallelo (con Marco)

- Percentuale referral e base di calcolo (una tantum o ricorrente)
- Valore e durata della sponsorizzazione del progetto
- Esclusiva o affiancamento ai deep link Playtomic/Wansport per i circoli che già li usano
- GDPR: finché si usano solo deep link e widget, il titolare del trattamento resta
  OpenPlay — verificare che il widget abbia la sua informativa; con la fase 3
  servirebbe un accordo ex art. 28

## Messaggio breve per gli sviluppatori (pronto da inoltrare)

> Ciao, per l'integrazione PickleballSpot ↔ OpenPlay ci servirebbero per partire:
> 1) l'URL stabile della pagina di prenotazione di ogni circolo (deep link);
> 2) se esiste, un widget/embed del flusso di prenotazione di un singolo circolo
> da mettere nei mini-siti dei circoli (iframe o script, responsive);
> 3) un parametro referral sui link di attivazione (es. ?ref=pbs) con un report
> dei circoli attivati tramite noi;
> 4) logo e indicazioni d'uso del vostro marchio per il "powered by".
> In un secondo momento ci piacerebbe parlare di una API in sola lettura per
> disponibilità campi e calendario tornei. Partiamo col pilota su Roma Pickleball.
