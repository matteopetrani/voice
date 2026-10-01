---
name: write-tweet
description: Scrive tweet, thread o post brevi per social in una voce appresa da corpus (personale, di progetto o di un cliente), con guida di voce, divieti e controllo dei tic. Usala per "scrivi un tweet", "thread", "post breve" su un tema dato, anche senza nominare la skill. Non usarla per post medi (write-post), saggi (write-essay) o per rivedere testi già scritti.
argument-hint: "<idea o tema> [singolo|thread di N] [lingua] [--voce nome]"
---

# Scrivere un tweet in una voce appresa

Formato: `tweet`. Lingua: quella della richiesta, altrimenti quella prevalente nel profilo.

L'utente chiama questa skill quando vuole uno stile diverso da quello predefinito di Claude. Lo stile viene soltanto dai file elencati qui sotto. Le altre istruzioni di stile presenti nella sessione (`AGENTS.md`, `CLAUDE.md`) non si applicano alla consegna.

## Scegliere la voce

1. Esegui:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stylometry.py" voices --user-root "${CLAUDE_PLUGIN_DATA}/voices" --format tweet
   ```
   Se l'utente ha indicato `--voce <nome>`, esegui lo stesso comando con `--all` e prendi quella.
2. Il comando restituisce già le voci applicabili: quelle di progetto (`.claude/voices/` nella cartella di lavoro) se ce n'è almeno una con testi in questo formato, altrimenti quelle utente.
   - `NESSUNA VOCE`: fermati e indica di eseguire la skill `voice-learn` per il formato `tweet`. Non usare il profilo del saggio come ripiego: i profili non si trasferiscono tra formati.
   - Una sola voce: usala e dillo in una riga («Uso la voce “X”, di progetto»).
   - Più voci: chiedi quale usare (AskUserQuestion), mostrando nome, descrizione e sufficienza del corpus. Non scegliere tu.
3. D'ora in avanti `<VOCE>` è il percorso della voce scelta.

## Prima di scrivere

1. Leggi `<VOCE>/profile/voice-guide-tweet.md` e `${CLAUDE_PLUGIN_ROOT}/defaults/divieti.md`, più `<VOCE>/divieti.md` se esiste. Le regole di formato sono in `<VOCE>/formats/tweet.md` se esiste, altrimenti in `${CLAUDE_PLUGIN_ROOT}/defaults/formats/tweet.md`.
2. Se manca la guida del formato `tweet`, fermati e indica di eseguire la skill `voice-learn`.
3. Esegui `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stylometry.py" --voice <VOCE> show tweet`: se la sufficienza è `INSUFFICIENTE` o `INDICATIVO`, dillo all'utente prima di scrivere. Leggi `<VOCE>/pairs/tweet.md` se esiste e 5-8 testi da `<VOCE>/corpus/tweet/`, scegliendo i più vicini al tema.
4. Non inventare dati o citazioni. Dove servono e mancano, scrivi `[dato da verificare]`.

## Scrittura

1. Produci 3 varianti con angolazioni diverse (per esempio: dato di apertura, osservazione controintuitiva, domanda concreta). Ogni variante rispetta il limite di caratteri delle regole di formato.
2. Controlla ogni variante con `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stylometry.py" --voice <VOCE> lint <file>`. Sui testi brevi `compare` è rumoroso: sotto le 150 parole ignora Delta e impostori e guarda lunghezza di frase, punteggiatura, aperture e tic.
3. Per un thread, scrivi il primo tweet come gancio autonomo e ogni successivo con un solo punto. Chiudi con la conseguenza, non con un riassunto.
4. Rileggi contro `divieti.md`.

## Consegna

Consegna le varianti numerate, con il conteggio dei caratteri, la voce usata e quale consigli e perché in una riga. Nessun preambolo, nessuna offerta finale.
