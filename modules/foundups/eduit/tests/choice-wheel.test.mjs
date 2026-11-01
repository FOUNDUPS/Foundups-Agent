import test from 'node:test';
import assert from 'node:assert/strict';
import {mountChoiceWheel} from '../../../communication/youtube_shorts/assets/kids_review/choice-wheel.mjs';

function fixture({reject=false,reduced=false,selected='mamma'}={}){
 const calls=[],timers=new Map(),frames=[];let timer=0,interactions=0;
 const view=Object.assign(new EventTarget(),{matchMedia:()=>({matches:reduced}),requestAnimationFrame:fn=>frames.push(fn),setTimeout:fn=>{timers.set(++timer,fn);return timer;},clearTimeout:id=>timers.delete(id)});
 const doc={defaultView:view,createElement:()=>new Element()};
 class Element extends EventTarget{
  constructor(){super();this.ownerDocument=doc;this.children=[];this.dataset={};this.attributes=new Map();this.clientWidth=160;this.scrollLeft=0;this.textContent='';}
  append(...nodes){this.children.push(...nodes);nodes.forEach(node=>node.parentElement=this);}
  setAttribute(name,value){this.attributes.set(name,value);}
  getAttribute(name){return this.attributes.get(name);}
  getBoundingClientRect(){return {left:0,width:112};}
  scrollTo(value){this.scrolled=value;}
  focus(){doc.activeElement=this;}
  remove(){this.removed=true;}
 }
 const host=new Element(),wheel=mountChoiceWheel({host,id:'test-wheel',label:'Characters',selected,
  choices:[{id:'mamma',label:'MAMMA'},{id:'mermaid',label:'Mermaid'}],onSelect:id=>{calls.push(id);return !reject;},onInteract:()=>interactions++});
 return {wheel,host,calls,doc,view,timers,frames,interactions:()=>interactions};
}
test('choice is explicit, rejects unknown IDs, and preserves one accessible selected card',()=>{
 const f=fixture();assert.equal(f.calls.length,0);assert.equal(f.wheel.selected(),'mamma');
 assert.equal(f.wheel.select('arbitrary-url',{notify:true}),false);assert.equal(f.calls.length,0);
 f.wheel.buttons[1].dispatchEvent(new Event('click'));
 assert.deepEqual(f.calls,['mermaid']);assert.equal(f.wheel.selected(),'mermaid');
 assert.equal(f.wheel.buttons[0].getAttribute('aria-pressed'),'false');assert.equal(f.wheel.buttons[0].tabIndex,-1);
 assert.equal(f.wheel.buttons[1].getAttribute('aria-pressed'),'true');assert.equal(f.wheel.buttons[1].tabIndex,0);
 const blocked=fixture({reject:true});blocked.wheel.buttons[1].dispatchEvent(new Event('click'));assert.equal(blocked.wheel.selected(),'mamma');
});
test('keyboard selection stays bounded, transfers focus, and announces interaction before selection',()=>{
 const f=fixture(),key=value=>{const event=new Event('keydown',{cancelable:true});event.key=value;f.wheel.element.dispatchEvent(event);return event;};
 assert.equal(key('End').defaultPrevented,true);assert.equal(f.wheel.selected(),'mermaid');assert.equal(f.doc.activeElement,f.wheel.buttons[1]);
 key('ArrowRight');assert.equal(f.wheel.selected(),'mermaid');
 key('Home');assert.equal(f.wheel.selected(),'mamma');assert.equal(f.doc.activeElement,f.wheel.buttons[0]);
 assert.equal(f.interactions(),3);
});
test('reduced motion avoids smooth scrolling and teardown removes interactive effects',()=>{
 const f=fixture({reduced:true});f.wheel.select('mermaid');
 const rail=f.wheel.buttons[0].parentElement;assert.equal(rail.scrolled.behavior,'auto');
 f.wheel.destroy();f.wheel.buttons[0].dispatchEvent(new Event('click'));
 assert.equal(f.wheel.element.removed,true);assert.equal(f.calls.length,0);assert.equal(f.wheel.select('mamma'),false);
});

test('initial selected card centers without motion or selection notification',()=>{
 const f=fixture({selected:'mermaid'}),rail=f.wheel.buttons[0].parentElement;
 f.frames.splice(0).forEach(frame=>frame());
 assert.equal(f.wheel.selected(),'mermaid');assert.equal(rail.scrolled.behavior,'auto');
 rail.dispatchEvent(new Event('scroll'));rail.dispatchEvent(new Event('scrollend'));
 assert.deepEqual(f.calls,[]);
});

test('intermediate programmatic scroll cannot replace a clicked or keyboard-selected choice',()=>{
 const f=fixture(),rail=f.wheel.buttons[0].parentElement;
 // The initial card remains nearest while centering travels toward the new choice.
 rail.getBoundingClientRect=()=>({left:0,width:160});
 f.wheel.buttons[0].getBoundingClientRect=()=>({left:24,width:112});
 f.wheel.buttons[1].getBoundingClientRect=()=>({left:180,width:112});
 rail.dispatchEvent(new Event('wheel'));rail.dispatchEvent(new Event('scroll'));
 const stale=[...f.timers.values()];
 f.wheel.buttons[1].dispatchEvent(new Event('click'));
 stale.forEach(callback=>callback());
 for(let i=0;i<3;i++){rail.dispatchEvent(new Event('scroll'));rail.dispatchEvent(new Event('scrollend'));}
 assert.equal(f.wheel.selected(),'mermaid');assert.deepEqual(f.calls,['mermaid']);
 const home=new Event('keydown',{cancelable:true});home.key='Home';f.wheel.element.dispatchEvent(home);
 f.wheel.buttons[0].getBoundingClientRect=()=>({left:-180,width:112});
 f.wheel.buttons[1].getBoundingClientRect=()=>({left:24,width:112});
 rail.dispatchEvent(new Event('scroll'));rail.dispatchEvent(new Event('scrollend'));
 assert.equal(f.wheel.selected(),'mamma');assert.deepEqual(f.calls,['mermaid','mamma']);
 // A subsequent explicit wheel gesture may change the choice normally.
 rail.dispatchEvent(new Event('wheel'));rail.dispatchEvent(new Event('scrollend'));
 assert.equal(f.wheel.selected(),'mermaid');assert.deepEqual(f.calls,['mermaid','mamma','mermaid']);
});

test('a drag that stops before finger release still commits once after release',()=>{
 const f=fixture(),rail=f.wheel.buttons[0].parentElement;
 rail.getBoundingClientRect=()=>({left:0,width:160});
 f.wheel.buttons[0].getBoundingClientRect=()=>({left:-180,width:112});
 f.wheel.buttons[1].getBoundingClientRect=()=>({left:24,width:112});
 const flush=()=>{const pending=[...f.timers.values()];f.timers.clear();pending.forEach(callback=>callback());};
 rail.dispatchEvent(new Event('pointerdown'));rail.dispatchEvent(new Event('scroll'));flush();rail.dispatchEvent(new Event('scrollend'));
 assert.equal(f.wheel.selected(),'mamma');assert.deepEqual(f.calls,[]);
 f.view.dispatchEvent(new Event('pointerup'));flush();
 assert.equal(f.wheel.selected(),'mermaid');assert.deepEqual(f.calls,['mermaid']);
 rail.dispatchEvent(new Event('scrollend'));assert.deepEqual(f.calls,['mermaid']);
});
