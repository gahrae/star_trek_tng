"""Source links for the curated text: which transcripts a claim rests on.

A claim cites a source in three ways: by naming it in italics (*The Battle*), or with an explicit
marker after the claim ({102}, or {102,103} for several). A marker can also quote the line it rests on,
{102|just too damned efficient}, and the link then goes to that line. A fact no transcript shows cites a Memory
Alpha page instead, {ma:Worf|chief of security}; the build checks the phrase is on the page (data/ma_pages/). cite() strips the markers and
appends the transcript links, e.g. "(S04E02 · S03E15)".
"""
import json, re, pathlib, unicodedata, urllib.parse
ROOT = pathlib.Path(__file__).resolve().parent.parent
_eps = json.load(open(ROOT / "data" / "episodes.json"))
_meta = json.load(open(ROOT / "data" / "metadata.json"))
CODE = {e["prod"]: _meta[e["prod"]]["code"] for e in _eps}
TITLE = {e["prod"]: e["title"] for e in _eps}

TOKEN = re.compile(r"\*([^*]+)\*|\{(\d{3}(?:,\d{3})*)(?:\|([^}]+))?\}|\{ma:([^|}]+)(?:\|([^}]+))?\}")
MARKER = re.compile(r"\s*\{(?:\d{3}(?:,\d{3})*|ma:[^|}]+)(?:\|[^}]+)?\}")
MA_TOKEN = re.compile(r"\{ma:([^|}]+)(?:\|([^}]+))?\}")

# Transcript structure; build_site.py renders the same lines, numbering each dialogue line as id="l<n>".
SPEAKER = re.compile(r"^([A-Z][A-Z0-9 .'\-]{0,30}?)(\s\[[^\]]+\])?:\s(.*)$")
LOG = re.compile(r"^(?:[A-Z][\w']*(?:'s)? )?(?:[A-Z][a-z]+ )*(?:[Oo]fficer's |[Cc]aptain's |[Ss]hip's |[Mm]edical |[Pp]ersonal )?[Ll]og\b")
_dialogue = {}
def dialogue(prod):
    """Dialogue lines of a transcript as [n, raw line number, speaker, text]; n is the site's anchor number."""
    if prod not in _dialogue:
        out, cur = [], None
        for i, raw in enumerate((ROOT / "data" / "text" / f"{prod}.txt").read_text(encoding="utf-8").split("\n")[5:], 6):
            s = raw.strip()
            if not s: continue
            if s.startswith("[") and s.endswith("]"): cur = None; continue
            m = SPEAKER.match(s)
            if m: cur = [len(out) + 1, i, m.group(1).strip(), m.group(3)]; out.append(cur); continue
            if s.startswith("(") or LOG.match(s): cur = None; continue
            if cur: cur[3] += " " + s
        _dialogue[prod] = out
    return _dialogue[prod]

def _flat(s):
    return " ".join(re.sub(r"[^a-z0-9]+", " ", unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()).split())

def locate(prod, phrase):
    """The first dialogue line of an episode containing the phrase (ignoring case and punctuation)."""
    want = _flat(phrase)
    for line in dialogue(prod):
        if want in _flat(line[3]): return line
    raise ValueError(f"{CODE[prod]} has no dialogue line containing '{phrase}'")

def anchor(prod, raw):
    """Site anchor number of the dialogue line at a raw line number."""
    for l in dialogue(prod):
        if l[1] == raw: return l[0]
    raise ValueError(f"{CODE[prod]} line {raw} is not a dialogue line, so a source link to it has no anchor")

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

def ma_slug(title): return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")

def ma_page(title, phrase=None):
    """Text of a fetched Memory Alpha page; with a phrase, raises ValueError if the page lacks it (ignoring case and punctuation)."""
    f = ROOT / "data" / "ma_pages" / f"{ma_slug(title)}.txt"
    if not f.exists(): raise ValueError(f"Memory Alpha page '{title}' not fetched (run scripts/fetch_ma_pages.py)")
    text = f.read_text(encoding="utf-8")
    if phrase and _flat(phrase) not in _flat(text): raise ValueError(f"Memory Alpha page '{title}' does not contain '{phrase}'")
    return text

def _url(u):
    """A URL safe inside a Markdown link: brackets and apostrophes encoded."""
    return u.replace("(", "%28").replace(")", "%29").replace("'", "%27")

def ma_link(title, phrase=None, titled=False):
    tip = f"Memory Alpha: {title}" + (f": {phrase}" if phrase else "")
    return f'[Memory Alpha{": " + title if titled else ""}](https://memory-alpha.fandom.com/wiki/{urllib.parse.quote(title.replace(" ", "_"), safe="_,.-:")} "{tip.replace(chr(34), chr(39))}")'

def _token(m, italics=True):
    """Episodes and quoted phrase of one token: a marker {102|phrase} or an italic title *The Battle|phrase*."""
    if m.group(4): return [], None
    if m.group(2): found, phrase = m.group(2).split(","), m.group(3)
    else:
        title, _, phrase = m.group(1).partition("|")
        found = title_prods(title) if italics else []
    return found, phrase

def cited_groups(text, italics=True):
    """One list of episodes per citation in a claim (an italic title can name several parts), in order of appearance."""
    groups = []
    for m in TOKEN.finditer(text):
        if m.group(4): ma_page(m.group(4), m.group(5))
        found, phrase = _token(m, italics)
        for p in found:
            if p not in CODE: raise ValueError(f"unknown episode {p} cited in: {text[:60]}")
        if phrase and found:
            if len(found) != 1: raise ValueError(f"a quoted line needs one episode: {text[:60]}")
            locate(found[0], phrase)
        if found: groups.append(sorted(found, key=_order.get) if m.group(1) else found)
    return groups

def cited_prods(text, italics=True):
    """Episodes a claim cites, once each, in order of appearance: explicit markers always, italic titles if italics."""
    prods = []
    for g in cited_groups(text, italics):
        prods += [p for p in g if p not in prods]
    return prods

def links(prods, prefix, line=None):
    """Markdown for a source list. prefix is the relative path from the page to the repository root; line is the
    raw line number to link to when there is one (GitHub's #L anchor; build_site.py turns it into the site's)."""
    def one(p):
        tip = TITLE[p] if not line else f"{TITLE[p]}: " + next(f"{l[2]}: {l[3]}"[:110] for l in dialogue(p) if l[1] == line)
        return f'[{CODE[p]}]({prefix}data/text/{p}.txt{f"#L{line}" if line else ""} "{tip.replace(chr(34), chr(39))}")'
    return " · ".join(one(p) for p in prods)

def cite(text, prefix, titled=False):
    """text with each citation turned into a link where it stands: after an italic title, or in brackets where a marker was.
    titled puts the page name in Memory Alpha links, for places (relationships) where it is not obvious which page is meant."""
    def sub(m):
        if m.group(4): return f' <span class="src">({ma_link(m.group(4), m.group(5), titled)})</span>'
        found, phrase = _token(m)
        if not found: return m.group(0)
        if phrase and len(found) != 1: raise ValueError(f"a quoted line needs one episode: {m.group(0)}")
        line = locate(found[0], phrase)[1] if phrase else None
        if m.group(1): return f'*{m.group(1).partition("|")[0]}* <span class="src">{links(found, prefix, line)}</span>'
        return f' <span class="src">({links(found, prefix, line)})</span>'
    out = TOKEN.sub(sub, re.sub(r"\s+(?=\{(?:\d{3}|ma:))", "", text))
    return out.replace(')</span> <span class="src">(', " · ")        # neighbouring sources share one bracket

_credits = json.load(open(ROOT / "data" / "credit_links.json"))

def airdate_links(prod, date):
    """The airdate followed by links to where it comes from: Wikipedia's page for the episode (else its season in the list) and Memory Alpha's."""
    c = _credits[prod]; w = c["wikipedia"]
    return f'{date} <span class="src">([Wikipedia]({_url(w["episode"] or w["list"])}) · [Memory Alpha]({_url(c["memory_alpha"]["episode"])}))</span>'

def credit_links(prod, text):
    """A director or writer credit with each person's Wikipedia and Memory Alpha pages after their name (only those that exist)."""
    c = _credits[prod]; wp, ma = c["wikipedia"]["people"], c["memory_alpha"]["people"]
    names = sorted((set(wp) | set(ma)) & {n for n in set(wp) | set(ma) if n in text}, key=len, reverse=True)
    stash = {}
    for i, n in enumerate(names):
        ls = ([f"[Wikipedia]({_url(wp[n])})"] if n in wp else []) + ([f"[Memory Alpha]({_url(ma[n])})"] if n in ma else [])
        if n in text: key = f"\0{i}\0"; stash[key] = f'{n} <span class="src">({" · ".join(ls)})</span>'; text = text.replace(n, key, 1)
    for key, val in stash.items(): text = text.replace(key, val)
    return text

def keywords(text):
    """Distinctive words in a claim: quoted phrases, capitalised words (not at the start of a sentence), long plain words."""
    plain = MARKER.sub("", re.sub(r"\*[^*]+\*", "", text))
    quoted = re.findall(r"(?<![A-Za-z])'([^']{4,}?)'(?![A-Za-z])", plain)
    caps = re.findall(r"(?<![.;:] )(?<!^)\b([A-Z][a-z]{3,})\b", plain)
    return quoted + caps + re.findall(r"\b([a-z]{8,})\b", plain)
