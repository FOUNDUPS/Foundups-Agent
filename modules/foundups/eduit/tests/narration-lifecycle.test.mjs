import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {replay} from '../storytime_replay.mjs';
const source=await readFile(new URL('../../../communication/youtube_shorts/assets/kids_review/story-narration.mjs',import.meta.url),'utf8');
const engine=new URL('../../../../public/eduit/storytime/cue-scheduler.mjs',import.meta.url).href;
const {mountNarration,replayNarrationCues,fitCaptionText}=await import('data:text/javascript;base64,'+Buffer.from(source.replace('../storytime/cue-scheduler.mjs',engine)).toString('base64'));

test('movie action cues use actual replay time and reject unknown or malformed timelines',()=>{
 const timeline={revision:'same-engine-rescue-1',duration:25,events:[{id:'victory-thump',kind:'thump',start:21.3666667,end:22.1666667}]};
 const [cue]=replayNarrationCues(timeline);assert.equal(cue.start_ms,timeline.events[0].start*1000);
 assert.equal(cue.text,'THUMP');assert.ok(cue.speech_ms>cue.start_ms&&cue.speech_ms<cue.fade_ms);
 for(const value of [null,{}, {...timeline,revision:'old'}, {...timeline,duration:Infinity}])assert.deepEqual(replayNarrationCues(value),[]);
 assert.deepEqual(replayNarrationCues({...timeline,events:[{kind:'remote-script',start:0,end:1},{kind:'thump',start:-1,end:2}]}),[]);
 assert.deepEqual(replayNarrationCues({...timeline,events:[null,{id:{},kind:'thump',start:1,end:2}]}),[]);
 const [short]=replayNarrationCues({...timeline,events:[{id:'short',kind:'thump',start:1,end:1.002}]});
 assert.ok(short.start_ms<short.speech_ms&&short.speech_ms<short.fade_ms&&short.fade_ms<short.end_ms);
 const actual=replay();assert.equal(replayNarrationCues(actual).length,actual.events.length);
});
test('media buffering and seeking cancel voice; caller volume change survives restoration',()=>{
 const prior=Object.fromEntries(['window','document','location','SpeechSynthesisUtterance','requestAnimationFrame','cancelAnimationFrame'].map(k=>[k,globalThis[k]]));
 let frame,spoken=[],cancels=0;
 const element=()=>({dataset:{},classList:{toggle(){}},setAttribute(){},replaceChildren(){},append(){}});
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
 const element=()=>({dataset:{},textContent:'',children:[],classList:{toggle(){}},setAttribute(){},replaceChildren(...nodes){this.children=nodes;},append(node){this.children.push(node);}});
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

test('completed story suppresses repeated movie introduction while retaining action teaching',()=>narrationFixture('',({api,video})=>{
 api.setStoryRead(true);video.paused=false;video.currentTime=.3;video.dispatchEvent(new Event('play'));
 assert.equal(api.status().voice,'idle');
 video.currentTime=4;video.dispatchEvent(new Event('play'));assert.equal(api.status().voice,'idle');
 video.currentTime=10.5;video.dispatchEvent(new Event('play'));assert.equal(api.status().voice,'requested');
 api.setStoryRead(false);video.currentTime=.3;video.dispatchEvent(new Event('play'));assert.equal(api.status().voice,'requested');
}));
test('action speech preserves complete Foley and survives the old short sniff endpoint',()=>narrationFixture('',({api,video,caption,spoken,tick})=>{
 const film=replay(),event=film.events.find(e=>e.kind==='sniff'),cues=replayNarrationCues(film),cue=cues.find(c=>c.id===event.id);
 assert.ok(cue.end_ms-cue.speech_ms>=800);api.setCues(cues);video.paused=false;video.currentTime=(cue.speech_ms+1)/1000;video.dispatchEvent(new Event('play'));
 assert.equal(spoken.length,1);assert.equal(spoken[0].text,'SNIFF');spoken[0].onstart();assert.equal(video.volume,1,'action voice must not duck instructional Foley');
 video.currentTime=event.end+.05;tick();assert.equal(api.status().voice,'speaking');assert.equal(typeof spoken[0].onend,'function');assert.equal(caption.children[1].textContent,'SNIFF');
 video.paused=true;video.dispatchEvent(new Event('pause'));assert.equal(spoken[0].onend,null);assert.equal(video.volume,1);
 const thumps=cues.filter(c=>c.text==='THUMP');assert.ok(thumps[0].word_scale<thumps[1].word_scale&&thumps[1].word_scale<thumps[2].word_scale);
}));
test('actual caption fit retains distinct far, near and landing sizes within the same available box',()=>{
 const prior=globalThis.getComputedStyle;globalThis.getComputedStyle=()=>({paddingLeft:'0',paddingRight:'0',paddingTop:'0',paddingBottom:'0',rowGap:'0',getPropertyValue:n=>n==='--lesson-min-size'?'32':'96'});
 try{
  const phrase={textContent:'THUMP',dataset:{},style:{fontSize:'32px'},get scrollWidth(){return parseFloat(this.style.fontSize)*3;},get scrollHeight(){return parseFloat(this.style.fontSize);},getBoundingClientRect(){return {height:parseFloat(this.style.fontSize)};}};
  const caption={clientWidth:390,clientHeight:64,children:[phrase],dataset:{}};
  const sizes=replayNarrationCues(replay()).filter(c=>c.text==='THUMP').map(c=>{phrase.dataset.wordScale=String(c.word_scale);fitCaptionText(phrase,caption);return parseFloat(phrase.style.fontSize);});
  assert.ok(sizes[0]<sizes[1]&&sizes[1]<sizes[2]);assert.ok(sizes[0]>=24);assert.ok(sizes[2]<=65);
 }finally{if(prior===undefined)delete globalThis.getComputedStyle;else globalThis.getComputedStyle=prior;}
});
