#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FoundUp scaffold dry-run materializer (FOUNDUP_SCAFFOLD_WRITER_DRYRUN_PHASE1).

Takes a FoundUpScaffoldContract (from create_foundup_dryrun.plan_create_foundup_dry_run)
and MATERIALIZES the planned WSP-49 artifacts into an ISOLATED sandbox path only.
It proves the writer can emit the exact planned artifact set, while fail-closing on
every unsafe target. It is NOT the live writer.

Contract: docs/audits/architecture/FOUNDUP_SCAFFOLD_CONTRACT_PHASE1.md

Boundary (fail closed):
    - Writes ONLY under a caller-supplied sandbox `output_root` that MUST be OUTSIDE
      the real repo. Any output_root inside the repo -> FAIL_WRITE_TO_MAIN_REPO.
    - NEVER writes the registry (foundup_registry.json) -> FAIL_REGISTRY_OVERWRITE;
      registry_mutated stays False.
    - Rejects path traversal, denied paths, and an already-existing real module.
    - NO branch/worktree creation. NO Hermes real-write path (AST-guarded).
    - The LIVE writer (modules/foundups/agent/src/foundup_scaffold_writer.py) remains
      forbidden until FOUNDUP_SCAFFOLD_WRITER (valve-gated) -- this module is dry-run only.

NAVIGATION:
    -> Consumes: create_foundup_dryrun.CreateFoundUpPlanResult.scaffold_contract
    -> Uses (lazy, validation only): foundup_manifest_validator (read-only)
    -> Does NOT import Hermes/FAM/launch/consumer (AST-guarded by tests).
"""

from __future__ import annotations

import fnmatch
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

REGISTRY_FILENAME = "foundup_registry.json"
_FOUNDUP_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,49}$")  # WSP 104
# Leading whitespace and trailing whitespace/dots per Win32 write semantics.
_LEAD_STRIP = " 	"
_TRAIL_STRIP = " .	"


def _norm_seg(seg: str) -> str:
    """Normalize a path segment the way Win32 resolves it for a write: strip
    LEADING whitespace and TRAILING whitespace/dots. Leading dots are PRESERVED
    (dotfiles like .env are real names) so denied/registry comparisons see the
    true basename."""
    return seg.lstrip(_LEAD_STRIP).rstrip(_TRAIL_STRIP)


@dataclass
class ScaffoldWriteResult:
    """Return-value-only dry-run sandbox materialization result."""

    ok: bool
    rejection_code: Optional[str]
    rejection_reason: Optional[str]
    output_root: Optional[str]
    files_written: List[str]           # absolute sandbox paths actually written
    relative_artifacts: List[str]      # module-relative artifact paths materialized
    matches_plan: bool
    materialized: bool
    dry_run_sandbox: bool = True
    wrote_to_main_repo: bool = False
    registry_mutated: bool = False
    worktree_created: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "rejection_code": self.rejection_code,
            "rejection_reason": self.rejection_reason,
            "output_root": self.output_root,
            "files_written": self.files_written,
            "relative_artifacts": self.relative_artifacts,
            "matches_plan": self.matches_plan,
            "materialized": self.materialized,
            "dry_run_sandbox": self.dry_run_sandbox,
            "wrote_to_main_repo": self.wrote_to_main_repo,
            "registry_mutated": self.registry_mutated,
            "worktree_created": self.worktree_created,
        }


# Always-enforced denied markers (NOT trusted to the contract). Case-insensitive.
_HARDCODED_DENIED = (".env", "main.py", "**/*_dae.py", "vendor")


def _default_repo_root() -> Path:
    # This file is modules/foundups/agent/src/scaffold_writer_dryrun.py -- 5 levels
    # below the repo root, so the repo root is parents[4] (src/agent/foundups/modules/<repo>).
    root = Path(__file__).resolve().parents[4]
    # Fail closed if the layout ever changes and this stops pointing at the repo root.
    if not (root / "WSP_framework").exists() and not (root / ".git").exists():
        raise RuntimeError(
            "scaffold_writer_dryrun: repo-root sentinel missing; refusing (fail-closed)"
        )
    return root


def _is_inside(child: Path, parent: Path) -> bool:
    child = child.resolve()
    parent = parent.resolve()
    return child == parent or parent in child.parents


def _is_denied(artifact: str, denied: List[str]) -> bool:
    # Case-insensitive (Windows/NTFS treats .ENV == .env); trailing spaces/dots
    # stripped per segment (Win32 strips them on write).
    norm = artifact.replace("\\", "/").lower()
    segs = [_norm_seg(s) for s in norm.split("/")]
    base = segs[-1] if segs else ""
    if base in (".env", "main.py"):
        return True
    if base.endswith("_dae.py"):
        return True
    if "vendor" in segs:
        return True
    # Union the hardcoded denials with any contract-supplied ones (do not trust the
    # contract to supply them); all lowercased.
    for pat in set(_HARDCODED_DENIED) | set(denied or []):
        p = pat.replace("\\", "/").lower().lstrip("*/")
        if p and (fnmatch.fnmatch(base, p) or fnmatch.fnmatch(norm, "*" + p)):
            return True
    return False


def _content_for(artifact: str, contract: Dict[str, Any]) -> str:
    """Deterministic WSP-49-shaped content for a single artifact."""
    fid = contract.get("foundup_id", "")
    name = contract.get("display_name", fid)
    module_path = contract.get("module_path", "")
    base = artifact.replace("\\", "/").rsplit("/", 1)[-1]

    if base == REGISTRY_FILENAME:
        # Should never reach here (rejected earlier); belt-and-braces.
        return ""
    if base == "foundup_manifest.json":
        return json.dumps(contract.get("manifest_fields", {}), indent=2, sort_keys=True) + "\n"
    if base == "__init__.py":
        return f"# {fid} package (genesis scaffold)\n"
    if base == "requirements.txt":
        return f"# {name} dependencies (genesis; none yet)\n"
    if base == "README.md" and artifact.replace("\\", "/").endswith(f"{module_path}/README.md"):
        return (
            f"# {name}\n\n> {contract.get('display_name', '')}\n\n"
            f"Genesis scaffold (dry-run materialization). Stage: incubating; Tier: F0_DAE.\n"
        )
    if base == "INTERFACE.md":
        return f"# {name} - INTERFACE (WSP 11)\n\nPublic API: TBD (genesis scaffold).\n"
    if base == "ROADMAP.md":
        return f"# {name} - ROADMAP\n\n## Genesis\n\n- POC scope derived from the WSP 109 intake packet.\n"
    if base == "ModLog.md":
        return (
            f"# {name} - ModLog\n\n## Genesis ({fid})\n\n"
            "Scaffold materialized in a dry-run sandbox from a FoundUpScaffoldContract. "
            "No live repo/registry write occurred.\n"
        )
    if base == "TestModLog.md":
        return f"# {name} - TestModLog\n\n## Genesis\n\n- Acceptance criteria seeded from the genesis envelope.\n"
    if base == "README.md":  # tests/README.md
        return f"# {name} Tests\n"
    if artifact.replace("\\", "/").endswith("/memory/README.md"):
        return f"# {name} Memory (WSP 60)\n\nModule memory directory. Data organization: TBD.\n"
    if base == f"{fid}.py":
        return f'"""{name} entrypoint (genesis scaffold)."""\n'
    if base == f"test_{fid}.py":
        return "def test_smoke():\n    assert True\n"
    return ""


def materialize_scaffold_dry_run(
    contract: Dict[str, Any],
    output_root: Path,
    *,
    real_repo_root: Optional[Path] = None,
) -> ScaffoldWriteResult:
    """Materialize the contract's scaffold artifacts into a sandbox (dry-run).

    Args:
        contract: a FoundUpScaffoldContract dict (from the create_foundup planner).
        output_root: an isolated sandbox directory OUTSIDE the real repo.
        real_repo_root: the real repo root (defaults to the actual repo) -- used to
            reject writes inside it and to detect an already-existing module.

    Returns:
        ScaffoldWriteResult with the written sandbox files, or a fail-closed rejection.
    """
    def _reject(code: str, reason: str) -> ScaffoldWriteResult:
        return ScaffoldWriteResult(
            ok=False, rejection_code=code, rejection_reason=reason[:300],
            output_root=str(output_root) if output_root is not None else None,
            files_written=[], relative_artifacts=[], matches_plan=False, materialized=False,
        )

    if not isinstance(contract, dict):
        return _reject("FAIL_CONTRACT_INVALID", "contract must be a dict")
    artifacts = contract.get("scaffold_artifacts")
    module_path = contract.get("module_path")
    if not isinstance(artifacts, list) or not artifacts:
        return _reject("FAIL_CONTRACT_INVALID", "contract.scaffold_artifacts missing/empty")
    if not isinstance(module_path, str) or not module_path:
        return _reject("FAIL_CONTRACT_INVALID", "contract.module_path missing")
    if output_root is None:
        return _reject("FAIL_CONTRACT_INVALID", "output_root (sandbox) is required")

    # Pin foundup_id + module_path to the canonical derivation. A hand-built contract
    # cannot inject a traversal/absolute module_path or a bogus id.
    foundup_id = str(contract.get("foundup_id", ""))
    if not _FOUNDUP_ID_RE.match(foundup_id):
        return _reject("FAIL_CONTRACT_INVALID", "foundup_id is not a valid WSP-104 token")
    if module_path != f"modules/foundups/{foundup_id}":
        return _reject(
            "FAIL_CONTRACT_INVALID",
            "module_path must be exactly modules/foundups/{foundup_id}",
        )

    # Reject Windows device / extended-length prefixes (\\?\ , \\.\ , //?/ , //./ ,
    # and \\?\UNC\ which begins with \\?\) BEFORE resolving/comparing. They disable
    # Win32 normalization, so .resolve() keeps a distinct anchor and an output_root
    # physically INSIDE the repo would evade the _is_inside isolation guard below.
    _raw_out = str(output_root)
    _res_out = str(Path(output_root).resolve())
    for _dp in ("\\\\?\\", "\\\\.\\", "//?/", "//./"):
        if _raw_out.startswith(_dp) or _res_out.startswith(_dp):
            return _reject(
                "FAIL_WRITE_TO_MAIN_REPO",
                "output_root uses an extended-length/device prefix; forbidden (isolation)",
            )

    out_r = Path(output_root).resolve()
    # Anchor on the sentinel-checked TRUE repo root AND any caller-supplied repo:
    # a caller cannot NARROW the forbidden zone by lying about real_repo_root.
    repos = {_default_repo_root().resolve()}
    if real_repo_root is not None:
        repos.add(Path(real_repo_root).resolve())

    # Guard 0: output_root must be a real, non-root directory (positive sandbox proof).
    if out_r == Path(out_r.anchor) or out_r.parent == out_r:
        return _reject(
            "FAIL_WRITE_TO_MAIN_REPO",
            "output_root is a filesystem/drive root; a genuine isolated sandbox is required",
        )

    # Guard 1: sandbox-only -- output_root must be OUTSIDE every repo root in BOTH
    # directions (not inside/equal to a repo, and no repo inside output_root).
    for repo_r in repos:
        if _is_inside(out_r, repo_r) or _is_inside(repo_r, out_r):
            return _reject(
                "FAIL_WRITE_TO_MAIN_REPO",
                "output_root is inside, equal to, or an ancestor of a real repo; "
                "dry-run writer requires an isolated sandbox outside the repo",
            )

    # Guard 2: an existing real module MUST NOT be clobbered by a create (every repo).
    for repo_r in repos:
        if (repo_r / module_path).exists():
            return _reject(
                "FAIL_MODULE_EXISTS",
                "target module_path already exists in a real repo; create_foundup authors NEW",
            )

    denied = contract.get("denied_paths", [])
    reg_lower = REGISTRY_FILENAME.lower()

    # Guard 3: per-artifact safety checks (ALL run BEFORE any write).
    for art in artifacts:
        norm = str(art).replace("\\", "/")
        if norm.startswith("/"):
            return _reject("FAIL_PATH_TRAVERSAL", "artifact path is absolute")
        segments = norm.split("/")
        for seg in segments:
            # No drive letter or NTFS alternate-data-stream colon in a module-relative artifact.
            if ":" in seg:
                return _reject("FAIL_PATH_TRAVERSAL", "artifact segment contains a ':' (drive/ADS)")
            # Strip BOTH ends (Win32 strips trailing space/dot; leading defensively).
            s = _norm_seg(seg)
            if s in ("", ".."):
                return _reject("FAIL_PATH_TRAVERSAL", "artifact segment is empty, '.', or '..'")
        target = (out_r / norm).resolve()
        if not _is_inside(target, out_r):
            return _reject("FAIL_PATH_TRAVERSAL", "artifact resolves outside the sandbox root")
        # Registry check: normalized (both-ends strip, lowercased) on EVERY segment.
        if any(_norm_seg(seg).lower() == reg_lower for seg in segments):
            return _reject("FAIL_REGISTRY_OVERWRITE", "artifact targets the FoundUp registry file")
        if _is_denied(norm, denied):
            return _reject("FAIL_DENIED_PATH", "artifact matches a denied path marker")

    # Guard 4: EXACT artifact set -- must equal the canonical WSP-49 plan (no extras/missing).
    # Binds the writer to the create_foundup planner's set; a hand-built contract with a
    # different artifact set is rejected rather than materialized.
    from modules.foundups.agent.src.create_foundup_dryrun import _wsp49_artifacts

    expected = _wsp49_artifacts(module_path, str(contract.get("foundup_id", "")))
    if sorted(str(a).replace("\\", "/") for a in artifacts) != sorted(expected):
        return _reject(
            "FAIL_ARTIFACT_SET_MISMATCH",
            "scaffold_artifacts does not equal the canonical WSP-49 set for this foundup_id",
        )

    # All guards passed -> materialize into the sandbox.
    written: List[str] = []
    for art in artifacts:
        norm = str(art).replace("\\", "/")
        target = out_r / norm
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_content_for(norm, contract), encoding="utf-8")
        written.append(str(target))

    relative = [str(a).replace("\\", "/") for a in artifacts]
    # matches_plan is a REAL on-disk proof: enumerate the sandbox and compare the
    # actual files to the canonical expected set (not just the requested list).
    on_disk = sorted(
        str(p.relative_to(out_r)).replace("\\", "/")
        for p in out_r.rglob("*") if p.is_file()
    )
    matches = on_disk == sorted(expected)

    return ScaffoldWriteResult(
        ok=True, rejection_code=None, rejection_reason=None,
        output_root=str(out_r), files_written=written, relative_artifacts=relative,
        matches_plan=matches, materialized=True,
    )
