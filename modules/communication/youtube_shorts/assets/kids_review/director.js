import {bindPanelGestures} from '../storytime/panel-gestures.mjs';
import {locales,normalizeLocale} from '../storytime/learning-events.mjs';
const $=id=>document.getElementById(id),game=$('game'),ink=$('ink');
const revision='sound-languages-9',key='eduit.game-feedback.v2.'+revision;
let capture=null,strokes=[],drawing=null,entries=[],activePointer=null;
try{const saved=JSON.parse(localStorage.getItem(key)||'[]');if(Array.isArray(saved))entries=saved.filter(e=>e?.capture&&typeof e.capture.svg==='string'&&e.capture.svg.length<100000&&Number.isFinite(e.capture.clock)&&e.capture.clock>=0&&e.capture.clock<=15&&typeof e.note==='string'&&e.note.length<=4000&&Array.isArray(e.strokes)&&e.strokes.length<=200&&e.strokes.every(line=>Array.isArray(line)&&line.length<=3000&&line.every(p=>Array.isArray(p)&&p.length===2&&p.every(n=>Number.isFinite(n)&&n>=0&&n<=1)))).slice(-20);}catch{}
const api=()=>game.contentWindow?.storytimeReview;
function paint(){if(ink.hidden)return;const r=ink.getBoundingClientRect(),d=devicePixelRatio;ink.width=r.width*d;ink.height=r.height*d;const ctx=ink.getContext('2d');ctx.strokeStyle='#ef426f';ctx.lineWidth=3*d;ctx.lineCap='round';ctx.lineJoin='round';for(const line of strokes){ctx.beginPath();line.forEach(([x,y],i)=>i?ctx.lineTo(x*ink.width,y*ink.height):ctx.moveTo(x*ink.width,y*ink.height));ctx.stroke();}}
function show(){game.hidden=true;$('frozen').hidden=false; // SVG originates exclusively in the local scene renderer.
 const doc=new DOMParser().parseFromString(capture.svg,'image/svg+xml');
 // Reopened local feedback cannot introduce scripts, foreign objects or external references.
 const safeTags=new Set(['svg','defs','g','path','ellipse','circle','text','rect','use']);
 doc.querySelectorAll('*').forEach(n=>{if(n.namespaceURI!=='http://www.w3.org/2000/svg'||!safeTags.has(n.localName))n.remove();});
 doc.querySelectorAll('*').forEach(n=>[...n.attributes].forEach(a=>{if(/^on/i.test(a.name)||(/href/i.test(a.name)&&!/^#[a-zA-Z][\w-]*$/.test(a.value))||/url\(/i.test(a.value))n.removeAttribute(a.name);}));
 $('frozen').replaceChildren(document.importNode(doc.documentElement,true));ink.hidden=false;$('tools').hidden=false;paint();}
function play(){$('video').pause();ink.hidden=true;$('frozen').hidden=true;$('tools').hidden=true;game.hidden=false;drawing=null;activePointer=null;api()?.play();}
$('play').onclick=$('close').onclick=play;
$('feedback').onclick=()=>{expand(gamePanel,false);const current=api()?.freeze();if(!current)return;$('video').pause();capture=current;strokes=[];$('note').value='';show();};
const point=e=>{const r=ink.getBoundingClientRect();return [Math.max(0,Math.min(1,(e.clientX-r.left)/r.width)),Math.max(0,Math.min(1,(e.clientY-r.top)/r.height))];};
ink.onpointerdown=e=>{if(activePointer!==null)return;activePointer=e.pointerId;e.preventDefault();ink.setPointerCapture(e.pointerId);drawing=[point(e)];strokes.push(drawing);paint();};ink.onpointermove=e=>{if(drawing&&e.pointerId===activePointer){drawing.push(point(e));paint();}};ink.onpointerup=ink.onpointercancel=ink.onlostpointercapture=e=>{if(e.pointerId===activePointer){drawing=null;activePointer=null;}};
$('undo').onclick=()=>{strokes.pop();paint();};$('clear').onclick=()=>{strokes=[];paint();};
function record(){return JSON.stringify({schema:'eduit.creator_feedback.v2',revision,episode:'little-shrew-01',coordinate_space:'normalized-game-frame',entries},null,2);}
function list(){$('saved').replaceChildren();entries.forEach((e,i)=>{const b=document.createElement('button');b.textContent=`${i+1} · ${e.capture.phase} · ${e.capture.clock.toFixed(2)}s`;b.onclick=()=>{api()?.freeze();capture=e.capture;strokes=structuredClone(e.strokes);$('note').value=e.note;show();};$('saved').append(b);});$('record').value=record();}
$('save').onclick=()=>{if(!capture)return;entries.push({capture:structuredClone(capture),strokes:structuredClone(strokes),note:$('note').value.trim()});entries=entries.slice(-20);try{localStorage.setItem(key,JSON.stringify(entries));$('status').textContent='Saved on this device. Copy to share with 0102.';}catch{$('status').textContent='Storage full. Copy your feedback before leaving.';}list();};
$('copy').onclick=async()=>{try{await navigator.clipboard.writeText(record());$('status').textContent='Copied. Paste into our conversation.';}catch{$('record').hidden=false;$('record').select();$('status').textContent='Copy the record below.';}};
$('video').onplay=()=>api()?.freeze();new ResizeObserver(paint).observe(ink);list();

const gamePanel=$('game-panel'),videoPanel=$('video-panel'),video=$('video');
const expandIcon='<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 3H3v6m12-6h6v6M3 15v6h6m12-6v6h-6"/></svg>';
const collapseIcon='<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9h6V3m6 0v6h6M9 21v-6H3m12 6v-6h6"/></svg>';
let lastViewport="";
function viewport(){const v=window.visualViewport;const width=v?.scale===1?v.width:window.innerWidth,height=v?.scale===1?v.height:window.innerHeight;const size=width+'x'+height;if(lastViewport&&size!==lastViewport)api()?.pause();lastViewport=size;document.documentElement.style.setProperty('--app-width',width+'px');document.documentElement.style.setProperty('--app-height',height+'px');}
window.addEventListener('resize',viewport);window.addEventListener('orientationchange',viewport);window.visualViewport?.addEventListener('resize',viewport);viewport();
let focusReturn=null;
function expand(el,on){
 if(on&&!document.body.classList.contains("focused"))focusReturn=document.activeElement;
 if(el===gamePanel){video.pause();api()?.pause();}else api()?.pause();
 document.querySelectorAll('.expanded').forEach(n=>n.classList.remove('expanded'));
 if(on)el.classList.add('expanded');document.body.classList.toggle('focused',on);
 for(const [panel,id,label] of [[videoPanel,'full-video','video'],[gamePanel,'full-game','game']]){const active=panel.classList.contains('expanded'),button=$(id);button.setAttribute('aria-expanded',String(active));button.setAttribute('aria-label',(active?'Collapse ':'Expand ')+label);button.innerHTML=active?collapseIcon:expandIcon;}
 for(const sibling of document.querySelector('main').children){if(on&&sibling!==el)sibling.setAttribute('inert','');else sibling.removeAttribute('inert');}
 if(on)el.querySelector('.expand-button').focus({preventScroll:true});else if(focusReturn?.isConnected){focusReturn.focus({preventScroll:true});focusReturn=null;}
 viewport();
}
$('full-game').onclick=()=>expand(gamePanel,!gamePanel.classList.contains('expanded'));
$('full-video').onclick=()=>expand(videoPanel,!videoPanel.classList.contains('expanded'));
window.addEventListener('keydown',e=>{const panel=document.querySelector('.unit.expanded');if(e.key==='Escape'&&panel)expand(panel,false);});
expand(gamePanel,false);
window.addEventListener('message',e=>{if(e.origin===location.origin&&e.source===game.contentWindow&&e.data?.type==='storytime.fullscreen')expand(gamePanel,e.data.expanded===true);});
bindPanelGestures(videoPanel,{expand:()=>expand(videoPanel,true),collapse:()=>expand(videoPanel,false)});
bindPanelGestures(gamePanel,{expand:()=>{if(ink.hidden)expand(gamePanel,true);},collapse:()=>{if(ink.hidden)expand(gamePanel,false);}});

let language='en';try{language=normalizeLocale(localStorage.getItem('eduit.game-language'));}catch{}
const languageBar=$('languages');
function chooseLanguage(value){language=normalizeLocale(value);api()?.pause();api()?.setLocale(language);try{localStorage.setItem('eduit.game-language',language);}catch{}languageBar.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.locale===language)));}
for(const [id,l] of Object.entries(locales)){const button=document.createElement('button');button.dataset.locale=id;button.lang=id;button.setAttribute('aria-label',l.label);const flag=document.createElement('img');flag.src=new URL('flags/'+({en:'gb',ja:'jp',pt:'pt',es:'es'}[id])+'.svg',import.meta.url).href;flag.alt='';flag.width=36;flag.height=24;button.title=l.label;button.append(flag);button.onclick=()=>chooseLanguage(id);languageBar.append(button);}
game.addEventListener('load',()=>chooseLanguage(language));chooseLanguage(language);

if('serviceWorker' in navigator)navigator.serviceWorker.register(new URL('../storytime-sw.js',import.meta.url),{scope:new URL('../',import.meta.url).pathname}).catch(()=>{});
