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
if fails:
    print("CHECKS FAILED:\n  " + "\n  ".join(fails)); sys.exit(1)
print("all checks passed")
