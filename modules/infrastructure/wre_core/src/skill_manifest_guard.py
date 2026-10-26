#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Skill manifest integrity verification (hash + optional signature)."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Dict, List, Optional, Tuple

from modules.infrastructure.wre_core.src.skill_path_security import (
    absolute_unresolved as _absolute_unresolved,
    has_link_or_reparse_component as _has_link_or_reparse_component,
    path_has_link_or_reparse as _path_has_link_or_reparse,
)


@dataclass
class SkillManifestResult:
    available: bool
    passed: bool
    manifest_path: Optional[str]
    message: str
    checked_files: int = 0
    missing_files: List[str] = field(default_factory=list)
    mismatched_files: List[str] = field(default_factory=list)
    unexpected_files: List[str] = field(default_factory=list)
    signature_verified: bool = False


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _collect_skill_docs(skills_dir: Path) -> List[Path]:
    files: List[Path] = []
    for pattern in ("**/SKILL.md", "**/SKILLz.md", "**/executor.py"):
        files.extend(skills_dir.glob(pattern))
    return sorted(set(files), key=lambda path: path.as_posix())


def _canonical_signature_payload(entries: List[Tuple[str, str]]) -> str:
    lines = [f"{path}:{sha}" for path, sha in sorted(entries)]
    return "\n".join(lines)


def _manifest_under_root(skills_dir: Path, manifest_path: Optional[Path]) -> Path:
    raw = manifest_path or (skills_dir / "SKILL_MANIFEST.json")
    raw = raw if raw.is_absolute() else skills_dir / raw
    if _has_link_or_reparse_component(skills_dir, raw):
        raise ValueError("manifest path is outside, linked, or reparsed")
    resolved = raw.resolve()
    resolved.relative_to(skills_dir)
    return resolved


def _failure(
    manifest_path: Path,
    message: str,
    *,
    available: bool = True,
    checked_files: int = 0,
    missing_files: Optional[List[str]] = None,
    mismatched_files: Optional[List[str]] = None,
    unexpected_files: Optional[List[str]] = None,
) -> SkillManifestResult:
    return SkillManifestResult(
        available=available,
        passed=False,
        manifest_path=str(manifest_path),
        message=message,
        checked_files=checked_files,
        missing_files=missing_files or [],
        mismatched_files=mismatched_files or [],
        unexpected_files=unexpected_files or [],
        signature_verified=False,
    )


def _load_expected_entries(
    manifest_path: Path, required: bool
) -> tuple[Optional[Dict], Dict[str, str], Optional[SkillManifestResult]]:
    if not manifest_path.exists():
        missing = SkillManifestResult(
            available=False,
            passed=not required,
            manifest_path=str(manifest_path),
            message="manifest not found",
        )
        return None, {}, missing
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None, {}, _failure(manifest_path, "manifest parse failed")
    if not isinstance(payload, dict) or not isinstance(payload.get("files"), list):
        return None, {}, _failure(manifest_path, "manifest missing files list")
    expected: Dict[str, str] = {}
    for entry in payload["files"]:
        if not isinstance(entry, dict):
            return None, {}, _failure(manifest_path, "manifest contains invalid entry")
        rel = entry.get("path")
        sha = entry.get("sha256")
        if not _valid_manifest_entry(rel, sha) or rel in expected:
            return None, {}, _failure(manifest_path, "manifest contains invalid entry")
        expected[rel] = sha.lower()
    if not expected:
        return None, {}, _failure(manifest_path, "manifest contains no valid entries")
    return payload, expected, None


def _valid_manifest_entry(relative: object, digest: object) -> bool:
    if not isinstance(relative, str) or not relative.strip():
        return False
    if not isinstance(digest, str) or len(digest) != 64:
        return False
    return all(character in "0123456789abcdefABCDEF" for character in digest)


def _collect_file_evidence(
    skills_dir: Path, expected: Dict[str, str], allow_extra: bool
) -> tuple[List[str], List[str], List[str], List[Tuple[str, str]]]:
    missing: List[str] = []
    mismatched: List[str] = []
    tuples: List[Tuple[str, str]] = []
    for rel, expected_sha in expected.items():
        raw_path = _safe_manifest_entry_path(skills_dir, rel)
        if raw_path is None:
            mismatched.append(rel)
            continue
        if not raw_path.is_file():
            missing.append(rel)
            continue
        try:
            actual_sha = _sha256(raw_path)
        except OSError:
            mismatched.append(rel)
            continue
        tuples.append((rel, actual_sha))
        if actual_sha.lower() != expected_sha:
            mismatched.append(rel)
    unexpected = [] if allow_extra else _unexpected_files(skills_dir, expected)
    return missing, mismatched, unexpected, tuples


def _safe_manifest_entry_path(skills_dir: Path, relative: str) -> Optional[Path]:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts or "\\" in relative:
        return None
    raw_path = skills_dir / Path(*pure.parts)
    if _has_link_or_reparse_component(skills_dir, raw_path):
        return None
    resolved = raw_path.resolve()
    try:
        resolved.relative_to(skills_dir)
    except ValueError:
        return None
    return resolved


def _unexpected_files(skills_dir: Path, expected: Dict[str, str]) -> List[str]:
    listed = set(expected)
    return [
        path.relative_to(skills_dir).as_posix()
        for path in _collect_skill_docs(skills_dir)
        if path.relative_to(skills_dir).as_posix() not in listed
    ]


def _signature_failure(
    payload: Dict,
    tuples: List[Tuple[str, str]],
    hmac_key: Optional[str],
    manifest_path: Path,
    evidence: tuple[List[str], List[str], List[str]],
) -> Optional[SkillManifestResult]:
    sig_obj = payload.get("signature")
    if not isinstance(sig_obj, dict):
        return _failure_with_evidence(
            manifest_path,
            "signature missing or unsupported algorithm",
            evidence,
            len(payload["files"]),
        )
    algorithm = sig_obj.get("algorithm")
    signature = sig_obj.get("value")
    if algorithm != "hmac-sha256" or not isinstance(signature, str):
        return _failure_with_evidence(
            manifest_path,
            "signature missing or unsupported algorithm",
            evidence,
            len(payload["files"]),
        )
    if not hmac_key:
        return _failure_with_evidence(
            manifest_path,
            "signature verification requested but HMAC key missing",
            evidence,
            len(payload["files"]),
        )
    computed = hmac.new(
        hmac_key.encode("utf-8"),
        _canonical_signature_payload(tuples).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(computed, signature.lower()):
        return _failure_with_evidence(
            manifest_path,
            "signature verification failed",
            evidence,
            len(payload["files"]),
        )
    return None


def _failure_with_evidence(
    manifest_path: Path,
    message: str,
    evidence: tuple[List[str], List[str], List[str]],
    checked_files: int,
) -> SkillManifestResult:
    missing, mismatched, unexpected = evidence
    return _failure(
        manifest_path,
        message,
        checked_files=checked_files,
        missing_files=missing,
        mismatched_files=mismatched,
        unexpected_files=unexpected,
    )


def generate_skill_manifest(
    skills_dir: Path,
    *,
    manifest_path: Optional[Path] = None,
    hmac_key: Optional[str] = None,
) -> Dict:
    """Generate manifest payload for workspace skills."""
    raw_skills_dir = _absolute_unresolved(skills_dir)
    if _path_has_link_or_reparse(raw_skills_dir):
        raise ValueError("Skill manifest root cannot be linked or reparsed")
    skills_dir = raw_skills_dir.resolve()
    docs = _collect_skill_docs(skills_dir)
    files = []
    tuples: List[Tuple[str, str]] = []
    for p in docs:
        if _has_link_or_reparse_component(skills_dir, p):
            raise ValueError("Skill manifest cannot include links or reparse points")
        rel = p.relative_to(skills_dir).as_posix()
        sha = _sha256(p)
        files.append({"path": rel, "sha256": sha})
        tuples.append((rel, sha))

    payload: Dict[str, object] = {"version": 1, "files": files}
    if hmac_key:
        canonical = _canonical_signature_payload(tuples)
        sig = hmac.new(
            hmac_key.encode("utf-8"),
            canonical.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        payload["signature"] = {"algorithm": "hmac-sha256", "value": sig}

    if manifest_path:
        output_path = _manifest_under_root(skills_dir, manifest_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def verify_skill_manifest(
    skills_dir: Path,
    *,
    manifest_path: Optional[Path] = None,
    required: bool = True,
    verify_signature: bool = False,
    hmac_key: Optional[str] = None,
    allow_extra: bool = False,
) -> SkillManifestResult:
    """Verify workspace skill files against signed hash manifest."""
    raw_skills_dir = _absolute_unresolved(skills_dir)
    if _path_has_link_or_reparse(raw_skills_dir):
        return _failure(raw_skills_dir, "skill root is linked or reparsed")
    skills_dir = raw_skills_dir.resolve()
    try:
        manifest_path = _manifest_under_root(skills_dir, manifest_path)
    except ValueError:
        return _failure(skills_dir / "SKILL_MANIFEST.json", "manifest path is outside, linked, or reparsed")
    payload, expected, load_failure = _load_expected_entries(manifest_path, required)
    if load_failure is not None or payload is None:
        return load_failure
    missing, mismatched, unexpected, tuples = _collect_file_evidence(
        skills_dir, expected, allow_extra
    )
    evidence = (missing, mismatched, unexpected)
    if verify_signature:
        signature_failure = _signature_failure(
            payload, tuples, hmac_key, manifest_path, evidence
        )
        if signature_failure is not None:
            return signature_failure
    passed = not any(evidence)
    message = "manifest verified" if passed else "manifest verification failed"
    return SkillManifestResult(
        available=True,
        passed=passed,
        manifest_path=str(manifest_path),
        message=message,
        checked_files=len(expected),
        missing_files=missing,
        mismatched_files=mismatched,
        unexpected_files=unexpected,
        signature_verified=verify_signature,
    )
