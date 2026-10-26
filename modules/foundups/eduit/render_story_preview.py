"""Render the browser's shared scene as three clips and a 15-second movie.
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
import cairosvg
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / 'modules/communication/youtube_shorts/src'
def load(name):
    spec = importlib.util.spec_from_file_location(name, SRC / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def render(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    author, editor = load('little_shrew_animation'), load('kids_episode')
    with tempfile.TemporaryDirectory(prefix='eduit-svg-') as temp:
        frames = Path(temp) / 'frames'
        subprocess.run(['node', str(Path(__file__).with_name('export_story_frames.mjs')), str(frames)],check=True,timeout=60)
        events=json.loads((frames/'events.json').read_text())
        class Scene:
            def frame(self, seconds):
                svg = (frames / f'{round(seconds * 30):03d}.svg').read_bytes()
                return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg))).convert('RGB')
        for i in range(3):
            author.render_shot(Scene(), i, output / f'b0{i+1}.mp4')
        Scene().frame(3).save(output / 'poster.jpg')
    cues = author.compose_audio(output / 'original-score.wav', stomp=True, events=events)
    # Keep the original early tremor/sniffs; no borrowed song or sampled recordings.
    spec = {'schema_version':1,'duration_seconds':15,'preset':'final','orientation':'landscape',
            'clips':[{'path':f'b0{i+1}.mp4','start':0,'duration':5} for i in range(3)],
            'captions':cues,'captions_in_scene':True,'music':{'path':'original-score.wav','rights_evidence':'Original code-composed score and synthesized foley, no samples or lyrics.'},
            'title':'Little Shrew — Find the Root Pocket','learning_objective':'Match THUMP, SNIFF, CRACK and SQUISH to their visible sound-making events.','activity':'Tap the shrew, then the root.','language':'en','age_band':'3-6'}
    result=editor.render_episode(spec,output/'little-shrew.mp4',base_dir=output)
    result['video_path'] = Path(result['video_path']).name
    result['captions_path'] = Path(result['captions_path']).name
    sources=[ROOT/'public/eduit/storytime'/n for n in ('scene.mjs','rig.mjs','engine.mjs','learning-events.mjs')]
    sources += [Path(__file__), Path(__file__).with_name('export_story_frames.mjs'), SRC/'little_shrew_animation.py', SRC/'kids_episode.py']
    record={'schema':'eduit.story_preview.v1','revision':'sound-languages-9','created_at':datetime.now(timezone.utc).isoformat(),'status':'rendered_unreviewed','duration_seconds':15,'method':'shared_browser_svg_scene','paid_calls':0,'result':result,
            'source_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
            'asset_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()}}
    (output/'provenance.json').write_text(json.dumps(record,indent=2)+'\n')
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',required=True);render(parser.parse_args().output_dir)
