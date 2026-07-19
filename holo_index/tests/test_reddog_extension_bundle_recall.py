#!/usr/bin/env python3
"""Regression tests for RedDog extension / bridge bundle-json recall."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from holo_index.cli.commands.bundle_json import (
    _lexical_task_retrieval,
    _resolve_module_dir,
    _direct_read_fetch,
    _direct_read_deny_reason,
    _normalize_direct_read_path,
    _resolve_within_repo,
    _split_path_symbol,
    _locate_symbol_line,
    _read_symbol_window,
    DIRECT_READ_PER_FILE_BYTES,
    DIRECT_READ_TOTAL_BUDGET_BYTES,
    DIRECT_READ_SYMBOL_SCAN_BYTES,
)

EXTENSION_JS = REPO_ROOT / "extensions" / "reddog" / "extension.js"

# REDDOG_TARGET_RECALL_PATH_AWARE_PHASE1 (slice 1/3): the detector under test is
# evaluateTargetRecall in extension.js. These required targets mirror the
# FoundUp-creation audit prompt whose run trace falsely reported no index gap.
FOUNDUP_REQUIRED_TARGETS = [
    "WSP_framework/src/WSP_109_FoundUp_Onboarding_Protocol.md",
    "modules/infrastructure/openclaw/src/openclaw_foundup_orchestrator.py",
    "modules/communication/moltbot_bridge/src/hermes_foundup_job_executor.py",
]

FOUNDUP_CREATION_PROMPT = (
    "Audit the FoundUp creation monorepo WSP_109 execution path.\n"
    "\n"
    "Required direct-read targets:\n"
    "- " + FOUNDUP_REQUIRED_TARGETS[0] + "\n"
    "- " + FOUNDUP_REQUIRED_TARGETS[1] + "\n"
    "- " + FOUNDUP_REQUIRED_TARGETS[2] + "\n"
    "\n"
    "Produce required RedDog architect output sections per contract.\n"
)


def _node_available() -> bool:
    return shutil.which("node") is not None


def _run_target_recall(task_text: str, code_hits: list[dict]) -> dict:
    """Invoke evaluateTargetRecall (extension.js) via node and return its JSON."""
    driver = (
        "const path=require('path');const Module=require('module');"
        "const root=process.argv[1];"
        "const extDir=path.join(root,'extensions','reddog');"
        "const vscodeMock={window:{activeTextEditor:null,visibleTextEditors:[]},"
        "workspace:{workspaceFolders:[{uri:{fsPath:root}}],getConfiguration:()=>({get:(_k,f)=>f})},"
        "commands:{registerCommand:()=>({dispose(){}})},env:{clipboard:{writeText:async()=>{}}},"
        "Uri:{joinPath:()=>({fsPath:''})},ViewColumn:{Beside:2}};"
        "const vscodePath=path.join(extDir,'node_modules','vscode','index.js');"
        "require.cache[vscodePath]={exports:vscodeMock,loaded:true,id:vscodePath};"
        "const origResolve=Module._resolveFilename;"
        "Module._resolveFilename=function(r,p,m,o){if(r==='vscode')return vscodePath;"
        "return origResolve.call(this,r,p,m,o);};"
        "const orch=require(path.join(extDir,'extension.js'));"
        "Module._resolveFilename=origResolve;"
        "const input=JSON.parse(require('fs').readFileSync(0,'utf8'));"
        "const out=orch.evaluateTargetRecall(input.task,{task_retrieval:{code_hits:input.code_hits}});"
        "process.stdout.write(JSON.stringify(out));"
    )
    proc = subprocess.run(
        ["node", "-e", driver, str(REPO_ROOT)],
        input=json.dumps({"task": task_text, "code_hits": code_hits}),
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout.strip())


def _hits(*locations: str) -> list[dict]:
    return [{"location": loc, "need": "path match: " + loc.split("/")[-1]} for loc in locations]


def _code_locations(payload: dict) -> list[str]:
    hits = payload.get("code_hits") or []
    return [str(h.get("location", "")).replace("\\", "/") for h in hits]


def _canonical_extension_locations(payload: dict) -> list[str]:
    return [
        loc.replace(
            "extensions/foundups_advisory_workers/extension.js",
            "extensions/reddog/extension.js",
        )
        for loc in _code_locations(payload)
    ]


@pytest.fixture
def ssd_path():
    return os.environ.get("HOLO_SSD_PATH", str(REPO_ROOT / "holo_index" / "ssd"))


def test_extension_js_in_top_hits_for_review_query(ssd_path):
    module_dir = _resolve_module_dir(REPO_ROOT, "extensions/reddog")
    payload = _lexical_task_retrieval(
        REPO_ROOT,
        "Review extensions/reddog/extension.js for WSP_97",
        5,
        ssd_path,
        module_dir=module_dir,
    )
    locs = _canonical_extension_locations(payload)
    assert "extensions/reddog/extension.js" in locs[:3]


def test_buildcopymarkdown_query_surfaces_extension_js(ssd_path):
    module_dir = _resolve_module_dir(REPO_ROOT, "extensions/reddog")
    payload = _lexical_task_retrieval(
        REPO_ROOT,
        "buildCopyMarkdown Copy MD Run Trace Redaction Gate Report",
        5,
        ssd_path,
        module_dir=module_dir,
    )
    locs = _canonical_extension_locations(payload)
    assert "extensions/reddog/extension.js" in locs[:3]


def test_advisory_bridge_query_surfaces_advisory_model_once(ssd_path):
    payload = _lexical_task_retrieval(
        REPO_ROOT,
        "advisory_model_once redaction gate bridge OpenRouter",
        5,
        ssd_path,
        module_dir=None,
    )
    locs = _code_locations(payload)
    assert "scripts/advisory_model_once.py" in locs[:3]


def test_bundle_json_cli_extension_js_recall(ssd_path, tmp_path, monkeypatch):
    monkeypatch.chdir(REPO_ROOT)
    import subprocess

    env = os.environ.copy()
    env["HOLO_SKIP_MODEL"] = "1"
    proc = subprocess.run(
        [
            sys.executable,
            "-B",
            "holo_index.py",
            "--bundle-json",
            "--search",
            "Review extensions/reddog/extension.js for WSP_97",
            "--bundle-module-hint",
            "extensions/reddog",
            "--limit",
            "5",
            "--quiet-root-alerts",
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    bundle = json.loads(proc.stdout.strip())
    locs = _canonical_extension_locations(bundle.get("task_retrieval") or {})
    assert bundle.get("ok") is True
    assert "extensions/reddog/extension.js" in locs[:3]


# --- REDDOG_TARGET_RECALL_PATH_AWARE_PHASE1 (slice 1/3) path-aware detector -------------

requires_node = pytest.mark.skipif(not _node_available(), reason="node runtime required for evaluateTargetRecall")


@requires_node
def test_required_targets_zero_recalled_flags_index_gap():
    """0 of N required direct-read targets in bundle => honest blind report."""
    result = _run_target_recall(FOUNDUP_CREATION_PROMPT, _hits("docs/unrelated_note.md"))
    assert result["index_gap_detected"] is True
    assert result["target_recall_ok"] is False
    assert result["required_targets_total"] == len(FOUNDUP_REQUIRED_TARGETS)
    assert result["required_targets_recalled"] == 0
    assert sorted(result["required_targets_missing"]) == sorted(FOUNDUP_REQUIRED_TARGETS)


@requires_node
def test_self_file_only_does_not_satisfy_required_recall():
    """A bundle containing ONLY extension.js must not count toward required recall."""
    result = _run_target_recall(
        FOUNDUP_CREATION_PROMPT,
        _hits("extensions/reddog/extension.js"),
    )
    assert result["index_gap_detected"] is True
    assert result["target_recall_ok"] is False
    assert result["required_targets_recalled"] == 0
    assert sorted(result["required_targets_missing"]) == sorted(FOUNDUP_REQUIRED_TARGETS)


@requires_node
def test_all_required_targets_present_no_index_gap():
    """All required targets present in content => index_gap_detected=false."""
    result = _run_target_recall(FOUNDUP_CREATION_PROMPT, _hits(*FOUNDUP_REQUIRED_TARGETS))
    assert result["index_gap_detected"] is False
    assert result["target_recall_ok"] is True
    assert result["required_targets_recalled"] == len(FOUNDUP_REQUIRED_TARGETS)
    assert result["required_targets_missing"] == []


@requires_node
def test_no_required_list_preserves_prior_behavior():
    """Backward-compat: no required-target list => prior inference behavior."""
    result = _run_target_recall(
        "Review extensions/reddog/extension.js for WSP_97",
        _hits("extensions/reddog/extension.js"),
    )
    # Inference path: extension.js is the inferred target and it was recalled.
    assert result["target_recall_ok"] is True
    assert result["index_gap_detected"] is False
    assert result["required_targets_total"] == 0

    unknown = _run_target_recall("generic task with no recall targets", [])
    # No explicit list AND no inferred targets => unknown, never a fabricated gap.
    assert unknown["target_recall_ok"] == "unknown"
    assert unknown["index_gap_detected"] is False
    assert unknown["required_targets_total"] == 0


# --- REDDOG_DIRECT_READ_FALLBACK_BY_PATH_PHASE1 (slice 2/3) governed direct-read ------

# Real repo files that exist and mirror the FoundUp-creation audit required list.
FOUNDUP_ACCEPTANCE_TARGETS = [
    "WSP_framework/src/WSP_109_FoundUp_Onboarding_Intake_Protocol.md",
    "modules/communication/moltbot_bridge/src/openclaw_foundup_orchestrator.py",
    "modules/foundups/agent/src/hermes_foundup_job_executor.py",
    "modules/communication/moltbot_bridge/src/foundup_job_contract.py",
    "modules/communication/moltbot_bridge/src/reddog_governed_work_order_dryrun.py",
    "modules/communication/moltbot_bridge/src/reddog_wre_execution_valve.py",
    "modules/foundups/agent/src/source_authority.py",
]


def _rejected_reasons(telemetry: dict) -> dict:
    return {r["path"]: r["reason"] for r in telemetry.get("direct_read_rejected", [])}


def test_direct_read_deny_reason_lexical_gate():
    """Hard-deny + traversal + absolute rules are pure-lexical and testable."""
    assert _direct_read_deny_reason("../../etc/passwd") == "traversal"
    assert _direct_read_deny_reason("/etc/passwd") == "absolute_path"
    assert _direct_read_deny_reason("C:/Windows/system32/hosts") == "absolute_path"
    assert _direct_read_deny_reason(".env") == "denied_basename"
    assert _direct_read_deny_reason("modules/x/.env.local") == "denied_basename"
    assert _direct_read_deny_reason("certs/server.key") == "denied_extension"
    assert _direct_read_deny_reason("certs/server.pem") == "denied_extension"
    assert _direct_read_deny_reason("keys/store.keystore") == "denied_extension"
    assert _direct_read_deny_reason("home/id_rsa") == "denied_basename"
    assert _direct_read_deny_reason(".git/config") == "denied_segment"
    assert _direct_read_deny_reason("config/my_secret_thing.py") == "denied_secret_like"
    assert _direct_read_deny_reason("auth/access_token.json") == "denied_secret_like"
    assert _direct_read_deny_reason("vault/user_credential.yaml") == "denied_secret_like"
    # A benign in-repo source file passes the lexical gate.
    assert _direct_read_deny_reason("modules/foundups/agent/src/source_authority.py") is None


def test_direct_read_fetch_real_targets_present():
    """Acceptance: FoundUp required targets are fetched + present in bundle hits."""
    result = _direct_read_fetch(REPO_ROOT, FOUNDUP_ACCEPTANCE_TARGETS)
    tel = result["telemetry"]
    fetched = set(tel["direct_read_paths"])
    for target in FOUNDUP_ACCEPTANCE_TARGETS:
        assert target in fetched, f"required target not fetched: {target}"
    assert tel["direct_read_fallback_used"] is True
    assert tel["direct_read_rejected"] == []
    assert tel["direct_read_bytes"] > 0
    # Each fetched target is a content-bearing hit.
    hit_locs = {h["location"] for h in result["hits"]}
    for target in FOUNDUP_ACCEPTANCE_TARGETS:
        assert target in hit_locs
    for hit in result["hits"]:
        assert hit["direct_read"] is True
        assert isinstance(hit["content"], str) and hit["content"]


def test_direct_read_fetch_flips_recall_via_node():
    """Slice-2 bar: after the fetch, slice-1's recall reports satisfied."""
    if not _node_available():
        pytest.skip("node runtime required for evaluateTargetRecall")
    prompt = (
        "Audit the FoundUp creation monorepo WSP_109 execution path.\n\n"
        "Required direct-read targets:\n"
        + "".join("- " + t + "\n" for t in FOUNDUP_ACCEPTANCE_TARGETS)
        + "\nProduce required architect sections.\n"
    )
    # Pre-fetch: bundle has none of the targets => index gap.
    before = _run_target_recall(prompt, _hits("docs/unrelated_note.md"))
    assert before["index_gap_detected"] is True
    assert before["target_recall_ok"] is False
    # Fetch, then re-run recall on the now-present locations.
    result = _direct_read_fetch(REPO_ROOT, FOUNDUP_ACCEPTANCE_TARGETS)
    fetched_hits = [
        {"location": h["location"], "need": h["need"]} for h in result["hits"]
    ]
    after = _run_target_recall(prompt, fetched_hits)
    assert after["target_recall_ok"] is True, after
    assert after["index_gap_detected"] is False
    assert after["required_targets_recalled"] == len(FOUNDUP_ACCEPTANCE_TARGETS)
    assert after["required_targets_missing"] == []


def test_direct_read_traversal_rejected_bundle_still_returned():
    """Path traversal is rejected + recorded; bundle fetch still completes."""
    result = _direct_read_fetch(
        REPO_ROOT,
        ["../../etc/passwd", "..\\..\\windows\\system32\\config", "modules/foundups/agent/src/source_authority.py"],
    )
    tel = result["telemetry"]
    reasons = _rejected_reasons(tel)
    assert reasons.get("../../etc/passwd") == "traversal"
    assert reasons.get("../../windows/system32/config") == "traversal"
    # The benign target is still fetched (rejections do not abort the bundle).
    assert "modules/foundups/agent/src/source_authority.py" in tel["direct_read_paths"]


def test_direct_read_absolute_path_rejected():
    result = _direct_read_fetch(REPO_ROOT, ["/etc/passwd", "C:/Windows/System32/drivers/etc/hosts"])
    reasons = _rejected_reasons(result["telemetry"])
    assert reasons.get("/etc/passwd") == "absolute_path"
    assert reasons.get("C:/Windows/System32/drivers/etc/hosts") == "absolute_path"
    assert result["telemetry"]["direct_read_paths"] == []
    assert result["telemetry"]["direct_read_fallback_used"] is False


def test_direct_read_windows_namespace_and_ads_rejected(tmp_path):
    fake_root = tmp_path / "repo"
    fake_root.mkdir(parents=True)
    (fake_root / "safe.py:payload").write_text("SYNTHETIC-ADS-CONTENT\n", encoding="utf-8")
    targets = [
        r"\\server\share\source.py",
        r"\\?\C:\repo\source.py",
        "safe.py:payload",
    ]
    result = _direct_read_fetch(fake_root, targets)
    reasons = _rejected_reasons(result["telemetry"])
    assert reasons.get("//server/share/source.py") == "absolute_path"
    assert reasons.get("//?/C:/repo/source.py") == "absolute_path"
    assert reasons.get("safe.py:payload") == "alternate_data_stream"
    assert result["telemetry"]["direct_read_paths"] == []
    assert "SYNTHETIC-ADS-CONTENT" not in "\n".join(
        hit.get("content", "") for hit in result["hits"]
    )


def test_direct_read_secret_fixtures_never_read(tmp_path, monkeypatch):
    """.env and *.key synthetic fixtures are hard-denied and never read."""
    # Build a synthetic repo root so real repo secrets are never touched.
    fake_root = tmp_path / "repo"
    (fake_root / "modules").mkdir(parents=True)
    # Synthetic dummy secret values ONLY (never a real credential).
    (fake_root / ".env").write_text("DUMMY_TOKEN=synthetic-not-a-real-secret\n", encoding="utf-8")
    (fake_root / "server.key").write_text("-----BEGIN PRIVATE KEY-----\nSYNTHETIC-DUMMY\n-----END PRIVATE KEY-----\n", encoding="utf-8")
    (fake_root / "app_secret.py").write_text("VALUE = 'synthetic'\n", encoding="utf-8")
    (fake_root / "modules" / "ok.py").write_text("SAFE = True\n", encoding="utf-8")

    result = _direct_read_fetch(fake_root, [".env", "server.key", "app_secret.py", "modules/ok.py"])
    tel = result["telemetry"]
    reasons = _rejected_reasons(tel)
    assert reasons.get(".env") == "denied_basename"
    assert reasons.get("server.key") == "denied_extension"
    assert reasons.get("app_secret.py") == "denied_secret_like"
    # No secret content ever appears in any fetched hit.
    joined = "\n".join(h.get("content", "") for h in result["hits"])
    assert "synthetic-not-a-real-secret" not in joined
    assert "BEGIN PRIVATE KEY" not in joined
    # The one safe file is fetched.
    assert "modules/ok.py" in tel["direct_read_paths"]


def test_direct_read_per_file_cap_and_total_budget(tmp_path):
    """Many large targets: each is bounded and total budget is not blown on one."""
    fake_root = tmp_path / "repo"
    (fake_root / "src").mkdir(parents=True)
    # Create more-than-budget worth of large files so the spread matters.
    big = "X" * 40000  # 40KB each, well over the per-file cap.
    n_files = (DIRECT_READ_TOTAL_BUDGET_BYTES // DIRECT_READ_PER_FILE_BYTES) + 4
    targets = []
    for i in range(n_files):
        rel = f"src/big_{i}.py"
        (fake_root / rel).write_text(big, encoding="utf-8")
        targets.append(rel)

    result = _direct_read_fetch(fake_root, targets)
    tel = result["telemetry"]
    # No single fetched file exceeded the per-file cap.
    for hit in result["hits"]:
        assert hit["content_bytes"] <= DIRECT_READ_PER_FILE_BYTES, hit["location"]
    # Total injected bytes never exceed the total budget.
    assert tel["direct_read_bytes"] <= DIRECT_READ_TOTAL_BUDGET_BYTES
    # Budget was spread across MANY targets, not consumed by one.
    assert len(tel["direct_read_paths"]) > 1
    # Every fetched large file records a per-file truncation.
    truncated_paths = {t["path"] for t in tel["direct_read_truncated"]}
    for rel in tel["direct_read_paths"]:
        assert rel in truncated_paths


def test_direct_read_symlink_escape_rejected(tmp_path):
    """A symlink whose real target escapes the repo root is rejected."""
    fake_root = tmp_path / "repo"
    (fake_root).mkdir(parents=True)
    outside = tmp_path / "outside_secret.txt"
    outside.write_text("SYNTHETIC-outside-do-not-read\n", encoding="utf-8")
    link = fake_root / "escape_link.txt"
    try:
        os.symlink(outside, link)
    except (OSError, NotImplementedError):
        # Runner cannot create symlinks: assert the realpath containment unit
        # instead (equivalent guarantee: resolved real path must stay in root).
        real, reason = _resolve_within_repo(fake_root, "../outside_secret.txt")
        assert real is None
        assert reason in ("traversal", "outside_root", "path_missing")
        return
    result = _direct_read_fetch(fake_root, ["escape_link.txt"])
    tel = result["telemetry"]
    reasons = _rejected_reasons(tel)
    assert reasons.get("escape_link.txt") == "outside_root"
    joined = "\n".join(h.get("content", "") for h in result["hits"])
    assert "SYNTHETIC-outside-do-not-read" not in joined


# --- REDDOG_SYMBOL_AWARE_EXCERPT_DEPTH_PHASE1 (slice 3/3): symbol line windows ----------------
def _deep_symbol_repo(tmp_path):
    """A synthetic repo with a file whose symbol is defined DEEP past the 12KB head-clip."""
    fake_root = tmp_path / "repo"
    (fake_root / "src").mkdir(parents=True)
    rel = "src/hermes.py"
    head = "# header\n" + ("# filler padding padding padding padding padding\n" * 400)  # ~18KB head
    assert len(head.encode("utf-8")) > DIRECT_READ_PER_FILE_BYTES
    body = ("def build_foundup(job):\n    return extract_foundup(job)  # DEEP-DEF-MARKER\n"
            + ("# trailing filler\n" * 100))
    (fake_root / rel).write_text(head + body, encoding="utf-8")
    return fake_root, rel


def test_split_path_symbol_forms():
    assert _split_path_symbol("modules/x/y.py#build_foundup") == ("modules/x/y.py", "build_foundup")
    assert _split_path_symbol("modules/x/y.py") == ("modules/x/y.py", None)
    assert _split_path_symbol("notes#draft.md") == ("notes#draft.md", None)  # suffix not an identifier
    assert _split_path_symbol("a#b#c") == ("a#b#c", None)                    # ambiguous -> whole path
    # the symbol is opaque: an absolute/traversal PATH portion is preserved for the deny gate
    assert _split_path_symbol("/etc/passwd#foo") == ("/etc/passwd", "foo")
    assert _split_path_symbol("../../.env#foo") == ("../../.env", "foo")


def test_locate_symbol_line_prefers_definition_word_boundary():
    lines = [
        "import build_foundup_v2            # substring, NOT this",
        "x = build_foundup()                # a call-site (first occurrence)",
        "def extract_build_foundup(): pass  # substring, NOT this",
        "def build_foundup(job):            # THE definition",
        "    return job",
    ]
    assert _locate_symbol_line(lines, "build_foundup") == 3          # def preferred over call-site
    # word-boundary: a symbol only present as a substring is not matched
    assert _locate_symbol_line(["build_foundup_v2 = 1"], "build_foundup") is None
    # JS/TS style definitions
    assert _locate_symbol_line(["const buildFoundup = () => {}"], "buildFoundup") == 0
    assert _locate_symbol_line(["export function buildFoundup() {}"], "buildFoundup") == 0


def test_symbol_window_reaches_symbol_deep_past_head(tmp_path):
    """CORE FIX: a symbol defined past the 12KB head-clip reaches the model via a line window,
    while the plain path (head-clip) misses it."""
    fake_root, rel = _deep_symbol_repo(tmp_path)
    result = _direct_read_fetch(fake_root, [rel + "#build_foundup", rel])
    by_need = {h["need"]: h for h in result["hits"]}
    win = by_need["direct-read target: " + rel + "#build_foundup"]
    plain = by_need["direct-read target: " + rel]
    assert "DEEP-DEF-MARKER" in win["content"] and win["symbol"] == "build_foundup"
    assert win["content_bytes"] <= DIRECT_READ_PER_FILE_BYTES
    assert "DEEP-DEF-MARKER" not in plain["content"] and plain["symbol"] is None  # head-clip misses it
    assert {"path": rel, "symbol": "build_foundup"} in result["telemetry"]["direct_read_symbol_windows"]


def test_symbol_window_lead_context_included(tmp_path):
    """The window keeps a few lead lines (decorators/docstring) before the def and stays contiguous."""
    fake_root = tmp_path / "repo"
    (fake_root / "src").mkdir(parents=True)
    rel = "src/w.py"
    (fake_root / rel).write_text(
        "\n".join([f"# lead {i}" for i in range(20)] + ["@decorator", "def target(x):", "    return x"])
        + "\n", encoding="utf-8")
    r = _direct_read_fetch(fake_root, [rel + "#target"])
    content = r["hits"][0]["content"]
    assert "@decorator" in content and "def target(x):" in content
    assert "# lead 19" in content  # nearest lead line kept as context


def test_symbol_not_found_falls_back_to_head_clip(tmp_path):
    fake_root = tmp_path / "repo"
    (fake_root / "src").mkdir(parents=True)
    rel = "src/f.py"
    (fake_root / rel).write_text("def other():\n    return 1\n", encoding="utf-8")
    r = _direct_read_fetch(fake_root, [rel + "#nonexistent_symbol"])
    assert len(r["hits"]) == 1
    assert r["hits"][0]["content"].startswith("def other():")     # head-clip fallback
    assert r["hits"][0]["symbol"] is None                          # not a symbol window
    assert r["telemetry"]["direct_read_symbol_windows"] == []


def test_invalid_symbol_falls_back_to_head_clip(tmp_path):
    fake_root = tmp_path / "repo"
    (fake_root / "src").mkdir(parents=True)
    rel = "src/g.py"
    (fake_root / rel).write_text("def build_foundup():\n    return 1\n", encoding="utf-8")
    # a non-identifier suffix is not split as a symbol -> whole '#...' treated as a path -> not_a_file
    r = _direct_read_fetch(fake_root, [rel + "#not a valid symbol!"])
    assert r["telemetry"]["direct_read_symbol_windows"] == []


def test_symbol_split_does_not_bypass_security_deny(tmp_path):
    """The deny/containment gates run on the PATH portion only; a symbol suffix cannot smuggle a
    denied path past them."""
    fake_root = tmp_path / "repo"
    (fake_root / "src").mkdir(parents=True)
    (fake_root / ".env").write_text("DUMMY=synthetic-not-a-real-secret\n", encoding="utf-8")
    (fake_root / "src" / "ok.py").write_text("def build_foundup():\n    return 1\n", encoding="utf-8")
    r = _direct_read_fetch(fake_root, [".env#build_foundup", "/etc/passwd#x",
                                       "../../outside.py#y", "src/ok.py#build_foundup"])
    reasons = {t["path"]: t["reason"] for t in r["telemetry"]["direct_read_rejected"]}
    assert reasons.get(".env") == "denied_basename"
    assert reasons.get("/etc/passwd") == "absolute_path"
    assert reasons.get("../../outside.py") == "traversal"
    joined = "\n".join(h.get("content", "") for h in r["hits"])
    assert "synthetic-not-a-real-secret" not in joined            # denied file never read
    assert "def build_foundup():" in joined                        # the safe symbol target still fetched


def test_two_symbols_same_file_both_windowed(tmp_path):
    fake_root = tmp_path / "repo"
    (fake_root / "src").mkdir(parents=True)
    rel = "src/two.py"
    (fake_root / rel).write_text(
        "def build_foundup():\n    return 1\n\n\ndef extract_foundup():\n    return 2\n", encoding="utf-8")
    r = _direct_read_fetch(fake_root, [rel + "#build_foundup", rel + "#extract_foundup"])
    syms = {w["symbol"] for w in r["telemetry"]["direct_read_symbol_windows"]}
    assert syms == {"build_foundup", "extract_foundup"}
    assert len(r["hits"]) == 2
    for h in r["hits"]:
        assert h["location"] == rel                                # location stays the bare path


def test_case_distinct_symbols_same_file_both_windowed(tmp_path):
    """CoR R2 (major): case-differing symbols ('Config' class vs 'config' factory) are DISTINCT
    (matching is case-sensitive) and must each get their own window -- the dedup key must not
    lowercase the symbol."""
    fake_root = tmp_path / "repo"
    (fake_root / "src").mkdir(parents=True)
    rel = "src/c.py"
    (fake_root / rel).write_text(
        "class Config:  # UPPER-CONFIG-MARKER\n    pass\n\n\ndef config():  # lower-config-marker\n    return 1\n",
        encoding="utf-8")
    r = _direct_read_fetch(fake_root, [rel + "#Config", rel + "#config"])
    syms = {w["symbol"] for w in r["telemetry"]["direct_read_symbol_windows"]}
    assert syms == {"Config", "config"}
    joined = "\n".join(h["content"] for h in r["hits"])
    assert "UPPER-CONFIG-MARKER" in joined and "lower-config-marker" in joined


def test_symbol_window_binary_file_omitted(tmp_path):
    fake_root = tmp_path / "repo"
    (fake_root / "src").mkdir(parents=True)
    rel = "src/b.py"
    (fake_root / rel).write_bytes(b"def build_foundup():\x00\x01binary\n")
    r = _direct_read_fetch(fake_root, [rel + "#build_foundup"])
    assert r["hits"] == []
    reasons = {t["path"]: t["reason"] for t in r["telemetry"]["direct_read_rejected"]}
    assert reasons.get(rel) == "binary"


def test_symbol_window_oversized_def_line_falls_back_not_lead_only(tmp_path):
    """CoR R1 (blocker/major x3): a def line LONGER than the per-file cap must NOT ship lead-only
    context labeled as a successful symbol window (the symbol would be absent while recall reads as
    satisfied). It falls back to the head-clip and is NOT reported as a symbol window."""
    fake_root = tmp_path / "repo"
    (fake_root / "src").mkdir(parents=True)
    rel = "src/f.py"
    lead = "# leadA\n# leadB\n# leadC\n"
    big_def = "def build_foundup(" + ("a," * 7000) + "):  # DEEP-DEF-MARKER\n"  # >12KB single def line
    assert len(big_def.encode("utf-8")) > DIRECT_READ_PER_FILE_BYTES
    (fake_root / rel).write_text(lead + big_def + "    return 1\n", encoding="utf-8")
    # unit: the window read reports symbol_window_empty (def did not fit)
    snip = _read_symbol_window(fake_root / rel, "build_foundup", DIRECT_READ_PER_FILE_BYTES,
                               DIRECT_READ_TOTAL_BUDGET_BYTES)
    assert snip["omitted_reason"] == "symbol_window_empty"
    # end-to-end: falls back to head-clip, NOT a symbol window, and never ships lead-only content
    r = _direct_read_fetch(fake_root, [rel + "#build_foundup"])
    assert r["telemetry"]["direct_read_symbol_windows"] == []
    assert len(r["hits"]) == 1 and r["hits"][0]["symbol"] is None
    assert r["hits"][0]["content"].startswith("# leadA")  # deterministic head-clip, not lead-then-nothing


def test_symbol_fallback_head_clip_dedups_on_path_not_symbol(tmp_path):
    """CoR R3 (major): a symbol target that FALLS BACK to the head-clip produces path-based content;
    it must dedup on the bare path (colliding with the plain-path hit), not on (path, symbol) -- else
    the same head-clip is emitted twice and budget is double-charged."""
    fake_root = tmp_path / "repo"
    (fake_root / "src").mkdir(parents=True)
    rel = "src/f.py"
    (fake_root / rel).write_text("def other():\n    return 1\n", encoding="utf-8")
    r = _direct_read_fetch(fake_root, [rel + "#absent_symbol", rel])
    assert len(r["hits"]) == 1                                   # one head-clip, not two
    assert r["telemetry"]["direct_read_paths"] == [rel]          # not double-counted


def test_many_absent_symbols_one_file_cannot_blow_total_budget(tmp_path):
    """CoR R3 (major, amplification): many absent symbols of ONE big file must NOT each redraw a
    per-file cap and starve a distinct legitimate target of the total budget."""
    fake_root = tmp_path / "repo"
    (fake_root / "src").mkdir(parents=True)
    big = "src/big.py"
    (fake_root / big).write_text("# no matching symbols here\n" + ("X" * 60000), encoding="utf-8")
    (fake_root / "src" / "important.py").write_text("IMPORTANT-CONTENT = 1\n", encoding="utf-8")
    targets = [f"{big}#sym{i}" for i in range(40)] + ["src/important.py"]
    r = _direct_read_fetch(fake_root, targets)
    joined = "\n".join(h["content"] for h in r["hits"])
    assert "IMPORTANT-CONTENT" in joined                          # the legit distinct target still lands
    assert r["telemetry"]["direct_read_bytes"] <= DIRECT_READ_TOTAL_BUDGET_BYTES
    assert len({h["location"] for h in r["hits"]}) >= 2           # budget spread, not consumed by one file


def test_read_symbol_window_bounded_scan_cap(tmp_path):
    """A symbol beyond the scan cap is not located (bounded scan) -> omitted 'symbol_not_found',
    so a pathological file cannot force an unbounded read."""
    fake_root = tmp_path / "repo"
    (fake_root / "src").mkdir(parents=True)
    rel = "src/huge.py"
    filler = "# filler line to push the symbol beyond the scan cap zzzzzzzzzzzzzzzzzz\n"
    reps = (DIRECT_READ_SYMBOL_SCAN_BYTES // len(filler.encode("utf-8"))) + 50
    (fake_root / rel).write_text(filler * reps + "def build_foundup():\n    return 1\n", encoding="utf-8")
    real = fake_root / rel
    snip = _read_symbol_window(real, "build_foundup", DIRECT_READ_PER_FILE_BYTES, DIRECT_READ_TOTAL_BUDGET_BYTES)
    assert snip["omitted_reason"] == "symbol_not_found"


def test_direct_read_cli_end_to_end(monkeypatch):
    """--bundle-must-include fetches real targets into the CLI bundle JSON."""
    monkeypatch.chdir(REPO_ROOT)
    env = os.environ.copy()
    env["HOLO_SKIP_MODEL"] = "1"
    cli = [
        sys.executable,
        "-B",
        "holo_index.py",
        "--bundle-json",
        "--search",
        "Audit FoundUp creation monorepo WSP_109 execution path",
        "--limit",
        "5",
        "--quiet-root-alerts",
    ]
    for target in FOUNDUP_ACCEPTANCE_TARGETS:
        cli += ["--bundle-must-include", target]
    # Include a hard-deny + traversal to prove they are rejected, not read.
    cli += ["--bundle-must-include", ".env", "--bundle-must-include", "../../etc/passwd"]
    proc = subprocess.run(cli, cwd=REPO_ROOT, env=env, capture_output=True, text=True, check=True)
    bundle = json.loads(proc.stdout.strip())
    assert bundle.get("ok") is True
    dr = bundle.get("direct_read") or {}
    assert dr.get("direct_read_fallback_used") is True
    fetched = set(dr.get("direct_read_paths") or [])
    for target in FOUNDUP_ACCEPTANCE_TARGETS:
        assert target in fetched, f"CLI did not fetch {target}"
    reasons = {r["path"]: r["reason"] for r in dr.get("direct_read_rejected", [])}
    assert reasons.get(".env") == "denied_basename"
    assert reasons.get("../../etc/passwd") == "traversal"
    # Fetched content is spliced into code_hits as direct-read hits.
    dr_hits = [h for h in (bundle["task_retrieval"]["code_hits"]) if h.get("direct_read")]
    dr_hit_locs = {h["location"] for h in dr_hits}
    for target in FOUNDUP_ACCEPTANCE_TARGETS:
        assert target in dr_hit_locs
