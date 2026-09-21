"""
Route Contract Bridge Tests

Tests for the /f/{foundup_id} canonical landing route.
WSP 104: /f/{foundup_id} is the canonical FoundUp landing namespace.

Route behavior:
  - /f/ and /f/{foundup_id} render scope-free public discovery
  - /f/{foundup_id}/app and app deep links hand off to /member/
  - Member runtime catalog and entry_url stay outside public rendering
"""
import json
import os
import re
import shutil
import subprocess
from html.parser import HTMLParser
import pytest

# public/member
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _find_repo_root():
    """Walk up from ROOT to find repo root (contains .git)."""
    current = ROOT
    for _ in range(10):  # safety limit
        if os.path.isdir(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:  # reached filesystem root
            break
        current = parent
    # Fallback to computed path (original behavior)
    return os.path.dirname(os.path.dirname(ROOT))


REPO_ROOT = _find_repo_root()


def _firebase_json_exists():
    """Check if firebase.json exists (may not be tracked in repo)."""
    return os.path.isfile(os.path.join(REPO_ROOT, "firebase.json"))


def _read(relpath, base=ROOT):
    with open(os.path.join(base, relpath), encoding="utf-8") as f:
        return f.read()


class _InlineScripts(HTMLParser):
    """Collect inline script text using HTML's case-insensitive tag semantics."""

    def __init__(self):
        super().__init__()
        self.scripts = []
        self.in_script = False

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.in_script = not any(name == "src" for name, _ in attrs)
            if self.in_script:
                self.scripts.append("")

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False

    def handle_data(self, data):
        if self.in_script:
            self.scripts[-1] += data


def _raw_landing_script():
    """Extract the actual sole inline owner without rewriting its JavaScript."""
    parser = _InlineScripts()
    parser.feed(_read("../f/index.html"))
    parser.close()
    assert len(parser.scripts) == 1, "Expected the canonical inline route owner"
    return parser.scripts[0]


def _landing_script():
    """Keep documentation comments from satisfying static runtime assertions."""
    return re.sub(r"(?m)^\s*//[^\n]*$", "", _raw_landing_script())


def _app_gate():
    script = _landing_script()
    gate = re.search(r"if\s*\(isAppMount\)\s*\{([^}]+)\}", script)
    assert gate, "App routes must retain an explicit participation gate"
    return script, gate


@pytest.mark.parametrize("tag", ["SCRIPT", "ScRiPt", 'script type="text/javascript"'])
def test_inline_script_extraction_uses_html_tag_semantics(monkeypatch, tag):
    """Casing/attributes cannot hide code; external script names are not code."""
    close_tag = tag.split()[0]
    html = (
        '<SCRIPT SRC="/member/mall-video-catalog.json"></SCRIPT>'
        f"<{tag}>\n// documentation only\nvar marker = 'actual code';\n</{close_tag}>"
    )
    monkeypatch.setitem(globals(), "_read", lambda _: html)
    assert _landing_script().strip() == "var marker = 'actual code';"


class TestCanonicalRouteExists:
    """Test that the canonical landing surface exists."""

    def test_landing_html_exists(self):
        """Canonical landing HTML file exists at public/f/index.html."""
        landing_path = os.path.join(REPO_ROOT, "public", "f", "index.html")
        assert os.path.isfile(landing_path), "public/f/index.html must exist"

    def test_landing_has_route_parsing(self):
        """Landing parses foundup_id from path."""
        landing = _read("../f/index.html")
        assert "/f/" in landing
        assert "foundup_id" in landing.lower() or "foundupId" in landing

    def test_landing_fetches_catalog(self):
        """Discovery fetches only the scope-free projection, never member data."""
        script = _landing_script()
        assert "var PUBLIC_CATALOG_URL = '/f/public_catalog.json';" in script
        assert re.findall(r"fetch\(([^)]+)\)", script) == [
            "PUBLIC_CATALOG_URL", "PUBLIC_CATALOG_URL"
        ]
        assert "mall-video-catalog.json" not in script


@pytest.mark.skipif(not _firebase_json_exists(), reason="firebase.json not tracked in repo")
class TestFirebaseRouting:
    """Test Firebase hosting configuration for canonical route.

    Note: firebase.json may not be tracked in the repo (deployment config).
    These tests are skipped in clean checkouts without firebase.json.
    """

    def test_firebase_json_exists(self):
        """firebase.json exists at repo root."""
        firebase_path = os.path.join(REPO_ROOT, "firebase.json")
        assert os.path.isfile(firebase_path)

    def test_f_route_rewrite_exists(self):
        """Firebase has rewrite rule for /f/**."""
        firebase_path = os.path.join(REPO_ROOT, "firebase.json")
        with open(firebase_path, encoding="utf-8") as f:
            config = json.load(f)

        rewrites = config.get("hosting", {}).get("rewrites", [])
        f_rule = next((r for r in rewrites if r.get("source") == "/f/**"), None)

        assert f_rule is not None, "Must have /f/** rewrite rule"
        assert f_rule.get("destination") == "/f/index.html"

    def test_f_route_comes_before_catchall(self):
        """The /f/** rule must come before the ** catchall."""
        firebase_path = os.path.join(REPO_ROOT, "firebase.json")
        with open(firebase_path, encoding="utf-8") as f:
            config = json.load(f)

        rewrites = config.get("hosting", {}).get("rewrites", [])
        sources = [r.get("source") for r in rewrites]

        f_index = sources.index("/f/**") if "/f/**" in sources else -1
        catchall_index = sources.index("**") if "**" in sources else -1

        assert f_index >= 0, "/f/** rule must exist"
        assert catchall_index >= 0, "** catchall must exist"
        assert f_index < catchall_index, "/f/** must come before ** catchall"


class TestCanonicalRouteBehavior:
    """Test canonical landing page behavior."""

    def test_landing_handles_missing_id(self):
        """The root route is the public portfolio, not an old missing-ID error."""
        script = _landing_script()
        assert "var isPortfolioIndex = !match || !match[1] || match[1] === 'index.html';" in script
        assert "renderPortfolioShowcase(projection);" in script

    def test_landing_handles_invalid_id(self):
        """Landing shows error for unknown/invalid foundup_id."""
        landing = _read("../f/index.html")
        # Landing shows "not found" for invalid IDs (catalog lookup fails)
        assert "not found" in landing.lower() or "does not exist" in landing.lower()

    def test_landing_has_mall_fallback(self):
        """Landing has Return to Mall link."""
        landing = _read("../f/index.html")
        assert "/member/" in landing
        assert "Mall" in landing

    def test_landing_preserves_subpath(self):
        """Landing captures subpath for future routing."""
        landing = _read("../f/index.html")
        assert "subpath" in landing


class TestCanonicalRouteRendering:
    """Test that landing renders content directly (no redirect)."""

    def test_landing_does_not_redirect(self):
        """Landing does NOT redirect to /member/foundup.html."""
        landing = _read("../f/index.html")
        # Should NOT have location.replace redirect
        assert "location.replace" not in landing
        # Should NOT redirect to transitional entry
        assert "/member/foundup.html?id=" not in landing

    def test_landing_renders_entry_content(self):
        """Landing renders entry content directly."""
        landing = _read("../f/index.html")
        # Should render landing UI elements
        assert "entry-hero" in landing
        assert "entry-details" in landing
        assert "entry-footer" in landing

    def test_landing_is_canonical(self):
        """Landing explicitly marks itself as canonical."""
        landing = _read("../f/index.html")
        assert "canonical" in landing.lower()
        assert "WSP 104" in landing


class TestWsp104Compliance:
    """Test WSP 104 route namespace compliance."""

    def test_canonical_route_displayed(self):
        """Canonical route is displayed to user."""
        landing = _read("../f/index.html")
        assert "Canonical route:" in landing or "canonical-route" in landing

    def test_no_transitional_redirect(self):
        """No auto-redirect on page load — canonical URL stays visible."""
        landing = _read("../f/index.html")
        # The old bridge had location.replace redirect — this should not
        assert "location.replace(" not in landing
        # Should not auto-redirect to transitional entry on load
        assert "/member/foundup.html?id=" not in landing
        # The word "transitional" should not appear (old bridge language)
        assert "transitional" not in landing.lower()

    def test_stable_identity_from_path(self):
        """FoundUp identity derived from URL path, not query params."""
        landing = _read("../f/index.html")
        # Should parse from pathname, not search params
        assert "window.location.pathname" in landing
        assert "/f/" in landing
        # Should NOT rely on query param for primary routing
        assert "params.get('id')" not in landing


class TestSubpathForwardCompatibility:
    """Test subpath support for future /app mount."""

    def test_subpath_captured(self):
        """Subpath is captured from URL."""
        landing = _read("../f/index.html")
        assert "subpath" in landing

    def test_subpath_info_displayed(self):
        """Subpath info displayed when present."""
        landing = _read("../f/index.html")
        assert "subpath-info" in landing or "Subpath:" in landing

    def test_app_mount_comment(self):
        """Code mentions future /app mount."""
        landing = _read("../f/index.html")
        assert "/app" in landing


class TestTransitionalFallbackPreserved:
    """Test that transitional entry path still works (backward compat)."""

    def test_foundup_html_exists(self):
        """Transitional entry page still exists."""
        assert os.path.isfile(os.path.join(ROOT, "foundup.html"))

    def test_foundup_html_accepts_id_param(self):
        """Transitional entry still reads id from URL param."""
        entry = _read("foundup.html")
        assert "params.get('id')" in entry

    def test_member_entry_flow_unchanged(self):
        """Member entry flow structure is preserved."""
        entry = _read("foundup.html")
        assert "entry-shell" in entry
        assert "entryContent" in entry


class TestAppMountRoute:
    """Canonical identity does not grant participation (WSP 104/97)."""

    def test_app_mount_detection(self):
        """Landing detects /app subpath."""
        landing = _read("../f/index.html")
        assert "isAppMount" in landing
        assert "subpath === 'app'" in landing or "'app'" in landing

    def test_app_mount_hands_off_to_existing_member_gate(self):
        """Public app routes leave before reading a tenant or rendering it."""
        script, gate = _app_gate()
        assert "var MALL_HOME = '/member/';" in script
        assert re.fullmatch(r"\s*window\.location\.href = MALL_HOME;\s*return;\s*", gate[1])
        assert "fetch(" not in script[script.index("var foundupId"):gate.start()]

    def test_public_route_does_not_use_member_entry_url(self):
        """A member entry_url cannot become a public iframe source."""
        script = _landing_script()
        assert "entry_url" not in script
        assert "renderAppMount" not in script

    def test_public_landing_retains_return_to_mall(self):
        """Discovery keeps navigation to the existing admission owner."""
        script = _landing_script()
        assert "'return_to_mall'" in script
        assert "'Return to Mall'" in script
        assert "window.location.href = MALL_HOME;" in script

    def test_public_route_does_not_embed_tenant_iframe(self):
        """Retired CSS must not count as an active or authorized app mount."""
        script = _landing_script().lower()
        assert "<iframe" not in script
        assert not re.search(r"createelement\(['\"]iframe['\"]\)", script)

    def test_app_gate_is_independent_of_catalog_readiness(self):
        """Admission happens before a catalog response or readiness decision."""
        script, gate = _app_gate()
        detail = script[script.index("var foundupId"):]
        assert detail.index("if (isAppMount)") < detail.index("fetch(PUBLIC_CATALOG_URL)")
        assert "entry_url" not in gate[1]


class TestAppMountDeepLinks:
    """App deep links use the same admission owner; no public frame forwarding."""

    def test_deep_path_is_included_in_participation_gate(self):
        script = _landing_script()
        assert "subpath === 'app' || subpath.startsWith('app/')" in script
        _app_gate()

    def test_deep_path_does_not_become_public_frame_url(self):
        script = _landing_script()
        assert "appSubpath" not in script
        assert "deepPath" not in script
        assert "resolvedUrl" not in script


class TestPublicDiscoveryLinks:
    """Public view links do not resurrect the retired member launch control."""

    def test_public_link_container_exists(self):
        script = _landing_script()
        assert "entry-cta-block" in script
        assert "entry-launch-app-block" not in script
        assert "entry-launch-app-btn" not in script

    def test_public_links_do_not_construct_tenant_mount_route(self):
        script = _landing_script()
        assert "'/f/' + foundupId + '/app'" not in script
        assert "addLink('app_url', 'Open App', item.app_url);" in script

    def test_public_links_use_validated_url_properties(self):
        script = _landing_script()
        assert "var safe = safeUrl(url);" in script
        assert "if (safe) links.push" in script
        assert "a.href = l[2];" in script
        assert "item.entry_url" not in script

    def test_recommendations_do_not_offer_public_tenant_launch(self):
        script = _landing_script()
        assert "launch_app" not in script
        assert "'Launch App'" not in script
        assert "'return_to_mall'" in script


class TestGotJunkTenantBinding:
    """Test GotJunk as first bound tenant (WSP 104)."""

    def test_gotjunk_in_catalog(self):
        """GotJunk exists in mall-video-catalog.json."""
        catalog = _read("mall-video-catalog.json")
        assert '"foundup_id": "gotjunk_001"' in catalog

    def test_gotjunk_has_routing_prefix(self):
        """GotJunk catalog entry has correct routing_prefix."""
        catalog = _read("mall-video-catalog.json")
        assert '"/f/gotjunk_001"' in catalog

    def test_gotjunk_has_data_namespace(self):
        """GotJunk catalog entry has data_namespace."""
        catalog = _read("mall-video-catalog.json")
        assert '"idb_gotjunk_001"' in catalog

    def test_gotjunk_no_entry_url_until_frame_compatible(self):
        """GotJunk has no entry_url until Cloud Run headers allow iframe embed.

        BLOCKER: Cloud Run returns X-Frame-Options: SAMEORIGIN which blocks
        the shell iframe mount at /f/gotjunk_001/app. entry_url must remain
        absent until the deployment is configured with frame-compatible headers.

        Unblock by: adding X-Frame-Options: ALLOWALL or removing the header
        and setting Content-Security-Policy frame-ancestors to include the
        shell origin, then re-adding entry_url to catalog and manifest.
        """
        catalog = _read("mall-video-catalog.json")
        idx = catalog.find('"foundup_id": "gotjunk_001"')
        assert idx > 0
        next_entry = catalog.find('"foundup_id":', idx + 30)
        if next_entry < 0:
            next_entry = len(catalog)
        gotjunk_entry = catalog[idx:next_entry]
        assert '"entry_url"' not in gotjunk_entry


class TestKoseiTenantBinding:
    """Test Kosei as second bound tenant (WSP 104).

    Kosei is bound to the canonical shell route family after GotJunk.
    Unlike GotJunk, Kosei has no embeddable runtime yet (discoverable_only).
    """

    def test_kosei_in_catalog(self):
        """Kosei exists in mall-video-catalog.json."""
        catalog = _read("mall-video-catalog.json")
        assert '"foundup_id": "kosei"' in catalog

    def test_kosei_has_routing_prefix(self):
        """Kosei catalog entry has correct routing_prefix."""
        catalog = _read("mall-video-catalog.json")
        assert '"/f/kosei"' in catalog

    def test_kosei_has_data_namespace(self):
        """Kosei catalog entry has data_namespace."""
        catalog = _read("mall-video-catalog.json")
        assert '"idb_kosei"' in catalog

    def test_kosei_has_entry_url(self):
        """Kosei has entry_url after BX4 iframe verification confirmed embeddability.

        BX4 (PR #337) verified the Kosei app renders inside the FoundUps shell iframe.
        entry_url is now truthfully set to the deployed app URL.
        """
        catalog = _read("mall-video-catalog.json")
        idx = catalog.find('"foundup_id": "kosei"')
        assert idx > 0
        next_entry = catalog.find('"foundup_id":', idx + 20)
        if next_entry < 0:
            next_entry = len(catalog)
        kosei_entry = catalog[idx:next_entry]
        # entry_url should be present after iframe verification
        assert '"entry_url": "https://foundupscom.web.app/kosei/app/"' in kosei_entry

    def test_kosei_launch_readiness_is_ready(self):
        """Kosei is ready after iframe embed verification (BX4)."""
        catalog = _read("mall-video-catalog.json")
        idx = catalog.find('"foundup_id": "kosei"')
        assert idx > 0
        next_entry = catalog.find('"foundup_id":', idx + 20)
        if next_entry < 0:
            next_entry = len(catalog)
        kosei_entry = catalog[idx:next_entry]
        assert '"ready"' in kosei_entry


class TestPublicProjectionHandling:
    """Public projection shapes are sanitized before landing rendering."""

    def test_landing_handles_public_projection_shapes(self):
        script = _landing_script()
        assert "Array.isArray(projection.entities)" in script
        assert "Array.isArray(projection.items)" in script
        assert "Array.isArray(projection)" in script
        assert "var items = projectionEntities(projection);" in script

    def test_projection_is_sanitized_before_use(self):
        script = _landing_script()
        assert "return raw.map(sanitizeEntity);" in script
        assert "Object.prototype.hasOwnProperty.call(entity, k)" in script
        assert "PUBLIC_FIELD_ALLOWLIST[k] === true" in script
        assert "resolvedUrl" not in script


_NODE_ROUTE_VM = r"""
const {runInNewContext} = require('node:vm');
const input = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
const events = [], fetches = [], forbidden = [], errors = [];
let address = new URL(input.path + (input.search || '') + (input.hash || ''),
  'https://shell.invalid');
let sandbox;
function record(kind, target, value) {
  const context = sandbox && sandbox.entryRedDog && sandbox.entryRedDog.getContext();
  events.push({kind, target, value, pathname: address.pathname,
    contextId: context ? context.foundupId : null,
    itemId: context && context.item ? context.item.foundup_id : null});
}
function element(id) {
  let html = '';
  return {id, style: {}, children: [], value: '',
    classList: {toggle() {}, remove() {}, add() {}},
    addEventListener() {}, scrollIntoView() {}, querySelectorAll() { return []; },
    querySelector() { return null; },
    appendChild(child) { this.children.push(child); }, insertAdjacentHTML() {},
    set innerHTML(value) { html = String(value); record('html', id, html); },
    get innerHTML() { return html; },
    set textContent(value) {
      html = String(value).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    },
    set href(value) { record('link', id, value); }
  };
}
const ids = ['entryContent', 'entryRedDog', 'conciergeSheet', 'conciergeScrim',
  'conciergeContextBody', 'entryBriefingBody', 'entryRecsBody',
  'showcaseSearch', 'showcaseReadiness', 'showcaseGrid'];
const nodes = Object.fromEntries(ids.map(id => [id, element(id)]));
const location = {
  get pathname() { return address.pathname; }, get search() { return address.search; },
  get hash() { return address.hash; }, get origin() { return address.origin; },
  get href() { return address.href; },
  set href(value) { record('navigate', 'location', value); address = new URL(value, address); }
};
const document = {
  getElementById(id) { if (!nodes[id]) throw new Error('Unexpected DOM id: ' + id); return nodes[id]; },
  createElement(tag) {
    if (tag === 'iframe' || tag === 'script') {
      forbidden.push('element:' + tag); throw new Error('Forbidden active element');
    }
    return element('created:' + tag);
  },
  createTextNode(text) { return {textContent: String(text)}; },
  addEventListener() {}, querySelector() { return null; },
  set title(value) { record('title', 'document', value); }
};
const history = {replaceState(_state, _title, value) {
  record('history', 'replaceState', value);
  if (input.history === 'throw') throw new Error('Synthetic history rejection');
  const next = new URL(value, address);
  if (next.origin !== address.origin) throw new Error('Cross-origin replacement');
  address = next;
}};
async function run() {
  sandbox = {document, location, URL, URLSearchParams,
    console: {error(...args) { errors.push(args.map(String).join(' ')); }},
    fetch(url) {
      fetches.push(url);
      if (url !== '/f/public_catalog.json') {
        forbidden.push('fetch:' + url); return Promise.reject(new Error('Forbidden fetch'));
      }
      if (input.pending_fetch) return new Promise(() => {});
      if (input.fetch_fail) return Promise.reject(new Error('Synthetic unavailable catalog'));
      return Promise.resolve({ok: true, json: () => Promise.resolve(input.projection)});
    }
  };
  sandbox.window = sandbox;
  if (input.history !== 'missing') sandbox.history = history;
  runInNewContext(input.script, sandbox, {filename: 'actual-f-inline.js', timeout: 500,
    contextCodeGeneration: {strings: false, wasm: false}});
  // Real Promise callbacks run after the IIFE initializes its local state.
  await new Promise(resolve => setImmediate(resolve));
  const context = sandbox.entryRedDog ? sandbox.entryRedDog.getContext() : null;
  process.stdout.write(JSON.stringify({events, fetches, forbidden, errors, context,
    pathname: address.pathname, search: address.search, hash: address.hash,
    html: Object.fromEntries(ids.map(id => [id, nodes[id].innerHTML]))}));
}
run().catch(error => { console.error(error.stack); process.exitCode = 1; });
"""


def _public_entity(**overrides):
    item = {"foundup_id": "synthetic_001", "display_name": "Synthetic discovery",
            "portfolio_status": "portfolio_candidate", "poc_landing_status": "discoverable_only"}
    item.update(overrides)
    return item


def _landing_vm(tmp_path, path, entities=None, **overrides):
    """Run only the real inline owner with synthetic DOM, history and fetch."""
    node = "C:/Program Files/nodejs/node.exe" if os.name == "nt" else shutil.which("node")
    assert node and os.path.isfile(node), "Node is required for route behavior coverage"
    request = {"script": _raw_landing_script(), "path": path,
               "projection": {"entities": entities if entities is not None else [_public_entity()]}}
    request.update(overrides)
    env = {k: v for k, v in os.environ.items()
           if k.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "PATHEXT"}}
    env.update(TEMP=str(tmp_path), TMP=str(tmp_path), HOME=str(tmp_path), USERPROFILE=str(tmp_path))
    proc = subprocess.run([node, "--unhandled-rejections=strict", "-e", _NODE_ROUTE_VM],
                          input=json.dumps(request), capture_output=True, text=True,
                          encoding="utf-8", timeout=10, cwd=tmp_path, env=env)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    result = json.loads(proc.stdout)
    assert result["forbidden"] == [], result
    return result


def _assert_no_tenant_render(result):
    assert not any(e["kind"] == "html" and "entry-hero" in e["value"]
                   for e in result["events"])
    assert not any(e["kind"] == "html" and e["target"] == "conciergeContextBody"
                   for e in result["events"])
    if result["context"] is not None:
        assert result["context"]["item"] is None
        assert result["context"]["foundupId"] is None


def _assert_canonical_render(result, canonical, *, replaced):
    context = result["context"]
    assert context["foundupId"] == canonical and context["item"]["foundup_id"] == canonical
    assert "Canonical: /f/" + canonical in result["html"]["entryContent"]
    renders = [i for i, e in enumerate(result["events"]) if e["kind"] == "html"
               and ("entry-hero" in e["value"] or e["target"] == "conciergeContextBody")]
    assert len(renders) >= 2, result
    for index in renders:
        event = result["events"][index]
        assert event["pathname"] == "/f/" + canonical
        assert event["contextId"] == canonical
    histories = [i for i, e in enumerate(result["events"]) if e["kind"] == "history"]
    if replaced:
        assert len(histories) == 1 and histories[0] < min(renders)
        assert result["events"][histories[0]]["value"] == "/f/" + canonical
    else:
        assert histories == []
    assert not any(e["kind"] == "navigate" for e in result["events"])
    assert result["fetches"] == ["/f/public_catalog.json"]


@pytest.mark.parametrize("shape", ["entities", "items", "array"])
def test_vm_legacy_canonical_identity_and_projection_shapes(tmp_path, shape):
    public = _public_entity()
    projection = [dict(public, entry_url="/private", creator="private-principal")]
    result = _landing_vm(tmp_path, "/f/synthetic_001", search="?devMall=1", hash="#keep",
                         projection=projection if shape == "array" else {shape: projection})
    _assert_canonical_render(result, "synthetic_001", replaced=False)
    assert result["context"]["item"] == public
    assert result["search"] == "?devMall=1" and result["hash"] == "#keep"
    assert "private-principal" not in result["html"]["entryContent"]


@pytest.mark.parametrize("canonical,alias", [
    ("synthetic_001", "friendly"), ("canonical", "constructor"),
    ("canonical", "__proto__"), ("canonical", "prototype"),
    ("__proto__", "friendly"), ("constructor", "friendly"), ("canonical", "a" * 65),
])
@pytest.mark.parametrize("suffix", ["", "/"])
def test_vm_alias_canonicalizes_before_render_and_context(tmp_path, canonical, alias, suffix):
    item = _public_entity(foundup_id=canonical, public_discovery_alias=alias)
    result = _landing_vm(tmp_path, "/f/" + alias + suffix, [item],
                         search="?id=other&next=https://elsewhere.invalid", hash="#other")
    _assert_canonical_render(result, canonical, replaced=True)
    assert result["pathname"] == "/f/" + canonical
    assert result["search"] == result["hash"] == ""
    assert result["context"]["item"] == item


def test_vm_alias_single_decode_and_canonical_render_bytes(tmp_path):
    item = _public_entity(public_discovery_alias="friendly")
    canonical = _landing_vm(tmp_path, "/f/synthetic_001", [item])
    alias = _landing_vm(tmp_path, "/f/%66riendly", [item])
    _assert_canonical_render(alias, "synthetic_001", replaced=True)
    assert alias["html"] == canonical["html"]
    assert alias["context"] == canonical["context"]


@pytest.mark.parametrize("token", ["synthetic_001", "friendly", "unknown"])
@pytest.mark.parametrize("suffix", ["app", "app/jobs/1"])
@pytest.mark.parametrize("fetch_fail", [False, True])
def test_vm_app_handoff_precedes_even_failed_catalog(tmp_path, token, suffix, fetch_fail):
    result = _landing_vm(tmp_path, "/f/" + token + "/" + suffix,
                         [_public_entity(public_discovery_alias="friendly")],
                         fetch_fail=fetch_fail, search="?devMall=1")
    assert result["fetches"] == [] and result["context"] is None
    assert result["pathname"] == "/member/" and result["search"] == "?devMall=1"
    assert result["events"] == [{"kind": "navigate", "target": "location",
                                  "value": "/member/?devMall=1", "pathname": "/f/" + token + "/" + suffix,
                                  "contextId": None, "itemId": None}]


@pytest.mark.parametrize("path", [
    "/f/unknown", "/f/Friendly", "/f/friendly/other", "/f/friendly/application",
    "/f/friendly//", "/f/friendly%2fapp", "/f/friendly%5c", "/f/friendly%25",
    "/f/friendly%252f", "/f/%", "/f/%GG", "/f/%E0%A4%A",
    "/f/friendly%0A", "/f/friendly%0D", "/f/friendly%20",
])
def test_vm_invalid_alias_paths_do_not_publish_tenant(tmp_path, path):
    result = _landing_vm(tmp_path, path, [_public_entity(public_discovery_alias="friendly")])
    _assert_no_tenant_render(result)
    assert not any(e["kind"] in {"history", "navigate"} for e in result["events"])


@pytest.mark.parametrize("bad_alias", [
    "", None, False, 0, [], {}, "Friendly", "two words", "a/b", "a\\b", "a%2fb",
    "caf\u00e9", "friendly\n", "friendly\r", "friendly\t", "friendly\r\n",
])
def test_vm_malformed_projection_alias_rejects_before_canonical_render(tmp_path, bad_alias):
    result = _landing_vm(tmp_path, "/f/synthetic_001", [_public_entity(public_discovery_alias=bad_alias)])
    _assert_no_tenant_render(result)
    assert not any(e["kind"] == "history" for e in result["events"])


@pytest.mark.parametrize("status", ["not_portfolio", "missing", None, "", "portfolio", "PORTFOLIO_READY"])
def test_vm_alias_ineligible_or_missing_portfolio_status_is_rejected(tmp_path, status):
    item = _public_entity(public_discovery_alias="friendly", portfolio_status=status)
    if status == "missing":
        del item["portfolio_status"]
    result = _landing_vm(tmp_path, "/f/friendly", [item])
    _assert_no_tenant_render(result)
    assert not any(e["kind"] == "history" for e in result["events"])


@pytest.mark.parametrize("status", ["not_portfolio", "missing", None])
def test_vm_no_alias_keeps_legacy_canonical_status_handling(tmp_path, status):
    item = _public_entity(portfolio_status=status)
    if status == "missing":
        del item["portfolio_status"]
    result = _landing_vm(tmp_path, "/f/synthetic_001", [item])
    _assert_canonical_render(result, "synthetic_001", replaced=False)


@pytest.mark.parametrize("case", ["duplicate_alias", "canonical_collision", "self_collision", "duplicate_target"])
def test_vm_ambiguous_projection_alias_is_not_first_match(tmp_path, case):
    first = _public_entity(public_discovery_alias="friendly")
    second = _public_entity(foundup_id="second")
    if case == "duplicate_alias":
        second["public_discovery_alias"] = "friendly"
    elif case == "canonical_collision":
        second["foundup_id"] = "friendly"
    elif case == "self_collision":
        first["public_discovery_alias"] = first["foundup_id"]
    else:
        second["foundup_id"] = first["foundup_id"]
    path = "/f/synthetic_001" if case == "self_collision" else "/f/friendly"
    result = _landing_vm(tmp_path, path, [first, second])
    _assert_no_tenant_render(result)
    assert not any(e["kind"] == "history" for e in result["events"])


@pytest.mark.parametrize("history", ["missing", "throw"])
def test_vm_failed_alias_history_cannot_render_or_publish_context(tmp_path, history):
    result = _landing_vm(tmp_path, "/f/friendly", [_public_entity(public_discovery_alias="friendly")],
                         history=history)
    _assert_no_tenant_render(result)
    assert result["pathname"] == "/f/friendly"
    assert not any(e["kind"] == "navigate" for e in result["events"])


@pytest.mark.parametrize("path", ["/f/synthetic_001", "/f/friendly"])
def test_vm_failed_catalog_does_not_publish_tenant(tmp_path, path):
    result = _landing_vm(tmp_path, path, [_public_entity(public_discovery_alias="friendly")], fetch_fail=True)
    _assert_no_tenant_render(result)
    assert result["fetches"] == ["/f/public_catalog.json"]
    assert not any(e["kind"] == "history" for e in result["events"])


@pytest.mark.parametrize("path", ["/f/synthetic_001", "/f/friendly"])
def test_vm_pending_catalog_exposes_no_unverified_identity(tmp_path, path):
    result = _landing_vm(tmp_path, path, [_public_entity(public_discovery_alias="friendly")], pending_fetch=True)
    _assert_no_tenant_render(result)
    assert result["context"] is not None
    assert result["fetches"] == ["/f/public_catalog.json"]
    assert result["events"] == [] and result["errors"] == []
