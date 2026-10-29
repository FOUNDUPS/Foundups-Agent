// Optional storybook presentation. Same concepts/speech scheduler as the film overlay;
// its page clock is deliberately independent of the retained 15-second MP4.
import {StorybookPlayback} from '../storytime/cue-scheduler.mjs';
import {rig} from '../storytime/rig.mjs';
import {createSpeechChannel} from './story-narration.mjs';

export function mountStorybook({dialog,video,narration,beforePlay=()=>{},onFinish=()=>{}}){
 const $=id=>dialog.querySelector('#'+id),cleanup=[];
 const listen=(el,type,fn,options)=>{el.addEventListener(type,fn,options);cleanup.push(()=>el.removeEventListener(type,fn,options));};
 const title=$('story-intro-title'),description=$('story-intro-description'),illustration=dialog.querySelector('.intro-illustration');
 const actions=dialog.querySelector('.intro-actions');
 if(!title||!description||!illustration||!actions)throw new Error('Story dialog contract missing');
 const surface=document.createElement('section');surface.className='storybook-page';
 surface.setAttribute('aria-roledescription','slide');surface.setAttribute('aria-live','polite');
 title.before(surface);surface.append(illustration,title);
 description.hidden=true;
 for(const p of [...dialog.children])if(p.tagName==='P'&&p!==description)p.hidden=true;
 dialog.removeAttribute('aria-describedby');dialog.classList.add('storybook-ready');dialog.lang='en';
 const progress=document.createElement('p');progress.id='storybook-progress';progress.setAttribute('aria-live','polite');
 const notice=document.createElement('p');notice.id='storybook-audio';notice.setAttribute('role','status');notice.hidden=true;
 const nav=document.createElement('nav');nav.className='storybook-navigation';nav.setAttribute('aria-label','Story pages');
 function control(id,text,label){const b=document.createElement('button');b.id=id;b.type='button';b.textContent=text;b.setAttribute('aria-label',label);nav.append(b);return b;}
 const previous=control('storybook-previous','←','Previous story page');
 const autoplay=control('storybook-play','▶ Auto play','Play the story automatically');
 const next=control('storybook-next','→','Next story page');
 actions.before(progress,notice,nav);
 const handoff=document.createElement('button');handoff.id='storybook-watch';handoff.type='button';handoff.textContent='Watch the story';handoff.hidden=true;
 actions.before(handoff);
 let frame=0,lastPage=null,interacted=false,model=null,audioSnapshot=null;
 const trace=[];const debug=new URLSearchParams(location.search).has('timing');
 const voice=createSpeechChannel({volume:()=>video.volume,notice:ok=>{notice.hidden=ok;notice.textContent=ok?'':'Voice unavailable · use the arrows or read along';}});
 function family(sleeping){
  const poses=[[0,0,.7],[122,0,.7],[245,40,.4],[300,40,.4],[355,40,.32]];
  return `<svg viewBox="0 0 420 125" aria-hidden="true"><defs>${rig}</defs>${poses.map(([x,y,s])=>`<g transform="translate(${x},${y}) scale(${s})"><use href="#${sleeping?'sleepy':'neutral'}"/></g>`).join('')}</svg>`;
 }
 function view(page,state){
  if(lastPage!==page.id){
   lastPage=page.id;title.textContent=page.text;title.setAttribute('aria-label',page.spoken_text??page.text);
   if(['family','sleeping'].includes(page.id))illustration.innerHTML=family(page.id==='sleeping');else illustration.textContent=page.picture||'🌿';
  }
  surface.setAttribute('aria-label',`Page ${state.index+1} of ${state.total}`);
  surface.setAttribute('aria-live',state.playing?'off':'polite');surface.classList.toggle('page-fading',state.fading);
  progress.textContent=`${state.index+1} / ${state.total}`;
  previous.disabled=state.index===0;next.disabled=state.index===state.total-1;
  autoplay.textContent=state.playing?'Ⅱ Pause':'▶ Auto play';
  autoplay.setAttribute('aria-label',state.playing?'Pause the story':'Play the story automatically');
  autoplay.setAttribute('aria-pressed',String(state.playing));
  next.classList.toggle('gentle-hint',!interacted&&!state.playing&&!next.disabled);
  handoff.hidden=state.index!==state.total-1;
  if(state.unavailable){notice.hidden=false;notice.textContent='Voice unavailable · use the arrows or read along';}
  else if(state.silent){notice.hidden=false;notice.textContent='Sound is off · read along';}
 }
 model=new StorybookPlayback({speak:voice.speak,cancel:voice.cancel,view,trace:r=>{if(debug){trace.push(r);if(trace.length>300)trace.shift();}}});
 function pause(reason='interaction'){cancelAnimationFrame(frame);frame=0;model.pause(reason);}
 function navigate(delta){interacted=true;pause('navigation');model.select(model.index+delta);}
 function loop(now){if(!dialog.open||document.hidden){pause('not-visible');return;}model.tick(now);if(model.finished){pause('story-complete');onFinish();return;}if(model.playing)frame=requestAnimationFrame(loop);}
 function play(){
  interacted=true;
  if(model.playing){pause('explicit-pause');return;}
  beforePlay();video.pause();narration.stop('storybook');notice.hidden=true;
  audioSnapshot={volume:video.volume,muted:video.muted};
  model.play({audible:!video.muted&&video.volume>0&&narration.status().enabled!==false});
  cancelAnimationFrame(frame);frame=requestAnimationFrame(loop);
 }
 listen(previous,'click',()=>navigate(-1));listen(next,'click',()=>navigate(1));listen(autoplay,'click',play);
 listen(handoff,'click',()=>{pause('watch-handoff');onFinish();});
 listen(dialog,'close',()=>pause('closed'));listen(dialog,'cancel',()=>pause('cancelled'));
 listen(dialog,'focusin',e=>{if(model.playing&&e.target!==autoplay)pause('focus');});
 listen(dialog,'keydown',e=>{
  if(e.altKey||e.ctrlKey||e.metaKey||!['ArrowLeft','ArrowRight'].includes(e.key))return;
  e.preventDefault();navigate(e.key==='ArrowLeft'?-1:1);
 });
 const pointers=new Map();let origin=null,multiple=false;
 listen(surface,'pointerdown',e=>{
  pause('touch');pointers.set(e.pointerId,true);
  if(pointers.size>1){multiple=true;origin=null;return;}
  if(e.isPrimary!==false)origin={id:e.pointerId,x:e.clientX,y:e.clientY};
 });
 listen(surface,'pointerup',e=>{
  const point=origin;const wasMultiple=multiple;pointers.delete(e.pointerId);
  if(!pointers.size){origin=null;multiple=false;}
  if(wasMultiple||!point||point.id!==e.pointerId)return;
  const dx=e.clientX-point.x,dy=e.clientY-point.y;
  if(Math.abs(dx)>=40&&Math.abs(dx)>Math.abs(dy)*1.5)navigate(dx<0?1:-1);
 });
 const abortPointer=e=>{pointers.delete(e.pointerId);origin=null;if(!pointers.size)multiple=false;};
 listen(surface,'pointercancel',abortPointer);listen(surface,'pointerleave',abortPointer);
 listen(document,'visibilitychange',()=>{if(document.hidden)pause('hidden');});
 listen(window,'pagehide',()=>pause('pagehide'));
 listen(video,'volumechange',()=>{if(dialog.open&&model.playing&&audioSnapshot&&(video.volume!==audioSnapshot.volume||video.muted!==audioSnapshot.muted))pause('volume-change');});
 return {
  open(){interacted=false;lastPage=null;notice.hidden=true;pause('opened');model.select(0);},
  pause,
  status:()=>({index:model.index,playing:model.playing,finished:model.finished,englishOnly:true,trace:debug?trace.slice():[]}),
  destroy(){pause('destroy');cleanup.splice(0).forEach(remove=>remove());voice.cancel();}
 };
}
