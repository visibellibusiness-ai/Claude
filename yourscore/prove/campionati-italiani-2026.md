# Prova su torneo reale: Campionati italiani pickleball 2026

Torneo: **Campionati italiani di pickleball 2026**, 159 Pickleball, Cassano Magnago, 11-14 giugno 2026.
Fonti dei risultati ufficiali: [FITP Lombardia](https://www.fitp.it/Siti-regionali/Lombardia/News/News/campionati-italiani-pickleball-2026-cassano-magnago) · [Calabria Pickleball](https://www.calabriapickleball.it/2026/06/15/campionati-italiani-di-pickleball-a-cassano-magnago-eletti-i-campioni-2026/).
Prova eseguita il 22/10/2026, 13:40:38.

## Cosa è stato simulato

- Una piattaforma di tornei carica evento e tabellone con 7 partite in una chiamata, con i propri ID.
- Tre tablet, uno per campo. I campi reali non sono pubblicati: l'assegnazione dei campi è della prova.
- Ogni referto è firmato da tutti i giocatori (firme generate dalla prova, non firme reali).
- La piattaforma riceve i referti via webhook firmato e aggiorna il proprio tabellone.

## Risultati ufficiali e referti Your Score

| Partita | Esito | Ufficiale | Referto Your Score | Verifica |
|---|---|---|---|---|
| Singolare maschile · Semifinale | **Matteo Cugliari** b. Yasser Taha | 15-8 | 15-8 (uguale), 2 firme | integro · `BA2DF96CB4E4` |
| Singolare maschile · Semifinale | **Alberto Seccia** b. Andrea Bosi | 15-7 | 15-7 (uguale), 2 firme | integro · `7A5E42B8A41A` |
| Singolare maschile · 3° posto | Andrea Bosi – Yasser Taha | — | vinta da Bosi, punteggio non pubblicato | — |
| Singolare maschile · Finale | **Matteo Cugliari** b. Alberto Seccia | 11-1 8-11 11-3 | 11-1 8-11 11-3 (uguale), 2 firme | integro · `E3F5DA667307` |
| Doppio maschile · Finale | **Matteo Cugliari / Alberto Seccia** b. Sergio Patricio Salandro / Stefano Moioli | 11-1 12-10 | 11-1 12-10 (uguale), 4 firme | integro · `61FAFAD9ADF1` |
| Doppio femminile · Finale | **Paola Tampieri / Natascia Sciolti** b. Antonella Sonda / Paola Bolzon | 11-7 11-8 | 11-7 11-8 (uguale), 4 firme | integro · `4DAC0D899009` |
| Doppio misto · Finale | **Andrea Bosi / Paola Tampieri** b. Cristian Gallucci / Francesca Rumi | 12-10 11-9 | 12-10 11-9 (uguale), 4 firme | integro · `846976BB8240` |

## Controlli

- Partite caricate dalla piattaforma: 7 su 7.
- Referti certificati arrivati alla piattaforma via webhook: 6.
- Webhook con firma valida: 6 su 6.
- Punteggio impossibile (15-14 in un game ai 15) rifiutato: sì — «set 1: servono 2 punti di scarto».
- Il punteggio reale 12-10 (vantaggi oltre l'11) è stato accettato correttamente.

## Limiti della prova

- Le semifinali del singolare maschile vengono solo da Calabria Pickleball; un'altra versione delle semifinali
  riportata dai motori di ricerca non coincide e non è stata usata.
- La finale per il 3° posto del singolare maschile non ha un punteggio pubblicato: resta aperta.
- Le altre partite del torneo (gironi, tabelloni completi, singolare femminile) non sono pubbliche
  nelle fonti consultate e non sono state ricostruite.

## Registro webhook

```
11:40:18 scoresheet.certified SM-SF1 firma webhook valida
11:40:18 scoresheet.certified SM-SF2 firma webhook valida
11:40:18 scoresheet.certified DF-F firma webhook valida
11:40:19 scoresheet.certified DX-F firma webhook valida
11:40:35 scoresheet.certified DM-F firma webhook valida
11:40:38 scoresheet.certified SM-F firma webhook valida
```

## Dal tablet del campo 1

Le due finali del campo 1 sono state inserite e firmate dal tablet in un browser, come farebbe un giocatore:
[punteggio](tablet-punteggio.png) · [firma](tablet-firma.png) · [referto certificato](tablet-certificato.png).

Cosa migliorare, emerso dalla prova: arrivare a un punteggio come 12-10 richiede molti tocchi su «+».
Serve un tastierino numerico o l'inserimento a voce.

Per rifare la prova: `node examples/campionati-italiani-2026.js`.
