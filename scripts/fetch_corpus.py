#!/usr/bin/env python3
"""Scarica pagine web pubbliche e le salva come testi markdown del corpus (solo libreria standard).

Uso (con --voice CARTELLA_VOCE obbligatorio, la voce si crea con `stylometry.py new-voice`):
  fetch_corpus.py --voice DIR <formato> <url> [<url> ...]          scarica le pagine indicate
  fetch_corpus.py --voice DIR <formato> --sitemap <url-sitemap>    scarica le pagine elencate in una sitemap
  fetch_corpus.py --voice DIR <formato> --feed <url-feed>          scarica le pagine elencate in un feed RSS o Atom

Opzioni: --limit N (default 30), --match REGEX (tiene solo gli URL che corrispondono), --lang it,
         --delay SECONDI (default 1.5), --dry-run (elenca senza scaricare).

Scrive <voce>/corpus/<formato>/AAAA-MM-GG_slug.md con frontmatter `ai_assisted: unverified`:
prima di `analyze` va confermato con l'autore che il testo è suo e non scritto o rifinito da un LLM.
Rispetta robots.txt e aspetta tra una richiesta e l'altra. Non aggira login o blocchi: social e siti
protetti (LinkedIn, X, Instagram) vanno forniti come file esportati o incollati dall'utente.
"""
import argparse
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

UA = "writing-skill-corpus-fetch/1.0 (raccolta di testi dell'autore per analisi stilometrica locale)"
SKIP_TAGS = {"script", "style", "nav", "header", "footer", "aside", "form", "noscript", "svg", "button", "iframe"}
BLOCK = {"p": "p", "h1": "h1", "h2": "h2", "h3": "h3", "h4": "h3", "li": "li", "blockquote": "q"}


def get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "it,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        enc = r.headers.get_content_charset() or "utf-8"
    return raw.decode(enc, errors="replace")


class Extractor(HTMLParser):
    """Raccoglie i blocchi di testo dentro <article> (o <main>, o tutto il corpo) ignorando navigazione e margini."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta, self.title_tag, self.h1 = {}, "", ""
        self.time_dt = None
        self.stack, self.skip = [], 0
        self.containers = {"article": [], "main": [], "body": []}
        self.cur_container = []
        self.open_blocks = []
        self.buf = None
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            k = a.get("property") or a.get("name")
            if k and a.get("content"):
                self.meta[k] = a["content"]
        if tag == "title":
            self.in_title = True
        if tag == "time" and a.get("datetime") and not self.time_dt:
            self.time_dt = a["datetime"]
        if tag in SKIP_TAGS:
            self.skip += 1
        self.stack.append(tag)
        if self.skip:
            return
        if tag in BLOCK:
            self.buf = {"kind": BLOCK[tag], "text": []}
        if tag == "br" and self.buf is not None:
            self.buf["text"].append(" ")

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag in BLOCK and self.buf is not None and not self.skip and BLOCK[tag] == self.buf["kind"]:
            text = re.sub(r"\s+", " ", "".join(self.buf["text"])).strip()
            if text:
                self.emit(self.buf["kind"], text)
            self.buf = None
        if tag in SKIP_TAGS and self.skip:
            self.skip -= 1
        while self.stack and self.stack.pop() != tag:
            pass

    def handle_data(self, data):
        if self.in_title:
            self.title_tag += data
        if self.skip or self.buf is None:
            return
        self.buf["text"].append(data)

    def emit(self, kind, text):
        if kind == "h1" and not self.h1:
            self.h1 = text
        for name in ("article", "main", "body"):
            if name in self.stack or name == "body":
                self.containers[name].append((kind, text))


def to_markdown(blocks):
    out = []
    for kind, text in blocks:
        if kind == "h1":
            continue
        if kind == "h2":
            out.append(f"## {text}")
        elif kind == "h3":
            out.append(f"### {text}")
        elif kind == "li":
            out.append(f"- {text}")
        elif kind == "q":
            out.append(f"> {text}")
        else:
            out.append(text)
    md = "\n\n".join(out)
    return re.sub(r"\n\n- ", "\n- ", md)


def find_date(url, ex):
    for k in ("article:published_time", "datePublished", "date", "og:updated_time"):
        if ex.meta.get(k):
            return ex.meta[k][:10]
    if ex.time_dt:
        return ex.time_dt[:10]
    m = re.search(r"/(20\d\d)/(\d\d)/(\d\d)/", url)
    return "-".join(m.groups()) if m else "0000-00-00"


def slugify(s):
    s = re.sub(r"[^\w\s-]", "", s.lower(), flags=re.U)
    return re.sub(r"[\s_-]+", "-", s).strip("-")[:60] or "testo"


def tail_warning(md):
    paras = [p for p in md.split("\n\n") if p.strip()]
    tail = paras[int(len(paras) * 0.7):]
    if len(tail) >= 4 and sum(1 for p in tail if p.lstrip().startswith("- ")) / len(tail) > 0.5:
        return "la coda sembra un elenco di link o rubriche: controlla e taglia ciò che non è il pezzo"
    for a, b in zip(tail, tail[1:]):
        if len(a.split()) <= 4 and not re.search(r"[.!?:»”\"]$", a.strip()) and b.lstrip().startswith("- "):
            return f"in coda compare forse una rubrica («{a.strip()}»): controlla e taglia ciò che non è il pezzo"
    return ""


def urls_from_sitemap(url, depth=0):
    root = ET.fromstring(get(url))
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    if root.tag.endswith("sitemapindex") and depth < 2:
        out = []
        for loc in root.findall(".//s:loc", ns):
            out += urls_from_sitemap(loc.text.strip(), depth + 1)
        return out
    return [loc.text.strip() for loc in root.findall(".//s:loc", ns)]


def urls_from_feed(url):
    root = ET.fromstring(get(url))
    out = [el.text.strip() for el in root.iter("link") if el.text and el.text.strip().startswith("http")]
    out += [el.get("href") for el in root.iter("{http://www.w3.org/2005/Atom}link")
            if el.get("href") and el.get("rel") in (None, "alternate")]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--voice", required=True, help="cartella della voce in cui salvare il corpus")
    ap.add_argument("format")
    ap.add_argument("urls", nargs="*")
    ap.add_argument("--sitemap")
    ap.add_argument("--feed")
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--match")
    ap.add_argument("--lang", default="it")
    ap.add_argument("--delay", type=float, default=1.5)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    urls = list(a.urls)
    try:
        if a.sitemap:
            urls += urls_from_sitemap(a.sitemap)
        if a.feed:
            urls += urls_from_feed(a.feed)
    except (urllib.error.URLError, ET.ParseError, OSError) as e:
        sys.exit(f"Impossibile leggere l'elenco degli URL: {e}")
    urls = list(dict.fromkeys(urls))
    if a.match:
        urls = [u for u in urls if re.search(a.match, u)]
    urls = urls[:a.limit]
    if not urls:
        sys.exit("Nessun URL da scaricare.")
    dest = Path(a.voice).expanduser().resolve() / "corpus" / a.format
    dest.mkdir(parents=True, exist_ok=True)
    known = {re.search(r"^source:\s*(\S+)", p.read_text(encoding="utf-8"), re.M).group(1)
             for p in dest.glob("*.md") if re.search(r"^source:\s*(\S+)", p.read_text(encoding="utf-8"), re.M)}
    if a.dry_run:
        print("\n".join(urls))
        return

    robots = {}
    saved = 0
    for i, url in enumerate(urls):
        if url in known:
            print(f"già presente: {url}")
            continue
        host = urllib.parse.urlsplit(url)
        base = f"{host.scheme}://{host.netloc}"
        if base not in robots:
            rp = urllib.robotparser.RobotFileParser(base + "/robots.txt")
            try:
                rp.read()
            except OSError:
                rp = None
            robots[base] = rp
        if robots[base] and not robots[base].can_fetch(UA, url):
            print(f"vietato da robots.txt: {url}")
            continue
        try:
            html = get(url)
        except (urllib.error.URLError, OSError) as e:
            print(f"errore su {url}: {e}")
            continue
        ex = Extractor()
        ex.feed(html)
        blocks = ex.containers["article"] or ex.containers["main"] or ex.containers["body"]
        md = to_markdown(blocks)
        words = len(re.findall(r"\w+", md))
        title = (ex.meta.get("og:title") or ex.h1 or ex.title_tag).strip()
        if words < 150:
            print(f"troppo corto ({words} parole), scartato: {url}")
            continue
        date = find_date(url, ex)
        name = f"{date}_{slugify(title or urllib.parse.urlsplit(url).path)}.md"
        front = f'---\nlang: {a.lang}\ndate: {date}\nsource: {url}\ntitle: "{title.replace(chr(34), chr(39))}"\nai_assisted: unverified\n---\n\n'
        (dest / name).write_text(front + md + "\n", encoding="utf-8")
        saved += 1
        warn = tail_warning(md)
        print(f"salvato {name} ({words} parole)" + (f"  ATTENZIONE: {warn}" if warn else ""))
        if i < len(urls) - 1:
            time.sleep(a.delay)
    print(f"{saved} testi salvati in {dest}. Conferma con l'autore `ai_assisted` e rimuovi ciò che non è il pezzo prima di `analyze`.")


if __name__ == "__main__":
    main()
