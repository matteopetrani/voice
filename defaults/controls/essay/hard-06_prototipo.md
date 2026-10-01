---
lang: it
source: controllo negativo difficile, LLM con regole di prosa e divieti ma senza guida di voce
ai_assisted: true
---

# Quando un prototipo sembra finito ma non lo è

Un prototipo cliccabile con transizioni animate, testi rifiniti e nomi plausibili nei campi viene giudicato come un prodotto. Succede in ogni riunione di restituzione: chi guarda lo schermo vede un'app funzionante, e la domanda successiva riguarda la data di rilascio. Chi l'ha costruito sa che dietro ogni pulsante c'è un collegamento tracciato a mano, con un solo esito possibile. La distanza tra ciò che si vede e ciò che esiste produce la maggior parte dei malintesi tra design e sviluppo.

## La finitura visiva comunica completezza

I margini allineati, le icone coerenti e gli stati di caricamento sono i segnali con cui chiunque riconosce un software collaudato. Chi non progetta li legge così, in buona fede. Un wireframe a matita produce l'effetto contrario: il tratto incerto dichiara che la struttura è ancora aperta, e le persone discutono dell'architettura invece che del colore dei bottoni. Quando la fedeltà sale cambia il tipo di feedback. Le domande sul senso di un passaggio lasciano spazio alle richieste di spostare un'etichetta di due pixel.

Alzare la fedeltà ha quindi un costo che non compare nel preventivo. Ogni ora spesa sulle rifiniture sposta l'attenzione del cliente verso ciò che si può ritoccare e la allontana da ciò che manca.

## Il prototipo racconta il percorso in cui tutto va bene

Prendiamo l'onboarding di una banca, con apertura del conto da smartphone. Nel prototipo la persona inserisce un codice fiscale valido, il documento viene riconosciuto al primo scatto e il riconoscimento video parte senza interruzioni. Nel servizio reale il codice fiscale può contenere un'omocodia, con lettere al posto di alcune cifre, e il modulo lo rifiuta perché la validazione era scritta per il caso comune. Il documento può essere scaduto. La connessione cade a metà del video. Il cliente ricorda di avere lo SPID ma non la password.

Ciascuna di queste eccezioni richiede una schermata, un testo, una regola di business e spesso un operatore dell'assistenza che sappia che cosa è successo al cliente. Il prototipo ne mostra zero. Chi ha progettato solo il percorso principale ha completato una parte del lavoro, forse la più rapida, perché i casi limite richiedono decisioni che il percorso principale permette di rimandare.

Gli stati vuoti e gli errori sono un buon indicatore. Se nel file non esiste la schermata che compare quando la lista è vuota, quando il server non risponde o quando la persona non ha i permessi, il prototipo copre la superficie e lascia scoperto il comportamento.

## I dati di prova nascondono i problemi di contenuto

Nei prototipi gli elenchi hanno tre voci ordinate, gli importi sono tondi e i nomi sono Mario Rossi e Laura Bianchi. Nel servizio reale l'elenco ha zero voci o trecento, gli importi hanno sette cifre e i cognomi sono doppi, con apostrofi e accenti. Un titolo di due righe nel prototipo diventa di cinque in una traduzione o in un caso reale, e il layout cede. La maggior parte delle regressioni visive scoperte in fase di sviluppo nasce da contenuti che nessuno ha provato a inserire.

## Il prototipo mostra soltanto ciò che sta davanti

Nel linguaggio del service design, il prototipo rappresenta il frontstage. Non dice chi riceve la segnalazione inviata dall'utente, in quanto tempo e con quale strumento. Non dice quale sistema esistente fornisce il dato che la schermata visualizza, né con quale ritardo. Non dice se l'ufficio legale ha approvato il testo del consenso.

Nella pubblica amministrazione il divario è frequente. Un modulo online che nel prototipo conclude la pratica con la schermata «Richiesta inviata» può in realtà depositare un messaggio in una casella condivisa, letta da due persone che poi inseriscono i dati a mano in un gestionale. Il cittadino vede una conferma immediata che il servizio non è in grado di mantenere. Nessun test di usabilità lo rileva, perché il problema sta dietro lo schermo.

## La validazione conferma soltanto ciò che il prototipo contiene

Jakob Nielsen sostiene dal 2000 che cinque partecipanti bastano a individuare circa l'85% dei problemi di usabilità di un'interfaccia. Il dato riguarda però i problemi dell'interfaccia testata, cioè di quelle schermate in quello scenario. Se il prototipo non contiene il caso dell'omocodia, nessuno dei cinque partecipanti lo incontrerà e il test restituirà un esito positivo su un perimetro più stretto di quanto sembri.

Pesa anche la conduzione. In un test moderato il facilitatore conosce il percorso corretto e, quando la persona si perde, la riporta sulla strada con un suggerimento. Le persone inoltre si comportano con più pazienza davanti a un osservatore di quanta ne avrebbero da sole in coda alla fermata. Un test positivo dice che il percorso progettato è comprensibile, e non dice che il servizio regge.

## Che cosa fare

Il rimedio consiste nel rendere visibile ciò che manca, prima che qualcuno lo scopra in produzione.

Conviene anzitutto dare al prototipo il suo nome esatto. «Simulazione del percorso principale» descrive il contenuto meglio di «prototipo dell'app», e sposta l'aspettativa del cliente dalla data di rilascio alla discussione sul perimetro.

Serve poi una mappa di copertura allegata al file, con l'elenco delle schermate progettate, di quelle solo previste e di quelle non ancora considerate. Basta una tabella di tre colonne. Il suo effetto pratico è che, leggendola, il cliente vede la proporzione tra ciò che ha davanti e ciò che resta da fare.

In restituzione vale la pena mostrare un caso di errore prima del percorso felice. Se il primo scenario che il cliente vede è la password dimenticata o il documento rifiutato, capisce subito che il lavoro riguarda anche le eccezioni, e le richieste successive cambiano.

Infine il prototipo andrebbe fatto leggere al team che lo svilupperà prima della consegna, con un compito preciso: elencare tutto ciò che nello schermo dipende da un dato, da un'integrazione o da una regola che oggi non esiste. Chi sviluppa trova in un'ora ciò che il designer non ha modo di sapere, e la lista che ne risulta diventa la base per stimare il lavoro vero.

Un prototipo è finito quando, insieme alle schermate, consegna l'elenco dei punti in cui non regge. Senza quell'elenco resta una bella simulazione, e verrà giudicata come un prodotto da chi non ha partecipato alla sua costruzione.
