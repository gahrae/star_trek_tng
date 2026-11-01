#!/usr/bin/env python3
"""Fetch each character's species from the infobox of their Memory Alpha page.

Reads the page for each character from data/images.json and writes data/species.json: slug -> {"page", "species"}
(species is null when the page has no species field). Skips characters already fetched for the same page.
Text is Memory Alpha's (CC BY-NC) and is for personal study only.
"""
import re, json, sys, time, pathlib, requests
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from provenance import record
API = "https://memory-alpha.fandom.com/api.php"
S = requests.Session(); S.headers["User-Agent"] = "Mozilla/5.0 (personal study; contact gareth.stretton@gmail.com)"

def clean(v):
    """A species field as plain text: links, templates, fractions and line breaks flattened."""
    v = re.sub(r"<!--.*?-->|<ref.*?</ref>|<ref[^>]*/>", "", v, flags=re.S)
    v = v.replace("&frac12;", "Half").replace("&frac34;", "Three-quarters").replace("&frac14;", "One-quarter")
    v = re.sub(r"\{\{dis\|([^|}]*)[^}]*\}\}", r"\1", v)           # {{dis|Q|species}} -> Q
    v = re.sub(r"\{\{small\|(.*?)\}\}", r"\1", v)
    v = re.sub(r"\{\{[^{}]*\}\}", "", v)
    v = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", v)         # [[a|b]] -> b
    v = re.sub(r"<br\s*/?>", ", ", v); v = re.sub(r"<[^>]+>", "", v)
    return re.sub(r"\s+", " ", v).strip(" ,")

images = json.load(open(ROOT / "data" / "images.json"))
path = ROOT / "data" / "species.json"
out = json.load(open(path)) if path.exists() else {}
todo = {sl: rec["page"] for sl, rec in images.items() if rec.get("page") and out.get(sl, {}).get("page") != rec["page"]}
out = {sl: v for sl, v in out.items() if sl in images and images[sl].get("page") == v.get("page")}      # drop characters whose page changed
by_page = {}
for sl, pg in todo.items(): by_page.setdefault(pg, []).append(sl)
titles = sorted(by_page)
for i in range(0, len(titles), 15):
    batch = titles[i:i + 15]
    r = S.get(API, params=dict(action="query", prop="revisions", rvprop="content", rvslots="main", titles="|".join(batch), redirects=1, format="json"), timeout=60); r.raise_for_status()
    q = r.json()["query"]; moved = {x["from"]: x["to"] for x in q.get("redirects", []) + q.get("normalized", [])}
    pages = {pg["title"]: pg for pg in q["pages"].values()}
    for t in batch:
        pg = pages.get(moved.get(moved.get(t, t), moved.get(t, t))) or pages.get(t)
        text = pg["revisions"][0]["slots"]["main"]["*"] if pg and "revisions" in pg else ""
        m = re.search(r"\|\s*species\s*=\s*([^\n]*)", text); sp = clean(m.group(1)) if m else ""
        for sl in by_page[t]: out[sl] = {"page": t, "species": sp or None}
    time.sleep(1.0)
path.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
record("species", source=API, characters=len(out), with_species=sum(1 for v in out.values() if v["species"]))
print(f"{len(out)} characters; {sum(1 for v in out.values() if v['species'])} with a species ({len(todo)} fetched)")
