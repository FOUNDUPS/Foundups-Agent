"""Render a deterministic playthrough using the browser's actual game mechanics.
Local authoring only; no network, publishing, or runtime admission.
"""
from datetime import datetime, timezone
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import io
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / 'modules/communication/youtube_shorts/src'
def load(name):
    spec = importlib.util.spec_from_file_location(name, SRC / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def render(output, *, rasterizer='cairo'):
    if rasterizer not in ('cairo', 'sharp'):
        raise ValueError('Unknown SVG rasterizer')
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    author, editor = load('little_shrew_animation'), load('kids_episode')
    with tempfile.TemporaryDirectory(prefix='eduit-svg-') as temp:
        frames = Path(temp) / 'frames'
        subprocess.run(['node', str(Path(__file__).with_name('export_story_frames.mjs')), str(frames)] + (['--png'] if rasterizer=='sharp' else []),check=True,timeout=180)
        events=json.loads((frames/'events.json').read_text())
        timeline=json.loads((frames/'timeline.json').read_text())
        duration=timeline['duration']
        class Scene:
            def frame(self, seconds):
                if rasterizer=='sharp':
                    return Image.open(frames / f'{round(seconds * 30):03d}.png').convert('RGB')
                import cairosvg
                svg = (frames / f'{round(seconds * 30):03d}.svg').read_bytes()
                return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg))).convert('RGB')
        for i in range(duration//5):
            author.render_shot(Scene(), i, output / f'b0{i+1}.mp4', duration_seconds=duration)
        Scene().frame(3).save(output / 'poster.jpg')
    (output/'replay-timeline.json').write_text(json.dumps(timeline,indent=2)+'\n',encoding='utf-8')
    # Preserve the live game's original sourceTime offsets independently of film edits.
    original_events=json.loads(subprocess.run(['node','--input-type=module','-e',
        "import {events} from './public/eduit/storytime/learning-events.mjs';console.log(JSON.stringify(events))"],
        cwd=ROOT,check=True,capture_output=True,text=True,timeout=10).stdout)
    author.compose_audio(output/'game-foley.wav',stomp=True,events=original_events)
    cues = author.compose_audio(output / 'original-score.wav', stomp=True, events=events,duration_seconds=duration)
    spec = {'schema_version':1,'duration_seconds':duration,'preset':'final','orientation':'landscape',
            'clips':[{'path':f'b0{i+1}.mp4','start':0,'duration':5} for i in range(duration//5)],
            'captions':cues,'captions_in_scene':True,'music':{'path':'original-score.wav','rights_evidence':'Original code-composed score and synthesized foley, no samples or lyrics.'},
            'title':'Little Shrew — Rescue the Family','learning_objective':'Wake each family member and guide it to the safe root pocket.','activity':'Tap the shrew, then the root.','language':'en','age_band':'3-4'}
    result=editor.render_episode(spec,output/'little-shrew.mp4',base_dir=output,duration_seconds=duration)
    result['video_path'] = Path(result['video_path']).name
    result['captions_path'] = Path(result['captions_path']).name
    sources=[ROOT/'public/eduit/storytime'/n for n in ('scene.mjs','rig.mjs','engine.mjs','game-world.mjs','learning-events.mjs')]
    sources += [Path(__file__), Path(__file__).with_name('export_story_frames.mjs'), Path(__file__).with_name('storytime_replay.mjs'), SRC/'little_shrew_animation.py', SRC/'kids_episode.py']
    record={'schema':'eduit.story_preview.v1','revision':timeline['revision'],'created_at':datetime.now(timezone.utc).isoformat(),'status':'rendered_unreviewed','duration_seconds':duration,'method':'deterministic_game_engine_replay','paid_calls':0,'result':result,
            'source_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
            'asset_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()}}
    (output/'provenance.json').write_text(json.dumps(record,indent=2)+'\n')
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',required=True);parser.add_argument('--rasterizer',choices=['cairo','sharp'],default='cairo');args=parser.parse_args();render(args.output_dir,rasterizer=args.rasterizer)
