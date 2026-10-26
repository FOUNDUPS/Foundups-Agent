import {rig} from './rig.mjs';
const clamp=x=>Math.max(0,Math.min(1,x));
export function movie(t){
 return {t,awake:t>=2,progress:clamp((t-3.2)/2.3),impact:clamp((t-10)/.7),lift:clamp((t-11.5)/1.3),shake:t>.7&&t<1.5};
}
export function scene({t=0,awake=false,progress=0,impact=0,lift=0,shake=false}){
 const p=clamp(progress), k=clamp(impact), l=clamp(lift), crushed=k>=.8?1:0;
 const x=350+410*p, y=346-(p>0&&p<1?3*Math.abs(Math.sin(t*16)):0);
 const tremor=shake?2*Math.sin(t*40):0;
 const cave='M30 430 L30 260 Q30 95 230 100 L610 100 Q725 100 730 230 Q900 200 930 325 L930 430 Z';
 const sleeping=[[75,202,1.12],[290,192,1.2],[120,346,.42],[235,346,.42]].map(([x,y,s])=>`<g transform="translate(${x},${y+Math.sin(t*3)*1.1}) scale(${s})"><use href="#sleepy"/></g>`).join('');
 const hero=`<g transform="translate(${x},${y}) scale(.42) rotate(${awake&&p===0?Math.sin(t*16)*6:p===1?Math.max(0,Math.sin(t*8))*3:0},91,100)"><use href="#${crushed?'surprised':awake?'neutral':'sleepy'}"/></g>`;
 // Side-section of a heavy three-toed foot; impression remains in compacted earth.
 const foot='M-40 -100 H690 V75 Q680 110 640 115 H580 Q560 145 510 145 H430 Q405 178 350 178 H220 Q190 157 145 145 L55 120 Q-10 100 -40 60 Z';
 const ground=k>0?`<rect width="960" height="540" fill="#9C724F" opacity="${crushed}"/><path d="${foot}" transform="translate(0,${-190+300*k})" fill="#9C724F" stroke="#69472F" stroke-width="5" opacity="${crushed}"/><path d="${foot}" transform="translate(0,${-190+300*k-360*l})" fill="#71846D" stroke="#4C5C49" stroke-width="7"/>` : '';
 return `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 960 540" width="960" height="540" role="img" aria-label="Little shrew in its underground root pocket"><defs>${rig}</defs><rect width="960" height="540" fill="#D9B78B"/><g transform="translate(${tremor},0)"><path d="${cave}" fill="#FFF4D9"/><path d="M30 430 H930" stroke="#9C724F" stroke-width="5" opacity="${1-crushed}"/>${sleeping}${ground}<path d="M740 430 V300 Q740 230 820 230 Q930 230 930 340 V430 Z" fill="#FFF4D9" opacity="${crushed}"/><path d="M850 235 Q825 290 834 370 M839 302 Q805 275 797 292 M839 284 Q868 255 877 275" fill="none" stroke="#789468" stroke-width="7" stroke-linecap="round"/>${hero}</g></svg>`;
}
