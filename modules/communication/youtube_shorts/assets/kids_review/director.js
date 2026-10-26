const $=id=>document.getElementById(id),game=$('game'),ink=$('ink');
const revision='rescue-five-7',key='eduit.game-feedback.v2.'+revision;
let capture=null,strokes=[],drawing=null,entries=[];
try{const saved=JSON.parse(localStorage.getItem(key)||'[]');if(Array.isArray(saved))entries=saved.filter(e=>e?.capture?.svg&&Array.isArray(e.strokes)).slice(-20);}catch{}
const api=()=>game.contentWindow?.storytimeReview;
function paint(){if(ink.hidden)return;const r=ink.getBoundingClientRect(),d=devicePixelRatio;ink.width=r.width*d;ink.height=r.height*d;const ctx=ink.getContext('2d');ctx.strokeStyle='#ef426f';ctx.lineWidth=3*d;ctx.lineCap='round';ctx.lineJoin='round';for(const line of strokes){ctx.beginPath();line.forEach(([x,y],i)=>i?ctx.lineTo(x*ink.width,y*ink.height):ctx.moveTo(x*ink.width,y*ink.height));ctx.stroke();}}
function show(){game.hidden=true;$('frozen').hidden=false; // SVG originates exclusively in the local scene renderer.
 const doc=new DOMParser().parseFromString(capture.svg,'image/svg+xml');
 // Reopened local feedback cannot introduce scripts, foreign objects or external references.
 doc.querySelectorAll('script,foreignObject,image,a,style').forEach(n=>n.remove());
 doc.querySelectorAll('*').forEach(n=>[...n.attributes].forEach(a=>{if(/^on/i.test(a.name)||(/href/i.test(a.name)&&!/^#[a-zA-Z][\w-]*$/.test(a.value))||/url\(/i.test(a.value))n.removeAttribute(a.name);}));
 $('frozen').replaceChildren(document.importNode(doc.documentElement,true));ink.hidden=false;$('tools').hidden=false;paint();}
function play(){$('video').pause();ink.hidden=true;$('frozen').hidden=true;$('tools').hidden=true;game.hidden=false;drawing=null;api()?.play();}
$('play').onclick=$('close').onclick=play;
$('feedback').onclick=()=>{const current=api()?.freeze();if(!current)return;$('video').pause();capture=current;strokes=[];$('note').value='';show();};
const point=e=>{const r=ink.getBoundingClientRect();return [Math.max(0,Math.min(1,(e.clientX-r.left)/r.width)),Math.max(0,Math.min(1,(e.clientY-r.top)/r.height))];};
ink.onpointerdown=e=>{e.preventDefault();ink.setPointerCapture(e.pointerId);drawing=[point(e)];strokes.push(drawing);paint();};ink.onpointermove=e=>{if(drawing){drawing.push(point(e));paint();}};ink.onpointerup=ink.onpointercancel=()=>drawing=null;
$('undo').onclick=()=>{strokes.pop();paint();};$('clear').onclick=()=>{strokes=[];paint();};
function record(){return JSON.stringify({schema:'eduit.creator_feedback.v2',revision,episode:'little-shrew-01',coordinate_space:'normalized-game-frame',entries},null,2);}
function list(){$('saved').replaceChildren();entries.forEach((e,i)=>{const b=document.createElement('button');b.textContent=`${i+1} · ${e.capture.phase} · ${e.capture.clock.toFixed(2)}s`;b.onclick=()=>{api()?.freeze();capture=e.capture;strokes=structuredClone(e.strokes);$('note').value=e.note;show();};$('saved').append(b);});$('record').value=record();}
$('save').onclick=()=>{if(!capture)return;entries.push({capture:structuredClone(capture),strokes:structuredClone(strokes),note:$('note').value.trim()});entries=entries.slice(-20);try{localStorage.setItem(key,JSON.stringify(entries));$('status').textContent='Saved on this device. Copy to share with 0102.';}catch{$('status').textContent='Storage full. Copy your feedback before leaving.';}list();};
$('copy').onclick=async()=>{try{await navigator.clipboard.writeText(record());$('status').textContent='Copied. Paste into our conversation.';}catch{$('record').hidden=false;$('record').select();$('status').textContent='Copy the record below.';}};
$('video').onplay=()=>api()?.freeze();new ResizeObserver(paint).observe(ink);list();

const gamePanel=document.querySelector('.stage'),video=$('video');
function expand(el,on){document.querySelectorAll('.expanded').forEach(n=>n.classList.remove('expanded'));if(on)el.classList.add('expanded');document.body.classList.toggle('focused',on);$('exit-full').hidden=!on;}
$('full-game').onclick=()=>expand(gamePanel,!gamePanel.classList.contains('expanded'));
$('full-video').onclick=()=>expand(video,!video.classList.contains('expanded'));
$('exit-full').onclick=()=>expand(gamePanel,false);
window.addEventListener('keydown',e=>{if(e.key==='Escape')expand(gamePanel,false);});
window.addEventListener('message',e=>{if(e.origin===location.origin&&e.source===game.contentWindow&&e.data?.type==='storytime.fullscreen')expand(gamePanel,e.data.expanded===true);});
window.gestureZone?.(video,{onPinchOut:()=>expand(video,true),onPinchIn:()=>expand(video,false)});
window.gestureZone?.(gamePanel,{onPinchOut:()=>{if(ink.hidden)expand(gamePanel,true);},onPinchIn:()=>{if(ink.hidden)expand(gamePanel,false);}});
