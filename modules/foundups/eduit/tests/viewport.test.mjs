import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../../../communication/youtube_shorts/assets/kids_review/director.js',import.meta.url),'utf8');
const owner=source.slice(source.indexOf('let lastViewport='),source.indexOf('let focusReturn='));
function fixture(visualViewport){
 const style=new Map(),events={},counts={game:0,video:0};
 const window={innerWidth:390,innerHeight:844,visualViewport,addEventListener:(n,f)=>events[n]=f};
 const document={hidden:false,documentElement:{style:{setProperty:(k,v)=>style.set(k,v)}},addEventListener:(n,f)=>events[n]=f};
 const context={window,document,video:{pause(){counts.video++;}},api:()=>({pause(){counts.game++;}})};
 vm.runInNewContext(owner,context);
 return {context,window,document,style,counts,events};
}
test('visible viewport offset and rotation pause both owners and update fixed-panel bounds',()=>{
 const v={width:390,height:700,offsetLeft:4,offsetTop:32,scale:1,addEventListener(){}};
 const f=fixture(v);assert.equal(f.style.get('--app-top'),'32px');assert.equal(f.style.get('--app-left'),'4px');assert.equal(f.style.get('--app-height'),'700px');assert.equal(f.counts.game,0);
 v.offsetTop=48;f.context.viewport();assert.deepEqual(f.counts,{game:1,video:1});
 v.width=700;v.height=390;f.events.orientationchange();assert.equal(f.style.get('--app-width'),'700px');assert.deepEqual(f.counts,{game:2,video:2});
 f.events.pageshow();assert.equal(f.counts.game,2);v.offsetTop=0;f.events.visibilitychange();assert.equal(f.style.get('--app-top'),'0px');
});
test('missing viewport API and browser zoom retain layout viewport instead of device guessing',()=>{
 const f=fixture(undefined);assert.equal(f.style.get('--app-width'),'390px');assert.equal(f.style.get('--app-height'),'844px');assert.equal(f.style.get('--app-left'),'0px');
 const z=fixture({width:200,height:400,offsetLeft:40,offsetTop:60,scale:2,addEventListener(){}});assert.equal(z.style.get('--app-width'),'390px');assert.equal(z.style.get('--app-top'),'0px');
});
test('visual viewport subscribes to movement as well as resize',()=>{
 const listeners=[];fixture({width:390,height:844,scale:1,addEventListener:(n)=>listeners.push(n)});assert.deepEqual(listeners,['resize','scroll']);
});
