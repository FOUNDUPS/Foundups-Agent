import {rig} from './rig.mjs';
const clamp=x=>Math.max(0,Math.min(1,x));
// Material identity is invariant: roof, ground and compacted chamber are one soil.
export const EARTH='#69472F';
export function movie(t){
 return {t,awake:t>=1.35,progress:clamp((t-3.2)/2.3),impact:clamp((t-10)/.7),lift:clamp((t-11.5)/1.3),shake:t>=1&&t<1.5,warning:clamp((t-2)/1.2),reaction:clamp((t-9.15)/.65),collapse:clamp((t-10)/.7)};
}
export function scene({t=0,awake=false,progress=0,impact=0,lift=0,shake=false,showWords=true,warning=awake?1:0,reaction=impact>0?1:0,collapse=impact}){
 const p=clamp(progress),k=clamp(impact),l=clamp(lift),c=clamp(collapse),r=clamp(reaction),crushed=c>=1;
 const x=350+410*p,y=346-(p>0&&p<1?3*Math.abs(Math.sin(t*16)):0);
 const tremor=shake?2*Math.sin(t*40):c>0&&!crushed?2*Math.sin(t*52):0;
 const cave='M30 430 L30 260 Q30 95 230 100 L610 100 Q725 100 730 230 Q900 200 930 325 L930 430 Z';
 const family=crushed?'':[[75,202,1.12],[290,192,1.2],[120,346,.42],[235,346,.42]].map(([fx,fy,s],i)=>`<g data-character="family-${i}" transform="translate(${fx+r*(i%2?15:9)},${fy+(r? -3*Math.abs(Math.sin(t*15+i)):Math.sin(t*3)*1.1)}) scale(${s})"><use href="#${r>0?'surprised':'sleepy'}"/></g>`).join('');
 const hero=`<g data-character="hero" transform="translate(${x},${y}) scale(.42) rotate(${awake&&p===0?Math.sin(t*16)*6:0},91,100)"><use href="#${crushed&&l>.25?'front':awake?'neutral':'sleepy'}"/></g>`;
 const cracks=warning>0&&!crushed?`<path data-event="cracks" transform="translate(0,${330*c})" d="M210 65 l14 36 -18 24 26 21 m-8 -45 35 12 10 21 M490 60 l-12 40 20 24 -12 27 m-8 -51 -28 15 -8 20 M640 80 l-15 35 15 30" fill="none" stroke="#382417" stroke-width="${2+3*clamp(warning)}" stroke-linecap="round" opacity="${clamp(warning)}"/>`:'';
 // Descending roof occludes the reacting cast; the pocket is outside its sweep.
 const roof=c>0?`<path data-event="falling-roof" d="M0 0 H740 V${100+330*c} H0 Z" fill="${EARTH}"/>`:'';
 // One silhouette defines both the foot and the negative-space impression.
 const foot='M-40 -180 H690 V75 Q680 110 640 115 L580 115 Q560 145 510 145 H430 Q405 178 350 178 H220 Q190 157 145 145 L55 120 Q-10 100 -40 60 Z';
 const imprint=crushed?`<path data-event="footprint" d="${foot}" transform="translate(0,110)" fill="#C9E4EC"/>`:'';
 const dinosaur=k>0?`<g data-event="foot" transform="translate(0,${-190+300*k-440*l})"><path d="${foot}" fill="#71846D" stroke="#4C5C49" stroke-width="7"/><path d="M580 115 L640 115 Q628 97 604 96 Z M430 145 H510 Q490 125 462 128 Z M220 178 H300 Q280 158 250 158 Z" fill="#E9DEBF" stroke="#4C5C49" stroke-width="3"/></g>`:'';
 const word=shake&&showWords?'<text x="480" y="480" text-anchor="middle" font-family="sans-serif" font-weight="bold" font-size="38" fill="#FFF4D9">THUMP!</text>':'';
 return `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Little shrew in its underground root pocket"><defs>${rig}</defs><rect data-material="earth" width="960" height="540" fill="${EARTH}"/><g transform="translate(${tremor},0)">${crushed?'':`<path d="${cave}" fill="#FFF4D9"/>`}${family}${roof}${cracks}${imprint}${dinosaur}<path data-place="root-pocket" d="M740 430 V300 Q740 230 820 230 Q930 230 930 340 V430 Z" fill="#FFF4D9"/><path d="M850 235 Q825 290 834 370 M839 302 Q805 275 797 292 M839 284 Q868 255 877 275" fill="none" stroke="#789468" stroke-width="7" stroke-linecap="round"/>${hero}</g>${word}</svg>`;
}
