# Rubrica news quotidiana di @you.didnot.know

Completamente automatica, come i post di curiosità.

Ogni giorno alle 12:35 UTC (mattina negli USA, primo pomeriggio in Europa) il
workflow `.github/workflows/post.yml` esegue `python -m bot.main create --series news`:

1. `bot/news.py`: Claude cerca sul web le notizie delle ultime 24-36 ore e sceglie
   5 storie (la quinta sempre leggera), ognuna confermata da almeno 2 fonti
   autorevoli e indipendenti; tono neutrale.
2. Scrive per ogni storia titolo, numero o parola in evidenza, categoria e tre
   righe: cosa è successo, perché conta, cosa cambia per te.
3. Genera l'immagine di copertina per la notizia principale (vedi `bot/imagegen.py`).
4. Il sistema crea il carosello (copertina + 5 notizie + chiusura) e un Reel di
   circa 20 secondi con le stesse notizie, nello stile Mystery e con la musica
   mystery.
5. Pubblica il carosello e il Reel (come Trial Reel) e li registra in
   `posts/history.json` con `series: news`, così l'apprendimento li considera.

Se un giro fallisce, la rubrica non pubblicata viene scartata dopo 12 ore, così
non escono mai notizie vecchie.
