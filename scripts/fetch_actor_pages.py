#!/usr/bin/env python3
"""Find each listed actor's own Memory Alpha page, for the actors page.

Writes data/actor_pages.json: actor -> {"page": title or null, "note": why not}. A page counts only if it exists, is not a
disambiguation page, and mentions the series (so a namesake is not linked). Page text is not kept. Skips actors already looked up.
"""
import re, json, sys, time, pathlib, collections, requests
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from provenance import record
API = "https://memory-alpha.fandom.com/api.php"
S = requests.Session(); S.headers["User-Agent"] = "Mozilla/5.0 (personal study; contact gareth.stretton@gmail.com)"
cast = json.load(open(ROOT / "data" / "cast.json"))
credits = collections.Counter(r["actor"] for rows in cast.values() for r in rows)
# every actor the page can list: two or more roles (credits matched to different characters count) or five or more episodes, so two or more credits
actors = sorted(a for a, n in credits.items() if n >= 2 and not a.lower().startswith("unknown"))
path = ROOT / "data" / "actor_pages.json"
out = json.load(open(path)) if path.exists() else {}
todo = [a for a in actors if a not in out]
def lookup(titles):
    r = S.get(API, params=dict(action="query", prop="revisions", rvprop="content", rvslots="main", titles="|".join(titles), redirects=1, format="json"), timeout=60); r.raise_for_status()
    q = r.json()["query"]; redirected = {x["from"]: x["to"] for x in q.get("redirects", []) + q.get("normalized", [])}
    pages = {pg["title"]: pg for pg in q["pages"].values()}
    return redirected, pages
for i in range(0, len(todo), 15):
    batch = todo[i:i + 15]; redirected, pages = lookup(batch)
    for a in batch:
        t = a
        for _ in range(2): t = redirected.get(t, t)
        pg = pages.get(t); text = pg["revisions"][0]["slots"]["main"]["*"] if pg and "revisions" in pg else None
        if text is None: out[a] = {"page": None, "note": "no page"}
        elif re.search(r"may refer to|might refer to", text[:400]): out[a] = {"page": None, "note": "disambiguation page"}
        elif not re.search(r"Next Generation|\bTNG\b", text): out[a] = {"page": None, "note": "page does not mention the series"}
        else: out[a] = {"page": t}
    time.sleep(1.0)
path.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
record("actor_pages", source=API, actors=len(out), with_page=sum(1 for v in out.values() if v["page"]))
print(f"{len(out)} actors; {sum(1 for v in out.values() if v['page'])} with a page; others: {collections.Counter(v.get('note') for v in out.values() if not v['page'])}")
