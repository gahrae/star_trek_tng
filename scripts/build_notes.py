#!/usr/bin/env python3
"""Build the notes from transcripts + Wikipedia metadata + the curated data modules.

Reads   data/episodes.json, data/metadata.json, data/text/*.txt, scripts/curated_*.py
Writes  data/characters.json, data/scenes.json and everything under notes/
"""
import json, re, collections, pathlib, sys, itertools
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from curated_episodes import EPISODES, ARCS, ARC_GROUPS, LINK_NOTES
from curated_characters import FACTS, PROFILES, GUESTS, ENTITIES, CATCHPHRASES, SPLIT, GUEST_FACTS

NOTES = ROOT / "notes"
for d in ("characters", "episodes", "locations"): (NOTES / d).mkdir(parents=True, exist_ok=True)
eps = json.load(open(ROOT / "data" / "episodes.json"))
meta = json.load(open(ROOT / "data" / "metadata.json"))
by_prod = {e["prod"]: e for e in eps}
for e in eps: e.update(meta[e["prod"]])
order = {e["prod"]: i for i, e in enumerate(eps)}          # broadcast order

# Stardates: the fan transcripts occasionally misread a digit; Memory Alpha's season tables are used where they differ.
ma_stardate = {}
try:
    from bs4 import BeautifulSoup
    for n in range(1, 8):
        soup_ = BeautifulSoup(json.load(open(ROOT / "data" / "ma" / f"season{n}.json"))["parse"]["text"]["*"], "html.parser")
        for tr in soup_.find("table").find_all("tr"):
            c = [x.get_text(" ", strip=True) for x in tr.find_all(["th", "td"])]
            if len(c) >= 5 and re.search(r"-(\d{3})$", c[3]):
                m = re.match(r"\d{5}(?:\.\d+)?", c[4])
                if m: ma_stardate["101" if c[3].endswith("941") else c[3][-3:]] = m.group()
except Exception as ex:
    print("Memory Alpha stardates unavailable:", ex)
for e in eps:
    e["stardate_transcript"] = e["stardate"]
    ma = ma_stardate.get(e["prod"])
    if ma and e["stardate"] and re.fullmatch(r"[\d.]+", e["stardate"]) and abs(float(ma) - float(e["stardate"])) >= 0.05: e["stardate"] = ma
    elif ma and not re.fullmatch(r"[\d.]+", e["stardate"] or ""): e["stardate"] = ma
json.dump({e["prod"]: e["stardate"] for e in eps}, open(ROOT / "data" / "stardates.json", "w"), indent=1)

SPEAKER = re.compile(r"^([A-Z][A-Z0-9 .'\-]{0,30}?)(?:\s\[[^\]]+\])?:\s")
SCENE = re.compile(r"^\[(.+)\]$")
LOG = re.compile(r"^(?:[A-Z][\w']*(?:'s)? )?(?:[Pp]ersonal |[Mm]edical |[Ss]hip's |[Ss]cience |[Ss]ecurity |[Ee]ngineering |[Ss]econd |[Ff]irst |[Aa]cting |[Cc]hief )*[Oo]fficer's [Ll]og|^(?:Captain's|First Officer's|First officer's|Ship's|Medical|Science|Personal|Chief Medical Officer's|Chief Engineer's|Acting Captain's|Second Officer's|Second officer's|Engineering|Security) (?:[Pp]ersonal )?[Ll]og\b")
ALIASES = {"GEORDI": "LAFORGE", "BEVERLY": "CRUSHER", "ALYSSA": "OGAWA", "PIKER": "RIKER"}
GENERIC_RE = re.compile(r"^(?:COMPUTER|CREW(?:MAN|WOMAN)|ENSIGN|CHIEF|MAN|WOMAN|MEDIC|NURSE|SECURITY|HELM|ALL|BOTH|VOICES?|WAITER|WAITRESS|BOY|GIRL|GUARD|DOCTOR|BORG|ROMULAN|KLINGON|CARDASSIAN|FERENGI|VULCAN|ALIEN|SOLDIER|OFFICER|STARBASE|PILOT|SCIENTIST|TEACHER|ENGINEER|BARMAN|BARTENDER|CROWD|POLICEMAN|BELLBOY|TROOPER|TECHNICIAN|CONN|OPS|TACTICAL|ANNOUNCER|CHILD|CHILDREN|OTHERS|EVERYONE|CAPTAIN|ADMIRAL|COMMANDER|LIEUTENANT|CADET|CROUPIER|DEALER|GAMBLER|SINGER|PATIENT|VISITOR|DRIVER|REPORTER|OLD MAN|OLD WOMAN|YOUNG MAN|YOUNG WOMAN|MINER|FARMER|VILLAGER|MOTHER|FATHER|SON|DAUGHTER|WIFE|HUSBAND)(?: \d+)?$")
REGULARS = ["PICARD", "RIKER", "DATA", "LAFORGE", "WORF", "CRUSHER", "TROI", "WESLEY", "TASHA", "PULASKI", "GUINAN", "O'BRIEN"]
SHORT = {"PICARD": "Picard", "RIKER": "Riker", "DATA": "Data", "LAFORGE": "La Forge", "WORF": "Worf", "CRUSHER": "Crusher", "TROI": "Troi", "WESLEY": "Wesley", "TASHA": "Yar", "PULASKI": "Pulaski", "GUINAN": "Guinan", "O'BRIEN": "O'Brien"}

# How the main and recurring cast are referred to in stage directions (possessives excluded).
NAME_FORMS = {
 "PICARD": r"(Picard|Jean-Luc)", "RIKER": r"Riker", "DATA": r"Data", "LAFORGE": r"(La ?Forge|Geordi)", "WORF": r"Worf",
 "CRUSHER": r"((?<!Wesley )(?<!Ensign )Crusher|Beverly)", "TROI": r"((?<!Lwaxana )(?<!Mrs )Troi|Deanna)", "WESLEY": r"(Wesley|Wes)",
 "TASHA": r"(Tasha|Yar)", "Q": r"Q", "O'BRIEN": r"(O'Brien|Miles)", "RO": r"Ro", "BARCLAY": r"(Barclay|Reg)", "OGAWA": r"(Ogawa|Alyssa)",
 "LEAH": r"(Leah|Brahms)", "SCOTT": r"(Scott|Scotty)", "K'EHLEYR": r"K'Ehleyr",
}
def proper(label): return re.sub(r"(^|['\- ])([a-z])", lambda m: m.group(1) + m.group(2).upper(), label.lower())
FORMS = {lbl: re.compile(r"\b" + NAME_FORMS.get(lbl, re.escape(proper(lbl))) + r"\b(?!'s\b)") for lbl in PROFILES}
NAME_WORDS = {lbl: set(re.findall(r"[A-Z][A-Za-z'\-]*", NAME_FORMS.get(lbl, proper(lbl)))) for lbl in PROFILES}
TITLES = {"Captain", "Commander", "Cmdr", "Lieutenant", "Lt", "Doctor", "Dr", "Counselor", "Counsellor", "Ensign", "Chief", "Admiral", "Mister", "Mr",
          "Mrs", "Ms", "Ambassador", "Professor", "Nurse", "Acting", "Young", "Little", "Old", "Number", "Locutus", "Kamin", "Cadet", "Crewman", "Mum", "Mother", "Father"}
def present_in(text, lbl):
    """True if the character's name occurs as itself, not as part of someone else's name ('Tryla Scott', 'Alexander Court')."""
    for m in FORMS[lbl].finditer(text):
        before = re.search(r"([A-Za-z'\-]+)\s+$", text[:m.start()]); after = re.match(r"\s+([A-Z][a-z'\-]+)", text[m.end():])
        bw = before.group(1) if before else ""; aw = after.group(1) if after else ""
        if bw and bw[0].isupper() and bw not in TITLES and bw not in NAME_WORDS[lbl]: continue
        if aw and aw not in NAME_WORDS[lbl]: continue
        return True
    return False
# Cast credits name characters differently from the transcript labels.
ROLE_ALIASES = {"YAR": "TASHA", "NATASHA": "TASHA", "GEORDI": "LAFORGE", "BEVERLY": "CRUSHER", "DEANNA": "TROI", "JEAN-LUC": "PICARD",
                "MILES": "O'BRIEN", "ALYSSA": "OGAWA", "LAREN": "RO", "REGINALD": "BARCLAY", "KATHERINE": "PULASKI", "NOONIEN": "SOONG"}
FULL_ROLES = {"Thomas Riker": "RIKER 2", "Computer Voice": "COMPUTER", "Enterprise Computer": "COMPUTER"}

def canon(label, prod=None):
    if label.startswith("DATA-"): return "DATA"
    label = ALIASES.get(label, label)
    return SPLIT.get((label, prod), label)          # labels that cover different people in different episodes
def generic(label): return bool(GENERIC_RE.match(label))
def slug(label): return re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
def name_of(label):
    if label in FACTS: return FACTS[label][0]
    if label in GUESTS: return GUESTS[label][0]
    return label.title()
def ep_ref(prod, link=True):
    e = by_prod[prod]; t = f"*{e['title']}* ({e['code']})"
    return f"[{t}](../episodes/{prod}.md)" if link else t
def char_link(label, rel="characters/"):
    return f"[{name_of(label)}]({rel}{slug(label)}.md)" if label in indexed else name_of(label)

# ---------------------------------------------------------------- parse transcripts
scenes_by_ep = {}; logs_by_ep = {}; lines_by_ep = {}; entity_hits = collections.defaultdict(collections.Counter)
phrase_hits = collections.defaultdict(collections.Counter); dialogue_by_ep = {}
ENT_RE = [(n, c, re.compile(rx)) for n, c, rx in ENTITIES]
PH_RE = [(n, re.compile(rx), who) for n, rx, who in CATCHPHRASES]
for e in eps:
    text = (ROOT / "data" / "text" / f"{e['prod']}.txt").read_text(encoding="utf-8").split("\n")
    scenes = []; cur = {"location": "(untitled)", "speakers": collections.Counter(), "stage": []}; logs = []; in_log = False
    counter = collections.Counter(); dialogue = []; depth = 0
    for line in text:
        if (m := SCENE.match(line)):
            if cur["speakers"] or scenes: scenes.append(cur)
            cur = {"location": m.group(1).strip(), "speakers": collections.Counter(), "stage": []}; in_log = False; depth = 0; continue
        if SPEAKER.match(line): depth = 0          # a new dialogue line closes any unbalanced direction
        buf = []
        for ch in line:                            # text inside parentheses = stage directions (may span lines)
            if ch == "(": depth += 1
            elif ch == ")": depth = max(0, depth - 1)
            elif depth > 0: buf.append(ch)
        if buf: cur["stage"].append("".join(buf))
        if line.startswith("("): in_log = False; continue
        if (m := SPEAKER.match(line)):
            lbl = canon(m.group(1).strip(), e["prod"]); cur["speakers"][lbl] += 1; counter[lbl] += 1; in_log = False
            dialogue.append((lbl, line[m.end():]))
            for n, rx, who in PH_RE:
                if (who is None or who == lbl) and (rx.search(line) if rx.pattern.startswith("^") else rx.search(line[m.end():])): phrase_hits[n][e["prod"]] += 1
            continue
        if LOG.match(line): logs.append(line); in_log = True; continue
        if in_log: logs[-1] += " " + line
    scenes.append(cur)
    for s in scenes:
        s["speakers"] = dict(s["speakers"]); st = " ".join(s.pop("stage"))
        s["present"] = sorted(l for l in FORMS if present_in(st, l))   # named in directions
        s["stage_text"] = st
    scenes_by_ep[e["prod"]] = scenes; logs_by_ep[e["prod"]] = logs; lines_by_ep[e["prod"]] = counter; dialogue_by_ep[e["prod"]] = dialogue
    hdr = next((i for i, l in enumerate(text[:12]) if l.startswith("Original Airdate")), -1)
    full = "\n".join(text[hdr + 1:])            # skip the title header, which repeats the episode name
    for n, c, rx in ENT_RE:
        k = len(rx.findall(full))
        if k: entity_hits[n][e["prod"]] = k
json.dump(scenes_by_ep, open(ROOT / "data" / "scenes.json", "w"), indent=1)

# ---------------------------------------------------------------- aggregate characters
chars = collections.defaultdict(lambda: {"episodes": [], "lines": 0, "by_season": collections.Counter()})
for e in eps:
    for lbl, n in lines_by_ep[e["prod"]].items():
        chars[lbl]["episodes"].append({"prod": e["prod"], "code": e["code"], "title": e["title"], "season": e["season"], "lines": n})
        chars[lbl]["lines"] += n; chars[lbl]["by_season"][e["season"]] += n
json.dump(chars, open(ROOT / "data" / "characters.json", "w"), indent=1)
presence = {}   # prod -> label -> scenes speaking / scenes present in directions but silent
for e in eps:
    d = collections.defaultdict(lambda: {"speaking_scenes": 0, "silent_scenes": 0})
    for s in scenes_by_ep[e["prod"]]:
        for l in s["speakers"]: d[l]["speaking_scenes"] += 1
        for l in s["present"]:
            if l not in s["speakers"]: d[l]["silent_scenes"] += 1
    presence[e["prod"]] = dict(d)
json.dump(presence, open(ROOT / "data" / "presence.json", "w"), indent=1)

cast_path = ROOT / "data" / "cast.json"
cast = json.load(open(cast_path)) if cast_path.exists() else {}
def match_role(role, prod):
    full = role.split("(")[0].strip()
    if full in FULL_ROLES: return FULL_ROLES[full]
    toks = [t for t in (re.sub(r"[^A-Z'\-]", "", t.upper()) for t in full.replace(".", " ").split()) if t]
    for labels in (set(lines_by_ep[prod]) | set(presence[prod]), set(PROFILES)):   # this episode's speakers, then the regular cast
        for i, t in enumerate(toks):
            t2 = ROLE_ALIASES.get(t, t)
            if t2 in labels: return t2
            if i + 1 < len(toks):
                for joined in (t + toks[i + 1], t + " " + toks[i + 1]):
                    if joined in labels: return joined
    return None
actors_of = collections.defaultdict(collections.Counter)       # label -> actor -> episodes
actor_roles = collections.defaultdict(lambda: {"roles": collections.defaultdict(set), "episodes": set(), "credited": collections.defaultdict(set), "as": {}})
for prod, entries in cast.items():
    for c in entries:
        c["label"] = match_role(c["role"], prod)
        if c["label"]: actors_of[c["label"]][c["actor"]] += 1
        key = c["label"] or c["role"]; ar = actor_roles[c["actor"]]
        ar["roles"][key].add(prod); ar["episodes"].add(prod); ar["as"][key] = c["role"]
        if "ncredited" not in c["credit"]: ar["credited"][key].add(prod)
NOT_PRESENT = re.compile(r"credit only|stock footage|archive footage|deleted scene|picture|photograph", re.I)
nonspeak = collections.defaultdict(dict)        # label -> prod -> {sources}: present in the episode without dialogue
for e in eps:
    for l, v in presence[e["prod"]].items():
        if v["silent_scenes"] and not lines_by_ep[e["prod"]].get(l): nonspeak[l].setdefault(e["prod"], set()).add("stage directions")
for prod, entries in cast.items():
    for c in entries:
        l = c["label"]
        if l and not generic(l) and not NOT_PRESENT.search(c["role"]) and not lines_by_ep[prod].get(l): nonspeak[l].setdefault(prod, set()).add("cast list")
ns_by_ep = collections.defaultdict(dict)
for l, d in nonspeak.items():
    for prod, src in d.items(): ns_by_ep[prod][l] = src
appearances = {l: {e["prod"]: {"lines": e["lines"]} for e in d["episodes"]} for l, d in chars.items()}
for l, d in nonspeak.items():
    for prod, src in d.items(): appearances.setdefault(l, {})[prod] = {"lines": 0, "sources": sorted(src)}
json.dump(appearances, open(ROOT / "data" / "appearances.json", "w"))
def played_by(lbl):
    if lbl in PROFILES: return PROFILES[lbl]["actor"]
    return ", ".join(a for a, _ in actors_of[lbl].most_common(3)) if actors_of.get(lbl) else ""

indexed = {lbl for lbl, d in chars.items() if not generic(lbl) and (len(d["episodes"]) >= 2 or d["lines"] >= 40 or lbl in FACTS or lbl in GUESTS)}
coapp = collections.Counter()          # scene-level co-appearance of named characters
for prod, scenes in scenes_by_ep.items():
    for s in scenes:
        named = sorted(l for l in s["speakers"] if l in indexed)
        for a, b in itertools.combinations(named, 2): coapp[(a, b)] += 1
def partners(lbl, k=8):
    out = [(b if a == lbl else a, n) for (a, b), n in coapp.items() if lbl in (a, b)]
    return sorted(out, key=lambda x: -x[1])[:k]

# ---------------------------------------------------------------- notes: episodes
with open(NOTES / "episodes.md", "w", encoding="utf-8") as f:
    f.write("# Episodes\n\n176 transcript entries covering all 178 broadcast episodes (double-length episodes are one entry). "
            "Listed in broadcast order. Director and writer credits come from Wikipedia; synopses and arc tags come from the curated data files, written from each episode's transcript. "
            "Click a title for the episode note.\n")
    cur = None
    for e in eps:
        if e["season"] != cur:
            cur = e["season"]; f.write(f"\n## Season {cur}\n\n| Code | Title | Aired | Director | Writer | Arcs | Synopsis |\n|---|---|---|---|---|---|---|\n")
        syn, arcs, links = EPISODES[e["prod"]]
        f.write(f"| {e['code']} | [{e['title']}](episodes/{e['prod']}.md) | {e['airdate_iso']} | {e['director']} | {e['writer']} | {', '.join(arcs)} | {syn} |\n")

for e in eps:
    prod = e["prod"]; syn, arcs, links = EPISODES[prod]
    back = [p for p, (_, _, l) in EPISODES.items() if prod in l and p not in links]
    scenes = scenes_by_ep[prod]; locs = collections.Counter(s["location"] for s in scenes)
    with open(NOTES / "episodes" / f"{prod}.md", "w", encoding="utf-8") as f:
        f.write(f"# {e['title']}\n\n")
        i = order[prod]; pv = eps[i - 1] if i else None; nx = eps[i + 1] if i + 1 < len(eps) else None
        f.write((f"Previous: [{pv['title']}]({pv['prod']}.md) ({pv['code']})" if pv else "First episode") + " · " + (f"Next: [{nx['title']}]({nx['prod']}.md) ({nx['code']})" if nx else "Last episode") + "\n\n")
        f.write(f"| | |\n|---|---|\n| Code | {e['code']} (episode {', '.join(map(str, e['overall']))} overall) |\n"
                f"| Aired | {e['airdate_iso']} |\n| Stardate | {e['stardate'] or 'none given'}" + (f" (the transcript reads {e['stardate_transcript']}; Memory Alpha's value is used)" if e['stardate_transcript'] and e['stardate_transcript'] != e['stardate'] else "") + f" |\n| Director | {e['director']} |\n| Writer | {e['writer']} |\n"
                f"| Arcs | {', '.join(f'[{a}](../arcs.md#{slug(a)})' for a in arcs)} |\n| Transcript | `data/text/{prod}.txt` |\n\n")
        f.write(f"## Synopsis\n\n{syn}\n\n")
        if links or back:
            f.write("## Continuity\n\n")
            for p in sorted(links, key=order.get):
                note = LINK_NOTES.get((prod, p)) or LINK_NOTES.get((p, prod), "")
                f.write(f"- {'Follows' if order[p] < order[prod] else 'Leads to'} {ep_ref(p)}" + (f": {note}" if note else "") + "\n")
            for p in sorted(back, key=order.get):
                note = LINK_NOTES.get((p, prod), "")
                f.write(f"- Referenced by {ep_ref(p)}" + (f": {note}" if note else "") + "\n")
            f.write("\n")
        if logs_by_ep[prod]:
            f.write("## Log entries\n\n" + "".join(f"> {l}\n\n" for l in logs_by_ep[prod]))
        f.write(f"## Characters ({len(lines_by_ep[prod])} speaking)\n\n| Character | Lines |\n|---|---:|\n")
        for lbl, n in lines_by_ep[prod].most_common():
            f.write(f"| {char_link(lbl, '../characters/')} | {n} |\n")
        if ns_by_ep.get(prod):
            f.write("\n## Present without dialogue\n\nCharacters with no lines who appear according to the cast list or the stage directions.\n\n")
            for l, src in sorted(ns_by_ep[prod].items(), key=lambda x: name_of(x[0])):
                if l in indexed: f.write(f"- {char_link(l, '../characters/')} ({', '.join(sorted(src))})\n")
        f.write(f"\n## Locations ({len(scenes)} scenes)\n\n| Location | Scenes |\n|---|---:|\n")
        for loc, n in locs.most_common(): f.write(f"| {loc} | {n} |\n")
        if cast.get(prod):
            f.write("\n## Cast\n\nFrom Memory Alpha. Linked where the credit could be matched to a transcript label.\n")
            for heading in dict.fromkeys(c["credit"] for c in cast[prod]):
                f.write(f"\n**{heading}**\n\n")
                for c in (x for x in cast[prod] if x["credit"] == heading):
                    link = f" ({char_link(c['label'], '../characters/')})" if c["label"] in indexed else ""
                    f.write(f"- {c['actor']} as {c['role']}{link}\n")

# ---------------------------------------------------------------- notes: characters
rows = sorted(indexed, key=lambda l: (-len(chars[l]["episodes"]), -chars[l]["lines"], name_of(l)))
with open(NOTES / "character_index.md", "w", encoding="utf-8") as f:
    f.write("# Character index\n\nEvery named speaking character in two or more episodes, plus notable single-episode characters. "
            "Line counts are dialogue lines in the transcripts; a character present but silent is not counted. "
            "'Non-speaking' counts further episodes where the character appears without dialogue, according to the cast list or the stage directions. "
            "Profile fields come from the curated data files where present; actors come from Memory Alpha credits.\n\n| Character | Episodes | Non-speaking | Lines | Played by | Species | Affiliation | Status | First | Last |\n|---|---:|---:|---:|---|---|---|---|---|---|\n")
    for lbl in rows:
        d = chars[lbl]; p = PROFILES.get(lbl, {})
        f.write(f"| {char_link(lbl)} | {len(d['episodes'])} | {len(nonspeak.get(lbl, {})) or ''} | {d['lines']} | {played_by(lbl)} | {p.get('species','')} | {p.get('affiliation','')} | {p.get('status','')} | {d['episodes'][0]['title']} | {d['episodes'][-1]['title']} |\n")

for lbl in rows:
    d = chars[lbl]; p = PROFILES.get(lbl); name = name_of(lbl)
    with open(NOTES / "characters" / f"{slug(lbl)}.md", "w", encoding="utf-8") as f:
        f.write(f"# {name}\n\n")
        sil = sorted(nonspeak.get(lbl, {}).items(), key=lambda x: order[x[0]])
        f.write(f"| | |\n|---|---|\n| Transcript label | `{lbl}` |\n| Episodes | {len(d['episodes'])} of 176 speaking" + (f", plus {len(sil)} non-speaking" if sil else "") + f" |\n| Dialogue lines | {d['lines']} |\n")
        if played_by(lbl): f.write(f"| Played by | {played_by(lbl)} |\n")
        if p:
            f.write(f"| Species | {p['species']} |\n| Affiliation | {p['affiliation']} |\n| Status | {p['status']} |\n")
        f.write("\n## Key facts\n\n")
        if lbl in FACTS: f.write("".join(f"- {x}\n" for x in FACTS[lbl][1]))
        elif lbl in GUEST_FACTS: f.write("".join(f"- {x}\n" for x in GUEST_FACTS[lbl]))
        elif lbl in GUESTS: f.write(f"- {GUESTS[lbl][1]}\n")
        else: f.write("- (not yet written)\n")
        if p and p["ranks"]:
            f.write("\n## Rank and role timeline\n\n| From | Rank / role |\n|---|---|\n")
            for prod, r in p["ranks"]: f.write(f"| {ep_ref(prod)} | {r} |\n")
        if p and p["relationships"]:
            f.write("\n## Relationships\n\n")
            for other, kind in p["relationships"]: f.write(f"- {char_link(other, '')}: {kind}\n")
        inbound = [(o, k) for o, q in PROFILES.items() if o != lbl for r, k in q["relationships"] if r == lbl and not (p and any(r2 == o for r2, _ in p["relationships"]))]
        if inbound:
            f.write("\n" if not (p and p["relationships"]) else "")
            if not (p and p["relationships"]): f.write("## Relationships\n\n")
            for o, k in inbound: f.write(f"- {char_link(o, '')} lists this character as: {k}\n")
        pt = partners(lbl)
        if pt:
            f.write("\n## Most scenes shared with\n\n| Character | Scenes |\n|---|---:|\n")
            for o, n in pt: f.write(f"| {char_link(o, '')} | {n} |\n")
        if len(d["episodes"]) > 3:
            f.write("\n## Lines per season\n\n| " + " | ".join(f"S{s}" for s in range(1, 8)) + " |\n|" + "---:|" * 7 + "\n| " + " | ".join(str(d["by_season"].get(s, 0)) for s in range(1, 8)) + " |\n")
        f.write("\n## Appearances\n\n| Code | Episode | Lines |\n|---|---|---:|\n")
        for e in d["episodes"]: f.write(f"| {e['code']} | [{e['title']}](../episodes/{e['prod']}.md) | {e['lines']} |\n")
        if sil:
            f.write("\n## Non-speaking appearances\n\nEpisodes where the character appears without dialogue, and how we know.\n\n| Code | Episode | Source |\n|---|---|---|\n")
            for prod, src in sil: f.write(f"| {by_prod[prod]['code']} | [{by_prod[prod]['title']}](../episodes/{prod}.md) | {', '.join(sorted(src))} |\n")
        top = sorted(d["episodes"], key=lambda e: -e["lines"])[:5]
        if len(d["episodes"]) > 5:
            f.write("\n## Heaviest episodes\n\n" + "".join(f"- {ep_ref(e['prod'])}: {e['lines']} lines\n" for e in top))

# ---------------------------------------------------------------- notes: arcs, continuity, relationships, co-appearance
with open(NOTES / "arcs.md", "w", encoding="utf-8") as f:
    f.write("# Story arcs and themes\n\nArc tags from the curated data files (assigned from each episode's transcript), in four groups: recurring adversaries and factions, storytelling devices, arcs centred on one character, and broader themes. "
            "Episodes are in broadcast order within each arc.\n")
    for group, arcs in ARC_GROUPS:
        f.write(f"\n## {group}\n")
        for a in arcs:
            members = [e for e in eps if a in EPISODES[e["prod"]][1]]
            f.write(f"\n### {a}\n\n{len(members)} episodes.\n\n")
            for e in members: f.write(f"- {e['code']} [{e['title']}](episodes/{e['prod']}.md): {EPISODES[e['prod']][0]}\n")

with open(NOTES / "continuity.md", "w", encoding="utf-8") as f:
    f.write("# Continuity links\n\nEpisodes that pick up threads from earlier ones, as recorded in the curated data files, in broadcast order of the later episode, with a note on what is carried forward. Notes that begin with the words Related rather than explicit mark links where the later episode does not refer back to the earlier one.\n\n"
            "| Later episode | Picks up from | What continues |\n|---|---|---|\n")
    for e in eps:
        prior = sorted([p for p in EPISODES[e["prod"]][2] if order[p] < order[e["prod"]]], key=order.get)
        for p in prior:
            f.write(f"| {e['code']} [{e['title']}](episodes/{e['prod']}.md) | {by_prod[p]['code']} [{by_prod[p]['title']}](episodes/{p}.md) | {LINK_NOTES.get((e['prod'], p), '')} |\n")

with open(NOTES / "relationships.md", "w", encoding="utf-8") as f:
    f.write("# Relationships\n\n## Curated relationships\n\nLinks between characters (family, romance, rivalry, mentorship) recorded in the curated data files, grouped by character. "
            "The [Visuals](visuals.md) page shows the same data as a graph.\n\n")
    for lbl, p in PROFILES.items():
        f.write(f"### {name_of(lbl)}\n\n" if lbl not in indexed else f"### [{name_of(lbl)}](characters/{slug(lbl)}.md)\n\n")
        for other, kind in p["relationships"]: f.write(f"- {char_link(other)}: {kind}\n")
        f.write("\n")
    f.write("\n## Most frequent scene pairings\n\nPairs of named characters who speak in the same scene most often, across the whole series.\n\n| Pair | Scenes together |\n|---|---:|\n")
    for (a, b), n in coapp.most_common(60): f.write(f"| {char_link(a)} and {char_link(b)} | {n} |\n")
    f.write("\n## Strongest pairings outside the main cast\n\n| Pair | Scenes together |\n|---|---:|\n")
    for (a, b), n in [x for x in coapp.most_common() if x[0][0] not in REGULARS and x[0][1] not in REGULARS][:40]: f.write(f"| {char_link(a)} and {char_link(b)} | {n} |\n")

with open(NOTES / "co_appearance.md", "w", encoding="utf-8") as f:
    f.write("# Co-appearance matrix\n\nNumber of scenes in which both characters speak (main and recurring cast).\n\n")
    f.write("| | " + " | ".join(SHORT[l] for l in REGULARS) + " |\n|---|" + "---:|" * len(REGULARS) + "\n")
    for a in REGULARS:
        f.write(f"| **{SHORT[a]}** | " + " | ".join("" if a == b else str(coapp.get((min(a, b), max(a, b)), 0)) for b in REGULARS) + " |\n")
    f.write("\n## Episodes shared\n\nNumber of episodes in which both characters speak.\n\n")
    epsets = {l: {e["prod"] for e in chars[l]["episodes"]} for l in REGULARS}
    f.write("| | " + " | ".join(SHORT[l] for l in REGULARS) + " |\n|---|" + "---:|" * len(REGULARS) + "\n")
    for a in REGULARS:
        f.write(f"| **{SHORT[a]}** | " + " | ".join("" if a == b else str(len(epsets[a] & epsets[b])) for b in REGULARS) + " |\n")

# ---------------------------------------------------------------- notes: locations, entities, stats
# scene headings vary in capitalisation ("Ten Forward" / "Ten forward"); merge by lower-case key, display the commonest spelling
spellings = collections.defaultdict(collections.Counter)
for e in eps:
    for s in scenes_by_ep[e["prod"]]:
        raw = re.sub(r"\s+", " ", s["location"]).strip(); spellings[raw.lower()][raw[0].upper() + raw[1:]] += 1
LOC_NAME = {k: v.most_common(1)[0][0] for k, v in spellings.items()}
def loc_name(raw): return LOC_NAME[re.sub(r"\s+", " ", raw).strip().lower()]
loc_total = collections.Counter(); loc_season = collections.defaultdict(collections.Counter); loc_eps = collections.defaultdict(set)
for e in eps:
    for s in scenes_by_ep[e["prod"]]:
        L = loc_name(s["location"])
        loc_total[L] += 1; loc_season[L][e["season"]] += 1; loc_eps[L].add(e["prod"])
loc_speakers = collections.defaultdict(collections.Counter); loc_ep_scenes = collections.defaultdict(collections.Counter)
for e in eps:
    for s in scenes_by_ep[e["prod"]]:
        L = loc_name(s["location"])
        loc_ep_scenes[L][e["prod"]] += 1
        for l, n in s["speakers"].items():
            if not generic(l): loc_speakers[L][l] += n
loc_pages = {L for L, n in loc_total.items() if n >= 8}
for L in loc_pages:
    with open(NOTES / "locations" / f"{slug(L)}.md", "w", encoding="utf-8") as f:
        f.write(f"# {L}\n\n{loc_total[L]} scenes in {len(loc_eps[L])} episodes.\n\n")
        f.write("## Who speaks here\n\n| Character | Lines |\n|---|---:|\n")
        for l, n in loc_speakers[L].most_common(15): f.write(f"| {char_link(l, '../characters/')} | {n} |\n")
        f.write("\n## Episodes\n\n| Code | Episode | Scenes |\n|---|---|---:|\n")
        for prod, n in sorted(loc_ep_scenes[L].items(), key=lambda x: order[x[0]]): f.write(f"| {by_prod[prod]['code']} | [{by_prod[prod]['title']}](../episodes/{prod}.md) | {n} |\n")
with open(NOTES / "locations.md", "w", encoding="utf-8") as f:
    n_scenes = sum(loc_total.values())
    f.write(f"# Locations\n\nScene headings from the transcripts: {n_scenes} scenes across 176 episodes, {len(loc_total)} distinct headings (spelling as transcribed). "
            "The 80 most used, with scenes per season.\n\n| Location | Scenes | Episodes | " + " | ".join(f"S{s}" for s in range(1, 8)) + " |\n|---|---:|---:|" + "---:|" * 7 + "\n")
    for L, n in loc_total.most_common(80):
        name = f"[{L}](locations/{slug(L)}.md)" if L in loc_pages else L
        f.write(f"| {name} | {n} | {len(loc_eps[L])} | " + " | ".join(str(loc_season[L].get(s, 0)) for s in range(1, 8)) + " |\n")

with open(NOTES / "entities.md", "w", encoding="utf-8") as f:
    f.write("# Ships, places, organisations and technology\n\nMentions in transcript text (dialogue, logs and stage directions) for a curated list of recurring entities. "
            "'Episodes' is how many episodes mention it at least once.\n")
    for cat in ["ship", "place", "organisation", "technology", "concept", "culture"]:
        f.write(f"\n## {cat.title()}s\n\n| Entity | Mentions | Episodes | Most mentions in |\n|---|---:|---:|---|\n")
        for n, c, _ in sorted([x for x in ENTITIES if x[1] == cat], key=lambda x: -sum(entity_hits[x[0]].values())):
            h = entity_hits[n]; top = h.most_common(3)
            f.write(f"| {n} | {sum(h.values())} | {len(h)} | " + ", ".join(f"[{by_prod[p]['title']}](episodes/{p}.md) ({k})" for p, k in top) + " |\n")

with open(NOTES / "stats.md", "w", encoding="utf-8") as f:
    f.write("# Statistics\n\n## Episodes, scenes and dialogue per season\n\n| Season | Entries | Scenes | Scenes per entry | Dialogue lines | Speaking characters |\n|---|---:|---:|---:|---:|---:|\n")
    for s in range(1, 8):
        se = [e for e in eps if e["season"] == s]; sc = sum(len(scenes_by_ep[e["prod"]]) for e in se)
        dl = sum(sum(lines_by_ep[e["prod"]].values()) for e in se); sp = len({l for e in se for l in lines_by_ep[e["prod"]]})
        f.write(f"| {s} | {len(se)} | {sc} | {sc/len(se):.1f} | {dl} | {sp} |\n")
    f.write("\n## Dialogue lines per season, main and recurring cast\n\n| Character | " + " | ".join(f"S{s}" for s in range(1, 8)) + " | Total | Share of all dialogue |\n|---|" + "---:|" * 9 + "\n")
    total_lines = sum(sum(c.values()) for c in lines_by_ep.values())
    for lbl in REGULARS + ["Q", "LWAXANA", "RO", "BARCLAY", "ALEXANDER", "OGAWA", "KEIKO", "LORE", "GOWRON"]:
        d = chars[lbl]; f.write(f"| {char_link(lbl)} | " + " | ".join(str(d["by_season"].get(s, 0)) for s in range(1, 8)) + f" | {d['lines']} | {100*d['lines']/total_lines:.1f}% |\n")
    f.write("\n## Catchphrases and recurring lines\n\nCounted in dialogue lines; where a speaker is named, only that character's lines count.\n\n| Line | Speaker | Count | Episodes | Most in |\n|---|---|---:|---:|---|\n")
    for n, rx, who in CATCHPHRASES:
        h = phrase_hits[n]; top = h.most_common(2)
        f.write(f"| {n} | {name_of(who) if who else 'anyone'} | {sum(h.values())} | {len(h)} | " + ", ".join(f"[{by_prod[p]['title']}](episodes/{p}.md) ({k})" for p, k in top) + " |\n")
    f.write("\n## Longest and shortest transcripts\n\n| | Episode | Dialogue lines |\n|---|---|---:|\n")
    ranked = sorted(eps, key=lambda e: -sum(lines_by_ep[e["prod"]].values()))
    for tag, e in [("Longest", ranked[0]), ("2nd", ranked[1]), ("3rd", ranked[2]), ("Shortest", ranked[-1]), ("2nd shortest", ranked[-2])]:
        f.write(f"| {tag} | [{e['title']}](episodes/{e['prod']}.md) | {sum(lines_by_ep[e['prod']].values())} |\n")
    f.write("\n## Stardate anomalies\n\nEpisodes whose stardate is earlier than the previous episode's, in broadcast order. Stardates are Memory Alpha's where the fan transcript misreads one. "
            "Episodes without a stated stardate are skipped.\n\n| Episode | Stardate | Previous episode | Its stardate | What explains it |\n|---|---:|---|---:|---|\n")
    seq = [(e, float(e["stardate"])) for e in eps if re.fullmatch(r"[\d.]+", e["stardate"] or "")]
    for k in range(1, len(seq)):
        e, sd = seq[k]; pe, psd = seq[k - 1]
        if sd >= psd: continue
        if int(e["prod"]) < int(pe["prod"]): reason = "aired out of production order: this episode was made before the previous one"
        elif k + 1 < len(seq) and seq[k + 1][1] < psd and k >= 2 and psd - seq[k - 2][1] > psd - sd: reason = f"the previous episode's stardate is the one out of sequence: it jumps ahead of the episodes on either side of it"
        else:
            agree = all(ma_stardate.get(x["prod"]) and abs(float(ma_stardate[x["prod"]]) - v) < 0.05 for x, v in ((e, sd), (pe, psd)))
            reason = "none: the script's stardates were not kept in sequence" + (" (Memory Alpha lists the same two values)" if agree else "")
        if e["stardate_transcript"] != e["stardate"]: reason += f"; the transcript reads {e['stardate_transcript']}"
        f.write(f"| {e['code']} [{e['title']}](episodes/{e['prod']}.md) | {sd} | {pe['code']} [{pe['title']}](episodes/{pe['prod']}.md) | {psd} | {reason} |\n")
    f.write("\n## Most speaking characters in one episode\n\n| Episode | Speaking characters |\n|---|---:|\n")
    for e in sorted(eps, key=lambda e: -len(lines_by_ep[e["prod"]]))[:10]: f.write(f"| [{e['title']}](episodes/{e['prod']}.md) | {len(lines_by_ep[e['prod']])} |\n")

# ---------------------------------------------------------------- notes: actors
if cast:
    with open(NOTES / "actors.md", "w", encoding="utf-8") as f:
        f.write("# Actors\n\nFrom Memory Alpha cast lists (credited and uncredited). Actors with two or more roles, or five or more episodes. "
                "Roles are linked where they were matched to a transcript label.\n\n| Actor | Episodes | Roles |\n|---|---:|---|\n")
        rows_a = [(a, v) for a, v in actor_roles.items() if (len(v["roles"]) >= 2 or len(v["episodes"]) >= 5) and not a.lower().startswith("unknown")]
        for a, v in sorted(rows_a, key=lambda x: (-len(x[1]["episodes"]), x[0])):
            roles = sorted(v["roles"].items(), key=lambda r: -len(r[1]))[:8]
            def role_txt(r, ps):
                name = char_link(r) if r in indexed else name_of(r) if r in chars else r
                cred = v["as"].get(r, "")
                if r in chars and cred and cred.split("(")[0].strip().lower() != name_of(r).lower(): name += f" (credited as {cred})"
                tags = []
                if len(ps) > 1: tags.append(f"{len(ps)} episodes")
                else: tags.append(f"[{by_prod[next(iter(ps))]['title']}](episodes/{next(iter(ps))}.md)")
                if not v["credited"].get(r): tags.append("uncredited")
                return f"{name} ({', '.join(tags)})"
            txt = "; ".join(role_txt(r, ps) for r, ps in roles)
            f.write(f"| {a} | {len(v['episodes'])} | {txt} |\n")

# ---------------------------------------------------------------- notes: crew (directors and writers)
def split_names(txt):
    return [n.strip() for n in re.split(r"\s*(?:&|,|\band\b)\s*", txt) if n.strip()]
def parse_writer(credit):
    """'Story by: A & B Teleplay by: C' -> [(name, role)]; plain 'A & B' -> written."""
    parts = re.split(r"(Story by:|Teleplay by:|Written by:)", credit)
    if len(parts) == 1: return [(n, "written") for n in split_names(credit)]
    out = []; role = "written"
    for piece in parts:
        if piece in ("Story by:", "Teleplay by:", "Written by:"): role = piece.split()[0].lower(); continue
        out += [(n, role) for n in split_names(piece)]
    return out
directors = collections.defaultdict(list); writers = collections.defaultdict(lambda: {"story": [], "teleplay": [], "written": []})
for e in eps:
    for d in split_names(e["director"]): directors[d].append(e["prod"])
    for n, role in parse_writer(e["writer"]): writers[n][role].append(e["prod"])
def w_eps(w): return sorted(set(w["story"] + w["teleplay"] + w["written"]), key=order.get)
actor_names = {a for prod in cast for a in (c["actor"] for c in cast[prod])}
pairs = collections.Counter()
for e in eps:
    for d in split_names(e["director"]):
        for n in {n for n, _ in parse_writer(e["writer"])}: pairs[(d, n)] += 1
with open(NOTES / "crew.md", "w", encoding="utf-8") as f:
    f.write("# Directors and writers\n\nFrom the Wikipedia episode credits. Writer counts separate 'story by' and 'teleplay by' credits from undivided writing credits; "
            "a person credited for both story and teleplay on one episode counts once in the episode total.\n\n")
    f.write(f"## Directors\n\n{len(directors)} directors. Episodes are in broadcast order.\n\n| Director | Episodes | Seasons | Episodes directed |\n|---|---:|---|---|\n")
    for d, ps in sorted(directors.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        ps = sorted(ps, key=order.get); seasons = sorted({by_prod[p]["season"] for p in ps})
        f.write(f"| {d}{' (also in cast lists)' if d in actor_names else ''} | {len(ps)} | {', '.join(f'S{x}' for x in seasons)} | " + ", ".join(f"[{by_prod[p]['title']}](episodes/{p}.md)" for p in ps) + " |\n")
    f.write(f"\n## Writers\n\n{len(writers)} credited writers.\n\n| Writer | Episodes | Story | Teleplay | Written | Seasons | Favourite arcs |\n|---|---:|---:|---:|---:|---|---|\n")
    for n, w in sorted(writers.items(), key=lambda kv: (-len(w_eps(kv[1])), kv[0])):
        ps = w_eps(w); seasons = sorted({by_prod[p]["season"] for p in ps})
        arcs = collections.Counter(a for p in ps for a in EPISODES[p][1]).most_common(3)
        f.write(f"| {n} | {len(ps)} | {len(w['story'])} | {len(w['teleplay'])} | {len(w['written'])} | {', '.join(f'S{x}' for x in seasons)} | {', '.join(f'{a} ({k})' for a, k in arcs if k > 1)} |\n")
    f.write("\n## Writers' episodes\n\nWriters with three or more episodes.\n\n")
    for n, w in sorted(writers.items(), key=lambda kv: (-len(w_eps(kv[1])), kv[0])):
        ps = w_eps(w)
        if len(ps) < 3: continue
        f.write(f"### {n}\n\n")
        for p in ps:
            roles = [r for r in ("story", "teleplay", "written") if p in w[r]]
            f.write(f"- {by_prod[p]['code']} [{by_prod[p]['title']}](episodes/{p}.md) ({', '.join(roles)})\n")
        f.write("\n")
    f.write("## Director and writer pairings\n\nPairs who worked together on three or more episodes.\n\n| Director | Writer | Episodes |\n|---|---|---:|\n")
    for (d, n), k in sorted(pairs.items(), key=lambda kv: (-kv[1], kv[0])):   # stable on ties
        if k >= 3: f.write(f"| {d} | {n} | {k} |\n")
    f.write("\n## Credits per season\n\n| Season | Episodes | Directors | Writers | Most episodes directed | Most writing credits |\n|---|---:|---:|---:|---|---|\n")
    def top2(c): return sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[:2]   # stable on ties
    for sn in range(1, 8):
        se = [e for e in eps if e["season"] == sn]
        dc = collections.Counter(d for e in se for d in split_names(e["director"])); wc = collections.Counter(n for e in se for n in {n for n, _ in parse_writer(e["writer"])})
        f.write(f"| {sn} | {len(se)} | {len(dc)} | {len(wc)} | {', '.join(f'{d} ({k})' for d, k in top2(dc))} | {', '.join(f'{n} ({k})' for n, k in top2(wc))} |\n")

# ---------------------------------------------------------------- README
(NOTES / "README.md").write_text(f"""# Star Trek: The Next Generation notes

Built from {len(eps)} episode transcripts (fan transcriptions from Chrissie's Transcripts Site, chakoteya.net, downloaded for personal study), episode credits from Wikipedia, and curated synopses, arc tags, continuity links and character profiles from the data modules in `scripts/`.

## Start here

- [episodes.md](episodes.md): every episode by season with code, airdate, director, writer, arcs and a one-line synopsis.
- [character_index.md](character_index.md): {len(indexed)} characters with species, affiliation and status, linked to individual notes.
- [arcs.md](arcs.md): episodes grouped by storyline or theme (Borg, Klingon politics, Q, Data's humanity, and so on).
- [continuity.md](continuity.md): which episodes pick up threads from earlier ones.
- [relationships.md](relationships.md): curated relationships plus the most frequent scene pairings.
- [co_appearance.md](co_appearance.md): scene and episode co-appearance matrices for the main cast.
- [locations.md](locations.md): most used sets, by season, with a page per major location under `locations/`.
- [entities.md](entities.md): mention counts for recurring ships, places, factions and technology.
- [stats.md](stats.md): dialogue per character per season, catchphrase counts, longest and shortest episodes.
- [actors.md](actors.md): actors with multiple roles or many episodes, from Memory Alpha cast lists.
- [crew.md](crew.md): directors and writers, their episode counts, seasons, favourite arcs and pairings.

## Per-item notes

- `episodes/<prod>.md`: metadata, synopsis, continuity, every log entry, speaking characters with line counts, and scene locations.
- `characters/<slug>.md`: profile, key facts, rank timeline, relationships, most shared scenes, lines per season, full appearance list.

## Identifiers

Episodes are identified on the pages by their code (S03E15, broadcast order) and overall episode number. Two-part stories with a single transcript carry a code range (S01E01-E02). The studio production number (e.g. 163) is used only as the file name for transcripts, data and notes.

## Caveats

- Appearance counts are based on dialogue. For the main and recurring cast, episodes where the character is only named in stage directions are listed separately as silent appearances; this is a heuristic and can miss or over-count.
- Cast lists come from Memory Alpha (CC BY-NC) and are matched to transcript labels by name, which fails for some credits.
- Speaker labels follow the transcriber's spelling. A few aliases are merged (Geordi, Beverly, Alyssa, and Data's personas in *Masks*).
- Synopses, arc tags, continuity links, key facts, profiles, relationships and guest descriptions were written with Claude, an AI assistant. Each episode's synopsis and arc tags were written from its full transcript. Key facts, profiles, relationships and guest descriptions were written from general knowledge of the show and then checked against Memory Alpha and the transcripts. Each continuity link was checked against both episodes' transcripts. Portraits are picked by an automated search, so a few may be wrong. Check anything you rely on.

## Rebuilding

```
python3 scripts/fetch_transcripts.py   # downloads transcripts, skips files already present
python3 scripts/fetch_metadata.py      # credits and numbering from Wikipedia
python3 scripts/fetch_cast.py          # cast lists from Memory Alpha (skips pages already saved)
python3 scripts/build_notes.py         # everything under notes/
```

The curated content (synopses, arcs, continuity notes, profiles, relationships) lives in `scripts/curated_episodes.py` and `scripts/curated_characters.py`; edit those and rebuild.
""", encoding="utf-8")
print(f"{sum(len(v) for v in nonspeak.values())} non-speaking appearances; {sum(1 for v in cast.values() for c in v if c['label'])} of {sum(map(len, cast.values()))} cast credits matched")
print(f"{len(eps)} episodes, {len(indexed)} characters indexed, {sum(len(s) for s in scenes_by_ep.values())} scenes, {sum(len(l) for l in logs_by_ep.values())} log entries, {len(coapp)} co-appearance pairs")
