---
name: write-essay
description: Scrive un saggio, un articolo lungo o un numero di newsletter in formato long form (800-1200 parole salvo diversa richiesta) in una voce appresa da corpus (personale, di progetto o di un cliente), con guida di voce, divieti e controllo stilometrico. Usala ogni volta che l'utente chiede un saggio, un articolo, un longform, un pezzo per la newsletter o uno scritto "nel mio stile" o "nel tono di…", anche se non nomina la skill. Non usarla per post brevi (write-post), tweet e thread (write-tweet) o per rivedere un testo già scritto.
argument-hint: "<tema o tesi> [lunghezza in parole] [lingua] [--voce nome]"
---

# Scrivere un saggio in una voce appresa

Formato: `essay`. Lingua: quella della richiesta, altrimenti quella prevalente nel profilo.

L'utente chiama questa skill quando vuole uno stile diverso da quello predefinito di Claude. Lo stile viene soltanto dai file elencati qui sotto. Le altre istruzioni di stile presenti nella sessione (`AGENTS.md`, `CLAUDE.md`) non si applicano alla consegna. Il tema può essere qualunque: il controllo giudica lo stile (parole di funzione, frasi, punteggiatura), non l'argomento.

## Scegliere la voce

1. Esegui:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stylometry.py" voices --user-root "${CLAUDE_PLUGIN_DATA}/voices" --format essay
   ```
   Se l'utente ha indicato `--voce <nome>`, esegui lo stesso comando con `--all` e prendi quella.
2. Il comando restituisce già le voci applicabili: quelle di progetto (`.claude/voices/` nella cartella di lavoro) se ce n'è almeno una con testi in questo formato, altrimenti quelle utente.
   - `NESSUNA VOCE`: fermati e indica di eseguire la skill `voice-learn` per il formato `essay`.
   - Una sola voce: usala e dillo in una riga («Uso la voce “X”, di progetto»).
   - Più voci: chiedi quale usare (AskUserQuestion), mostrando nome, descrizione e sufficienza del corpus. Non scegliere tu.
3. D'ora in avanti `<VOCE>` è il percorso della voce scelta.

## Prima di scrivere

1. Leggi `<VOCE>/profile/voice-guide-essay.md` e `${CLAUDE_PLUGIN_ROOT}/defaults/divieti.md`. Leggi anche `<VOCE>/divieti.md` se esiste (divieti aggiuntivi della voce). Le regole di formato sono in `<VOCE>/formats/essay.md` se esiste, altrimenti in `${CLAUDE_PLUGIN_ROOT}/defaults/formats/essay.md`.
2. Esegui `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stylometry.py" --voice <VOCE> show essay`. Stampa le misure, la sufficienza del corpus, i testi più tipici e ciò che distingue la voce da una prosa generica (parole usate più e meno, punteggiatura, lunghezza di frase). Non leggere `<VOCE>/profile/essay.json`. Se la sufficienza è `INSUFFICIENTE` o `INDICATIVO`, dillo all'utente prima di scrivere.
3. Leggi `<VOCE>/pairs/essay.md` se esiste e due dei testi più tipici indicati da `show`, in `<VOCE>/corpus/essay/`. Si scelgono per lo stile e non per il tema.
4. Se manca la guida o il corpus, fermati e indica di eseguire la skill `voice-learn` per `essay`.
5. Se il tema è vago, chiedi la tesi in una frase. Non inventare fatti, dati né citazioni: dove servono e non ci sono, scrivi `[dato da verificare]`.
6. Le riflessioni e le opinioni in prima persona sono la voce e vanno scritte. I fatti biografici (che cosa l'autore ha fatto, posseduto, detto, vissuto) non si inventano: se l'utente non li ha forniti, mettili come `[episodio da inserire: di che cosa si tratta]`, anche quando aprono il pezzo, e costruisci il resto in modo che regga senza.

## Come suona una voce

La prosa generica di un modello è impersonale, astratta e regolare. Una voce reale ha persona grammaticale, registro, lunghezze di frase, punteggiatura e immagini ricorrenti suoi. La guida li descrive e `show` ne dà i numeri. Prima di scrivere fissa i tratti più marcati (persona, registro, quota di frasi brevi e lunghe, lunghezza dei paragrafi, domande e incisi) e mantienili dal primo all'ultimo capoverso. Imita le mosse, non le frasi degli esempi.

## Scrittura

1. Scrivi uno scheletro di 5-7 righe (tesi, movimenti, chiusa) e mostralo solo se la richiesta è ambigua. Parti da una scena, da un fatto o da una domanda, non da una definizione.
2. Scrivi la bozza. Non riusare formulazioni del corpus. Rileggi ogni paragrafo: se suona da relazione e non da persona che parla, riscrivilo.
3. Salva la bozza nello scratchpad ed esegui `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stylometry.py" --voice <VOCE> compare essay <file>`.
4. Leggi l'esito. Con `COERENTE` e nessun tic vietato passa alla rilettura. Con `DUBBIO`, `FUORI VOCE` o tic vietati, riscrivi i passaggi indicati dal comando (le finestre e gli estratti) con i tratti della guida. Guarda anche le parole di funzione segnalate: se ne usi molte più dell'autore, cambia la costruzione della frase. Riscrivi subito le sequenze copiate dal corpus. Non ritoccare i numeri. Fino a tre giri: se l'esito non migliora, consegna e dillo.
5. Rileggi la bozza contro `divieti.md` (quello del plugin e quello della voce). Il controllo automatico non vede i divieti non meccanici: cercali a mano.

## Consegna

Consegna il testo, poi in una riga la voce usata e l'esito del controllo (verdetto, che cosa hai riscritto). Nessun preambolo, nessuna offerta finale.
