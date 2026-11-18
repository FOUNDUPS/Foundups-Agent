import test from 'node:test';
import assert from 'node:assert/strict';
import {createMusicPlayer,musicTracks} from '../../../communication/youtube_shorts/assets/kids_review/music-picker.mjs';
function fixture(play){let calls=0,pauses=0;const audio={paused:true,pause(){pauses++;this.paused=true;},play(){calls++;this.paused=false;return play?.()??Promise.resolve();},removeAttribute(name){delete this[name];},load(){}};return {audio,player:createMusicPlayer({audio}),calls:()=>calls,pauses:()=>pauses};}
test('music is opt-in and track selection cannot start sound or authorize arbitrary media',()=>{
 const f=fixture();assert.equal(f.player.status().selected,'off');f.player.sync({active:true,explicit:true});assert.equal(f.calls(),0);
 assert.equal(f.player.setTrack('carefree'),true);f.player.sync({active:true});assert.equal(f.calls(),0);
 const src=f.audio.src;assert.equal(f.player.setTrack('https://untrusted.invalid/music.mp3'),false);assert.equal(f.audio.src,src);
 assert.ok(musicTracks.filter(t=>t.file).every(t=>t.source.startsWith('https://incompetech.com/')));
});
test('only explicit active game starts soft music; pause requires explicit resume',async()=>{
 const f=fixture();f.player.setTrack('wholesome');f.player.sync({active:true,explicit:true});await Promise.resolve();assert.equal(f.calls(),1);assert.equal(f.audio.volume,.12);
 f.player.sync({active:true});assert.equal(f.calls(),1);f.player.sync({active:false});assert.ok(f.audio.paused);
 f.player.sync({active:true});assert.equal(f.calls(),1);f.player.sync({active:true,explicit:true});assert.equal(f.calls(),2);
 f.player.setTrack('off');assert.ok(f.audio.paused);assert.equal(f.audio.src,undefined);
});
test('late old playback promise and policy rejection cannot misreport a changed track',async()=>{
 let finish;const f=fixture(()=>new Promise(resolve=>finish=resolve));f.player.setTrack('carefree');f.player.sync({active:true,explicit:true});
 f.player.setTrack('off');finish();await Promise.resolve();assert.equal(f.player.status().selected,'off');assert.ok(f.audio.paused);assert.equal(f.player.status().message,'Music is off');
 const denied=fixture(()=>Promise.reject(Error('not allowed')));denied.player.setTrack('carefree');denied.player.sync({active:true,explicit:true});await Promise.resolve();assert.equal(denied.player.status().armed,false);assert.match(denied.player.status().message,/Tap Play/);
});
