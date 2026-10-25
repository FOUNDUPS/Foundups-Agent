export function initial(){return {phase:'ready',elapsed:0};}
export function advance(state,event,dt=0,practice=false){
 let s={...state};
 if(event==='start'||event==='retry')return {phase:'wake',elapsed:0};
 if(event==='shrew'&&s.phase==='wake')return {phase:'root',elapsed:0};
 if(event==='root'&&s.phase==='root')return {phase:'walk',elapsed:0};
 if(event!=='tick'||s.phase==='ready'||s.phase==='success'||s.phase==='retry')return s;
 s.elapsed+=Math.max(0,Math.min(dt,.1));
 if((s.phase==='wake'||s.phase==='root')&&s.elapsed>=4&&!practice)return {phase:'retry',elapsed:0};
 if(s.phase==='walk'&&s.elapsed>=2.4)return {phase:'stomp',elapsed:0};
 if(s.phase==='stomp'&&s.elapsed>=3)return {phase:'success',elapsed:0};
 return s;
}
