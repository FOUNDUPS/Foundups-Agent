// Stable event IDs; locale text can later vary without moving sound/action timing.
export const events=[
 {id:'step-far',start:.6,end:1.35,kind:'thump',word:'THUMP',x:170,y:65,size:30,gain:.07},
 {id:'step-near',start:2,end:2.8,kind:'thump',word:'THUMP',x:420,y:65,size:42,gain:.11},
 {id:'sniff-wake-1',start:3.1,end:3.65,kind:'sniff',word:'SNIFF',size:34,gain:.10},
 {id:'sniff-wake-2',start:4,end:4.55,kind:'sniff',word:'SNIFF',size:34,gain:.10},
 {id:'sniff-root',start:5.8,end:6.35,kind:'sniff',word:'SNIFF',size:34,gain:.10},
 {id:'step-overhead',start:6.7,end:7.45,kind:'thump',word:'THUMP',x:540,y:65,size:58,gain:.15},
 {id:'crack-left',start:7.6,end:8.25,kind:'crack',word:'CRACK',x:240,y:180,size:36,gain:.10},
 {id:'crack-right',start:8.45,end:9.1,kind:'crack',word:'CRACK',x:540,y:180,size:40,gain:.11},
 {id:'roof-contact',start:9.6,end:10.25,kind:'thump',word:'THUMP',x:420,y:230,size:60,gain:.17},
 {id:'compression',start:10.65,end:11.65,kind:'squish',word:'SQUISH',x:440,y:440,size:48,gain:.12}
];
export const activeEvent=t=>events.find(e=>t>=e.start&&t<e.end);
