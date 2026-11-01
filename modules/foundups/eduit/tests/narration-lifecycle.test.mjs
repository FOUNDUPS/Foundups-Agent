import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const source=await readFile(new URL('../../../communication/youtube_shorts/assets/kids_review/story-narration.mjs',import.meta.url),'utf8');
const engine=new URL('../../../../public/eduit/storytime/cue-scheduler.mjs',import.meta.url).href;
const {mountNarration}=await import('data:text/javascript;base64,'+Buffer.from(source.replace('../storytime/cue-scheduler.mjs',engine)).toString('base64'));
test('media buffering and seeking cancel voice; caller volume change survives restoration',()=>{
 const prior=Object.fromEntries(['window','document','location','SpeechSynthesisUtterance','requestAnimationFrame','cancelAnimationFrame'].map(k=>[k,globalThis[k]]));
 let frame,spoken=[],cancels=0;
 const element=()=>({classList:{toggle(){}},setAttribute(){},replaceChildren(){},append(){}});
 globalThis.document=Object.assign(new EventTarget(),{hidden:false,createElement:element});
 globalThis.location={search:'?timing'};
 globalThis.SpeechSynthesisUtterance=class{constructor(text){this.text=text;}};
 globalThis.window=Object.assign(new EventTarget(),{SpeechSynthesisUtterance,speechSynthesis:{getVoices:()=>[],speak:u=>spoken.push(u),cancel:()=>cancels++}});
 globalThis.requestAnimationFrame=fn=>(frame=fn,1);globalThis.cancelAnimationFrame=()=>{};
 try{
 const v=Object.assign(new EventTarget(),{currentTime:0,paused:true,ended:false,muted:false,volume:1});
 const api=mountNarration(v,element());v.paused=false;v.currentTime=.3;v.dispatchEvent(new Event('play'));
 assert.equal(spoken.length,1);spoken[0].onstart();assert.equal(v.volume,.2);
 v.volume=.6;v.dispatchEvent(new Event('volumechange'));v.dispatchEvent(new Event('waiting'));assert.equal(v.volume,.6);frame();assert.equal(spoken.length,1);
 v.dispatchEvent(new Event('playing'));assert.equal(spoken.length,2);
 v.dispatchEvent(new Event('seeking'));v.currentTime=4;frame();assert.equal(spoken.length,2);
 v.dispatchEvent(new Event('seeked'));assert.equal(spoken.length,3);assert.equal(spoken[2].text,'there were dinosaurs');
 spoken[2].onstart();v.volume=0;v.dispatchEvent(new Event('volumechange'));frame();assert.equal(v.volume,0);assert.equal(spoken.length,3);
 assert.ok(cancels>=2);assert.ok(api.status().trace.some(r=>r.reason==='buffering'));
 }finally{for(const [k,v]of Object.entries(prior))if(v===undefined)delete globalThis[k];else globalThis[k]=v;}
});

function narrationFixture(search,run){
 const keys=['window','document','location','SpeechSynthesisUtterance','requestAnimationFrame','cancelAnimationFrame'];
 const prior=Object.fromEntries(keys.map(k=>[k,globalThis[k]]));let frame;const spoken=[];
 const element=()=>({textContent:'',children:[],classList:{toggle(){}},setAttribute(){},replaceChildren(...nodes){this.children=nodes;},append(node){this.children.push(node);}});
 globalThis.document=Object.assign(new EventTarget(),{hidden:false,createElement:element});globalThis.location={search};
 globalThis.SpeechSynthesisUtterance=class{constructor(text){this.text=text;}};
 globalThis.window=Object.assign(new EventTarget(),{SpeechSynthesisUtterance,speechSynthesis:{getVoices:()=>[],speak:u=>spoken.push(u),cancel(){}}});
 globalThis.requestAnimationFrame=fn=>(frame=fn,1);globalThis.cancelAnimationFrame=()=>{};
 try{const video=Object.assign(new EventTarget(),{currentTime:0,paused:true,ended:false,muted:false,volume:1}),caption=element();
  const api=mountNarration(video,caption);run({api,video,caption,spoken,tick:()=>frame()});
 }finally{for(const [k,v]of Object.entries(prior))if(v===undefined)delete globalThis[k];else globalThis[k]=v;}
}
test('adapter binds live callback time and caption correspondence to explicit cue evidence',()=>narrationFixture('?timing',({api,video,caption,spoken})=>{
 video.paused=false;video.currentTime=.3;video.dispatchEvent(new Event('play'));
 assert.equal(caption.children[1].textContent,spoken[0].text);
 video.currentTime=.7;spoken[0].onstart();
 const status=api.status(),r=status.trace.find(x=>x.type==='speech_started');
 assert.equal(r.media_ms,700);assert.equal(r.media_clock,'sampled');assert.equal(r.onset_source,'speech_callback');
 assert.equal(r.cue_revision,'english-narration-1');assert.equal(r.locale,'en-GB');
 assert.equal(status.timing.acoustic_onset,'unverified');assert.equal(status.timing.caption_onset_source,'view_callback');
}));
test('debug evidence is bounded and opt-in, while status returns detached trace rows',()=>{
 for(const search of ['', '?timing'])narrationFixture(search,({api,video})=>{
  video.paused=false;for(let i=0;i<400;i++){video.currentTime=i%2?.3:4;video.dispatchEvent(new Event('play'));}
  const rows=api.status().trace;assert.equal(rows.length,search?300:0);
  if(search){rows[0].cue_id='tampered';assert.notEqual(api.status().trace[0].cue_id,'tampered');}
 });
});
