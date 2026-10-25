/* Sarah Mark 1 X-ray front end: polls the local server, animates the circuit, shows the decision funnel and internal state. */
(function(){
const $=id=>document.getElementById(id),C=HUD.C;
let state=null,since=0,decisions=[],sel=-1,pulses=[],glow={},logEl=$("log"),truth=false,lastState=0;
const esc=s=>String(s).replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
async function post(o){await fetch("/control",{method:"POST",body:JSON.stringify(o)})}

/* ---------------- circuit ---------------- */
const N={curriculum:[.08,.76,"CURRICULUM"],task:[.08,.30,"TASK"],memory:[.26,.30,"MEMORY"],filter:[.43,.30,"LESSON FILTER"],imagine:[.60,.30,"IMAGINATION"],llm:[.77,.30,"LLM"],action:[.93,.30,"ACTION"],env:[.93,.76,"WORLD"],reflect:[.77,.76,"REFLECT"],skills:[.43,.76,"SKILLS"]};
const E=[["curriculum","task"],["task","memory"],["memory","filter"],["filter","imagine"],["imagine","llm"],["skills","llm"],["llm","action"],["action","env"],["env","reflect"],["reflect","memory"],["reflect","skills"],["reflect","imagine"]];
const MOD={memory:"memory",filter:"lesson_filter",imagine:"worldmodel",skills:"skills",reflect:"reflection"};
function pulse(a,b,col){pulses.push({a,b,t:performance.now(),col:col||C.cyan});glow[b]=performance.now()}
function drawCircuit(){const cv=$("circuit"),{g,w,h}=HUD.fit(cv);g.clearRect(0,0,w,h);const now=performance.now(),cfg=state?state.cfg:{};
  const P=k=>[N[k][0]*w,N[k][1]*h];
  E.forEach(([a,b])=>{const[p,q]=[P(a),P(b)];g.strokeStyle="rgba(0,229,255,.22)";g.lineWidth=1.2;g.beginPath();g.moveTo(...p);g.lineTo(...q);g.stroke()});
  pulses=pulses.filter(u=>now-u.t<650);pulses.forEach(u=>{const t=(now-u.t)/650,p=P(u.a),q=P(u.b);const x=p[0]+(q[0]-p[0])*t,y=p[1]+(q[1]-p[1])*t;g.fillStyle=u.col;g.shadowColor=u.col;g.shadowBlur=12;g.beginPath();g.arc(x,y,4,0,7);g.fill();g.shadowBlur=0});
  const counts=state?{memory:state.stats.lessons+" lessons",filter:(state.stats.filtered_actions||0)+" removed",imagine:"top-"+cfg.shortlist_k,llm:state.llm_calls+" calls",skills:state.skills.length+" skills",reflect:(state.stats.reflect_hint+state.stats.reflect_llm)+" refl.",curriculum:state.curriculum.unlocked.length+"/4 stages",task:"",action:"",env:""}:{};
  Object.entries(N).forEach(([k,[fx,fy,label]])=>{const[x,y]=P(k),on=!MOD[k]||cfg[MOD[k]]!==false;const gl=Math.max(0,1-(now-(glow[k]||0))/900);
    g.fillStyle=on?`rgba(0,229,255,${.10+.35*gl})`:"rgba(80,80,80,.15)";g.strokeStyle=on?(gl>0.05?C.gold:C.cyan):"#555";g.lineWidth=1.5+2*gl;if(gl>.05){g.shadowColor=C.gold;g.shadowBlur=18*gl}
    g.beginPath();g.rect(x-34,y-17,68,34);g.fill();g.stroke();g.shadowBlur=0;g.fillStyle=on?C.txt:"#777";g.font="9.5px 'Share Tech Mono',monospace";g.textAlign="center";g.fillText(label,x,y-3);g.fillStyle=on?C.gold:"#777";g.font="9px 'Share Tech Mono',monospace";g.fillText(on?(counts[k]||""):"OFF",x,y+9)});
  g.textAlign="left";g.fillStyle=C.muted;g.font="10px 'Share Tech Mono',monospace";g.fillText("decide →",8,12);g.fillText("← learn: outcome → reflection → lessons / skills / imagination",8,h-6)}

/* ---------------- events ---------------- */
function logLine(e){const d=e.data,k=e.kind;let t="";
  if(k==="choose")t=`curiosity picks <b>${d.activity}</b>  (LP ${Object.entries(d.lp).map(([a,v])=>a[0]+":"+v).join(" ")})`;
  else if(k==="decide")t=`decide [${d.domain}] ${d.props.join("+")} → options ${d.options.length}/${d.all.length}${d.removed.length?` (filter removed ${d.removed.length})`:""} → <b>${d.choice}</b>${d.via_llm?"":" (only option)"}${d.invalid?" ⚠invalid reply":""}`;
  else if(k==="outcome")t=`outcome ${d.success?"<span class=ok>✔ success</span>":"<span class=bad>✘ fail</span>"} — ${d.feedback}`;
  else if(k==="reflect")t=`reflect: culprit = <b>${d.prop||"?"}</b> (${d.source})`;
  else if(k==="lesson")t=`lesson stored: ${d.text} (support ${d.support})`;
  else if(k==="skill")t=`skill: ${d.action} works for ${d.props.join("+")}`;
  else if(k==="wm")t=`imagination updated: ${d.action} · ${d.success?"worked":"failed"}${d.culprit?" ("+d.culprit+")":""}`;
  else if(k==="sleep")t=`<b>sleep</b>: consolidation — forgot ${d.forgotten.length} lesson(s)${d.forgotten.length?": "+d.forgotten.join("; "):""}`;
  else if(k==="unlock")t=`<b>★ stage unlocked: ${d.stage}</b>`;
  else if(k==="toggle")t=`module ${d.module} → ${d.value}`;
  else if(k==="error")t=d.message;else return null;
  return `<div class="ev ${k}">${t}</div>`}
function onEvent(e){const d=e.data,k=e.kind;
  if(k==="choose"){pulse("curriculum","task",C.green)}
  if(k==="decide"){pulse("task","memory");setTimeout(()=>pulse("memory","filter"),120);setTimeout(()=>pulse("filter","imagine"),240);setTimeout(()=>pulse("imagine","llm"),360);if(d.skill)setTimeout(()=>pulse("skills","llm",C.violet),360);setTimeout(()=>pulse("llm","action",C.gold),520);
    decisions.push({dec:d,out:null,refl:null,lesson:null});if(decisions.length>60)decisions.shift();if(sel<0||sel>=decisions.length-2)sel=decisions.length-1;renderDecision()}
  if(k==="outcome"){pulse("action","env",C.gold);const r=decisions[decisions.length-1];if(r)r.out=d;renderDecision()}
  if(k==="reflect"){pulse("env","reflect",C.red);setTimeout(()=>pulse("reflect","memory",C.violet),150);const r=decisions[decisions.length-1];if(r)r.refl=d;renderDecision()}
  if(k==="lesson"){glow.memory=performance.now();const r=decisions[decisions.length-1];if(r)r.lesson=d;renderDecision()}
  if(k==="skill"){pulse("reflect","skills",C.green)}
  if(k==="wm"){pulse("reflect","imagine",C.green)}
  if(k==="sleep"){glow.memory=performance.now()+800;pulse("reflect","memory",C.green)}
  const html=logLine(e);if(html){logEl.insertAdjacentHTML("beforeend",html);while(logEl.children.length>300)logEl.removeChild(logEl.firstChild);logEl.scrollTop=logEl.scrollHeight}}

/* ---------------- decision x-ray ---------------- */
function chip(a,cls="",extra=""){return `<span class="chip ${cls}">${a}${extra}</span>`}
function renderDecision(){const hist=$("hist");hist.innerHTML=decisions.map((r,i)=>`<i class="${r.out?(r.out.success?"s":"f"):""} ${i===sel?"sel":""}" data-i="${i}" title="${r.dec.domain}: ${r.dec.props.join("+")}"></i>`).join("");
  hist.querySelectorAll("i").forEach(el=>el.onclick=()=>{sel=+el.dataset.i;renderDecision()});
  const r=decisions[sel];if(!r){$("xr").innerHTML="<p class='note'>waiting for the first decision — press RUN or STEP</p>";return}const d=r.dec,tf=new Set(truth?d.truth_forbidden:[]);
  $("decTitle").textContent=`[${d.domain}] ${d.props.join(" + ")}`;
  const allChips=d.all.map(a=>chip(a,tf.has(a)?"truth":"",tf.has(a)?" ✖":"")).join(""),
    rm=d.removed.length?d.removed.map(([a,t])=>`<span class="chip rm" title="${esc(t)}">${a}</span>`).join(""):"",
    afterF=d.after_filter.map(a=>chip(a,tf.has(a)?"truth":"")).join(""),
    risk=d.risk?d.risk.map(([a,p])=>chip(a,(a===d.choice?"pick ":"")+(tf.has(a)?"truth":""),`<span class="bar" style="width:${Math.round(p*100)}%"></span>`)).join(""):d.options.map(a=>chip(a,a===d.choice?"pick":"")).join("");
  const o=r.out,ok=o?o.success:null;
  $("xr").innerHTML=`<div class="row"><b>1 task</b><div>${d.props.map(p=>`<span class="tag g">${p}</span>`).join("")} <span class="mini">stage: ${d.domain}</span></div></div>
   <div class="row"><b>2 all actions</b><div class="chips">${allChips}</div></div>
   <div class="row"><b>3 lesson filter</b><div class="chips">${afterF}${rm}</div><div class="mini" style="grid-column:2">${d.removed.length?d.removed.map(([a,t])=>"✂ "+esc(t)).join(" · "):"nothing removed (no confident lessons apply)"}</div></div>
   <div class="row"><b>4 imagination</b><div class="chips">${risk}</div><div class="mini" style="grid-column:2">world model shortlist with predicted success</div></div>
   <div class="row"><b>5 LLM</b><div>${d.via_llm?`<pre class="pr">${esc(d.prompt)}</pre><div class="mini">reply: <b>${esc((d.reply||"").trim())}</b>${d.invalid?" <span class=bad>— unparseable, random option used</span>":""}</div>`:`<span class="mini">skipped: only one option left</span>`}${d.lessons&&d.lessons.length?`<div class="mini">lessons shown: ${d.lessons.map(esc).join(" · ")}</div>`:""}${d.skill?`<div class="mini">skill hint: ${d.skill}</div>`:""}</div></div>
   <div class="row"><b>6 choice</b><div>${chip(d.choice,"pick"+(tf.has(d.choice)?" truth":""))} ${o?(ok?"<span class=ok>✔ worked</span>":"<span class=bad>✘ failed</span>")+` <span class="mini">${esc(o.feedback)}</span>`:""}</div></div>
   ${r.refl?`<div class="row"><b>7 reflection</b><div class="mini">culprit <b class="warn">${r.refl.prop||"unknown"}</b> via ${r.refl.source}${r.lesson?` → stored “${esc(r.lesson.text)}”`:""}</div></div>`:""}`}

/* ---------------- state tabs ---------------- */
function renderLessons(){const L=state.lessons.slice().sort((a,b)=>b.conf-a.conf||b.support-a.support);
  $("lessons").innerHTML=L.length?L.map(l=>{const col=truth?(l.true?C.green:C.red):C.cyan;return `<div class="lrow"><span>${esc(l.text)}</span><div class="lbar"><i style="width:${l.conf*100}%;background:${col}"></i></div><span class="mini">+${l.support}/−${l.contra}</span></div>`}).join(""):"<p class='note'>no lessons yet</p>"}
function renderWM(){if(!state)return;const dm=$("wmDom").value||"grasp",m=state.wm[dm];const cv=$("wmcv"),{g,w,h}=HUD.fit(cv);g.clearRect(0,0,w,h);if(!m)return;const ml=84,mt=28,cw=(w-ml-6)/m.props.length,ch=(h-mt-6)/m.actions.length;g.font="10px 'Share Tech Mono',monospace";
  m.props.forEach((p,j)=>{g.fillStyle=C.muted;g.textAlign="center";g.fillText(p,ml+j*cw+cw/2,mt-8)});
  m.actions.forEach((a,i)=>{g.fillStyle=C.muted;g.textAlign="right";g.fillText(a,ml-6,mt+i*ch+ch/2+3);m.props.forEach((p,j)=>{const v=m.pred[i][j],x=ml+j*cw,y=mt+i*ch;
    g.fillStyle=v===null?"rgba(120,140,150,.18)":`rgb(${Math.round(255*(1-v))},${Math.round(60+170*v)},${Math.round(80)})`;g.fillRect(x+1,y+1,cw-2,ch-2);
    if(v!==null){g.fillStyle="#001018";g.textAlign="center";g.fillText(v.toFixed(2),x+cw/2,y+ch/2+3)}
    if(truth&&m.truth[i][j]){g.strokeStyle=C.red;g.lineWidth=2;g.strokeRect(x+2,y+2,cw-4,ch-4);g.lineWidth=1}})})}
function renderSkills(){$("skills").innerHTML=state.skills.length?state.skills.map(s=>`<div class="lrow"><span>[${s[0]}] ${s[1].join("+")} → <b>${s[2]}</b></span><span></span><span class="mini">×${s[3]}</span></div>`).join(""):"<p class='note'>no skills yet</p>"}
function renderCur(){const c=state.curriculum;$("curr").innerHTML=`<p class="note">policy <b>${c.policy}</b> · unlocked: ${c.unlocked.map(u=>`<span class="tag g">${u}</span>`).join("")}</p>`+c.activities.map(a=>{const r=c.rates[a],lp=c.lp[a],sh=c.shares[a]||0,tot=Object.values(c.shares).reduce((x,y)=>x+y,0)||1;
    return `<div style="margin:8px 0"><div class="mini">${a} · success(10) ${r===null?"—":Math.round(r*100)+"%"} · LP ${lp} · ${c.counts[a]} tries · share ${Math.round(sh/tot*100)}%</div><div class="lbar"><i style="width:${(r||0)*100}%;background:${C.green}"></i></div><div class="lbar" style="margin-top:2px"><i style="width:${Math.min(100,lp*100)}%;background:${C.gold}"></i></div></div>`}).join("")+`<p class="mini">green = recent success · gold = learning-progress score that steers curiosity</p>`}
function renderMods(){const cfg=state.cfg;const items=[["memory","Memory (lessons in prompt)"],["reflection","Reflection"],["lesson_filter","Lesson filter (hard constraint)"],["skills","Skill library"],["worldmodel","Imagination (world model)"],["consolidation","Sleep / consolidation"]];
  $("mods").innerHTML=items.map(([k,l])=>`<div class="toggle"><span>${l}</span><input type="checkbox" data-m="${k}" ${cfg[k]?"checked":""}></div>`).join("")+`<div class="toggle"><span>Curiosity chooser</span><select id="curSel">${["lp","random","sequential"].map(p=>`<option ${cfg.curiosity===p?"selected":""}>${p}</option>`).join("")}</select></div>`;
  $("mods").querySelectorAll("input[data-m]").forEach(el=>el.onchange=()=>post({action:"toggle",module:el.dataset.m,value:el.checked}));$("curSel").onchange=e=>post({action:"toggle",module:"curiosity",value:e.target.value})}
function renderCurve(){const c=state.curve,ys=c.map((_,i)=>{const s=c.slice(Math.max(0,i-19),i+1);return s.reduce((a,b)=>a+b,0)/s.length});
  HUD.line($("curve"),[{x:ys.map((_,i)=>i),y:ys,color:C.gold,width:2}],{xmin:0,xmax:Math.max(60,ys.length),ymin:0,ymax:1,ny:4,ml:36,mb:22,mt:6,yfmt:v=>(v*100|0)+"%",xlabel:"task"});
  const last=c.slice(-20);$("sSucc").textContent=last.length?Math.round(last.reduce((a,b)=>a+b,0)/last.length*100)+"%":"—"}
let modsKey="";
function renderState(){if(!state)return;const s=state;$("tick").textContent=s.tick;$("calls").textContent=s.llm_calls;$("status").innerHTML=(s.running?"<span class=ok>● RUNNING</span>":"<span class=warn>❚❚ PAUSED</span>")+` · ${s.llm_mode==="ollama"?s.model:"stub LLM"} · seed ${s.seed}`+(s.error?` · <span class=bad>${esc(s.error)}</span>`:"");
  $("bRun").textContent=s.running?"❚❚ PAUSE":"▶ RUN";$("sLes").textContent=s.stats.lessons;$("sPrec").textContent=s.stats.lesson_precision===null?"—":Math.round(s.stats.lesson_precision*100)+"%";$("sStage").textContent=s.curriculum.unlocked.length+"/4";
  renderLessons();renderSkills();renderCur();renderCurve();renderWM();const k=JSON.stringify(s.cfg);if(k!==modsKey){modsKey=k;renderMods()}}
async function pollState(){try{state=await (await fetch("/state")).json();renderState();$("status").style.opacity=1}catch(e){$("status").textContent="server offline"}}
async function pollEvents(){try{const r=await (await fetch("/events?since="+since)).json();r.events.forEach(onEvent);if(r.last<since)since=0;else since=r.last;if(r.events.length)lastState=0}catch(e){}}
function init(){HUD.tabs($("tabsroot"),()=>renderWM());
  ["grasp","carry","stack","tool"].forEach(d=>$("wmDom").insertAdjacentHTML("beforeend",`<option>${d}</option>`));$("wmDom").onchange=renderWM;
  fetch("/state").then(r=>r.json()).then(s=>{s.configs.forEach(c=>$("cfgSel").insertAdjacentHTML("beforeend",`<option ${c==="full"?"selected":""}>${c}</option>`))});
  $("bRun").onclick=()=>post({action:state&&state.running?"pause":"run"});$("bStep").onclick=()=>post({action:"step"});
  $("bReset").onclick=async()=>{logEl.innerHTML="";decisions=[];sel=-1;since=0;await post({action:"reset",seed:+$("seed").value,config:$("cfgSel").value,llm_mode:$("llmSel").value,model:$("model").value});renderDecision()};
  $("spd").oninput=e=>{$("spdv").textContent=e.target.value;post({action:"speed",value:+e.target.value})};
  $("truth").onchange=e=>{truth=e.target.checked;renderDecision();if(state){renderLessons();renderWM()}};
  $("llmSel").onchange=e=>{if(e.target.value==="ollama")alert("Ollama mode shares the local Ollama server with any benchmark you have running — both will slow down. Press RESET to apply.")};
  renderDecision();pollState();setInterval(pollState,700);setInterval(pollEvents,250);(function loop(){drawCircuit();requestAnimationFrame(loop)})();window.addEventListener("resize",()=>{renderWM();if(state)renderCurve()})}
window.addEventListener("DOMContentLoaded",init);
})();
