"""Build an EDUIT static deployment with freshly rendered, local media assets."""
import argparse
from pathlib import Path
import shutil
import tempfile
from render_story_preview import ROOT, render
from storytime_site import mount_storytime_root

def build(output, storytime_root=False):
    output=Path(output).resolve()
    if output.exists():
        raise FileExistsError(output)
    with tempfile.TemporaryDirectory(prefix='eduit-build-') as scratch:
        media=Path(scratch)/'media'
        render(media)
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
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',required=True);parser.add_argument('--storytime-root',action='store_true')
    args=parser.parse_args();build(args.output_dir,args.storytime_root)
