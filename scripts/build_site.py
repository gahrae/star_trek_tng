#!/usr/bin/env python3
"""Render notes/ into a static website under site/ (no dependencies beyond python-markdown).

  python3 scripts/build_site.py && python3 -m http.server -d site 8000   # then open http://localhost:8000
"""
import json, re, pathlib, html, shutil, collections
import markdown
ROOT = pathlib.Path(__file__).resolve().parent.parent
NOTES, SITE = ROOT / "notes", ROOT / "site"
NAV = [("README.md", "Home"), ("episodes.md", "Episodes"), ("character_index.md", "Characters"), ("arcs.md", "Arcs"),
       ("continuity.md", "Continuity"), ("relationships.md", "Relationships"), ("co_appearance.md", "Co-appearance"),
       ("locations.md", "Locations"), ("entities.md", "Entities"), ("stats.md", "Stats"), ("actors.md", "Actors"), ("crew.md", "Crew"),
       ("transcripts/index.md", "Transcripts"), ("search.md", "Search"), ("visuals.md", "Visuals")]
import sys; sys.path.insert(0, str(ROOT / "scripts"))
import site_visuals
from curated_characters import SPLIT

CSS = """
:root{--bg:#050508;--panel:#15151c;--panel2:#1d1d26;--text:#f1ece2;--muted:#b5ad9e;--line:#2d2d3a;
 --peach:#ffb77c;--lilac:#c7a3ff;--tan:#e3c48d;--sky:#9ec9ff;--rose:#ff9d9d;--mint:#9fe3c2;--amber:#f5c96a;
 --accent:var(--peach);--link:var(--sky);
 --seq1:#0d366b;--seq2:#104281;--seq3:#1c5cab;--seq4:#256abf;--seq5:#3987e5;--seq6:#6da7ec;--seq7:#9ec5f4}
td.hc{text-align:center;font-variant-numeric:tabular-nums}td.hc.deep{color:#fff}td.hc.pale{color:var(--text)}
*{box-sizing:border-box}html{scroll-padding-top:calc(var(--hdr,4.8rem) + .75rem)}
body{margin:0;background:var(--bg);color:var(--text);font:16px/1.55 "Helvetica Neue",Arial,system-ui,sans-serif}
h1,h2,h3,h4,[id]{scroll-margin-top:calc(var(--hdr,4.8rem) + .75rem)}
/* console header: a bar of rounded segments with the nav as pills */
header{position:sticky;top:0;z-index:5;background:var(--bg);padding:.6rem 1rem .5rem;display:flex;flex-wrap:wrap;gap:.35rem .5rem;align-items:center;border-bottom:3px solid var(--tan)}
header::before{content:"";display:block;width:4.2rem;height:2rem;border-radius:1rem 0 0 1rem;background:var(--peach);margin-right:.2rem}
header .brand{font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--peach);text-decoration:none;font-size:1.05rem;margin-right:.6rem}
header nav{display:flex;flex-wrap:wrap;gap:.3rem;flex-basis:100%;order:2}
header nav a{color:#0b0b0f;background:var(--lilac);text-decoration:none;padding:.22rem .7rem;border-radius:1rem;font-size:.8rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em}
header nav a:nth-child(3n+2){background:var(--tan)}header nav a:nth-child(3n){background:var(--sky)}header nav a:hover,header nav a:focus-visible{color:#0b0b0f;filter:brightness(1.12);text-decoration:underline}header nav a.active{background:var(--peach);outline:2px solid var(--text);outline-offset:1px}
header .search{margin-left:auto;position:relative;order:1}header input{background:var(--panel);color:var(--text);border:2px solid var(--tan);border-radius:1rem;padding:.35rem .8rem;width:23rem;max-width:60vw;font:inherit;font-size:.9rem}
header input::placeholder{color:var(--muted);text-transform:uppercase;font-size:.75rem;letter-spacing:.06em}
#results{position:absolute;right:0;top:2.6rem;width:26rem;max-height:60vh;overflow:auto;background:var(--panel);border:2px solid var(--tan);border-radius:12px;display:none}
#results a{display:block;padding:.4rem .6rem;color:var(--text);text-decoration:none;border-bottom:1px solid var(--line)}#results a:hover{background:var(--panel2)}#results small{color:var(--muted);display:block}
/* decorative side rail with a date readout, wide screens only */
.rail{position:fixed;left:0;top:calc(var(--hdr,4.8rem) + .6rem);bottom:.6rem;width:4.2rem;display:flex;flex-direction:column;gap:.35rem;padding:0 0 0 .5rem;z-index:1}
.rail span{display:block;border-radius:0 .5rem .5rem 0;color:#0b0b0f;font-size:.62rem;font-weight:700;text-align:right;padding:.15rem .35rem;letter-spacing:.04em;overflow:hidden;white-space:nowrap}
.rail span:nth-child(1){background:var(--tan);flex:0 0 2.6rem}.rail span:nth-child(2){background:var(--lilac);flex:1 1 auto}.rail span:nth-child(3){background:var(--sky);flex:0 0 4rem}
.rail span:nth-child(4){background:var(--peach);flex:0 0 7rem}.rail span:nth-child(5){background:var(--rose);flex:0 0 1.6rem}.rail span:nth-child(6){background:var(--tan);flex:0 0 2.2rem;border-radius:0 .5rem 1.4rem 0}
main{max-width:1100px;margin:0 auto;padding:1.5rem 1rem 4rem}@media (min-width:1500px){main{margin-left:max(5.5rem,calc((100% - 1100px)/2))}}@media (max-width:1499px){.rail{display:none}}
h1{margin-top:0;text-transform:uppercase;letter-spacing:.06em;color:var(--peach);font-size:2rem;font-weight:800}
h2{text-transform:uppercase;letter-spacing:.08em;color:var(--tan);font-size:1.15rem;margin-top:2rem;padding-left:.7rem;border-left:.55rem solid var(--tan);border-radius:.3rem 0 0 .3rem}
h3{text-transform:uppercase;letter-spacing:.06em;color:var(--lilac);font-size:.98rem}
a{color:var(--link)}a:hover{color:var(--peach)}strong{color:var(--amber)}
table{border-collapse:separate;border-spacing:0;width:100%;margin:1rem 0;font-size:.93rem}th:empty{padding:0;height:.4rem}
th,td{border:0;border-bottom:1px solid var(--line);padding:.4rem .55rem;text-align:left;vertical-align:top}
th{background:var(--tan);color:#0b0b0f;text-transform:uppercase;font-size:.75rem;letter-spacing:.06em;position:sticky;top:var(--hdr,4.8rem);z-index:2}
th:first-child{border-radius:.6rem 0 0 0}th:last-child{border-radius:0 .6rem 0 0}
tr:nth-child(even) td{background:var(--panel)}td{background:var(--bg)}td code{color:var(--mint)}
blockquote{border-left:.55rem solid var(--sky);border-radius:.3rem;background:var(--panel);margin:1rem 0;padding:.5rem 1rem;color:var(--text);font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.88rem}
blockquote::before{content:"Log entry";display:block;color:var(--sky);text-transform:uppercase;letter-spacing:.1em;font-size:.65rem;font-weight:700;margin-bottom:.2rem}
code{background:var(--panel);padding:.1rem .3rem;border-radius:4px;font-size:.9em;color:var(--mint)}pre{background:var(--panel);padding:.8rem;border-radius:8px;overflow:auto}
.filter{width:100%;margin:.5rem 0;padding:.45rem .9rem;border:2px solid var(--lilac);border-radius:1rem;background:var(--panel);color:var(--text);font:inherit}
.filter::placeholder{color:var(--muted);text-transform:uppercase;font-size:.75rem;letter-spacing:.06em}
.strip{display:grid;grid-template-columns:2.4rem repeat(28,1fr);gap:3px;align-items:center;margin:.5rem 0 1rem}.strip .cell{display:block;aspect-ratio:1;border-radius:3px;background:var(--panel2)}.strip .cell.ns{outline:2px solid var(--peach);outline-offset:-2px}.strip .cell:hover{outline:2px solid var(--text)}.strip .sl{color:var(--muted);font-size:.75rem}
figure.portrait{float:right;margin:0 0 1rem 1.5rem;max-width:220px;text-align:center;font-size:.75rem;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}
figure.portrait.still{max-width:320px}
figure.portrait img{width:100%;border-radius:12px;border:3px solid var(--tan);display:block}
/* chart panels keep the validated dark surface and palette steps */
.egowrap{--surface-1:#1a1a19;--text-primary:#f0efec;--text-secondary:#c3c2b7;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181;background:var(--surface-1);border:1px solid var(--line);border-radius:10px;padding:0;margin:1rem 0;clear:both;height:460px;min-height:260px;resize:vertical;overflow:hidden}
.egowrap canvas{width:100%;height:100%;display:block}.egosec .sub{color:var(--muted);font-size:.9rem;margin:.2rem 0 .5rem}
.egotools{display:flex;flex-wrap:wrap;gap:.5rem 1.5rem;align-items:center;margin:.3rem 0 .5rem;font-size:.9rem;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181}
.legend{display:flex;flex-wrap:wrap;gap:.4rem 1rem;font-size:.85rem;color:var(--muted)}.legend span::before{content:"";display:inline-block;width:10px;height:10px;border-radius:50%;background:var(--c);margin-right:.35rem;vertical-align:middle}
input[type=range]{accent-color:var(--peach)}select{background:var(--panel);color:var(--text);border:2px solid var(--tan);border-radius:1rem;padding:.2rem .5rem}
.tip{position:fixed;pointer-events:none;background:var(--panel);color:var(--text);border:2px solid var(--tan);border-radius:8px;padding:.35rem .55rem;font-size:.85rem;max-width:22rem;z-index:9;display:none;box-shadow:0 2px 8px rgba(0,0,0,.5)}
details.toc{background:var(--panel);border-left:.55rem solid var(--lilac);border-radius:.6rem;padding:.4rem .9rem;margin:1rem 0}details.toc summary{cursor:pointer;font-weight:700;padding:.2rem 0;text-transform:uppercase;letter-spacing:.08em;font-size:.8rem;color:var(--lilac)}
details.toc ul{columns:2;margin:.4rem 0;padding-left:1.2rem}details.toc li{break-inside:avoid;padding:.1rem 0}
details.nested>ul{columns:4;list-style:none;padding-left:0}details.nested li.grp>a{font-weight:700;color:var(--tan);text-transform:uppercase;font-size:.8rem;letter-spacing:.06em}details.nested li.grp ul{columns:1;margin:.2rem 0 .6rem;padding-left:1rem}
@media (max-width:900px){details.nested>ul{columns:2}}@media (max-width:700px){details.toc ul{columns:1}}
footer a{color:inherit;text-decoration:underline}footer{color:var(--muted);font-size:.78rem;text-align:center;padding:2rem 1rem;border-top:3px solid var(--tan);text-transform:uppercase;letter-spacing:.08em}
header .menu{display:none}
@media (max-width:700px){header{padding:.5rem .8rem}header::before{display:none}header .brand{font-size:.95rem;margin-right:.3rem}header .menu{display:inline-block;background:var(--peach);color:#0b0b0f;border:0;border-radius:1rem;padding:.3rem .7rem;font:inherit;font-size:.8rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;cursor:pointer;white-space:nowrap}header .search{flex:1;min-width:7rem;margin-left:.4rem}header input{width:100%;max-width:none}#results{width:90vw}header nav{display:none;position:absolute;left:0;right:0;top:100%;background:var(--bg);padding:.6rem .8rem .8rem;border-bottom:3px solid var(--tan);box-shadow:0 8px 16px rgba(0,0,0,.5)}header.open nav{display:flex}}
"""
JS = """
// site search over episodes and characters
let idx=null;const box=document.getElementById('q'),out=document.getElementById('results');
async function load(){if(!idx){idx=await (await fetch(ROOTP+'search.json')).json();}}
box.addEventListener('input',async()=>{await load();const q=box.value.trim().toLowerCase();if(q.length<2){out.style.display='none';return;}
 const hits=idx.filter(r=>r.t.toLowerCase().includes(q)||r.d.toLowerCase().includes(q)).slice(0,30);
 out.innerHTML=hits.map(r=>`<a href="${ROOTP}${r.p}">${r.t}<small>${r.d}</small></a>`).join('')||'<a>No matches</a>';out.style.display='block';});
document.addEventListener('click',e=>{if(!e.target.closest('.search'))out.style.display='none';});
// side-rail readout: today's date as a fan-convention stardate (1000 per year from 2323)
(()=>{const r=document.getElementById('rail-date');if(!r)return;const d=new Date(),y=d.getFullYear(),doy=(d-new Date(y,0,0))/864e5;r.textContent=y+'.'+String(Math.floor(doy)).padStart(3,'0');})();
// narrow-screen menu: the nav drops down under the header; closes on a link, outside tap or Escape
(()=>{const hd=document.querySelector('header'),b=document.getElementById('menu');const set=o=>{hd.classList.toggle('open',o);b.setAttribute('aria-expanded',o);};b.onclick=e=>{e.stopPropagation();set(!hd.classList.contains('open'));};addEventListener('click',e=>{if(hd.classList.contains('open')&&!e.target.closest('nav'))set(false);});addEventListener('keydown',e=>{if(e.key==='Escape')set(false);});})();
// measure the sticky header so table headings and anchor jumps clear it at any window width
(()=>{const hd=document.querySelector('header'),set=()=>document.documentElement.style.setProperty('--hdr',hd.offsetHeight+'px');set();addEventListener('resize',set);})();
// live filter for big tables: one box per page, applied to every large table (so a page split by season filters as a whole)
(()=>{const tables=[...document.querySelectorAll('table')].filter(t=>t.rows.length>=15);if(!tables.length)return;
 const f=document.createElement('input');f.className='filter';f.placeholder=tables.length>1?'Filter all tables...':'Filter rows...';
 const toc=document.querySelector('main details.toc');const anchor=tables.length>1?toc||document.querySelector('main h1').nextElementSibling||tables[0]:tables[0];anchor.parentNode.insertBefore(f,tables.length>1?anchor.nextSibling:anchor);
 f.addEventListener('input',()=>{const q=f.value.toLowerCase();tables.forEach(t=>{let shown=0;[...t.tBodies[0].rows].forEach(r=>{const on=r.textContent.toLowerCase().includes(q);r.style.display=on?'':'none';if(on)shown++;});
  const h=t.previousElementSibling;if(h&&/^H[2-4]$/.test(h.tagName))h.style.display=shown?'':'none';t.style.display=shown?'':'none';});});})();
"""

def shell(title, body, rel, depth):
    rootp = "../" * depth
    nav = "".join(f'<a href="{rootp}{"index" if f == "README.md" else f[:-3]}.html"{" class=active" if f == rel else ""}>{n}</a>'
                  for f, n in NAV if (NOTES / f).exists() or f in ("transcripts/index.md", "visuals.md", "search.md"))
    section = {"characters/": "character_index.md", "episodes/": "episodes.md", "locations/": "locations.md", "transcripts/": "transcripts/index.md"}
    cur = next((n for f, n in NAV if f == rel), None) or next((n for f, n in NAV if f == section.get(rel.split("/")[0] + "/")), "Menu")   # label for the narrow-screen menu toggle
    return f"""<!doctype html><html lang="en" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} - TNG notes</title><style>{CSS}</style></head><body>
<header><a class="brand" href="{rootp}index.html">TNG notes</a><button class="menu" id="menu" type="button" aria-expanded="false" aria-controls="nav">{cur} &#9662;</button><nav id="nav">{nav}</nav>
<div class="search"><input id="q" type="search" placeholder="Search episodes and characters" autocomplete="off"><div id="results"></div></div></header>
<aside class="rail" aria-hidden="true"><span>LCR</span><span id="rail-date"></span><span>176</span><span>NCC-1701-D</span><span></span><span>SEC</span></aside>
<main>{body}</main><div class="tip" id="tip"></div><footer>Unofficial fan project, not affiliated with or endorsed by Paramount. Star Trek and related marks are trademarks of Paramount Skydance Corporation.<br>Transcripts from <a href="http://www.chakoteya.net/NextGen/episodes.htm">Chrissie&#39;s Transcripts Site</a> (chakoteya.net), credits from <a href="https://en.wikipedia.org/wiki/List_of_Star_Trek:_The_Next_Generation_episodes">Wikipedia</a>, cast lists, portraits and episode screenshots from <a href="https://memory-alpha.fandom.com/">Memory Alpha</a> (CC BY-NC). For personal study.</footer>
<script>const ROOTP="{rootp}";{JS}</script>{'<script src="../ego.js"></script>' if rel.startswith("characters/") else ''}</body></html>"""

def slug(label): return re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")   # same rule as build_notes, so arc links match

def shade_matrices(body):
    """Colour numeric cells of each table by magnitude, single hue light-to-dark, scaled per table (co-appearance page)."""
    import math
    def one(tbl):
        cells = [int(v) for v in re.findall(r"<td[^>]*>(\d+)</td>", tbl)]
        if not cells: return tbl
        mx = max(cells)
        def paint(m):
            v = int(m.group(1)); k = min(6, int(math.sqrt(v / mx) * 7))
            return f'<td class="hc {"deep" if k >= 4 else "pale"}" style="background:var(--seq{k+1})" title="{v}">{v}</td>'
        return re.sub(r"<td[^>]*>(\d+)</td>", paint, tbl)
    return re.sub(r"<table>.*?</table>", lambda m: one(m.group(0)), body, flags=re.S)

def add_contents(body, nest=False):
    """Insert a collapsible table of contents after the intro when a page has several sections.
    With nest=True the h3 headings are listed under their h2 group."""
    heads = re.findall(r'<h([23]) id="([^"]+)">(.*?)</h[23]>', body)
    if not nest: heads = [h for h in heads if h[0] == "2"]
    if len(heads) < 5: return body
    strip = lambda t: re.sub("<[^>]+>", "", t)
    if nest:
        groups = []
        for lvl, i, t in heads:
            if lvl == "2": groups.append((i, t, []))
            elif groups: groups[-1][2].append((i, t))
        items = "".join(f'<li class="grp"><a href="#{i}">{strip(t)}</a><ul>' + "".join(f'<li><a href="#{j}">{strip(u)}</a></li>' for j, u in subs) + "</ul></li>" for i, t, subs in groups)
        n = sum(len(g[2]) for g in groups); cls = "toc nested"
    else:
        items = "".join(f'<li><a href="#{i}">{strip(t)}</a></li>' for _, i, t in heads); n = len(heads); cls = "toc"
    toc = f'<details class="{cls}" open><summary>Contents ({n} sections)</summary><ul>{items}</ul></details>'
    m = re.search(r"</h1>(?:\s*<p>.*?</p>)?", body, re.S)       # after the title and its first paragraph
    return body[:m.end()] + toc + body[m.end():] if m else toc + body

def render(md_path):
    rel = md_path.relative_to(NOTES); depth = len(rel.parts) - 1
    text = md_path.read_text(encoding="utf-8")
    body = markdown.markdown(text, extensions=["tables", "fenced_code", "toc"], extension_configs={"toc": {"slugify": lambda v, sep: slug(v)}})
    body = add_contents(body, nest=(rel.name == "arcs.md"))
    if rel.name == "co_appearance.md": body = shade_matrices(body)
    body = re.sub(r'href="([^"]+?)\.md(#[^"]*)?"', lambda m: f'href="{m.group(1)}.html{m.group(2) or ""}"', body)
    body = body.replace('href="README.html"', 'href="index.html"')
    body = re.sub(r"<code>data/text/(\d+)\.txt</code>", r'<a href="../transcripts/\1.html">read the transcript</a>', body)
    title = re.search(r"^# (.+)$", text, re.M); title = html.unescape(title.group(1)) if title else rel.stem
    if rel.parent.name == "characters": body = character_extras(body, rel.stem)
    if rel.parent.name == "episodes": body = episode_still(body, rel.stem, title)
    return shell(title, body, str(rel), depth)

EP_IMAGES = json.load(open(ROOT / "data" / "episode_images.json")) if (ROOT / "data" / "episode_images.json").exists() else {}
def episode_still(body, prod, title):
    """Screenshot beside the episode's metadata, from the lead image of its Memory Alpha page."""
    img = EP_IMAGES.get(prod)
    if not img or not img.get("file"): return body
    return re.sub(r"(<h1[^>]*>.*?</h1>)", lambda m: m.group(1) + f'<figure class="portrait still"><img src="../episode_images/{img["file"]}" alt="Still from the episode {html.escape(re.sub(r"<[^>]+>", "", title))}" loading="lazy">'
                  f'<figcaption>Image: <a href="https://memory-alpha.fandom.com/wiki/{html.escape(img["page"].replace(" ", "_"))}">Memory Alpha</a></figcaption></figure>', body, count=1, flags=re.S)

IMAGES = json.load(open(ROOT / "data" / "images.json")) if (ROOT / "data" / "images.json").exists() else {}
APPEAR = json.load(open(ROOT / "data" / "appearances.json")) if (ROOT / "data" / "appearances.json").exists() else {}
EPS = json.load(open(ROOT / "data" / "episodes.json")); META = json.load(open(ROOT / "data" / "metadata.json"))
def appearance_strip(label):
    """One cell per episode by season: shaded by lines spoken, outlined when present without dialogue."""
    import math
    app = APPEAR.get(label)
    if not app: return ""
    mx = max((v["lines"] for v in app.values()), default=1) or 1
    rows = collections.defaultdict(list)
    for e in EPS: rows[META[e["prod"]]["season"]].append(e)
    h = '<h2 id="appearance-strip">Appearances at a glance</h2><p class="sub">One cell per episode in broadcast order; darker means more lines, an outlined cell is an appearance without dialogue. Hover for the episode, click to open it.</p><div class="strip">'
    for sn, es in sorted(rows.items()):
        h += f'<div class="sl">S{sn}</div>'
        for e in es:
            v = app.get(e["prod"]); code = META[e["prod"]]["code"]
            if v and v["lines"]: k = min(6, int(math.sqrt(v["lines"] / mx) * 7)); cls = f'on" style="background:var(--seq{k+1})'; tip = f'{code} {e["title"]}: {v["lines"]} lines'
            elif v: cls = 'ns'; tip = f'{code} {e["title"]}: present, no dialogue ({", ".join(v.get("sources", []))})'
            else: cls = ''; tip = f'{code} {e["title"]}'
            h += f'<a class="cell {cls}" href="../episodes/{e["prod"]}.html" title="{html.escape(tip)}"></a>'
        h += '<div class="pad"></div>' * (28 - len(es))
    return h + '</div>' 
GRAPH_LABELS = set()
def character_extras(body, stem):
    """Portrait beside the profile table, and an ego relationship graph after the key facts."""
    label = re.search(r"<code>([^<]+)</code>", body); label = html.unescape(label.group(1)) if label else ""
    if IMAGES.get(stem, {}).get("file"):
        img = IMAGES[stem]
        body = re.sub(r"(<h1[^>]*>.*?</h1>)", lambda m: m.group(1) + f'<figure class="portrait"><img src="../images/{img["file"]}" alt="{html.escape(stem)}" loading="lazy">'
                      f'<figcaption>Image: <a href="https://memory-alpha.fandom.com/wiki/{html.escape(img["page"].replace(" ", "_"))}">Memory Alpha</a></figcaption></figure>', body, count=1, flags=re.S)
    strip = appearance_strip(label)
    if strip:
        body = re.sub(r"(<h2 id=\"appearances\">)", strip + r"\1", body, count=1) if 'id="appearances"' in body else body + strip
    if label in GRAPH_LABELS:
        legend = "".join(f'<span style="--c:var(--s{i+1})">{g}</span>' for i, g in enumerate(["Starfleet", "Klingon", "Romulan", "Civilian / Federation", "Other"]))
        graph = (f'<h2 id="relationship-graph">Relationship graph</h2><div class="egosec"><p class="sub">Relationships recorded in the curated data for this character, as on the Visuals page. '
                 f'Colour is affiliation. Hover a person for detail, click to open their note. Faint curves are ties between the people shown.</p>'
                 f'<div class="egotools"><div class="legend">{legend}</div><label>Height <input type="range" id="egoh" min="300" max="1400" step="20"></label></div>'
                 f'<div class="egowrap"><canvas id="ego" data-label="{html.escape(label)}"></canvas></div></div>')
        body = re.sub(r"(<h2 id=\"relationships\">)", graph + r"\1", body, count=1) if 'id="relationships"' in body else re.sub(r"(<h2 id=\"most-scenes-shared-with\">)", graph + r"\1", body, count=1)
    return body

SEARCH_BODY = r"""
<h1>Search transcripts</h1>
<p class="sub">Full-text search of every line of dialogue. All words must appear in the same line; put a phrase in quotes to match it exactly; add <code>speaker:worf</code> to limit to one character.</p>
<form id="sf" onsubmit="return false"><input id="sq" type="search" class="filter" placeholder="e.g. &quot;make it so&quot; or tea earl grey or speaker:data contractions" autofocus></form>
<p id="ss" class="sub"></p><div id="sr"></div>
<style>.hitep{margin:1.2rem 0}.hitep h3{margin:.2rem 0}.hitl{margin:.25rem 0 .25rem 1rem;font-size:.92rem}.hitl b{color:var(--sky)}.hitl mark{background:var(--amber);color:#0b0b0f;padding:0 .15rem;border-radius:3px}</style>
<script>
let IDX=null;const q=document.getElementById('sq'),ss=document.getElementById('ss'),sr=document.getElementById('sr');const LCACHE={};
const tok=t=>t.toLowerCase().match(/[a-z0-9']+/g)||[];
const esc=t=>t.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const rx=w=>w.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
async function lines(i){if(!LCACHE[i])LCACHE[i]=await (await fetch('data/lines/'+IDX.prods[i]+'.json')).json();return LCACHE[i];}
async function run(){const raw=q.value.trim();if(raw.length<2){sr.innerHTML='';ss.textContent='';return;}
 if(!IDX){ss.textContent='Loading index...';IDX=await (await fetch('data/index.json')).json();}
 let spk=null;const text=raw.replace(/speaker:(\S+)/i,(m,s)=>{spk=s.toUpperCase();return '';}).trim();
 const phrases=[...text.matchAll(/"([^"]+)"/g)].map(m=>m[1].toLowerCase());
 const allw=tok(text.replace(/"[^"]+"/g,' ')).concat(phrases.flatMap(tok)).map(w=>w.replace(/^'|'$/g,'')).filter(w=>w.length>=2);
 const words=allw.filter(w=>!IDX.stop.includes(w));           // stop words are not indexed; phrases still check them
 if(!allw.length){ss.textContent='Type at least one word.';return;}
 if(!words.length){ss.textContent='Those are all very common words; add a less common one or use a quoted phrase with it.';return;}
 const lists=words.map(w=>IDX.words[w]||[]);
 let ids=lists.reduce((a,b)=>{const st=new Set(b);return a.filter(x=>st.has(x));},lists[0]);
 const byEp={};ids.forEach(id=>{const i=Math.floor(id/4000);(byEp[i]=byEp[i]||[]).push(id%4000);});
 const eps=Object.keys(byEp).map(Number).sort((a,b)=>a-b);let shown=0,total=0,html='';
 for(const i of eps){if(shown>=40)break;const L=await lines(i);const rows=[];
  for(const n of byEp[i]){const r=L[n-1];if(!r)continue;if(spk&&r[1]!==spk)continue;const low=r[2].toLowerCase();if(phrases.some(p=>!low.includes(p)))continue;rows.push(r);}
  if(!rows.length)continue;total+=rows.length;shown++;
  html+=`<div class="hitep"><h3><a href="transcripts/${IDX.prods[i]}.html">${IDX.codes[i]} ${esc(IDX.titles[i])}</a> <span class="sub">(${rows.length})</span></h3>`;
  html+=rows.slice(0,8).map(r=>{let t=esc(r[2]);for(const w of words)t=t.replace(new RegExp('(^|[^a-z0-9])('+rx(w)+')','gi'),'$1<mark>$2</mark>');
   const who=r[1].toLowerCase().replace(/(^|[\s'-])\w/g,c=>c.toUpperCase());
   return `<p class="hitl"><b>${esc(who)}</b>: ${t} <a href="transcripts/${IDX.prods[i]}.html#l${r[0]}">&rarr;</a></p>`;}).join('')+(rows.length>8?`<p class="hitl sub">and ${rows.length-8} more in this episode</p>`:'')+'</div>';}
 ss.textContent=total?`${total} lines in ${shown} episode${shown>1?'s':''}${shown>=40?' (first 40 episodes shown)':''}`:'No matches.';sr.innerHTML=html;}
let tmr;q.addEventListener('input',()=>{clearTimeout(tmr);tmr=setTimeout(run,250);});
const u=new URLSearchParams(location.search).get('q');if(u){q.value=u;run();}
</script>
"""

SPEAKER = re.compile(r"^([A-Z][A-Z0-9 .'\-]{0,30}?)(\s\[[^\]]+\])?:\s(.*)$")
LOG = re.compile(r"^(?:[A-Z][\w']*(?:'s)? )?(?:[A-Z][a-z]+ )*(?:[Oo]fficer's |[Cc]aptain's |[Ss]hip's |[Mm]edical |[Pp]ersonal )?[Ll]og\b")
def render_transcript(e, meta, slugs, loc_pages, prev_e, next_e):
    """Mark up one cleaned transcript: scene headings (linked to location pages), speaker labels linked to character
    pages, stage directions, logs. Each dialogue line gets an id so search results can link to it. Returns (html, lines)."""
    lines = (ROOT / "data" / "text" / f"{e['prod']}.txt").read_text(encoding="utf-8").split("\n")
    out = []; para = []; mode = None; depth = 0; n = [0]; rec = []; speakers = set(); cur_key = [None]; scene = [""]
    def flush():
        nonlocal para, mode
        if para:
            t = html.escape(" ".join(para))
            if mode == "dir": out.append(f'<p class="dir">({t})</p>')
            elif mode == "log": out.append(f'<blockquote>{t}</blockquote>')
            elif mode == "line":
                text = " ".join(para[1:]); n[0] += 1
                out.append(f'<p class="line" id="l{n[0]}" data-s="{html.escape(cur_key[0] or "")}">{para[0]}{html.escape(text)}</p>')
                rec.append([n[0], cur_key[0] or "", text, scene[0]])
        para = []; mode = None
    for raw in lines[5:]:                       # skip the title/stardate header block
        line = raw.strip()
        if not line: continue
        if line.startswith("[") and line.endswith("]"):
            flush(); loc = line[1:-1].strip(); scene[0] = loc; L = loc[0].upper() + loc[1:]
            out.append(f'<h3 id="s{len(out)}">' + (f'<a href="../locations/{slug(L)}.html">{html.escape(loc)}</a>' if L in loc_pages else html.escape(loc)) + '</h3>'); continue
        m = SPEAKER.match(line)
        if m:
            flush(); lbl = m.group(1).strip(); key = {"GEORDI": "LAFORGE", "BEVERLY": "CRUSHER", "ALYSSA": "OGAWA", "PIKER": "RIKER"}.get(lbl, "DATA" if lbl.startswith("DATA-") else lbl)
            key = SPLIT.get((key, e["prod"]), key)
            tag = m.group(2) or ""; cur_key[0] = key; speakers.add(key)
            name = f'<a href="../characters/{slugs[key]}.html">{html.escape(lbl)}</a>' if key in slugs else html.escape(lbl)
            para = [f'<b>{name}</b>{html.escape(tag)}: ', m.group(3)]; mode = "line"; continue
        if line.startswith("(") :
            flush(); mode = "dir"; para = [line.strip("()")]; depth = line.count("(") - line.count(")"); continue
        if mode == "dir" and depth > 0:
            para.append(line.rstrip(")")); depth += line.count("(") - line.count(")"); continue
        if LOG.match(line):
            flush(); mode = "log"; para = [line]; continue
        if mode in ("line", "log"): para.append(line); continue
        flush(); mode = "dir"; para = [line.strip("()")]
    flush()
    opts = "".join(f'<option value="{html.escape(k)}">{html.escape(k.title())}</option>' for k in sorted(speakers))
    nav = ((f'<a href="{prev_e["prod"]}.html">&larr; {html.escape(prev_e["title"])}</a>' if prev_e else "First episode") + " &middot; " +
           (f'<a href="{next_e["prod"]}.html">{html.escape(next_e["title"])} &rarr;</a>' if next_e else "Last episode"))
    body = (f'<h1>{html.escape(e["title"])}</h1><p class="sub">{meta["code"]} &middot; aired {meta["airdate_iso"]} &middot; '
            f'<a href="../episodes/{e["prod"]}.html">episode note</a> &middot; {nav}</p>'
            f'<p class="sub">Fan transcription from <a href="{e["url"]}">Chrissie&#39;s Transcripts Site</a>, reformatted. Speaker names link to character notes; scene headings link to location pages.</p>'
            f'<div class="ttools"><label>Follow a speaker <select id="spk"><option value="">(everyone)</option>{opts}</select></label>'
            '<button id="spk-prev" type="button" title="k or left arrow">&uarr; previous line</button><button id="spk-next" type="button" title="j or right arrow">next line &darr;</button>'
            '<label><input type="checkbox" id="spk-dim"> dim others</label><span id="spk-count" class="sub"></span></div>'
            '<style>.line{margin:.35rem 0;padding:.1rem .4rem;border-radius:6px}.dir{color:var(--muted);font-style:italic;margin:.5rem 0}h3{margin:1.4rem 0 .4rem;color:var(--accent);font-size:1rem;text-transform:uppercase;letter-spacing:.04em}.sub{color:var(--muted)}'
            '.line.hit{background:var(--panel2);box-shadow:inset .3rem 0 0 var(--peach)}.line.cur{outline:2px solid var(--peach)}.dimmed .line:not(.hit){opacity:.35}.line:target{outline:2px solid var(--amber)}'
            '.ttools{display:flex;flex-wrap:wrap;gap:.5rem 1rem;align-items:center;margin:.6rem 0 1rem;font-size:.9rem}.ttools.pinned{position:sticky;top:var(--hdr,4.8rem);z-index:4;background:var(--bg);padding:.5rem 0;border-bottom:1px solid var(--line)}.ttools kbd{font:inherit;font-size:.8rem;color:var(--muted)}.ttools button{background:var(--panel);color:var(--text);border:2px solid var(--tan);border-radius:1rem;padding:.2rem .7rem;cursor:pointer;font:inherit;font-size:.85rem}</style>'
            '<div class="transcript" id="tr">' + "\n".join(out) + "</div>"
            f'<p class="sub" style="margin-top:2rem">{nav}</p>'
            '<script>(()=>{const sel=document.getElementById("spk"),tr=document.getElementById("tr"),cnt=document.getElementById("spk-count"),dim=document.getElementById("spk-dim");let hits=[],i=-1;'
            'function apply(){tr.querySelectorAll(".line").forEach(l=>l.classList.remove("hit","cur"));hits=sel.value?[...tr.querySelectorAll(`.line[data-s="${CSS.escape(sel.value)}"]`)]:[];hits.forEach(l=>l.classList.add("hit"));i=-1;count();tr.classList.toggle("dimmed",dim.checked&&!!sel.value);sel.closest(".ttools").classList.toggle("pinned",!!sel.value);}function count(){cnt.textContent=!sel.value?"":(i<0?hits.length+" lines":(i+1)+" of "+hits.length)+(hits.length?"  (j / k to step)":"");}'
            'function go(d){if(!hits.length)return;hits[i]&&hits[i].classList.remove("cur");i=(i+d+hits.length)%hits.length;hits[i].classList.add("cur");hits[i].scrollIntoView({block:"center"});count();}'
            'sel.onchange=apply;dim.onchange=apply;document.getElementById("spk-next").onclick=()=>go(1);document.getElementById("spk-prev").onclick=()=>go(-1);addEventListener("keydown",e=>{if(!sel.value||e.ctrlKey||e.metaKey||e.altKey||/^(INPUT|SELECT|TEXTAREA)$/.test(e.target.tagName))return;if(e.key==="j"||e.key==="ArrowRight"){e.preventDefault();go(1);}else if(e.key==="k"||e.key==="ArrowLeft"){e.preventDefault();go(-1);}});})();</script>')
    return shell(e["title"] + " transcript", body, "transcripts/index.md", 1), rec

def main():
    if SITE.exists(): shutil.rmtree(SITE)
    SITE.mkdir(); (SITE / "data").mkdir(); (SITE / ".nojekyll").write_text("")   # GitHub Pages: serve as plain files
    vis = site_visuals.build_data(ROOT); (SITE / "data" / "visuals.json").write_text(json.dumps(vis, ensure_ascii=False), encoding="utf-8")
    GRAPH_LABELS.update(n["id"] for n in vis["nodes"])
    shutil.copy(ROOT / "scripts" / "site_ego.js", SITE / "ego.js")
    if (ROOT / "data" / "images").exists(): shutil.copytree(ROOT / "data" / "images", SITE / "images")
    if (ROOT / "data" / "episode_images").exists(): shutil.copytree(ROOT / "data" / "episode_images", SITE / "episode_images")
    n = 0
    for md in NOTES.rglob("*.md"):
        rel = md.relative_to(NOTES); out = SITE / rel.with_suffix(".html")
        if rel.name == "README.md": out = SITE / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(render(md), encoding="utf-8"); n += 1
    # transcripts
    eps_ = json.load(open(ROOT / "data" / "episodes.json")); meta_ = json.load(open(ROOT / "data" / "metadata.json"))
    slugs = {p.stem.upper(): p.stem for p in (NOTES / "characters").glob("*.md")}
    slugs = {}
    for p in (NOTES / "characters").glob("*.md"):
        lbl = re.search(r"Transcript label \| `([^`]+)`", p.read_text(encoding="utf-8"))
        if lbl: slugs[lbl.group(1)] = p.stem
    (SITE / "transcripts").mkdir(exist_ok=True); (SITE / "data" / "lines").mkdir(exist_ok=True)
    loc_pages = {p.stem for p in (NOTES / "locations").glob("*.md")}
    loc_pages = {L for L in loc_pages}          # slugs
    class _L(set):
        def __contains__(self, L): return slug(L) in loc_pages
    rows = []; index = collections.defaultdict(list); STOP = set("the a an and or of to in is it that you i we he she they this for on with be are was not have as at but do if so my me your his her our its".split())
    for i, e in enumerate(eps_):
        html_, rec = render_transcript(e, meta_[e["prod"]], slugs, _L(), eps_[i - 1] if i else None, eps_[i + 1] if i + 1 < len(eps_) else None)
        (SITE / "transcripts" / f"{e['prod']}.html").write_text(html_, encoding="utf-8")
        (SITE / "data" / "lines" / f"{e['prod']}.json").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
        for ln, spk, text, _ in rec:
            for w in set(re.findall(r"[a-z0-9']+", text.lower())):
                w = w.strip("'")
                if len(w) >= 2 and w not in STOP: index[w].append(i * 4000 + ln)
        rows.append(f'<tr><td>{meta_[e["prod"]]["code"]}</td><td><a href="../episodes/{e["prod"]}.html">{html.escape(e["title"])}</a></td>'
                    f'<td>{meta_[e["prod"]]["airdate_iso"]}</td><td><a href="{e["prod"]}.html">read transcript</a></td></tr>')
    (SITE / "data" / "index.json").write_text(json.dumps({"prods": [e["prod"] for e in eps_], "titles": [e["title"] for e in eps_], "codes": [meta_[e["prod"]]["code"] for e in eps_], "stop": sorted(STOP), "words": index}, separators=(",", ":")), encoding="utf-8")
    (SITE / "search.html").write_text(shell("Search transcripts", SEARCH_BODY, "search.md", 0), encoding="utf-8")
    (SITE / "transcripts" / "index.html").write_text(shell("Transcripts", "<h1>Transcripts</h1><p>All 176 transcripts, reformatted with linked speaker names. Titles open the episode note. To find a line, use <a href=\"../search.html\">Search</a>.</p>"
        "<table><thead><tr><th>Code</th><th>Episode</th><th>Aired</th><th>Transcript</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>", "transcripts/index.md", 1), encoding="utf-8")
    # visuals
    (SITE / "visuals.html").write_text(shell("Visualisations", site_visuals.PAGE_BODY, "visuals.md", 0), encoding="utf-8")
    # search index: episodes (title, code, synopsis) and characters (name, description)
    from curated_episodes import EPISODES
    from curated_characters import FACTS, GUESTS
    eps = json.load(open(ROOT / "data" / "episodes.json")); meta = json.load(open(ROOT / "data" / "metadata.json"))
    index_ = [{"t": f"{e['title']} ({meta[e['prod']]['code']})", "d": EPISODES[e["prod"]][0], "p": f"episodes/{e['prod']}.html"} for e in eps]
    for p in (SITE / "characters").glob("*.html"):
        t = re.search(r"<h1[^>]*>(.*?)</h1>", p.read_text(encoding="utf-8")); label = re.search(r"<code>([^<]+)</code>", p.read_text(encoding="utf-8"))
        lbl = html.unescape(label.group(1)) if label else ""
        d = FACTS[lbl][1][0] if lbl in FACTS else GUESTS[lbl][1] if lbl in GUESTS else "Character"
        index_.append({"t": html.unescape(t.group(1)) if t else p.stem, "d": d[:160], "p": f"characters/{p.name}"})
    (SITE / "search.json").write_text(json.dumps(index_, ensure_ascii=False), encoding="utf-8")
    print(f"{n} note pages + {len(eps_)} transcripts + search + visuals -> {SITE}; {len(index)} indexed words, {len(index_)} quick-search entries")

if __name__ == "__main__":
    main()
