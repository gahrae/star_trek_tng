"""Source links for the curated text: which transcripts a claim rests on.

A claim cites an episode in two ways: by naming it in italics (*The Battle*), or with an explicit
marker after the claim ({102}, or {102,103} for several). cite() strips the markers and appends the
transcript links, e.g. "(S04E02 · S03E15)".
"""
import json, re, pathlib, unicodedata
ROOT = pathlib.Path(__file__).resolve().parent.parent
_eps = json.load(open(ROOT / "data" / "episodes.json"))
_meta = json.load(open(ROOT / "data" / "metadata.json"))
CODE = {e["prod"]: _meta[e["prod"]]["code"] for e in _eps}
TITLE = {e["prod"]: e["title"] for e in _eps}

TOKEN = re.compile(r"\*([^*]+)\*|\{(\d{3}(?:,\d{3})*)\}")
MARKER = re.compile(r"\s*\{\d{3}(?:,\d{3})*\}")

def _norm(title):
    t = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()      # Ménage à Troi -> Menage a Troi
    t = re.sub(r"[^a-z0-9 ]", "", t.lower().replace("&", "and").replace("'", "")).replace("honour", "honor")
    t = re.sub(r"\s+(part\s*(\d+|i+|one|two)|ii?i?|iv)$", "", t.strip())       # "X, part 2" and "X II" -> "x"
    return re.sub(r"^the\s+", "", t).strip()

_by_title = {}
for _p in TITLE: _by_title.setdefault(_norm(TITLE[_p]), []).append(_p)

ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4}
def _part(title):
    m = re.search(r"\s(?:part\s*)?(\d+|ii?i?|iv)$", title.strip().lower().rstrip("."))
    return int(m.group(1)) if m and m.group(1).isdigit() else ROMAN.get(m.group(1)) if m else None
_by_part = {(_norm(TITLE[p]), _part(TITLE[p])): p for p in TITLE if _part(TITLE[p])}

def title_prods(title):
    """Episodes an italic title names. 'Unification I' is part 1 only; a bare 'Unification' is every part."""
    n, part = _norm(title), _part(title)
    if part and (n, part) in _by_part: return [_by_part[(n, part)]]
    return _by_title.get(n, [])

_order = {e["prod"]: i for i, e in enumerate(_eps)}         # broadcast order

def cited_groups(text, italics=True):
    """One list of episodes per citation in a claim (an italic title can name several parts), in order of appearance."""
    groups = []
    for m in TOKEN.finditer(text):
        found = m.group(2).split(",") if m.group(2) else (title_prods(m.group(1)) if italics else [])
        for p in found:
            if p not in CODE: raise ValueError(f"unknown episode {p} cited in: {text[:60]}")
        if found: groups.append(sorted(found, key=_order.get) if m.group(1) else found)
    return groups

def cited_prods(text, italics=True):
    """Episodes a claim cites, once each, in order of appearance: explicit markers always, italic titles if italics."""
    prods = []
    for g in cited_groups(text, italics):
        prods += [p for p in g if p not in prods]
    return prods

def links(prods, prefix):
    """Markdown for a source list. prefix is the relative path from the page to the repository root."""
    return " · ".join(f'[{CODE[p]}]({prefix}data/text/{p}.txt "{TITLE[p].replace(chr(34), chr(39))}")' for p in prods)

def cite(text, prefix, base=(), italics=True):
    """text without its markers, followed by links to the transcripts it cites (base first)."""
    prods = list(base) + [p for p in cited_prods(text, italics) if p not in base]
    clean = MARKER.sub("", text)
    return f'{clean} <span class="src">({links(prods, prefix)})</span>' if prods else clean

def keywords(text):
    """Distinctive words in a claim: quoted phrases, else capitalised words (not at the start of a sentence)."""
    plain = MARKER.sub("", re.sub(r"\*[^*]+\*", "", text))
    quoted = re.findall(r"'([^']{4,})'", plain)
    if quoted: return quoted
    return [w for w in re.findall(r"(?<![.;:] )(?<!^)\b([A-Z][a-z]{3,})\b", plain)]
