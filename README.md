# voice

Plugin per Claude Code. Impara una **voce di scrittura** da un corpus di testi e scrive saggi, post e tweet in quella voce, con un controllo stilometrico locale che segnala quando la bozza torna a suonare come la prosa di un modello. Pensato per l'italiano.

Si usa quando serve uno stile diverso da quello predefinito di Claude. Lo stile viene soltanto dai file della voce scelta.

## Installazione

```
/plugin marketplace add matteopetrani/voice
/plugin install voice@voice
```

Richiede `python3` (solo libreria standard, nessuna dipendenza).

## Skill

- `/voice:voice-learn [formato] [testo o URL]`: crea o aggiorna una voce. Chiede se è **dell'utente** (resta tua in ogni cartella: tono personale, professionale da freelance) o **del progetto** (salvata in `.claude/voices/` nella cartella di lavoro: il tono di un cliente), che tipo di tono è, e da dove prendere i testi. Calcola profilo e calibrazione e verifica che il corpus basti.
- `/voice:write-essay`, `write-post`, `write-tweet`: scrivono nel formato indicato. Cercano prima una voce di progetto, poi una dell'utente; se ce n'è più d'una chiedono quale usare. Con `--voce nome` la scelgono direttamente.

Formati: `essay` (800-1200 parole), `post` (150-400 parole, sito o LinkedIn), `tweet` (tweet e thread).

## Dove stanno i dati

Il plugin non contiene testi di nessuno. Le voci vivono fuori dalla cartella del plugin, che viene sostituita a ogni aggiornamento:

| Ambito | Percorso | Quando |
|---|---|---|
| Utente | `${CLAUDE_PLUGIN_DATA}/voices/<nome>/` | tono che ti segue in ogni cartella |
| Progetto | `<cartella di lavoro>/.claude/voices/<nome>/` | tono legato a un progetto o a un cliente |

Una voce contiene `voice.json`, `corpus/<formato>/`, `profile/`, `pairs/` e, se serve, `divieti.md`, `formats/<formato>.md` e `controls/<formato>/`. Nei progetti condivisi `voice-learn` offre di tenere il corpus fuori da git.

Il plugin fornisce in `defaults/`: i divieti comuni (tic da prosa generata), le regole predefinite dei formati e 18 controlli negativi per `essay`, così `calibrate` funziona subito.

## Che cosa misura il controllo

Cosine Delta sulle parole di funzione e impostori generali, calibrati con leave-one-out su controlli negativi generati da LLM. Misura la distanza dalla prosa generica, non un'attribuzione d'autore. Dettagli e limiti in [scripts/README.md](scripts/README.md).

## Riservatezza

Il corpus resta sul disco. Quello che Claude legge durante una sessione passa dal servizio che stai usando: per testi riservati di terzi (per esempio un cliente) verifica prima cosa consente il contratto.

## Licenza

MIT, vedi [LICENSE](LICENSE).
