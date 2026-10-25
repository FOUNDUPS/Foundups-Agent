import {initial,advance} from './engine.mjs';
import {scene} from './scene.mjs';
let state=initial(),last=0,clock=0,paused=false,audio;
const $=id=>document.getElementById(id), stage=$('scene'), wake=$('wake'),root=$('root'),start=$('start'),message=$('message');
function sound(freq){if(!$('sound').checked)return;try{audio??=new AudioContext();audio.resume();let o=audio.createOscillator(),g=audio.createGain();o.type='sine';o.frequency.value=freq;g.gain.setValueAtTime(.045,audio.currentTime);g.gain.exponentialRampToValueAtTime(.001,audio.currentTime+.22);o.connect(g).connect(audio.destination);o.start();o.stop(audio.currentTime+.23);}catch{}}
function act(event){let prev=state.phase;state=advance(state,event);if(state.phase!==prev){sound(event==='root'?660:440);update();}}
start.onclick=()=>act('start');$('retry').onclick=()=>act('retry');wake.onclick=()=>act('shrew');root.onclick=()=>act('root');
$('pause').onclick=()=>{paused=!paused;$('pause').textContent=paused?'Resume':'Pause';};
function update(){
 const phase=state.phase;
 const text={ready:'A tiny adventure beneath your feet.',wake:'The ground is shaking. Tap the little shrew!',root:'Now tap the root to move into the little pocket.',walk:'Shuffle, shuffle… sniff, sniff!',stomp:'A big foot presses down…',success:'Safe in the little pocket! You noticed and acted.',retry:'Oops! Try again. First the shrew, then the root.'};
 message.textContent=text[phase];wake.hidden=phase!=='wake';root.hidden=phase!=='root';start.hidden=phase!=='ready';$('retry').hidden=!['success','retry'].includes(phase);
 $('pause').hidden=['ready','success','retry'].includes(phase);
 if(phase==='wake')wake.focus({preventScroll:true});if(phase==='root')root.focus({preventScroll:true});if(['success','retry'].includes(phase))$('retry').focus({preventScroll:true});
}
function frame(now){const dt=last?Math.min((now-last)/1000,.1):0;last=now;
 if(!paused&&!document.hidden){clock+=dt;const old=state.phase;state=advance(state,'tick',dt,$('practice').checked);if(old!==state.phase){if(state.phase==='success')sound(784);update();}}
 const p=state.phase,e=state.elapsed;
 const moving=['walk','stomp','success'].includes(p),impact=p==='stomp'?Math.min(e/.7,1):p==='success'?1:0;
 stage.innerHTML=scene({t:clock,awake:['root','walk','stomp','success'].includes(p),progress:moving?(p==='walk'?Math.min(e/1.5,1):1):0,impact,warning:state.phase==='ready'?0:1,reaction:p==='walk'?Math.max(0,(e-1.7)/.7):impact>0?1:0,collapse:impact,lift:p==='stomp'?Math.max(0,(e-1.5)/1.3):p==='success'?1:0,shake:p==='wake'&&!matchMedia('(prefers-reduced-motion: reduce)').matches});
 $('time').textContent=['wake','root'].includes(p)&&!$('practice').checked?`${Math.max(0,Math.ceil(4-e))} seconds`:$('practice').checked?'Practice · no timer':'';
 requestAnimationFrame(frame);
}
update();requestAnimationFrame(frame);
