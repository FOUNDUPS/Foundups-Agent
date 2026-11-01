import test from 'node:test';
import assert from 'node:assert/strict';
import {scene,scenePresentation,movie} from '../../../../public/eduit/storytime/scene.mjs';

test('expanded window preserves original art scale and centered world coordinates',()=>{
 for(const [width,height]of [[374,600],[752,800],[390,650],[320,500],[800,450]]){
  const frame=scenePresentation(width,height,true),scale=width/960;
  assert.equal(frame.top,frame.bottom);
  assert.ok(Math.abs(frame.height*scale-height)<1e-8);
  assert.ok(Math.abs(frame.top*scale-(height-540*scale)/2)<1e-8);
  for(const [x,y]of [[132,378],[850,302],[35,510]]){
   const screen={x:x*scale,y:(y+frame.top)*scale};
   assert.ok(Math.abs(screen.x/scale-x)<1e-8);
   assert.ok(Math.abs((screen.y-frame.top*scale)/scale-y)<1e-8);
  }
 }
});

test('optional extension retains default scene bytes and never mutates supplied world',()=>{
 for(const time of [0,3.2,9.9,10.8,14]){
  const world=movie(time),before=structuredClone(world);
  assert.equal(scene(world),scene({...world,presentation:scenePresentation(390,650,false)}));
  for(const presentation of [null,{top:NaN,bottom:0},{top:-1,bottom:0},{top:3000,bottom:0}])
   assert.equal(scene(world),scene({...world,presentation}));
  scene({...world,presentation:scenePresentation(390,650,true)});assert.deepEqual(world,before);
 }
});

test('same SVG sky joins lifted footprint and foot shaft reaches true expanded top',()=>{
 const presentation=scenePresentation(390,650,true);
 for(const impact of [.01,.3,1])for(const lift of [0,.7,1]){
  const svg=scene({impact,lift,collapse:impact,presentation,showWords:false});
  assert.equal((svg.match(/<svg /g)||[]).length,1);
  const view=svg.match(/viewBox="0 (-?[\d.]+) 960 ([\d.]+)"/);
  assert.equal(Number(view[1]),-presentation.top);assert.equal(Number(view[2]),presentation.height);
  const foot=svg.match(/data-event="foot" transform="translate\(0,(-?[\d.]+)\)"><path d="M-40 (-?[\d.]+)/);
  assert.ok(Number(foot[1])+Number(foot[2])<=-presentation.top);
  assert.ok(svg.includes('data-presentation="sky"'));
  if(impact===1)assert.ok(svg.includes('data-event="footprint"'));
 }
});

test('expanded foot tip enters at upper edge, descends continuously, and reaches original contact position',()=>{
 const presentation=scenePresentation(390,650,true);
 const footY=(impact,lift=0)=>Number(scene({impact,lift,presentation,showWords:false}).match(/data-event="foot" transform="translate\(0,(-?[\d.]+)\)/)[1]);
 const first=footY(.000001)+178;
 assert.ok(first<-presentation.top);
 assert.ok(first>-presentation.top-13);
 let previous=footY(.000001);
 for(let i=1;i<=100;i++){
  const next=footY(i/100);assert.ok(next>previous);
  assert.ok(next-previous<=(300+presentation.top)/100+.001);previous=next;
 }
 assert.equal(footY(1),110);
 previous=footY(1);
 for(let i=1;i<=100;i++){
  const next=footY(1,i/100);assert.ok(next<previous);
  assert.ok(previous-next<=(440+presentation.top)/100+.001);previous=next;
 }
 assert.ok(footY(1,1)+178<-presentation.top,'entire toe clears the real expanded top after lift');
 for(const appearance of ['mamma','mermaid']){
  const color=appearance==='mermaid'?'#A8DBE7':'#C9E4EC';
  const svg=scene({impact:1,collapse:1,lift:1,presentation,appearance,showWords:false});
  assert.ok(svg.includes(`data-presentation="sky" y="${-presentation.top}" width="960" height="${presentation.top}" fill="${color}"`));
  assert.ok(svg.includes(`data-event="footprint" d="M-40 -180 H690 V75 Q680 110 640 115 L580 115 Q560 145 510 145 H430 Q405 178 350 178 H220 Q190 157 145 145 L55 120 Q-10 100 -40 60 Z" transform="translate(0,110)" fill="${color}"`));
 }
});
