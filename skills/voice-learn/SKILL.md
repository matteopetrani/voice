---
name: voice-learn
description: Impara e aggiorna una voce di scrittura. Chiede se la voce è dell'utente (disponibile in ogni cartella) o del progetto (salvata in .claude/voices/ nella cartella di lavoro), di che tipo di tono si tratta, poi parte dai testi già presenti oppure chiede siti e profili da cui scaricarne e verifica che il corpus sia abbastanza esteso e stabile per inferire lo stile. Usala quando si vuole creare una voce, aggiungere testi, "imparare", "aggiornare", "ricalcolare" o "ricalibrare" uno stile, quando si indica un sito o un blog da cui prendere i testi, o quando la guida di una voce non riflette più i testi recenti.
argument-hint: "[formato: essay|tweet|post] [percorso di un testo o URL di un sito, sitemap o feed da cui scaricare]"
---

# Apprendimento e aggiornamento di una voce

Una **voce** è una cartella con i testi di riferimento (corpus), il profilo misurabile, la guida scritta e le coppie neutro-originale. Una voce può essere dell'utente, per esempio il tono personale o quello professionale da freelance, oppure di un progetto, per esempio il tono delle landing page di un cliente. Le skill `write-*` leggono guida, coppie e riepilogo del profilo della voce scelta.

Dove stanno le voci:

- **Utente**: `${CLAUDE_PLUGIN_DATA}/voices/<nome>/`. Sopravvive agli aggiornamenti del plugin e vale in ogni cartella di lavoro.
- **Progetto**: `<cartella di lavoro>/.claude/voices/<nome>/`. Vale solo in quella cartella ed è la prima a essere cercata.

Dentro ogni voce: `voice.json`, `corpus/<formato>/`, `profile/` (`<formato>.json` e `voice-guide-<formato>.md`), `pairs/<formato>.md`. Facoltativi: `divieti.md` (divieti aggiuntivi), `formats/<formato>.md` (regole di formato che sostituiscono quelle predefinite), `controls/<formato>/` (controlli negativi propri).

## Passi

1. **Ambito e voce.** Esegui `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stylometry.py" voices --user-root "${CLAUDE_PLUGIN_DATA}/voices" --all` per vedere le voci esistenti.
   - Chiedi (AskUserQuestion) dove salvare la voce: **utente** (disponibile in ogni cartella) o **progetto** (nella cartella nascosta `.claude/voices/` di questa cartella di lavoro). Se l'utente lo ha già detto, non chiederlo.
   - Se nell'ambito scelto esistono voci, chiedi se aggiornarne una o crearne una nuova.
   - Per una voce nuova chiedi che tipo di tono è: un nome breve e una riga di descrizione («personale», «professionale da freelance», «landing page del cliente X»). Poi creala:
     ```bash
     python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stylometry.py" new-voice --root "<RADICE>" --name "<nome>" --description "<descrizione>"
     ```
     con `<RADICE>` uguale a `${CLAUDE_PLUGIN_DATA}/voices` per l'utente e a `<cartella di lavoro>/.claude/voices` per il progetto. Il comando stampa il percorso: da qui è `<VOCE>`.
   - Voce di progetto: chiedi se il corpus deve restare fuori da git. Se sì, aggiungi `.claude/voices/*/corpus/` al `.gitignore` della cartella (crealo se manca e la cartella è un repository). Profilo, guida e divieti restano versionabili e il team può usare la voce senza ricalcolarla. Se il corpus è di un cliente, ricorda di verificare che il contratto consenta di caricare i suoi testi in un servizio di terzi.
2. **Stato e fonti.** Esegui `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/stylometry.py" --voice <VOCE> status` e guarda quanti testi ha `<VOCE>/corpus/<formato>/`.
   - Se il corpus c'è, lavora su quello. Se l'argomento contiene il percorso di un testo, copialo nella cartella (passo 3).
   - Se manca o è sotto la soglia di sufficienza, chiedi all'utente da dove prendere i testi: sito, blog, newsletter, profili social, documenti. Preferisci, nell'ordine, feed RSS o sitemap, poi URL singoli. Scarica con `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/fetch_corpus.py" --voice <VOCE> <formato> --feed <url>` (oppure `--sitemap <url>`, oppure gli URL uno per uno); usa `--dry-run` per vedere prima l'elenco e `--match` per tenere solo gli articoli.
   - LinkedIn, X e Instagram non si scaricano: lo script non aggira login né blocchi. Chiedi l'archivio esportato dalla piattaforma o i testi incollati, e salvali tu nel corpus.
   - Non scaricare oltre quanto serve. Il corpus contiene solo testi della persona o del marchio di cui la voce è il tono, che l'utente ha il diritto di usare. Non salvare testi di altri.
3. **Pulizia e conferma.** Ogni file ha nome `AAAA-MM-GG_slug.md` e frontmatter (`lang`, `date`, `source`, `ai_assisted`). I testi scaricati hanno `ai_assisted: unverified`: chiedi se sono dell'autore della voce e se sono stati scritti o rifiniti con un LLM, poi imposta `false` o `true` (un testo con `true` è escluso dal profilo). Togli da ogni testo ciò che non è il pezzo: rubriche di coda («Cosa sto leggendo», «Link belli»), inviti a condividere, elenchi di link, commenti, menu. Lo script avvisa quando la coda sembra una rubrica, ma non sempre la vede: rileggi la fine di ogni testo. Le misure contano queste parti come prosa e falsano lunghezza di frase e punteggiatura.
4. **Controlli negativi.** `calibrate` ha bisogno di almeno 8 testi non dell'autore, sugli stessi temi e della stessa lunghezza. Per `essay` il plugin ne fornisce già 18 (`defaults/controls/essay`) e non serve fare nulla. Per `post` e `tweet`, o se vuoi controlli più vicini al tuo genere, creali in `<VOCE>/controls/<formato>/`. Servono due tipi: testi scritti da un LLM senza istruzioni di stile (prefisso `ctrl-`) e testi scritti da un LLM con le regole di prosa e i divieti ma senza la guida di voce (prefisso `hard-`). Il secondo tipo misura davvero se la skill raggiunge la voce. Generali con sottoagenti, con `ai_assisted: true` nel frontmatter. Testi di altri autori umani migliorano la calibrazione.
5. **Calcolo.** Esegui in ordine `--voice <VOCE> analyze <formato>`, `calibrate <formato>` e `check <formato>`. `calibrate` salva soglie e AUC, `check` salva l'esito di sufficienza: non copiarli a mano nella guida, riportane solo i valori finali nella sezione Affidabilità.
6. **Sufficienza.** Leggi l'esito di `check`.
   - `INSUFFICIENTE`: fermati. Di' che cosa manca (testi, parole, calibrazione) e torna al passo 2 chiedendo altre fonti. Non scrivere la guida.
   - `INDICATIVO`: scrivi la guida marcandola «provvisoria» in testa e ripeti le cautele. Dichiara quali criteri non sono soddisfatti.
   - `SUFFICIENTE`: prosegui. Vuol dire misure stabili su questo corpus, non stile certo: vale per testi dello stesso genere e periodo, e il controllo misura la distanza dalla prosa generica.
7. **Lettura qualitativa.** Leggi almeno 5 testi del formato (i più recenti e i più caratteristici). Le misure non catturano struttura dell'argomentazione, uso dell'esempio, ironia, aperture e chiuse. Cerca quelle.
8. **Guida di voce.** Scrivi o aggiorna `<VOCE>/profile/voice-guide-<formato>.md` con queste sezioni, in prosa asciutta e con una citazione breve dal corpus a sostegno di ogni tratto:
   - **Descrittori:** 5-8 aggettivi con evidenza.
   - **Mosse ricorrenti:** come apre, come argomenta, come chiude.
   - **Lessico e sintassi:** parole e costrutti che usa, che evita, lunghezza tipica delle frasi (da `show`).
   - **Punteggiatura e tipografia:** dai valori misurati.
   - **Divieti:** ciò che non compare mai nel corpus e suona estraneo. I divieti comuni a tutte le voci stanno in `${CLAUDE_PLUGIN_ROOT}/defaults/divieti.md`: non duplicarli. Se la voce ha regole sue di gusto (per esempio niente virgola prima di «e», niente trattino lungo), scrivile in `<VOCE>/divieti.md`. Per far trattare come vietati anche i controlli meccanici corrispondenti, aggiungi a `<VOCE>/voice.json` la chiave `"lint_vietato"` con i nomi tra `virgola_prima_di_e`, `trattino_lungo`, `grassetto_nel_testo`.
   - **Affidabilità:** numero di testi e parole, data dell'ultimo aggiornamento, esito di `check`, AUC, limiti.
9. **Coppie neutro-originale (metodo STYLL).** Per ogni formato scegli fino a 8 passaggi rappresentativi e scrivi in `<VOCE>/pairs/<formato>.md` la parafrasi neutra e il passaggio originale. Scarta i passaggi che contengono tic dei divieti (prova con `--voice <VOCE> lint`): gli esempi insegnano ciò che imitano.
10. **Differenza.** Se esisteva un profilo precedente, riferisci in poche righe che cosa è cambiato (lunghezza media delle frasi, punteggiatura, aperture, AUC, sufficienza). Se un valore cambia molto con pochi testi nuovi, segnala il rischio di deriva e chiedi se il testo nuovo rappresenta la voce che si vuole.
11. **Chiusura.** Di' dove è stata salvata la voce (percorso e ambito) e come usarla: le skill `write-*` la trovano da sole, e se ce n'è più d'una chiedono quale usare.

## Regole

- Non inventare tratti che il corpus non mostra. Se manca evidenza scrivi `[dato da verificare]`.
- Il profilo vale per una lingua e un formato. Non usare il profilo `tweet` per un saggio. Il controllo stilometrico è tarato sull'italiano.
- Le soglie di sufficienza sono euristiche (vedi `${CLAUDE_PLUGIN_ROOT}/scripts/README.md`) e le AUC, con pochi testi, sono stime rumorose. Dillo quando le riporti.
- Non modificare i file del corpus, tranne aggiungere il frontmatter a un testo appena copiato o scaricato e togliere le parti che non sono il pezzo (passo 3).
- Non scrivere mai dentro la cartella del plugin (`${CLAUDE_PLUGIN_ROOT}`): ogni aggiornamento la sostituisce. I dati vanno solo nella voce.
- Scarica solo pagine pubbliche e rispetta `robots.txt`: lo script lo fa, non chiedergli di aggirarlo.
