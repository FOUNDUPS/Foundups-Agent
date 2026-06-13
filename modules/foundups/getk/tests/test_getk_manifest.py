#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GetK manifest + registry-entry contract tests."""

from __future__ import annotations

import json
from pathlib import Path

from modules.foundups.agent.src.foundup_manifest_validator import (
    validate_manifest_file,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
MANIFEST = REPO_ROOT / "modules/foundups/getk/foundup_manifest.json"
REGISTRY = REPO_ROOT / "modules/foundups/foundup_registry.json"


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _registry_entry() -> dict:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    entries = [e for e in data["entities"] if e["foundup_id"] == "getk"]
    assert len(entries) == 1, "exactly one getk registry entry expected"
    return entries[0]


# --- manifest validates against the #771/#773 validator ----------------------

def test_getk_manifest_validates():
    result = validate_manifest_file(MANIFEST)
    assert result.ok, result.errors


def test_getk_manifest_identity_and_path():
    m = _manifest()
    assert m["foundup_id"] == "getk"
    assert m["build_contract"]["foundup_id"] == "getk"
    assert m["build_contract"]["module_path"] == "modules/foundups/getk"


def test_getk_readiness_flags_all_false():
    r = _manifest()["build_contract"]["readiness"]
    assert r["manifest_ready"] is False
    assert r["build_ready"] is False
    assert r["autonomous_execution_ready"] is False


def test_getk_execution_routing_locked_down():
    er = _manifest()["execution_routing"]
    assert er["external_agent_allowed"] is False
    assert er["declarative_only"] is True
    assert er["can_self_authorize"] is False


def test_getk_dry_run_default_true():
    assert _manifest()["build_contract"]["dry_run"]["default"] is True


def test_getk_forbidden_paths_cover_main_dae_secrets_registry():
    fp = _manifest()["build_contract"]["forbidden_paths"]
    assert "main.py" in fp
    assert any("_dae.py" in p for p in fp)
    assert any("secrets" in p for p in fp)
    assert any("foundup_registry.json" in p for p in fp)


# --- registry entry resolves + utility-only token boundary -------------------

def test_getk_registry_entry_resolves():
    e = _registry_entry()
    assert e["entity_type"] == "foundup"
    assert e["module_path"] == "modules/foundups/getk"
    assert e["manifest_path"] == "modules/foundups/getk/foundup_manifest.json"
    assert e["manifest_status"] == "exists"
    assert e["stage"] == "incubating"
    assert e["tier"] == "F0_DAE"


def test_getk_registry_no_overclaim():
    e = _registry_entry()
    # Scaffold-only: must NOT claim proto/mvp/launch maturity.
    assert e["implementation_status"] == "SPECIFIED"
    assert e["poc_status"] in ("idea", "poc")
    assert e["prototype_gate_status"] != "passed"
    assert e["portfolio_ready"] is False


def test_getk_token_is_utility_deferred_not_exists():
    e = _registry_entry()
    # Token is utility-only and deferred -- never asserted as an existing asset.
    assert e["token_status"] == "TOKEN_DEFERRED"
    assert e["token_symbol"] == "GETK"


def test_getk_manifest_and_registry_agree_on_module_path():
    assert _manifest()["build_contract"]["module_path"] == _registry_entry()["module_path"]
