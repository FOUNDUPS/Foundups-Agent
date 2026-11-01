// Presentation data comes from the existing film recorder, never a second game.
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {replay,replayWorld} from './storytime_replay.mjs';
import {scene} from '../../../public/eduit/storytime/scene.mjs';
import {validateMovieFrames} from '../../../public/eduit/storytime/movie-presentation.mjs';
const root=fileURLToPath(new URL('../../../',import.meta.url));
const assets=resolve(process.argv[2]||'');
if(!process.argv[2])throw Error('Pass existing rendered asset directory');
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const provenance=JSON.parse(await readFile(resolve(assets,'provenance.json'),'utf8'));
const requiredSources=[...['scene.mjs','rig.mjs','engine.mjs','game-world.mjs','learning-events.mjs'].map(n=>'public/eduit/storytime/'+n),...['render_story_preview.py','export_story_frames.mjs','storytime_replay.mjs'].map(n=>'modules/foundups/eduit/'+n),...['little_shrew_animation.py','kids_episode.py'].map(n=>'modules/communication/youtube_shorts/src/'+n)].sort();
const sourceEntries=Object.entries(provenance.source_hashes||{}).map(([p,h])=>[p.replaceAll('\\','/'),h]);
if(provenance.schema!=='eduit.story_preview.v1'||provenance.method!=='deterministic_game_engine_replay'||JSON.stringify(sourceEntries.map(([p])=>p).sort())!==JSON.stringify(requiredSources))throw Error('Incomplete film provenance');
for(const [path,expected]of sourceEntries){
 if(hash(await readFile(resolve(root,path.replaceAll('\\','/'))))!==expected)throw Error('Film source differs: '+path);
}
const video=await readFile(resolve(assets,'little-shrew.mp4'));
if(hash(video)!==provenance.asset_hashes['little-shrew.mp4'])throw Error('Film bytes differ');
const recording=replay();
if(recording.duration!==provenance.duration_seconds||recording.revision!==provenance.revision)throw Error('Film timeline differs');
const frames=recording.states.map(replayWorld);
const data={schema:'eduit.movie_frames.v1',revision:recording.revision,fps:recording.fps,duration:recording.duration,frames};
const validated=validateMovieFrames(data);
// Dropping unused state fields must not change even one original movie frame.
for(let i=0;i<frames.length;i++)if(scene(frames[i])!==scene(validated.frames[i]))throw Error('Frame projection differs: '+i);
const bytes=Buffer.from(JSON.stringify(data));
const sources={};
for(const name of ['scene.mjs','rig.mjs','learning-events.mjs'])sources[name]=hash(await readFile(resolve(root,'public/eduit/storytime',name)));
const binding={schema:'eduit.movie_presentation.v1',revision:recording.revision,fps:recording.fps,duration:recording.duration,frameCount:frames.length,framesSha256:hash(bytes),videoSha256:hash(video),sources};
await writeFile(resolve(assets,'movie-frames.json'),bytes);
await writeFile(resolve(assets,'movie-presentation.json'),JSON.stringify(binding,null,2)+'\n');
console.log(JSON.stringify({frames:frames.length,bytes:bytes.length,canonicalFramesEqual:true,...binding}));
