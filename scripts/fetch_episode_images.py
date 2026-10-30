#!/usr/bin/env python3
"""Fetch one screenshot per episode from Memory Alpha (lead image of the episode's page).

Writes data/episode_images/<prod>.<ext> and data/episode_images.json: prod -> {"page", "source", "file", "how"}.
Episode pages come from the cached season tables in data/ma/ (see fetch_cast.py). Where a page has no lead image,
OVERRIDES names a file to use. Screenshots are Memory Alpha's (used there under fair use) and are for personal study only.
"""
import json, re, sys, time, pathlib, requests
from bs4 import BeautifulSoup
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
IMG = ROOT / "data" / "episode_images"; IMG.mkdir(parents=True, exist_ok=True)
API = "https://memory-alpha.fandom.com/api.php"
S = requests.Session(); S.headers["User-Agent"] = "Mozilla/5.0 (personal study; contact gareth.stretton@gmail.com)"
DELAY = 1.0
WIDTH = 480
# prod -> Memory Alpha page, where the season tables don't give one
PAGES = {"277": "All Good Things... (episode)"}
# prod -> image file title to use instead of the page's lead image (filled in after review)
OVERRIDES = {}
eps = [e["prod"] for e in json.load(open(ROOT / "data" / "episodes.json"))]

def api(**params):
    for attempt in range(3):
        try:
            r = S.get(API, params={**params, "format": "json"}, timeout=30); r.raise_for_status(); time.sleep(DELAY); return r.json()
        except Exception as ex:
            print(f"  retry {attempt+1}: {ex}", file=sys.stderr); time.sleep(5)
    return {}
def download(src):
    r = S.get(src, timeout=30); time.sleep(DELAY)
    if r.status_code != 200: return None, None
    ctype = r.headers.get("content-type", "")
    return r.content, (".webp" if "webp" in ctype else ".png" if "png" in ctype else ".jpg")

pages = dict(PAGES)
for n in range(1, 8):
    soup = BeautifulSoup(json.load(open(ROOT / "data" / "ma" / f"season{n}.json"))["parse"]["text"]["*"], "html.parser")
    for tr in soup.find("table").find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if len(cells) < 4: continue
        a = cells[1].find("a", title=re.compile(r"\(episode\)$"))
        m = re.search(r"-(\d{3})$", cells[3].get_text(strip=True))
        if a and m: pages.setdefault("101" if m.group(1) == "941" else m.group(1), a["title"])
print(f"{len(pages)} pages for {len(eps)} episodes; missing: {sorted(set(eps) - set(pages))}")

out = json.load(open(ROOT / "data" / "episode_images.json")) if (ROOT / "data" / "episode_images.json").exists() else {}
todo = [p for p in eps if p in pages and not (out.get(p, {}).get("file") and out[p].get("page") == pages[p] and p not in OVERRIDES)]
print(f"{len(todo)} to fetch")
for p in todo:
    out[p] = {"page": pages[p]}
# lead images in batches
lead = [p for p in todo if p not in OVERRIDES]
for i in range(0, len(lead), 40):
    batch = lead[i:i + 40]
    q = api(action="query", prop="pageimages", titles="|".join(pages[p] for p in batch), pithumbsize=WIDTH, redirects=1)["query"]
    redirects = {r["from"]: r["to"] for r in q.get("redirects", [])}
    bytitle = {pg["title"]: pg for pg in q["pages"].values()}
    for p in batch:
        pg = bytitle.get(redirects.get(pages[p], pages[p])) or {}
        src = (pg.get("thumbnail") or {}).get("source")
        if src: out[p].update({"source": src, "image_title": "File:" + pg.get("pageimage", ""), "how": "lead"})
# overrides
for p in [p for p in todo if p in OVERRIDES]:
    q = api(action="query", prop="imageinfo", iiprop="url", iiurlwidth=WIDTH, titles=OVERRIDES[p])["query"]["pages"]
    src = next(iter(q.values())).get("imageinfo", [{}])[0].get("thumburl")
    if src: out[p].update({"source": src, "image_title": OVERRIDES[p], "how": "override"})
for p in todo:
    src = out[p].get("source")
    if not src: print(f"{p}: no image for {pages[p]}"); continue
    data, ext = download(src)
    if not data: print(f"{p}: download failed"); continue
    for old in IMG.glob(f"{p}.*"): old.unlink()
    (IMG / f"{p}{ext}").write_bytes(data); out[p]["file"] = f"{p}{ext}"
(ROOT / "data" / "episode_images.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
have = sum(1 for r in out.values() if r.get("file"))
from provenance import record; record("episode_images", source=API, episodes=len(eps), images=have)
print(f"{have} images for {len(eps)} episodes -> {IMG}; without: {[p for p in eps if not out.get(p, {}).get('file')]}")
