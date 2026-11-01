"""Build an EDUIT static deployment with freshly rendered, local media assets."""
import argparse
from pathlib import Path
import shutil
import tempfile
import subprocess
from render_story_preview import ROOT, render
from storytime_site import mount_storytime_root

def build(output, storytime_root=False, rasterizer='cairo'):
    output=Path(output).resolve()
    if output.exists():
        raise FileExistsError(output)
    with tempfile.TemporaryDirectory(prefix='eduit-build-') as scratch:
        media=Path(scratch)/'media'
        if rasterizer=='cairo':
            render(media)
        else:
            render(media,rasterizer=rasterizer)
        shutil.copytree(ROOT/'public/eduit',output)
        # Review tooling belongs to the existing Shorts editor; EDUIT mounts it.
        shutil.copytree(
            ROOT/'modules/communication/youtube_shorts/assets/kids_review',
            output/'review',
        )
        gestures=output/'member/js'
        gestures.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/'public/member/js/gesture-engine.js',gestures/'gesture-engine.js')
        # Standalone PWA assets belong to this module; Mall integration keeps its own worker.
        if storytime_root:
            mount_storytime_root(output)
        # Keep every hashed artifact with its receipt for reproducible review.
        shutil.copytree(media, output/'storytime/assets', dirs_exist_ok=True)
        subprocess.run(['node', str(Path(__file__).with_name('export_movie_presentation.mjs')),
                        str(output/'storytime/assets')], check=True, timeout=30)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',required=True);parser.add_argument('--storytime-root',action='store_true');parser.add_argument('--rasterizer',choices=['cairo','sharp'],default='cairo')
    args=parser.parse_args();build(args.output_dir,args.storytime_root,args.rasterizer)
