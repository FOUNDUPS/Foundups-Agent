// Scene owns spatial words. Renderer retains an SRT without duplicate burn-in.
// Offline video authoring uses the exact browser scene, not a second animation.
import {mkdir,writeFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {scene} from '../../../public/eduit/storytime/scene.mjs';
import {replay,replayWorld} from './storytime_replay.mjs';
const out=process.argv[2];if(!out)throw Error('Pass a new output directory');
await mkdir(out,{recursive:false});
const recording=replay();
// Optional local rasterizer uses the same SVG scene, not another animation.
const sharp=process.argv[3]==='--png'?createRequire(import.meta.url)('sharp'):null;
for(let frame=0;frame<recording.frameCount;frame++){
 const name=`${out}/${String(frame).padStart(3,'0')}`,svg=scene(replayWorld(recording.states[frame]));
 await writeFile(name+'.svg',svg,{flag:'wx'});
 if(sharp)await sharp(Buffer.from(svg)).flatten({background:'#69472f'}).png().toFile(name+'.png');
}
const {states,...timeline}=recording;
await writeFile(`${out}/events.json`,JSON.stringify(recording.events));
await writeFile(`${out}/timeline.json`,JSON.stringify({...timeline,final:states.at(-1)}));
