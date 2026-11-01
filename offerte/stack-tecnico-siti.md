# Stack tecnico per mini-siti e siti a template (1 novembre 2026)

Requisiti dal documento offerta: decine di sottodomini `*.pickleballspot.eu`,
3 layout × 3 font con colori liberi, siti personalizzati liv. 4, gestione
minima per Andrea (il canone include 2 ore/anno di modifiche), script di
compliance GDPR in licenza, costi di hosting che lascino margine sul canone
di 200 €/anno.

## Confronto opzioni

| Opzione | Costo per sito | Gestione | Verdetto |
|---|---|---|---|
| **Sito statico (Astro) + Cloudflare Pages** | ~0 € (tier gratuito, dominio già posseduto) | Un solo repo, zero server da aggiornare | **Consigliata** |
| HTML puro, un progetto per sito | ~0 € | Zero build, ma ogni modifica comune va ripetuta sito per sito | Buona solo per i primi 2-3 siti |
| WordPress multisite | 15-30 €/mese di hosting + aggiornamenti e sicurezza continui | Alta (plugin, PHP, backup) | Da scartare: i circoli i contenuti li facciamo noi, il CMS serve a poco |
| Webflow / Framer | 15-25 €/mese **per sito** | Bassa | Da scartare: il solo hosting mangia l'intero canone annuo |

## Raccomandazione: monorepo Astro + Cloudflare Pages

Un repository unico `circoli-siti` che genera tutti i siti statici:

1. **Un circolo = una cartella di contenuti** (dati in JSON/Markdown: nome,
   testi, foto, colori, font scelto, link OpenPlay). Il sito si rigenera dal
   contenuto: le 2 ore/anno di modifiche diventano minuti.
2. **I 3 layout sono 3 temi Astro** condivisi; i 3 font per layout sono una
   voce di configurazione. Il livello 4 aggiunge un tema dedicato per cliente.
3. **Deploy su Cloudflare Pages** (tier gratuito: 500 build/mese, banda
   illimitata, SSL automatico). Un progetto Pages per sito, collegato allo
   stesso repo con build filtrata, oppure un unico progetto + routing per
   hostname: si parte con un progetto per sito (più semplice) e si passa al
   routing se i numeri crescono.
4. **DNS**: `pickleballspot.eu` gestito su Cloudflare; ogni sottodominio è un
   record CNAME verso il progetto Pages. Dominio personalizzato (opzione a
   400 €/anno): custom domain sul progetto Pages, col cliente che delega il DNS.
5. **Form contatti senza server**: due vie già compatibili con l'offerta:
   inoltro WhatsApp con `wa.me` precompilato (zero infrastruttura, perfetto per
   i mini-siti) e, dove serve l'email, un Cloudflare Worker che inoltra il form
   alla casella del circolo. Entrambe a costo zero.
6. **GDPR**: lo script dello strumento di compliance in licenza ad Andrea si
   incorpora nelle pagine statiche come su qualsiasi sito; privacy e cookie
   policy per sito, coperte dal canone.
7. **Prenotazioni**: bottone con deep link OpenPlay subito (fase 1
   dell'integrazione); il widget embed, quando arriva, si incolla nel layout
   senza cambiare stack.

### Perché statico

- Niente database né server da mantenere: la voce "mantenimento" del canone
  resta quasi tutta margine.
- Velocità e SEO massimi (Core Web Vitals perfetti di base): l'argomento di
  vendita "ti indicizzi su Google" è sostenuto dalla tecnica.
- Claude Code lavora direttamente sul repo: creare un nuovo mini-sito diventa
  "aggiungi una cartella di contenuti e fai il deploy".

### Costi stimati a regime (20 siti)

| Voce | Costo/anno |
|---|---|
| Hosting (Cloudflare Pages) | 0 € |
| Dominio pickleballspot.eu | già posseduto |
| Domini personalizzati (se venduti a 400 €/anno) | ~10-15 €/dominio, a carico della voce di canone |
| Ricavo canoni (ipotesi 15 liv. 2 + 5 liv. 3-4) | 1.500 + 1.000 = 2.500 €/anno |

## Prossimi passi tecnici

1. Creare il repo `circoli-siti` con lo scaffolding Astro e il primo tema
   (layout 1) derivato dalla demo template.
2. Portare la demo "Roma Pickleball in 3 versioni" (cartella
   `demo/roma-pickleball/` di questo repo) dentro lo scaffolding come primo
   contenuto reale.
3. Configurare Cloudflare Pages + DNS wildcard su pickleballspot.eu (serve
   accesso al pannello DNS di Andrea).
4. Decidere la via dei form (WhatsApp subito, Worker email quando serve).
