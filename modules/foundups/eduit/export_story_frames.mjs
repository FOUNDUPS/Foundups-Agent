// Offline video authoring uses the exact browser scene, not a second animation.
import {mkdir,writeFile} from 'node:fs/promises';
import {scene,movie} from '../../../public/eduit/storytime/scene.mjs';
const out=process.argv[2];if(!out)throw Error('Pass a new output directory');
await mkdir(out,{recursive:false});
for(let frame=0;frame<450;frame++)await writeFile(`${out}/${String(frame).padStart(3,'0')}.svg`,scene(movie(frame/30)),{flag:'wx'});
