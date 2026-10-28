// Game time is independent of the film. Only active play advances this clock.
export const DEADLINE=48, DURATION=60, PRACTICE_HOLD=30, VICTORY_REVEAL=3.5;
export const CAST=[
 {id:'parent-1',x:75,y:215.6,scale:1.12,duration:4,wakeTaps:3,destX:715,destY:240},
 {id:'parent-2',x:290,y:206,scale:1.2,duration:4.5,wakeTaps:4,destX:710,destY:280},
 {id:'baby-1',x:120,y:378,scale:.42,duration:2,wakeTaps:1,destX:720,destY:378},
 {id:'baby-2',x:235,y:378,scale:.42,duration:2.4,wakeTaps:2,destX:790,destY:378},
 {id:'baby-3',x:350,y:378,scale:.42,duration:2.2,wakeTaps:2,destX:860,destY:378}
];
export function initial({practice=false,round=1}={}){const shift=(round-1)%3;return {phase:'ready',round,elapsed:0,practice,selected:null,score:0,awards:[],victoryAt:null,actors:CAST.map((a,i)=>({...a,x:a.x+([0,-12,12][(i+shift)%3]||0),status:'sleeping',started:null,taps:0,tappedAt:null,awakeAt:null,wandered:false}))};}
export const rescuePoints=(elapsed,practice=false)=>10+(practice?0:Math.max(0,Math.floor(10*(1-elapsed/DEADLINE))));
export const worldTime=s=>s.practice?Math.min(PRACTICE_HOLD,s.elapsed):s.elapsed;
export function advance(state,event,dt=0){
 if(event==='start'||event==='retry')return {...initial({practice:state.practice,round:event==='retry'?Math.min(3,(state.round||1)+1):state.round||1}),phase:'playing'};
 if(!['playing','celebrating'].includes(state.phase))return state;
 const s={...state,actors:state.actors.map(a=>({...a})),awards:[...state.awards]};
 if(event==='tick'){
  if(s.phase==='celebrating'){
   s.elapsed+=Math.max(0,Math.min(Number.isFinite(dt)?dt:0,.1));
   if(s.elapsed-s.victoryAt>=VICTORY_REVEAL)s.phase='over';
   return s;
  }
  s.elapsed=Math.min(86400,s.elapsed+Math.max(0,Math.min(Number.isFinite(dt)?dt:0,.1)));
  for(const a of s.actors){
   if(a.status==='moving'&&a.started+a.duration<=Math.min(s.elapsed,s.practice?Infinity:DEADLINE)+1e-8){
    a.status='safe';s.selected=null;const points=rescuePoints(a.started+a.duration,s.practice);s.score+=points;s.awards.push({id:a.id,points,at:a.started+a.duration});
   }
   // Partial wake-up lasts generously; no rapid-tapping requirement.
   if(a.status==='sleeping'&&a.tappedAt!==null&&s.elapsed-a.tappedAt>8)a.taps=0;
   if(a.status==='awake'&&s.elapsed-a.awakeAt>10){a.status='sleeping';a.taps=0;s.selected=null;}
   // One predictable light sleeper investigates once, then dozes again.
   if(a.id==='baby-1'&&!a.wandered&&s.elapsed>=6&&a.status==='sleeping'&&a.taps===0){a.status='wandering';a.awakeAt=s.elapsed;a.wandered=true;}
   if(a.status==='wandering'&&s.elapsed-a.awakeAt>=5){a.status='sleeping';a.taps=0;}
   if(!s.practice&&s.elapsed>=DEADLINE&&a.status!=='safe')a.status='lost';
  }
  if(!s.practice&&s.elapsed>=DEADLINE)s.selected=null;
  if(s.actors.every(a=>a.status==='safe')){s.phase='celebrating';s.outcome='rescued';s.victoryAt=s.elapsed;}
  else if(!s.practice&&s.elapsed>=DURATION){s.elapsed=DURATION;s.phase='over';s.outcome='retry';}
 }else if(s.practice||s.elapsed<DEADLINE){
  if(event.startsWith('select:')&&s.selected===null){
   const a=s.actors.find(a=>a.id===event.slice(7));
   if(a&&['sleeping','wandering'].includes(a.status)){
    a.taps=Math.min(a.wakeTaps,a.taps+1);a.tappedAt=s.elapsed;
    if(a.taps>=a.wakeTaps||a.status==='wandering'){a.status='awake';a.awakeAt=s.elapsed;s.selected=a.id;}
   }
  }
  if(event==='root'&&s.selected){const a=s.actors.find(a=>a.id===s.selected);if(a.status==='awake'){a.status='moving';a.started=s.elapsed;}}
 }
 return s;
}
export function actorPose(a,t){
 const p=a.started===null?0:Math.max(0,Math.min(1,((a.status==='lost'?Math.min(t,DEADLINE):t)-a.started)/a.duration));
 const wander=a.status==='wandering'?18*Math.sin(Math.PI*Math.min(1,(t-a.awakeAt)/5)):0;
 const wiggle=a.tappedAt!==null&&t-a.tappedAt<.6?3*Math.sin((t-a.tappedAt)*25):0;
 return {...a,x:a.x+(a.destX-a.x)*p+wander+wiggle,y:a.y+(a.destY-a.y)*p-(p>0&&p<1?2*Math.abs(Math.sin(t*10)):0),awake:['awake','moving','safe','wandering'].includes(a.status)};
}
