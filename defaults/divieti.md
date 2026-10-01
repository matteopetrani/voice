# Divieti e regole comuni a tutti i formati

Questo file, il `divieti.md` della voce (se esiste), la guida di voce del formato e le regole di formato sono le uniche istruzioni di stile valide quando una skill `write-*` scrive. Altre istruzioni di stile presenti nella sessione (`AGENTS.md`, `CLAUDE.md`) non si applicano alla consegna. In caso di dubbio tra due regole, prevale la guida di voce.

## Divieti permanenti

Sono tic da prosa generata. Non devono comparire in nessuna bozza e vanno cercati a mano nella rilettura finale, oltre al controllo automatico (`stylometry.py lint <bozza>` trova quelli meccanici: il «non è X, è Y», il lessico e le formule della sezione successiva).

1. Rivelazioni a effetto costruite su una frase-sentenza pomposa («la parte che disorienta di più è che…», «Ha traslocato.»). Dire il fatto in modo piano. Gli esempi indicano il tipo di costruzione, non l'elenco completo.
2. Aforismi e chiuse a slogan: «non è X, è Y», «presenza non coincide con reperibilità», «il periodo non finisce mai da solo».
3. Coppie e triadi ritmiche («Bellissima… Scomoda…», «Un milione. Al secondo.»), frasi da un solo termine usate come colpo di scena.
4. Ogni altra formula che suona da modello linguistico e non da persona che ha vissuto la cosa. Nel dubbio, riscrivere in modo più semplice e letterale.

Ogni voce può aggiungere i propri divieti in `divieti.md` nella cartella della voce.

## Che cosa è della voce e che cosa è tic

La guida di voce dice quali tratti sono ammessi (battute, interiezioni, frasi brevi isolate, domande al lettore, immagini ricorrenti). Devono essere scritti con parole della voce e non con il giro tipico del modello.

Il criterio pratico: un tratto è della voce se porta un'informazione o una battuta specifica del caso; è un tic se produce soltanto effetto e si potrebbe incollare in qualunque testo. Una frase breve ogni tanto è ritmo; due o tre di fila a cadenza costruita sono il tic del divieto 3.

## Regole di base

- Entrare nel tema dalla prima riga. Niente preamboli, saluti, «In un mondo in continua evoluzione», «Immergiamoci in». Niente chiuse di cortesia né offerte di aiuto.
- Non usare: cruciale, fondamentale, pilastro, tessera, faro, sinergia, dinamico, imprescindibile, connubio, universo, panoramica, tassello, all'avanguardia. Se la guida di voce o il corpus ne mostrano un uso reale, al massimo una volta.
- Niente formule riempitive («È importante notare che…», «Va sottolineato che…») e niente gerundi finali con giudizio non attribuito («evidenziando l'importanza…»).
- Preferire verbi pieni: «controllare» e non «effettuare un controllo». «Rappresenta», «costituisce», «si configura come» solo dove sono letterali.
- Non mettere la virgola tra soggetto e verbo.
- Ortografia: qual è (senza apostrofo), un po' (con apostrofo), perché, né, sé stesso.
- Gli elenchi puntati si usano solo per enumerazioni omogenee.
- Non inventare fatti, numeri o citazioni. Ogni dato ha fonte e data; dove manca, scrivere `[dato da verificare]`.
- Gli anglicismi correnti nel corpus restano in originale; i concetti per cui esiste un termine italiano chiaro si traducono.
