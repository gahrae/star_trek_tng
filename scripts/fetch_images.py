#!/usr/bin/env python3
"""Fetch one portrait per indexed character from Memory Alpha (lead image of the character's page).

Writes data/images/<slug>.<ext> and data/images.json: slug -> {"page", "source", "file"}.
Images are Memory Alpha's (CC BY-NC text; screenshots used there under fair use) and are for personal study only.
"""
import json, re, sys, time, pathlib, requests
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from curated_characters import FACTS, PROFILES, GUESTS
IMG = ROOT / "data" / "images"; IMG.mkdir(parents=True, exist_ok=True)
API = "https://memory-alpha.fandom.com/api.php"
S = requests.Session(); S.headers["User-Agent"] = "Mozilla/5.0 (personal study; contact gareth.stretton@gmail.com)"
DELAY = 1.0
def slug(label): return re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
def api(**params):
    for attempt in range(3):
        try:
            r = S.get(API, params={**params, "format": "json"}, timeout=30); r.raise_for_status(); time.sleep(DELAY); return r.json()
        except Exception as ex:
            print(f"  retry {attempt+1}: {ex}", file=sys.stderr); time.sleep(5)
    return {}

# Memory Alpha page titles for the profiled characters; guests are found by search.
PAGES = {"PICARD": "Jean-Luc Picard", "RIKER": "William T. Riker", "DATA": "Data", "LAFORGE": "Geordi La Forge", "WORF": "Worf", "CRUSHER": "Beverly Crusher",
 "TROI": "Deanna Troi", "WESLEY": "Wesley Crusher", "TASHA": "Natasha Yar", "PULASKI": "Katherine Pulaski", "Q": "Q", "GUINAN": "Guinan", "O'BRIEN": "Miles O'Brien",
 "LWAXANA": "Lwaxana Troi", "RO": "Ro Laren", "BARCLAY": "Reginald Barclay", "ALEXANDER": "Alexander Rozhenko", "LORE": "Lore", "GOWRON": "Gowron", "K'EHLEYR": "K'Ehleyr",
 "KURN": "Kurn", "KEIKO": "Keiko O'Brien", "OGAWA": "Alyssa Ogawa", "SELA": "Sela", "TOMALAK": "Tomalak", "HUGH": "Hugh", "VASH": "Vash", "MORIARTY": "James Moriarty (hologram)",
 "LEAH": "Leah Brahms", "SOONG": "Noonien Soong", "JELLICO": "Edward Jellico", "SHELBY": "Elizabeth Shelby", "NECHAYEV": "Alynna Nechayev", "SPOCK": "Spock", "SAREK": "Sarek", "SCOTT": "Montgomery Scott", "BRACKETT": "Ruah Brackett", "TEXAS": "Texas (character)", "TIMOTHY": "Timothy (Vico)"}
STRIP = re.compile(r"^(Captain|Commander|Lieutenant Commander|Lieutenant|Counselor|Dr|Doctor|Chief|Ensign|Nurse|Admiral|Professor|Ambassador|DaiMon|Gul|Chancellor|Proconsul|Senator|Sovereign|Commander|General|Vice Admiral)\s+", re.I)

chars = json.load(open(ROOT / "data" / "characters.json"))
labels = [l for l in chars if l in FACTS or l in GUESTS]
def display(l): return FACTS[l][0] if l in FACTS else GUESTS[l][0]
def find_page(l):
    if l in PAGES: return PAGES[l]
    name = re.sub(r"\s*\(.*?\)", "", STRIP.sub("", display(l))).strip()
    res = api(action="query", list="search", srsearch=name, srlimit=5).get("query", {}).get("search", [])
    toks = {t.lower() for t in re.findall(r"[A-Za-z']{3,}", name)}
    for r in res:
        if toks & {t.lower() for t in re.findall(r"[A-Za-z']{3,}", r["title"])} and "Unnamed" not in r["title"]: return r["title"]
    return None

existing = json.load(open(ROOT / "data" / "images.json")) if (ROOT / "data" / "images.json").exists() else {}
out = dict(existing)
TNG_YEAR = re.compile(r"\b(236[4-9]|2370)\b")
LATER = re.compile(r"\b(237[1-9]|23[89]\d|24\d\d)\b")
def tng_file(page, name):
    """Best TNG-era image file on the page: a solo portrait '<name>, <year>' with the latest TNG year, else any TNG-year file naming the character."""
    ims = [i["title"] for pg in api(action="query", prop="images", titles=page, imlimit=500).get("query", {}).get("pages", {}).values() for i in pg.get("images", [])]
    first = name.split()[-1] if name else ""
    solo = [(int(TNG_YEAR.search(t).group(1)), t) for t in ims if TNG_YEAR.search(t) and re.fullmatch(rf"File:{re.escape(name)},\s*(early |late |mid )?(236[4-9]|2370)\.(jpg|png|jpeg)", t, re.I)]
    if solo: return max(solo)[1]
    any_ = [(int(TNG_YEAR.search(t).group(1)), t) for t in ims if TNG_YEAR.search(t) and first.lower() in t.lower() and " and " not in t.lower()]
    return max(any_)[1] if any_ else None
def download(src):
    r = S.get(src, timeout=30); time.sleep(DELAY)
    if r.status_code != 200: return None, None
    ctype = r.headers.get("content-type", ""); return r.content, (".webp" if "webp" in ctype else ".png" if "png" in ctype else ".jpg")

# pass 1: resolve pages for characters we have not seen
for l in labels:
    sl = slug(l)
    if sl in out and out[sl].get("page"): continue
    t = find_page(l); print(f"{sl:18} -> {t}")
    if t: out[sl] = {"page": t}
# pass 2: prefer a TNG-era file over the page's lead image
want = {}
for sl, rec in out.items():
    if rec.get("era") == "tng" or not rec.get("page"): continue
    page = rec["page"]; name = re.sub(r"\s*\(.*?\)", "", page)
    f = tng_file(page, name)
    if f: want[sl] = f; print(f"{sl:18} TNG-era: {f}")
    elif rec.get("source") and LATER.search(rec["source"]) and not TNG_YEAR.search(rec["source"]):
        print(f"{sl:18} lead image is from a later era and no TNG-era file found; dropping"); rec.pop("file", None); rec.pop("source", None); rec["era"] = "none"
    elif rec.get("file"): rec["era"] = "lead"      # file-less records stay open for pass 3 (lead image)
items = list(want.items())
for i in range(0, len(items), 50):
    batch = items[i:i + 50]
    q = api(action="query", prop="imageinfo", iiprop="url", iiurlwidth=320, titles="|".join(f for _, f in batch))
    urls = {pg["title"]: (pg.get("imageinfo") or [{}])[0].get("thumburl") for pg in q.get("query", {}).get("pages", {}).values()}
    for sl, f in batch:
        src = urls.get(f)
        if not src: print(f"  no url for {f}"); continue
        data, ext = download(src)
        if not data: print(f"  download failed {sl}"); continue
        for old in IMG.glob(f"{sl}.*"): old.unlink()
        (IMG / f"{sl}{ext}").write_bytes(data)
        out[sl].update({"source": src, "file": f"{sl}{ext}", "era": "tng", "image_title": f})
# pass 3: lead image for anyone still without a file and not marked as dropped
need = [(sl, rec["page"]) for sl, rec in out.items() if not rec.get("file") and rec.get("era") != "none"]
for i in range(0, len(need), 40):
    batch = need[i:i + 40]
    q = api(action="query", prop="pageimages", titles="|".join(t for _, t in batch), pithumbsize=320, redirects=1)
    bytitle = {pg["title"]: pg for pg in q.get("query", {}).get("pages", {}).values()}
    redirects = {r["from"]: r["to"] for r in q.get("query", {}).get("redirects", [])}
    for sl, t in batch:
        pg = bytitle.get(redirects.get(t, t)); src = pg.get("thumbnail", {}).get("source") if pg else None
        if not src: out[sl]["era"] = "none"; continue
        if LATER.search(src) and not TNG_YEAR.search(src): out[sl]["era"] = "none"; print(f"{sl:18} lead image is from a later era; skipping"); continue
        data, ext = download(src)
        if data: (IMG / f"{sl}{ext}").write_bytes(data); out[sl].update({"source": src, "file": f"{sl}{ext}", "era": "lead"})
out = {sl: rec for sl, rec in out.items() if rec.get("file") or rec.get("page")}
(ROOT / "data" / "images.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
have = sum(1 for r in out.values() if r.get("file")); tng = sum(1 for r in out.values() if r.get("era") == "tng")
from provenance import record; record("images", source=API, characters=len(labels), images=have, tng_era=tng)
print(f"{have} images for {len(labels)} characters ({tng} TNG-era, {have - tng} lead images) -> {IMG}")
