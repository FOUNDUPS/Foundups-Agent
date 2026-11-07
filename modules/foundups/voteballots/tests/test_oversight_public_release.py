"""Exercise the public release projection against the preserved site."""

import json
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import sys
from urllib.parse import urljoin, urlsplit


OVERSIGHT = Path(__file__).resolve().parents[1] / "oversight"


def test_public_release_excludes_archive_operations_and_keeps_staff_routes(tmp_path):
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
    assert receipt["files"] == 43
    for name in ("index.html", "sw.js", "overview.css", "overview.js", "accountability.json",
                 "llms.txt", "state-ag-transitions.html", "state-ag-transitions.json", "manifest.webmanifest"):
        assert (output / "dist" / name).read_bytes() == (output / "dist/web" / name).read_bytes()

    index = (output / "dist/index.html").read_text("utf-8")
    assert index.count("<h1 ") == 1
    assert 'href="/accountability.json"' in index
    assert 'href="/11-house-first-pwa.html"' in index and 'href="#senate"' in index
    assert '<details class="thumb-nav">' in index and "hub-map" in index
    assert len({row["jurisdiction"] for row in json.loads((output / "dist/state-ag-transitions.json").read_text("utf-8"))["rows"]}) == 15

    dist = output / "dist"
    for path in ("openclaw.json", "search.json", "MASTER_BLUEPRINT.html",
                 "skills", "api/openapi.yaml", "web/app.js", "research", "documents.json"):
        assert not (dist / path).exists()
    for html in dist.rglob("*.html"):
        parser = Links()
        content = html.read_text("utf-8")
        parser.feed(content)
        if "<table>" in content:
            assert content.count("<thead>") == content.count("<table>")
            assert '<th scope="col">' in content
        page = "/" + html.relative_to(dist).as_posix()
        for target in parser.targets:
            resolved = urlsplit(urljoin("https://oversight.test" + page, target))
            if resolved.hostname == "oversight.test":
                local = dist / resolved.path.lstrip("/")
                assert local.is_file() or (local / "index.html").is_file(), (page, target)

    data = json.loads((output / "dist/accountability.json").read_text("utf-8"))
    assert "foundup_id" not in data
    assert data["entry_points"]["transition_data"] == "/state-ag-transitions.json"


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        self.targets.extend(value for key, value in attrs if key in ("href", "src", "data-worker") and value)
