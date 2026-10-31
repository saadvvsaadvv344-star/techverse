"""Auric designs and codes TechVerse itself: every cycle it adds design and interactivity, written by its own brain in
React, with its design toolkit (src/auric/kit.js): scroll animations, hover and cursor effects, animated heroes,
3D cards, page transitions, enhanced diagrams, live demos...

Three kinds of work:
  * effect   - something new on the site (a button, a cursor glow, a reading-progress bar...)
  * enhancer - RESTYLES / ANIMATES existing parts of the site (cards, hero, headings, diagrams, glossary...): it adds its
               own "ax-..." classes to them with kit.enhance() and styles those (so the core files stay untouched)
  * demo     - an interactive learning demo shown on pages and on /demos

Never breaks the site:
  * it only writes in its own area: TechVerse/site/src/auric/ (effects/, demos/, auric.css with "ax-" classes);
    the registry that plugs its components in is generated here, not written by the brain;
  * safety rules: no network calls, no eval, no raw HTML, imports only React and its kit, CSS only for "ax-" classes;
  * ESLint: undefined names, hooks misuse... with line numbers (the brain gets them, and 2 tries to fix);
  * the site must BUILD with no error;
  * headless Edge opens the self-test page (a sample of every part of the site) at phone (375px) and desktop size,
    scrolls, moves the mouse, clicks every button: any error, unreadable text (contrast), invisible button or
    sideways scrolling = rejected;
  * only then it's deployed, with BEFORE / AFTER screenshots published for the Live page; the previous code is zipped
    in data/techverse_code_backups (rollback = unzip); on the site each part runs in a safety wrapper.
"""
import base64
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE = Path(os.environ.get("AURIC_SITE") or ROOT / "TechVerse" / "site")          # (GitHub: the repository's site/)
AREA = SITE / "src" / "auric"
MANIFEST = AREA / "manifest.json"
STATE_DIR = Path(os.environ.get("AURIC_STATE_DIR") or ROOT / "data")
BACKUPS = STATE_DIR / "techverse_code_backups"
TRIED = STATE_DIR / "techverse_code_tried.json"
NODE = ROOT / "tools" / "node"
WINDOWS = os.name == "nt"
EDGE = next((Path(p) for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                               r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                               r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                               shutil.which("google-chrome") or "", shutil.which("chromium") or "") if p and Path(p).exists()), None)
FLAGS = {"creationflags": 0x08000000} if WINDOWS else {}      # (no console windows on Windows; nothing elsewhere)
TRIES = 5                                    # the checker's messages are precise: worth a few tries
KIT_NAMES = {"enhance", "onVisible", "animate", "springValue", "useInView", "useScrollProgress", "useMouse", "useSpring",
             "useFrame", "reducedMotion", "canHover", "clamp", "lerp", "mapRange", "easeOut"}
REACT_NAMES = {"useState", "useEffect", "useRef", "useMemo", "useCallback", "useLayoutEffect"}

# (kind, Name, the page it changes most - for the before/after screenshots, exactly what to build)
IDEAS = [
    ("enhancer", "HeroAurora", "home", "a soft animated aurora glow behind the home page hero. With enhance('section.hero', "
     "hero => ...): add the class ax-hero-aurora to the hero (CSS: position relative; isolation isolate; overflow hidden; "
     "border-radius 24px; padding 24px) and append 3 divs with classes 'ax-hero-aurora-blob ax-hero-aurora-b1' (b2, b3). "
     "CSS for the blobs: position absolute; z-index -1; pointer-events none; border-radius 50%; filter blur(60px); "
     "opacity .5; b1: 380px wide and high, left -80px, top -120px, background var(--accent); b2: 320px, right -60px, top "
     "-40px, background var(--accent2); b3: 300px, left 35%, bottom -180px, background #ff6bb5; each drifts with "
     "@keyframes ax-hero-aurora-float (translate 0,0 -> 40px,-30px -> -30px,25px) 18s/24s/30s ease-in-out infinite "
     "alternate; inside @media (prefers-reduced-motion: reduce) no animation. The cleanup returned to enhance removes the "
     "3 blobs (keep them in an array of ELEMENTS) and the class"),
    ("enhancer", "MagneticButtons", "home", "buttons with class 'btn' are gently pulled toward the mouse (max 8px) and spring "
     "back on leave: use enhance on '.btn', listen to pointermove/pointerleave on each, set transform translate; only if canHover()"),
    ("enhancer", "SplitTitle", "article", "every h1 inside main reveals word by word: with enhance, wrap each word in a span "
     "(class ax-split-title-word, style animation-delay i*60ms) that slides up and fades in; keep the same text; once per h1"),
    ("enhancer", "GradientBorderCards", "home", "cards (.card) get an animated rotating gradient border on hover: enhance adds a "
     "class; CSS ::before with conic-gradient(var(--accent), var(--accent2), var(--accent)) and a mask so only a 2px border shows; "
     "rotation with a CSS @property angle or a background-position animation"),
    ("enhancer", "HeadingGlow", "article", "article h2 headings get a soft glowing gradient underline that grows from left to "
     "right when they scroll into view (use onVisible from the kit to add an 'in' class)"),
    ("enhancer", "StepsLine", "article", "the 'How it works' steps (ol.steps) get a vertical gradient line on their left that "
     "fills from top to bottom as each step (li) scrolls into view (onVisible adds a class to each li)"),
    ("enhancer", "DiagramDraw", "article", "SVG diagrams (svg.diagram): their rect and line outlines draw themselves when they "
     "scroll into view: enhance sets each shape's stroke-dasharray and stroke-dashoffset to its length (getTotalLength for "
     "lines/paths, perimeter for rects) then onVisible animates the offset to 0 with a CSS transition"),
    ("enhancer", "GlossaryFlip", "article", "glossary items (dl.glossary > div) become flip cards: the term on the front, the "
     "definition on the back, flipping in 3D on click/tap and with Enter/Space (tabIndex 0, role button, aria-pressed)"),
    ("enhancer", "NavGlow", "home", "top navigation links (.nav a) get a gradient underline that slides in from the left on hover; "
     "the current link (.on) keeps it"),
    ("enhancer", "CountUp", "home", "numbers inside the topic cards (.sec em) count up from 0 to their value when they scroll "
     "into view (keep the words after the number)"),
    ("enhancer", "TiltCards", "home", "cards (.card, .sec) tilt slightly toward the mouse in 3D on hover (max 6 degrees, perspective "
     "800px) and spring back on leave; only if canHover()"),
    ("enhancer", "SourcePreview", "article", "hovering or focusing a citation number (a.cite) shows a small floating card above it "
     "with the title of that source (read from the li with the id in the link's href, e.g. #src-1); removed on leave"),
    ("enhancer", "PageEnter", "article", "when a new page is shown (each new direct child of main.main), it fades and slides up "
     "into place (enhance on 'main.main > *' adds an animation class)"),
    ("effect", "CursorGlow", "home", "a soft glowing circle (var(--accent), blurred, 300px, low opacity, mix-blend-mode screen) "
     "follows the mouse with a spring delay (useMouse + useSpring for x and y); only if canHover(); behind the content "
     "(position fixed, pointer-events none, z-index 0)"),
    ("effect", "ScrollSpyToc", "article", "on wide screens (min-width 1200px) and only on article pages, a floating mini table "
     "of contents of the article's h2 headings at the right, highlighting the one being read; clicking scrolls to it smoothly"),
    ("effect", "ReadingTime", "article", "on article pages (article.article), shows 'about N min read' as a small pill under "
     "the h1 (insert it with enhance), counting 200 words a minute"),
    ("effect", "SlashSearch", "home", "pressing '/' focuses the site's search box (form.search input) unless you're typing in a "
     "field; a small hint '/' appears inside the search box on desktop"),
    ("effect", "QuizConfetti", "article", "when an element with class 'score' contains 'perfect', a 1.5 s confetti burst falls "
     "(a fixed canvas, coloured pieces with gravity), then the canvas is removed"),
    ("effect", "HeadingLinks", "article", "hovering an article h2 shows a small '#' button that copies the page link with the "
     "heading's text as a hash to the clipboard and says 'Copied!' for a second"),
    ("demo", "MorseCode", "demos", "a Morse code translator: type text, see dots and dashes, press play to hear it (Web Audio API)"),
    ("demo", "PasswordStrength", "demos", "a password strength meter: type a password, see its length, character types, a rough "
     "number of guesses, a coloured bar and tips (nothing is sent anywhere)"),
    ("demo", "OhmsLaw", "demos", "Ohm's law: sliders for voltage and resistance, shows the current and an SVG circuit with a bulb "
     "that glows brighter with more current"),
    ("demo", "BinarySearch", "demos", "binary search game: think of a number 1-100; the computer guesses by halving; you answer "
     "higher/lower; it shows each step and how many it took"),
    ("demo", "ParityBit", "demos", "error detection: 7 data bits and a computed parity bit; flip any bit to see the error detected"),
    ("demo", "HashDemo", "demos", "type text and see a short checksum (sum of char codes times position, modulo 65536, in hex) "
     "change completely when one letter changes"),
    ("demo", "Pipeline", "demos", "a CPU pipeline animation: instructions move through fetch, decode, execute and write stages; "
     "play/pause and step buttons"),
    ("demo", "ShortestPath", "demos", "6 routers drawn as an SVG network with distances; tap two routers to see the shortest "
     "route highlighted (Dijkstra) and its length"),
    ("demo", "SolarAngle", "demos", "a slider for the sun's angle shows a panel and how much light it receives (cosine)"),
    ("demo", "ImagePixels", "demos", "a smiley drawn on a grid; a slider changes the grid from 4x4 to 32x32 pixels"),
]

# Auric's own earlier work, rewritten better (its new version replaces the old one if it passes every test)
REDO = [
    ("effect", "BackToTop", "article", "improve the existing back-to-top button: it must render NOTHING until the page is "
     "scrolled down more than 600px, then appear with a fade and slide-up; round 48px button at the bottom right, gradient "
     "background from var(--accent) to var(--accent2), a white '↑' arrow, soft shadow, aria-label 'Back to top'; clicking "
     "scrolls smoothly to the top; one scroll listener (passive) cleaned up on unmount"),
]

RULES = """Rules (checked automatically; breaking one = rejected):
- One React function component, `export default function {name}`. Only import from 'react' and from '../kit.js'.
- Functions used in the JSX (onClick...) are defined in the component body, NOT inside useEffect.
- No fetch, no XMLHttpRequest, no eval, no new Function, no innerHTML, no dangerouslySetInnerHTML, no external URLs,
  no localStorage, no cookies, no window.open. Everything happens in the visitor's browser only.
- Clean up everything in useEffect's return (listeners, timers, observers, animation frames, elements you inserted,
  classes you added).
- Never render an invisible or unclickable button: if it shouldn't show yet, render nothing. The test scrolls the page,
  moves the mouse and clicks every button. Text must be readable (contrast) in dark AND light mode.
- Mobile first: works at 375px wide with no sideways scrolling; touch-friendly (buttons at least 36px tall).
- Respect reduced motion (kit: reducedMotion()). Hover-only effects only when canHover().
- CSS: only classes starting with "ax-{slug}" (pseudo-elements, :hover, @keyframes ax-{slug}-... are fine), using the
  site's variables: var(--bg), var(--bg2), var(--card), var(--line), var(--text), var(--muted), var(--accent),
  var(--accent2), var(--good), var(--bad), var(--r). Make it beautiful: smooth easing (cubic-bezier(.2,.8,.2,1)),
  soft shadows, gradients from var(--accent) to var(--accent2), 200-600 ms transitions.
- Plain, friendly English for any text shown."""

KIT = """Your design toolkit (import from '../kit.js'):
- enhance(selector, el => { ...; return () => undo }) -> cleanup: runs on every matching element now and on new ones
  (page changes); use it to add your ax- classes / insert small elements into existing parts of the site.
- onVisible(selector, (isVisible, el) => ..., { once }) -> cleanup: when elements scroll into view.
- NO-REACT tools, for use INSIDE enhance callbacks and event handlers:
  animate({ from, to, duration, onUpdate: v => ..., onDone }) -> cancel;
  springValue(v => ..., { initial: [0, 0] }) -> { set(target), stop() }  (smooth following: magnetic, tilt...).
- HOOKS (only at the top of the component body, never inside callbacks, loops or enhance):
  useInView(ref), useScrollProgress() (0..1), useMouse() ({x, y}), useSpring(target), useFrame(seconds => ...).
- reducedMotion(), canHover(), clamp, lerp, mapRange, easeOut.
Hover / magnetic / tilt effects on many elements: enhance + pointer listeners + springValue + el.style.transform.
The site's parts: header.top (a.brand, form.search > input, nav.nav > a, a.on = current), main.main,
section.hero (h1 with span.grad, p, .hero-actions > a.btn / a.btn.primary), .sections > a.sec (span.ic, b, small, em),
.cards > a.card (small.tag, b, span), article.article (h1, p.lead, .meta-line, section.block > h2 + p,
ol.steps > li, svg.diagram, ul.dates, dl.glossary > div > dt + dd, .quiz, .score, section.sources > ol > li#src-N),
sup > a.cite (href "#src-N"), .demo, footer.foot."""

EXAMPLE_ENHANCER = """Example of a good enhancer (exactly this style):
```jsx
import { useEffect } from 'react';
import { enhance, canHover } from '../kit.js';

export default function LiftCards() {
  useEffect(() => {
    if (!canHover()) return undefined;
    return enhance('.card', (el) => {
      el.classList.add('ax-lift-cards');
      const on = () => el.classList.add('ax-lift-cards-up');
      const off = () => el.classList.remove('ax-lift-cards-up');
      el.addEventListener('pointerenter', on);
      el.addEventListener('pointerleave', off);
      return () => { el.removeEventListener('pointerenter', on); el.removeEventListener('pointerleave', off);
        el.classList.remove('ax-lift-cards', 'ax-lift-cards-up'); };
    });
  }, []);
  return null;
}
```
```css
.ax-lift-cards { transition: transform .35s cubic-bezier(.2,.8,.2,1), box-shadow .35s; }
.ax-lift-cards-up { transform: translateY(-4px); box-shadow: 0 14px 30px color-mix(in srgb, var(--accent) 25%, transparent); }
```
Second example, an element that smoothly follows the mouse inside each hero (springValue, no hooks inside callbacks):
```jsx
import { useEffect } from 'react';
import { enhance, canHover, springValue } from '../kit.js';

export default function HeroDot() {
  useEffect(() => {
    if (!canHover()) return undefined;
    return enhance('section.hero', (hero) => {
      hero.classList.add('ax-hero-dot-host');
      const dot = document.createElement('div');
      dot.className = 'ax-hero-dot';
      hero.appendChild(dot);
      const s = springValue(([x, y]) => { dot.style.transform = `translate(${x}px, ${y}px)`; }, { initial: [0, 0] });
      const move = (e) => { const r = hero.getBoundingClientRect(); s.set([e.clientX - r.left - 20, e.clientY - r.top - 20]); };
      hero.addEventListener('pointermove', move);
      return () => { hero.removeEventListener('pointermove', move); s.stop(); dot.remove(); hero.classList.remove('ax-hero-dot-host'); };
    });
  }, []);
  return null;
}
```
```css
.ax-hero-dot-host { position: relative; }
.ax-hero-dot { position: absolute; left: 0; top: 0; width: 40px; height: 40px; border-radius: 50%; pointer-events: none;
  background: radial-gradient(circle, var(--accent), transparent 70%); opacity: .6; }
```"""

EXAMPLE_DEMO = """A DEMO is an interactive box wrapped in <div className="demo"> (the site styles .demo, .demo .row,
.demo button, .demo button.on, .demo input[type=range], .block-label, .muted, .mono). Example:
```jsx
import { useState } from 'react';
export default function Caesar() {
  const [k, setK] = useState(3);
  return (<div className="demo"><label className="block-label">Shift <b>{k}</b>
    <input type="range" min="1" max="25" value={k} onChange={(e) => setK(Number(e.target.value))} /></label></div>);
}
```"""

FORBIDDEN = re.compile(r"\bfetch\s*\(|XMLHttpRequest|\beval\s*\(|new\s+Function|innerHTML|dangerouslySetInnerHTML|"
                       r"localStorage|sessionStorage|document\.cookie|window\.open|https?://(?!www\.w3\.org/)|WebSocket|"
                       r"navigator\.sendBeacon|importScripts", re.I)


def slug(name):
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def manifest():
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"effects": [], "demos": []}


def write_registry(m):
    """src/auric/registry.js from the manifest (generated: the brain never writes it)."""
    lines = ["// GENERATED by techverse_code.py from manifest.json: Auric's own components. Don't edit by hand.",
             "import './auric.css';"]
    for e in m["effects"]:
        lines.append(f"import {e['name']} from './effects/{e['name']}.jsx';")
    for d in m["demos"]:
        lines.append(f"import {d['name']} from './demos/{d['name']}.jsx';")
    lines.append("")
    lines.append("export const EFFECTS = [" + ", ".join(f"{{ name: '{e['name']}', Component: {e['name']} }}" for e in m["effects"]) + "];")
    lines.append("export const AURIC_DEMOS = {")
    for d in m["demos"]:
        lines.append(f"  '{d['id']}': {{ name: {json.dumps(d['title'])}, about: {json.dumps(d['about'])}, Component: {d['name']} }},")
    lines.append("};")
    (AREA / "registry.js").write_text("\n".join(lines) + "\n", encoding="utf-8")


def static_check(name, jsx, css):
    """-> problem text or ''."""
    if len(jsx) > 10000 or len(css) > 5000:
        return "too long"
    if f"function {name}" not in jsx or "export default" not in jsx:
        return f"it must be `export default function {name}`"
    bad = FORBIDDEN.search(jsx) or FORBIDDEN.search(css)
    if bad:
        return f"forbidden: {bad.group(0)}"
    for imp in re.findall(r"^\s*import\s.*?from\s+['\"]([^'\"]+)['\"]", jsx, re.M):
        if imp not in ("react", "../kit.js"):
            return f"it imports '{imp}' (only 'react' and '../kit.js' are allowed)"
    prefix = f"ax-{slug(name)}"
    body = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    body = re.sub(r"@keyframes\s+[\w-]+\s*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}", "", body)        # (keyframe steps aren't selectors)
    for kf in re.findall(r"@keyframes\s+([\w-]+)", css):
        if not kf.startswith(prefix):
            return f"@keyframes {kf} must start with {prefix}"
    for sel in re.findall(r"([^{}]+)\{", body):
        sel = sel.strip()
        if sel.startswith("@"):
            continue
        if not all(prefix in part for part in sel.split(",") if part.strip()):
            return f"CSS selector '{sel[:60]}' styles something that isn't its own (classes must start with {prefix})"
    return ""


def autofix(name, jsx, css):
    """Mechanical fixes (like a formatter would do), so the brain's tries go to real problems:
    animation names get the component's prefix everywhere they're used."""
    prefix = f"ax-{slug(name)}"
    for kf in set(re.findall(r"@keyframes\s+([\w-]+)", css)):
        if not kf.startswith(prefix):
            new = f"{prefix}-{kf}"
            css = re.sub(rf"(?<![\w-]){re.escape(kf)}(?![\w-])", new, css)
            jsx = re.sub(rf"(?<![\w-]){re.escape(kf)}(?![\w-])", new, jsx)
    return jsx, css


def _node_env():
    return {**os.environ, "PATH": str(NODE) + os.pathsep + os.environ["PATH"]} if WINDOWS else dict(os.environ)


def _bin(name):
    """A node tool: Windows needs 'cmd /c tool.cmd'."""
    return ["cmd", "/c", str(name) + ".cmd"] if WINDOWS else [str(name)]


def lint(file):
    """ESLint on Auric's file -> '' or the problems with line numbers."""
    r = subprocess.run(_bin(SITE / "node_modules" / ".bin" / "eslint") + ["--format", "json",
                        str(file.relative_to(SITE))], cwd=SITE, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=180, env=_node_env(), **FLAGS)
    try:
        res = json.loads(r.stdout)
    except ValueError:
        return f"the code checker couldn't read it: {(r.stdout + r.stderr)[-300:]}" if r.returncode else ""
    msgs = [f"line {m.get('line')}: {m.get('message')}" for f in res for m in f.get("messages", []) if m.get("severity") == 2]
    return "; ".join(msgs[:8])


def npm_build(out="dist-try"):
    r = subprocess.run(_bin(NODE / "npm" if WINDOWS else "npm") + ["run", "build", "--", "--outDir", out, "--emptyOutDir"],
                       cwd=SITE, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600,
                       env=_node_env(), **FLAGS)
    return r.returncode == 0, (r.stdout + r.stderr)[-2500:]


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class Served:
    """A built folder served on 127.0.0.1 (SPA: every path -> index.html) while in use."""
    def __init__(self, folder):
        self.folder, self.port = SITE / folder, free_port()

    def __enter__(self):
        script = ("import http.server,os,sys\n"
                  "d=sys.argv[1]\n"
                  "class H(http.server.SimpleHTTPRequestHandler):\n"
                  "  def __init__(s,*a,**k): super().__init__(*a,directory=d,**k)\n"
                  "  def send_head(s):\n"
                  "    p=s.translate_path(s.path)\n"
                  "    if not os.path.exists(p): s.path='/index.html'\n"
                  "    return super().send_head()\n"
                  "  def log_message(s,*a): pass\n"
                  "http.server.ThreadingHTTPServer(('127.0.0.1',int(sys.argv[2])),H).serve_forever()\n")
        self.p = subprocess.Popen([sys.executable, "-c", script, str(self.folder), str(self.port)],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **FLAGS)
        time.sleep(1.2)
        return f"http://127.0.0.1:{self.port}"

    def __exit__(self, *a):
        self.p.terminate()


def edge(args, timeout=90):
    prof = tempfile.mkdtemp(prefix="tv-edge-")
    try:
        return subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
                               "--hide-scrollbars", f"--user-data-dir={prof}", *([] if WINDOWS else ["--no-sandbox"]), *args],
                              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, **FLAGS)
    finally:
        shutil.rmtree(prof, ignore_errors=True)


def selftest(folder="dist-try"):
    """The self-test page in headless Edge, phone (375px frame) then desktop -> (ok, report)."""
    if not EDGE:
        return False, "no browser to test with"
    report = {}
    with Served(folder) as base:
        for label, extra in (("phone", "&phone=1"), ("desktop", "")):
            r = edge(["--window-size=1280,900", "--virtual-time-budget=14000", "--dump-dom", f"{base}/?selftest=1{extra}"])
            m = re.search(r'<pre id="selftest-result">(.*?)</pre>', r.stdout, re.S)
            if not m or m.group(1).strip() == "running":
                return False, f"{label}: the self-test page didn't finish (the site may not start)"
            res = json.loads(m.group(1).replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">"))
            report[label] = res
            if not res.get("ok"):
                why = "; ".join(res.get("errors", [])[:3]) or (f"sideways scrolling ({', '.join(res.get('offenders', []))})" if res.get("wide") else "failed")
                return False, f"{label}: {why}"
    return True, report


def screenshot(folder, path):
    """A JPEG data URL of `path` on the built site (desktop, 1280x800, shown at 720px)."""
    if not EDGE:
        return ""
    out = Path(tempfile.mkdtemp(prefix="tv-shot-")) / "shot.png"
    try:
        with Served(folder) as base:
            edge(["--window-size=1280,800", "--virtual-time-budget=9000", f"--screenshot={out}", f"{base}{path}"])
        if not out.exists():
            return ""
        from PIL import Image
        im = Image.open(out).convert("RGB")
        im.thumbnail((720, 720))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=72, optimize=True)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""
    finally:
        shutil.rmtree(out.parent, ignore_errors=True)


def page_path(page):
    if page == "article":
        try:
            from techverse_cloud import TechCloud
            items = (TechCloud().get("meta", "index") or {}).get("items", [])
            if items:
                return f"/a/{items[0]['slug']}"
        except Exception:
            pass
    return {"demos": "/demos", "article": "/"}.get(page, "/")


def save_to_github(message):
    """In the cloud, Auric's accepted designs (and its memory) go back into the GitHub project at once - the project
    is the one place the site's code lives."""
    if not os.environ.get("AURIC_CLOUD"):
        return
    repo = SITE.parent
    run = lambda *a: subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True)
    run("add", "site/src/auric", "state")
    if run("commit", "-m", message).returncode == 0:
        run("pull", "--rebase", "--autostash")
        run("push")


def deploy():
    import techverse_cloud
    code, out = techverse_cloud.firebase("deploy", "--only", "hosting", "--project", "techverse-saad", "--non-interactive")
    return code == 0, out[-600:]


def backup():
    BACKUPS.mkdir(parents=True, exist_ok=True)
    z = BACKUPS / f"auric-{datetime.now():%Y%m%d-%H%M%S}.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as f:
        for p in AREA.rglob("*"):
            if p.is_file():
                f.write(p, p.relative_to(AREA))
    return z


def restore(z):
    shutil.rmtree(AREA)
    AREA.mkdir(parents=True)
    with zipfile.ZipFile(z) as f:
        f.extractall(AREA)


def parse(raw):
    jsx = re.search(r"```(?:jsx|javascript|js|react)?\s*\n(.*?)```", raw, re.S)
    css = re.search(r"```css\s*\n(.*?)```", raw, re.S)
    about = re.search(r"ABOUT:\s*(.+)", raw)
    title = re.search(r"TITLE:\s*(.+)", raw)
    return (jsx.group(1).strip() if jsx else "", css.group(1).strip() if css else "",
            about.group(1).strip()[:160] if about else "", title.group(1).strip()[:60] if title else "")


def spec_review(brain, kind, name, what, jsx, css):
    """Auric can't see its designs, but it can read its code: each point of the brief is checked against the code.
    -> '' or the points the code misses."""
    raw = brain.b.ask("You turn a design brief into a short checklist of concrete, checkable points.",
                      f"Brief for {name}: {what}\n\nWrite 3 to 6 short checklist points, one per line, starting with '- ', "
                      "each about something visible or behavioural that the code must do (sizes, blur, colours, motion, "
                      "when it appears, what clicking does).", max_new=220)
    points = [p.strip("- ").strip() for p in raw.splitlines() if p.strip().startswith("-")][:6]
    missing = []
    for p in points:
        if not brain.yes(f"Code:\n```jsx\n{jsx[:5000]}\n```\n```css\n{css[:2500]}\n```\n\nDoes this code clearly do this: {p}? "
                         "Answer no if it's missing, only partly done, or done differently.",
                         system="You are a strict senior front-end reviewer. Answer only yes or no.", sure=0.6):
            missing.append(p)
    return "; ".join(missing)


def remove_component(name):
    """Takes one of Auric's components out (its file, its CSS, its manifest entry) - used for rollbacks."""
    m = manifest()
    m["effects"] = [e for e in m["effects"] if e["name"] != name]
    m["demos"] = [d for d in m["demos"] if d["name"] != name]
    MANIFEST.write_text(json.dumps(m, indent=1), encoding="utf-8")
    write_registry(m)
    for sub in ("effects", "demos"):
        (AREA / sub / f"{name}.jsx").unlink(missing_ok=True)
    text = (AREA / "auric.css").read_text(encoding="utf-8")
    (AREA / "auric.css").write_text(re.sub(rf"\n/\* auric:{name} \*/.*?(?=\n/\* auric:|\Z)", "", text, flags=re.S).rstrip() + "\n",
                                    encoding="utf-8")


def tried():
    try:
        return json.loads(TRIED.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def next_idea(brain, m):
    have = {e["name"] for e in m["effects"]} | {d["name"] for d in m["demos"]}
    done = set(tried())
    for kind, name, page, what in REDO:
        if f"redo:{name}" not in done:
            TRIED.write_text(json.dumps(tried() + [f"redo:{name}"]), encoding="utf-8")
            return kind, name, page, what
    for kind, name, page, what in IDEAS:
        if name not in have and name not in done:
            return kind, name, page, what
    raw = brain.b.ask("You are a world-class web designer improving an educational technology website built with React.",
                      "Existing parts: " + ", ".join(sorted(have)) + ". Suggest ONE new design improvement that would make "
                      "the site feel like one of the best-designed websites in the world (an enhancer that restyles or animates "
                      "existing parts, a new effect, or an interactive learning demo). Reply exactly as:\n"
                      "KIND: enhancer or effect or demo\nNAME: PascalCaseName\nPAGE: home or article or demos\n"
                      "WHAT: two sentences describing exactly what it does and how it looks", max_new=160)
    k, n, p, w = (re.search(rf"{x}:\s*(.+)", raw) for x in ("KIND", "NAME", "PAGE", "WHAT"))
    if k and n and w and re.fullmatch(r"[A-Z][A-Za-z0-9]{2,30}", n.group(1).strip()) and n.group(1).strip() not in have | done:
        kind = next((x for x in ("enhancer", "effect", "demo") if x in k.group(1).lower()), "effect")
        return kind, n.group(1).strip(), (p.group(1).strip().lower() if p else "home"), w.group(1).strip()
    return None


def improve_code(brain, live, history):
    """One design / code improvement, fully checked. Returns True if deployed."""
    m = manifest()
    idea = next_idea(brain, m)
    if not idea:
        return False
    kind, name, page, what = idea
    TRIED.write_text(json.dumps(tried() + [name]), encoding="utf-8")       # (never the same idea forever)
    short = re.split(r"[:(;]", what)[0].strip()[:90]
    live.set(step="code", mode="designing the website", subject=name, phase=f"{short} — writing the React code",
             code="", checks=[], sources=[], draft={}, force=True)
    sl = slug(name)
    example = EXAMPLE_DEMO if kind == "demo" else EXAMPLE_ENHANCER
    ask = (f"Build a new {kind} for the TechVerse website: {name}.\nWhat it does: {what}.\n\n{KIT}\n\n{example}\n\n"
           + RULES.format(name=name, slug=sl) +
           f"\n\nReply with:\nTITLE: a short title\nABOUT: one sentence for visitors\n```jsx\n(the whole component)\n```\n"
           f"```css\n(its styles: classes ax-{sl}...)\n```")
    system = ("You are Auric, a world-class front-end designer and careful React developer improving your own website. "
              "You write clean, working, accessible, beautiful code.")
    raw = brain.b.ask(system, ask, max_new=2000)
    jsx, css, about, title = parse(raw)
    live.set(code=jsx[:4000], phase=f"checking the code of {name}", force=True)
    z = backup()
    before = ""
    problem = ""
    for attempt in range(TRIES):
        jsx, css = autofix(name, jsx, css)
        problem = static_check(name, jsx, css) if jsx else "no code block"
        if not problem:
            folder = AREA / ("demos" if kind == "demo" else "effects")
            folder.mkdir(parents=True, exist_ok=True)
            (folder / f"{name}.jsx").write_text(jsx + "\n", encoding="utf-8")
            text = (AREA / "auric.css").read_text(encoding="utf-8")
            text = re.sub(rf"\n/\* auric:{name} \*/.*?(?=\n/\* auric:|\Z)", "", text, flags=re.S)
            (AREA / "auric.css").write_text(text.rstrip() + f"\n\n/* auric:{name} */\n{css}\n", encoding="utf-8")
            m2 = manifest()
            entry = {"name": name, "about": about or what[:160], "added": datetime.now().isoformat(timespec="seconds"), "by": "Auric",
                     "kind": kind}
            if kind == "demo":
                m2["demos"] = [d for d in m2["demos"] if d["name"] != name] + [{**entry, "id": sl, "title": title or name}]
            else:
                m2["effects"] = [e for e in m2["effects"] if e["name"] != name] + [entry]
            MANIFEST.write_text(json.dumps(m2, indent=1), encoding="utf-8")
            write_registry(m2)
            live.check(f"{name}: safety rules", True, "no network, no eval, own CSS only")
            problem = lint(folder / f"{name}.jsx")
            missing_imports = [u for u in dict.fromkeys(re.findall(r"'(\w+)' is not defined", problem)) if u in KIT_NAMES | REACT_NAMES]
            if missing_imports:                             # forgot to import a kit tool or a React hook: added automatically
                for u in missing_imports:
                    src = "../kit.js" if u in KIT_NAMES else "react"
                    m_imp = re.search(rf"import\s*\{{([^}}]*)\}}\s*from\s*['\"]{re.escape(src)}['\"];?", jsx)
                    if m_imp:
                        jsx = jsx.replace(m_imp.group(0), f"import {{ {', '.join(dict.fromkeys([x.strip() for x in m_imp.group(1).split(',') if x.strip()] + [u]))} }} from '{src}';")
                    else:
                        jsx = f"import {{ {u} }} from '{src}';\n" + jsx
                (folder / f"{name}.jsx").write_text(jsx + "\n", encoding="utf-8")
                problem = lint(folder / f"{name}.jsx")
            unused = re.findall(r"'(\w+)' is defined but never used", problem)
            if unused:                                      # unused imports: removed automatically, then checked again
                fixed = jsx
                for u in unused:
                    fixed = re.sub(rf"(import\s*\{{[^}}]*?)\b{u}\b\s*,?\s*", r"\1", fixed)
                fixed = re.sub(r"import\s*\{\s*\}\s*from\s*['\"][^'\"]+['\"];?\n?", "", fixed).replace(", }", " }")
                if fixed != jsx:
                    jsx = fixed
                    (folder / f"{name}.jsx").write_text(jsx + "\n", encoding="utf-8")
                    problem = lint(folder / f"{name}.jsx")
            if problem:
                live.check(f"{name}: code checker", False, problem[:160])
            else:
                live.check(f"{name}: code checker", True, "no undefined names, hooks used correctly")
                live.set(phase=f"reviewing {name} against the design brief", force=True)
                missing = spec_review(brain, kind, name, what, jsx, css)
                if missing:
                    problem = f"the design review found that the code doesn't do: {missing}"
                    live.check(f"{name}: design review", False, missing[:160])
                    ok, out = False, ""
                else:
                    live.check(f"{name}: design review", True, "every point of the brief is in the code")
                    ok, out = npm_build()
                if ok:
                    live.check(f"{name}: build", True, "built with no errors")
                    ok, rep = selftest()
                    if ok:
                        live.check(f"{name}: phone + desktop test", True, "scrolled, clicked, readable, no sideways scrolling")
                        path = page_path(page)
                        live.set(phase="taking before / after screenshots", force=True)
                        before = screenshot("dist", path)
                        after = screenshot("dist-try", path)
                        shutil.rmtree(SITE / "dist", ignore_errors=True)
                        (SITE / "dist-try").rename(SITE / "dist")
                        done, dout = deploy()
                        if not done:
                            history("fail", name, "the code passed every test but the deploy failed", dout[-200:])
                            return False
                        try:
                            from techverse_cloud import TechCloud
                            TechCloud().put("meta", "showcase", {"name": title or name, "kind": kind, "about": about or what[:160],
                                                                  "page": path, "before": before, "after": after,
                                                                  "time": datetime.utcnow().isoformat(timespec="seconds") + "+00:00"})
                        except Exception:
                            pass
                        history("code", f"{title or name} ({kind})", f"Auric designed and coded: {about or what[:160]}",
                                {"demo": "visitors get a new interactive demo to learn by playing",
                                 "enhancer": "existing parts of the site now look and move better",
                                 "effect": "the site gets a new interactive touch"}[kind] +
                                f"; ESLint clean, built with no errors, passed the phone and desktop tests (backup: {z.name})")
                        save_to_github(f"Auric designed {title or name} ({kind})")
                        live.set(step="done", phase=f"the site now has {title or name}", slug="", showcase=True, force=True)
                        return True
                    problem = f"the browser test failed: {rep}"
                    live.check(f"{name}: browser test", False, str(rep)[:160])
                elif not missing:
                    lines = [l for l in out.splitlines() if l.strip() and not l.strip().startswith("at ") and "npm" not in l]
                    problem = "the build failed: " + "\n".join(lines[-14:])[-1200:]
                    live.check(f"{name}: build", False, problem[:160])
            restore(z)                                          # back to the code that worked
        else:
            live.check(f"{name}: safety rules", False, problem)
        if attempt == TRIES - 1:
            break
        live.set(phase=f"fixing {name} (try {attempt + 2} of {TRIES})", force=True)
        hint = ""
        undefined = re.search(r"'?(\w+)'? is not defined", problem)
        if undefined:                                    # the most common mistake: a handler defined inside useEffect
            u = undefined.group(1)
            hint = (f"\nHow to fix it: `{u}` is used but not visible there (defined inside useEffect, inside another "
                    f"function, or not at all). Define `const {u} = ...` directly in the component body, before `return` "
                    "(or import it from '../kit.js' if it is a kit function).")
        if re.search(r"Parsing error|Unexpected token", problem):
            hint += ("\nHow to fix it: a syntax error. In JavaScript, CSS values must be strings: style={{ background: "
                     "'var(--accent)', width: '48px' }}; check every bracket and quote around that line.")
        if re.search(r"postcss|CssSyntaxError|Unknown word|Unclosed", problem):
            hint += ("\nHow to fix it: the CSS has a syntax error. Every rule is `.ax-name { property: value; }`, every { "
                     "has its }, no JavaScript inside the CSS block.")
        if re.search(r"React Hook .* (cannot be called inside a callback|is called in function|called conditionally)", problem):
            hint += ("\nHow to fix it: hooks (useSpring, useFrame, useMouse, useState...) can only be called at the top of the "
                     "component body. Inside enhance() callbacks and event handlers use the kit's springValue(...) or "
                     "animate(...) instead, and change el.style.transform / classes directly.")
        raw = brain.b.ask(system, ask + f"\n\nYour previous code was rejected: {problem}{hint}\n\nPrevious code:\n```jsx\n{jsx}\n```\n"
                          f"```css\n{css}\n```\nFix it. Reply in the same format, with the whole corrected code.", max_new=2000)
        jsx2, css2, about2, title2 = parse(raw)
        jsx, css = jsx2 or jsx, css2 or css
        about, title = about2 or about, title2 or title
        live.set(code=jsx[:4000], force=True)
    restore(z)
    shutil.rmtree(SITE / "dist-try", ignore_errors=True)
    history("fail", f"{name} ({kind})", "Auric's design wasn't published", problem[:300])
    return False


if __name__ == "__main__":                                   # python techverse_code.py registry
    if "registry" in sys.argv:
        write_registry(manifest())
        print("registry written")
