import {CueScheduler,cueRevision,storyCues} from '../storytime/cue-scheduler.mjs';
let activeSpeechChannel=null;
export function createSpeechChannel({notice=()=>{},volume=()=>.85}={}){
 const synth=window.speechSynthesis;let utterance=null;
 const channel={
  cancel(){if(!utterance)return;utterance.onstart=utterance.onend=utterance.onerror=null;
   if(activeSpeechChannel===channel){synth?.cancel();activeSpeechChannel=null;}utterance=null;},
  speak(text,callbacks){
   channel.cancel();activeSpeechChannel?.cancel();
   if(!synth||!window.SpeechSynthesisUtterance){notice(false);callbacks.error();return;}
   const current=new window.SpeechSynthesisUtterance(text);utterance=current;activeSpeechChannel=channel;
   current.lang='en-GB';current.rate=.9;current.volume=Math.max(0,Math.min(1,volume()));
   const voices=synth.getVoices();const voice=voices.find(v=>v.lang.startsWith('en')&&v.localService)||voices.find(v=>v.lang.startsWith('en'));
   if(voice)current.voice=voice;
   const finish=ok=>{if(utterance!==current)return;utterance=null;if(activeSpeechChannel===channel)activeSpeechChannel=null;
    notice(ok);if(ok)callbacks.end();else callbacks.error();};
   current.onstart=()=>{if(utterance===current){notice(true);callbacks.start();}};
   current.onend=()=>finish(true);current.onerror=()=>finish(false);
   try{synth.speak(current);}catch{finish(false);}
  }
 };
 return channel;
}
// Fit the teaching phrase to its actual reserved caption region, not screenshot pixels.
export function fitCaptionText(phrase,caption){
 if(!phrase.textContent||typeof getComputedStyle!=='function')return;
 const style=getComputedStyle(caption),px=name=>parseFloat(style[name])||0;
 const width=caption.clientWidth-px('paddingLeft')-px('paddingRight');
 const others=[...caption.children].filter(el=>el!==phrase&&!el.hidden&&el.textContent);
 const occupied=others.reduce((sum,el)=>sum+el.getBoundingClientRect().height,0)+others.length*px('rowGap');
 const height=caption.clientHeight-px('paddingTop')-px('paddingBottom')-occupied;
 if(width<=0||height<=0)return;
 const minimum=Number(style.getPropertyValue('--lesson-min-size'))||32;
 const maximum=Number(style.getPropertyValue('--lesson-max-size'))||96;
 let low=minimum,high=maximum;
 function fits(size){phrase.style.fontSize=size+'px';return phrase.scrollWidth<=width+1&&Math.max(phrase.scrollHeight,phrase.getBoundingClientRect().height)<=height+1;}
 if(!fits(low)){caption.dataset.textOverflow='true';return;}
 for(let i=0;i<8;i++){const mid=(low+high)/2;if(fits(mid))low=mid;else high=mid;}
 fits(Math.max(24,Math.floor(low*(Number(phrase.dataset.wordScale)||1))));caption.dataset.textOverflow='false';
}
export function replayNarrationCues(timeline){
 if(!['same-engine-rescue-1','same-engine-rescue-2'].includes(timeline?.revision)||!Number.isFinite(timeline.duration)||timeline.duration<=0||timeline.duration>120||!Array.isArray(timeline.events)||timeline.events.length>100)return [];
 const words={thump:'THUMP',sniff:'SNIFF',crack:'CRACK',crunch:'CRUNCH',squish:'SQUISH'};
 const events=timeline.events.filter(e=>e&&typeof e==='object'&&typeof e.id==='string'&&/^[a-z0-9.-]{1,80}$/.test(e.id)&&Object.hasOwn(words,e.kind)&&Number.isFinite(e.start)&&Number.isFinite(e.end)&&e.start>=0&&e.end-e.start>=.001&&e.end<=timeline.duration).sort((a,b)=>a.start-b.start);
 return events.map((e,i)=>{
  const end=Math.min(timeline.duration,events[i+1]?.start??timeline.duration,Math.max(e.end,e.start+1.2));
  const offset=e.kind==='squish'?.6:e.kind==='sniff'?.32:.36;
  return {id:e.id,text:words[e.kind],template:'action',word_scale:e.kind==='thump'?Math.max(.6,Math.min(1,.6+((e.size||112)-48)/64*.4)):1,start_ms:e.start*1000,end_ms:end*1000,
   speech_ms:(e.start+Math.min(offset,(end-e.start)/3))*1000,fade_ms:(end-Math.min(.05,(end-e.start)/6))*1000};
 });
}
export function mountNarration(video,caption,{statusHost=caption,cues=storyCues}={}){
 const debug=new URLSearchParams(location.search).has('timing');
 const records=[];let fitFrame=0,lastText=null,volume=null,changingVolume=false,voiceOn=true,raf=0,buffering=false,seeking=false,duckedVolume=null;
 const phrase=document.createElement('span'),picture=document.createElement('span');
 phrase.id='story-phrase';picture.className='story-picture';picture.setAttribute('aria-hidden','true');
 caption.replaceChildren(picture,phrase);caption.lang='en';
 const notice=document.createElement('small');notice.id='narration-status';notice.textContent='English story · device voice';statusHost.append(notice);
 const failure=document.createElement('span');failure.id='story-audio-notice';failure.textContent='Voice unavailable';failure.hidden=true;failure.setAttribute('role','status');caption.append(failure);
 const channel=createSpeechChannel({notice:ok=>{notice.textContent=ok?'English story · device voice':'English captions · voice unavailable';failure.hidden=ok;queueFit();}});
 function queueFit(){if(typeof ResizeObserver==='undefined')return;cancelAnimationFrame(fitFrame);fitFrame=requestAnimationFrame(()=>fitCaptionText(phrase,caption));}
 if(typeof ResizeObserver!=='undefined')new ResizeObserver(queueFit).observe(caption);
 function duck(on){if(on&&scheduler.current?.template==='action')return;if(on&&volume===null){volume=video.volume;changingVolume=true;duckedVolume=volume*.2;video.volume=duckedVolume;changingVolume=false;}
  else if(!on&&volume!==null){const restore=volume;volume=null;duckedVolume=null;changingVolume=true;video.volume=restore;changingVolume=false;}}
 const cancel=()=>channel.cancel();
 let activeCues=cues,storyRead=false;
 const scheduler=new CueScheduler({cues,cancel,duck,mediaNow:()=>video.currentTime*1000,
  trace:r=>{if(debug){records.push({cue_revision:cueRevision,locale:'en-GB',...r});if(records.length>300)records.shift();}},
  view:(cue,fading)=>{const text=cue?.text||'',scale=cue?.word_scale||1,signature=text+':'+scale;if(signature!==lastText){lastText=signature;phrase.textContent=text;phrase.dataset.wordScale=String(scale);picture.textContent=cue?.picture||'';queueFit();}caption.classList.toggle('caption-fading',fading);},
  speak:(text,callbacks)=>channel.speak(text,callbacks)});
 const update=()=>scheduler.update(video.currentTime*1000,{running:!video.paused&&!video.ended&&!document.hidden&&!buffering&&!seeking,audible:voiceOn&&!video.muted&&video.volume>0});
 function loop(){update();if(!video.paused&&!video.ended)raf=requestAnimationFrame(loop);}
 video.addEventListener('play',()=>{cancelAnimationFrame(raf);loop();});
 video.addEventListener('pause',()=>{cancelAnimationFrame(raf);scheduler.stop();update();});
 video.addEventListener('waiting',()=>{buffering=true;scheduler.stop('buffering');});
 video.addEventListener('playing',()=>{buffering=false;update();});
 video.addEventListener('seeking',()=>{seeking=true;scheduler.reset();});
 video.addEventListener('seeked',()=>{seeking=false;update();});
 video.addEventListener('ended',()=>{scheduler.reset('ended');update();});
 video.addEventListener('volumechange',()=>{if(!changingVolume){if(volume!==null&&video.volume!==duckedVolume){volume=null;duckedVolume=null;}update();}});
 document.addEventListener('visibilitychange',()=>{if(document.hidden)scheduler.stop('hidden');});
 window.addEventListener('pagehide',()=>{cancelAnimationFrame(raf);cancelAnimationFrame(fitFrame);scheduler.stop('pagehide');});
 update();
 return {stop:reason=>scheduler.stop(reason),setCues(value){activeCues=value;scheduler.reset('film-revision');scheduler.cues=storyRead?activeCues.filter(c=>c.template==='action'):activeCues;update();},setStoryRead(value){storyRead=!!value;scheduler.reset('story-read');scheduler.cues=storyRead?activeCues.filter(c=>c.template==='action'):activeCues;update();},setEnabled(value){voiceOn=!!value;scheduler.stop('voice-option');update();},
  status:()=>({voice:scheduler.voice,enabled:voiceOn,englishOnly:true,trace:debug?records.map(r=>({...r})):[],traceEnabled:debug,
   timing:{cue_revision:cueRevision,locale:'en-GB',caption_onset_source:'view_callback',speech_onset_source:'speech_callback',acoustic_onset:'unverified'}})};
}
