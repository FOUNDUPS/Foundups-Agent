// Stable event IDs; locale text can later vary without moving sound/action timing.
export const events=[
 {id:'step-far',start:.6,end:1.35,kind:'thump',word:'THUMP',x:170,y:65,size:48,shakeSize:30,gain:.07},
 {id:'step-near',start:2,end:2.8,kind:'thump',word:'THUMP',x:420,y:65,size:60,shakeSize:42,gain:.11},
 {id:'sniff-wake-1',start:3.1,end:3.65,kind:'sniff',word:'SNIFF',size:58,gain:.10},
 {id:'sniff-wake-2',start:4,end:4.55,kind:'sniff',word:'SNIFF',size:58,gain:.10},
 {id:'sniff-root',start:5.8,end:6.35,kind:'sniff',word:'SNIFF',size:58,gain:.10},
 {id:'step-overhead',start:6.7,end:7.45,kind:'thump',word:'THUMP',x:540,y:65,size:78,shakeSize:58,gain:.15},
 {id:'crack-left',start:7.6,end:8.25,kind:'crack',word:'CRACK',x:240,y:180,size:62,gain:.10},
 {id:'crack-right',start:8.45,end:9.1,kind:'crack',word:'CRACK',x:540,y:180,size:66,gain:.11},
 {id:'roof-contact',start:9.6,end:10.25,kind:'thump',word:'THUMP',x:420,y:230,size:80,shakeSize:60,gain:.17},
 {id:'roof-crunch',start:10.3,end:10.6,kind:'crunch',word:'CRUNCH',x:440,y:330,size:66,gain:.11},
 {id:'compression',start:10.65,end:11.65,kind:'squish',word:'SQUISH',x:440,y:440,size:68,gain:.12}
];
export const activeEvent=t=>events.find(e=>t>=e.start&&t<e.end);

// Authored display-word variants. Foley is shared, not translated spoken narration.
export const locales={
 en:{label:'English',flag:'🇬🇧',thump:'THUMP',sniff:'SNIFF',crack:'CRACK',crunch:'CRUNCH',squish:'SQUISH',over:'Game over',again:'Play again'},
 ja:{label:'日本語',flag:'🇯🇵',thump:'ドン',sniff:'クンクン',crack:'パキッ',crunch:'バリッ',squish:'グシャッ',over:'おしまい',again:'もういちど'},
 pt:{label:'Português',flag:'🇵🇹',thump:'TUM',sniff:'SNIF',crack:'CRAC',crunch:'CREC',squish:'CHOF',over:'Fim de jogo',again:'Jogar de novo'},
 es:{label:'Español',flag:'🇪🇸',thump:'PUM',sniff:'SNIF',crack:'CRAC',crunch:'CRUJIDO',squish:'CHOF',over:'Fin del juego',again:'Jugar de nuevo'}
};
export const normalizeLocale=value=>Object.hasOwn(locales,value)?value:'en';
export function localizeEvent(cue,locale){return cue?{...cue,word:locales[normalizeLocale(locale)][cue.kind]||cue.word}:cue;}
