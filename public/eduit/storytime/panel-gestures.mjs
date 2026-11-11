// Episode adapter: reuse the Mall gesture owner, plus iOS WebKit gesture events.
export function bindPanelGestures(el,{expand,collapse},owner=globalThis.gestureZone){
 const shared=owner?.(el,{onPinchOut:expand,onPinchIn:collapse});
 let touching=false,blockedUntil=0,fired=false;
 const block=()=>{blockedUntil=Date.now()+350;};
 const touchStart=e=>{if(e.touches.length>=2){touching=true;block();if(e.cancelable)e.preventDefault();}};
 const touchEnd=e=>{if(touching){block();if(!e.touches.length)touching=false;}};
 const start=e=>{fired=false;touching=true;block();if(e.cancelable)e.preventDefault();};
 const change=e=>{if(e.cancelable)e.preventDefault();if(fired)return;if(e.scale>1.15){fired=true;expand();}else if(e.scale<.85){fired=true;collapse();}};
 const end=()=>{touching=false;fired=false;block();};
 const listeners=[['touchstart',touchStart],['touchend',touchEnd],['touchcancel',end],['gesturestart',start],['gesturechange',change],['gestureend',end]];
 listeners.forEach(([name,fn])=>el.addEventListener(name,fn,{passive:false}));
 return {isPinching:()=>touching||Date.now()<blockedUntil,destroy(){shared?.destroy();listeners.forEach(([name,fn])=>el.removeEventListener(name,fn));}};
}
