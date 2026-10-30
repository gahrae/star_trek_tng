// Radial relationship graph for a character page: the character in the centre, their relations spaced round a ring,
// the relationship kind along each spoke, ties between relations as faint chords. Same data and colours as the Visuals page.
(async()=>{
 const cv=document.getElementById('ego');if(!cv)return;const me=cv.dataset.label;
 const D=await (await fetch('../data/visuals.json')).json();
 const nb=new Set();D.edges.forEach(e=>{if(e.s===me)nb.add(e.t);if(e.t===me)nb.add(e.s);});
 const byId={};D.nodes.forEach(n=>byId[n.id]=n);
 if(!byId[me]||!nb.size){cv.closest('.egosec').style.display='none';return;}
 const group=['Starfleet','Klingon','Romulan','Civilian / Federation','Other'];
 const ring=[...nb].map(i=>byId[i]).sort((a,b)=>group.indexOf(a.group)-group.indexOf(b.group)||a.name.localeCompare(b.name));
 const spokes=D.edges.filter(e=>e.s===me||e.t===me).map(e=>({o:e.s===me?e.t:e.s,kind:e.kind}));
 const chords=D.edges.filter(e=>e.s!==me&&e.t!==me&&nb.has(e.s)&&nb.has(e.t));
 const col={'Starfleet':'--s1','Klingon':'--s2','Romulan':'--s3','Civilian / Federation':'--s4','Other':'--s5'};
 const wrap=cv.parentNode,css=n=>getComputedStyle(wrap).getPropertyValue(n).trim();
 const ctx=cv.getContext('2d'),dpr=devicePixelRatio||1;let W,H,pos={},hover=null;
 const short=n=>n.replace(/^(Captain|Commander|Lieutenant Commander|Lieutenant|Counselor|Dr|Chief|Ensign|Nurse|Admiral|Professor|Ambassador) /,'');
 function layout(){W=cv.clientWidth;H=cv.clientHeight;cv.width=W*dpr;cv.height=H*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);
  const cx=W/2,cy=H/2,R=Math.max(60,Math.min(W/2-150,H/2-40));pos={};pos[me]={x:cx,y:cy,r:16};
  ring.forEach((n,i)=>{const a=-Math.PI/2+i*2*Math.PI/ring.length;pos[n.id]={x:cx+Math.cos(a)*R,y:cy+Math.sin(a)*R,a,r:6+Math.sqrt(n.lines)/8};});}
 function pill(text,x,y,ang,font){ctx.save();ctx.translate(x,y);if(ang>Math.PI/2||ang<-Math.PI/2)ang+=Math.PI;ctx.rotate(ang);ctx.font=font;const w=ctx.measureText(text).width+8;
  ctx.fillStyle=css('--surface-1');ctx.globalAlpha=.9;ctx.fillRect(-w/2,-8,w,16);ctx.globalAlpha=1;ctx.fillStyle=css('--text-secondary');ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(text,0,0);ctx.restore();}
 function draw(){ctx.clearRect(0,0,W,H);const c=pos[me];
  ctx.strokeStyle=css('--text-secondary');ctx.lineWidth=1;ctx.globalAlpha=.25;
  for(const e of chords){const a=pos[e.s],b=pos[e.t];ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.quadraticCurveTo(c.x,c.y,b.x,b.y);ctx.stroke();}
  ctx.globalAlpha=1;ctx.lineWidth=1.4;
  for(const s of spokes){const p=pos[s.o];ctx.globalAlpha=hover&&hover!==s.o?.3:.7;ctx.beginPath();ctx.moveTo(c.x,c.y);ctx.lineTo(p.x,p.y);ctx.stroke();}
  ctx.globalAlpha=1;
  for(const n of ring){const p=pos[n.id];ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,7);ctx.fillStyle=css(col[n.group]||'--s4');ctx.fill();ctx.lineWidth=2;ctx.strokeStyle=css('--surface-1');ctx.stroke();}
  ctx.beginPath();ctx.arc(c.x,c.y,c.r,0,7);ctx.fillStyle=css(col[byId[me].group]||'--s4');ctx.fill();ctx.lineWidth=3;ctx.strokeStyle=css('--text-primary');ctx.stroke();
  for(const s of spokes){const p=pos[s.o];const t=s.kind.length>30?s.kind.slice(0,28)+'...':s.kind;const k=.56;pill(t,c.x+(p.x-c.x)*k,c.y+(p.y-c.y)*k,p.a,'11px system-ui');}
  ctx.font='12px system-ui';ctx.textBaseline='middle';ctx.fillStyle=css('--text-primary');
  for(const n of ring){const p=pos[n.id],cos=Math.cos(p.a),sin=Math.sin(p.a);ctx.textAlign=Math.abs(cos)<.3?'center':cos>0?'left':'right';
   ctx.fillText(short(n.name),p.x+cos*(p.r+8),p.y+sin*(p.r+8)+(Math.abs(cos)<.3?(sin>0?10:-10):0));}
  ctx.font='bold 13px system-ui';ctx.textAlign='center';ctx.fillText(short(byId[me].name),c.x,c.y+c.r+12);}
 function all(){layout();draw();}all();new ResizeObserver(all).observe(wrap);
 const tip=document.getElementById('tip');const at=e=>{const b=cv.getBoundingClientRect(),x=e.clientX-b.left,y=e.clientY-b.top;return ring.find(n=>{const p=pos[n.id];return (p.x-x)**2+(p.y-y)**2<(p.r+8)**2;});};
 cv.addEventListener('mousemove',e=>{const n=at(e);hover=n?n.id:null;cv.style.cursor=n?'pointer':'default';draw();
  if(n&&tip){const rel=spokes.filter(s=>s.o===n.id).map(s=>s.kind).join('; ');const other=chords.filter(e=>e.s===n.id||e.t===n.id).map(e=>`${short(byId[e.s===n.id?e.t:e.s].name)}: ${e.kind}`);
   tip.innerHTML=`<b>${n.name}</b><br>${n.group}<br>${rel}`+(other.length?'<br><i>Also tied to</i><br>'+other.join('<br>'):'');tip.style.display='block';tip.style.left=Math.min(e.clientX+14,innerWidth-tip.offsetWidth-8)+'px';tip.style.top=(e.clientY+14)+'px';}else if(tip)tip.style.display='none';});
 cv.addEventListener('mouseleave',()=>{hover=null;draw();if(tip)tip.style.display='none';});
 cv.addEventListener('click',e=>{const n=at(e);if(n)location.href='../'+n.url;});
 const sl=document.getElementById('egoh');if(sl){try{const s=localStorage.getItem('tng-ego-height');if(s)wrap.style.height=s+'px';}catch(x){}sl.value=wrap.clientHeight;
  sl.oninput=()=>{wrap.style.height=sl.value+'px';try{localStorage.setItem('tng-ego-height',sl.value);}catch(x){}};
  new ResizeObserver(()=>{sl.value=wrap.clientHeight;try{localStorage.setItem('tng-ego-height',wrap.clientHeight);}catch(x){}}).observe(wrap);}
})();
