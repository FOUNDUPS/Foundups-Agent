// Cosmetic choices only. Native horizontal scrolling owns touch/mouse gestures.
export function mountChoiceWheel({host,id,label,choices,selected,onSelect=()=>true,onInteract=()=>{},renderChoice}={}){
 if(!host||!Array.isArray(choices)||!choices.length||new Set(choices.map(c=>c.id)).size!==choices.length)throw new TypeError('Invalid choice wheel');
 const doc=host.ownerDocument,view=doc.defaultView,items=choices.map(c=>({...c})),cleanups=[];
 const element=doc.createElement('div');element.id=id;element.className='choice-wheel';element.setAttribute('role','group');element.setAttribute('aria-label',label);
 const heading=doc.createElement('p');heading.className='choice-label';heading.textContent=label;
 const controls=doc.createElement('div');controls.className='choice-controls';
 const previous=doc.createElement('button'),next=doc.createElement('button');
 for(const [button,text,name]of [[previous,'←','Previous '+label.toLowerCase()],[next,'→','Next '+label.toLowerCase()]]){button.type='button';button.textContent=text;button.setAttribute('aria-label',name);}
 const rail=doc.createElement('div');rail.className='choice-rail';
 const status=doc.createElement('p');status.className='choice-status';status.setAttribute('role','status');status.setAttribute('aria-live','polite');
 const buttons=items.map(item=>{
  const button=doc.createElement('button');button.type='button';button.className='choice-card';button.dataset.choice=item.id;button.setAttribute('aria-pressed','false');
  if(renderChoice)renderChoice(item,button);
  else if(item.icon){const icon=doc.createElement('span');icon.className='choice-picture';icon.textContent=item.icon;icon.setAttribute('aria-hidden','true');button.append(icon);}
  const text=doc.createElement('span');text.textContent=item.label;button.append(text);rail.append(button);return button;
 });
 controls.append(previous,rail,next);element.append(heading,controls,status);host.append(element);
 let current=null,timer=0,disposed=false,scrollIntent=false,pointerDown=false,centering=false;
 const listen=(target,name,handler)=>{target.addEventListener(name,handler);cleanups.push(()=>target.removeEventListener(name,handler));};
 function center(index,{initial=false}={}){
  scrollIntent=false;centering=true;view.clearTimeout(timer);
  const card=buttons[index].getBoundingClientRect(),bounds=rail.getBoundingClientRect();
  if(!bounds.width){centering=false;return;}
  rail.scrollTo({left:rail.scrollLeft+card.left+card.width/2-bounds.left-rail.clientWidth/2,
   behavior:initial||view.matchMedia?.('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
 }
 function select(value,{notify=false,scroll=true}={}){
  const index=items.findIndex(item=>item.id===value);
  if(disposed||index<0)return false;
  if(notify&&value!==current&&onSelect(value)===false)return false;
  current=value;
  buttons.forEach((button,i)=>{button.setAttribute('aria-pressed',String(i===index));button.tabIndex=i===index?0:-1;});
  previous.disabled=index===0;next.disabled=index===items.length-1;
  const message='Selected: '+items[index].label;if(status.textContent!==message)status.textContent=message;
  if(scroll)center(index);return true;
 }
 function move(delta){const index=Math.max(0,Math.min(items.length-1,items.findIndex(item=>item.id===current)+delta));if(select(items[index].id,{notify:true}))buttons[index].focus({preventScroll:true});}
 function settle(){
  view.clearTimeout(timer);if(disposed||!rail.clientWidth||pointerDown)return;
  // Click/key/API centering must never reinterpret intermediate animation frames.
  if(centering){centering=false;return;}
  if(!scrollIntent)return;
  scrollIntent=false;
  const bounds=rail.getBoundingClientRect(),middle=bounds.left+rail.clientWidth/2;
  const index=buttons.reduce((best,button,i)=>{
   const distance=b=>{const r=b.getBoundingClientRect();return Math.abs(r.left+r.width/2-middle);};
   return distance(button)<distance(buttons[best])?i:best;
  },0);
  select(items[index].id,{notify:true,scroll:false});
 }
 buttons.forEach((button,index)=>listen(button,'click',()=>select(items[index].id,{notify:true})));
 listen(previous,'click',()=>move(-1));listen(next,'click',()=>move(1));
 listen(element,'pointerdown',onInteract);listen(element,'focusin',onInteract);
 listen(rail,'pointerdown',()=>{centering=false;scrollIntent=true;pointerDown=true;});
 function releasePointer(){pointerDown=false;if(scrollIntent){view.clearTimeout(timer);timer=view.setTimeout(settle,150);}}
 listen(view,'pointerup',releasePointer);listen(view,'pointercancel',releasePointer);
 listen(rail,'wheel',()=>{onInteract();centering=false;scrollIntent=true;});
 listen(element,'keydown',event=>{
  onInteract();if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
  event.preventDefault();
  if(event.key==='Home'||event.key==='End'){const index=event.key==='Home'?0:items.length-1;if(select(items[index].id,{notify:true}))buttons[index].focus({preventScroll:true});}
  else move(event.key==='ArrowLeft'?-1:1);
 });
 listen(rail,'scroll',()=>{view.clearTimeout(timer);timer=view.setTimeout(settle,150);});listen(rail,'scrollend',settle);
 select(items.some(c=>c.id===selected)?selected:items[0].id,{scroll:false});
 if(view.requestAnimationFrame)view.requestAnimationFrame(()=>{if(!disposed)center(items.findIndex(item=>item.id===current),{initial:true});});
 return {element,buttons,select,selected:()=>current,destroy(){disposed=true;view.clearTimeout(timer);cleanups.splice(0).forEach(remove=>remove());element.remove();}};
}
