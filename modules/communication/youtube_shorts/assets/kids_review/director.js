import {mountNarration} from './story-narration.mjs';
import {bindPanelGestures} from '../storytime/panel-gestures.mjs';
import {locales,normalizeLocale} from '../storytime/learning-events.mjs';
const $=id=>document.getElementById(id),game=$('game'),ink=$('ink');
const revision='slow-rescue-11',key='eduit.game-feedback.v2.'+revision;
let capture=null,strokes=[],drawing=null,entries=[],activePointer=null,childLocked=false;
const pointers=new Set();let inkBlocked=false,history=[];
function rememberInk(){history.push(structuredClone(strokes));if(history.length>50)history.shift();}
try{const saved=JSON.parse(localStorage.getItem(key)||'[]');if(Array.isArray(saved))entries=saved.filter(e=>e?.capture&&typeof e.capture.svg==='string'&&e.capture.svg.length<100000&&Number.isFinite(e.capture.clock)&&e.capture.clock>=0&&e.capture.clock<=86400&&typeof e.note==='string'&&e.note.length<=4000&&Array.isArray(e.strokes)&&e.strokes.length<=200&&e.strokes.every(line=>Array.isArray(line)&&line.length<=3000&&line.every(p=>Array.isArray(p)&&p.length===2&&p.every(n=>Number.isFinite(n)&&n>=0&&n<=1)))).slice(-20);}catch{}
const api=()=>game.contentWindow?.storytimeReview;
function paint(){if(ink.hidden)return;const r=ink.getBoundingClientRect(),d=devicePixelRatio;ink.width=r.width*d;ink.height=r.height*d;const ctx=ink.getContext('2d');ctx.strokeStyle='#ef426f';ctx.lineWidth=3*d;ctx.lineCap='round';ctx.lineJoin='round';for(const line of strokes){ctx.beginPath();line.forEach(([x,y],i)=>i?ctx.lineTo(x*ink.width,y*ink.height):ctx.moveTo(x*ink.width,y*ink.height));ctx.stroke();}}
function show(){$('game-panel').classList.add('marking');$('feedback-actions').hidden=false;game.hidden=true;$('frozen').hidden=false; // SVG originates exclusively in the local scene renderer.
 const doc=new DOMParser().parseFromString(capture.svg,'image/svg+xml');
 // Reopened local feedback cannot introduce scripts, foreign objects or external references.
 const safeTags=new Set(['svg','defs','g','path','ellipse','circle','text','rect','use']);
 doc.querySelectorAll('*').forEach(n=>{if(n.namespaceURI!=='http://www.w3.org/2000/svg'||!safeTags.has(n.localName))n.remove();});
 doc.querySelectorAll('*').forEach(n=>[...n.attributes].forEach(a=>{if(/^on/i.test(a.name)||(/href/i.test(a.name)&&!/^#[a-zA-Z][\w-]*$/.test(a.value))||/url\(/i.test(a.value))n.removeAttribute(a.name);}));
 $('frozen').replaceChildren(document.importNode(doc.documentElement,true));ink.hidden=false;$('tools').hidden=false;paint();}
function play(){$('game-panel').classList.remove('marking');$('feedback-actions').hidden=true;$('video').pause();ink.hidden=true;$('frozen').hidden=true;$('tools').hidden=true;game.hidden=false;drawing=null;activePointer=null;api()?.play();}
$('play').onclick=()=>{if(['playing','celebrating'].includes(api()?.status().phase)&&!api()?.status().paused)api()?.pause();else play();};$('close').onclick=$('resume-game').onclick=play;
$('feedback').onclick=()=>{if(childLocked)return;options.hidden=true;const current=api()?.freeze();if(!current)return;$('video').pause();if(!capture||capture.clock!==current.clock||capture.locale!==current.locale||JSON.stringify(capture.state)!==JSON.stringify(current.state)){if(capture)saveDraft();capture=current;strokes=[];history=[];$('note').value='';}show();};
const point=e=>{const r=ink.getBoundingClientRect();return [Math.max(0,Math.min(1,(e.clientX-r.left)/r.width)),Math.max(0,Math.min(1,(e.clientY-r.top)/r.height))];};
ink.onpointerdown=e=>{pointers.add(e.pointerId);if(pointers.size>1){if(drawing){strokes.pop();history.pop();}drawing=null;activePointer=null;inkBlocked=true;paint();return;}if(inkBlocked||activePointer!==null)return;activePointer=e.pointerId;e.preventDefault();ink.setPointerCapture(e.pointerId);rememberInk();drawing=[point(e)];strokes.push(drawing);paint();};ink.onpointermove=e=>{if(drawing&&e.pointerId===activePointer){drawing.push(point(e));paint();}};ink.onpointerup=ink.onpointercancel=ink.onlostpointercapture=e=>{pointers.delete(e.pointerId);if(e.pointerId===activePointer){drawing=null;activePointer=null;}if(!pointers.size)inkBlocked=false;};
$('undo').onclick=$('mark-undo').onclick=()=>{if(history.length)strokes=history.pop();paint();};$('clear').onclick=$('mark-clear').onclick=()=>{if(strokes.length){rememberInk();strokes=[];paint();}};
function record(){return JSON.stringify({schema:'eduit.creator_feedback.v2',revision,episode:'little-shrew-01',coordinate_space:'normalized-game-frame',entries,draft:capture?{capture,strokes,note:$('note').value}:null},null,2);}
function list(){$('saved').replaceChildren();entries.forEach((e,i)=>{const b=document.createElement('button');b.textContent=`${i+1} · ${e.capture.phase} · ${e.capture.clock.toFixed(2)}s`;b.onclick=()=>{api()?.freeze();if(capture)saveDraft();capture=structuredClone(e.capture);history=[];strokes=structuredClone(e.strokes);$('note').value=e.note;show();};$('saved').append(b);});$('record').value=record();}
function saveDraft(){if(!capture)return;entries.push({capture:structuredClone(capture),strokes:structuredClone(strokes),note:$('note').value.trim()});entries=entries.slice(-20);try{localStorage.setItem(key,JSON.stringify(entries));$('status').textContent='Saved on this device. Copy to share with 0102.';}catch{$('status').textContent='Storage full. Copy your feedback before leaving.';}list();}
$('save').onclick=saveDraft;
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
 if(childLocked&&!on)return;
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
bindPanelGestures(gamePanel,{expand:()=>expand(gamePanel,true),collapse:()=>expand(gamePanel,false)});

let language='en';try{language=normalizeLocale(localStorage.getItem('eduit.game-language'));}catch{}
const languageBar=$('languages');
function chooseLanguage(value){if(childLocked)return;video.pause();language=normalizeLocale(value);api()?.pause();api()?.setLocale(language);try{localStorage.setItem('eduit.game-language',language);}catch{}languageBar.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.locale===language)));}
for(const [id,l] of Object.entries(locales)){const button=document.createElement('button');button.dataset.locale=id;button.lang=id;button.setAttribute('aria-label',l.label);const flag=document.createElement('img');flag.src=new URL('flags/'+({en:'gb',ja:'jp',pt:'pt',es:'es'}[id])+'.svg',import.meta.url).href;flag.alt='';flag.width=36;flag.height=24;button.title=l.label;button.append(flag);button.onclick=()=>chooseLanguage(id);languageBar.append(button);}
game.addEventListener('load',()=>chooseLanguage(language));chooseLanguage(language);

if('serviceWorker' in navigator)navigator.serviceWorker.register(new URL('../storytime-sw.js',import.meta.url),{scope:new URL('../',import.meta.url).pathname}).catch(()=>{});

// One panel-owned control rail; no duplicate player or game state.
const paths={play:'M8 5l12 7-12 7Z',pause:'M8 5v14M16 5v14',pencil:'M4 20l4-1L20 7l-3-3L5 16Z M14 7l3 3',film:'M3 5h18v14H3Z M7 5v14M17 5v14 M3 10h4m10 0h4M3 14h4m10 0h4',game:'M7 7h10q4 0 4 5v5q0 4-5-1H8q-5 5-5 1v-5q0-5 4-5Z M7 10v4m-2-2h4m6-1h1m2 2h1',more:'M5 12h1m5 0h1m5 0h1',lock:'M6 10h12v11H6Z M8 10V6a4 4 0 0 1 8 0v4',undo:'M9 5L3 10l6 5 M4 10h10q6 0 6 7',clear:'M4 7h16M9 7V4h6v3M6 7l1 14h10l1-14M10 10v7m4-7v7',share:'M12 16V3m-5 5 5-5 5 5M5 13v8h14v-8'};
function icon(kind){return `<svg viewBox="0 0 24 24" aria-hidden="true" fill="${kind==='play'?'currentColor':'none'}" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="${paths[kind]}"/></svg>`;}
function button(id,label,kind,host,action){const b=document.createElement('button');b.id=id;b.setAttribute('aria-label',label);b.title=label;b.innerHTML=icon(kind);b.onclick=action;host.append(b);return b;}
for(const [id,kind] of [['play','play'],['feedback','pencil'],['mark-undo','undo'],['mark-clear','clear'],['share-image','share'],['resume-game','play']])$(id).innerHTML=icon(kind);
$('feedback').classList.add('adult-control');
const videoRail=document.createElement('nav');videoRail.className='video-controls';videoRail.setAttribute('aria-label','Video controls');videoPanel.append(videoRail);
button('video-play','Play video','play',videoRail,()=>{api()?.pause();if(video.paused)video.play().catch(()=>{});else video.pause();});
function switchTo(panel){video.pause();api()?.pause();expand(panel,true);}
button('to-game','Play the game','game',videoRail,()=>switchTo(gamePanel));
button('to-video','Watch the video','film',document.querySelector('.game-controls'),()=>switchTo(videoPanel));
const options=document.createElement('section');options.id='options';options.hidden=true;options.setAttribute('aria-label','Grown-up options');document.body.append(options);
function openOptions(){video.pause();api()?.pause();options.hidden=!options.hidden;if(!options.hidden)options.querySelector('button').focus();}
for(const [id,rail] of [['video-options',videoRail],['game-options',document.querySelector('.game-controls')]])button(id,'Grown-up options','more',rail,openOptions).classList.add('adult-control');
const repeat=button('repeat','Repeat video','undo',options,()=>{video.loop=!video.loop;repeat.setAttribute('aria-pressed',String(video.loop));repeat.textContent=video.loop?'Repeat video: on':'Repeat video: off';});repeat.textContent='Repeat video: off';repeat.setAttribute('aria-pressed','false');
const unlock=button('unlock','Hold to unlock controls','lock',document.body,()=>{});unlock.hidden=true;
function lock(on){if(on){if(capture)saveDraft();api()?.pause();video.pause();$('game-panel').classList.remove('marking');$('feedback-actions').hidden=true;ink.hidden=true;$('frozen').hidden=true;$('tools').hidden=true;game.hidden=false;}childLocked=on;document.body.classList.toggle('child-locked',on);unlock.hidden=!on;options.hidden=true;}
const lockButton=button('lock-child','Child lock','lock',options,()=>{if(!document.querySelector('.unit.expanded'))expand(gamePanel,true);lock(true);});lockButton.textContent='Child lock';
const restart=button('restart-game','Restart game','undo',options,()=>{if(capture)saveDraft();api()?.reset();$('game-panel').classList.remove('marking');$('feedback-actions').hidden=true;ink.hidden=true;$('frozen').hidden=true;$('tools').hidden=true;game.hidden=false;options.hidden=true;});restart.textContent='Restart game';
const practice=button('practice-game','Untimed practice','game',options,()=>{const next=!api()?.status().practice;restart.click();api()?.setPractice(next);practice.setAttribute('aria-pressed',String(next));practice.textContent=next?'Untimed practice: on':'Untimed practice: off';options.hidden=true;});practice.textContent='Untimed practice: off';practice.setAttribute('aria-pressed','false');
const optionsClose=button('close-options','Close options','more',options,()=>{options.hidden=true;});optionsClose.textContent='Done';
let hold=null;const cancelHold=()=>{clearTimeout(hold);hold=null;};
function beginHold(e){if(e.type==='keydown'&&![' ','Enter'].includes(e.key))return;if(hold)return;e.preventDefault();hold=setTimeout(()=>{cancelHold();if(confirm('Unlock grown-up controls?'))lock(false);},1200);}
unlock.onpointerdown=beginHold;unlock.onkeydown=beginHold;unlock.onpointerup=unlock.onpointercancel=unlock.onpointerleave=unlock.onkeyup=unlock.onblur=cancelHold;
window.addEventListener('keydown',e=>{if(e.key==='Escape'){options.hidden=true;}});
let lastPlay='';setInterval(()=>{const state=api()?.status(),running=['playing','celebrating'].includes(state?.phase)&&!state.paused;const label=running?'Pause game':state?.phase==='over'?'Replay game':'Play game';if(label!==lastPlay){$('play').innerHTML=icon(running?'pause':'play');$('play').setAttribute('aria-label',label);lastPlay=label;}$('video-play').innerHTML=icon(video.paused?'play':'pause');$('video-play').setAttribute('aria-label',video.paused?'Play video':'Pause video');},200);
document.addEventListener('visibilitychange',()=>{if(document.hidden){video.pause();api()?.pause();}});
const picture=document.createElement('dialog');picture.id='picture';picture.setAttribute('aria-label','Your marked picture');document.body.append(picture);
let pictureURL=null;
$('share-image').onclick=async()=>{if(!capture)return;saveDraft();const svg=$('frozen').querySelector('svg');if(!svg)return;const source=URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(svg)],{type:'image/svg+xml'}));try{const img=new Image();img.src=source;await img.decode();const canvas=document.createElement('canvas');canvas.width=1920;canvas.height=1080;const ctx=canvas.getContext('2d');ctx.drawImage(img,0,0,1920,1080);ctx.strokeStyle='#ef426f';ctx.lineWidth=6;ctx.lineCap='round';ctx.lineJoin='round';for(const line of strokes){ctx.beginPath();line.forEach(([x,y],i)=>i?ctx.lineTo(x*1920,y*1080):ctx.moveTo(x*1920,y*1080));ctx.stroke();}const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));if(!blob)throw Error('Image unavailable');if(pictureURL)URL.revokeObjectURL(pictureURL);pictureURL=URL.createObjectURL(blob);picture.replaceChildren();const preview=new Image();preview.src=pictureURL;preview.alt='Frozen game with your marks';picture.append(preview);const file=new File([blob],'storytime-note.png',{type:'image/png'});if(navigator.canShare?.({files:[file]})){const share=button('send-picture','Share picture','share',picture,async()=>{try{await navigator.share({files:[file]});}catch(e){if(e.name!=='AbortError')share.title='Sharing unavailable. Take a screen capture.';}});}const close=button('close-picture','Close picture','undo',picture,()=>picture.close());picture.showModal();}catch{$('status').textContent='Picture could not be prepared. Your marks are retained; use a screen capture.';}finally{URL.revokeObjectURL(source);}};

// Information opens without navigating away or consuming the child's active round.
const storyInfo=$('story-info');let infoReturn=null;
function openInfo(section){if(childLocked)return;video.pause();api()?.pause();options.hidden=true;infoReturn=document.activeElement;$('about-content').hidden=section!=='about';$('how-content').hidden=section!=='how';storyInfo.setAttribute('aria-label',section==='about'?'About EDUIT':'How to play');storyInfo.removeAttribute('aria-labelledby');storyInfo.showModal();$('info-close').focus();}
$('about-open').onclick=()=>openInfo('about');$('how-open').onclick=()=>openInfo('how');$('info-close').onclick=()=>storyInfo.close();
storyInfo.addEventListener('close',()=>infoReturn?.focus());

// One-time illustrated pre-video story. Does not auto-play media or collect child data.
const introDialog=$('story-intro'),introSeenKey='eduit.storytime.intro-seen.v1';
let introReturn=null,introClosing=false;
function openStoryIntro(){if(childLocked||introDialog.open)return;video.pause();api()?.pause();introReturn=document.activeElement;introDialog.classList.remove('intro-collapsing');introDialog.showModal();$('intro-close').focus();}
function finishStoryIntro(){if(introClosing||!introDialog.open)return;introClosing=true;try{localStorage.setItem(introSeenKey,'1');}catch{}const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;if(!reduced)introDialog.classList.add('intro-collapsing');const close=()=>{introDialog.close();introDialog.classList.remove('intro-collapsing');introClosing=false;$('video').focus({preventScroll:true});$('video-panel').scrollIntoView({block:'nearest',behavior:'instant'});};if(reduced)close();else {introDialog.addEventListener('animationend',close,{once:true});setTimeout(()=>{if(introClosing)close();},350);}}
$('intro-skip').addEventListener('click',finishStoryIntro);
$('intro-close').addEventListener('click',finishStoryIntro);
$('intro-replay').addEventListener('click',openStoryIntro);
introDialog.addEventListener('cancel',event=>{event.preventDefault();finishStoryIntro();});
introDialog.addEventListener('close',()=>{if(!introClosing)introReturn?.focus();});
let introSeen=false;try{introSeen=localStorage.getItem(introSeenKey)==='1';}catch{}
if(!introSeen)queueMicrotask(openStoryIntro);


// Narration is an English overlay over the retained film, not regenerated media.
const narration=mountNarration(video,$('story-caption'));
window.storytimeNarration=narration;
const voiceOption=button('story-voice','English story voice','more',options,()=>{const enabled=voiceOption.getAttribute('aria-pressed')!=='true';voiceOption.setAttribute('aria-pressed',String(enabled));voiceOption.textContent=enabled?'English story voice: on':'English story voice: off';narration.setEnabled(enabled);});
voiceOption.setAttribute('aria-pressed','true');voiceOption.textContent='English story voice: on';
