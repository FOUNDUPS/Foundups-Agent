import {CueScheduler} from '../storytime/cue-scheduler.mjs';
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
 fits(Math.floor(low));caption.dataset.textOverflow='false';
}
export function mountNarration(video,caption,{statusHost=caption}={}){
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
 function duck(on){if(on&&volume===null){volume=video.volume;changingVolume=true;duckedVolume=volume*.2;video.volume=duckedVolume;changingVolume=false;}
  else if(!on&&volume!==null){const restore=volume;volume=null;duckedVolume=null;changingVolume=true;video.volume=restore;changingVolume=false;}}
 const cancel=()=>channel.cancel();
 const scheduler=new CueScheduler({cancel,duck,
  trace:r=>{if(debug){records.push(r);if(records.length>300)records.shift();}},
  view:(cue,fading)=>{const text=cue?.text||'';if(text!==lastText){lastText=text;phrase.textContent=text;picture.textContent=cue?.picture||'';queueFit();}caption.classList.toggle('caption-fading',fading);},
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
 return {stop:reason=>scheduler.stop(reason),setEnabled(value){voiceOn=!!value;scheduler.stop('voice-option');update();},
  status:()=>({voice:scheduler.voice,enabled:voiceOn,englishOnly:true,trace:debug?records.slice():[],traceEnabled:debug})};
}
