#!/usr/bin/env python3
"""Fetch per-episode cast lists from Memory Alpha (CC BY-NC) through its MediaWiki API.

Writes data/ma/season<n>.json, data/ma/<prod>.json (raw API responses, reused on rerun)
and data/cast.json: prod -> [{"actor", "role", "credit"}] in page order.
"""
import json, re, sys, time, pathlib, requests
from bs4 import BeautifulSoup
ROOT = pathlib.Path(__file__).resolve().parent.parent
MA = ROOT / "data" / "ma"; MA.mkdir(parents=True, exist_ok=True)
API = "https://memory-alpha.fandom.com/api.php"
S = requests.Session(); S.headers["User-Agent"] = "Mozilla/5.0 (personal study; contact gareth.stretton@gmail.com)"
DELAY = 1.0
eps = {e["prod"] for e in json.load(open(ROOT / "data" / "episodes.json"))}

def parse_page(title, path):
    if not path.exists():
        for attempt in range(3):
            try:
                r = S.get(API, params={"action": "parse", "page": title, "prop": "text", "format": "json"}, timeout=30)
                r.raise_for_status(); data = r.json()
                if "parse" not in data: raise ValueError(data.get("error", data))
                path.write_text(json.dumps(data)); time.sleep(DELAY); break
            except Exception as ex:
                print(f"  retry {attempt+1} for {title}: {ex}", file=sys.stderr); time.sleep(5)
        else:
            raise SystemExit(f"giving up on {title}")
    return BeautifulSoup(json.load(open(path))["parse"]["text"]["*"], "html.parser")

# 1. season pages -> production number -> episode page title
pages = {}
for n in range(1, 8):
    soup = parse_page(f"TNG Season {n}", MA / f"season{n}.json")
    for tr in soup.find("table").find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if len(cells) < 4: continue
        a = cells[1].find("a", title=re.compile(r"\(episode\)$"))
        m = re.search(r"-(\d{3})$", cells[3].get_text(strip=True))
        if a and m:
            prod = "101" if m.group(1) == "941" else m.group(1)     # the pilot has a special number
            pages[prod] = a["title"]
missing = sorted(eps - set(pages))
print(f"{len(pages)} episode pages mapped; missing: {missing}")

# 2. episode pages -> cast lists
SECTION = re.compile(r"(star|co-star|cast|appearance)", re.I)
SKIP = re.compile(r"(stand-in|stunt|photo double|podcast|cast and characters)", re.I)
cast = {}
for i, prod in enumerate(sorted(eps), 1):
    if prod not in pages: continue
    soup = parse_page(pages[prod], MA / f"{prod}.json")
    entries = []
    for h in soup.find_all(["h2", "h3", "h4"]):
        heading = re.sub(r"\s*\[.*?\]\s*", "", h.get_text(" ", strip=True)).strip()
        if not SECTION.search(heading) or SKIP.search(heading): continue
        ul = h.find_next_sibling()
        while ul is not None and ul.name not in ("ul", "h2", "h3", "h4"): ul = ul.find_next_sibling()
        if ul is None or ul.name != "ul": continue
        for li in ul.find_all("li", recursive=False):
            own = " ".join(t if isinstance(t, str) else t.get_text(" ", strip=True) for t in li.children if getattr(t, "name", None) != "ul")
            text = re.sub(r"\s+", " ", re.sub(r"\s*\[.*?\]", "", own)).strip()     # the item's own text, not nested lists
            m = re.match(r"(.+?)\s+as\s+(.+)", text)
            if m: entries.append({"actor": m.group(1).strip(), "role": m.group(2).strip(), "credit": heading})
    cast[prod] = entries
    print(f"[{i:3}/{len(eps)}] {prod} {pages[prod]}: {len(entries)} credits")
(ROOT / "data" / "cast.json").write_text(json.dumps(cast, indent=1, ensure_ascii=False), encoding="utf-8")
sys.path.insert(0, str(ROOT / "scripts")); from provenance import record
record("cast", source=API, episodes=len(cast), credits=sum(map(len, cast.values())), revisions={p: json.load(open(MA / f"{p}.json"))["parse"].get("revid") for p in cast})
print("done ->", ROOT / "data" / "cast.json")
