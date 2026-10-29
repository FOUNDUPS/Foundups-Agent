import * as artwork from './rig.mjs';
import {activeEvent} from './learning-events.mjs';
const clamp=x=>Math.max(0,Math.min(1,x));
const smooth=x=>{x=clamp(x);return x*x*(3-2*x);};
export const EARTH='#69472F';
// Preschool presentation is independent of tremor amplitude and simulation coordinates.
export const wordPresentation=Object.freeze({minSize:72,maxSize:112,scale:1.15,padding:12});
export function learningWordLayout(label,cue,actors=[]){
 const units=[...label].reduce((sum,ch)=>sum+(/[\u3000-\u9fff]/u.test(ch)?1:.75),0);
 const size=Math.min(wordPresentation.maxSize,Math.max(wordPresentation.minSize,(cue?.size||58)*wordPresentation.scale),936/Math.max(units,1));
 const halfWidth=Math.max(70,units*size/2),padding=wordPresentation.padding;
 const obstacle=actors.filter(a=>a.status!=='lost').map(a=>({left:a.x+8*a.scale-padding,right:a.x+184*a.scale+padding,top:a.y+24*a.scale-padding,bottom:a.y+124*a.scale+padding}));
 // Keep the rescue destination and score clear, too.
 obstacle.push({left:775,right:935,top:230,bottom:435},{left:20,right:220,top:455,bottom:535});
 const referent=actors.find(a=>a.id===cue?.actorId);
 const preferred=[cue?.x??480,cue?.y??480];
 const candidates=[preferred,...(referent?[[referent.x+90*referent.scale,referent.y-18]]:[]),[480,195],[560,195],[350,195],[480,475]];
 const boxes=candidates.map(([x,y])=>{
  x=Math.max(halfWidth+padding,Math.min(960-halfWidth-padding,x));y=Math.max(size+padding,Math.min(530-size*.2,y));
  return {x,y,size,box:{left:x-halfWidth,right:x+halfWidth,top:y-size,bottom:y+size*.2}};
 });
 const area=(a,b)=>Math.max(0,Math.min(a.right,b.right)-Math.max(a.left,b.left))*Math.max(0,Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top));
 let best=boxes[0],overlap=Infinity;
 for(const next of boxes){const total=obstacle.reduce((n,o)=>n+area(next.box,o),0);if(total<overlap){best=next;overlap=total;}if(total===0)break;}
 return {...best,overlap};
}

export function movie(t){
 const cue=activeEvent(t);
 return {t,cue,awake:t>=2.2,progress:smooth((t-3.5)/2.5),impact:clamp((t-9.6)/1.2),lift:clamp((t-11.5)/1.3),shake:cue?.kind==='thump',warning:clamp((t-7.6)/1.5),reaction:clamp((t-8.5)/.8),collapse:clamp((t-9.6)/1.2),turn:smooth((t-12.4)/.8)};
}
export function scene({t=0,awake=false,progress=0,impact=0,lift=0,shake=false,showWords=true,cue=null,soundWord='',warning=awake?1:0,reaction=impact>0?1:0,collapse=impact,turn=lift>.6?smooth((lift-.6)/.4):0,actors=null,rootSway=0,progressiveCracks=false,dust=false,appearance='mamma'}){
 const skin=artwork.appearanceFor?.(appearance);
 const rig=skin?.rig||artwork.rig,earth=skin?.earth||EARTH,caveFill=skin?.cave||'#FFF4D9';
 const p=clamp(progress),k=clamp(impact),l=clamp(lift),c=clamp(collapse),r=clamp(reaction),crushed=c>=1;
 const sniff=cue?.kind==='sniff'?Math.sin(Math.PI*clamp((t-cue.start)/.32)):0;
 const x=350+410*p,y=378-(p>0&&p<1?3*Math.abs(Math.sin(t*16)):0);
 const tremor=shake?(cue?.shakeSize||30)/22*Math.sin(t*40):c>0&&!crushed?2*Math.sin(t*52):0;
 const cave='M30 430 L30 260 Q30 95 230 100 L610 100 Q725 100 730 230 Q900 200 930 325 L930 430 Z';
 const shelves='';
 const family=crushed?'':[[75,215.6,1.12],[290,206,1.2],[120,378,.42],[235,378,.42]].map(([fx,fy,s],i)=>{
  const a=smooth((r-i*.18)*2); // distinct cue responses, not synchronized clones
  const dx=i===2?-18*a:i===3?15*Math.sin(a*Math.PI):8*a;
  const dy=i===2?-4*Math.sin(a*Math.PI):0;
  return `<g data-character="family-${i}" transform="translate(${fx+dx},${fy+dy}) scale(${s})"><use href="#${a>.05?'surprised':'sleepy'}"/></g>`;
 }).join('');
 const side=awake?'neutral':'sleepy';
 const q=clamp(turn),nx=137-45*q,ex=108-34*q;
 // One opaque face: nose/eyes travel continuously from profile to front.
 const face=q>0?`<g stroke="#1F1F1F" stroke-width="3" stroke-linecap="round"><path d="M44 93 Q8 110 14 78" fill="none" opacity="${1-q}"/><ellipse cx="91" cy="77" rx="58" ry="43" fill="#B58963"/><ellipse cx="${ex}" cy="58" rx="${5+6*q}" ry="${5+10*q}" fill="#FFF4D9"/><ellipse cx="${ex}" cy="58" rx="5" ry="${5+4*q}" fill="#1F1F1F"/><g opacity="${q}"><ellipse cx="111" cy="58" rx="11" ry="15" fill="#FFF4D9"/><ellipse cx="111" cy="58" rx="5" ry="9" fill="#1F1F1F"/></g><ellipse cx="${nx}" cy="86" rx="${24-2*q}" ry="${19-2*q}" fill="#9C724F"/><path d="M${154-70*q} 78 L${166-66*q} 82 L${156-64*q} 91 Z" fill="#F26B7A" stroke-width="2"/><path d="M${nx-2} 81 l-23 -12 M${nx-2} 86 h-26 M${nx-2} 91 l-22 12 M${nx+17} 81 l22 -12 M${nx+19} 86 h25 M${nx+18} 91 l23 12" fill="none" stroke-width="2"/><circle cx="${141-49*q}" cy="102" r="${4*q}" fill="#1F1F1F"/></g>`:`<use href="#${side}"/>`;
 const hero=`<g data-character="hero" transform="translate(${x+sniff*6},${y}) scale(.42)">${skin?.id==='mermaid'?`<use href="#${q>.5?'front':side}"/>`:face}${sniff>0?`<path d="M184 68 q12 -7 20 0 M188 88 q14 -7 20 0" fill="none" stroke="#789468" stroke-width="4" opacity="${sniff}"/>`:''}</g>`;
 const gameActors=actors===null?null:actors.filter(a=>a.status!=='safe'&&!crushed).map(a=>`<g data-actor="${a.id}" transform="translate(${a.x+(cue?.actorId===a.id?sniff*6:0)},${a.y}) scale(${a.scale})"><use href="#${a.status==='safe'&&turn>.5?'front':a.awake||r>.2?'surprised':'sleepy'}"/></g>`).join('');
 const cracks=warning>0&&!crushed?`<path data-event="cracks" transform="translate(0,${330*c})" d="M210 72 l-14 -16 20 -19 -8 -17 m8 17 21 -9 8 -13 M490 70 l-12 -17 18 -15 -5 -20 m5 20 18 -8 8 -12" fill="none" stroke="#382417" stroke-width="${2+3*clamp(warning)}" stroke-linecap="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="${progressiveCracks?1-clamp(warning):0}" opacity="${(progressiveCracks?1:clamp(warning))*(1-c)}"/>${progressiveCracks&&warning>.4?`<path data-event="new-cracks" transform="translate(0,${330*c})" opacity="${1-c}" d="M350 76 l-12 -15 17 -15 -8 -20 M620 78 l-14 -18 10 -19" pathLength="1" stroke-dasharray="1" stroke-dashoffset="${1-clamp((warning-.4)/.6)}" fill="none" stroke="#382417" stroke-width="3"/>`:""}`:'';
 const dirt=dust&&!crushed?Array.from({length:7},(_,i)=>{const fall=(t*.4+i*.17)%1;return `<circle data-event="falling-dirt" cx="${210+i*59}" cy="${110+fall*110+330*c}" r="${2+i%3}" fill="${earth}" opacity="${.8*(1-fall)}"/>`;}).join(''):'';
 const roof=c>0?`<path data-event="falling-roof" d="M0 0 H960 V${100+330*c} H0 Z" fill="${earth}"/>`:'';
 const foot='M-40 -180 H690 V75 Q680 110 640 115 L580 115 Q560 145 510 145 H430 Q405 178 350 178 H220 Q190 157 145 145 L55 120 Q-10 100 -40 60 Z';
 const imprint=(crushed||(k>=1&&l>.65))?`<path data-event="footprint" d="${foot}" transform="translate(0,110)" fill="#503625" opacity=".45"/>`:'';
 const dinosaur=k>0?`<g data-event="foot" transform="translate(0,${-190+300*k-440*l})"><path d="${foot}" fill="#71846D" stroke="#4C5C49" stroke-width="7"/><path d="M580 115 L640 115 Q628 97 604 96 Z M430 145 H510 Q490 125 462 128 Z M220 178 H300 Q280 158 250 158 Z" fill="#E9DEBF" stroke="#4C5C49" stroke-width="3"/></g>`:'';
 const label=cue?.word||(['THUMP!','CRACK!','SNIFF!','SQUISH!'].includes(soundWord)?soundWord:'');
 const labelActors=actors??[{x:75,y:215.6,scale:1.12},{x:290,y:206,scale:1.2},{x:120,y:378,scale:.42},{x:235,y:378,scale:.42},{x,y,scale:.42}];
 const placement=learningWordLayout(label,cue,labelActors),fontSize=placement.size,wx=placement.x,wy=placement.y;
 const textAttrs=`x="${wx}" y="${wy}" text-anchor="middle" font-family="DejaVu Sans,Hiragino Kaku Gothic ProN,Yu Gothic,Noto Sans JP,sans-serif" font-weight="bold" font-size="${fontSize}"`;
 // Explicit two-pass text works in browser SVG and Cairo (paint-order is not portable).
 const word=label&&showWords?`<g data-learning="${cue?.id||'game'}"><text ${textAttrs} fill="#FFF9E8" stroke="#173F43" stroke-width="7" stroke-linejoin="round">${label}</text><text ${textAttrs} fill="#FFF9E8" aria-hidden="true">${label}</text></g>`:'';

 return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="${skin?.description||'Little shrew in its underground root pocket'}"><defs>${rig}</defs><rect data-material="earth" width="960" height="540" fill="${earth}"/><g transform="translate(${tremor},0)">${crushed?'':`<path d="${cave}" fill="${caveFill}"/>`}${shelves}${gameActors===null?family:gameActors}${roof}<path data-place="root-pocket" d="M740 430 V300 Q740 230 820 230 Q930 230 930 340 V430 Z" fill="${caveFill}"/>${cracks}${dirt}${imprint}${dinosaur}<path data-place="root" transform="rotate(${rootSway} 850 235)" d="M850 235 Q825 290 834 370 M839 302 Q805 275 797 292 M839 284 Q868 255 877 275" fill="none" stroke="#789468" stroke-width="7" stroke-linecap="round"/>${gameActors===null?hero:actors.filter(a=>a.status==='safe').map(a=>`<g data-survivor="${a.id}" transform="translate(${a.x+(cue?.actorId===a.id?sniff*6:0)},${a.y}) scale(${a.scale})"><use href="#${turn>.5?'front':'neutral'}"/></g>`).join('')}</g>${word}</svg>`;
}
