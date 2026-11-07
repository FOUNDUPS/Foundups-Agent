"""Exercise the public release projection against the preserved site."""

import json
from pathlib import Path
import subprocess
import sys


OVERSIGHT = Path(__file__).resolve().parents[1] / "oversight"


def test_public_overlay_preserves_archive_and_non_overlay_bytes(tmp_path):
    output = tmp_path / "release"
    result = subprocess.run(
        [sys.executable, "-B", str(OVERSIGHT / "scripts/build_public_release.py"), "--output", str(output)],
        check=True,
        capture_output=True,
        text=True,
    )
    receipt = json.loads(result.stdout)
    snapshot = json.loads((OVERSIGHT / "source-snapshot.json").read_text("utf-8"))
    assert receipt["baseline_files"] == len(snapshot["files"]) == 155
    assert receipt["files"] == 163
    changed = set()
    for entry in snapshot["files"]:
        name = entry["source_path"]
        if (output / name).read_bytes() != (OVERSIGHT / entry["export_path"]).read_bytes():
            changed.add(name)
    assert changed == {"dist/index.html", "dist/web/index.html", "dist/sw.js", "dist/web/sw.js"}
    for name in ("index.html", "sw.js", "overview.css", "overview.js", "accountability.json", "llms.txt"):
        assert (output / "dist" / name).read_bytes() == (output / "dist/web" / name).read_bytes()

    index = (output / "dist/index.html").read_text("utf-8")
    assert index.count("<h1 ") == 1
    assert 'href="/llms.txt"' in index and 'href="/accountability.json"' in index
    assert 'href="/11-house-first-pwa.html"' in index and 'href="#senate"' in index
    data = json.loads((output / "dist/accountability.json").read_text("utf-8"))
    assert data["foundup_id"] == "voteballots"
    assert data["provenance"]["baseline_inventory"] == snapshot["inventory_sha256"]
    source_ids = data["sources"].keys()
    for statement in data["verified_public_records"] + data["proposed"]:
        assert statement["sources"] and set(statement["sources"]) <= source_ids
