export const rig = "<defs xmlns=\"http://www.w3.org/2000/svg\" xmlns:ns1=\"http://www.w3.org/1999/xlink\"><g id=\"body\" stroke=\"#1F1F1F\" stroke-width=\"4\" stroke-linecap=\"round\" stroke-linejoin=\"round\">\n<path d=\"M44 93 Q8 110 14 78\" fill=\"none\" />\n<ellipse cx=\"91\" cy=\"77\" rx=\"58\" ry=\"43\" fill=\"#B58963\" />\n<ellipse cx=\"137\" cy=\"86\" rx=\"24\" ry=\"19\" fill=\"#9C724F\" />\n<path d=\"M154 78 L166 82 L156 91 Z\" fill=\"#F26B7A\" stroke-width=\"2\" />\n<path d=\"M135 81 L112 69 M135 86 L109 86 M135 91 L113 103 M154 81 L176 69 M156 86 L181 86 M155 91 L178 103\" fill=\"none\" stroke-width=\"2\" />\n</g><g id=\"neutral\"><use href=\"#body\" ns1:href=\"#body\" /><circle cx=\"108\" cy=\"59\" r=\"5\" /></g><g id=\"sleepy\"><use href=\"#body\" ns1:href=\"#body\" /><path d=\"M101 60 Q108 66 115 60\" fill=\"none\" stroke=\"#1F1F1F\" stroke-width=\"3\" /></g><g id=\"surprised\"><use href=\"#body\" ns1:href=\"#body\" /><ellipse cx=\"108\" cy=\"58\" rx=\"6\" ry=\"9\" /><circle cx=\"141\" cy=\"100\" r=\"4\" /></g><g id=\"happy\"><use href=\"#body\" ns1:href=\"#body\" /><path d=\"M101 61 Q108 51 115 61 M135 99 Q141 107 148 99\" fill=\"none\" stroke=\"#1F1F1F\" stroke-width=\"3\" /></g><g id=\"front\" stroke=\"#1F1F1F\" stroke-width=\"3\"><ellipse cx=\"91\" cy=\"77\" rx=\"58\" ry=\"43\" fill=\"#B58963\"/><ellipse cx=\"74\" cy=\"57\" rx=\"11\" ry=\"15\" fill=\"#FFF4D9\"/><ellipse cx=\"111\" cy=\"57\" rx=\"11\" ry=\"15\" fill=\"#FFF4D9\"/><ellipse cx=\"75\" cy=\"58\" rx=\"5\" ry=\"9\"/><ellipse cx=\"110\" cy=\"58\" rx=\"5\" ry=\"9\"/><ellipse cx=\"92\" cy=\"86\" rx=\"22\" ry=\"17\" fill=\"#9C724F\"/><path d=\"M84 80 L100 80 L92 88 Z\" fill=\"#F26B7A\"/><circle cx=\"92\" cy=\"102\" r=\"4\"/></g></defs>";

// Original local fantasy artwork. The simulation never consumes these presets.
const mermaidBody = `<g id="body" stroke="#183F52" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
 <path d="M55 91 Q32 70 12 80 L30 99 L10 116 Q39 125 63 104" fill="#4AABA7"/>
 <path d="M49 99 Q76 119 108 97 L131 78 L117 66 Q100 86 86 86 Q64 84 49 99Z" fill="#78CFC0"/>
 <path d="M62 98 Q74 102 82 97 M78 92 Q87 98 94 92" fill="none" stroke="#348C93" stroke-width="2"/>
 <path d="M114 81 Q103 60 112 39 Q130 22 149 37 Q161 55 149 80Z" fill="#514866"/>
 <circle cx="132" cy="56" r="22" fill="#EFC6A2"/>
 <path d="M111 49 Q116 24 140 34 L154 51 Q137 48 132 38 Q125 48 111 49Z" fill="#514866"/>
 <path d="M115 78 Q126 68 139 78 L137 92 L114 92Z" fill="#C8A6DC"/>
 <path d="M116 80 L103 89 M139 80 L153 84" fill="none" stroke="#EFC6A2" stroke-width="8"/>
 <path d="M130 68 Q137 73 142 67" fill="none"/>
</g>`;
export const mermaidRig = `<defs>${mermaidBody}
 <g id="neutral"><use href="#body"/><circle cx="137" cy="55" r="3" fill="#183F52"/></g>
 <g id="sleepy"><use href="#body"/><path d="M132 55 Q137 60 142 55" fill="none" stroke="#183F52" stroke-width="3"/></g>
 <g id="surprised"><use href="#body"/><ellipse cx="137" cy="55" rx="3" ry="5" fill="#183F52"/></g>
 <g id="happy"><use href="#body"/><path d="M132 56 Q137 49 142 56" fill="none" stroke="#183F52" stroke-width="3"/></g>
 <g id="front"><use href="#body"/><circle cx="125" cy="55" r="3" fill="#183F52"/><circle cx="140" cy="55" r="3" fill="#183F52"/></g>
</defs>`;
const original = Object.freeze({id:'mamma',revision:1,label:'MAMMA 🥚',rig,earth:'#69472F',cave:'#FFF4D9',description:'Little shrew in its underground root pocket'});
const mermaid = Object.freeze({id:'mermaid',revision:1,label:'MAMMA Mermaid 🧜',rig:mermaidRig,earth:'#164D68',cave:'#D8F2EF',description:'Fictional MAMMA mermaid family in a blue cave'});
export const appearances = Object.freeze({mamma:original,mermaid});
export function appearanceFor(id){
 return typeof id==='string'&&Object.hasOwn(appearances,id)?appearances[id]:original;
}
