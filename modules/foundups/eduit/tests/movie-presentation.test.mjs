import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {replay,replayWorld} from '../storytime_replay.mjs';
import {scene,scenePresentation} from '../../../../public/eduit/storytime/scene.mjs';
import {validateMovieFrames,movieFrameIndex,mountMoviePresentation,loadMovieFrames} from '../../../../public/eduit/storytime/movie-presentation.mjs';
const replayData=replay(),raw={schema:'eduit.movie_frames.v1',revision:replayData.revision,fps:30,duration:25,frames:replayData.states.map(replayWorld)};
const recording=validateMovieFrames(raw);
test('responsive movie retains every canonical film frame and end-frame boundary',()=>{
 for(let i=0;i<750;i++)assert.equal(scene(recording.frames[i]),scene(raw.frames[i]),'film frame '+i);
 for(const [time,index]of [[0,0],[1/30,1],[.999,29],[24.999,749],[25,749]])assert.equal(movieFrameIndex(time,recording),index);
 for(const time of [NaN,-1,Infinity,'1'])assert.throws(()=>movieFrameIndex(time,recording));
});
test('external frame data cannot introduce executable SVG text, IDs or unbounded values',()=>{
 for(const mutate of [x=>x.frames.pop(),x=>x.fps=60,x=>x.frames[0].actors[0].id='x" onload="alert(1)',x=>x.frames[0].actors[0].x=NaN,x=>x.frames[0].actors[0].scale=1e9,x=>x.frames[0].actors[0].status='unreviewed',x=>x.frames[0].actors[1].id='parent-1',x=>x.frames[0].impact=2,x=>x.frames[0].shake='true',x=>x.frames[0].cue={kind:'thump',word:'<script>'}]){
  const copy=structuredClone(raw);mutate(copy);assert.throws(()=>validateMovieFrames(copy));
 }
});
function fixture({load=async()=>({...recording,renderer:{scene,scenePresentation}}),fallback=false,wordPlacement='below',captionAvailable=true,inline=false,onChange=()=>{}}={}){
 const classes=new Set(),queue=new Map();let next=1,resizeCb,writes=0;
 const layer={hidden:true,setAttribute(){},remove(){},set innerHTML(v){this.svg=v;writes++;}};
 const doc=Object.assign(new EventTarget(),{hidden:false,createElement:()=>layer});
 const video=Object.assign(new EventTarget(),{currentTime:0,paused:true,ended:false,requestVideoFrameCallback:cb=>{const id=next++;queue.set(id,cb);return id;},cancelVideoFrameCallback:id=>queue.delete(id)});
 if(fallback){delete video.requestVideoFrameCallback;delete video.cancelVideoFrameCallback;}
 const panel={dataset:{},classList:{add:x=>classes.add(x),remove:x=>classes.delete(x)}};
 let width=390,height=650;
 const surface={append(){},getBoundingClientRect:()=>({width,height})};
 const view=mountMoviePresentation({video,panel,surface,load,wordPlacement,captionAvailable,inline,onChange,document:doc,requestFrame:cb=>{const id=next++;queue.set(id,cb);return id;},cancelFrame:id=>queue.delete(id),observe:cb=>{resizeCb=cb;return {observe(){},disconnect(){}};}});
 return {view,video,doc,layer,panel,queue,classes,writes:()=>writes,event:name=>video.dispatchEvent(new Event(name)),resize:(w,h)=>{width=w;height=h;resizeCb();},present(time){const [id,cb]=queue.entries().next().value;queue.delete(id);video.currentTime=time;cb(0,{mediaTime:time});}};
}
test('video alone advances picture; pause, seek, resize, collapse and repeat preserve transport',async()=>{
 const f=fixture();assert.equal(f.queue.size,0);f.view.setExpanded(true);await f.view.ready();assert.equal(f.queue.size,0);assert.equal(f.layer.hidden,false);
 const still=f.layer.svg;f.event('pause');assert.equal(f.layer.svg,still);assert.equal(f.writes(),1);
 f.video.paused=false;f.event('play');assert.equal(f.queue.size,1);f.present(22.1);assert.notEqual(f.layer.svg,still);assert.equal(f.queue.size,1);
 f.video.paused=true;f.event('pause');assert.equal(f.queue.size,0);assert.equal(f.video.currentTime,22.1);
 f.resize(768,900);assert.equal(f.video.currentTime,22.1);assert.equal(f.queue.size,0);
 f.view.setExpanded(false);assert.equal(f.layer.hidden,true);assert.equal(f.classes.size,0);
 f.view.setExpanded(true);assert.equal(f.layer.hidden,false,'same retained frame reveals again');
 f.doc.hidden=true;f.doc.dispatchEvent(new Event('visibilitychange'));assert.equal(f.layer.hidden,true);
 f.doc.hidden=false;f.doc.dispatchEvent(new Event('visibilitychange'));assert.equal(f.layer.hidden,false,'same frame after foreground');
 f.video.currentTime=0;f.event('seeked');assert.equal(f.video.currentTime,0);assert.ok(f.layer.svg.includes('data-actor="parent-1"'));
 f.video.paused=false;f.event('play');f.view.dispose();assert.equal(f.queue.size,0);assert.equal(f.classes.size,0);
});
test('failed sidecar leaves native movie visible and never starts transport',async()=>{
 const f=fixture({load:async()=>{throw Error('digest mismatch');}});f.view.setExpanded(true);await f.view.ready();assert.equal(f.classes.size,0);assert.equal(f.layer.hidden,true);assert.equal(f.video.paused,true);assert.equal(f.queue.size,0);f.view.dispose();
});
test('one-word placement switches paused drawing without changing time, actors or recorded data',async()=>{
 const before=structuredClone(recording.frames),f=fixture();f.view.setExpanded(true);await f.view.ready();
 f.video.currentTime=.9;f.event('seeked');const outside=f.layer.svg;
 assert.equal(f.view.status().wordPlacement,'below');assert.equal(f.panel.dataset.wordPlacement,'below');assert.ok(!outside.includes('data-learning='));
 assert.equal(f.view.setWordPlacement('scene'),true);const inside=f.layer.svg;assert.ok(inside.includes('>SNIFF</text>'));assert.notEqual(inside,outside);
 const actors=svg=>[...svg.matchAll(/<g data-(?:actor|survivor)="[^"]+" transform="[^"]+"/g)].map(m=>m[0]);assert.deepEqual(actors(inside),actors(outside));
 assert.equal(f.video.currentTime,.9);assert.equal(f.video.paused,true);assert.equal(f.queue.size,0);assert.deepEqual(recording.frames,before);
 for(const invalid of ['both','https://example.invalid/words.js',{},null]){assert.equal(f.view.setWordPlacement(invalid),false);assert.equal(f.layer.svg,inside);assert.equal(f.view.status().wordPlacement,'scene');}
 f.view.setWordPlacement('below');assert.equal(f.layer.svg,outside);f.view.dispose();assert.equal(f.panel.dataset.wordPlacement,undefined);assert.equal(f.view.setWordPlacement('scene'),false);assert.equal(f.panel.dataset.wordPlacement,undefined);
});
test('invalid initial word profiles fail before loading or drawing, while failed media remains explicit',async()=>{
 assert.throws(()=>fixture({wordPlacement:'both'}),TypeError);
 const states=[],f=fixture({onChange:s=>states.push(s),load:async()=>{throw Error('missing sidecar');}});f.view.setExpanded(true);await f.view.ready();
 assert.equal(f.view.status().failed,true);assert.equal(f.view.status().ready,false);assert.equal(f.classes.has('movie-responsive'),false);assert.equal(f.layer.hidden,true);assert.equal(f.video.paused,true);assert.ok(states.some(s=>s.failed));f.view.dispose();
});
test('unavailable separate captions retain picture labels until caption metadata is ready',async()=>{
 const f=fixture({captionAvailable:false});f.view.setExpanded(true);await f.view.ready();f.video.currentTime=.9;f.event('seeked');
 assert.equal(f.view.status().wordPlacement,'below');assert.equal(f.view.status().effectivePlacement,'scene');assert.ok(f.layer.svg.includes('>SNIFF</text>'));
 assert.equal(f.view.setCaptionAvailable('yes'),false);assert.equal(f.view.setCaptionAvailable(true),true);assert.equal(f.view.status().effectivePlacement,'below');assert.ok(!f.layer.svg.includes('data-learning='));
 assert.equal(f.video.currentTime,.9);assert.equal(f.video.paused,true);f.view.dispose();assert.equal(f.view.setCaptionAvailable(false),false);
});
test('rAF fallback samples retained media time and performs no work while collapsed',async()=>{
 const f=fixture({fallback:true});f.view.setExpanded(true);await f.view.ready();f.video.paused=false;f.event('play');assert.equal(f.queue.size,1);f.present(21);const picture=f.layer.svg;assert.equal(f.queue.size,1);f.present(21);assert.equal(f.layer.svg,picture);const count=f.writes();f.view.setExpanded(false);assert.equal(f.queue.size,0);f.event('play');assert.equal(f.writes(),count);assert.equal(f.queue.size,0);f.view.dispose();
});
test('loader accepts bound assets and rejects mismatched frames, movie and renderer',async()=>{
 const previous=globalThis.location;globalThis.location=new URL('https://storytime.example/');
 const encode=v=>Buffer.from(typeof v==='string'?v:JSON.stringify(v));
 const sha=v=>createHash('sha256').update(v).digest('hex');
 const frameBytes=encode(raw),movieBytes=encode('unchanged movie'),sourceBytes=encode('renderer');
 const binding={schema:'eduit.movie_presentation.v1',revision:replayData.revision,fps:30,duration:25,frameCount:750,framesSha256:sha(frameBytes),videoSha256:sha(movieBytes),sources:Object.fromEntries(['scene.mjs','rig.mjs','learning-events.mjs'].map(n=>[n,sha(sourceBytes)]))};
 binding.rendererGeneration=sha(encode(binding.sources));
 try{
  for(const bad of [null,'frames','movie','renderer']){
   const copy=structuredClone(binding);if(bad==='frames')copy.framesSha256='0'.repeat(64);if(bad==='movie')copy.videoSha256='0'.repeat(64);if(bad==='renderer')copy.sources['rig.mjs']='0'.repeat(64);
   const fetcher=async url=>{const name=new URL(url).pathname.split('/').at(-1);const data=name==='movie-presentation.json'?encode(copy):name==='movie-frames.json'?frameBytes:name==='little-shrew.mp4'?movieBytes:sourceBytes;return {ok:true,redirected:false,headers:new Headers({'content-length':String(data.length)}),arrayBuffer:async()=>data.buffer.slice(data.byteOffset,data.byteOffset+data.length)};};
   let imports=0;const importer=async url=>{imports++;assert.ok(url.pathname.endsWith('/presentations/'+binding.rendererGeneration+'/scene.mjs'));return {scene,scenePresentation:()=>({top:0,bottom:0})};};
   const promise=loadMovieFrames({src:'https://storytime.example/storytime/assets/little-shrew.mp4'},{fetcher,importer});if(bad){await assert.rejects(promise);assert.equal(imports,0);}else {assert.equal((await promise).frames.length,750);assert.equal(imports,1);}
  }
 }finally{globalThis.location=previous;}
});
test('mount uses the verified generation renderer rather than the static fallback',async()=>{
 let renders=0;const f=fixture({load:async()=>({...recording,renderer:{scene:()=>{renders++;return '<svg data-generation="verified"/>';},scenePresentation:()=>({top:1,bottom:1})}})});
 f.view.setExpanded(true);await f.view.ready();assert.equal(renders,1);assert.equal(f.layer.svg,'<svg data-generation="verified"/>');f.view.dispose();
});
test('unexpected origin or invalid binding fails before requesting frame/video payloads',async()=>{
 const previous=globalThis.location;globalThis.location=new URL('https://storytime.example/');
 try{
  let calls=0;const fetcher=async()=>{calls++;return {ok:true,redirected:false,headers:new Headers(),arrayBuffer:async()=>new TextEncoder().encode('{}').buffer};};
  await assert.rejects(loadMovieFrames({src:'https://other.example/storytime/assets/little-shrew.mp4'},{fetcher}));assert.equal(calls,0);
  await assert.rejects(loadMovieFrames({src:'https://storytime.example/storytime/assets/little-shrew.mp4'},{fetcher}));assert.equal(calls,1);
 }finally{globalThis.location=previous;}
});


test('inline opt-in retains one clean picture through compact/fullscreen without transport writes',async()=>{
 const f=fixture({inline:true});f.resize(390,219.375);f.view.setExpanded(false);await f.view.ready();
 assert.equal(f.view.status().inline,true);assert.equal(f.view.status().expanded,false);assert.equal(f.classes.has('movie-responsive'),true);
 f.video.currentTime=2.5;f.event('seeked');assert.ok(!f.layer.svg.includes('data-learning='));
 const compact=f.layer.svg;assert.ok(compact.includes('viewBox="0 0 960 540"'));
 f.resize(390,650);f.view.setExpanded(true);assert.notEqual(f.layer.svg,compact);assert.equal(f.video.currentTime,2.5);assert.equal(f.video.paused,true);
 f.view.setExpanded(false);assert.ok(f.layer.svg.includes('viewBox="0 0 960 540"'));assert.equal(f.layer.hidden,false);
 f.view.setWordPlacement('scene');assert.ok(f.layer.svg.includes('>THUMP</text>'));
 f.video.paused=false;f.event('play');assert.equal(f.queue.size,1);f.present(4);assert.equal(f.video.currentTime,4);
 f.doc.hidden=true;f.doc.dispatchEvent(new Event('visibilitychange'));assert.equal(f.queue.size,0);assert.equal(f.layer.hidden,true);
 f.doc.hidden=false;f.doc.dispatchEvent(new Event('visibilitychange'));assert.equal(f.layer.hidden,false);assert.equal(f.queue.size,1);
 f.view.dispose();assert.equal(f.queue.size,0);assert.equal(f.classes.has('movie-responsive'),false);
});

test('inline failure leaves native fallback and unknown inline option is rejected',async()=>{
 assert.throws(()=>fixture({inline:'true'}),TypeError);
 const f=fixture({inline:true,load:async()=>{throw Error('missing data');}});f.view.setExpanded(false);await f.view.ready();
 assert.equal(f.view.status().failed,true);assert.equal(f.layer.hidden,true);assert.equal(f.classes.has('movie-responsive'),false);assert.equal(f.video.paused,true);assert.equal(f.queue.size,0);f.view.dispose();
});
