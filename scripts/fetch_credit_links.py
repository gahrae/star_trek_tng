#!/usr/bin/env python3
"""Find the exact Wikipedia and Memory Alpha pages behind each episode's airdate, director and writer.

Writes data/credit_links.json: prod -> {"wikipedia": {...}, "memory_alpha": {...}}, each with the page for the episode
and a {name: url} map for the people credited. Wikipedia comes from the episode list (the source of data/metadata.json);
Memory Alpha from the episode pages already in data/ma/. Prints where the two sources disagree.
"""
import re, json, sys, pathlib, datetime, urllib.parse, requests
from bs4 import BeautifulSoup
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from provenance import record
LIST = "https://en.wikipedia.org/wiki/List_of_Star_Trek:_The_Next_Generation_episodes"
meta = json.load(open(ROOT / "data" / "metadata.json")); eps = json.load(open(ROOT / "data" / "episodes.json"))
soup = BeautifulSoup(requests.get(LIST, headers={"User-Agent": "Mozilla/5.0 (personal study)"}, timeout=30).text, "html.parser")

def links(cell, base):
    """{visible name: page url} for the links in a cell that point at a page that exists."""
    out = {}
    for a in cell.find_all("a", href=True):
        h = a["href"]
        if "redlink=1" in h or "new" in (a.get("class") or []) or "#" in h or ":" in h.split("/wiki/")[-1]: continue
        out[a.get_text(" ", strip=True)] = h if h.startswith("http") else base + h
    return out

wiki = {}; season = 0; everyone = {}     # Wikipedia links a person only where they first appear, so collect every link in the list

for table in soup.find_all("table", class_="wikitable"):
    rows = []
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        t = [re.sub(r"\s*\[[^\]]*\]", "", c.get_text(" ", strip=True)) for c in cells]
        if len(t) >= 7 and re.fullmatch(r"\d+", t[0]) and re.fullmatch(r"\d{3}( \d{3})?", t[6]): rows.append((cells, t))
    if not rows: continue
    season += 1
    head = table.find_previous(["h2", "h3"]); anchor = head.get("id") if head else None
    for cells, t in rows:
        art = links(cells[2], "https://en.wikipedia.org")
        everyone.update(links(cells[3], "https://en.wikipedia.org")); everyone.update(links(cells[4], "https://en.wikipedia.org"))
        for prod in t[6].split():
            wiki[prod] = {"episode": next(iter(art.values()), None), "list": LIST + (f"#{urllib.parse.quote(anchor, safe='_()')}" if anchor else ""),
                          "people": {**links(cells[3], "https://en.wikipedia.org"), **links(cells[4], "https://en.wikipedia.org")}}

out = {}; disagree = []
for e in eps:
    p = e["prod"]; m = meta[p]
    # a hand-added second part has no row of its own: use its first part's page
    w = wiki.get(p) or next((wiki[q] for q in wiki if q in meta and meta[q]["title_wiki"].split(",")[0] == m["title_wiki"].split(",")[0]), None)
    f = ROOT / "data" / "ma" / f"{p}.json"
    if f.exists(): ma = json.load(open(f))["parse"]
    else:       # the finale has no stored page (its production number maps differently on Memory Alpha)
        ma = requests.get("https://memory-alpha.fandom.com/api.php", params={"action": "parse", "page": e["title"] + " (episode)", "prop": "text", "format": "json"},
                          headers={"User-Agent": "Mozilla/5.0 (personal study)"}, timeout=30).json()["parse"]
    page = BeautifulSoup(ma["text"]["*"], "html.parser")
    people = {}; date = None
    for el in page.find_all(string=re.compile(r"^(Directed by|Written by|Story by|Teleplay by|Based in part on)")):
        row = el.find_parent(["div", "tr"])
        if row: people.update(links(row, "https://memory-alpha.fandom.com"))
    el = page.find(string=re.compile(r"First aired"))
    div = el and el.find_parent("div")
    box = el and (el.find_parent(class_="pi-item") or (div and div.find_parent("div")))
    m2 = box and re.search(r"(\d{1,2} [A-Z][a-z]+ \d{4})", box.get_text(" ", strip=True))
    date = datetime.datetime.strptime(m2.group(1), "%d %B %Y").date().isoformat() if m2 else None
    if date and date != m["airdate_iso"]: disagree.append(f"{p} {e['title']}: Wikipedia {m['airdate_iso']}, Memory Alpha {date}")
    out[p] = {"wikipedia": {"episode": (w or {}).get("episode"), "list": (w or {}).get("list"), "people": {n: u for n, u in everyone.items() if n in m["director"] or n in m["writer"]}},
              "memory_alpha": {"episode": "https://memory-alpha.fandom.com/wiki/" + ma["title"].replace(" ", "_"), "people": people, "airdate": date}}
(ROOT / "data" / "credit_links.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
record("credit_links", source=LIST, episodes=len(out))
print(f"{len(out)} episodes; {sum(1 for v in out.values() if v['wikipedia']['episode'])} with a Wikipedia article; Memory Alpha airdate found for {sum(1 for v in out.values() if v['memory_alpha']['airdate'])}")
print("\n".join(disagree) or "airdates agree")
