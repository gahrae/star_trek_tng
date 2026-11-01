#!/usr/bin/env python3
"""Fetch the Memory Alpha pages that curated facts cite with {ma:Page Title|phrase}, as plain text.

Writes data/ma_pages/<slug>.txt (the page's text, first line the title) so check.py can confirm a cited phrase is on the page.
Skips pages already downloaded. Text is Memory Alpha's (CC BY-NC) and is for personal study only.
"""
import re, sys, time, pathlib, requests
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from sources import MA_TOKEN, ma_slug
OUT = ROOT / "data" / "ma_pages"; OUT.mkdir(parents=True, exist_ok=True)
API = "https://memory-alpha.fandom.com/api.php"
S = requests.Session(); S.headers["User-Agent"] = "Mozilla/5.0 (personal study; contact gareth.stretton@gmail.com)"
src = (ROOT / "scripts" / "curated_characters.py").read_text(encoding="utf-8") + (ROOT / "scripts" / "curated_episodes.py").read_text(encoding="utf-8")
titles = sorted({m.group(1) for m in MA_TOKEN.finditer(src)} | set(sys.argv[1:]))
got = 0
for t in titles:
    f = OUT / f"{ma_slug(t)}.txt"
    if f.exists(): continue
    r = S.get(API, params=dict(action="query", prop="extracts", explaintext=1, titles=t, redirects=1, format="json"), timeout=30); r.raise_for_status()
    pg = next(iter(r.json()["query"]["pages"].values())); time.sleep(1.0)
    if "extract" not in pg: print(f"no page for {t!r}", file=sys.stderr); continue
    f.write_text(t + "\n" + pg["extract"], encoding="utf-8"); got += 1; print(f"{t}: {len(pg['extract'])} characters")
from provenance import record; record("ma_pages", source=API, pages=len(list(OUT.glob("*.txt"))))
print(f"{got} new pages, {len(titles)} cited -> {OUT}")
