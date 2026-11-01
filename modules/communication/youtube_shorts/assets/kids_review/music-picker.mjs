import {mountChoiceWheel} from './choice-wheel.mjs';

export const musicTracks=Object.freeze([
 Object.freeze({id:'off',label:'Off',icon:'🔇'}),
 Object.freeze({id:'carefree',label:'Carefree',icon:'☀️',file:'../storytime/assets/music/carefree.mp3',title:'Carefree',artist:'Kevin MacLeod',source:'https://incompetech.com/music/royalty-free/index.html?isrc=USUAN1400037'}),
 Object.freeze({id:'wholesome',label:'Wholesome',icon:'🌿',file:'../storytime/assets/music/wholesome.mp3',title:'Wholesome',artist:'Kevin MacLeod',source:'https://incompetech.com/music/royalty-free/index.html?isrc=USUAN1900022'})
]);

// Presentation audio only. No physics, learner records, generated music or external streams.
export function createMusicPlayer({audio,onStatus=()=>{}}){
 let selected='off',armed=false,pending=false,epoch=0,message='Music is off';
 audio.loop=true;audio.preload='none';audio.volume=.12;
 function report(text){if(message!==text){message=text;onStatus(text);}}
 function stop(){armed=false;if(pending||!audio.paused){epoch++;pending=false;audio.pause();}report(selected==='off'?'Music is off':'Music paused · press Play game to listen');}
 audio.onerror=()=>{epoch++;pending=false;armed=false;audio.pause();report('Music unavailable · the game still works');};
 return {
  setTrack(id){const track=musicTracks.find(t=>t.id===id);if(!track)return false;
   epoch++;pending=false;audio.pause();armed=false;selected=id;
   if(track.file)audio.src=new URL(track.file,import.meta.url).href;
   else{audio.removeAttribute('src');audio.load();}
   report(id==='off'?'Music is off':'Press Play game to hear '+track.label);return true;
  },
  sync({active=false,explicit=false}={}){
   if(!active||selected==='off'){stop();return;}
   if(explicit)armed=true;
   if(!armed||pending||!audio.paused)return;
   pending=true;const generation=++epoch;
   try{Promise.resolve(audio.play()).then(()=>{if(epoch!==generation)return;pending=false;report(musicTracks.find(t=>t.id===selected).label+' · playing softly');},()=>{
    if(epoch!==generation)return;pending=false;armed=false;report('Tap Play game again to enable music');
   });}catch{pending=false;armed=false;report('Music unavailable · the game still works');}
  },
  stop,status:()=>({selected,armed,pending,playing:!audio.paused,message}),
  destroy(){stop();audio.onerror=null;audio.removeAttribute('src');audio.load();}
 };
}

export function mountMusicPicker({host,video,game,pauseSession,isStoryOpen=()=>false}){
 const doc=host.ownerDocument,win=doc.defaultView,group=doc.createElement('fieldset');group.id='game-music';
 const legend=doc.createElement('legend');legend.textContent='Background music';group.append(legend);host.append(group);
 const note=doc.createElement('p');note.textContent='Pick a tune, then press Play game. Music pauses for the story.';
 const status=doc.createElement('p');status.setAttribute('role','status');status.textContent='Music is off';
 const audio=doc.createElement('audio');audio.hidden=true;group.append(note,audio);
 const player=createMusicPlayer({audio,onStatus:text=>status.textContent=text});
 const wheel=mountChoiceWheel({host:group,id:'music-wheel',label:'Music',choices:musicTracks,selected:'off',
  onInteract:pauseSession,onSelect:id=>{pauseSession();return player.setTrack(id);}});
 group.append(status);
 const credits=doc.createElement('details'),summary=doc.createElement('summary');summary.textContent='Music credits';credits.append(summary);
 for(const track of musicTracks.filter(t=>t.file)){
  const p=doc.createElement('p'),link=doc.createElement('a');link.href=track.source;link.textContent=track.title;link.target='_blank';link.rel='noopener noreferrer';
  const license=doc.createElement('a');license.href='https://creativecommons.org/licenses/by/4.0/';license.textContent='CC BY 4.0';license.target='_blank';license.rel='noopener noreferrer';
  p.append(link,' — Kevin MacLeod (incompetech.com). Licensed under Creative Commons: By Attribution 4.0 License. ',license,'. Full track transcoded to 96 kbps MP3; played quietly on loop.');credits.append(p);
 }
 group.append(credits);
 const active=()=>{const s=game.contentWindow?.storytimeReview?.status();return !!s&&!s.paused&&['playing','celebrating'].includes(s.phase)&&!doc.hidden&&video.paused&&!isStoryOpen();};
 const sync=(explicit=false)=>player.sync({active:active(),explicit});
 const onParentClick=e=>{if(e.target.closest?.('#play,#resume-game,#close'))sync(true);};
 const onGameClick=e=>{if(e.target.closest?.('#start,#retry,#ending button'))sync(true);};let gameDoc=null;
 function bindGame(){gameDoc?.removeEventListener('click',onGameClick);gameDoc=game.contentDocument;gameDoc?.addEventListener('click',onGameClick);}
 doc.addEventListener('click',onParentClick);game.addEventListener('load',bindGame);bindGame();
 const stop=()=>player.stop(),onVisibility=()=>{if(doc.hidden)stop();};doc.addEventListener('visibilitychange',onVisibility);
 win.addEventListener('pagehide',stop);video.addEventListener('play',stop);
 const poll=win.setInterval(()=>sync(),150);
 return {status:player.status,stop,destroy(){win.clearInterval(poll);doc.removeEventListener('click',onParentClick);doc.removeEventListener('visibilitychange',onVisibility);game.removeEventListener('load',bindGame);gameDoc?.removeEventListener('click',onGameClick);win.removeEventListener('pagehide',stop);video.removeEventListener('play',stop);wheel.destroy();player.destroy();group.remove();}};
}
