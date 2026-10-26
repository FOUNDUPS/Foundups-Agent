"""Build an EDUIT static deployment with freshly rendered, local media assets."""
import argparse
from pathlib import Path
import shutil
import tempfile
from render_story_preview import ROOT, render

def build(output):
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
        # Keep every hashed artifact with its receipt for reproducible review.
        shutil.copytree(media, output/'storytime/assets', dirs_exist_ok=True)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',required=True)
    build(parser.parse_args().output_dir)
