// Media-clock cue coordination. Browser voice callbacks are not hardware onset proof.
export const storyCues=Object.freeze([
 {id:'long-ago',start_ms:0,end_ms:3400,speech_ms:220,fade_ms:3000,text:'long long ago'},
 {id:'dinosaurs',start_ms:3400,end_ms:6500,speech_ms:3620,fade_ms:6100,text:'there were dinosaurs',picture:'🦕'},
 {id:'waking',start_ms:6500,end_ms:9500,speech_ms:6720,fade_ms:9100,text:'one little animal woke up'},
 {id:'thump',start_ms:9680,end_ms:12300,speech_ms:10400,fade_ms:11900,text:'THUMP',template:'action'},
 {id:'safe',start_ms:12300,end_ms:15000,speech_ms:12520,fade_ms:14600,text:'a little one was safe'}
]);
export class CueScheduler {
 constructor({cues=storyCues,speak,cancel,view,duck=()=>{},trace=()=>{},now=()=>performance.now()}){
  Object.assign(this,{cues,speak,cancel,view,duck,trace,now});
  this.current=null;this.epoch=0;this.voice='idle';this.lastMs=0;this.running=false;
 }
 emit(type,extra={}){this.trace({type,cue_id:this.current?.id||null,media_ms:this.lastMs,observed_ms:this.now(),...extra});}
 stop(reason='pause'){
  this.epoch++;this.cancel();this.duck(false);this.voice='idle';this.running=false;
  this.emit('cancelled',{reason});
 }
 reset(reason='seek'){this.stop(reason);this.current=null;}
 update(ms,{running=false,audible=true}={}){
  if(!Number.isFinite(ms)||ms<0)return;
  if(ms<this.lastMs)this.reset('rewind');
  this.lastMs=ms;
  const cue=this.cues.find(c=>ms>=c.start_ms&&ms<c.end_ms)||null;
  if(cue!==this.current){this.stop('cue-change');this.current=cue;if(cue)this.emit('word_visible',{intended_ms:cue.start_ms});}
  if((!running||!audible)&&this.running)this.stop(!running?'pause':'muted');
  this.running=running&&audible;
  const speaking=['requested','speaking'].includes(this.voice);
  this.view(cue,!!cue&&ms>=cue.fade_ms&&!speaking);
  if(!cue||!this.running||this.voice!=='idle'||ms<cue.speech_ms||ms>=cue.fade_ms)return;
  const epoch=++this.epoch;this.voice='requested';
  this.emit('speech_requested',{intended_ms:cue.speech_ms});
  const valid=()=>this.epoch===epoch;
  const finish=(type)=>{if(!valid())return;this.voice='done';this.duck(false);this.emit(type);};
  try{this.speak(cue.text,{
   start:()=>{if(!valid())return;this.voice='speaking';this.duck(true);this.emit('speech_started',{intended_ms:cue.speech_ms});},
   end:()=>finish('speech_ended'),error:()=>finish('speech_unavailable')
  });}catch{finish('speech_unavailable');}
 }
}
