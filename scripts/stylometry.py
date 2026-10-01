#!/usr/bin/env python3
"""Controllo stilometrico locale, senza dipendenze esterne.

Uso: stylometry.py [--voice CARTELLA_VOCE] <comando> ...

Una voce è una cartella con voice.json, corpus/<formato>/, profile/ e pairs/. I comandi che lavorano su una voce
richiedono --voice. Le voci stanno in <progetto>/.claude/voices/<nome>/ (progetto) oppure nella cartella dati del
plugin, voices/<nome>/ (utente): il comando `voices` le elenca.

Comandi:
  voices    [--user-root DIR] [--project DIR] [--format F] [--all] [--json]
                                       elenca le voci disponibili; senza --all restituisce solo quelle da usare
  new-voice --root DIR --name NOME [--description D]
                                       crea la cartella di una voce nuova
  analyze   <formato> [--lang it|en]   legge <voce>/corpus/<formato>/ e scrive <voce>/profile/<formato>.json
  calibrate <formato>                  misura quanto il controllo separa i tuoi testi dai controlli negativi
                                       (<voce>/controls/<formato>/ se ce ne sono, altrimenti quelli del plugin) e salva soglie e AUC nel profilo
  compare   <formato> <bozza> [-v]     giudica una bozza: esito, scostamenti, finestre anomale, tic
  check     <formato>                  verifica se il corpus è abbastanza esteso e stabile per inferire lo stile
  lint      <bozza>                    cerca solo i tic da prosa generata (con --voice applica i divieti meccanici di quella voce)
  show      <formato>                  stampa in forma compatta il profilo (al posto di leggere il json)
  status                               riepilogo di corpus, controlli e profili della voce

Metodo (vedi scripts/README.md):
  - Cosine Delta di Burrows/Evert: frequenze relative delle parole del lessico chiuso (articoli, preposizioni, pronomi, ausiliari…), standardizzate in z-score
    sul corpus di riferimento, confrontate con il centroide dei testi dell'autore per distanza coseno.
  - Impostori generali (Koppel e Winter, versione ridotta): ripetute estrazioni casuali di sottoinsiemi di
    parole e di testi; si conta quante volte la bozza è più vicina ai testi dell'autore che ai controlli negativi.
  - Soglie e AUC ricavate da leave-one-out sui testi dell'autore e dai controlli negativi, non fissate a mano.

Un file del corpus può avere un frontmatter con: lang, date, source, ai_assisted.
I file del corpus con `ai_assisted: true` vengono esclusi dal profilo; i controlli negativi sono sempre inclusi.
"""
import argparse
import datetime
import json
import math
import os
import random
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
DEFAULT_CONTROLS = PLUGIN / "defaults" / "controls"
VOICE = CORPUS = CONTROLS = PROFILE = None

N_MFW = 300
WINDOW = 250
WINDOW_STEP = 125
GI_ROUNDS = 400
MIN_WORDS_RELIABLE = 300

FUNCTION_WORDS = {
    "it": (
        "il lo la i gli le un uno una di a da in con su per tra fra e ed o ma però anche se che chi cui non "
        "più come quando dove perché quindi allora poi già ancora sempre mai solo tutto tutti questo questa "
        "questi queste quello quella ci si mi ti ne è sono era ha hanno del dello della dei degli delle al "
        "allo alla ai agli alle dal dallo dalla dai dagli dalle nel nello nella nei negli nelle sul sullo "
        "sulla sui sugli sulle io tu lui lei noi voi loro mio tuo suo nostro vostro"
    ).split(),
    "en": (
        "the a an of to in on at by for with from and or but if that which who whom whose not no more as when "
        "where because so then also still always never only all this these those it its is are was were be been "
        "has have had do does did will would can could should may might i you he she we they me him her us them "
        "my your his our their there here than too very just about into over after before"
    ).split(),
}

PUNCT = {
    "virgola": ",",
    "punto_e_virgola": ";",
    "due_punti": ":",
    "trattino_lungo": "—",
    "trattino_medio": "–",
    "parentesi": "(",
    "punto_interrogativo": "?",
    "punto_esclamativo": "!",
    "virgolette_alte": '"“',
    "virgolette_basse": "«",
    "puntini": "…",
}

SCALARS = [
    "sent_len_mean", "sent_len_sd", "word_len_mean", "para_len_words_mean",
    "ttr_500", "sent_per_para", "opener_variety", "short_share", "long_share", "mente_per_1000",
]

# Tic da prosa generata. Regole meccaniche: quelle semantiche stanno in defaults/divieti.md e nel divieti.md della voce.
# gravita: "vietato" = compare sempre nell'elenco; "verifica" = solo conteggio, il corpus ne contiene.
LINT_RULES = [
    ("virgola_prima_di_e", "vietato", re.compile(r",\s+(?:e|ed)\b"), "virgola prima di «e»"),
    ("trattino_lungo", "vietato", re.compile("—"), "trattino lungo"),
    ("lessico_da_ia", "vietato", re.compile(
        r"\b(?:cruciale|cruciali|fondamentale|fondamentali|pilastro|pilastri|tessera|faro|sinergia|sinergie|"
        r"dinamico|dinamica|dinamici|dinamiche|imprescindibile|imprescindibili|connubio|universo|panoramica|"
        r"tassello|all['’]avanguardia)\b", re.I), "lessico inflazionato"),
    ("incipit_retorico", "vietato", re.compile(
        r"\b(?:in un mondo|in un['’]era|in un['’]epoca|nell['’]era|nel panorama|immergiamoci|"
        r"non è un mistero|in continua evoluzione)\b", re.I), "formula d'apertura generica"),
    ("riempitivo", "vietato", re.compile(
        r"\b(?:è importante (?:notare|sottolineare|evidenziare)|va sottolineato|vale la pena (?:notare|sottolineare)|"
        r"è (?:bene|doveroso) (?:ricordare|precisare))\b", re.I), "riempitivo"),
    ("contrasto_non_e", "vietato", re.compile(
        r"\bnon (?:è|sono|era|si tratta di) [^.;:!?]{1,60}?[,;] (?:è|sono|ma|bensì)\b", re.I), "«non è X, è Y»"),
    ("gerundio_giudicante", "vietato", re.compile(
        r",\s+(?:evidenziando|sottolineando|dimostrando|rivelando|riflettendo|confermando|ribadendo)\b", re.I),
        "gerundio finale con giudizio"),
    ("anafora_questo", "vietato", re.compile(
        r"(?:^|[.!?]\s+)(?:Questo|Ciò)\s+(?:permette|consente|comporta|rende|significa|implica)\b"),
        "«questo permette/comporta…»"),
    ("offerta_finale", "vietato", re.compile(
        r"\b(?:fammi sapere|se vuoi|spero che|resto a disposizione|sono qui per)\b", re.I), "chiusa di cortesia"),
    ("grassetto_nel_testo", "vietato", re.compile(r"\*\*[^*\n]+\*\*"), "grassetto nel paragrafo"),
    ("non_solo_ma", "verifica", re.compile(
        r"\bnon (?:solo|soltanto|tanto)\b[^.!?]{1,120}\b(?:ma|bensì)\b", re.I), "«non solo… ma»"),
    ("verbo_burocratico", "verifica", re.compile(
        r"\b(?:rappresenta|rappresentano|costituisce|costituiscono|si configura|si pone (?:come|quale))\b", re.I),
        "verbo burocratico"),
]
SHORT_RUN_MAX_WORDS = 2

# Regole di gusto personale: di default sono solo conteggi ("verifica"). Diventano "vietato" se la voce
# le elenca in voice.json, chiave "lint_vietato" (per esempio ["virgola_prima_di_e", "trattino_lungo"]).
LINT_PERSONAL = {"virgola_prima_di_e", "trattino_lungo", "grassetto_nel_testo"}


def apply_lint_policy(vietati):
    LINT_RULES[:] = [
        (n, ("vietato" if n in vietati else "verifica") if n in LINT_PERSONAL else sev, rx, d)
        for n, sev, rx, d in LINT_RULES
    ]


apply_lint_policy([])


# ---------------------------------------------------------------- voci

def voice_meta(vdir):
    try:
        return json.loads((Path(vdir) / "voice.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def set_voice(path):
    """Imposta la voce su cui lavorano i comandi."""
    global VOICE, CORPUS, CONTROLS, PROFILE
    VOICE = Path(path).expanduser().resolve()
    if not VOICE.is_dir():
        sys.exit(f"Voce non trovata: {VOICE}. Elenca le voci con `voices --all`.")
    CORPUS = VOICE / "corpus"
    PROFILE = VOICE / "profile"
    CONTROLS = VOICE / "controls"
    apply_lint_policy(voice_meta(VOICE).get("lint_vietato", []))


def need_voice(a):
    if not a.voice:
        sys.exit("Manca --voice <cartella della voce>. Elenca le voci con `voices`.")
    set_voice(a.voice)


def slugify(name):
    import unicodedata
    t = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-") or "voce"


def voice_formats(vdir):
    out = {}
    corpus = Path(vdir) / "corpus"
    for d in sorted(corpus.glob("*")) if corpus.is_dir() else []:
        if not d.is_dir():
            continue
        docs = load_dir(d, honor_ai_flag=True)
        if not docs:
            continue
        pf = Path(vdir) / "profile" / f"{d.name}.json"
        suf = "-"
        if pf.exists():
            suf = json.loads(pf.read_text(encoding="utf-8")).get("sufficiency", {}).get("verdict", "non verificata")
        out[d.name] = {"texts": len(docs), "words": sum(len(words(t)) for _, t, _ in docs),
                       "profile": pf.exists(), "sufficiency": suf}
    return out


def scan_voices(root, scope):
    root = Path(root).expanduser() if root else None
    found = []
    if not root or not root.is_dir():
        return found
    for d in sorted(root.iterdir()):
        if d.is_dir() and ((d / "voice.json").exists() or (d / "corpus").is_dir()):
            meta = voice_meta(d)
            found.append({"slug": d.name, "scope": scope, "name": meta.get("name", d.name),
                          "description": meta.get("description", ""), "path": str(d.resolve()),
                          "formats": voice_formats(d)})
    return found


def voices_cmd(a):
    project_root = Path(a.project).expanduser().resolve() / ".claude" / "voices"
    user_root = a.user_root or (Path(os.environ["CLAUDE_PLUGIN_DATA"]) / "voices" if os.environ.get("CLAUDE_PLUGIN_DATA") else None)
    project = scan_voices(project_root, "progetto")
    user = scan_voices(user_root, "utente")
    if a.all:
        chosen, scope = project + user, "tutte"
    else:
        fits = lambda v: not a.format or a.format in v["formats"]
        pf, uf = [v for v in project if fits(v)], [v for v in user if fits(v)]
        chosen, scope = (pf, "progetto") if pf else (uf, "utente")
    if a.json:
        print(json.dumps({"scope": scope, "voices": chosen,
                          "project_root": str(project_root), "user_root": str(user_root) if user_root else None},
                         ensure_ascii=False, indent=2))
        return
    print(f"Radice voci di progetto: {project_root}")
    print(f"Radice voci utente: {user_root or '(non impostata: passa --user-root)'}")
    if not chosen:
        print("NESSUNA VOCE" + (f" con testi nel formato {a.format}" if a.format else "") + ". Esegui /voice:voice-learn.")
        return
    print(f"Ambito: {scope}; voci: {len(chosen)}")
    for v in chosen:
        fm = "; ".join(f"{k}: {x['texts']} testi, {x['words']} parole, profilo {'sì' if x['profile'] else 'no'}, sufficienza {x['sufficiency']}"
                       for k, x in v["formats"].items()) or "nessun testo"
        print(f"- {v['slug']} [{v['scope']}] «{v['name']}»" + (f" ({v['description']})" if v["description"] else ""))
        print(f"  percorso: {v['path']}")
        print(f"  {fm}")


def new_voice_cmd(a):
    slug = slugify(a.name)
    vdir = Path(a.root).expanduser() / slug
    if vdir.exists():
        sys.exit(f"Esiste già una voce '{slug}' in {vdir}. Aggiornala con /voice-learn oppure scegli un altro nome.")
    for sub in ("corpus", "profile", "pairs"):
        (vdir / sub).mkdir(parents=True)
    meta = {"name": a.name, "description": a.description or "", "created": datetime.date.today().isoformat()}
    (vdir / "voice.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Voce creata: {vdir.resolve()}")


# ---------------------------------------------------------------- testo

def parse(path):
    return clean_text(Path(path).read_text(encoding="utf-8"))


def clean_text(raw):
    meta = {}
    m = re.match(r"^---\n(.*?)\n---\n", raw, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"')
        raw = raw[m.end():]
    raw = re.sub(r"```.*?```", " ", raw, flags=re.S)
    raw = re.sub(r"^#{1,6}\s+.*$", "", raw, flags=re.M)
    raw = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", raw)
    return raw.strip(), meta


FEAT_RX = re.compile(r"[^\W\d_]+['’]|[^\W\d_]+")

# Lessico chiuso dell'italiano: articoli, preposizioni, congiunzioni, pronomi, determinanti, avverbi
# di uso generale e forme di essere, avere, fare, potere, dovere, volere, andare, stare.
# Sono le parole che non dipendono dall'argomento: il controllo giudica lo stile, non il tema.
CLOSED_CLASS = set((
    "il lo la i gli le l' un uno una un' di a da in con su per tra fra del dello della dei degli delle dell' "
    "al allo alla ai agli alle all' dal dallo dalla dai dagli dalle dall' nel nello nella nei negli nelle nell' "
    "sul sullo sulla sui sugli sulle sull' col "
    "e ed o oppure ma però anzi tuttavia eppure invece dunque quindi perciò allora infatti cioè ovvero né neanche "
    "nemmeno neppure che se perché poiché siccome mentre quando come dove benché sebbene anche pure "
    "io tu lui lei noi voi loro mi ti si ci vi ne li me te sé mio mia miei mie tuo tua tuoi tue suo sua suoi sue "
    "nostro nostra nostri nostre vostro vostra vostri vostre chi cui quale quali quanto quanta quanti quante "
    "questo questa questi queste quello quella quelli quelle quell' quest' ciò stesso stessa stessi stesse altro "
    "altra altri altre ogni qualche qualsiasi qualunque nessuno nessuna niente nulla tutto tutta tutti tutte "
    "molto molta molti molte poco poca pochi poche troppo troppa troppi troppe tanto tanta tanti tante alcuni "
    "alcune alcun alcuno certo certa "
    "non più già ancora sempre mai solo soltanto proprio così forse magari davvero insomma beh boh ecco ok poi "
    "prima dopo oggi ieri domani ora adesso qui qua lì là sopra sotto dentro fuori insieme almeno appena "
    "abbastanza piuttosto spesso comunque infine ormai subito presto tardi bene male meglio peggio sì no "
    "po' c' d' s' m' t' n' v' "
    "è sono sei siamo siete era ero eri eravamo erano fu sarà sarebbe sia siano stato stata stati state "
    "ho hai ha abbiamo avete hanno aveva avevo avevano avrà avrebbe abbia abbiano avuto "
    "fa faccio fai facciamo fanno fare fatto può posso puoi possiamo possono potrebbe potremmo possa possano "
    "deve devo devi dobbiamo devono dovrebbe dovremmo debba vuole voglio vuoi vogliamo vogliono vorrei vorrebbe "
    "va vado vai andiamo vanno sta sto stai stiamo stanno"
).split())


def feat_words(text):
    """Parole per Delta e impostori: l'elisione è separata («dell'» e «uomo»), così gli articoli restano contabili."""
    return [w.lower().replace("’", "'") for w in FEAT_RX.findall(text)]


def words(text):
    return re.findall(r"[^\W\d_]+(?:['’][^\W\d_]+)?", text.lower())


def sentences(text):
    flat = re.sub(r"\s+", " ", text)
    parts = re.split(r"(?<=[.!?…])\s+(?=[«\"“(]?[A-ZÀ-ÖØ-Þ0-9])", flat)
    return [p for p in parts if words(p)]


def detect_lang(ws):
    scores = {l: sum(1 for w in ws if w in set(fw)) for l, fw in FUNCTION_WORDS.items()}
    return max(scores, key=scores.get)


def trigrams(text):
    t = re.sub(r"\s+", " ", text.lower())
    return Counter(t[i:i + 3] for i in range(len(t) - 2))


def doc_features(text, lang):
    ws = words(text)
    sents = sentences(text)
    paras = [p for p in re.split(r"\n\s*\n", text) if words(p)]
    lens = [len(words(s)) for s in sents] or [0]
    openers = Counter(words(s)[0] for s in sents if words(s))
    n = max(len(ws), 1)
    return {
        "n_words": len(ws),
        "sent_len_mean": statistics.mean(lens),
        "sent_len_sd": statistics.pstdev(lens),
        "word_len_mean": statistics.mean(len(w) for w in ws) if ws else 0,
        "para_len_words_mean": statistics.mean(len(words(p)) for p in paras) if paras else 0,
        "sent_per_para": len(sents) / max(len(paras), 1),
        "ttr_500": len(set(ws[:500])) / max(len(ws[:500]), 1),
        "opener_variety": len(openers) / max(len(sents), 1),
        "short_share": sum(1 for x in lens if x <= 5) / max(len(lens), 1),
        "long_share": sum(1 for x in lens if x >= 30) / max(len(lens), 1),
        "mente_per_1000": sum(1 for w in ws if len(w) > 7 and w.endswith("mente")) * 1000 / n,
        "punct_per_1000": {k: sum(text.count(ch) for ch in c) * 1000 / n for k, c in PUNCT.items()},
        "top_openers": openers.most_common(8),
    }


def load_dir(folder, honor_ai_flag):
    docs = []
    for p in sorted(Path(folder).glob("*")):
        if p.suffix not in {".md", ".txt"} or p.name.lower().startswith("readme"):
            continue
        text, meta = parse(p)
        if not text or (honor_ai_flag and meta.get("ai_assisted", "").lower() == "true"):
            continue
        docs.append((p, text, meta.get("lang") or detect_lang(words(text))))
    return docs


def load_corpus(fmt, lang=None):
    docs = load_dir(CORPUS / fmt, honor_ai_flag=True)
    return [d for d in docs if not lang or d[2] == lang]


def load_controls(fmt, lang=None):
    """Controlli della voce per il formato; se mancano, quelli forniti dal plugin."""
    for base in (CONTROLS, DEFAULT_CONTROLS):
        folder = base / fmt
        docs = [d for d in load_dir(folder, honor_ai_flag=False) if not lang or d[2] == lang] if folder.exists() else []
        if docs:
            return docs
    return []


def mean_dict(dicts):
    return {k: statistics.mean(d[k] for d in dicts) for k in dicts[0]}


# ---------------------------------------------------------------- vettori

def cosine_dict(a, b):
    keys = set(a) | set(b)
    dot = sum(a.get(k, 0) * b.get(k, 0) for k in keys)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def cosine(a, b, dims=None):
    idx = dims if dims is not None else range(len(a))
    dot = na = nb = 0.0
    for i in idx:
        x, y = a[i], b[i]
        dot += x * y
        na += x * x
        nb += y * y
    return dot / math.sqrt(na * nb) if na and nb else 0.0


def normalize(c, top=300):
    tot = sum(c.values()) or 1
    return {k: v / tot for k, v in c.most_common(top)}


def rel_freq(ws, mfw):
    c = Counter(ws)
    n = max(len(ws), 1)
    return [c[w] / n for w in mfw]


def choose_mfw(word_lists, n=N_MFW, vocab=CLOSED_CLASS):
    """Le parole del lessico chiuso con frequenza relativa media più alta, presenti in più di un testo.

    Il lessico chiuso (articoli, preposizioni, congiunzioni, pronomi, avverbi generali, ausiliari) non dipende
    dall'argomento: il controllo giudica lo stile, non il tema.
    """
    acc, df = Counter(), Counter()
    for ws in word_lists:
        c, tot = Counter(ws), max(len(ws), 1)
        for w, k in c.items():
            if w in vocab:
                acc[w] += k / tot
                df[w] += 1
    return [w for w, _ in acc.most_common() if df[w] >= 2][:n]


def build_model(auth_rel, ctrl_rel):
    """Statistiche di z-score sul corpus di riferimento (autore più controlli) e centroide dell'autore."""
    ref = auth_rel + ctrl_rel
    dim = len(ref[0])
    mean = [statistics.mean(v[i] for v in ref) for i in range(dim)]
    sd = [statistics.pstdev([v[i] for v in ref]) or 1.0 for i in range(dim)]
    z = lambda v: [(v[i] - mean[i]) / sd[i] for i in range(dim)]
    auth_z = [z(v) for v in auth_rel]
    ctrl_z = [z(v) for v in ctrl_rel]
    centroid = [statistics.mean(v[i] for v in auth_z) for i in range(dim)]
    return {"z": z, "auth_z": auth_z, "ctrl_z": ctrl_z, "centroid": centroid, "dim": dim}


def delta(model, zq):
    return 1 - cosine(zq, model["centroid"])


def gi_score(model, zq, rounds=GI_ROUNDS, seed=0):
    """Impostori generali ridotti: frazione di estrazioni in cui la bozza è più vicina all'autore che ai controlli."""
    if len(model["ctrl_z"]) < 3 or len(model["auth_z"]) < 3:
        return None
    rng = random.Random(seed)
    dim, m = model["dim"], min(len(model["auth_z"]), len(model["ctrl_z"]), 8)
    wins = 0.0
    for _ in range(rounds):
        dims = rng.sample(range(dim), dim // 2)
        sa = max(cosine(zq, x, dims) for x in rng.sample(model["auth_z"], m))
        si = max(cosine(zq, x, dims) for x in rng.sample(model["ctrl_z"], m))
        wins += 1.0 if sa > si else 0.5 if sa == si else 0.0
    return wins / rounds


def windows(ws, size=WINDOW, step=WINDOW_STEP):
    if len(ws) < size + step:
        return []
    return [(i, ws[i:i + size]) for i in range(0, len(ws) - size + 1, step)]


def auc(pos, neg, higher_is_better=True):
    """Probabilità che un testo dell'autore ottenga un punteggio migliore di un controllo."""
    if not pos or not neg:
        return None
    s = 0.0
    for p in pos:
        for n in neg:
            if p == n:
                s += 0.5
            elif (p > n) == higher_is_better:
                s += 1.0
    return s / (len(pos) * len(neg))


def best_threshold(pos, neg, higher_is_better=True):
    """Soglia che massimizza l'accuratezza bilanciata; a parità, il centro del tratto ottimo."""
    vals = sorted(set(pos + neg))
    cands = [(a + b) / 2 for a, b in zip(vals, vals[1:])] or vals
    best, best_ba = [], -1.0
    for t in cands:
        if higher_is_better:
            tp = sum(1 for p in pos if p >= t) / len(pos)
            tn = sum(1 for n in neg if n < t) / len(neg)
        else:
            tp = sum(1 for p in pos if p <= t) / len(pos)
            tn = sum(1 for n in neg if n > t) / len(neg)
        ba = (tp + tn) / 2
        if ba > best_ba + 1e-12:
            best, best_ba = [t], ba
        elif abs(ba - best_ba) <= 1e-12:
            best.append(t)
    return statistics.mean(best), best_ba


# ---------------------------------------------------------------- modello del formato

def reference(fmt, lang):
    a = load_corpus(fmt, lang)
    c = load_controls(fmt, lang)
    if not a:
        sys.exit(f"Nessun testo in {CORPUS / fmt}.")
    a_ws = [feat_words(t) for _, t, _ in a]
    c_ws = [feat_words(t) for _, t, _ in c]
    mfw = choose_mfw(a_ws + c_ws)
    a_rel = [rel_freq(w, mfw) for w in a_ws]
    c_rel = [rel_freq(w, mfw) for w in c_ws]
    return {"docs": a, "controls": c, "a_ws": a_ws, "c_ws": c_ws, "mfw": mfw, "a_rel": a_rel, "c_rel": c_rel}


# ---------------------------------------------------------------- tic

def lint(text):
    """Restituisce (occorrenze, conteggi). Ogni occorrenza: (paragrafo, regola, gravita, descrizione, estratto)."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    hits = []
    for pi, p in enumerate(paras, 1):
        for name, sev, rx, desc in LINT_RULES:
            for m in rx.finditer(p):
                a, b = max(m.start() - 25, 0), min(m.end() + 25, len(p))
                hits.append((pi, name, sev, desc, p[a:b].replace("\n", " ")))
        sents = sentences(p)
        run = 0
        for s in sents + [""]:
            if s and len(words(s)) <= SHORT_RUN_MAX_WORDS:
                run += 1
                continue
            if run >= 2:
                hits.append((pi, "frasi_monoparola", "vietato", "serie di frasi di uno o due termini", p[:60]))
            run = 0
        for line in p.splitlines():
            if re.match(r"^\s*[-*•]\s+\S", line):
                hits.append((pi, "elenco_puntato", "verifica", "voce di elenco puntato", line.strip()[:50]))
    if paras:
        last = paras[-1]
        if len(paras) > 1 and re.search(r"\?\s*$", last) is None and len(words(last)) < 4:
            hits.append((len(paras), "chiusa_monca", "verifica", "ultimo paragrafo di meno di 4 parole", last))
    counts = Counter(h[1] for h in hits)
    return hits, counts


def print_lint(hits, n_words, limit=12):
    vietati = [h for h in hits if h[2] == "vietato"]
    verifica = Counter(h[1] for h in hits if h[2] == "verifica")
    print(f"Tic vietati: {len(vietati)}" + (" (nessuno)" if not vietati else ""))
    for pi, name, _, desc, snip in vietati[:limit]:
        print(f"  par. {pi} [{name}] {desc}: …{snip}…")
    if len(vietati) > limit:
        print(f"  (+{len(vietati) - limit} altri)")
    if verifica:
        print("Da verificare (presenti anche nel corpus): " + ", ".join(f"{k} {v}" for k, v in verifica.items()))


# ---------------------------------------------------------------- comandi

def analyze(fmt, lang):
    docs = load_corpus(fmt, lang)
    if not docs:
        sys.exit(f"Nessun testo in {CORPUS / fmt} (lingua: {lang or 'qualsiasi'}). Aggiungi file .md o .txt.")
    lang = lang or Counter(l for _, _, l in docs).most_common(1)[0][0]
    per_doc = [doc_features(t, lang) for _, t, _ in docs]
    total_words = sum(f["n_words"] for f in per_doc)
    scalars = {
        k: {"mean": statistics.mean(f[k] for f in per_doc),
            "sd": statistics.pstdev([f[k] for f in per_doc]) if len(per_doc) > 1 else 0.0}
        for k in SCALARS
    }
    all_sents = [len(words(s)) for _, t, _ in docs for s in sentences(t)]
    q = statistics.quantiles(all_sents, n=10) if len(all_sents) > 10 else all_sents
    hits_per_doc = [lint(t)[1] for _, t, _ in docs]
    lint_rate = {r[0]: sum(c[r[0]] for c in hits_per_doc) * 1000 / total_words
                 for r in LINT_RULES}
    profile = {
        "format": fmt,
        "lang": lang,
        "n_docs": len(docs),
        "n_words": total_words,
        "files": [p.name for p, _, _ in docs],
        "reliability": (
            "bassa: meno di 3000 parole o meno di 5 testi" if total_words < 3000 or len(docs) < 5
            else "media: base sufficiente per le feature di superficie" if total_words < 15000
            else "buona"
        ),
        "scalars": scalars,
        "sentence_length_deciles": q,
        "punct_per_1000": mean_dict([f["punct_per_1000"] for f in per_doc]),
        "lint_per_1000_corpus": lint_rate,
        "top_openers": Counter(
            {w: c for f in per_doc for w, c in f["top_openers"]}
        ).most_common(10),
    }
    PROFILE.mkdir(parents=True, exist_ok=True)
    out = PROFILE / f"{fmt}.json"
    out.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Profilo scritto in {out}")
    print(f"{len(docs)} testi, {total_words} parole, lingua {lang}, affidabilità {profile['reliability']}")
    unverified = [pth.name for pth, _, _ in docs if parse(pth)[1].get("ai_assisted", "").lower() != "false"]
    if unverified:
        print(f"ATTENZIONE: {len(unverified)} testi senza `ai_assisted: false` confermato (autore e uso di LLM da verificare): "
              + ", ".join(unverified[:5]) + ("…" if len(unverified) > 5 else ""))
    print("Il profilo è stato rigenerato: esegui anche `calibrate` per aggiornare soglie e AUC.")
    show(fmt)


def show(fmt):
    pf = PROFILE / f"{fmt}.json"
    if not pf.exists():
        sys.exit(f"Manca {pf}. Esegui prima: analyze {fmt}")
    p = json.loads(pf.read_text(encoding="utf-8"))
    s = p["scalars"]
    print(f"Profilo {p['format']} ({p['lang']}): {p['n_docs']} testi, {p['n_words']} parole, affidabilità {p['reliability'].split(':')[0]}")
    print("Misure per testo (media ± sd):")
    for k in SCALARS:
        print(f"  {k:22s} {s[k]['mean']:7.2f} ± {s[k]['sd']:.2f}")
    print("Decili di lunghezza frase (parole): " + ", ".join(f"{x:.0f}" for x in p["sentence_length_deciles"]))
    print("Punteggiatura per 1000 parole: " + ", ".join(
        f"{k} {v:.1f}" for k, v in sorted(p["punct_per_1000"].items(), key=lambda x: -x[1]) if v >= 0.5))
    print("Aperture frequenti: " + ", ".join(f"{w} ({c})" for w, c in p["top_openers"][:8]))
    cal = p.get("calibration")
    if cal:
        d, g = cal["delta"], cal["gi"]
        print(f"Calibrazione ({cal['n_genuine']} tuoi testi, {cal['n_control']} controlli): "
              f"AUC Delta {d['auc']:.2f}, AUC impostori {g['auc']:.2f}; "
              f"soglia Delta {d['threshold']:.3f}, soglia impostori {g['threshold']:.2f}")
    else:
        print("Calibrazione: assente. Esegui `calibrate`.")
    if cal:
        print("Testi più tipici della tua voce (da leggere per lo stile, a prescindere dal tema): " + ", ".join(cal.get("typical_texts", [])))
        contrast(fmt, top=10)
    suf = p.get("sufficiency")
    print(f"Sufficienza del corpus: {suf['verdict']}" if suf else "Sufficienza del corpus: non verificata. Esegui `check`.")


def calibrate(fmt):
    pf = PROFILE / f"{fmt}.json"
    if not pf.exists():
        sys.exit(f"Manca {pf}. Esegui prima: analyze {fmt}")
    p = json.loads(pf.read_text(encoding="utf-8"))
    ref = reference(fmt, p["lang"])
    na, nc = len(ref["docs"]), len(ref["controls"])
    if na < 4:
        sys.exit("Servono almeno 4 testi dell'autore per la calibrazione.")
    if nc < 3:
        sys.exit(f"Servono almeno 3 controlli negativi in {CONTROLS / fmt} o in {DEFAULT_CONTROLS / fmt} (testi non tuoi sugli stessi temi).")
    print(f"Leave-one-out su {na} tuoi testi; {nc} controlli negativi; {len(ref['mfw'])} parole più frequenti.")

    g_delta, g_gi, g_win = [], [], []
    c_delta, c_gi, c_win = [], [], []
    for i in range(na):
        model = build_model([v for j, v in enumerate(ref["a_rel"]) if j != i], ref["c_rel"])
        zq = model["z"](ref["a_rel"][i])
        g_delta.append(delta(model, zq))
        g_gi.append(gi_score(model, zq, seed=i))
        for _, wlist in windows(ref["a_ws"][i]):
            g_win.append(delta(model, model["z"](rel_freq(wlist, ref["mfw"]))))
        print(f"  tuo    {ref['docs'][i][0].name:44s} Delta {g_delta[-1]:.3f}  impostori {g_gi[-1]:.2f}")
    model = build_model(ref["a_rel"], ref["c_rel"])
    for k in range(nc):
        rest = [v for j, v in enumerate(ref["c_rel"]) if j != k]
        m2 = build_model(ref["a_rel"], rest)
        zq = m2["z"](ref["c_rel"][k])
        c_delta.append(delta(m2, zq))
        c_gi.append(gi_score(m2, zq, seed=100 + k))
        for _, wlist in windows(ref["c_ws"][k]):
            c_win.append(delta(m2, m2["z"](rel_freq(wlist, ref["mfw"]))))
        print(f"  altro  {ref['controls'][k][0].name:44s} Delta {c_delta[-1]:.3f}  impostori {c_gi[-1]:.2f}")

    def block(pos, neg, hib):
        thr, ba = best_threshold(pos, neg, hib)
        # soglia "fuori": il decimo percentile dei controlli dalla parte dei tuoi testi
        s_neg = sorted(neg, reverse=hib)
        out = s_neg[int(0.1 * (len(s_neg) - 1))]
        return {"genuine_mean": statistics.mean(pos), "genuine_sd": statistics.pstdev(pos),
                "control_mean": statistics.mean(neg), "control_sd": statistics.pstdev(neg),
                "auc": auc(pos, neg, hib), "threshold": thr, "out_threshold": out, "balanced_accuracy": ba}

    lint_g = [sum(lint(t)[1][r[0]] for r in LINT_RULES if r[1] == "vietato") * 1000 / max(len(words(t)), 1)
              for _, t, _ in ref["docs"]]
    lint_c = [sum(lint(t)[1][r[0]] for r in LINT_RULES if r[1] == "vietato") * 1000 / max(len(words(t)), 1)
              for _, t, _ in ref["controls"]]
    cal = {
        "n_genuine": na, "n_control": nc, "n_mfw": len(ref["mfw"]),
        "delta": block(g_delta, c_delta, False),
        "gi": block(g_gi, c_gi, True),
        "genuine_coherent_rate": sum(1 for d_, g_ in zip(g_delta, g_gi)
                                     if d_ <= best_threshold(g_delta, c_delta, False)[0]
                                     and g_ >= best_threshold(g_gi, c_gi, True)[0]) / na,
        "window_delta_p95_genuine": sorted(g_win)[int(0.95 * (len(g_win) - 1))] if g_win else None,
        "window_delta_median_control": statistics.median(c_win) if c_win else None,
        "tic_vietati_per_1000": {"tuoi": statistics.mean(lint_g), "controlli": statistics.mean(lint_c)},
        "note": "leave-one-out; MFW scelte sull'insieme completo (perdita lieve); controlli generati da LLM, non altri autori umani",
    }
    order = sorted(range(na), key=lambda i: g_delta[i])
    cal["typical_texts"] = [ref["docs"][i][0].name for i in order[:3]]
    p["calibration"] = cal
    pf.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    for k, label in (("delta", "Cosine Delta"), ("gi", "Impostori")):
        b = cal[k]
        print(f"{label:13s} AUC {b['auc']:.3f}  accuratezza bilanciata {b['balanced_accuracy']:.2f}  soglia {b['threshold']:.3f}  "
              f"(tuoi {b['genuine_mean']:.3f}±{b['genuine_sd']:.3f}, controlli {b['control_mean']:.3f}±{b['control_sd']:.3f})")
    print(f"Tic vietati per 1000 parole: tuoi {cal['tic_vietati_per_1000']['tuoi']:.2f}, controlli {cal['tic_vietati_per_1000']['controlli']:.2f}")
    print(f"Soglia di finestra (95° percentile dei tuoi): {cal['window_delta_p95_genuine']:.3f}")
    print("Calibrazione salvata nel profilo. Con pochi testi l'AUC è una stima rumorosa.")


def assess(fmt, text):
    """Valuta una bozza rispetto al profilo calibrato. Restituisce un dizionario usato da compare e dagli evals."""
    pf = PROFILE / f"{fmt}.json"
    if not pf.exists():
        sys.exit(f"Manca {pf}. Esegui prima: analyze {fmt}")
    p = json.loads(pf.read_text(encoding="utf-8"))
    cal = p.get("calibration")
    f = doc_features(text, p["lang"])
    ws = feat_words(text)
    ref = reference(fmt, p["lang"])
    model = build_model(ref["a_rel"], ref["c_rel"])
    zq = model["z"](rel_freq(ws, ref["mfw"]))
    d = delta(model, zq)
    g = gi_score(model, zq)
    verdict = "NON CALIBRATO"
    if cal and g is not None:
        coherent = d <= cal["delta"]["threshold"] and g >= cal["gi"]["threshold"]
        out = d >= cal["delta"]["out_threshold"] and g <= cal["gi"]["out_threshold"]
        verdict = "COERENTE" if coherent else "FUORI VOCE" if out else "DUBBIO"
    bad = []
    if cal and cal.get("window_delta_p95_genuine") is not None:
        starts = [m.start() for m in FEAT_RX.finditer(text)]
        for start, wl in windows(ws):
            dw = delta(model, model["z"](rel_freq(wl, ref["mfw"])))
            if dw > cal["window_delta_p95_genuine"]:
                pos = starts[start] if start < len(starts) else 0
                bad.append((start, dw, re.sub(r"\s+", " ", text[pos:pos + 90])))
    hits, _ = lint(text)
    # parole del lessico chiuso che si discostano di più dal centroide, con le frequenze per 1000 parole
    rel_a = [statistics.mean(v[k] for v in ref["a_rel"]) * 1000 for k in range(len(ref["mfw"]))]
    rel_q = [x * 1000 for x in rel_freq(ws, ref["mfw"])]
    dev = sorted(range(len(ref["mfw"])), key=lambda k: -abs(zq[k] - model["centroid"][k]))[:16]
    over = [(ref["mfw"][k], rel_q[k], rel_a[k]) for k in dev if zq[k] > model["centroid"][k]][:6]
    under = [(ref["mfw"][k], rel_q[k], rel_a[k]) for k in dev if zq[k] < model["centroid"][k]][:6]
    # sequenze di 8 parole in comune con il corpus
    grams = {tuple(ws[i:i + 8]) for i in range(len(ws) - 7)}
    copied = []
    for w in ref["a_ws"]:
        for i in range(len(w) - 7):
            if tuple(w[i:i + 8]) in grams:
                copied.append(" ".join(w[i:i + 8]))
    return {"profile": p, "calibration": cal, "features": f, "delta": d, "gi": g, "verdict": verdict,
            "bad_windows": bad, "lint": hits, "n_words": f["n_words"], "has_windows": bool(windows(ws)),
            "over": over, "under": under, "copied": sorted(set(copied))}


def compare(fmt, draft_path, verbose=False):
    text, _ = parse(draft_path)
    r = assess(fmt, text)
    p, cal, f = r["profile"], r["calibration"], r["features"]
    print(f"Bozza: {r['n_words']} parole.")
    if r["n_words"] < MIN_WORDS_RELIABLE:
        print(f"Avviso: sotto {MIN_WORDS_RELIABLE} parole Delta e impostori sono rumorosi; vale soprattutto il controllo dei tic.")
    if r["verdict"] != "NON CALIBRATO":
        label = {"COERENTE": "COERENTE con la voce"}.get(r["verdict"], r["verdict"])
        print(f"Esito: {label}")
        dl, gl = cal["delta"], cal["gi"]
        print(f"  Cosine Delta {r['delta']:.3f}: coerente fino a {dl['threshold']:.3f}, fuori da {dl['out_threshold']:.3f} (tuoi {dl['genuine_mean']:.3f}, controlli {dl['control_mean']:.3f})")
        print(f"  Impostori {r['gi']:.2f}: coerente da {gl['threshold']:.2f}, fuori sotto {gl['out_threshold']:.2f} (1 = sempre più vicina a te che ai controlli)")
    else:
        print(f"Esito: NON CALIBRATO. Delta {r['delta']:.3f}. Servono `calibrate` e i controlli negativi per un giudizio.")

    flagged = []
    for k in SCALARS:
        m, sd = p["scalars"][k]["mean"], p["scalars"][k]["sd"]
        sd = sd or max(abs(m) * 0.15, 1e-6)
        z = (f[k] - m) / sd
        if abs(z) > 2 or verbose:
            flagged.append(f"  {k:22s} bozza {f[k]:7.2f}  profilo {m:7.2f}  z {z:+.1f}" + ("  <-- fuori" if abs(z) > 2 else ""))
    print("Misure di superficie " + ("(tutte)" if verbose else "fuori profilo (|z| > 2)") + (":" if flagged else ": nessuna"))
    print("\n".join(flagged))

    pl = []
    for k, ref_v in p["punct_per_1000"].items():
        val = f["punct_per_1000"][k]
        if (ref_v > 0.5 or val > 0.5) and (abs(val - ref_v) > max(ref_v * 0.6, 2) or verbose):
            pl.append(f"  {k:20s} {val:6.1f} vs {ref_v:6.1f}")
    if pl:
        print("Punteggiatura per 1000 parole (bozza vs profilo), scostamenti:")
        print("\n".join(pl))

    if r["bad_windows"]:
        thr = cal["window_delta_p95_genuine"]
        print(f"Passaggi da rivedere (finestre di {WINDOW} parole con Delta oltre {thr:.3f}):")
        for start, dw, snip in r["bad_windows"][:5]:
            print(f"  dalla parola {start}: Delta {dw:.3f}, «{snip}…»")
    elif cal and r["has_windows"]:
        print(f"Nessun passaggio di {WINDOW} parole oltre la soglia.")

    if r["verdict"] != "COERENTE":
        fmtw = lambda rows: ", ".join(f"«{w}» {q:.1f} contro {a:.1f}" for w, q, a in rows)
        if r["over"]:
            print("Parole di funzione usate più di te (bozza contro tuo, per 1000 parole): " + fmtw(r["over"]))
        if r["under"]:
            print("Parole di funzione usate meno di te: " + fmtw(r["under"]))
    if r["copied"]:
        print(f"Sequenze di 8 parole copiate dal corpus ({len(r['copied'])}): " + "; ".join(f"«{c}»" for c in r["copied"][:3]) + ". Riscrivile con parole nuove.")
    print_lint(r["lint"], r["n_words"])
    print("Nota: l'esito è una sentinella contro la prosa generica, non un obiettivo da ottimizzare. "
          "Correggi i passaggi segnalati riscrivendoli, non ritoccando i numeri.")


SUFF = {"docs_ok": 8, "words_ok": 10000, "docs_min": 5, "words_min": 3000,
        "ci_mean": 0.10, "ci_sd": 0.20, "saturation": 0.02, "auc_ok": 0.90, "auc_min": 0.80, "coherent_ok": 0.90}
# Bloccanti: misure di frase e di parola. Informative: dipendono dall'impaginazione (paragrafi) o da pochi eventi (frasi brevi).
CI_KEYS = [("sent_len_mean", "ci_mean", True), ("word_len_mean", "ci_mean", True), ("sent_len_sd", "ci_sd", True),
           ("para_len_words_mean", "ci_mean", False), ("short_share", "ci_sd", False)]


def check(fmt):
    """Verifica che il corpus sia abbastanza esteso e stabile. Salva l'esito nel profilo."""
    pf = PROFILE / f"{fmt}.json"
    if not pf.exists():
        sys.exit(f"Manca {pf}. Esegui prima: analyze {fmt}")
    p = json.loads(pf.read_text(encoding="utf-8"))
    ref = reference(fmt, p["lang"])
    docs = ref["docs"]
    n = len(docs)
    lens = [len(w) for w in ref["a_ws"]]
    total = sum(lens)
    med = statistics.median(lens)
    crit = []  # (nome, ok, dettaglio)

    crit.append(("quantità", n >= SUFF["docs_ok"] and total >= SUFF["words_ok"],
                 f"{n} testi e {total} parole; per «sufficiente» servono almeno {SUFF['docs_ok']} testi e {SUFF['words_ok']} parole"))

    # 1. intervallo di confidenza bootstrap sulle misure di superficie
    feats = [doc_features(t, p["lang"]) for _, t, _ in docs]
    rng = random.Random(0)
    ci_ok, ci_lines = True, []
    for key, kind, blocking in CI_KEYS:
        vals = [f[key] for f in feats]
        boots = sorted(statistics.mean(rng.choices(vals, k=n)) for _ in range(1000))
        lo, hi = boots[25], boots[974]
        m = statistics.mean(vals)
        half = (hi - lo) / 2 / abs(m) if m else 0.0
        ok = half <= SUFF[kind]
        if blocking:
            ci_ok &= ok
        ci_lines.append(f"{key} ±{half * 100:.0f}% (limite {SUFF[kind] * 100:.0f}%)"
                        + ("" if ok else " NO" if blocking else " instabile, non vincolante"))
    crit.append(("stabilità delle misure (bootstrap 95%)", ci_ok, "; ".join(ci_lines)))

    # 2. curva di apprendimento: il centroide smette di cambiare aggiungendo testi?
    full = build_model(ref["a_rel"], ref["c_rel"])
    zs = full["auth_z"]
    centroid_of = lambda ids: [statistics.mean(zs[i][d] for i in ids) for d in range(full["dim"])]
    curve, ks = [], list(range(4, n - 1, 2))
    if len(ks) >= 2:
        for k in ks:
            meds = []
            for _ in range(40):
                idx = rng.sample(range(n), k)
                c = centroid_of(idx)
                meds.append(statistics.median(1 - cosine(zs[i], c) for i in range(n) if i not in idx))
            curve.append((k, statistics.mean(meds)))
        ref_pt = curve[-3] if len(curve) >= 3 else curve[0]
        gain = ref_pt[1] - curve[-1][1]
        sat = gain <= SUFF["saturation"]
        detail = ("Delta mediano dei testi esclusi, con k testi nel profilo: " + ", ".join(f"{k}: {v:.3f}" for k, v in curve)
                  + f"; guadagno tra k={ref_pt[0]} e k={curve[-1][0]}: {gain:+.3f} (limite {SUFF['saturation']})")
    else:
        sat, detail = False, f"servono almeno 6 testi per tracciare la curva (ora {n})"
    crit.append(("saturazione (curva di apprendimento)", sat, detail))

    # 3. calibrazione
    cal = p.get("calibration")
    if cal:
        ok = (cal["delta"]["auc"] >= SUFF["auc_ok"] and cal["gi"]["auc"] >= SUFF["auc_ok"]
              and cal.get("genuine_coherent_rate", 0) >= SUFF["coherent_ok"] and cal["n_control"] >= 8)
        crit.append(("calibrazione", ok,
                     f"AUC Delta {cal['delta']['auc']:.2f}, impostori {cal['gi']['auc']:.2f}; "
                     f"tuoi testi giudicati coerenti {cal.get('genuine_coherent_rate', 0) * 100:.0f}%; {cal['n_control']} controlli (servono almeno 8)"))
    else:
        crit.append(("calibrazione", False, "assente: esegui `calibrate`"))

    # 4. eterogeneità (non blocca, limita la portata)
    metas = [parse(pth)[1] for pth, _, _ in docs]
    dates = sorted(m.get("date", "")[:7] for m in metas if m.get("date"))
    sources = {re.sub(r"^https?://([^/]+).*", r"\1", m.get("source", "")) for m in metas if m.get("source")}
    span = f"{dates[0]}…{dates[-1]}" if dates else "date assenti"
    notes = [f"periodo {span}", f"{len(sources)} fonte/i: {', '.join(sorted(sources)) or 'non indicate'}"]
    unverified = sum(1 for m in metas if m.get("ai_assisted", "").lower() not in {"false"})
    if unverified:
        notes.append(f"{unverified} testi senza `ai_assisted: false` confermato")

    hard_min = n >= SUFF["docs_min"] and total >= SUFF["words_min"]
    all_ok = all(ok for _, ok, _ in crit)
    cal_weak = cal and (cal["delta"]["auc"] < SUFF["auc_min"] or cal["gi"]["auc"] < SUFF["auc_min"])
    verdict = "SUFFICIENTE" if all_ok else "INDICATIVO" if hard_min and not cal_weak else "INSUFFICIENTE"

    print(f"Sufficienza del corpus '{fmt}': {verdict}")
    for name, ok, detail in crit:
        print(f"  {'OK   ' if ok else 'NO   '} {name}: {detail}")
    print("  Portata: " + "; ".join(notes))
    if not crit[0][1]:
        need_w = max(SUFF["words_ok"] - total, 0)
        need_d = max(SUFF["docs_ok"] - n, 0)
        print(f"  Mancano circa {need_w} parole e {need_d} testi (a {med:.0f} parole per testo: {max(math.ceil(need_w / med), need_d)} testi in più).")
    print("  Nota: «sufficiente» vuol dire che le misure sono stabili su questo corpus, non che lo stile sia certo. "
          "Vale per testi dello stesso genere e periodo. Per un campione di un solo saggio (circa 1000 parole) Eder (2015) "
          "trova che l'attribuzione d'autore affidabile richiede in genere campioni di 2500-5000 parole: il controllo misura "
          "la distanza dalla prosa generica, non un'attribuzione certa.")
    p["sufficiency"] = {"verdict": verdict, "criteria": {n_: ok for n_, ok, _ in crit}, "n_docs": n, "n_words": total}
    pf.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")


def contrast(fmt, top=14):
    """Che cosa distingue i tuoi testi dai controlli: parole del lessico chiuso e misure di superficie."""
    pf = PROFILE / f"{fmt}.json"
    p = json.loads(pf.read_text(encoding="utf-8"))
    ref = reference(fmt, p["lang"])
    if len(ref["controls"]) < 3:
        print("Servono almeno 3 controlli per il confronto.")
        return
    rows = []
    for k, w in enumerate(ref["mfw"]):
        a = [v[k] * 1000 for v in ref["a_rel"]]
        c = [v[k] * 1000 for v in ref["c_rel"]]
        sd = math.sqrt((statistics.pvariance(a) + statistics.pvariance(c)) / 2) or 1e-9
        rows.append(((statistics.mean(a) - statistics.mean(c)) / sd, w, statistics.mean(a), statistics.mean(c)))
    rows.sort()
    fmt_row = lambda r: f"{r[1]} ({r[2]:.1f} contro {r[3]:.1f})"
    print("Usi più dei controlli (per 1000 parole, tuoi contro controlli): " + ", ".join(fmt_row(r) for r in rows[::-1][:top]))
    print("Usi meno dei controlli: " + ", ".join(fmt_row(r) for r in rows[:top]))
    ff = [doc_features(t, p["lang"]) for _, t, _ in ref["controls"]]
    fa = [doc_features(t, p["lang"]) for _, t, _ in ref["docs"]]
    out = []
    for k in SCALARS:
        a, c = statistics.mean(f[k] for f in fa), statistics.mean(f[k] for f in ff)
        out.append((abs(a - c) / (abs(a) + abs(c) + 1e-9), f"{k} {a:.2f} contro {c:.2f}"))
    for k in ("virgola", "due_punti", "punto_interrogativo", "punto_esclamativo", "parentesi", "virgolette_basse", "virgolette_alte"):
        a = statistics.mean(f["punct_per_1000"][k] for f in fa)
        c = statistics.mean(f["punct_per_1000"][k] for f in ff)
        out.append((abs(a - c) / (abs(a) + abs(c) + 1e-9), f"{k} per 1000 parole {a:.1f} contro {c:.1f}"))
    out.sort(reverse=True)
    print("Misure che si distinguono di più (tuoi contro controlli): " + "; ".join(x[1] for x in out[:8]))


def lint_cmd(path):
    text, _ = parse(path)
    hits, _ = lint(text)
    print_lint(hits, len(words(text)), limit=40)


def status():
    print(f"Voce: {voice_meta(VOICE).get('name', VOICE.name)} ({VOICE})")
    for d in sorted(CORPUS.glob("*")) if CORPUS.is_dir() else []:
        if not d.is_dir():
            continue
        docs = load_corpus(d.name)
        nw = sum(len(words(t)) for _, t, _ in docs)
        ctrl = load_controls(d.name)
        pf = PROFILE / f"{d.name}.json"
        cal = "calibrato" if pf.exists() and "calibration" in json.loads(pf.read_text(encoding="utf-8")) else "non calibrato"
        suf = json.loads(pf.read_text(encoding="utf-8")).get("sufficiency", {}).get("verdict", "non verificata") if pf.exists() else "-"
        print(f"{d.name:8s} testi {len(docs):3d}  parole {nw:6d}  controlli {len(ctrl):3d}  "
              f"profilo {'sì, ' + cal if pf.exists() else 'no'}  sufficienza {suf}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--voice", help="cartella della voce su cui lavorare")
    sub = ap.add_subparsers(dest="cmd", required=True)
    vo = sub.add_parser("voices"); vo.add_argument("--user-root"); vo.add_argument("--project", default=".")
    vo.add_argument("--format"); vo.add_argument("--all", action="store_true"); vo.add_argument("--json", action="store_true")
    nv = sub.add_parser("new-voice"); nv.add_argument("--root", required=True); nv.add_argument("--name", required=True)
    nv.add_argument("--description")
    a = sub.add_parser("analyze"); a.add_argument("format"); a.add_argument("--lang")
    c = sub.add_parser("compare"); c.add_argument("format"); c.add_argument("draft"); c.add_argument("-v", "--verbose", action="store_true")
    k = sub.add_parser("calibrate"); k.add_argument("format")
    ck = sub.add_parser("check"); ck.add_argument("format")
    li = sub.add_parser("lint"); li.add_argument("draft")
    sh = sub.add_parser("show"); sh.add_argument("format")
    sub.add_parser("status")
    args = ap.parse_args()
    if args.cmd == "voices":
        return voices_cmd(args)
    if args.cmd == "new-voice":
        return new_voice_cmd(args)
    if args.cmd == "lint":
        if args.voice:
            set_voice(args.voice)
        return lint_cmd(args.draft)
    need_voice(args)
    if args.cmd == "analyze":
        analyze(args.format, args.lang)
    elif args.cmd == "compare":
        compare(args.format, args.draft, args.verbose)
    elif args.cmd == "calibrate":
        calibrate(args.format)
    elif args.cmd == "check":
        check(args.format)
    elif args.cmd == "lint":
        lint_cmd(args.draft)
    elif args.cmd == "show":
        show(args.format)
    else:
        status()


if __name__ == "__main__":
    main()
