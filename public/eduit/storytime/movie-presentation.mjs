// Responsive film picture, driven exclusively by the existing video's media clock.
import {scene,scenePresentation} from './scene.mjs';
const ids=new Set(['parent-1','parent-2','baby-1','baby-2','baby-3']);
const statuses=new Set(['sleeping','awake','wandering','moving','safe','lost']);
const kinds=new Set(['thump','crack','crunch','squish','sniff']);
const number=(v,min,max)=>{if(typeof v!=='number'||!Number.isFinite(v)||v<min||v>max)throw Error('Invalid movie number');return v;};
const text=v=>{if(typeof v!=='string'||!/^[-a-zA-Z0-9 !.]{1,120}$/.test(v))throw Error('Invalid movie text');return v;};
const bool=v=>{if(typeof v!=='boolean')throw Error('Invalid movie flag');return v;};
export function validateMovieFrames(data){
 if(data?.schema!=='eduit.movie_frames.v1'||data.revision!=='same-engine-rescue-1'||data.fps!==30||data.duration!==25||!Array.isArray(data.frames)||data.frames.length!==750)throw Error('Unsupported movie frames');
 const frames=data.frames.map(w=>{
  const out={t:number(w.t,0,120)};
  for(const key of ['warning','reaction','collapse','impact','lift','turn'])out[key]=number(w[key],0,1);
  out.rootSway=number(w.rootSway,-20,20);
  for(const key of ['shake','progressiveCracks','dust'])out[key]=bool(w[key]);
  if(!Array.isArray(w.actors)||w.actors.length!==5||new Set(w.actors.map(a=>a.id)).size!==5)throw Error('Invalid movie cast');
  out.actors=w.actors.map(a=>{
   if(!ids.has(a.id)||!statuses.has(a.status))throw Error('Invalid movie actor');
   return {id:a.id,status:a.status,x:number(a.x,-200,1100),y:number(a.y,-200,700),scale:number(a.scale,.1,2),awake:bool(a.awake)};
  });
  if(w.cue!=null){
   const c=w.cue;if(!kinds.has(c.kind))throw Error('Invalid movie cue');
   out.cue={id:text(c.id),kind:c.kind,word:text(c.word),start:number(c.start,0,120),end:number(c.end,0,120),x:number(c.x,-200,1200),y:number(c.y,-200,800),size:number(c.size,1,200)};
   if(c.actorId!==undefined){if(!ids.has(c.actorId))throw Error('Invalid cue actor');out.cue.actorId=c.actorId;}
   if(c.shakeSize!==undefined)out.cue.shakeSize=number(c.shakeSize,0,150);
  }
  return out;
 });
 return {fps:30,duration:25,frames};
}
export function movieFrameIndex(time,recording){return Math.min(recording.frames.length-1,Math.max(0,Math.floor(number(time,0,1e6)*recording.fps+1e-6)));}
const digest=async bytes=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),v=>v.toString(16).padStart(2,'0')).join('');
export async function loadMovieFrames(video,{fetcher=fetch}={}){
 const media=new URL(video.currentSrc||video.src,location.href);media.search='';
 if(media.origin!==location.origin||!media.pathname.endsWith('/storytime/assets/little-shrew.mp4'))throw Error('Unsupported movie origin');
 const base=new URL('./',media);
 const get=async(url,max)=>{
  const response=await fetcher(url,{cache:'no-store',credentials:'same-origin'});
  if(!response.ok||response.redirected)throw Error('Movie data unavailable');
  const length=Number(response.headers.get('content-length'));if(length>max)throw Error('Movie data too large');
  const bytes=await response.arrayBuffer();if(bytes.byteLength>max)throw Error('Movie data too large');return bytes;
 };
 const binding=JSON.parse(new TextDecoder().decode(await get(new URL('movie-presentation.json',base),4096)));
 if(binding?.schema!=='eduit.movie_presentation.v1'||binding.revision!=='same-engine-rescue-1'||binding.fps!==30||binding.duration!==25||binding.frameCount!==750)throw Error('Unsupported movie binding');
 const [framesBytes,videoBytes]=await Promise.all([get(new URL('movie-frames.json',base),2e6),get(media,4e6)]);
 if(await digest(framesBytes)!==binding.framesSha256||await digest(videoBytes)!==binding.videoSha256)throw Error('Movie asset mismatch');
 for(const name of ['scene.mjs','rig.mjs','learning-events.mjs']){
  const bytes=await get(new URL(name,import.meta.url),200000);
  if(await digest(bytes)!==binding.sources?.[name])throw Error('Movie renderer mismatch');
 }
 return validateMovieFrames(JSON.parse(new TextDecoder().decode(framesBytes)));
}
export function mountMoviePresentation({video,panel,surface,load=()=>loadMovieFrames(video),document:doc=globalThis.document,requestFrame=cb=>requestAnimationFrame(cb),cancelFrame=id=>cancelAnimationFrame(id),observe=cb=>new ResizeObserver(cb)}){
 const layer=doc.createElement('div');layer.className='movie-scene';layer.setAttribute('aria-hidden','true');layer.hidden=true;surface.append(layer);
 let recording=null,pending=null,failed=false,disposed=false,callback=null,last='',enabled=false;
 const visible=()=>enabled&&!doc.hidden&&!disposed&&!failed;
 function cancel(){if(callback){if(callback.video)video.cancelVideoFrameCallback(callback.id);else cancelFrame(callback.id);callback=null;}}
 function draw(time=video.currentTime){
  if(!visible()||!recording)return;
  const {width,height}=surface.getBoundingClientRect();if(!(width>0&&height>0))return;
  const index=movieFrameIndex(time,recording),key=[index,width,height].join(':');
  if(key!==last){layer.innerHTML=scene({...recording.frames[index],presentation:scenePresentation(width,height,true)});last=key;}
  layer.hidden=false;panel.classList.add('movie-responsive');
 }
 function schedule(){
  if(callback||!visible()||!recording||video.paused||video.ended)return;
  const run=(_,metadata)=>{callback=null;draw(metadata?.mediaTime??video.currentTime);schedule();};
  callback=video.requestVideoFrameCallback?{video:true,id:video.requestVideoFrameCallback(run)}:{video:false,id:requestFrame(run)};
 }
 function refresh(){cancel();if(!visible()){layer.hidden=true;return;}draw();schedule();}
 function setExpanded(value){
  enabled=value===true;
  if(!enabled){cancel();layer.hidden=true;panel.classList.remove('movie-responsive');return;}
  if(!recording&&!pending&&!failed){pending=Promise.resolve().then(load).then(result=>{recording=result;refresh();}).catch(()=>{failed=true;layer.hidden=true;panel.classList.remove('movie-responsive');});}
  refresh();
 }
 const events=['play','pause','seeked','loadeddata','ended'];for(const event of events)video.addEventListener(event,refresh);
 doc.addEventListener('visibilitychange',refresh);const resize=observe(refresh);resize.observe(surface);
 return {setExpanded,ready:()=>pending||Promise.resolve(),dispose(){disposed=true;cancel();resize.disconnect();for(const event of events)video.removeEventListener(event,refresh);doc.removeEventListener('visibilitychange',refresh);layer.remove();panel.classList.remove('movie-responsive');}};
}
