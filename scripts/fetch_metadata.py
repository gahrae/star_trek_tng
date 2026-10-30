#!/usr/bin/env python3
"""Fetch broadcast numbering, director and writer credits per episode from Wikipedia's
episode list and join them to our production numbers.  Writes data/metadata.json."""
import re, json, pathlib, requests
from bs4 import BeautifulSoup
ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = "https://en.wikipedia.org/wiki/List_of_Star_Trek:_The_Next_Generation_episodes"
html = requests.get(URL, headers={"User-Agent": "Mozilla/5.0 (personal study)"}, timeout=30).text
soup = BeautifulSoup(html, "html.parser")
meta = {}
season = 0
for table in soup.find_all("table", class_="wikitable"):
    rows = []
    for tr in table.find_all("tr"):
        cells = [re.sub(r"\s*\[[^\]]*\]", "", c.get_text(" ", strip=True)) for c in tr.find_all(["th", "td"])]
        if len(cells) >= 7 and re.fullmatch(r"\d+", cells[0]) and re.fullmatch(r"\d{3}( \d{3})?", cells[6]):
            rows.append(cells)
    if not rows:
        continue
    season += 1
    for cells in rows:
        prods = cells[6].split()
        overall = int(cells[0]); in_season = int(cells[1])
        n = len(prods)
        date = re.search(r"(\d{4}-\d{2}-\d{2})", cells[5])
        meta[prods[0]] = {
            "overall": list(range(overall, overall + n)),
            "season": season,
            "episode_in_season": list(range(in_season, in_season + n)),
            "code": f"S{season:02d}E{in_season:02d}" + (f"-E{in_season+n-1:02d}" if n > 1 else ""),
            "title_wiki": cells[2].strip(' "'),
            "director": cells[3],
            "writer": re.sub(r"\s*:\s*", ": ", cells[4]),
            "airdate_iso": date.group(1) if date else "",
            "viewers_millions": cells[7] if len(cells) > 7 else "",
        }
# Wikipedia lists these two-parters as a single row; add the second parts by hand.
PART2 = {  # prod: (part-1 prod, director, writer, airdate)
    "207": ("208", "Cliff Bole", "Story by: Rick Berman & Michael Piller Teleplay by: Michael Piller", "1991-11-11"),
    "237": ("236", "Les Landau", "Frank Abatemarco", "1992-12-21"),
    "243": ("242", "Dan Curry", "René Echevarria", "1993-03-01"),
    "257": ("256", "Alexander Singer", "Story by: Naren Shankar Teleplay by: Ronald D. Moore", "1993-10-18"),
}
for prod, (p1, director, writer, date) in PART2.items():
    a = meta[p1]
    meta[prod] = {**a, "overall": [a["overall"][0] + 1], "episode_in_season": [a["episode_in_season"][0] + 1],
                  "code": f"S{a['season']:02d}E{a['episode_in_season'][0]+1:02d}", "title_wiki": a["title_wiki"] + ", Part II",
                  "director": director, "writer": writer, "airdate_iso": date, "viewers_millions": ""}
    meta[p1] = {**a, "title_wiki": a["title_wiki"] + ", Part I"}
# The finale is a double-length episode counted as 177-178 but listed under one production number.
meta["277"].update({"overall": [177, 178], "episode_in_season": [25, 26], "code": "S07E25-E26"})
import sys; sys.path.insert(0, str(ROOT / "scripts")); from provenance import record; record("metadata", source=URL, episodes=len(meta))
(ROOT / "data" / "metadata.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
eps = {e["prod"] for e in json.load(open(ROOT / "data" / "episodes.json"))}
print(len(meta), "episodes from Wikipedia;", "missing:", sorted(eps - set(meta)), "extra:", sorted(set(meta) - eps))
