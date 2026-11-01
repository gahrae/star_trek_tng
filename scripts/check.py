#!/usr/bin/env python3
"""Sanity checks on the data, notes and site. Exit code 1 on any failure."""
import json, re, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
fails = []
def check(cond, msg):
    if not cond: fails.append(msg)
eps = json.load(open(ROOT / "data" / "episodes.json")); meta = json.load(open(ROOT / "data" / "metadata.json"))
check(len(eps) == 176, f"expected 176 episodes, found {len(eps)}")
check(set(e["prod"] for e in eps) == set(meta), "episodes.json and metadata.json cover different episodes")
check(len({m["code"] for m in meta.values()}) == len(meta), "duplicate episode codes in metadata")
check(all((ROOT / "data" / "text" / f"{e['prod']}.txt").stat().st_size > 10000 for e in eps), "a transcript is missing or suspiciously small")
chars = json.load(open(ROOT / "data" / "characters.json"))
check(chars.get("PICARD", {}).get("lines", 0) > 12000, "Picard's line count looks wrong")
for f in ("cast.json", "scenes.json", "presence.json", "images.json", "episode_images.json"):
    check((ROOT / "data" / f).exists(), f"data/{f} missing")
epimg = json.load(open(ROOT / "data" / "episode_images.json"))
check(all((epimg.get(e["prod"]) or {}).get("file") and (ROOT / "data" / "episode_images" / epimg[e["prod"]]["file"]).exists() for e in eps), "an episode has no screenshot on disk")
notes = ROOT / "notes"
check(len(list((notes / "episodes").glob("*.md"))) == 176, "not every episode has a note")
check(len(list((notes / "characters").glob("*.md"))) >= 190, "too few character notes")
for name in ("hand-written", "hand-assigned", "hand-curated"):
    hits = [p for p in notes.rglob("*.md") if name in p.read_text(encoding="utf-8").lower()]
    check(not hits, f"'{name}' wording found in {hits[:3]}")
# unrendered template placeholders such as {e['director']} mean a formatting prefix was lost
leaked = [p for p in notes.rglob("*.md") if re.search(r"\{[a-z_]+\[", p.read_text(encoding="utf-8"))]
check(not leaked, f"unrendered placeholders in {[str(x) for x in leaked[:3]]}")
# markdown links inside notes/ must resolve
broken = 0
for p in notes.rglob("*.md"):
    for link in re.findall(r"\]\(([^)#]+\.md)(?:#[^)]*)?\)", p.read_text(encoding="utf-8")):
        if link.split("/")[-1] in ("visuals.md", "search.md", "index.md") and "transcripts" in link or link in ("visuals.md", "search.md"): continue   # pages that exist only on the site
        if not (p.parent / link).resolve().exists(): broken += 1
check(broken == 0, f"{broken} broken links in notes/")
site = ROOT / "site"
if site.exists():
    check((site / "index.html").exists() and (site / "search.json").exists(), "site index or search index missing")
    check(len(list((site / "transcripts").glob("*.html"))) == 177, "transcript pages missing")
    broken = 0; n = 0
    for p in site.rglob("*.html"):
        for h in re.findall(r'href="([^"#$]+)(?:#[^"]*)?"', p.read_text(encoding="utf-8")):
            if h.startswith(("http", "mailto")): continue
            n += 1
            if not (p.parent / h).resolve().exists(): broken += 1
    check(broken == 0, f"{broken} of {n} internal site links are broken")
    ids = set(re.findall(r'id="([^"]+)"', (site / "arcs.html").read_text(encoding="utf-8")))
    used = set()
    for p in (site / "episodes").glob("*.html"): used |= set(re.findall(r'href="\.\./arcs\.html#([^"]+)"', p.read_text(encoding="utf-8")))
    check(used <= ids, f"arc anchors missing on arcs.html: {sorted(used - ids)[:5]}")
# source links: every cited episode exists, explicit markers are backed by the transcript they point to,
# and a character's facts only cite episodes that character is in
sys.path.insert(0, str(ROOT / "scripts"))
import sources, curated_characters as cc
appear = json.load(open(ROOT / "data" / "appearances.json")); presence = json.load(open(ROOT / "data" / "presence.json"))
_text = {}
def transcript(prod):
    if prod not in _text: _text[prod] = (ROOT / "data" / "text" / f"{prod}.txt").read_text(encoding="utf-8").lower()
    return _text[prod]
RANKS = {"captain", "commander", "lieutenant", "counselor", "doctor", "chief", "ensign", "admiral", "lord", "the"}
claims = ([(k, n, x) for k, (n, fs) in cc.FACTS.items() for x in fs] + [(k, cc.GUESTS[k][0], x) for k, fs in cc.GUEST_FACTS.items() for x in fs if k in cc.GUESTS]
          + [(k, n, d) for k, (n, d) in cc.GUESTS.items()])
unknown, unbacked, absent = [], [], []
def present(label, words, p):
    return label in appear and p in appear[label] or label in presence.get(p, {}) or any(w in transcript(p) for w in words)
for label, name, text in claims:
    try: groups = sources.cited_groups(text)
    except ValueError as ex: unknown.append(str(ex)); continue
    kws = sources.keywords(text)
    for p in sources.cited_prods(text, italics=False):
        if kws and not any(k.lower() in transcript(p) for k in kws): unbacked.append(f"{label} cites {sources.CODE[p]} but it has none of {kws[:3]}")
    words = [w.lower() for w in re.findall(r"[A-Za-z']{3,}", name) if w.lower() not in RANKS]
    for g in groups:      # a title naming two parts only needs the character in one of them
        if not any(present(label, words, p) for p in g): absent.append(f"{label} cites {', '.join(sources.CODE[p] + ' ' + sources.TITLE[p] for p in g)}, where the name never appears")
drift = [p for p in sources.CODE if (ROOT / "site" / "transcripts" / f"{p}.html").exists()
         and len(re.findall(r'id="l\d+"', (ROOT / "site" / "transcripts" / f"{p}.html").read_text(encoding="utf-8"))) != len(sources.dialogue(p))]
def spell(t): return " ".join(re.sub(r"[^a-z0-9]+", " ", t.lower().replace("traveler", "traveller")).split())
def strong(clause):     # names and quoted phrases: the words a transcript has to contain for the clause to be true
    plain = re.sub(r"\*[^*]+\*", "", clause)
    return re.findall(r"(?<![A-Za-z])'([^']{4,}?)'(?![A-Za-z])", plain) + re.findall(r"(?<!^)(?<![.;:] )\b([A-Z][a-z]{3,})\b", plain)
clause_bad = []
for label, name, text in claims:       # each link is tested against the clause it follows, not the whole fact
    for m in sources.TOKEN.finditer(text):
        found, _ = sources._token(m)
        before = text[:m.start()]; kws = strong(sources.TOKEN.sub("", before[max(before.rfind(";"), before.rfind(". "), 0):]))
        if found and kws and not any(any(spell(k) in spell(transcript(p)) for k in kws) for p in found):
            clause_bad.append(f"{label}: {', '.join(sources.CODE[p] for p in found)} does not contain any of {kws[:3]}")
check(not clause_bad, f"{len(clause_bad)} links where the clause before them is not in the episode: {clause_bad[:4]}")
check(not drift, f"line links would point at the wrong line in {drift[:5]}: sources.dialogue() no longer matches the transcript pages")
check(not unknown, f"unknown episodes cited: {unknown[:3]}")
check(not unbacked, f"explicit source markers the transcript does not back: {unbacked[:3]}")
check(not absent, f"{len(absent)} cited episodes where the character does not appear: {absent[:5]}")
if fails:
    print("CHECKS FAILED:\n  " + "\n  ".join(fails)); sys.exit(1)
print("all checks passed")
