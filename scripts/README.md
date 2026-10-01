# Script

Libreria standard di Python, nessuna dipendenza.

- `stylometry.py`: `voices`, `new-voice`, `analyze`, `calibrate`, `check`, `compare`, `lint`, `show`, `status` (vedi `-h`). I comandi che lavorano su una voce vogliono `--voice <cartella>`; `voices` elenca quelle disponibili (di progetto prima, poi utente).
- `fetch_corpus.py`: scarica pagine pubbliche (URL, sitemap, feed) e le salva nel corpus di una voce (`--voice`) come markdown.

## Che cosa misura stylometry.py

1. **Cosine Delta.** Le caratteristiche sono solo le frequenze relative delle parole del lessico chiuso: articoli, preposizioni (semplici e articolate), congiunzioni, pronomi, determinanti, avverbi di uso generale e forme di essere, avere, fare, potere, dovere, volere, andare, stare, circa 270 voci (l'elenco è `CLOSED_CLASS` in `stylometry.py`). Le elisioni sono separate («dell'» e «uomo»), così gli articoli si contano anche davanti a una vocale. Queste parole non dipendono dall'argomento: il controllo giudica lo stile, non il tema, e funziona per un saggio sull'AI come per uno sulle cose che non si riesce a buttare. Di ogni testo si calcola la frequenza relativa, si standardizza in z-score sul corpus di riferimento e si misura la distanza coseno dal centroide dei tuoi testi. È la variante di Burrows' Delta che Evert e colleghi (2017) hanno trovato più robusta.
2. **Impostori generali, versione ridotta.** In 400 estrazioni casuali, con metà delle parole e con otto testi tuoi contro otto controlli, si conta quante volte la bozza è più vicina a un tuo testo che a un controllo. Semplifica il metodo di Koppel e Winter (2014), che usa impostori raccolti dal web.
3. **Finestre.** La bozza è scorsa in finestre di 250 parole; quelle con Delta oltre il 95° percentile dei tuoi testi sono indicate, così si riscrive il passaggio e non tutto.
4. **Misure di superficie.** Lunghezza di frase e di paragrafo, varietà lessicale e delle aperture, quota di frasi brevi e lunghe, avverbi in -mente, punteggiatura. Servono a diagnosticare, non a decidere.
5. **Tic.** Espressioni regolari per i divieti meccanici di `defaults/divieti.md`: virgola prima di «e», trattino lungo, lessico inflazionato, «non è X, è Y», gerundi giudicanti e simili.

## Come si decide l'esito

`calibrate` fa un leave-one-out: ogni tuo testo è giudicato da un modello costruito senza di lui, ogni controllo da un modello senza di lui. Dai due insiemi ricava l'AUC e due soglie per ciascun metodo: la soglia che massimizza l'accuratezza bilanciata (sotto la quale il testo è coerente) e il decimo percentile dei controlli (oltre il quale il testo è nel territorio dei controlli). Le salva nel profilo.

`compare` dà `COERENTE` se Delta e impostori stanno dalla parte dei tuoi testi, `FUORI VOCE` se stanno entrambi nel territorio dei controlli, `DUBBIO` negli altri casi.

## Sufficienza del corpus (`check`)

Risponde alla domanda «ho testi a sufficienza per inferire lo stile?» con quattro criteri e un esito (`SUFFICIENTE`, `INDICATIVO`, `INSUFFICIENTE`):

1. **Quantità.** Almeno 8 testi e 10.000 parole per «sufficiente»; almeno 5 testi e 3.000 parole per «indicativo».
2. **Stabilità delle misure.** Intervallo di confidenza bootstrap al 95% (1000 ricampionamenti dei testi) sulla media di lunghezza di frase (limite ±10%), di lunghezza di parola (±10%) e sulla deviazione standard delle frasi (±20%). Lunghezza di paragrafo e quota di frasi brevi sono riportate ma non vincolano: dipendono dall'impaginazione e da pochi eventi.
3. **Saturazione.** Curva di apprendimento: il Delta mediano dei testi esclusi, al crescere dei testi usati per il centroide, non deve scendere di più di 0,02 negli ultimi due passi da due testi.
4. **Calibrazione.** AUC di Delta e impostori almeno 0,90, almeno il 90% dei tuoi testi giudicati coerenti, almeno 8 controlli.

Le soglie sono euristiche, scelte da chi ha scritto lo script. «Sufficiente» indica misure stabili su questo corpus, non uno stile certo. Eder (2015) ha trovato che l'attribuzione d'autore affidabile richiede in genere campioni anonimi di 2500-5000 parole: una bozza di 1000 parole sta sotto quel limite. Per questo il controllo si legge come distanza dalla prosa generica.

## fetch_corpus.py

Legge un feed RSS/Atom, una sitemap o un elenco di URL, scarica ogni pagina, ne estrae il testo dell'`<article>` (o di `<main>`) e lo salva in `<voce>/corpus/<formato>/AAAA-MM-GG_slug.md` con `ai_assisted: unverified`. Rispetta `robots.txt`, aspetta 1,5 secondi tra le richieste, scarta le pagine sotto 150 parole e avvisa quando la coda sembra una rubrica. Non scarica social protetti né aggira login: per quelli servono i testi esportati o incollati dall'utente. L'autore deve confermare che i testi sono suoi e non scritti da un LLM prima di `analyze`.

## Limiti

- Con 16 testi e 18 controlli le AUC sono stime rumorose. Il lessico chiuso è stato scelto a priori, per indipendenza dal tema, dopo che una selezione per frequenza documentale faceva cadere fuori soglia due tuoi testi per le parole di tema («design», «macchine»).
- Il tema incide ancora un po' attraverso le costruzioni: un saggio su un oggetto che si possiede fa usare molto «ho» e «lo». `compare` segnala queste parole e dice di cambiare costruzione.
- I controlli sono prosa di LLM, non altri autori.
- Sotto 300 parole Delta e impostori non sono affidabili.
- Il controllo vale come sentinella. Ottimizzare le bozze sui numeri le peggiora: si riscrivono i passaggi segnalati.

## Riferimenti

- Evert, Proisl, Jannidis, Reger, Pielström, Schöch, Vitt (2017), *Understanding and explaining Delta measures for authorship attribution*, Digital Scholarship in the Humanities.
- Koppel e Winter (2014), *Determining if two documents are written by the same author*, JASIST.
- Eder (2015), *Does size matter? Authorship attribution, small samples, big problem*, Digital Scholarship in the Humanities.
