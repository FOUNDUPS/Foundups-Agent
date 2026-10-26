import {bindPanelGestures} from './panel-gestures.mjs';
import {initial,advance,actorPose} from './engine.mjs';
import {scene,movie} from './scene.mjs';
import {locales,normalizeLocale,localizeEvent} from './learning-events.mjs';
let locale='en';
const $=id=>document.getElementById(id),stage=$('scene');
let panelGestures;
let state=initial(),last=0,paused=false,hitKey="";
const soundtrack=new Audio("assets/little-shrew.mp4");soundtrack.preload="auto";
function syncAudio(){soundtrack.currentTime=state.elapsed;if(!paused&&state.phase==="playing")soundtrack.play().catch(()=>{});else soundtrack.pause();}
const embedded=new URLSearchParams(location.search).get('embed')==='1';if(embedded)document.body.classList.add('embedded');
const hits=document.createElement('div');hits.className='rescue-targets';stage.after(hits);
for(const id of ['wake','root'])$(id).remove();
function act(e){if(panelGestures?.isPinching())return;state=advance(state,e);if(e==='start'||e==='retry')syncAudio();draw();}
$('start').onclick=()=>act('start');$('retry').onclick=()=>act('retry');$('pause').onclick=()=>{paused=!paused;syncAudio();};
function draw(){
 const t=state.elapsed,poses=state.actors.map(a=>actorPose(a,t));
 const world=movie(t);let cue=localizeEvent(world.cue,locale);
 if(cue?.kind==='sniff'){const a=poses.find(a=>a.id===(state.selected||'baby-3'));cue={...cue,actorId:a.id,x:Math.min(875,a.x+100),y:a.y+75};}
 stage.innerHTML=scene({...world,cue,actors:poses,showWords:true});
 const nextKey=state.phase+state.selected+state.actors.map(a=>a.status).join();
 if(nextKey!==hitKey){hitKey=nextKey;hits.replaceChildren();
 if(state.phase==='playing'&&t<9.6){
  for(const a of poses.filter(a=>a.status==='sleeping'&&state.selected===null)){
   const b=document.createElement('button');b.className='rescue-hit';b.setAttribute('aria-label',`Wake ${a.id}`);
   b.style.cssText=`left:${(a.x+20*a.scale)/9.6}%;top:${(a.y+20*a.scale)/5.4}%;width:${170*a.scale/9.6}%;height:${110*a.scale/5.4}%`;
   b.onclick=()=>act('select:'+a.id);hits.append(b);
  }
  if(state.actors.some(a=>a.id===state.selected&&a.status==='awake')){const b=document.createElement('button');b.className='rescue-hit';b.style.cssText='left:81%;top:43%;width:14%;height:30%';b.setAttribute('aria-label','Move selected shrew to root');b.onclick=()=>act('root');hits.append(b);}
 }
 }
 const over=state.phase==='over',saved=state.actors.filter(a=>a.status==='safe').length;
 $('message').textContent=over?(saved?`${saved} / 5 saved`:locales[locale].over):'';
 $('start').hidden=state.phase!=='ready';$('retry').hidden=!over;$('pause').hidden=state.phase!=='playing';$('time').textContent='';
 let end=$('ending');if(!end){end=document.createElement('div');end.id='ending';stage.parentElement.append(end);}
 end.hidden=!over;if(over){end.replaceChildren();const text=document.createElement('span');text.textContent=saved?`${saved} / 5`:locales[locale].over;const button=document.createElement('button');button.textContent='↻';button.setAttribute('aria-label',locales[locale].again);button.onclick=()=>act('retry');end.append(text,button);}
}
function frame(now){const dt=last?Math.min((now-last)/1000,.1):0;last=now;if(!paused&&!document.hidden&&state.phase==='playing'){state=advance(state,'tick',dt);if(!soundtrack.paused&&Math.abs(soundtrack.currentTime-state.elapsed)>.15)soundtrack.currentTime=state.elapsed;draw();}requestAnimationFrame(frame);}
window.storytimeReview={setLocale(value){locale=normalizeLocale(value);document.documentElement.lang=locale;draw();return locale;},freeze(){paused=true;soundtrack.pause();return {svg:stage.innerHTML,phase:state.phase,elapsed:state.elapsed,clock:state.elapsed,state:structuredClone(state),locale};},play(){paused=false;if(['ready','over'].includes(state.phase))act('start');syncAudio();},pause(){paused=true;soundtrack.pause();}};
// Reuse the Mall gesture owner inside the iframe; only same-origin parent can react.
panelGestures=bindPanelGestures(stage.parentElement,{expand:()=>parent.postMessage({type:'storytime.fullscreen',expanded:true},location.origin),collapse:()=>parent.postMessage({type:'storytime.fullscreen',expanded:false},location.origin)});
document.addEventListener('visibilitychange',()=>{if(document.hidden)soundtrack.pause();else syncAudio();});
draw();requestAnimationFrame(frame);
