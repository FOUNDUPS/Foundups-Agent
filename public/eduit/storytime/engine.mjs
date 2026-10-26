// Deterministic rescue game. The world clock never waits for a tap.
export const DEADLINE=9.6, DURATION=15;
export const CAST=[
 {id:'parent-1',x:75,y:215.6,scale:1.12,duration:2.6,destX:715,destY:240},
 {id:'parent-2',x:290,y:206,scale:1.2,duration:2.6,destX:710,destY:280},
 {id:'baby-1',x:120,y:378,scale:.42,duration:.9,destX:720,destY:378},
 {id:'baby-2',x:235,y:378,scale:.42,duration:.9,destX:790,destY:378},
 {id:'baby-3',x:350,y:378,scale:.42,duration:.9,destX:860,destY:378}
];
export function initial(){return {phase:'ready',elapsed:0,selected:null,actors:CAST.map(a=>({...a,status:'sleeping',started:null}))};}
export function advance(state,event,dt=0){
 if(event==='start'||event==='retry')return {...initial(),phase:'playing'};
 if(state.phase!=='playing')return state;
 let s={...state,actors:state.actors.map(a=>({...a}))};
 if(event==='tick'){
  s.elapsed=Math.min(DURATION,s.elapsed+Math.max(0,Math.min(Number.isFinite(dt)?dt:0,.1)));
  for(const a of s.actors){
   if(a.status==='moving'&&a.started+a.duration<=Math.min(s.elapsed,DEADLINE)+1e-8){a.status='safe';s.selected=null;}
   if(s.elapsed>=DEADLINE&&a.status!=='safe')a.status='lost';
  }
  if(s.elapsed>=DEADLINE)s.selected=null;
  if(s.elapsed>=DURATION)s.phase='over';
 }else if(s.elapsed<DEADLINE){
  if(event.startsWith('select:')&&s.selected===null){const a=s.actors.find(a=>a.id===event.slice(7));if(a?.status==='sleeping'){a.status='awake';s.selected=a.id;}}
  if(event==='root'&&s.selected){const a=s.actors.find(a=>a.id===s.selected);if(a.status==='awake'){a.status='moving';a.started=s.elapsed;}}
 }
 return s;
}
export function actorPose(a,t){const p=a.started===null?0:Math.max(0,Math.min(1,(Math.min(t,DEADLINE)-a.started)/a.duration));return {...a,x:a.x+(a.destX-a.x)*p,y:a.y+(a.destY-a.y)*p-(p>0&&p<1?2*Math.abs(Math.sin(t*20)):0),awake:a.status!=='sleeping'};}
