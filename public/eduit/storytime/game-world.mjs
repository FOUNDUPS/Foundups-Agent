// Shared scene, independently paced game cues. Source offsets reference original foley.
import {worldTime,DEADLINE} from './engine.mjs';
const clamp=x=>Math.max(0,Math.min(1,x));
export const gameEvents=[
 {id:'game-far',start:1,end:3,kind:'thump',x:170,y:65,size:48,shakeSize:20,sourceTime:.6,sourceDuration:.75},
 {id:'game-near',start:12,end:14,kind:'thump',x:420,y:65,size:60,shakeSize:30,sourceTime:2,sourceDuration:.8},
 {id:'game-crack-1',start:23,end:25,kind:'crack',x:240,y:180,size:62,sourceTime:7.6,sourceDuration:.65},
 {id:'game-overhead',start:32,end:34,kind:'thump',x:540,y:65,size:78,shakeSize:42,sourceTime:6.7,sourceDuration:.75},
 {id:'game-crack-2',start:38,end:40,kind:'crack',x:540,y:180,size:66,sourceTime:8.45,sourceDuration:.65},
 {id:'game-crack-3',start:44,end:46,kind:'crack',x:380,y:180,size:70,sourceTime:8.45,sourceDuration:.65},
 {id:'game-contact',start:48,end:50,kind:'thump',x:420,y:230,size:80,shakeSize:60,sourceTime:9.6,sourceDuration:.65},
 {id:'game-crunch',start:51,end:53,kind:'crunch',x:440,y:330,size:66,sourceTime:10.3,sourceDuration:.3},
 {id:'game-squish',start:54,end:56,kind:'squish',x:440,y:440,size:68,sourceTime:10.65,sourceDuration:1}
];
export function gameWorld(state,poses){
 const t=worldTime(state),won=state.outcome==='rescued';
 const victoryAge=won?Math.max(0,state.elapsed-state.victoryAt):0;
 if(won){
  const impact=clamp(victoryAge/.45),lift=clamp((victoryAge-1.1)/.85);
  const cue=victoryAge>=.35&&victoryAge<1.15?{id:'victory-thump',kind:'thump',word:'THUMP!',start:state.victoryAt+.35,end:state.victoryAt+1.15,x:450,y:230,size:112,shakeSize:85,sourceTime:9.6,sourceDuration:.65}:null;
  return {t,cue,actors:poses,warning:1,reaction:1,collapse:impact,impact,lift,turn:1,shake:!!cue,rootSway:cue?3:0,progressiveCracks:true,dust:false};
 }
 let cue=gameEvents.find(e=>t>=e.start&&t<e.end);
 const sniffActor=poses.find(a=>['awake','wandering'].includes(a.status));
 if(!cue&&sniffActor){const offset=state.elapsed-sniffActor.awakeAt,index=Math.floor(offset/1.8);if(offset%1.8<.8)cue={id:`sniff-${sniffActor.id}-${sniffActor.awakeAt}-${index}`,kind:'sniff',start:t-offset%1.8,end:t-offset%1.8+.8,size:58,actorId:sniffActor.id,sourceTime:3.1,sourceDuration:.55,x:sniffActor.x>650?sniffActor.x-130:sniffActor.x+180,y:sniffActor.scale<.6?sniffActor.y+28:sniffActor.y-20};}
 if(cue)cue={...cue,word:cue.kind.toUpperCase()};
 const collapse=clamp((t-DEADLINE)/7);
 return {t,cue:won?null:cue,actors:poses,warning:clamp((t-22)/24),reaction:clamp((t-44)/4),collapse,impact:collapse,lift:clamp((t-56)/3),turn:won?1:clamp((t-58)/2),shake:!won&&cue?.kind==='thump',rootSway:won?0:Math.sin(t*9)*(.2+clamp((t-12)/30))*(cue?.kind==='thump'?3:.3),progressiveCracks:true,dust:!won&&t>23&&t<55};
}
