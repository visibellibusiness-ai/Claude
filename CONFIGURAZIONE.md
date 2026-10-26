# Configurazione senza Pagina Facebook (accesso con login Instagram)

Aggiornato al 26 ottobre 2026. Questa guida **sostituisce** la sezione "Configurazione una tantum" del README: la pubblicazione usa l'API Instagram con Instagram Login (`graph.instagram.com`), che secondo la documentazione di Meta non richiede di collegare una Pagina Facebook all'account professionale.

Serve ancora un profilo Facebook personale, ma solo per entrare in developers.facebook.com e creare l'app (come indicato dal README originale; non verificato sulla documentazione Meta). Nessuna Pagina, nessun token di Pagina.

## Cosa si crea e cosa va nei Secrets

| Secret GitHub | Cos'è | Dove si prende |
|---|---|---|
| `ANTHROPIC_API_KEY` | chiave API Anthropic | console.anthropic.com → API keys |
| `IG_ACCESS_TOKEN` | token utente Instagram (60 giorni) | dashboard dell'app Meta → Genera token |
| `IG_USER_ID` | numero dell'account Instagram | risposta di `/me` (passo 5) |
| `GH_PAT` | token personale GitHub per rinnovare `IG_ACCESS_TOKEN` | GitHub → Settings → Developer settings (passo 7) |
| `PEXELS_API_KEY`, `UNSPLASH_ACCESS_KEY` | facoltativi: più foto tra cui scegliere | pexels.com/api, unsplash.com/developers |

Le chiavi le incolli solo tu, direttamente nei Secrets. Non scriverle in chat, in file o nel codice.

## 1. Account Instagram professionale

L'account `@you.didnot.know` deve essere di tipo **Creator** o **Attività** (Impostazioni → Tipo di account e strumenti).

## 2. App Meta

1. Vai su developers.facebook.com e accedi con il tuo profilo Facebook. La prima volta premi **Inizia** (*Get Started*), accetta le condizioni e conferma email o telefono.
2. **Le mie app** (*My Apps*) → **Crea app** (*Create App*).
3. Nome `You Did Not Know Bot` e la tua email → Avanti.
4. Caso d'uso: **Gestisci messaggi e contenuti su Instagram** (*Manage messaging & content on Instagram*) → Avanti.
5. Business: **Non voglio collegare un portfolio aziendale per ora** → Avanti → **Vai alla dashboard**.

L'app può restare in modalità sviluppo: sei il proprietario dell'account, basta l'accesso "Standard" e non serve la revisione di Meta.

## 3. Aggiungi l'account Instagram all'app

Nella dashboard: **Instagram → Configurazione API con accesso tramite Instagram** (*API setup with Instagram login*).

1. Aggiungi l'account `@you.didnot.know` (accedi con le credenziali Instagram quando richiesto).
2. Controlla che tra i permessi dell'app ci siano `instagram_business_basic`, `instagram_business_content_publish` e `instagram_business_manage_insights`. Il terzo serve per le statistiche; senza, il bot legge solo like e commenti.

## 4. Genera il token

Nella stessa pagina premi **Genera token** accanto all'account, accedi a Instagram e **copia il token**. Secondo la documentazione di Meta vale 60 giorni.

## 5. Ricava IG_USER_ID

Apri nel browser questo indirizzo, sostituendo `IL_TOKEN` con il token appena copiato (il token resta nella cronologia del browser: dopo l'uso cancellala, oppure usa una finestra privata):

```
https://graph.instagram.com/v26.0/me?fields=user_id,username&access_token=IL_TOKEN
```

La risposta contiene `username` (deve essere `you.didnot.know`) e `user_id`: quest'ultimo è `IG_USER_ID`.

## 6. Secrets su GitHub

Repo → Settings → Secrets and variables → Actions → New repository secret. Crea `ANTHROPIC_API_KEY`, `IG_ACCESS_TOKEN` e `IG_USER_ID` con i nomi esatti.

## 7. Rinnovo automatico del token (`GH_PAT`)

Il token Instagram dura 60 giorni. Il workflow `rinnovo-token.yml` lo rinnova il 1 e il 15 di ogni mese e salva il nuovo valore in `IG_ACCESS_TOKEN`. Per poter scrivere nei Secrets gli serve un token personale GitHub:

1. GitHub → clic sulla tua foto → **Settings** → in fondo **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**.
2. Nome `rinnovo-token-instagram`. Scadenza: la più lunga consentita (di solito 1 anno).
3. **Repository access** → *Only select repositories* → scegli solo `visibellibusiness-ai/Claude`.
4. **Permissions** → **Repository permissions** → **Secrets**: *Read and write*. Nessun altro permesso (Metadata in sola lettura compare da solo).
5. **Generate token**, copialo e salvalo come secret `GH_PAT` (stessa pagina del passo 6).
6. **Promemoria:** il `GH_PAT` scade (al massimo dopo un anno). Metti nel calendario un avviso 2 settimane prima: dopo la scadenza il rinnovo si ferma, e il token Instagram scade dopo al massimo 60 giorni.

Il rinnovo funziona solo se il token ha almeno 24 ore ed è ancora valido. Il primo giorno, quindi, non lanciarlo a mano: aspetta il giorno dopo.

## 8. Repo pubblico

Settings → General → Danger Zone → **Change visibility** → Public. Instagram scarica immagini e video da `raw.githubusercontent.com`, che per i repo privati non è raggiungibile. Prima di farlo controlla che nel repo non ci siano file con dati personali o chiavi.

## 9. Primo post

1. Actions → **Pubblica post Instagram** → **Run workflow** → scegli `facts`.
2. Apri il giro e leggi i log. Se un passo fallisce, copia il messaggio d'errore.

## Cosa non è stato provato dal vivo

- La pubblicazione con questo accesso, cioè tutto il flusso: nel codice è provata solo con risposte simulate.
- Che Instagram accetti i video da `raw.githubusercontent.com` (nel caso, si può usare GitHub Pages sul branch `media`).
- Il Trial Reel con l'accesso Instagram: se Meta lo rifiuta, il bot pubblica un Reel normale.
- Il carosello 4:5: Meta indica che i caroselli vengono ritagliati come la prima immagine, con 1:1 predefinito.

## Se il token scade o il rinnovo fallisce

GitHub manda una email quando un workflow fallisce. Rigenera il token dalla dashboard (passo 4), aggiorna il secret `IG_ACCESS_TOKEN` e rilancia **Rinnova il token Instagram** il giorno dopo.
