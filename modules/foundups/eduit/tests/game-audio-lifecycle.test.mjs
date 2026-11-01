// Execute the actual controller's audio/reset owners; fake media is not acoustic proof.
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
import {initial,advance} from '../../../../public/eduit/storytime/engine.mjs';
import {foleyVolume} from '../../../../public/eduit/storytime/game-world.mjs';
const source=readFileSync(new URL('../../../../public/eduit/storytime/game.js',import.meta.url),'utf8');
const audioOwner=source.slice(source.indexOf('function resetCueAudio()'),source.indexOf('const embedded='));
const actionOwner=source.split(/\r?\n/).find(line=>line.startsWith('function act(e)'));
const reviewOwner=source.slice(source.indexOf('window.storytimeReview='),source.indexOf('// Reuse the Mall gesture owner'));
assert.ok(audioOwner.startsWith('function resetCueAudio()')&&actionOwner&&reviewOwner.startsWith('window.storytimeReview='),'controller owner extraction must remain explicit');
const sniff={id:'sniff-test',kind:'sniff',sourceTime:3.1,sourceDuration:.55};
const squish={id:'game-squish',kind:'squish',sourceTime:10.65,sourceDuration:1};
function fixture(){
 const pending=[],plays=[];
 const soundtrack={currentTime:0,volume:.8,paused:true,pause(){this.paused=true;},play(){this.paused=false;plays.push({time:this.currentTime,volume:this.volume});return new Promise(resolve=>pending.push(resolve));}};
 const context=vm.createContext({soundtrack,initial,advance,foleyVolume,state:advance(initial(),'start'),paused:false,audioEnabled:true,lastCue:null,activeAudioCue:null,playedVictory:false,ctx:null,panelGestures:null,currentCue:null,window:{},locale:'en',appearance:'mamma',expandedPresentation:false,console});
 vm.runInContext(audioOwner+'\n'+actionOwner+'\nfunction draw(){cueAudio(currentCue);}\n'+reviewOwner,context);
 return {context,soundtrack,plays,run:code=>vm.runInContext(code,context),async settle(){pending.splice(0).forEach(resolve=>resolve());await Promise.resolve();await Promise.resolve();},oldSegment(){context.activeAudioCue=squish;context.lastCue=squish.id;soundtrack.currentTime=10.8;soundtrack.paused=false;}};
}
test('idle audio unlock stays silent and pauses after its media promise',async()=>{
 const f=fixture();f.run('cueAudio(null)');assert.equal(f.plays.length,0);
 f.run('enableAudio()');assert.equal(f.plays.length,1);assert.equal(f.plays[0].volume,0);
 await f.settle();assert.equal(f.soundtrack.paused,true);assert.equal(f.soundtrack.volume,0);
});
test('visual sniff ending does not truncate its active source segment',()=>{
 const f=fixture();f.context.currentCue=sniff;f.run('cueAudio(currentCue)');assert.equal(f.soundtrack.currentTime,3.1);assert.equal(f.soundtrack.volume,.8);
 f.soundtrack.currentTime=3.35;f.context.currentCue=null;f.run('cueAudio(null)');assert.equal(f.soundtrack.paused,false);assert.equal(f.context.activeAudioCue.id,sniff.id);
 f.soundtrack.currentTime=sniff.sourceTime+sniff.sourceDuration;f.run('cueAudio(null)');assert.equal(f.soundtrack.paused,true);assert.equal(f.context.activeAudioCue,null);
});
test('retry at an active squish clears the prior round before any unlock plays',async()=>{
 const f=fixture();f.oldSegment();f.context.state={...initial(),phase:'celebrating',outcome:'rescued',elapsed:22};
 f.run('act("retry")');assert.equal(f.context.activeAudioCue,null);assert.equal(f.context.lastCue,null);assert.equal(f.context.state.elapsed,0);assert.equal(f.soundtrack.currentTime,0);
 assert.ok(f.plays.every(p=>p.time===0&&p.volume===0),'new-round unlock cannot play the old offset audibly');
 await f.settle();assert.equal(f.soundtrack.paused,true);assert.equal(f.soundtrack.volume,0);
});
test('review reset, practice and resume clear retained audio and tolerate late unlock callbacks',async()=>{
 for(const action of ['window.storytimeReview.reset()','window.storytimeReview.setPractice(true)','window.storytimeReview.play()']){
  const f=fixture();f.oldSegment();f.run('enableAudio()');f.run(action);
  assert.equal(f.context.activeAudioCue,null,action);assert.equal(f.context.lastCue,null,action);assert.equal(f.soundtrack.currentTime,0,action);
  await f.settle();assert.equal(f.soundtrack.paused,true,action);assert.equal(f.soundtrack.volume,0,action);
 }
});
test('late unlock cannot stop a new valid cue, while explicit pause stops it',async()=>{
 const f=fixture();f.run('enableAudio()');f.context.currentCue=sniff;f.run('cueAudio(currentCue)');await f.settle();
 assert.equal(f.soundtrack.paused,false);assert.equal(f.soundtrack.volume,.8);assert.equal(f.context.activeAudioCue.id,sniff.id);
 f.run('window.storytimeReview.pause()');assert.equal(f.soundtrack.paused,true);
 f.run('cueAudio(currentCue)');assert.equal(f.soundtrack.paused,true,'paused drawing must not restart audio');
});
