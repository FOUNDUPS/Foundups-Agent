import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {replay,replayWorld} from '../storytime_replay.mjs';
import {scene} from '../../../../public/eduit/storytime/scene.mjs';
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
function fixture({load=async()=>recording,fallback=false}={}){
 const classes=new Set(),queue=new Map();let next=1,resizeCb,writes=0;
 const layer={hidden:true,setAttribute(){},remove(){},set innerHTML(v){this.svg=v;writes++;}};
 const doc=Object.assign(new EventTarget(),{hidden:false,createElement:()=>layer});
 const video=Object.assign(new EventTarget(),{currentTime:0,paused:true,ended:false,requestVideoFrameCallback:cb=>{const id=next++;queue.set(id,cb);return id;},cancelVideoFrameCallback:id=>queue.delete(id)});
 if(fallback){delete video.requestVideoFrameCallback;delete video.cancelVideoFrameCallback;}
 const panel={classList:{add:x=>classes.add(x),remove:x=>classes.delete(x)}};
 let width=390,height=650;
 const surface={append(){},getBoundingClientRect:()=>({width,height})};
 const view=mountMoviePresentation({video,panel,surface,load,document:doc,requestFrame:cb=>{const id=next++;queue.set(id,cb);return id;},cancelFrame:id=>queue.delete(id),observe:cb=>{resizeCb=cb;return {observe(){},disconnect(){}};}});
 return {view,video,doc,layer,queue,classes,writes:()=>writes,event:name=>video.dispatchEvent(new Event(name)),resize:(w,h)=>{width=w;height=h;resizeCb();},present(time){const [id,cb]=queue.entries().next().value;queue.delete(id);video.currentTime=time;cb(0,{mediaTime:time});}};
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
test('rAF fallback samples retained media time and performs no work while collapsed',async()=>{
 const f=fixture({fallback:true});f.view.setExpanded(true);await f.view.ready();f.video.paused=false;f.event('play');assert.equal(f.queue.size,1);f.present(21);const picture=f.layer.svg;assert.equal(f.queue.size,1);f.present(21);assert.equal(f.layer.svg,picture);const count=f.writes();f.view.setExpanded(false);assert.equal(f.queue.size,0);f.event('play');assert.equal(f.writes(),count);assert.equal(f.queue.size,0);f.view.dispose();
});
test('loader accepts bound assets and rejects mismatched frames, movie and renderer',async()=>{
 const previous=globalThis.location;globalThis.location=new URL('https://storytime.example/');
 const encode=v=>Buffer.from(typeof v==='string'?v:JSON.stringify(v));
 const sha=v=>createHash('sha256').update(v).digest('hex');
 const frameBytes=encode(raw),movieBytes=encode('unchanged movie'),sourceBytes=encode('renderer');
 const binding={schema:'eduit.movie_presentation.v1',revision:'same-engine-rescue-1',fps:30,duration:25,frameCount:750,framesSha256:sha(frameBytes),videoSha256:sha(movieBytes),sources:Object.fromEntries(['scene.mjs','rig.mjs','learning-events.mjs'].map(n=>[n,sha(sourceBytes)]))};
 try{
  for(const bad of [null,'frames','movie','renderer']){
   const copy=structuredClone(binding);if(bad==='frames')copy.framesSha256='0'.repeat(64);if(bad==='movie')copy.videoSha256='0'.repeat(64);if(bad==='renderer')copy.sources['rig.mjs']='0'.repeat(64);
   const fetcher=async url=>{const name=new URL(url).pathname.split('/').at(-1);const data=name==='movie-presentation.json'?encode(copy):name==='movie-frames.json'?frameBytes:name==='little-shrew.mp4'?movieBytes:sourceBytes;return {ok:true,redirected:false,headers:new Headers({'content-length':String(data.length)}),arrayBuffer:async()=>data.buffer.slice(data.byteOffset,data.byteOffset+data.length)};};
   const promise=loadMovieFrames({src:'https://storytime.example/storytime/assets/little-shrew.mp4'},{fetcher});if(bad)await assert.rejects(promise);else assert.equal((await promise).frames.length,750);
  }
 }finally{globalThis.location=previous;}
});
test('unexpected origin or invalid binding fails before requesting frame/video payloads',async()=>{
 const previous=globalThis.location;globalThis.location=new URL('https://storytime.example/');
 try{
  let calls=0;const fetcher=async()=>{calls++;return {ok:true,redirected:false,headers:new Headers(),arrayBuffer:async()=>new TextEncoder().encode('{}').buffer};};
  await assert.rejects(loadMovieFrames({src:'https://other.example/storytime/assets/little-shrew.mp4'},{fetcher}));assert.equal(calls,0);
  await assert.rejects(loadMovieFrames({src:'https://storytime.example/storytime/assets/little-shrew.mp4'},{fetcher}));assert.equal(calls,1);
 }finally{globalThis.location=previous;}
});
