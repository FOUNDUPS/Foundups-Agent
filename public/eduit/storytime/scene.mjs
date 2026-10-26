import {rig} from './rig.mjs';
import {activeEvent} from './learning-events.mjs';
const clamp=x=>Math.max(0,Math.min(1,x));
const smooth=x=>{x=clamp(x);return x*x*(3-2*x);};
export const EARTH='#69472F';
export function movie(t){
 const cue=activeEvent(t);
 return {t,cue,awake:t>=2.2,progress:smooth((t-3.5)/2.5),impact:clamp((t-9.6)/1.2),lift:clamp((t-11.5)/1.3),shake:cue?.kind==='thump',warning:clamp((t-7.6)/1.5),reaction:clamp((t-8.5)/.8),collapse:clamp((t-9.6)/1.2),turn:smooth((t-12.4)/.8)};
}
export function scene({t=0,awake=false,progress=0,impact=0,lift=0,shake=false,showWords=true,cue=null,soundWord='',warning=awake?1:0,reaction=impact>0?1:0,collapse=impact,turn=lift>.6?smooth((lift-.6)/.4):0,actors=null}){
 const p=clamp(progress),k=clamp(impact),l=clamp(lift),c=clamp(collapse),r=clamp(reaction),crushed=c>=1;
 const sniff=cue?.kind==='sniff'?Math.sin(Math.PI*clamp((t-cue.start)/.32)):0;
 const x=350+410*p,y=378-(p>0&&p<1?3*Math.abs(Math.sin(t*16)):0);
 const tremor=shake?(cue?.size||30)/22*Math.sin(t*40):c>0&&!crushed?2*Math.sin(t*52):0;
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
 const hero=`<g data-character="hero" transform="translate(${x+sniff*6},${y}) scale(.42)">${face}${sniff>0?`<path d="M184 68 q12 -7 20 0 M188 88 q14 -7 20 0" fill="none" stroke="#789468" stroke-width="4" opacity="${sniff}"/>`:''}</g>`;
 const gameActors=actors===null?null:actors.filter(a=>a.status!=='safe'&&!crushed).map(a=>`<g data-actor="${a.id}" transform="translate(${a.x+(cue?.actorId===a.id?sniff*6:0)},${a.y}) scale(${a.scale})"><use href="#${a.status==='safe'&&turn>.5?'front':a.awake||r>.2?'surprised':'sleepy'}"/></g>`).join('');
 const cracks=warning>0&&!crushed?`<path data-event="cracks" transform="translate(0,${330*c})" d="M210 65 l14 36 -18 24 26 21 m-8 -45 35 12 10 21 M490 60 l-12 40 20 24 -12 27 m-8 -51 -28 15 -8 20" fill="none" stroke="#382417" stroke-width="${2+3*clamp(warning)}" stroke-linecap="round" opacity="${clamp(warning)* (1-c)}"/>`:'';
 const roof=c>0?`<path data-event="falling-roof" d="M0 0 H740 V${100+330*c} H0 Z" fill="${EARTH}"/>`:'';
 const foot='M-40 -180 H690 V75 Q680 110 640 115 L580 115 Q560 145 510 145 H430 Q405 178 350 178 H220 Q190 157 145 145 L55 120 Q-10 100 -40 60 Z';
 const imprint=crushed?`<path data-event="footprint" d="${foot}" transform="translate(0,110)" fill="#C9E4EC"/>`:'';
 const dinosaur=k>0?`<g data-event="foot" transform="translate(0,${-190+300*k-440*l})"><path d="${foot}" fill="#71846D" stroke="#4C5C49" stroke-width="7"/><path d="M580 115 L640 115 Q628 97 604 96 Z M430 145 H510 Q490 125 462 128 Z M220 178 H300 Q280 158 250 158 Z" fill="#E9DEBF" stroke="#4C5C49" stroke-width="3"/></g>`:'';
 const label=cue?.word||(['THUMP!','CRACK!','SNIFF!','SQUISH!'].includes(soundWord)?soundWord:'');
 const wx=cue?.x??(cue?.kind==='sniff'?Math.min(875,x+100):480),wy=cue?.y??(cue?.kind==='sniff'?y+75:480);
 const word=label&&showWords?`<text data-learning="${cue?.id||'game'}" x="${wx}" y="${wy}" text-anchor="middle" font-family="DejaVu Sans,Hiragino Kaku Gothic ProN,Yu Gothic,Noto Sans JP,sans-serif" font-weight="bold" font-size="${cue?.size||38}" fill="${cue?.kind==='crack'?'#382417':'#F8DD79'}" stroke="${cue?.kind==='crack'?'#FFF4D9':'#382417'}" stroke-width="0.7">${label}</text>`:'';
 return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Little shrew in its underground root pocket"><defs>${rig}</defs><rect data-material="earth" width="960" height="540" fill="${EARTH}"/><g transform="translate(${tremor},0)">${crushed?'':`<path d="${cave}" fill="#FFF4D9"/>`}<path data-place="root-pocket" d="M740 430 V300 Q740 230 820 230 Q930 230 930 340 V430 Z" fill="#FFF4D9"/>${shelves}${gameActors===null?family:gameActors}${roof}${cracks}${imprint}${dinosaur}<path d="M850 235 Q825 290 834 370 M839 302 Q805 275 797 292 M839 284 Q868 255 877 275" fill="none" stroke="#789468" stroke-width="7" stroke-linecap="round"/>${gameActors===null?hero:actors.filter(a=>a.status==='safe').map(a=>`<g data-survivor="${a.id}" transform="translate(${a.x+(cue?.actorId===a.id?sniff*6:0)},${a.y}) scale(${a.scale})"><use href="#${turn>.5?'front':'neutral'}"/></g>`).join('')}</g>${word}</svg>`;
}
