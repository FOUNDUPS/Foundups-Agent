import {CueScheduler} from '../storytime/cue-scheduler.mjs';
export function mountNarration(video,caption){
 const synth=window.speechSynthesis,debug=new URLSearchParams(location.search).has('timing');
 const records=[];let utterance=null,volume=null,changingVolume=false,voiceOn=true,raf=0,buffering=false,seeking=false,duckedVolume=null;
 const phrase=document.createElement('span'),picture=document.createElement('span');
 phrase.id='story-phrase';picture.className='story-picture';picture.setAttribute('aria-hidden','true');
 caption.replaceChildren(picture,phrase);caption.lang='en';
 const notice=document.createElement('small');notice.id='narration-status';notice.textContent='English story · device voice';caption.append(notice);
 function duck(on){if(on&&volume===null){volume=video.volume;changingVolume=true;duckedVolume=volume*.2;video.volume=duckedVolume;changingVolume=false;}
  else if(!on&&volume!==null){const restore=volume;volume=null;duckedVolume=null;changingVolume=true;video.volume=restore;changingVolume=false;}}
 function cancel(){if(utterance){utterance.onstart=utterance.onend=utterance.onerror=null;synth?.cancel();utterance=null;}}
 const scheduler=new CueScheduler({cancel,duck,
  trace:r=>{if(debug){records.push(r);if(records.length>300)records.shift();}},
  view:(cue,fading)=>{phrase.textContent=cue?.text||'';picture.textContent=cue?.picture||'';caption.classList.toggle('caption-fading',fading);},
  speak:(text,callbacks)=>{
   if(!synth||!window.SpeechSynthesisUtterance){notice.textContent='English captions · voice unavailable';callbacks.error();return;}
   utterance=new SpeechSynthesisUtterance(text);utterance.lang='en-GB';utterance.rate=.9;utterance.volume=.85;
   const voice=synth.getVoices().find(v=>v.lang.startsWith('en')&&v.localService)||synth.getVoices().find(v=>v.lang.startsWith('en'));
   if(voice)utterance.voice=voice;
   utterance.onstart=()=>{notice.textContent='English story · device voice';callbacks.start();};
   utterance.onend=callbacks.end;utterance.onerror=()=>{notice.textContent='English captions · voice unavailable';callbacks.error();};
   synth.speak(utterance);
  }});
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
 window.addEventListener('pagehide',()=>{cancelAnimationFrame(raf);scheduler.stop('pagehide');});
 update();
 return {stop:reason=>scheduler.stop(reason),setEnabled(value){voiceOn=!!value;scheduler.stop('voice-option');update();},
  status:()=>({voice:scheduler.voice,englishOnly:true,trace:debug?records.slice():[],traceEnabled:debug})};
}
