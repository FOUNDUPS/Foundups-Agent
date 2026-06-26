#!/usr/bin/env python3
"""Regression tests for RedDog extension / bridge bundle-json recall."""

import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from holo_index.cli.commands.bundle_json import _lexical_task_retrieval, _resolve_module_dir


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
