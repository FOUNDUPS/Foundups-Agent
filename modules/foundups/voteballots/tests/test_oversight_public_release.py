"""Exercise the public release projection against the preserved site."""

import importlib.util
import json

import pytest
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
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Release build failed:\n{result.stdout}\n{result.stderr}"
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
    assert 'href="legislative-roadmap"' in index and 'href="./contact"' in index
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
    # Direct node navigation replaces interstitial links; legacy fragment screens remain.
    assert set(nodes) <= {url[1:] for url in parsed_map.targets if url.startswith("#")}
    assert not any(url.startswith("#edge-") for url in parsed_map.targets)
    assert "Why this connection?" not in explorer and ">Requirements</a>" not in explorer
    assert 'class="map-connector conditional"' in explorer
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
    assert "This is the project's assessment, not a finding of misconduct." in index
    assert 'Todd Blanche' in data["doj_leadership_context"]["verified_fact"]
    entries = ('href="https://vote.foundups.com/"', 'href="/templates/appendix-a-house-rules"',
               'href="/templates/staffing-and-recruitment-plan"', 'href="explore#investigation"')
    assert [index.index(value) for value in entries] == sorted(index.index(value) for value in entries)
    assert all(f'<details id="{key}">' in index for key in ("pain", "solution", "outcome"))
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


def load_public_script(name, monkeypatch):
    monkeypatch.syspath_prepend(str(OVERSIGHT / "scripts"))
    spec = importlib.util.spec_from_file_location(f"oversight_{name}", OVERSIGHT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def navigation_fixture():
    """Small deterministic renderer fixture; the release test uses the real graph."""
    titles = {
        "overview": "Oversight", "house": "House", "senate": "Senate",
        "review": "Evidence and legal review", "follow-money": "Follow the money",
        "test-evidence": "Test the evidence", "witnesses": "Witness cooperation and immunity",
        "decisions": "Authorized decisions", "congressional-action": "Congressional action",
        "coordination": "Independent state action", "authority": "Authority map",
        "investigation": "Investigation map", "lessons": "Lessons and failure points",
    }
    nodes = {key: {"title": title, "summary": f"Fixture: {title}.",
                   "parent": None if key == "overview" else "overview", "choices": []}
             for key, title in titles.items()}
    edges = (("overview", "house"), ("overview", "senate"),
             ("house", "review"), ("senate", "review"),
             ("review", "follow-money"), ("review", "test-evidence"), ("review", "witnesses"),
             ("follow-money", "decisions"), ("test-evidence", "decisions"), ("witnesses", "decisions"),
             ("decisions", "congressional-action"), ("decisions", "coordination"),
             ("overview", "authority"), ("overview", "investigation"), ("overview", "lessons"))
    for origin, target in edges:
        nodes[origin]["choices"].append([target, f"Required evidence: {origin} to {target}."])
    return nodes


@pytest.mark.parametrize("prefix", ["", "explore"])
def test_diagram_uses_only_direct_node_links_and_decorative_lines(monkeypatch, prefix):
    renderer = load_public_script("build_interactive_map", monkeypatch)
    html = renderer.diagram(navigation_fixture(), prefix)
    parsed = Links()
    parsed.feed(html)
    expected = ("overview", "house", "senate", "review", "follow-money", "test-evidence",
                "witnesses", "decisions", "congressional-action", "coordination")
    assert parsed.targets == [f"{prefix}#{key}" for key in expected]
    assert html.count('<svg class="map-connectors"') == 5
    assert html.count('aria-hidden="true" focusable="false"') == 5
    assert html.count('class="map-connector conditional"') == 1
    assert html.count('<path class="map-connector') == 12
    for removed in ("House authority", "Senate authority", "House approvals", "Senate approvals",
                    ">Records<", ">Review<", ">Witnesses<", "Provenance", "Findings", "Restrictions",
                    "Committee approval", "Separate state authority", "Why this connection?", ">Requirements<"):
        assert removed not in html
    assert 'tabindex=' not in html and '<text' not in html


def test_choice_cards_open_the_retained_destinations_once(monkeypatch):
    renderer = load_public_script("build_interactive_map", monkeypatch)
    html = renderer.choice_cards(navigation_fixture(), "overview", renderer.ENTRY_LABELS, renderer.ENTRY_LABELS)
    parsed = Links()
    parsed.feed(html)
    assert parsed.targets == ["#authority", "#investigation", "#lessons"]
    assert all(label in html for label in ("Explore the structure", "Walk through an investigation", "Lessons and failure points"))
    assert "map-wire" not in html and "Requirements" not in html and "Why this connection?" not in html


def test_legacy_gate_fragments_and_evidence_survive_direct_navigation(monkeypatch):
    renderer = load_public_script("build_interactive_map", monkeypatch)
    nodes = navigation_fixture()
    nodes["follow-money"]["fictional"] = True
    nodes["follow-money"]["connection_evidence"] = {"decisions": [["Counterevidence", "Fixture exhibit retained."]]}
    html = renderer.render_map(nodes)
    parsed = Links()
    parsed.feed(html)
    edges = {f"edge-{origin}--{target}" for origin, node in nodes.items() for target, _ in node["choices"]}
    assert parsed.screens == set(nodes) | edges
    assert "Fixture exhibit retained." in html and "Required evidence: house to review." in html
    assert not any(url.startswith("#edge-") for url in parsed.targets)


def test_diagram_still_validates_connections_and_escapes_titles(monkeypatch):
    renderer = load_public_script("build_interactive_map", monkeypatch)
    nodes = navigation_fixture()
    nodes["house"]["title"] = '<script>alert("fixture")</script>'
    html = renderer.diagram(nodes)
    assert "<script>" not in html and "&lt;script&gt;" in html
    nodes["house"]["choices"].clear()
    with pytest.raises(ValueError, match="Missing diagram connection house to review"):
        renderer.diagram(nodes)


@pytest.mark.parametrize("name", ["dist/index.html", "dist/web/index.html"])
def test_public_scan_allows_one_exact_vote_action_only_on_landings(monkeypatch, name):
    builder = load_public_script("build_public_release", monkeypatch)
    action = '<a class="button primary" href="https://vote.foundups.com/">Vote — contact Congress</a>'.encode("utf-8")
    builder.validate_public_file(name, b"<main>" + action + b"</main>")
    with pytest.raises(ValueError):
        builder.validate_public_file(name, action + action)
    with pytest.raises(ValueError):
        builder.validate_public_file(name, action + b"<p>internal 0102</p>")
    with pytest.raises(ValueError):
        builder.validate_public_file("dist/explore.html", action)


@pytest.mark.parametrize("payload", [
    b'<a href="https://vote.foundups.com/">Visit</a>',
    b'<a class="button primary" href="https://vote.foundups.com/private">Visit</a>',
    b'<a href="https://vote.foundups.com.evil.example/">Visit</a>',
    b'<a href="https://vote.foundups.com/?next=internal">Visit</a>',
    b"foundups", b"voteballots", b"openclaw", b"github", b"WSP 97", b"\xef\xbf\xbd",
])
def test_public_scan_rejects_nonallowlisted_content(monkeypatch, payload):
    builder = load_public_script("build_public_release", monkeypatch)
    with pytest.raises(ValueError):
        builder.validate_public_file("dist/index.html", payload)
