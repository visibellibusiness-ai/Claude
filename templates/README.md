# Template Photoshop per i post

La grafica la disegni tu in Photoshop; il sistema cambia solo testi e immagini.

## Partire dai template già pronti

1. Installa i font della cartella `fonts/` (doppio clic su ogni `.ttf` → **Installa**).
2. In Photoshop: **File → Script → Sfoglia…** (*File → Scripts → Browse…*) e scegli
   `crea_template.jsx`. In pochi secondi crea `cover.psd`, `slide.psd` ed `end.psd`
   nella stessa cartella, con livelli modificabili e già nominati.
3. Modificali come vuoi (colori, posizioni, font, decorazioni). Non rinominare i
   livelli in maiuscolo (`IMAGE`, `TITLE`, `BODY`, ...): sono quelli che il sistema
   riempie.
4. Carica i tre `.psd` in questa cartella su GitHub (Add file → Upload files).

I file che servono qui (1080×1350 px, RGB, 72 dpi):

| File | Uso |
|---|---|
| `cover.psd` | copertina del carosello |
| `slide.psd` | slide interne (una per ogni curiosità o notizia) |
| `end.psd` | ultima slide con l'invito a seguire (facoltativo: senza, si usa `slide.psd`) |

## Come nominare i livelli

Rinomina i livelli da sostituire con questi nomi esatti (maiuscolo, con o senza `{{ }}`):

| Livello | Tipo | Cosa ci mette il sistema |
|---|---|---|
| `IMAGE` | rettangolo o immagine segnaposto | la foto della slide, ritagliata per riempire il riquadro |
| `TITLE` | testo | titolo (copertina: il gancio) |
| `BODY` | testo | testo della slide |
| `HIGHLIGHT` | testo | numero o parola in evidenza (es. "+1 cm") |
| `LABEL` | testo | etichetta (categoria, data) |
| `NUMBER` | testo | numero della slide (es. "02/06") |
| `HANDLE` | testo | @you.didnot.know |
| `CREDIT` | testo | credito della foto (es. "Foto: NASA") |

Usa solo i livelli che ti servono: quelli assenti vengono ignorati.

## Regole per i testi

- Usa **caselle di testo** (strumento Testo: clicca e trascina un rettangolo). Il riquadro
  è lo spazio massimo: se il testo nuovo è più lungo, il sistema riduce la dimensione
  finché entra.
- Font, dimensione, colore, interlinea e allineamento vengono presi dal livello.
  Scrivi nel livello un testo di esempio con lo stile che vuoi.
- Se il testo di esempio è tutto in MAIUSCOLO, anche il testo nuovo sarà in maiuscolo.
- In alternativa alla casella di testo puoi aggiungere un rettangolo chiamato
  `TITLE box` (o `BODY box`, ecc.) che definisce il riquadro a mano.

## L'immagine

- Il livello `IMAGE` decide **dove** va la foto e **a che altezza della pila**: i livelli
  sotto restano sotto, quelli sopra (sfumature, cornici, loghi, testi fissi) restano sopra.
- Puoi usare un rettangolo grigio qualsiasi come segnaposto.

## I font

Copia nella cartella `templates/fonts/` i file `.ttf` o `.otf` dei font che usi
(quelli di Google Fonts sono gratuiti; per gli altri controlla la licenza).
Se un font manca, il sistema usa un font di riserva e lo segnala nel log.

## Cosa non viene riprodotto

Il sistema ricompone il PSD con la libreria `psd-tools`, che riproduce la maggior parte
dei livelli e delle opzioni di fusione. Effetti molto particolari (alcuni filtri avanzati,
stili di livello complessi sui testi segnaposto) potrebbero non essere identici: dopo il
primo test ti mando l'anteprima da confrontare con Photoshop.
