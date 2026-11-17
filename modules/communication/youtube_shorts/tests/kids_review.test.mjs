import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('review preserves scrub time across modes and refreshes media without playing',()=>{
  const elements=new Map();
  const document={hidden:false,getElementById(id){
    if(!elements.has(id))elements.set(id,{currentTime:0,checked:true,
      addEventListener(){},pause(){this.paused=true;},load(){this.loaded=true;}});
    return elements.get(id);
  }};
  const source=readFileSync(new URL('../assets/kids_review/review.js',import.meta.url),'utf8').replace(/^import .*;\n/,'');
  vm.runInNewContext(source,{document,requestAnimationFrame(){},movie:t=>t,scene:t=>String(t),Date});
  const get=id=>document.getElementById(id);
  get('video').currentTime=3;
  get('mode').onclick();
  assert.equal(get('scene').innerHTML,'3');
  get('scrub').value='10.5';get('scrub').oninput();
  get('mode').onclick();
  assert.equal(get('video').currentTime,10.5);
  assert.equal(get('video').hidden,false);
  get('refresh').onclick();
  assert.match(get('video').src,/little-shrew\.mp4\?revision=\d+/);
  assert.equal(get('video').paused,true);assert.equal(get('video').loaded,true);
});
