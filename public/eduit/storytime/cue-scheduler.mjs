// Media-clock cue coordination. Browser voice callbacks are not hardware onset proof.
export const storyObjects=Object.freeze({
 'long-ago':Object.freeze({text:'long long ago',picture:'🌿'}),
 dinosaurs:Object.freeze({text:'there were dinosaurs',picture:'🦕'}),
 family:Object.freeze({text:'a family of MAMMA 🥚s',spoken_text:'a family of MAMMAs',picture:'🥚'}),
 sleeping:Object.freeze({text:'the little MAMMA 🥚s slept',spoken_text:'the little MAMMAs slept',picture:'💤'}),
 waking:Object.freeze({text:'one little animal woke up'}),
 thump:Object.freeze({text:'THUMP',picture:'🦶'}),
 safe:Object.freeze({text:'a little one was safe'})
});
export const storyCues=Object.freeze([
 {id:'long-ago',start_ms:0,end_ms:3400,speech_ms:220,fade_ms:3000,text:storyObjects['long-ago'].text},
 {id:'dinosaurs',start_ms:3400,end_ms:6500,speech_ms:3620,fade_ms:6100,text:storyObjects['dinosaurs'].text,picture:'🦕'},
 {id:'waking',start_ms:6500,end_ms:9500,speech_ms:6720,fade_ms:9100,text:storyObjects['waking'].text},
 {id:'thump',start_ms:9680,end_ms:12300,speech_ms:10400,fade_ms:11900,text:storyObjects['thump'].text,template:'action'},
 {id:'safe',start_ms:12300,end_ms:15000,speech_ms:12520,fade_ms:14600,text:storyObjects['safe'].text}
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
  try{this.speak(cue.spoken_text??cue.text,{
   start:()=>{if(!valid())return;this.voice='speaking';this.duck(true);this.emit('speech_started',{intended_ms:cue.speech_ms});},
   end:()=>finish('speech_ended'),error:()=>finish('speech_unavailable')
  });}catch{finish('speech_unavailable');}
 }
}

// Page playback reuses CueScheduler's speech-generation/cancellation boundary.
// These holds are authored UI defaults, not measured preschool memory intervals.
export const storyPages=Object.freeze(['long-ago','dinosaurs','family','sleeping','thump'].map(id=>Object.freeze({
 ...storyObjects[id],id,concept_id:id==='thump'?'sound.thump':`story.${id}`,
 ...(id==='thump'?{text:'then something went THUMP',spoken_text:'then something went thump'}:{}),
 speech_offset_ms:220,min_visible_ms:3000,hold_ms:1200,fade_ms:350,silent_hold_ms:4200
})));
export class StorybookPlayback {
 constructor({pages=storyPages,speak,cancel,view=()=>{},trace=()=>{},now=()=>performance.now(),speechTimeoutMs=12000}){
  if(!Array.isArray(pages)||!pages.length||!Number.isFinite(speechTimeoutMs)||speechTimeoutMs<1000)throw new TypeError('Invalid storybook contract');
  Object.assign(this,{pages,view,trace,now,speechTimeoutMs});
  this.index=0;this.playing=false;this.finished=false;this.elapsed=0;this.origin=0;this.completedAt=null;this.silent=false;this.unavailable=false;
  this.scheduler=new CueScheduler({speak,cancel,view:()=>{},now,trace:event=>{
   if(event.type==='speech_ended'||event.type==='speech_unavailable'){
    this.completedAt=Math.max(this.elapsed,this.now()-this.origin);
    this.unavailable=event.type==='speech_unavailable';
   }
   this.trace({...event,page:this.index});
  }});
  this.load();
 }
 load(){
  this.scheduler.reset('page');this.elapsed=0;this.completedAt=null;this.finished=false;this.unavailable=false;
  const page=this.pages[this.index];
  this.scheduler.cues=[{...page,start_ms:0,speech_ms:page.speech_offset_ms,
   fade_ms:this.speechTimeoutMs+60000,end_ms:this.speechTimeoutMs+60001}];
  this.render();
 }
 render(fading=false){this.view(this.pages[this.index],{index:this.index,total:this.pages.length,playing:this.playing,finished:this.finished,fading,silent:this.silent,unavailable:this.unavailable});}
 select(index){
  if(!Number.isInteger(index)||index<0||index>=this.pages.length)return false;
  this.pause('navigation');this.index=index;this.load();return true;
 }
 play({audible=true}={}){
  this.pause('explicit-play');this.silent=!audible;this.load();
  this.origin=this.now();this.playing=true;this.render();
 }
 pause(reason='pause'){this.playing=false;this.scheduler.stop(reason);this.render();}
 tick(at=this.now()){
  if(!this.playing||!Number.isFinite(at)||at<this.origin)return;
  this.elapsed=Math.max(this.elapsed,at-this.origin);
  if(this.completedAt===null)this.scheduler.update(Math.min(this.elapsed,this.speechTimeoutMs),{running:true,audible:!this.silent});
  if(this.silent&&this.completedAt===null)this.completedAt=0;
  if(this.completedAt===null&&this.elapsed>=this.speechTimeoutMs){
   this.scheduler.stop('voice-timeout');this.completedAt=this.elapsed;this.unavailable=true;
   this.trace({type:'speech_unavailable',reason:'timeout',page:this.index,observed_ms:at});
  }
  const page=this.pages[this.index];
  const finish=this.completedAt===null?Infinity:Math.max(
   this.silent||this.unavailable?page.silent_hold_ms:page.min_visible_ms,this.completedAt+page.hold_ms);
  this.render(this.elapsed>=finish);
  if(this.elapsed<finish+page.fade_ms)return;
  if(this.index===this.pages.length-1){this.playing=false;this.finished=true;this.scheduler.stop('book-ended');this.render();}
  else{this.index++;this.load();this.origin=at;}
 }
}
