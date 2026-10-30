"""Data and page for the visualisations: relationship graph, co-appearance heatmap, lines per season, arc timeline.
Used by build_site.py. Colours follow a validated categorical/sequential palette with separate dark-mode steps."""
import json, collections, itertools, re
from curated_characters import PROFILES, FACTS, GUESTS
from curated_episodes import EPISODES, ARCS, ARC_GROUPS

REGULARS = ["PICARD", "RIKER", "DATA", "LAFORGE", "WORF", "CRUSHER", "TROI", "WESLEY", "TASHA", "PULASKI", "GUINAN", "O'BRIEN"]
SHORT = {"PICARD": "Picard", "RIKER": "Riker", "DATA": "Data", "LAFORGE": "La Forge", "WORF": "Worf", "CRUSHER": "Crusher", "TROI": "Troi",
         "WESLEY": "Wesley", "TASHA": "Yar", "PULASKI": "Pulaski", "GUINAN": "Guinan", "O'BRIEN": "O'Brien"}
def slug(label): return re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
def name_of(l): return FACTS[l][0] if l in FACTS else GUESTS[l][0] if l in GUESTS else l.title()
def group_of(l):
    a = PROFILES.get(l, {}).get("affiliation", "")
    if "Starfleet" in a: return "Starfleet"
    if "Klingon" in a: return "Klingon"
    if "Romulan" in a: return "Romulan"
    if "Q" in a or "Borg" in a or "None" in a or "Hologram" in PROFILES.get(l, {}).get("species", ""): return "Other"
    return "Civilian / Federation"
GROUPS = ["Starfleet", "Klingon", "Romulan", "Civilian / Federation", "Other"]

def build_data(root):
    chars = json.load(open(root / "data" / "characters.json")); scenes = json.load(open(root / "data" / "scenes.json"))
    eps = json.load(open(root / "data" / "episodes.json")); meta = json.load(open(root / "data" / "metadata.json"))
    # graph: curated relationships among profiled characters and the guests they name
    nodes = {}; edges = []
    for l, p in PROFILES.items():
        for other, kind in p["relationships"]:
            for x in (l, other):
                if x not in nodes:
                    d = chars.get(x, {"episodes": [], "lines": 0})
                    nodes[x] = {"id": x, "name": name_of(x), "url": f"characters/{slug(x)}.html", "group": group_of(x) if x in PROFILES else "Civilian / Federation",
                                "lines": d["lines"], "episodes": len(d["episodes"]), "main": x in PROFILES}
            edges.append({"s": l, "t": other, "kind": kind})
    # scene co-appearance among profiled characters (for the optional overlay and the heatmap)
    co = collections.Counter()
    for prod, sc in scenes.items():
        for s in sc:
            named = sorted(x for x in s["speakers"] if x in PROFILES)
            for a, b in itertools.combinations(named, 2): co[(a, b)] += 1
    co_edges = [{"s": a, "t": b, "w": n} for (a, b), n in co.most_common() if n >= 15 and a in nodes and b in nodes]
    heat = [[co.get((min(a, b), max(a, b)), 0) if a != b else None for b in REGULARS] for a in REGULARS]
    seasons = {SHORT[l]: [chars[l]["by_season"].get(str(s), 0) for s in range(1, 8)] for l in REGULARS[:7]}
    timeline = [{"prod": e["prod"], "code": meta[e["prod"]]["code"], "title": e["title"], "season": meta[e["prod"]]["season"],
                 "arcs": EPISODES[e["prod"]][1], "synopsis": EPISODES[e["prod"]][0], "url": f"episodes/{e['prod']}.html"} for e in eps]
    stardates = []; prev = None
    fixed = json.load(open(root / "data" / "stardates.json")) if (root / "data" / "stardates.json").exists() else {}
    for i, e in enumerate(eps, 1):
        sd = fixed.get(e["prod"], e.get("stardate", ""))
        try: v = float(sd)
        except ValueError: v = None
        back = v is not None and prev is not None and v < prev
        if v is not None: prev = v
        stardates.append({"i": i, "prod": e["prod"], "code": meta[e["prod"]]["code"], "title": e["title"], "season": meta[e["prod"]]["season"],
                          "sd": v, "airdate": meta[e["prod"]]["airdate_iso"], "back": back, "url": f"episodes/{e['prod']}.html"})
    return {"stardates": stardates, "nodes": list(nodes.values()), "edges": edges, "co_edges": co_edges, "groups": GROUPS, "heat": {"labels": [SHORT[l] for l in REGULARS], "m": heat},
            "seasons": seasons, "timeline": timeline, "arcs": ARCS, "arc_groups": ARC_GROUPS}

PAGE_BODY = """
<h1>Visualisations</h1>
<p>Interactive views of the same data as the notes. Hover for details; click a node, cell or episode to open its page. All views are also available as tables in the notes.</p>
<style>
main{max-width:none}.gwrap{height:max(560px,72vh);min-height:300px;resize:vertical;overflow:hidden;border-radius:8px}
.viz{--surface-1:#fcfcfb;--text-primary:#0b0b0b;--text-secondary:#52514e;--grid:#e4e3df;--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--s5:#e87ba4;--s6:#008300;--s7:#6250d6;--s8:#e34948;
 --seq1:#cde2fb;--seq2:#9ec5f4;--seq3:#6da7ec;--seq4:#3987e5;--seq5:#256abf;--seq6:#184f95;--seq7:#0d366b;color-scheme:light;background:var(--surface-1);color:var(--text-primary);border:1px solid var(--grid);border-radius:10px;padding:1rem;margin:1.5rem 0}
@media (prefers-color-scheme: dark){:root:where(:not([data-theme="light"])) .viz{color-scheme:dark;--surface-1:#1a1a19;--text-primary:#f0efec;--text-secondary:#c3c2b7;--grid:#383835;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181;--s6:#008300;--s7:#9085e9;--s8:#e66767;--seq1:#0d366b;--seq2:#104281;--seq3:#1c5cab;--seq4:#256abf;--seq5:#3987e5;--seq6:#6da7ec;--seq7:#9ec5f4}}
:root[data-theme="dark"] .viz{color-scheme:dark;--surface-1:#1a1a19;--text-primary:#f0efec;--text-secondary:#c3c2b7;--grid:#383835;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181;--s6:#008300;--s7:#9085e9;--s8:#e66767;--seq1:#0d366b;--seq2:#104281;--seq3:#1c5cab;--seq4:#256abf;--seq5:#3987e5;--seq6:#6da7ec;--seq7:#9ec5f4}
.viz h2{margin:.2rem 0 .3rem;font-size:1.15rem;border:0;padding:0;color:var(--text-primary)}.viz p.sub{color:var(--text-secondary);margin:0 0 .8rem;font-size:.9rem}
.viz .controls{display:flex;flex-wrap:wrap;gap:.5rem 1rem;align-items:center;margin-bottom:.6rem;font-size:.9rem}
.viz select,.viz input[type=range]{background:var(--surface-1);color:var(--text-primary);border:1px solid var(--grid);border-radius:6px;padding:.25rem .4rem}
.legend{display:flex;flex-wrap:wrap;gap:.4rem 1rem;font-size:.85rem;color:var(--text-secondary);margin:.4rem 0}.legend span::before{content:"";display:inline-block;width:10px;height:10px;border-radius:50%;background:var(--c);margin-right:.35rem;vertical-align:middle}
.legend span.line::before{height:2px;width:16px;border-radius:0}
canvas{width:100%;height:100%;display:block;border-radius:8px;cursor:grab}
.tip{position:fixed;pointer-events:none;background:var(--panel,#fff);color:var(--text,#111);border:1px solid var(--line,#ccc);border-radius:6px;padding:.35rem .55rem;font-size:.85rem;max-width:22rem;z-index:9;display:none;box-shadow:0 2px 8px rgba(0,0,0,.2)}
.heat{display:grid;gap:2px;font-size:.78rem;max-width:760px}.heat div{aspect-ratio:1;display:flex;align-items:center;justify-content:center;border-radius:3px;min-width:0}.heat .h{background:none;color:var(--text-secondary);aspect-ratio:auto;padding:.2rem;justify-content:flex-end}.heat .ht{aspect-ratio:auto;justify-content:center;writing-mode:vertical-rl;transform:rotate(180deg);padding:.2rem}
.heat .c{color:var(--text-primary);cursor:default}.heat .c.dark{color:#fff}
svg text{fill:var(--text-primary);font-size:12px}svg .axis{stroke:var(--grid)}svg .lab{fill:var(--text-secondary)}
.tl{display:grid;grid-template-columns:3rem repeat(28,1fr);gap:3px;align-items:center}.tl .cell{aspect-ratio:1;border-radius:3px;background:var(--grid);cursor:pointer}.tl .cell.on{background:var(--s1)}.tl .cell:hover{outline:2px solid var(--text-primary)}.tl .sl{color:var(--text-secondary);font-size:.8rem}
</style>
<div class="tip" id="tip"></div>

<section class="viz" id="graph">
<h2>Relationship graph</h2>
<p class="sub">Relationships (family, romance, rivalry, mentorship) recorded in the curated data between the main and recurring cast and the people they are tied to. Node size follows dialogue lines; colour follows affiliation. Drag to move, scroll to zoom.</p>
<div class="controls"><label><input type="checkbox" id="rel" checked> Relationship edges</label><label><input type="checkbox" id="coapp"> Co-appearance edges (15+ shared scenes)</label><label>Charge <input type="range" id="charge" min="500" max="6000" value="2600"></label><label>Height <input type="range" id="gh" min="300" max="1600" step="20"></label><span style="color:var(--text-secondary)">(or drag the panel's bottom-right corner)</span></div>
<div class="legend" id="glegend"></div>
<div class="gwrap" id="gwrap"><canvas id="gc"></canvas></div>
</section>

<section class="viz" id="heatmap">
<h2>Scenes shared, main cast</h2>
<p class="sub">Number of scenes in which both characters speak. Darker is more.</p>
<div class="heat" id="heat"></div>
</section>

<section class="viz" id="seasons">
<h2>Dialogue lines per season</h2>
<p class="sub">The seven regulars across the run. Move across the chart to read exact values.</p>
<div class="legend" id="slegend"></div>
<svg id="sv" viewBox="0 0 900 380" style="width:100%;height:auto"></svg>
</section>

<section class="viz" id="stardates">
<h2>Stardates across the run</h2>
<p class="sub">Each episode's stated stardate against its broadcast position. Stardates advance about a thousand units per season; hollow orange points are episodes whose stardate is earlier than the previous episode's. Four episodes give no stardate and are omitted.</p>
<div class="legend"><span style="--c:var(--s1)">stardate</span><span style="--c:var(--s2)">earlier than the previous episode</span></div>
<svg id="sdv" viewBox="0 0 1000 420" style="width:100%;height:auto"></svg>
</section>

<section class="viz" id="timeline">
<h2>Arc timeline</h2>
<p class="sub">One cell per transcript entry, in broadcast order by season. Pick an arc to highlight its episodes.</p>
<div class="controls"><label>Arc <select id="arc"></select></label><span id="arccount" style="color:var(--text-secondary)"></span></div>
<div class="tl" id="tl"></div>
</section>

<script>
const VROOT='';const tip=document.getElementById('tip');
function showTip(e,html){tip.innerHTML=html;tip.style.display='block';const x=Math.min(e.clientX+14,innerWidth-tip.offsetWidth-8);tip.style.left=x+'px';tip.style.top=(e.clientY+14)+'px';}
function hideTip(){tip.style.display='none';}
const css=n=>getComputedStyle(document.querySelector('.viz')).getPropertyValue(n).trim();
fetch(VROOT+'data/visuals.json').then(r=>r.json()).then(D=>{graph(D);heat(D);seasons(D);stardates(D);timeline(D);});

// ---------- force-directed relationship graph (canvas, no dependencies)
function graph(D){
 const cv=document.getElementById('gc'),ctx=cv.getContext('2d');const dpr=devicePixelRatio||1;
 const gcol={'Starfleet':'--s1','Klingon':'--s2','Romulan':'--s3','Civilian / Federation':'--s4','Other':'--s5'};
 document.getElementById('glegend').innerHTML=D.groups.map(g=>`<span style="--c:var(${gcol[g]})">${g}</span>`).join('')+'<span class="line" style="--c:var(--text-secondary)">relationship</span><span class="line" style="--c:var(--s7)">co-appearance</span>';
 const N=D.nodes.map(n=>({...n,x:Math.random()*800,y:Math.random()*500,vx:0,vy:0,r:4+Math.sqrt(n.lines)/6}));const id={};N.forEach(n=>id[n.id]=n);
 const E=D.edges.map(e=>({a:id[e.s],b:id[e.t],kind:e.kind}));const C=D.co_edges.map(e=>({a:id[e.s],b:id[e.t],w:e.w}));
 let W,H,zoom=1,ox=0,oy=0,drag=null,hover=null,charge=2600,showCo=false,showRel=true,alpha=1;
 const wrap=document.getElementById('gwrap'),gh=document.getElementById('gh');
 function size(){W=cv.clientWidth;H=cv.clientHeight;cv.width=W*dpr;cv.height=H*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);}
 try{const saved=localStorage.getItem('tng-graph-height');if(saved)wrap.style.height=saved+'px';}catch(e){}
 size();addEventListener('resize',size);gh.value=wrap.clientHeight;
 new ResizeObserver(()=>{size();gh.value=wrap.clientHeight;try{localStorage.setItem('tng-graph-height',wrap.clientHeight);}catch(e){}}).observe(wrap);
 gh.oninput=()=>{wrap.style.height=gh.value+'px';size();try{localStorage.setItem('tng-graph-height',gh.value);}catch(e){}};
 N.forEach(n=>{n.x=W/2+(Math.random()-.5)*W*.8;n.y=H/2+(Math.random()-.5)*H*.8;});
 function step(){
  for(const n of N){n.fx=0;n.fy=0;}
  for(let i=0;i<N.length;i++)for(let j=i+1;j<N.length;j++){const a=N[i],b=N[j];let dx=b.x-a.x,dy=b.y-a.y,d2=dx*dx+dy*dy+1,f=charge/d2;const d=Math.sqrt(d2);dx/=d;dy/=d;a.fx-=dx*f;a.fy-=dy*f;b.fx+=dx*f;b.fy+=dy*f;}
  const links=(showRel?E:[]).concat(showCo?C:[]);
  for(const e of links){const a=e.a,b=e.b;let dx=b.x-a.x,dy=b.y-a.y,d=Math.sqrt(dx*dx+dy*dy)+.1;const L=e.w?120:100,k=e.w?.002:.02,f=(d-L)*k;dx/=d;dy/=d;a.fx+=dx*f;a.fy+=dy*f;b.fx-=dx*f;b.fy-=dy*f;}
  for(const n of N){n.fx+=(W/2-n.x)*.004;n.fy+=(H/2-n.y)*.004;if(n===drag)continue;n.vx=(n.vx+n.fx)*.6*alpha+n.vx*(1-alpha)*0;n.vy=(n.vy+n.fy)*.6*alpha;n.x+=n.vx;n.y+=n.vy;}
  alpha=Math.max(.05,alpha*.995);
 }
 function draw(){ctx.clearRect(0,0,W,H);ctx.save();ctx.translate(ox,oy);ctx.scale(zoom,zoom);
  const ink=css('--text-secondary'),co=css('--s7');
  if(showCo){ctx.strokeStyle=co;for(const e of C){ctx.globalAlpha=Math.min(.7,e.w/400);ctx.lineWidth=1+e.w/150;ctx.beginPath();ctx.moveTo(e.a.x,e.a.y);ctx.lineTo(e.b.x,e.b.y);ctx.stroke();}ctx.globalAlpha=1;}
  ctx.strokeStyle=ink;ctx.lineWidth=1.2;if(showRel)for(const e of E){ctx.globalAlpha=hover&&(e.a===hover||e.b===hover)?1:.35;ctx.beginPath();ctx.moveTo(e.a.x,e.a.y);ctx.lineTo(e.b.x,e.b.y);ctx.stroke();}ctx.globalAlpha=1;
  for(const n of N){ctx.beginPath();ctx.arc(n.x,n.y,n.r,0,7);ctx.fillStyle=css(gcol[n.group]);ctx.fill();ctx.lineWidth=2;ctx.strokeStyle=css('--surface-1');ctx.stroke();}
  ctx.fillStyle=css('--text-primary');ctx.font='12px system-ui';ctx.textAlign='center';for(const n of N)if(n.main||n===hover||zoom>1.4)ctx.fillText(n.name.replace(/^(Captain|Commander|Lieutenant Commander|Lieutenant|Counselor|Dr|Chief|Ensign|Nurse|Admiral|Professor|Ambassador) /,''),n.x,n.y-n.r-4);
  ctx.restore();}
 (function loop(){step();draw();requestAnimationFrame(loop);})();
 const pt=e=>{const b=cv.getBoundingClientRect();return{x:(e.clientX-b.left-ox)/zoom,y:(e.clientY-b.top-oy)/zoom};};
 const at=p=>N.find(n=>(n.x-p.x)**2+(n.y-p.y)**2<(n.r+6)**2);
 cv.addEventListener('mousemove',e=>{const p=pt(e);if(drag){drag.x=p.x;drag.y=p.y;alpha=Math.max(alpha,.3);return;}hover=at(p);cv.style.cursor=hover?'pointer':'grab';
  if(hover){const rel=showRel?E.filter(x=>x.a===hover||x.b===hover).map(x=>`${x.a===hover?x.b.name:x.a.name}: ${x.kind}`):[];const co=showCo?C.filter(x=>x.a===hover||x.b===hover).sort((p,q)=>q.w-p.w).slice(0,5).map(x=>`${x.a===hover?x.b.name:x.a.name}: ${x.w} scenes`):[];showTip(e,`<b>${hover.name}</b><br>${hover.lines} lines, ${hover.episodes} episodes`+(rel.length?'<br>'+rel.slice(0,8).join('<br>')+(rel.length>8?'<br>...':''):'')+(co.length?'<br><i>Shared scenes</i><br>'+co.join('<br>'):''));}else hideTip();});
 cv.addEventListener('mousedown',e=>{drag=at(pt(e));if(!drag){cv.dataset.pan=JSON.stringify([e.clientX-ox,e.clientY-oy]);}});
 addEventListener('mouseup',e=>{if(drag&&cv.dataset.click==='1'){location.href=VROOT+drag.url;}drag=null;delete cv.dataset.pan;});
 cv.addEventListener('mousedown',()=>cv.dataset.click='1');cv.addEventListener('mousemove',e=>{if(e.buttons){cv.dataset.click='0';if(cv.dataset.pan){const [px,py]=JSON.parse(cv.dataset.pan);ox=e.clientX-px;oy=e.clientY-py;}}});
 cv.addEventListener('wheel',e=>{e.preventDefault();const b=cv.getBoundingClientRect(),mx=e.clientX-b.left,my=e.clientY-b.top,z=Math.exp(-e.deltaY*.001);ox=mx-(mx-ox)*z;oy=my-(my-oy)*z;zoom*=z;},{passive:false});
 cv.addEventListener('mouseleave',hideTip);
 document.getElementById('coapp').onchange=e=>{showCo=e.target.checked;alpha=1;};document.getElementById('rel').onchange=e=>{showRel=e.target.checked;alpha=1;};document.getElementById('charge').oninput=e=>{charge=+e.target.value;alpha=1;};
}

// ---------- co-appearance heatmap (sequential single hue)
function heat(D){
 const el=document.getElementById('heat'),L=D.heat.labels,M=D.heat.m,max=Math.max(...M.flat().filter(v=>v!==null));
 el.style.gridTemplateColumns=`5rem repeat(${L.length},1fr)`;
 const steps=['--seq1','--seq2','--seq3','--seq4','--seq5','--seq6','--seq7'];
 let h='<div class="h"></div>'+L.map(l=>`<div class="ht h">${l}</div>`).join('');
 M.forEach((row,i)=>{h+=`<div class="h">${L[i]}</div>`;row.forEach((v,j)=>{if(v===null){h+='<div></div>';return;}const k=Math.min(6,Math.floor(Math.sqrt(v/max)*7));
  h+=`<div class="c ${k>=4?'dark':''}" style="background:var(${steps[k]})" data-t="<b>${L[i]} and ${L[j]}</b><br>${v} scenes together">${v}</div>`;});});
 el.innerHTML=h;el.querySelectorAll('.c').forEach(c=>{c.onmousemove=e=>showTip(e,c.dataset.t);c.onmouseleave=hideTip;});
}

// ---------- lines per season (SVG line chart with crosshair)
function seasons(D){
 const svg=document.getElementById('sv'),names=Object.keys(D.seasons),cols=['--s1','--s2','--s3','--s4','--s5','--s6','--s7'];
 const W=900,H=380,m={l:50,r:90,t:16,b:34},max=Math.ceil(Math.max(...names.flatMap(n=>D.seasons[n]))/500)*500;
 const x=s=>m.l+(s-1)*(W-m.l-m.r)/6,y=v=>H-m.b-v*(H-m.t-m.b)/max;
 let g='';for(let v=0;v<=max;v+=500)g+=`<line class="axis" x1="${m.l}" x2="${W-m.r}" y1="${y(v)}" y2="${y(v)}"/><text class="lab" x="${m.l-6}" y="${y(v)+4}" text-anchor="end">${v}</text>`;
 for(let s=1;s<=7;s++)g+=`<text class="lab" x="${x(s)}" y="${H-m.b+18}" text-anchor="middle">S${s}</text>`;
 names.forEach((n,i)=>{const d=D.seasons[n].map((v,k)=>`${k?'L':'M'}${x(k+1)},${y(v)}`).join(' ');g+=`<path d="${d}" fill="none" stroke="var(${cols[i]})" stroke-width="2" stroke-linejoin="round"/>`;
  D.seasons[n].forEach((v,k)=>{if(v)g+=`<circle cx="${x(k+1)}" cy="${y(v)}" r="4" fill="var(${cols[i]})" stroke="var(--surface-1)" stroke-width="2"/>`;});
  });
 // direct labels at the right edge, nudged apart so they never overlap
 const labs=names.map((n,i)=>({n,i,y:y(D.seasons[n][6])})).sort((a,b)=>a.y-b.y);
 for(let k=1;k<labs.length;k++)if(labs[k].y-labs[k-1].y<14)labs[k].y=labs[k-1].y+14;
 for(let k=labs.length-2;k>=0;k--)if(labs[k+1].y-labs[k].y<14)labs[k].y=labs[k+1].y-14;
 labs.forEach(l=>{const ly=y(D.seasons[l.n][6]);g+=`<line class="axis" x1="${x(7)+4}" y1="${ly}" x2="${x(7)+10}" y2="${l.y}"/><text x="${x(7)+12}" y="${l.y+4}">${l.n}</text>`;});
 g+=`<line id="xh" class="axis" y1="${m.t}" y2="${H-m.b}" x1="0" x2="0" style="display:none" stroke-dasharray="3 3"/>`;svg.innerHTML=g;
 document.getElementById('slegend').innerHTML=names.map((n,i)=>`<span class="line" style="--c:var(${cols[i]})">${n}</span>`).join('');
 const xh=document.getElementById('xh');
 svg.onmousemove=e=>{const b=svg.getBoundingClientRect(),px=(e.clientX-b.left)*W/b.width,s=Math.max(1,Math.min(7,Math.round((px-m.l)/((W-m.l-m.r)/6))+1));xh.setAttribute('x1',x(s));xh.setAttribute('x2',x(s));xh.style.display='';
  showTip(e,`<b>Season ${s}</b><br>`+names.map(n=>`${n}: ${D.seasons[n][s-1]}`).join('<br>'));};
 svg.onmouseleave=()=>{xh.style.display='none';hideTip();};
}

// ---------- stardates in broadcast order (scatter + line, season bands)
function stardates(D){
 const svg=document.getElementById('sdv'),P=D.stardates,W=1000,H=420,m={l:62,r:16,t:14,b:36};
 const pts=P.filter(p=>p.sd!==null),lo=Math.floor(Math.min(...pts.map(p=>p.sd))/1000)*1000,hi=Math.ceil(Math.max(...pts.map(p=>p.sd))/1000)*1000;
 const x=i=>m.l+(i-1)*(W-m.l-m.r)/(P.length-1),y=v=>H-m.b-(v-lo)*(H-m.t-m.b)/(hi-lo);
 let g='';
 const seasons={};P.forEach(p=>{(seasons[p.season]=seasons[p.season]||[]).push(p.i);});
 Object.entries(seasons).forEach(([s,is],k)=>{const a=x(Math.min(...is)),b=x(Math.max(...is));if(k%2)g+=`<rect x="${a}" y="${m.t}" width="${b-a}" height="${H-m.t-m.b}" fill="var(--grid)" opacity=".35"/>`;g+=`<text class="lab" x="${(a+b)/2}" y="${H-m.b+18}" text-anchor="middle">Season ${s}</text>`;});
 for(let v=lo;v<=hi;v+=1000)g+=`<line class="axis" x1="${m.l}" x2="${W-m.r}" y1="${y(v)}" y2="${y(v)}"/><text class="lab" x="${m.l-6}" y="${y(v)+4}" text-anchor="end">${v}</text>`;
 g+=`<path d="${pts.map((p,k)=>`${k?'L':'M'}${x(p.i)},${y(p.sd)}`).join(' ')}" fill="none" stroke="var(--s1)" stroke-width="1.5" opacity=".6"/>`;
 pts.forEach(p=>{g+=p.back?`<circle class="pt" data-i="${p.i}" cx="${x(p.i)}" cy="${y(p.sd)}" r="4.5" fill="var(--surface-1)" stroke="var(--s2)" stroke-width="2"/>`:`<circle class="pt" data-i="${p.i}" cx="${x(p.i)}" cy="${y(p.sd)}" r="3.5" fill="var(--s1)" stroke="var(--surface-1)" stroke-width="1.5"/>`;});
 svg.innerHTML=g;const byI={};P.forEach(p=>byI[p.i]=p);
 svg.querySelectorAll('.pt').forEach(c=>{const p=byI[c.dataset.i];c.style.cursor='pointer';c.onmousemove=e=>showTip(e,`<b>${p.code} ${p.title}</b><br>Stardate ${p.sd}<br>Aired ${p.airdate}${p.back?'<br><i>earlier than the previous episode</i>':''}`);c.onmouseleave=hideTip;c.onclick=()=>location.href=VROOT+p.url;});
}

// ---------- arc timeline
function timeline(D){
 const sel=document.getElementById('arc'),tl=document.getElementById('tl');sel.innerHTML='<option value="">(none)</option>'+D.arc_groups.map(([g,arcs])=>`<optgroup label="${g}">`+arcs.map(a=>`<option>${a}</option>`).join('')+'</optgroup>').join('');
 const bySeason={};D.timeline.forEach(e=>(bySeason[e.season]=bySeason[e.season]||[]).push(e));
 let h='';for(const s of Object.keys(bySeason)){h+=`<div class="sl">S${s}</div>`;bySeason[s].forEach(e=>h+=`<div class="cell" data-p="${e.prod}"></div>`);for(let k=bySeason[s].length;k<28;k++)h+='<div></div>';}
 tl.innerHTML=h;const byProd={};D.timeline.forEach(e=>byProd[e.prod]=e);
 tl.querySelectorAll('.cell').forEach(c=>{const e=byProd[c.dataset.p];c.onmousemove=ev=>showTip(ev,`<b>${e.code} ${e.title}</b><br>${e.synopsis}<br><i>${e.arcs.join(', ')}</i>`);c.onmouseleave=hideTip;c.onclick=()=>location.href=VROOT+e.url;});
 sel.onchange=()=>{let n=0;tl.querySelectorAll('.cell').forEach(c=>{const on=sel.value&&byProd[c.dataset.p].arcs.includes(sel.value);c.classList.toggle('on',!!on);if(on)n++;});document.getElementById('arccount').textContent=sel.value?`${n} episodes`:'';};
 sel.value='Borg';sel.onchange();
}
</script>
"""
