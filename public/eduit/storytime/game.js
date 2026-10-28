import {bindPanelGestures} from './panel-gestures.mjs';
import {initial,advance,actorPose,DEADLINE} from './engine.mjs';
import {scene} from './scene.mjs';
import {gameWorld} from './game-world.mjs';
import {locales,normalizeLocale,localizeEvent} from './learning-events.mjs';
let locale='en';
const $=id=>document.getElementById(id),stage=$('scene');
let panelGestures;
let state=initial(),last=0,paused=false,hitKey="";
const soundtrack=new Audio("assets/little-shrew.mp4");soundtrack.preload="auto";
let lastCue=null,audioEnabled=false,ctx=null,playedVictory=false;
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
 if(cue?.id!==lastCue){soundtrack.pause();lastCue=cue?.id||null;if(cue){soundtrack.currentTime=cue.sourceTime;soundtrack.play().catch(()=>{});}}
 if(cue&&soundtrack.currentTime>=cue.sourceTime+cue.sourceDuration)soundtrack.pause();
}
function enableAudio(){audioEnabled=true;soundtrack.play().then(()=>{if(!lastCue||paused||state.phase!=='playing')soundtrack.pause();}).catch(()=>{});}
const embedded=new URLSearchParams(location.search).get('embed')==='1';if(embedded)document.body.classList.add('embedded');
const hits=document.createElement('div');hits.className='rescue-targets';stage.after(hits);
for(const id of ['wake','root'])$(id).remove();
function act(e){if(panelGestures?.isPinching())return;if(e==='start'||e==='retry'){paused=false;lastCue=null;playedVictory=false;enableAudio();}else if(paused)return;state=advance(state,e);if(e==='start'||e==='retry')syncAudio();draw();}
$('start').onclick=()=>act('start');$('retry').onclick=()=>act('retry');$('pause').onclick=()=>{paused=!paused;syncAudio();};
function draw(){
 const t=state.elapsed,poses=state.actors.map(a=>actorPose(a,t));
 const world=gameWorld(state,poses),cue=localizeEvent(world.cue,locale);cueAudio(cue);
 stage.innerHTML=scene({...world,cue,actors:poses,showWords:true});
 const svg=stage.querySelector('svg');const ns='http://www.w3.org/2000/svg';
 const score=document.createElementNS(ns,'text');score.setAttribute('x','35');score.setAttribute('y','510');score.setAttribute('fill','#FFF4D9');score.setAttribute('font-size','60');score.setAttribute('font-family','sans-serif');score.setAttribute('font-weight','bold');score.setAttribute('aria-label',`${state.score} points`);score.textContent=`★ ${state.score}`;svg.append(score);
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
 const over=state.phase==='over',saved=state.actors.filter(a=>a.status==='safe').length;
 $('message').textContent=over?(saved===5?'Everyone is safe!':saved?`${saved} / 5 saved · ${state.score} points`:locales[locale].over):'';
 $('start').hidden=state.phase!=='ready';$('retry').hidden=!over;$('pause').hidden=state.phase!=='playing';$('time').textContent='';
 let end=$('ending');if(!end){end=document.createElement('div');end.id='ending';stage.parentElement.append(end);}
 end.hidden=!over;if(over){end.replaceChildren();const text=document.createElement('span');text.textContent=saved===5?'Everyone is safe!':saved?`${saved} / 5 ★ ${state.score}`:locales[locale].over;text.setAttribute('aria-label',saved?`${saved} of 5 shrews saved, ${state.score} points`:locales[locale].over);const button=document.createElement('button');button.textContent='↻';button.setAttribute('aria-label',locales[locale].again);button.onclick=()=>act('retry');end.append(text,button);}
}
function frame(now){const dt=last?Math.min((now-last)/1000,.1):0;last=now;if(!paused&&!document.hidden&&['playing','celebrating'].includes(state.phase)){state=advance(state,'tick',dt);draw();}requestAnimationFrame(frame);}
window.storytimeReview={status(){return {paused,phase:state.phase,clock:state.elapsed,score:state.score,practice:state.practice};},reset(){lastCue=null;state=advance(state,'retry');paused=true;soundtrack.pause();draw();},setPractice(value){state=initial({practice:!!value});lastCue=null;paused=true;soundtrack.pause();draw();},setLocale(value){locale=normalizeLocale(value);document.documentElement.lang=locale;draw();return locale;},freeze(){paused=true;soundtrack.pause();return {svg:stage.innerHTML,phase:state.phase,elapsed:state.elapsed,clock:state.elapsed,state:structuredClone(state),locale};},play(){paused=false;lastCue=null;enableAudio();if(['ready','over'].includes(state.phase))act('start');syncAudio();},pause(){paused=true;soundtrack.pause();}};
// Reuse the Mall gesture owner inside the iframe; only same-origin parent can react.
panelGestures=bindPanelGestures(stage.parentElement,{expand:()=>parent.postMessage({type:'storytime.fullscreen',expanded:true},location.origin),collapse:()=>parent.postMessage({type:'storytime.fullscreen',expanded:false},location.origin)});
document.addEventListener('visibilitychange',()=>{if(document.hidden){paused=true;soundtrack.pause();}});
draw();requestAnimationFrame(frame);
