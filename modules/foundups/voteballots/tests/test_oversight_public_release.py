"""Exercise the public release projection against the preserved site."""

import json
from html.parser import HTMLParser
from pathlib import Path
from posixpath import dirname, join, normpath
import subprocess
import sys


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
    assert receipt["files"] == 67
    for name in ("index.html", "sw.js", "overview.css", "overview.js", "accountability.json",
                 "llms.txt", "state-ag-transitions.html", "state-ag-transitions.json", "manifest.webmanifest",
                 "legislative-roadmap.html", "contact.html", "contact.css", "contact.js",
                 "contact-queue.mjs", "contact-roster.json", "states-boundaries.json", "states-location.mjs",
                 "explore.html", "map-data.json", "map.css", "map.js"):
        assert (output / "dist" / name).read_bytes() == (output / "dist/web" / name).read_bytes()

    index = (output / "dist/index.html").read_text("utf-8")
    assert index.count("<h1 ") == 1
    assert 'href="/accountability.json"' in index
    assert 'href="/11-house-first-pwa.html"' in index and 'href="#senate"' in index
    assert 'href="legislative-roadmap"' in index and 'href="contact"' in index
    assert index.index('id="pain"') < index.index('id="solution"') < index.index('id="outcome"') < index.index('id="hub"')
    assert "contact.js" not in index
    assert '<details class="thumb-nav">' in index and "map-diagram" in index
    assert 'href="explore#authority"' in index and 'href="explore#investigation"' in index
    assert len({row["jurisdiction"] for row in json.loads((output / "dist/state-ag-transitions.json").read_text("utf-8"))["rows"]}) == 15

    dist = output / "dist"
    for name in ("contact-queue.mjs", "contact-roster.json"):
        assert (dist / name).read_bytes() == (OVERSIGHT.parent / "web" / name).read_bytes()
    contact = (dist / "contact.html").read_text("utf-8")
    assert 'data-page-section="contact"' in contact and './contact.js' in contact
    roadmap = (dist / "legislative-roadmap.html").read_text("utf-8")
    assert 'data-page-section="legislative-roadmap"' in roadmap
    assert all(f'id="{id_}"' in roadmap for id_ in ("scope-inquiry", "act-on-findings", "decide-referral"))
    explorer = (dist / "explore.html").read_text("utf-8")
    parsed_map = Links()
    parsed_map.feed(explorer)
    nodes = json.loads((dist / "map-data.json").read_text("utf-8"))["nodes"]
    edge_screens = {f"edge-{key}--{target}" for key, node in nodes.items() for target, _ in node.get("choices", [])}
    assert parsed_map.screens == set(nodes) | edge_screens
    assert parsed_map.screens <= {url[1:] for url in parsed_map.targets if url.startswith("#")}
    assert {"congressional-action", "coordination"} == {key for key, _ in nodes["decisions"]["choices"]}
    assert all(nodes[key]["fictional"] is True for key in ("clemency-example", "trading-example", "contracting-example", "clemency-transfer-gap"))
    assert "Fictional record A-02 · Posted transfer" in explorer
    assert nodes["clemency-recipient"]["connection_evidence"]["clemency-transfer-gap"][-1][0] == "Not established"
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
            if target.startswith(("https://", "http://", "mailto:")):
                continue
            if target.startswith("tel:"):
                assert target == "tel:+12022243121", (page, target)
                continue
            path = target.split("#", 1)[0].split("?", 1)[0]
            resolved = normpath(join(dirname(page), path)) if path else page
            local = dist / resolved.lstrip("/")
            assert local.is_file() or (local / "index.html").is_file() or local.with_suffix(".html").is_file(), (page, target)

    data = json.loads((output / "dist/accountability.json").read_text("utf-8"))
    assert "foundup_id" not in data
    assert data["entry_points"]["legislative_roadmap"] == "/legislative-roadmap"
    assert data["entry_points"]["map_records"] == "/map-data.json"
    assert data["entry_points"]["senator_directory"] == "/contact"
    assert data["entry_points"]["transition_data"] == "/state-ag-transitions.json"
    assert 'In our view' in index and 'Todd Blanche' in data["doj_leadership_context"]["verified_fact"]
    for key in ("attorney_general_biography", "prior_defense_court_filing", "federal_criminal_contempt"):
        assert data["source_records"][key] in index


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []
        self.screens = set()

    def handle_starttag(self, tag, attrs):
        self.targets.extend(value for key, value in attrs if key in ("href", "src", "data-worker") and value)
        if tag == "section" and (attributes := dict(attrs)).get("class") == "map-screen":
            assert attributes["id"] not in self.screens
            self.screens.add(attributes["id"])
