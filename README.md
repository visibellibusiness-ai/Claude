# Pagina Instagram automatica: "Did You Know?"

Pagina in inglese di curiosità verificate (corpo umano, animali, spazio, storia, psicologia…)
che si gestisce da sola: **due caroselli al giorno**, generati, disegnati e
pubblicati senza intervento umano.

## Perché questa nicchia

- **I caroselli di curiosità generano tanti salvataggi e condivisioni**, i segnali
  che l'algoritmo di Instagram premia di più per arrivare a chi non ti segue.
- **Non serve un volto né riprese**: tutto si produce in automatico.
- **I contenuti non finiscono mai**: dieci categorie a rotazione e uno storico
  degli argomenti già usati, così i post non si ripetono.
- **Pubblico ampio e internazionale** (18-45, in inglese) e argomenti adatti ai brand, utile se in
  futuro vuoi monetizzare.

## Come funziona

Ogni giorno alle 13:40 e alle 23:40 UTC (pomeriggio in Europa / mattina e sera negli USA) GitHub Actions esegue
`.github/workflows/post.yml`:

1. `bot/generate.py` chiede a Claude un carosello nuovo (gancio, 5-7 slide, CTA,
   caption, hashtag, fonti).
2. `bot/render.py` disegna le slide 1080×1350.
3. Le immagini vengono committate nel repo, così hanno un indirizzo pubblico.
4. `bot/publish.py` pubblica il carosello con l'API ufficiale di Instagram.
5. `posts/history.json` registra cosa è uscito.

I file JSON in `posts/queue/` escono per primi: c'è già il primo post pronto.

## Configurazione una tantum (circa 20 minuti, poi non tocchi più niente)

Questi passaggi richiedono il tuo telefono e i tuoi account, quindi vanno fatti a mano.

1. **Crea l'account Instagram** (es. `@didyouknow.daily.facts`), poi in
   Impostazioni → Tipo di account passa a **Account professionale → Creator**.
   Metti foto profilo e bio (sotto trovi una proposta).
2. **Crea una Pagina Facebook** e collegala all'account Instagram
   (Instagram → Impostazioni → Centro gestione account).
3. **Crea un'app Meta** su developers.facebook.com → Le mie app → Crea app →
   tipo "Business". Aggiungi il prodotto **Instagram** (API con login di Facebook).
4. Da **Graph API Explorer** genera un token con i permessi
   `instagram_basic`, `instagram_content_publish`, `pages_show_list`,
   `pages_read_engagement`, `business_management`, poi convertilo in
   **token di lunga durata** (Strumenti → Debug token di accesso → Estendi).
5. Trova l'**ID Instagram**: in Graph API Explorer esegui
   `me/accounts?fields=instagram_business_account` e copia l'`id`
   dentro `instagram_business_account`.
6. Crea una **chiave API Anthropic** su console.anthropic.com.
7. Nel repo GitHub: Settings → Secrets and variables → Actions → aggiungi
   `ANTHROPIC_API_KEY`, `IG_USER_ID`, `IG_ACCESS_TOKEN`.
8. **Rendi pubblico il repo** (Settings → General → Change visibility): Instagram
   deve poter scaricare le immagini da `raw.githubusercontent.com`.
9. Unisci questo branch nel branch principale. Da lì il workflow parte da solo;
   per il primo post subito vai su Actions → "Pubblica post Instagram" → Run workflow.

Il token di lunga durata scade dopo circa 60 giorni: va rinnovato e aggiornato
nel secret `IG_ACCESS_TOKEN`.

### Bio consigliata

```
Did You Know? 🤯
Real facts you never knew, every day
Human body · Space · Animals · History
👉 Save posts to remember them
```

## Personalizzare

- Nome, handle, categorie e colori: `bot/config.py`
- Tono e regole dei contenuti: `SYSTEM` in `bot/generate.py`
- Orari di pubblicazione: `cron` in `.github/workflows/post.yml` (orari in UTC)

## Costi indicativi

- GitHub Actions: gratis per i repo pubblici.
- API Claude: pochi centesimi per post.
- Instagram API: gratis.
