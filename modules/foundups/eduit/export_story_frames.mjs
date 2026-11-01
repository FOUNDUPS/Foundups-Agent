// Scene owns spatial words. Renderer retains an SRT without duplicate burn-in.
// Offline video authoring uses the exact browser scene, not a second animation.
import {mkdir,writeFile} from 'node:fs/promises';
import {scene} from '../../../public/eduit/storytime/scene.mjs';
import {replay,replayWorld} from './storytime_replay.mjs';
const out=process.argv[2];if(!out)throw Error('Pass a new output directory');
await mkdir(out,{recursive:false});
const recording=replay();
for(let frame=0;frame<recording.frameCount;frame++)await writeFile(`${out}/${String(frame).padStart(3,'0')}.svg`,scene(replayWorld(recording.states[frame])),{flag:'wx'});
const {states,...timeline}=recording;
await writeFile(`${out}/events.json`,JSON.stringify(recording.events));
await writeFile(`${out}/timeline.json`,JSON.stringify({...timeline,final:states.at(-1)}));
