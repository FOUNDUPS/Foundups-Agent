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

from holo_index.cli.commands.bundle_json import _lexical_task_retrieval, _resolve_module_dir

EXTENSION_JS = REPO_ROOT / "extensions" / "foundups_advisory_workers" / "extension.js"

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
        "const extDir=path.join(root,'extensions','foundups_advisory_workers');"
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


@pytest.fixture
def ssd_path():
    return os.environ.get("HOLO_SSD_PATH", str(REPO_ROOT / "holo_index" / "ssd"))


def test_extension_js_in_top_hits_for_review_query(ssd_path):
    module_dir = _resolve_module_dir(REPO_ROOT, "extensions/foundups_advisory_workers")
    payload = _lexical_task_retrieval(
        REPO_ROOT,
        "Review extensions/foundups_advisory_workers/extension.js for WSP_97",
        5,
        ssd_path,
        module_dir=module_dir,
    )
    locs = _code_locations(payload)
    assert "extensions/foundups_advisory_workers/extension.js" in locs[:3]


def test_buildcopymarkdown_query_surfaces_extension_js(ssd_path):
    module_dir = _resolve_module_dir(REPO_ROOT, "extensions/foundups_advisory_workers")
    payload = _lexical_task_retrieval(
        REPO_ROOT,
        "buildCopyMarkdown Copy MD Run Trace Redaction Gate Report",
        5,
        ssd_path,
        module_dir=module_dir,
    )
    locs = _code_locations(payload)
    assert "extensions/foundups_advisory_workers/extension.js" in locs[:3]


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
            "Review extensions/foundups_advisory_workers/extension.js for WSP_97",
            "--bundle-module-hint",
            "extensions/foundups_advisory_workers",
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
    locs = _code_locations(bundle.get("task_retrieval") or {})
    assert bundle.get("ok") is True
    assert "extensions/foundups_advisory_workers/extension.js" in locs[:3]


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
        _hits("extensions/foundups_advisory_workers/extension.js"),
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
        "Review extensions/foundups_advisory_workers/extension.js for WSP_97",
        _hits("extensions/foundups_advisory_workers/extension.js"),
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
