"""Project the Shorts-owned viewer into a standalone Storytime site root."""
from pathlib import Path

def mount_storytime_root(output):
    output=Path(output)
    source=(output/'review/director.html').read_text()
    source=source.replace('href="director.css"','href="review/director.css"').replace('src="director.js"','src="review/director.js"')
    source=source.replace('href="../','href="').replace('src="../','src="')
    (output/'index.html').write_text(source)
