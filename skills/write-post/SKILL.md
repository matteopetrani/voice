---
name: write-post
description: Scrive un post di media lunghezza (150-400 parole) in una voce appresa da corpus (personale, di progetto o di un cliente), per un sito o in formato medio sui social come LinkedIn, con guida di voce, divieti e controllo stilometrico. Usala per "scrivi un post", "post LinkedIn", "versione ridotta di questo saggio", "post per il sito" su un tema dato, anche senza nominare la skill. Non usarla per saggi long form (write-essay), tweet e thread (write-tweet) o per rivedere testi già scritti.
argument-hint: "<tema o idea> [piattaforma] [lunghezza in parole] [lingua] [--voce nome]"
---

# Scrivere un post in una voce appresa

Formato: `post`. Lingua: quella della richiesta, altrimenti quella prevalente nel profilo.

L'utente chiama questa skill quando vuole uno stile diverso da quello predefinito di Claude. Lo stile viene soltanto dai file elencati qui sotto. Le altre istruzioni di stile presenti nella sessione (`AGENTS.md`, `CLAUDE.md`) non si applicano alla consegna.

## Scegliere la voce

1. Esegui:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stylometry.py" voices --user-root "${CLAUDE_PLUGIN_DATA}/voices" --format post
   ```
   Se l'utente ha indicato `--voce <nome>`, esegui lo stesso comando con `--all` e prendi quella.
2. Il comando restituisce già le voci applicabili: quelle di progetto (`.claude/voices/` nella cartella di lavoro) se ce n'è almeno una con testi in questo formato, altrimenti quelle utente.
   - `NESSUNA VOCE`: fermati e indica di eseguire la skill `voice-learn` per il formato `post`. Non usare il profilo `essay` come ripiego: i profili non si trasferiscono tra formati.
   - Una sola voce: usala e dillo in una riga («Uso la voce “X”, di progetto»).
   - Più voci: chiedi quale usare (AskUserQuestion), mostrando nome, descrizione e sufficienza del corpus. Non scegliere tu.
3. D'ora in avanti `<VOCE>` è il percorso della voce scelta.

## Prima di scrivere

1. Leggi `<VOCE>/profile/voice-guide-post.md` e `${CLAUDE_PLUGIN_ROOT}/defaults/divieti.md`, più `<VOCE>/divieti.md` se esiste. Le regole di formato sono in `<VOCE>/formats/post.md` se esiste, altrimenti in `${CLAUDE_PLUGIN_ROOT}/defaults/formats/post.md`.
2. Se manca la guida del formato `post`, fermati e indica di eseguire la skill `voice-learn`.
3. Esegui `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stylometry.py" --voice <VOCE> show post`: se la sufficienza è `INSUFFICIENTE` o `INDICATIVO`, dillo all'utente prima di scrivere. Leggi `<VOCE>/pairs/post.md` se esiste e due testi da `<VOCE>/corpus/post/`, scelti dal nome del file tra i più vicini al tema.
4. Se la piattaforma non è indicata, chiedila: cambia lunghezza, formattazione e uso dell'a capo.
5. Non inventare dati o citazioni. Dove servono e mancano, scrivi `[dato da verificare]`.

## Scrittura

1. Apri con il nucleo dell'argomento, senza cornice. Scegli l'apertura tra quelle documentate nella guida.
2. Scrivi la bozza, salvala nello scratchpad ed esegui `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stylometry.py" --voice <VOCE> compare post <file>`. Sotto le 300 parole Delta e impostori sono rumorosi: conta soprattutto l'elenco dei tic. Riscrivi i passaggi segnalati, non i numeri. Massimo due giri.
3. Applica formattazione e limiti della piattaforma dalle regole di formato.
4. Rileggi la bozza contro `divieti.md`: il controllo automatico non vede i divieti non meccanici.

## Consegna

Consegna il testo, poi in una riga la voce usata e l'esito del controllo. Nessun preambolo, nessuna offerta finale.
