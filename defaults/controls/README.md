# Controlli negativi

Testi non tuoi, uno per file, in `defaults/controls/<formato>/` (forniti dal plugin) o in `controls/<formato>/` dentro la cartella di una voce, che hanno la precedenza. `stylometry.py calibrate` li usa per misurare quanto il controllo separa la tua voce da una voce diversa, e il metodo degli impostori li usa come alternativa a ogni bozza. Senza controlli `compare` non può dare un esito.

Oggi sono saggi di 700-1300 parole generati da un LLM, con `ai_assisted: true` nel frontmatter, di due tipi:

- `ctrl-`: scritti senza istruzioni di stile, sui temi del corpus.
- `hard-`: scritti applicando le regole di prosa italiana e i divieti di `divieti.md`, ma senza guida di voce né corpus. Sono il confronto più severo: dicono se una bozza si distingue da una prosa pulita ma generica.

Il controllo misura perciò la distanza dalla prosa di un modello, che è il difetto da evitare. Non dimostra di riconoscere altri autori umani: per quello servono testi di altre persone, che si possono aggiungere in questa cartella.

Quantità: almeno 8 per formato (`check` lo richiede), meglio 15-20. Stesso argomento e stessa lunghezza del corpus rendono il confronto più severo.
