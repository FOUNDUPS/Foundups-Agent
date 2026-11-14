import {movie,scene} from '../storytime/scene.mjs';
const $=id=>document.getElementById(id),video=$('video');
let silent=false,playing=false,time=0,last=0;
video.loop=true;
function clock(t){$('clock').textContent=`${t.toFixed(2)} / 15.00 seconds`;}
function draw(){ $('scene').innerHTML=scene(movie(time));$('scrub').value=time;clock(time); }
video.addEventListener('timeupdate',()=>{if(!silent)clock(video.currentTime);});
video.addEventListener('loadedmetadata',()=>{$('status').textContent=`Rendered review cut loaded · ${video.duration.toFixed(2)} seconds · stomp / crunch / squish`;});
video.addEventListener('error',()=>{$('status').textContent='The rendered video is unavailable here. Use Show silent scene to review the animation.';});
$('loop').onchange=()=>{video.loop=$('loop').checked;};
$('refresh').onclick=()=>{playing=false;video.pause();video.src=`../storytime/assets/little-shrew.mp4?revision=${Date.now()}`;video.load();$('status').textContent='Reloading rendered cut…';$('play').textContent='Play scene';};
$('mode').onclick=()=>{if(!silent)time=video.currentTime||0;silent=!silent;playing=false;video.pause();video.hidden=silent;$('scene').hidden=!silent;$('scene-controls').hidden=!silent;$('mode').textContent=silent?'Show rendered video':'Show silent scene';$('play').textContent='Play scene';if(silent)draw();else{video.currentTime=time;clock(time);}};
$('play').onclick=()=>{if(time>=15)time=0;playing=!playing;$('play').textContent=playing?'Pause scene':'Play scene';};
$('scrub').oninput=()=>{playing=false;time=Number($('scrub').value);$('play').textContent='Play scene';draw();};
function frame(now){const dt=last?(now-last)/1000:0;last=now;if(silent&&playing&&!document.hidden){time+=Math.min(dt,.1);if(time>=15){if($('loop').checked)time=0;else{time=15;playing=false;$('play').textContent='Play scene';}}draw();}requestAnimationFrame(frame);}
requestAnimationFrame(frame);
