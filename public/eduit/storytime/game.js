import {bindPanelGestures} from './panel-gestures.mjs';
import {initial,advance,actorPose,DEADLINE} from './engine.mjs';
import {scene,scenePresentation} from './scene.mjs';
import * as artwork from './rig.mjs';
import {gameWorld,foleyVolume} from './game-world.mjs?rev=safe-sounds-26';
import {locales,normalizeLocale,localizeEvent} from './learning-events.mjs';
let locale='en',appearance='mamma';
const $=id=>document.getElementById(id),stage=$('scene');
let panelGestures;
const roundLabel=document.createElement('span');roundLabel.id='round-count';roundLabel.setAttribute('aria-live','polite');roundLabel.style.cssText='font-weight:800;font-size:clamp(16px,3vw,24px);padding:8px';$('retry').before(roundLabel);
$('retry').style.cssText='margin-left:auto;min-height:56px;min-width:64px;order:99';
const pulseStyle=document.createElement('style');pulseStyle.textContent='@keyframes eduitReplayPulse{50%{transform:scale(1.065);box-shadow:0 0 0 7px #f8d76b55}}#retry:not([hidden]){animation:eduitReplayPulse 1.5s ease-in-out infinite}@media(prefers-reduced-motion:reduce){#retry{animation:none!important}}';document.head.append(pulseStyle);
let state=initial(),last=0,paused=false,hitKey="";
let expandedPresentation=false;
// Fixed original Foley offsets do not follow the demonstration film's timeline.
const soundtrack=new Audio("assets/game-foley.wav");soundtrack.preload="auto";soundtrack.volume=.8;
let lastCue=null,audioEnabled=false,ctx=null,playedVictory=false,activeAudioCue=null;
function resetCueAudio(){soundtrack.pause();soundtrack.currentTime=0;lastCue=null;activeAudioCue=null;}
function synthImpact(){
 try{ctx ||= new (window.AudioContext||window.webkitAudioContext)();ctx.resume();const now=ctx.currentTime;
 const osc=ctx.createOscillator(),gain=ctx.createGain();osc.type='sine';osc.frequency.setValueAtTime(85,now);osc.frequency.exponentialRampToValueAtTime(34,now+.65);
 gain.gain.setValueAtTime(.001,now);gain.gain.exponentialRampToValueAtTime(.32,now+.025);gain.gain.exponentialRampToValueAtTime(.001,now+.8);
 osc.connect(gain).connect(ctx.destination);osc.start(now);osc.stop(now+.82);
 }catch(e){console.warn('Impact audio unavailable',e);}
}
function syncAudio(){if(paused||state.phase!=='playing')soundtrack.pause();}
function cueAudio(cue){
 if(!audioEnabled||paused||!['playing','celebrating'].includes(state.phase)){soundtrack.pause();return;}
 if(cue?.id==='victory-thump'&&!playedVictory){playedVictory=true;synthImpact();}
 soundtrack.volume=foleyVolume(cue||activeAudioCue);
 if(cue&&cue.id!==lastCue){soundtrack.pause();lastCue=cue.id;activeAudioCue=cue;soundtrack.currentTime=cue.sourceTime;soundtrack.play().catch(()=>{});}
 if(!cue)lastCue=null;
 if(activeAudioCue&&soundtrack.currentTime>=activeAudioCue.sourceTime+activeAudioCue.sourceDuration){soundtrack.pause();activeAudioCue=null;}
}
function enableAudio(){audioEnabled=true;soundtrack.volume=0;soundtrack.play().then(()=>{if(!lastCue||paused||!['playing','celebrating'].includes(state.phase))soundtrack.pause();soundtrack.volume=activeAudioCue?foleyVolume(activeAudioCue):0;}).catch(()=>{});}
const embedded=new URLSearchParams(location.search).get('embed')==='1';if(embedded)document.body.classList.add('embedded');
const hits=document.createElement('div');hits.className='rescue-targets';stage.after(hits);
for(const id of ['wake','root'])$(id).remove();
function act(e){if(panelGestures?.isPinching())return;if(e==='start'||e==='retry'){paused=false;resetCueAudio();playedVictory=false;enableAudio();}else if(paused)return;state=advance(state,e);if(e==='start'||e==='retry')syncAudio();draw();}
$('start').onclick=()=>act('start');$('retry').onclick=()=>act('retry');$('pause').onclick=()=>{paused=!paused;syncAudio();};
function draw(){
 const t=state.elapsed,poses=state.actors.map(a=>actorPose(a,t));
 const world=gameWorld(state,poses),cue=localizeEvent(world.cue,locale);cueAudio(cue);
 const bounds=stage.parentElement.getBoundingClientRect(),presentation=scenePresentation(bounds.width,bounds.height,expandedPresentation);
 const scale=Math.min(bounds.width/960,bounds.height/presentation.height);
 const worldWidth=960*scale,worldHeight=540*scale;
 for(const [name,value]of Object.entries({top:(bounds.height-worldHeight)/2,left:(bounds.width-worldWidth)/2,width:worldWidth,height:worldHeight}))
  stage.parentElement.style.setProperty('--world-'+name,value+'px');
 stage.innerHTML=scene({...world,cue,actors:poses,showWords:true,appearance,presentation});
 const svg=stage.querySelector('svg');const ns='http://www.w3.org/2000/svg';
 const score=document.createElementNS(ns,'text');score.setAttribute('x','35');score.setAttribute('y','510');score.setAttribute('fill','#FFF4D9');score.setAttribute('font-size','60');score.setAttribute('font-family','sans-serif');score.setAttribute('font-weight','bold');score.setAttribute('aria-label',`${state.score} points`);score.textContent=`★ ${state.score}`;svg.append(score);
 // Staggered sleeping cues and brief resistance bursts; keep tap-progress dots intact.
 for(const [i,a] of poses.filter(a=>a.status==='sleeping').entries()){
  const pulse=(t*.45+i*.31)%2.8;
  if(pulse<1.25||a.taps>0){const z=document.createElementNS(ns,'text');z.setAttribute('x',String(a.x+55*a.scale+((i%2)*14)));z.setAttribute('y',String(a.y-22-12*Math.min(pulse,1)));z.setAttribute('font-size',String(a.taps>0?32:22));z.setAttribute('font-weight','bold');z.setAttribute('fill','#FFF4D9');z.setAttribute('opacity',String(a.taps>0?.9:Math.max(.2,1-pulse/1.3)));z.textContent=a.taps>0?'Zzz':'Z';svg.append(z);}
 }
 for(const a of poses.filter(a=>a.status==='sleeping'&&a.taps>0)){const text=document.createElementNS(ns,'text');text.setAttribute('x',a.x+60*a.scale);text.setAttribute('y',a.y-12);text.setAttribute('font-size','42');text.setAttribute('fill','#173F43');text.textContent='●'.repeat(a.taps)+'○'.repeat(a.wakeTaps-a.taps);svg.append(text);}
 const award=state.awards.at(-1);if(award&&t-award.at<2){const pop=document.createElementNS(ns,'text');pop.setAttribute('x','820');pop.setAttribute('y','215');pop.setAttribute('text-anchor','middle');pop.setAttribute('font-size','60');pop.setAttribute('font-weight','bold');pop.setAttribute('fill','#FFF4D9');pop.textContent=`+${award.points}`;svg.append(pop);}
 const nextKey=state.phase+state.selected+state.actors.map(a=>a.status).join();
 if(nextKey!==hitKey){hitKey=nextKey;hits.replaceChildren();
 if(state.phase==='playing'&&(state.practice||t<DEADLINE)){
  for(const a of poses.filter(a=>['sleeping','wandering'].includes(a.status)&&state.selected===null)){
   const b=document.createElement('button');b.className='rescue-hit';b.setAttribute('aria-label',`Wake ${a.id}`);
   b.style.cssText=`left:${(a.x+20*a.scale)/9.6}%;top:${(a.y+20*a.scale)/5.4}%;width:${170*a.scale/9.6}%;height:${110*a.scale/5.4}%`;
   b.onclick=()=>act('select:'+a.id);hits.append(b);
  }
  if(state.actors.some(a=>a.id===state.selected&&a.status==='awake')){const b=document.createElement('button');b.className='rescue-hit';b.style.cssText='left:81%;top:43%;width:14%;height:30%';b.setAttribute('aria-label','Move selected shrew to root');b.onclick=()=>act('root');hits.append(b);}
 }
 }
 roundLabel.textContent=`Round ${state.round||1}/3`;
 const over=state.phase==='over',saved=state.actors.filter(a=>a.status==='safe').length;
 $('message').textContent=over?(saved===5?'Everyone is safe!':saved?`${saved} / 5 saved · ${state.score} points`:locales[locale].over):'';
 $('start').hidden=state.phase!=='ready';$('retry').hidden=!over;$('pause').hidden=!['playing','celebrating'].includes(state.phase);$('time').textContent='';
 let end=$('ending');if(!end){end=document.createElement('div');end.id='ending';stage.parentElement.append(end);}
 end.hidden=!over;if(over){end.replaceChildren();const text=document.createElement('span');text.textContent=saved===5?'Everyone is safe!':saved?`${saved} / 5 ★ ${state.score}`:locales[locale].over;text.setAttribute('aria-label',saved?`${saved} of 5 shrews saved, ${state.score} points`:locales[locale].over);const button=document.createElement('button');button.textContent='↻';button.setAttribute('aria-label',locales[locale].again);button.onclick=()=>act('retry');button.style.cssText='animation:eduitReplayPulse 1.5s ease-in-out infinite';end.append(text,button);}
}
function frame(now){const dt=last?Math.min((now-last)/1000,.1):0;last=now;if(!paused&&!document.hidden&&['playing','celebrating'].includes(state.phase)){state=advance(state,'tick',dt*(state.practice?1:Math.min(1.24,1+0.08*Math.max(0,(state.round||1)-1))));draw();}requestAnimationFrame(frame);}
function canonicalFrame(){
 if(!expandedPresentation)return stage.innerHTML;
 const svg=stage.querySelector('svg').cloneNode(true);
 svg.setAttribute('viewBox','0 0 960 540');svg.setAttribute('width','960');svg.setAttribute('height','540');
 svg.querySelectorAll('[data-presentation]').forEach(n=>n.remove());
 return new XMLSerializer().serializeToString(svg);
}
window.storytimeReview={setPresentation({expanded=false}={}){
 if(typeof expanded!=='boolean')return false;
 expandedPresentation=expanded;document.body.classList.toggle('scene-expanded',expanded);draw();return true;
 },setAppearance(value){
 const available=artwork.appearances;
 if(typeof value!=='string'||!available||!Object.hasOwn(available,value))return null;
 paused=true;soundtrack.pause();appearance=value;
 document.body.style.background=available[value].earth;draw();return appearance;
 },status(){return {paused,phase:state.phase,clock:state.elapsed,score:state.score,practice:state.practice,appearance};},reset(){playedVictory=false;resetCueAudio();state=advance(state,'retry');paused=true;soundtrack.pause();draw();},setPractice(value){playedVictory=false;state=initial({practice:!!value});resetCueAudio();paused=true;soundtrack.pause();draw();},setLocale(value){locale=normalizeLocale(value);document.documentElement.lang=locale;draw();return locale;},freeze(){paused=true;soundtrack.pause();return {svg:canonicalFrame(),phase:state.phase,elapsed:state.elapsed,clock:state.elapsed,state:structuredClone(state),locale,appearance};},play(){paused=false;resetCueAudio();enableAudio();if(['ready','over'].includes(state.phase))act('start');syncAudio();},pause(){paused=true;soundtrack.pause();}};
// Reuse the Mall gesture owner inside the iframe; only same-origin parent can react.
panelGestures=bindPanelGestures(stage.parentElement,{expand:()=>parent.postMessage({type:'storytime.fullscreen',expanded:true},location.origin),collapse:()=>parent.postMessage({type:'storytime.fullscreen',expanded:false},location.origin)});
document.addEventListener('visibilitychange',()=>{if(document.hidden){paused=true;soundtrack.pause();}});
new ResizeObserver(()=>{if(expandedPresentation)draw();}).observe(stage.parentElement);
draw();requestAnimationFrame(frame);
