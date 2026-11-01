// Offline demonstration inputs. The live engine owns every state transition.
import {initial,advance,actorPose} from '../../../public/eduit/storytime/engine.mjs';
import {gameWorld} from '../../../public/eduit/storytime/game-world.mjs';
export const replayRevision='same-engine-rescue-2',fps=30;
export function replay(){
 const states=[],actions=[];let state=initial(),frame=0;
 const capture=()=>states.push(structuredClone(state));
 const tick=()=>{capture();state=advance(state,'tick',1/fps);frame++;};
 const wait=n=>{for(let i=0;i<n;i++)tick();};
 const act=event=>{actions.push({frame,event});state=advance(state,event);};
 wait(15);act('start');
 for(const id of ['baby-1','baby-2','baby-3','parent-1','parent-2']){
  wait(5);const actor=state.actors.find(a=>a.id===id);
  for(let i=0;i<actor.wakeTaps;i++){act('select:'+id);if(i<actor.wakeTaps-1)wait(6);}
  wait(21);act('root');
  while(state.actors.find(a=>a.id===id).status!=='safe'){
   if(frame>=1800)throw Error('Replay failed to rescue within bounded timeline');tick();
  }
 }
 while(state.phase!=='over'){if(frame>=1800)throw Error('Replay did not finish');tick();}
 const completedFrame=frame;
 // Whole five-second shots preserve the existing renderer's shot contract.
 const frameCount=Math.ceil((frame+1)/150)*150;
 while(frame<frameCount)tick();
 const events=[];let lastCue=null,active=null;
 for(let i=0;i<states.length;i++){
  const s=states[i],world=gameWorld(s,s.actors.map(a=>actorPose(a,s.elapsed))),cue=world.cue;
  if((cue?.id||null)!==lastCue){
   if(active)active.end=i/fps;
   active=cue?{...cue,start:i/fps,end:frameCount/fps,
    word:cue.word||cue.kind.toUpperCase(),gain:cue.gain??.1}:null;
   if(active)events.push(active);
  }
  lastCue=cue?.id||null;
 }
 return {revision:replayRevision,fps,frameCount,duration:frameCount/fps,completedFrame,states,actions,events};
}
export function replayWorld(state){return gameWorld(state,state.actors.map(a=>actorPose(a,state.elapsed)));}
