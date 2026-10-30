#!/usr/bin/env python3
"""Download Star Trek: The Next Generation episode transcripts for personal study.

Source: http://www.chakoteya.net/NextGen/  (fan transcription site)

Outputs (relative to the project root):
  data/raw/<prod>.htm         raw HTML as served
  data/text/<prod>.txt        cleaned plain text (header + dialogue, footer stripped)
  data/episodes.json          index: production number, season, title, airdate, stardate
"""
import json, re, sys, time, pathlib
import requests
from bs4 import BeautifulSoup

BASE = "http://www.chakoteya.net/NextGen/"
ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, TXT = ROOT / "data" / "raw", ROOT / "data" / "text"
RAW.mkdir(parents=True, exist_ok=True); TXT.mkdir(parents=True, exist_ok=True)
S = requests.Session(); S.headers["User-Agent"] = "Mozilla/5.0 (personal study downloader; 1 req/s)"
DELAY = 1.0

def get(url):
    for attempt in range(3):
        try:
            r = S.get(url, timeout=30); r.raise_for_status(); return r.content
        except Exception as e:
            print(f"  retry {attempt+1} for {url}: {e}", file=sys.stderr); time.sleep(5)
    raise SystemExit(f"giving up on {url}")

def clean_text(html):
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style"]): t.decompose()
    text = soup.get_text("\n")
    lines = [re.sub(r"\s+", " ", l).strip() for l in text.split("\n")]
    lines = [l for l in lines if l]
    # drop site footer (starts at the "Star Trek ... trademarks" boilerplate)
    cut = next((i for i, l in enumerate(lines) if re.search(r"trademarks of|^<Back", l, re.I)), len(lines))
    return "\n".join(lines[:cut]) + "\n"

# Production numbers run continuously across seasons; these are the first number of each season.
SEASON_START = [(253, 7), (227, 6), (201, 5), (175, 4), (149, 3), (127, 2), (101, 1)]
def season_of(prod):
    n = int(prod)
    return next(s for start, s in SEASON_START if n >= start)

def main():
    index_html = get(BASE + "episodes.htm").decode("latin-1")
    soup = BeautifulSoup(index_html, "html.parser")
    episodes = []
    for a in soup.find_all("a", href=re.compile(r"^\d+\.htm$")):
        tr = a.find_parent("tr")
        cells = [re.sub(r"\s+", " ", c.get_text(" ", strip=True)) for c in tr.find_all("td")] if tr else []
        prod = a["href"][:-4]
        episodes.append({
            "prod": prod, "season": season_of(prod),
            "title": re.sub(r"\s+", " ", a.get_text(" ", strip=True)),
            "prod_label": cells[1] if len(cells) > 1 else prod,
            "airdate": cells[2] if len(cells) > 2 else "",
            "url": BASE + a["href"],
        })
    print(f"{len(episodes)} episodes in index")
    for i, ep in enumerate(episodes, 1):
        raw_path = RAW / f"{ep['prod']}.htm"
        if not raw_path.exists():
            raw_path.write_bytes(get(ep["url"])); time.sleep(DELAY)
        html = raw_path.read_bytes().decode("latin-1")
        text = clean_text(html)
        (TXT / f"{ep['prod']}.txt").write_text(text, encoding="utf-8")
        m = re.search(r"Stardate:\s*\n?\s*([\d.]+|Unknown)", text)
        ep["stardate"] = m.group(1) if m else ""
        ep["lines"] = text.count("\n")
        print(f"[{i:3}/{len(episodes)}] {ep['prod']} {ep['title']} ({ep['lines']} lines)")
    (ROOT / "data" / "episodes.json").write_text(json.dumps(episodes, indent=2), encoding="utf-8")
    from provenance import record; record("transcripts", source=BASE, episodes=len(episodes))
    print("done ->", ROOT / "data")

if __name__ == "__main__":
    main()
