"""Auric writes TechVerse (TechVerse/MISSION.md), forever, in cycles. Runs as the hidden switch job "techverse".

One cycle:
  1. pick a subject from the queue (weighted toward sections with few pages; never the same twice in a row);
     a short queue is refilled with real subjects (each one must have a Wikipedia article) + searches that found nothing
  2. research: Wikipedia, Simple Wikipedia, Wikidata, OpenAlex, Stack Exchange - at least 3 independent sources
  3. write with Auric's 7B brain, in parts (plan, each section, extras), citing sources like [1]
  4. CHECK every sentence: its numbers/dates must be in the cited source, the brain must judge it supported by that
     source, copied wording is rewritten, links must open, nothing personal/insulting. Unsupported = left out.
  5. publish to Firestore (live at once, no deploy needed for content) + the public history log
  6. improve one existing page (a weak or old one); the new version replaces it only if it is better, the old one is
     kept in the history as a backup
Once a week: a review (empty sections, pages without diagram/quiz, missed searches -> subjects).

The graphics card is borrowed one cycle at a time (switch's GPU lock + enough free memory), then given back.
    python techverse_agent.py           forever (what the job runs)
    python techverse_agent.py once      one cycle, then stop
"""
import gc
import html
import json
import os
import random
import re
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import switch
from techverse_cloud import TechCloud

ROOT = Path(__file__).resolve().parent
STATE = Path(os.environ.get("AURIC_STATE_DIR") or ROOT / "data") / "techverse_state.json"
try:                                         # Windows' certificate store misses some intermediates (doi.org -> arXiv)
    import ssl
    import certifi
    urllib.request.install_opener(urllib.request.build_opener(urllib.request.HTTPSHandler(
        context=ssl.create_default_context(cafile=certifi.where()))))
except ImportError:
    pass
BIG = ROOT / "models" / "qwen2.5-7b-instruct"
UA = {"User-Agent": "TechVerse/1.0 (Auric, a personal AI writing an educational site; polite)"}
SECTIONS = {
    "ai": "AI & Machine Learning", "hardware": "Computers & Hardware", "programming": "Programming",
    "internet": "Internet & Networks", "security": "Cybersecurity", "space": "Space Tech", "robotics": "Robotics",
    "gadgets": "Phones & Gadgets", "energy": "Energy & Green Tech", "biotech": "Biotech & Health Tech",
    "gaming": "Gaming", "transport": "Cars & Transport", "history": "History of Tech", "future": "Future Tech"}
DEMOS = {"sorting": "sorting algorithms", "binary": "binary numbers, bits and bytes", "logic-gates": "logic gates, chips, CPUs",
         "caesar": "encryption, ciphers, passwords", "latency": "internet speed, latency, fibre, satellites",
         "pixels": "screens, pixels, colours, displays"}
REST_BETWEEN = int(float(os.environ.get("AURIC_REST_MIN", "20")) * 60)   # rest between cycles (PC: the card is free meanwhile)
BAD = re.compile(r"\b(idiot|stupid|moron|retard\w*|whore|slut|fuck\w*|shit\w*|bitch\w*|nigg\w*|fag\w*)\b|"
                 r"[\w.+-]+@[\w-]+\.\w+|\+?\d[\d \-]{8,}\d", re.I)
SYSTEM = ("You are Auric, writing TechVerse, a website that explains technology clearly. You write plain, friendly "
          "English: short sentences, one idea at a time, an example for each idea, simple first and deeper after. "
          "You only use facts found in the numbered sources you are given, and you cite them like [1] or [2]. You never "
          "invent facts, numbers, dates or quotes; if the sources don't say it, you leave it out. You use your own "
          "words and never copy sentences from the sources.")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(msg):
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


def state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(**kw):
    s = state()
    s.update(kw)
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(s, indent=1), encoding="utf-8")


class Live:
    """What Auric is doing right now -> meta/live, for the site's Live page (a cursor, typed text, kept/cut sentences).
    At most one write every 5 s (Firestore's free plan: 20,000 writes a day)."""
    def __init__(self):
        self.cloud = None
        self.s = {"step": "rest", "phase": "", "subject": "", "sources": [], "draft": {}, "checks": [], "focus": "",
                  "where": "GitHub's free cloud" if os.environ.get("AURIC_CLOUD") else "Saad's PC"}
        self.sent = 0

    def set(self, force=False, **kw):
        self.s.update(kw)
        if self.cloud and (force or time.time() - self.sent >= 5):
            try:
                self.cloud.put("meta", "live", {**self.s, "updated": now()})
                self.sent = time.time()
            except Exception:
                pass                                          # (the live view is a bonus: never stops the work)

    def check(self, sentence, kept, reason=""):
        self.s["checks"] = (self.s["checks"] + [{"s": CITE.sub("", sentence)[:220], "ok": kept, "why": reason}])[-8:]
        self.set()


LIVE = Live()


def slugify(title):
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:80] or "page"


# ================================================================ research
def get_json(url, timeout=12):
    """(retries politely: a site saying "too many requests" or a slow answer gets 2 more tries, with pauses)"""
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(5 * (attempt + 1) ** 2)
    if raw[:2] == b"\x1f\x8b":
        import gzip
        raw = gzip.decompress(raw)
    return json.loads(raw)


def wikipedia(title, host="en.wikipedia.org", chars=7000):
    """(canonical title, plain text, url, wikidata id) or None."""
    url = (f"https://{host}/w/api.php?action=query&format=json&formatversion=2&redirects=1&prop=extracts|info|pageprops"
           f"&explaintext=1&inprop=url&ppprop=wikibase_item|disambiguation&titles={urllib.parse.quote(title)}")
    try:
        p = get_json(url)["query"]["pages"][0]
    except Exception:
        return None
    if p.get("missing") or "disambiguation" in p.get("pageprops", {}):
        return None
    text = re.sub(r"\n==+ (See also|References|External links|Further reading|Notes|Bibliography) ==+.*", "",
                  p.get("extract", ""), flags=re.S)
    text = re.sub(r"\n{2,}", "\n", re.sub(r"==+ (.*?) ==+", r"\n\1:", text)).strip()
    if len(text) < 400:
        return None
    return p["title"], text[:chars], p.get("fullurl", f"https://{host}/wiki/{urllib.parse.quote(p['title'])}"), \
        p.get("pageprops", {}).get("wikibase_item")


def wiki_search(q, n=1):
    try:
        s = get_json("https://en.wikipedia.org/w/api.php?action=query&format=json&list=search&srlimit="
                     f"{n}&srsearch={urllib.parse.quote(q)}")
        return [h["title"] for h in s["query"]["search"]]
    except Exception:
        return []


WD_PROPS = {"P571": "began / was created", "P575": "was discovered or invented", "P577": "was first released",
            "P61": "discoverer or inventor", "P178": "developer", "P176": "manufacturer", "P170": "creator",
            "P138": "named after", "P279": "is a kind of", "P366": "is used for"}


def wikidata(qid):
    """Structured facts as sentences (dates, inventors...) -> (text, url) or None."""
    if not qid:
        return None
    try:
        e = get_json(f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json")["entities"][qid]
    except Exception:
        return None
    label = e.get("labels", {}).get("en", {}).get("value", qid)
    facts, ids = [], set()
    for p, words in WD_PROPS.items():
        for c in e.get("claims", {}).get(p, [])[:3]:
            v = c.get("mainsnak", {}).get("datavalue", {}).get("value")
            if isinstance(v, dict) and "time" in v:
                y = re.match(r"([+-]\d+)", v["time"])
                if y:
                    facts.append((p, words, str(int(y.group(1)))))
            elif isinstance(v, dict) and "id" in v:
                facts.append((p, words, v["id"]))
                ids.add(v["id"])
    if not facts:
        return None
    names = {}
    if ids:
        try:
            got = get_json("https://www.wikidata.org/w/api.php?action=wbgetentities&format=json&props=labels&languages=en&ids="
                           + "|".join(list(ids)[:40]))
            names = {k: v.get("labels", {}).get("en", {}).get("value", k) for k, v in got.get("entities", {}).items()}
        except Exception:
            pass
    lines = [f"{label} {w}: {names.get(v, v)}." for p, w, v in facts if not re.fullmatch(r"Q\d+", names.get(v, v))]
    return ("\n".join(lines), f"https://www.wikidata.org/wiki/{qid}") if lines else None


def openalex(subject, n=2):
    """Abstracts of well-cited research works about the subject -> [(title, text, url)]."""
    try:
        s = get_json("https://api.openalex.org/works?per_page=5&sort=cited_by_count:desc&filter=has_abstract:true"
                     f",title.search:{urllib.parse.quote(subject)}")
    except Exception:
        return []
    out = []
    for w in s.get("results", []):
        inv = w.get("abstract_inverted_index") or {}
        pos = sorted((i, word) for word, idx in inv.items() for i in idx)
        text = " ".join(word for _, word in pos)
        if len(text) > 300 and w.get("title"):
            out.append((w["title"], text[:1800], w.get("doi") or w.get("id")))
        if len(out) >= n:
            break
    return out


def stackexchange(subject, site="stackoverflow", n=2):
    try:
        s = get_json("https://api.stackexchange.com/2.3/search/excerpts?order=desc&sort=relevance&pagesize=8"
                     f"&site={site}&q={urllib.parse.quote(subject)}")
    except Exception:
        return []
    out = []
    for it in s.get("items", []):
        if it.get("item_type") != "answer" or it.get("score", 0) < 5:
            continue
        text = html.unescape(re.sub(r"<[^>]+>", "", it.get("body") or it.get("excerpt", ""))).strip()
        if len(text) > 200:
            out.append((html.unescape(it.get("title", "")), text[:1500],
                        f"https://{site}.com/a/{it['answer_id']}" if site == "stackoverflow" else f"https://{site}.stackexchange.com/a/{it['answer_id']}"))
        if len(out) >= n:
            break
    return out


def research(subject):
    """[{title, site, url, text}] - the numbered sources of the page."""
    class Found(list):                                       # every source found appears on the Live page at once
        def append(self, s):
            super().append(s)
            LIVE.set(sources=[{"title": x["title"], "site": x["site"]} for x in self])
    sources = Found()
    LIVE.set(step="research", phase=f"reading about {subject}", sources=[], draft={}, checks=[], focus="", force=True)
    w = wikipedia(subject)
    if not w:
        return sources
    title, text, url, qid = w
    sources.append({"title": f"{title} (Wikipedia)", "site": "Wikipedia", "url": url, "text": text})
    sw = wikipedia(title, "simple.wikipedia.org", chars=2500)
    if sw:
        sources.append({"title": f"{sw[0]} (Simple English Wikipedia)", "site": "Simple English Wikipedia", "url": sw[2], "text": sw[1]})
    wd = wikidata(qid)
    if wd:
        sources.append({"title": f"{title} (Wikidata facts)", "site": "Wikidata", "url": wd[1], "text": wd[0]})
    for t, x, u in openalex(title):
        sources.append({"title": t, "site": "OpenAlex (research)", "url": u, "text": x})
    if re.search(r"program|code|software|algorithm|data|network|protocol|web|security|encrypt|computer|linux|python|java",
                 f"{subject} {text[:600]}", re.I):
        for t, x, u in stackexchange(title):
            sources.append({"title": t, "site": "Stack Overflow", "url": u, "text": x})
    return sources


def link_ok(url):
    """The link opens. (A site that only refuses robots - 401/403/429, like DOI -> arXiv - still opens in a browser.)"""
    try:
        req = urllib.request.Request(url, headers=UA, method="GET")
        with urllib.request.urlopen(req, timeout=12) as r:
            return r.status < 400
    except urllib.error.HTTPError as e:
        return e.code in (401, 403, 429)
    except Exception:
        return False


# ================================================================ the brain
CODER = ROOT / "models" / "qwen2.5-coder-7b-instruct"     # Auric's coding brain (design work), when downloaded


def coder_available():
    return bool(os.environ.get("AURIC_LLAMA_CODER")) or (CODER / "config.json").exists()


class Brain:
    """The writer (7B) or the coder (Coder 7B): on the PC with transformers on the graphics card; on GitHub's free
    computers (AURIC_LLAMA_WRITER / AURIC_LLAMA_CODER) the same brains in GGUF, run by llama.cpp's server."""
    def __init__(self, path=BIG):
        url = os.environ.get("AURIC_LLAMA_CODER" if path == CODER else "AURIC_LLAMA_WRITER")
        if url:
            from llama_brain import LlamaBrain
            self.b = LlamaBrain(url, label=f"{'Coder 7B' if path == CODER else '7B'} (GitHub cloud, processor)")
            return
        import auricv2_local
        self.b = auricv2_local.AuricV2(path=path, mode="gpu4", compact_head=True)

    def close(self):
        del self.b
        gc.collect()
        try:
            import torch
            torch.cuda.empty_cache()
        except Exception:
            pass

    def json(self, user, max_new=900):
        """Asks for JSON; one retry if it can't be read."""
        for attempt in range(2):
            raw = self.b.ask(SYSTEM, user + ("" if not attempt else "\n\nReply with ONE valid JSON object only."), max_new=max_new)
            m = re.search(r"\{.*\}", raw, re.S)
            if m:
                for text in (m.group(0), re.sub(r",\s*([}\]])", r"\1", m.group(0))):
                    try:
                        return json.loads(text)
                    except ValueError:
                        pass
        return None

    def yes(self, question, system="You are a strict fact checker. Answer only yes or no.", sure=0.75):
        """yes only when the brain is at least `sure` confident (not just a little more yes than no)."""
        import math
        s = self.b.scores(self.b.prompt(system, question), ["yes", "no"])
        return math.exp(s["yes"]) / (math.exp(s["yes"]) + math.exp(s["no"])) >= sure

    def pick(self, question, options):
        return self.b.choose(self.b.prompt("Answer with one of the given words only.", question), options)

    def rewrite(self, sentence):
        raw = self.b.ask("You rewrite sentences in simpler, different words, keeping exactly the same meaning and any "
                         "[n] citation. Reply with the new sentence only.", sentence, max_new=120)
        return raw.strip().strip('"').split("\n")[0]


def sources_block(sources):
    return "\n\n".join(f"[{i + 1}] {s['title']} ({s['site']})\n{s['text']}" for i, s in enumerate(sources))


def write_page(brain, subject, section, sources):
    """The draft (not checked yet)."""
    src = sources_block(sources)
    head = f"Sources:\n{src}\n\nSubject: {subject} (section: {SECTIONS.get(section, section)})\n\n"
    plan = brain.json(head + 'Plan the page. Reply with JSON: {"title": "the page title", "summary": "2 simple '
                      'sentences saying what it is and why it matters, with citations", "sections": ["3 or 4 headings, '
                      'from simple (what it is) to deeper (how it works in detail, history, limits)"]}', 400)
    if not plan or not plan.get("sections"):
        return None
    page = {"title": str(plan.get("title") or subject)[:90], "summary": str(plan.get("summary", "")), "body": []}
    draft = {"title": page["title"], "summary": CITE.sub("", page["summary"]), "body": [], "extras": []}
    LIVE.set(step="write", phase="writing the page", draft=draft, focus="summary", force=True)
    for h in [str(x) for x in plan["sections"][:4]]:
        LIVE.set(focus=h, phase=f"writing “{h}”")
        part = brain.json(head + f'Write the part "{h}" of the page "{page["title"]}": 2 or 3 short paragraphs, '
                          'simple first, with a concrete example TAKEN FROM THE SOURCES (never made up), citing the '
                          'sources like [1]. Reply with JSON: '
                          '{"paragraphs": ["...", "..."]}', 900)
        if part and part.get("paragraphs"):
            page["body"].append({"h": h, "p": [str(p) for p in part["paragraphs"][:3]]})
            draft["body"].append({"h": h, "p": [CITE.sub("", str(p)) for p in part["paragraphs"][:3]]})
            LIVE.set(draft=draft, force=True)
    LIVE.set(focus="extras", phase="drawing the diagram, the steps and the key dates")
    extras = brain.json(head + 'Now the extra parts of the page "' + page["title"] + '". Reply with JSON: {'
                        '"how": ["4 to 6 short steps explaining how it works, with citations"], '
                        '"dates": [{"year": "1947", "text": "what happened, with a citation"}], '
                        '"examples": ["2 or 3 real examples, with citations"], '
                        '"diagram": {"kind": "flow or cycle or layers or compare", "title": "short title", '
                        '"items": ["3 to 6 short labels (for compare: two objects {\\"title\\": ..., \\"points\\": [...]})"]}, '
                        '"disagree": ["only if two sources really disagree: say it, citing both; else empty"]} '
                        'Use only dates that are in the sources.', 900)
    page.update({k: (extras or {}).get(k) or [] for k in ("how", "dates", "examples", "disagree")})
    page["diagram"] = (extras or {}).get("diagram") or None
    draft["extras"] = [x for x, ok in (("How it works", page["how"]), ("Key dates", page["dates"]),
                                       ("Diagram", page["diagram"]), ("Examples", page["examples"])) if ok]
    LIVE.set(draft=draft, focus="learn", phase="writing the glossary and the quiz", force=True)
    learn = brain.json(head + 'Now the learning parts of the page "' + page["title"] + '". Reply with JSON: {'
                       '"glossary": [{"term": "a hard word used on the page", "def": "a simple definition"}] (4 to 8), '
                       '"quiz": [{"q": "a question", "options": ["4 short options"], "answer": 0, "why": "why it is '
                       'right, with a citation"}] (3 questions; answer = index of the right option)}', 900)
    page["glossary"] = [g for g in (learn or {}).get("glossary") or [] if isinstance(g, dict) and g.get("term") and g.get("def")][:8]
    page["quiz"] = [q for q in (learn or {}).get("quiz") or [] if isinstance(q, dict) and isinstance(q.get("options"), list)
                    and len(q["options"]) >= 2 and isinstance(q.get("answer"), int) and 0 <= q["answer"] < len(q["options"])][:4]
    topic = f"{page['title']} {subject}"
    fits = [k for k, words in DEMOS.items() if any(w in topic.lower() for w in re.findall(r"[a-z]+", words) if len(w) > 4)]
    page["demo"] = fits[0] if fits else ""
    return page


# ================================================================ checking
SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"“(])")
CITE = re.compile(r"\s*\[(\d+)\]")                    # (with the space before it: "making [1]." -> "making.")


def numbers(s):
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", CITE.sub("", s)) if len(n.replace(",", "")) > 0}


def window(text, sentence, size=1600):
    """The part of a source most about the sentence."""
    if len(text) <= size:
        return text
    want = set(re.findall(r"[a-z]{4,}", sentence.lower()))
    best, best_i = -1, 0
    for i in range(0, len(text) - size + 1, 300):
        n = len(want & set(re.findall(r"[a-z]{4,}", text[i:i + size].lower())))
        if n > best:
            best, best_i = n, i
    return text[best_i:best_i + size]


COMMON = set(("this that these those with from into about such also more most many much very some other than then "
              "their there they them have has had been being were will would could should which while where when what "
              "make makes made used uses using use like example instance including include includes important often "
              "different various several each every allow allows help helps based work works working way ways called "
              "known able need needs part parts form forms first second new kind type types thing things people").split())


def grounded(sentence, source_text, need=0.6):
    """The sentence's specific words (not common ones) are really in the source: an invented example ("a black cat on
    a dark road") has words no source contains. -> (ok, share)"""
    stem = lambda w: w[:6]
    words = {stem(w) for w in re.findall(r"[a-z]{4,}", CITE.sub("", sentence).lower()) if w not in COMMON}
    if not words:
        return True, 1.0
    have = {stem(w) for w in re.findall(r"[a-z]{4,}", source_text.lower())}
    share = len(words & have) / len(words)
    return share >= need, share


def copied(sentence, sources, n=9):
    words = re.findall(r"\w+", CITE.sub("", sentence).lower())
    grams = {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}
    if not grams:
        return False
    return any(g in " ".join(re.findall(r"\w+", s["text"].lower())) for s in sources for g in grams)


class Checker:
    def __init__(self, brain, sources):
        self.brain, self.sources = brain, sources
        self.claims = self.removed = 0

    def sentence(self, s):
        """The sentence as published (maybe rewritten, citation added), or None if no source supports it."""
        s = s.strip()
        if not s:
            return None
        if BAD.search(s):
            self.removed += 1
            LIVE.check(s, False, "personal or rude")
            return None
        cites = [int(c) for c in CITE.findall(s) if 0 < int(c) <= len(self.sources)]
        if not cites:                                    # find the source it comes from
            want = set(re.findall(r"[a-z]{4,}", s.lower()))
            scores = [len(want & set(re.findall(r"[a-z]{4,}", x["text"].lower()))) for x in self.sources]
            cites = [scores.index(max(scores)) + 1] if scores and max(scores) else []
            if cites:
                s = re.sub(r"([.!?])?$", lambda m: f" [{cites[0]}]{m.group(1) or '.'}", s, count=1)
        self.claims += 1
        texts = " ".join(self.sources[c - 1]["text"] for c in cites)
        plain = texts.replace(",", "")
        if not cites or any(n not in plain for n in numbers(s)):         # a number no cited source has
            self.removed += 1
            LIVE.check(s, False, "a number or date no source gives" if cites else "no source talks about it")
            return None
        ok, share = grounded(s, texts)
        if not ok:                                          # details no cited source contains (an invented example)
            self.removed += 1
            LIVE.check(s, False, f"details not in the source (only {share:.0%} of its key words are)")
            return None
        src = "\n...\n".join(window(self.sources[c - 1]["text"], s) for c in cites[:2])
        if not self.brain.yes(f"Source:\n{src}\n\nSentence: {CITE.sub('', s)}\n\nDoes the source state every fact in this "
                              "sentence? Answer no if the sentence adds any specific detail, example, name, number or "
                              "claim that the source doesn't contain."):
            self.removed += 1
            LIVE.check(s, False, "the source doesn't support it")
            return None
        if copied(s, self.sources):
            new = self.brain.rewrite(s)
            if new and not copied(new, self.sources) and numbers(new) <= numbers(s) and CITE.search(new):
                s = new
            else:
                self.removed += 1
                LIVE.check(s, False, "too close to the source's wording")
                return None
        LIVE.check(s, True, f"source [{cites[0]}]")
        return s

    def text(self, t):
        kept = [x for x in (self.sentence(s) for s in SENT.split(str(t))) if x]
        return " ".join(kept)


def check_page(brain, page, sources):
    """Every claim checked; what no source supports is left out. -> (page, report) or (None, why)."""
    c = Checker(brain, sources)
    LIVE.set(step="check", phase="checking every sentence against the sources", focus="", checks=[], force=True)
    page["summary"] = c.text(page["summary"])
    body = []
    for sec in page["body"]:
        ps = [p for p in (c.text(p) for p in sec["p"]) if len(p) > 40]
        if ps:
            body.append({"h": sec["h"], "p": ps})
    page["body"] = body
    page["how"] = [x for x in (c.text(s) for s in page["how"] if isinstance(s, str)) if x][:6]
    page["examples"] = [x for x in (c.text(s) for s in page["examples"] if isinstance(s, str)) if x][:4]
    page["disagree"] = [x for x in (c.text(s) for s in page["disagree"] if isinstance(s, str)) if x][:2]
    dates = []
    for d in page["dates"]:
        if isinstance(d, dict) and re.fullmatch(r"-?\d{1,4}s?", str(d.get("year", "")).strip()):
            t = c.text(f"In {d['year']}, {d.get('text', '')}" if str(d["year"]) not in str(d.get("text", "")) else d.get("text", ""))
            if t:
                dates.append({"year": str(d["year"]), "text": t})
    page["dates"] = sorted(dates, key=lambda d: int(re.sub(r"\D", "", d["year"]) or 0))[:8]
    whole = " ".join(s["text"] for s in sources)
    page["glossary"] = [g for g in page["glossary"] if not BAD.search(g["def"]) and
                        g["term"].lower() in (" ".join(p for s in page["body"] for p in s["p"]) + page["summary"]).lower()]
    quiz = []
    for q in page["quiz"]:
        right = q["options"][q["answer"]]
        c.claims += 1
        if numbers(right) <= set(whole.replace(",", "").split()) | numbers(whole) and brain.yes(
                f"Source:\n{window(whole, q['q'] + ' ' + right, 2400)}\n\nQuestion: {q['q']}\nAnswer: {right}\n\n"
                "Is this answer correct according to the source, and the only correct option among: "
                f"{', '.join(map(str, q['options']))}?"):
            q["why"] = CITE.sub("", str(q.get("why", ""))).strip()
            quiz.append(q)
        else:
            c.removed += 1
    page["quiz"] = quiz[:3]
    d = page.get("diagram")
    if isinstance(d, dict) and d.get("kind") != "compare" and isinstance(d.get("items"), list):   # labels, not objects
        d["items"] = [x if isinstance(x, str) else str((x or {}).get("title") or "") for x in d["items"]]
        d["items"] = [x[:60] for x in d["items"] if x.strip()]
    if isinstance(d, dict) and d.get("kind") == "compare" and not all(isinstance(x, dict) and x.get("title") for x in d.get("items") or []):
        d = None
    if not (isinstance(d, dict) and d.get("kind") in ("flow", "cycle", "layers", "compare") and isinstance(d.get("items"), list)
            and 2 <= len(d["items"]) <= 8):
        page["diagram"] = None
    if not page["summary"] or sum(len(s["p"]) for s in page["body"]) < 3:
        return None, f"too little survived the fact check ({c.removed} of {c.claims} claims had no clear source)"
    return page, {"claims": c.claims, "removed": c.removed}


# ================================================================ the cycle
class Writer:
    def __init__(self):
        self.cloud = TechCloud()
        self.brain = None

    def history(self, kind, subject, change, why="", sources=(), backup=None):
        h = {"time": now(), "kind": kind, "subject": subject, "change": change, "why": why, "sources": list(sources)}
        if backup:
            h["backup"] = backup
        self.cloud.put("history", f"{h['time'].replace(':', '-')}-{slugify(subject)[:40]}", h)
        log(f"history: {kind} | {subject} | {change}")

    def index(self):
        return self.cloud.get("meta", "index") or {"items": []}

    # ---- subjects
    def refill(self, items):
        queue = self.cloud.list("queue")
        have = {i["slug"] for i in items} | set(queue)
        added = 0
        for mid, m in self.cloud.list("misses").items():               # searches that found nothing
            hit = wiki_search(m.get("q", ""))
            if hit and slugify(hit[0]) not in have and wikipedia(hit[0]):
                sec = self.section_of(hit[0])
                self.cloud.put("queue", slugify(hit[0]), {"subject": hit[0], "section": sec, "reason": "a visitor searched for it",
                                                         "added": now(), "weight": 3})
                have.add(slugify(hit[0]))
                added += 1
            self.cloud.delete("misses", mid)
        counts = {s: sum(1 for i in items if i["section"] == s) + sum(1 for q in queue.values() if q.get("section") == s) for s in SECTIONS}
        for sec in sorted(SECTIONS, key=lambda s: counts[s])[:3]:          # the thinnest sections first
            ideas = self.brain.json(f'List 25 specific, well-known technology subjects for the section "{SECTIONS[sec]}" '
                                    'of a website that teaches technology. Each must be the exact title of an English '
                                    'Wikipedia article (like "Transistor", "Transmission Control Protocol"). Reply with '
                                    'JSON: {"subjects": ["..."]}', 500) or {}
            for idea in [str(x) for x in ideas.get("subjects", [])][:25]:
                w = wikipedia(idea, chars=3000)
                if not w or len(w[1]) < 2000 or slugify(w[0]) in have:
                    continue                                                # (no invented subjects: a real article)
                self.cloud.put("queue", slugify(w[0]), {"subject": w[0], "section": sec, "reason": f"{SECTIONS[sec]} has few pages",
                                                        "added": now(), "weight": 1})
                have.add(slugify(w[0]))
                added += 1
                if added >= 20:
                    break
            if added >= 20:
                break
        if added:
            self.history("subjects", f"{added} new subjects", f"added {added} subjects to the queue", "the queue was short")

    def section_of(self, subject):
        ids = list(SECTIONS)
        q = (f'Which section of a technology website does "{subject}" belong to? Sections: '
             + "; ".join(f"{k} = {v}" for k, v in SECTIONS.items()) + ". Answer with the section's short word.")
        return self.brain.pick(q, ids)

    def pick(self, items):
        queue = self.cloud.list("queue")
        last = state().get("last_subject")
        counts = {s: sum(1 for i in items if i["section"] == s) for s in SECTIONS}
        cands = [(k, q) for k, q in queue.items() if q.get("subject") != last and q.get("tries", 0) < 3]
        if not cands:
            return None, None
        weights = [(q.get("weight", 1) or 1) / (1 + counts.get(q.get("section"), 0)) for _, q in cands]
        return random.choices(cands, weights=weights, k=1)[0]

    # ---- one page
    def make(self, subject, section):
        sources = research(subject)
        independent = {s["site"] for s in sources}
        if len(sources) < 3 or len(independent) < 3:
            return None, f"only {len(independent)} independent source(s) found (3 needed)"
        sources = [s for s in sources if link_ok(s["url"])]
        if len(sources) < 3:
            return None, "the source links didn't all open"
        draft = write_page(self.brain, subject, section, sources)
        if not draft:
            return None, "the brain couldn't plan the page"
        page, report = check_page(self.brain, draft, sources)
        if not page:
            return None, report
        page.update({"slug": slugify(page["title"]), "section": section, "subject": subject, "updated": now(),
                     "sources": [{"title": s["title"], "url": s["url"], "site": s["site"]} for s in sources],
                     "checked": report, "status": "ok" if report["removed"] <= report["claims"] * 0.35 else "weak"})
        return page, report

    def publish(self, page, items, kind="publish", why="", backup=None, reason=""):
        related = [i["slug"] for i in items if i["section"] == page["section"] and i["slug"] != page["slug"]][:3]
        page["related"] = related
        LIVE.set(step="publish", phase=f"publishing “{page['title']}”", slug=page["slug"], force=True)
        old = next((i for i in items if i["slug"] == page["slug"]), None)
        page["version"] = (old or {}).get("version", 0) + 1
        self.cloud.put("articles", page["slug"], page)
        entry = {"slug": page["slug"], "title": page["title"], "section": page["section"], "updated": page["updated"],
                 "summary": CITE.sub("", page["summary"]).replace("  ", " ")[:260], "status": page["status"],
                 "version": page["version"], "dates": [{"year": d["year"], "text": CITE.sub("", d["text"])[:160]} for d in page["dates"][:4]],
                 "terms": [g["term"] for g in page["glossary"]][:8], "quiz": len(page["quiz"]),
                 "has": {"diagram": bool(page.get("diagram")), "demo": bool(page.get("demo")), "quiz": bool(page["quiz"])}}
        items = [i for i in items if i["slug"] != page["slug"]] + [entry]
        self.cloud.put("meta", "index", {"items": items, "updated": now()})
        c = page["checked"]
        self.history(kind, page["title"], (reason or ("new page" if kind == "publish" else "page rewritten")) +
                     f": {c['claims']} facts checked against {len(page['sources'])} sources, {c['removed']} unsure ones left out",
                     why, [s["url"] for s in page["sources"]], backup)
        LIVE.set(step="done", phase=f"published “{page['title']}”", slug=page["slug"], force=True)
        return items

    def improve(self, items, skip):
        """One existing page made better: a weak, incomplete or old page is researched and written again."""
        def need(i):
            age = (time.time() - datetime.fromisoformat(i["updated"]).timestamp()) / 86400
            missing = sum(not v for v in (i.get("has") or {}).values())
            return (3 if i.get("status") == "weak" else 0) + missing + min(age / 14, 2)
        pool = [i for i in items if i["slug"] != skip]
        if not pool:
            return items
        target = max(pool, key=need)
        if need(target) < 1:
            return items
        old = self.cloud.get("articles", target["slug"])
        LIVE.set(mode="improving an existing page", subject=old["title"], slug="", force=True)
        page, report = self.make(old.get("subject") or old["title"], old["section"])
        if not page:
            self.history("improve", old["title"], "tried to rewrite it, kept the old version", str(report))
            return items
        page["slug"] = old["slug"]
        better = []
        if page["checked"]["claims"] - page["checked"]["removed"] > old["checked"]["claims"] - old["checked"]["removed"]:
            better.append(f"more checked facts ({old['checked']['claims'] - old['checked']['removed']} -> "
                          f"{page['checked']['claims'] - page['checked']['removed']})")
        for k, name in (("diagram", "a diagram"), ("quiz", "a quiz"), ("glossary", "a glossary"), ("dates", "key dates")):
            if page.get(k) and not old.get(k):
                better.append(f"added {name}")
        if old.get("status") == "weak" and page["status"] == "ok":
            better.append("no longer weak")
        if not better:
            self.history("improve", old["title"], "rewrote it, but the new version wasn't better: kept the old one")
            return items
        return self.publish(page, items, "improve", "better because: " + ", ".join(better),
                            backup=json.dumps(old, ensure_ascii=False)[:200000], reason="page improved")

    def review(self, items):
        """Weekly, like a picky visitor: the 3 biggest problems -> queued or fixed by the next improvements."""
        problems = []
        empty = [s for s in SECTIONS if not any(i["section"] == s for i in items)]
        if empty:
            problems.append(f"{len(empty)} sections have no page yet ({', '.join(SECTIONS[s] for s in empty[:4])}): their subjects get more weight")
            for k, q in self.cloud.list("queue").items():
                if q.get("section") in empty:
                    self.cloud.put("queue", k, {**q, "weight": 3})
        bare = [i for i in items if not (i.get("has") or {}).get("diagram")]
        if bare:
            problems.append(f"{len(bare)} pages have no diagram: they go first in the daily improvements")
        weak = [i for i in items if i.get("status") == "weak"]
        if weak:
            problems.append(f"{len(weak)} pages are marked weak: they are rewritten first")
        self.history("review", "weekly review", "; ".join(problems[:3]) or "no big problem found", "a visitor's eye")
        save_state(last_review=time.time())

    def cycle(self):
        save_state(phase="loading the brain", cycle_started=now())
        LIVE.cloud = self.cloud
        LIVE.set(step="start", phase="waking up Auric's brain", mode="", subject="", slug="", sources=[], draft={},
                 checks=[], force=True)
        self.brain = Brain()
        try:
            idx = self.index()
            items = idx.get("items", [])
            if len(self.cloud.list("queue")) < 10:
                save_state(phase="finding new subjects")
                self.refill(items)
            if time.time() - state().get("last_review", 0) > 7 * 86400 and items:
                self.review(items)
            key, q = self.pick(items)
            if q:
                save_state(phase=f"researching and writing: {q['subject']}")
                log(f"subject: {q['subject']} ({q['section']})")
                LIVE.set(mode="writing a new page", subject=q["subject"], section=q["section"], why=q.get("reason", ""), force=True)
                page, report = self.make(q["subject"], q["section"])
                if page:
                    items = self.publish(page, items, reason=q.get("reason", ""))
                    self.cloud.delete("queue", key)
                    save_state(last_subject=q["subject"], published=state().get("published", 0) + 1)
                else:
                    self.cloud.put("queue", key, {**q, "tries": q.get("tries", 0) + 1})
                    self.history("fail", q["subject"], "not published", str(report))
                    save_state(last_subject=q["subject"])
            save_state(phase="improving an existing page")
            items = self.improve(items, q.get("subject") and slugify(q["subject"]) if q else None)
            import techverse_code                               # + design: two improvements to the site's own code,
            if coder_available():                               # by the coding brain (both 7Bs don't fit together)
                self.brain.close()
                LIVE.set(step="code", mode="designing the website", phase="waking up Auric's coding brain", force=True)
                self.brain = Brain(CODER)
            for _ in range(2):
                if not switch.is_on():
                    break
                save_state(phase="designing and coding the website")
                techverse_code.improve_code(self.brain, LIVE, self.history)
        finally:
            if self.brain:
                self.brain.close()
            self.brain = None
            save_state(phase="resting", cycle_ended=now(), cycles=state().get("cycles", 0) + 1)


def gpu_ready():
    """Our turn on the graphics card, with room for the 7B (the app may be using it)."""
    if not switch.acquire_gpu("techverse"):
        return False
    if os.environ.get("AURIC_LLAMA_WRITER"):
        return True                                       # (GitHub's computers: no graphics card to share)
    import auricv2_local
    if auricv2_local._free_gpu_gb() < 5.6:
        switch.release_gpu()
        return None
    return True


def main(once=False):
    w = Writer()
    LIVE.cloud = w.cloud
    while switch.is_on():
        ok = gpu_ready()
        if ok is False:
            return                                           # switched OFF
        if ok is None:
            save_state(phase="waiting: the graphics card is busy (the app or a training uses it)")
            LIVE.set(step="wait", phase="waiting for the graphics card (Saad's PC is using it)", force=True)
            time.sleep(10 * 60)
            continue
        try:
            w.cycle()
        except Exception as e:
            log("cycle failed:\n" + traceback.format_exc())
            try:
                w.history("fail", "cycle", f"the cycle stopped: {type(e).__name__}", str(e)[:300])
            except Exception:
                pass                                          # (no internet: logged here, retried next cycle)
        finally:
            switch.release_gpu()
        nxt = datetime.fromtimestamp(time.time() + REST_BETWEEN, timezone.utc).isoformat(timespec="seconds")
        LIVE.set(step="rest", phase="resting before the next page", next=nxt, force=True)
        if once:
            return
        save_state(phase="resting")
        for _ in range(REST_BETWEEN // 30):
            if not switch.is_on():
                return
            time.sleep(30)


if __name__ == "__main__":
    main(once="once" in sys.argv)
