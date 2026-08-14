"""Adversarial tests for exact-Git grant-service archive provenance."""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_archive_contract import (
    ARCHIVE_MAIN,
    ARCHIVE_MANIFEST,
    build_grant_service_archive,
    canonical_archive_bytes,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_git_archive_contract import (
    ARCHIVE_SCHEMA_V2,
    build_git_provenance_grant_service_archive,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_archive_validation import (
    validate_grant_service_archive,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_git_archive_builder import (
    build_grant_service_archive_from_git,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_git_archive_validation import (
    validate_grant_service_archive_git_provenance,
)
from modules.communication.moltbot_bridge.src.reddog_grant_authority_service_git_source_policy import (
    grant_service_git_source_policy_digest,
)
from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import (
    RuntimeArtifactManifestError,
    raw_digest,
)
from modules.infrastructure.wre_core.src.wre_git_bounded_io import (
    read_exact_git_blob,
)
from modules.infrastructure.wre_core.src.wre_git_tree_manifest import (
    exact_git_tree_manifest,
)

SERVICE = (
    b"import argparse\n"
    b"from helpers.runtime import status\n\n"
    b"def main(argv=None):\n"
    b"    argparse.ArgumentParser().parse_args(argv)\n"
    b"    return status()\n"
)
SOURCES = {
    "reddog_grant_authority_service.py": "service/reddog_grant_authority_service.py",
    "helpers/__init__.py": "service/helpers/__init__.py",
    "helpers/runtime.py": "service/helpers/runtime.py",
}


def test_exact_git_archive_round_trip(tmp_path: Path) -> None:
    repo, sha = _repository(tmp_path)
    archive = _build(repo, sha)
    manifest = _verify(archive, repo, sha)

    assert manifest["schema_version"] == ARCHIVE_SCHEMA_V2
    assert manifest["source_commit_sha"] == sha
    assert manifest["source_object_format"] == "sha1"
    with pytest.raises(RuntimeArtifactManifestError, match="manifest_invalid"):
        validate_grant_service_archive(archive)


def test_dirty_checkout_cannot_change_exact_commit_archive(tmp_path: Path) -> None:
    repo, sha = _repository(tmp_path)
    first = _build(repo, sha)
    (repo / SOURCES["reddog_grant_authority_service.py"]).write_bytes(
        b"raise RuntimeError('working tree attacker')\n"
    )
    second = _build(repo, sha)

    assert second == first
    _verify(second, repo, sha)


def test_legacy_claimed_commit_is_not_git_provenance(tmp_path: Path) -> None:
    repo, sha = _repository(tmp_path)
    archive = build_grant_service_archive(
        {"__main__.py": ARCHIVE_MAIN,
         "reddog_grant_authority_service.py": b"def main():\n    return 2\n"},
        source_commit_sha=sha,
    )

    with pytest.raises(RuntimeArtifactManifestError, match="provenance_missing"):
        _verify(
            archive, repo, sha, sources={
                "reddog_grant_authority_service.py": SOURCES[
                    "reddog_grant_authority_service.py"
                ]
            },
        )


def test_attacker_selected_committed_source_path_rejects(tmp_path: Path) -> None:
    repo, sha = _repository(
        tmp_path, extra={"attacker/service.py": b"def main():\n    return 0\n"}
    )
    attacker_sources = dict(SOURCES)
    attacker_sources["reddog_grant_authority_service.py"] = "attacker/service.py"
    archive = build_grant_service_archive_from_git(
        repo_root=repo, source_commit_sha=sha, sources=attacker_sources,
    )

    with pytest.raises(RuntimeArtifactManifestError, match="authority_mismatch"):
        _verify(archive, repo, sha)


def test_forged_member_with_real_blob_identity_rejects(tmp_path: Path) -> None:
    repo, sha = _repository(tmp_path)
    tree = exact_git_tree_manifest(repo, sha)
    payloads = {"__main__.py": ARCHIVE_MAIN}
    bindings: dict[str, dict[str, str]] = {}
    for archive_path, source_path in SOURCES.items():
        object_id = tree.blobs[source_path]
        payloads[archive_path] = read_exact_git_blob(
            repo, object_id, object_format=tree.object_format,
            max_bytes=1024 * 1024,
        )
        bindings[archive_path] = {
            "source_path": source_path, "source_object_id": object_id,
        }
    payloads["helpers/runtime.py"] = b"def status():\n    return 0\n"
    archive = build_git_provenance_grant_service_archive(
        payloads, source_commit_sha=sha,
        source_object_format=tree.object_format, source_bindings=bindings,
    )

    with pytest.raises(RuntimeArtifactManifestError, match="provenance_mismatch"):
        _verify(archive, repo, sha)


def test_uncommitted_source_is_not_buildable(tmp_path: Path) -> None:
    repo, sha = _repository(tmp_path)
    source = "service/untracked.py"
    (repo / source).write_bytes(b"x = 1\n")
    sources = dict(SOURCES)
    sources["untracked.py"] = source

    with pytest.raises(RuntimeArtifactManifestError, match="git_source_missing"):
        build_grant_service_archive_from_git(
            repo_root=repo, source_commit_sha=sha, sources=sources,
        )


def test_source_mapping_must_be_one_to_one(tmp_path: Path) -> None:
    repo, sha = _repository(tmp_path)
    sources = dict(SOURCES)
    sources["duplicate.py"] = SOURCES["helpers/runtime.py"]

    with pytest.raises(RuntimeArtifactManifestError, match="source_binding_invalid"):
        build_grant_service_archive_from_git(
            repo_root=repo, source_commit_sha=sha, sources=sources,
        )


def test_distinct_sources_may_share_one_committed_blob(tmp_path: Path) -> None:
    shared = b"def status():\n    return 2\n"
    alias_path = "service/helpers/alias.py"
    repo, sha = _repository(tmp_path, extra={alias_path: shared})
    sources = dict(SOURCES)
    sources["helpers/alias.py"] = alias_path

    archive = build_grant_service_archive_from_git(
        repo_root=repo, source_commit_sha=sha, sources=sources,
    )
    manifest = _verify(archive, repo, sha, sources=sources)

    bindings = {
        item["path"]: item for item in manifest["files"]
        if item["source_kind"] == "git_blob"
    }
    runtime_binding = bindings["helpers/runtime.py"]
    alias_binding = bindings["helpers/alias.py"]
    assert runtime_binding["source_path"] != alias_binding["source_path"]
    assert runtime_binding["source_object_id"] == alias_binding["source_object_id"]


def test_archive_selected_later_commit_rejects(tmp_path: Path) -> None:
    repo, authorized_sha = _repository(tmp_path)
    service_path = repo / SOURCES["reddog_grant_authority_service.py"]
    service_path.write_bytes(SERVICE.replace(b"return status()", b"return 0"))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "attacker-selected-later-commit")
    attacker_sha = _git(repo, "rev-parse", "HEAD").strip()
    archive = _build(repo, attacker_sha)

    with pytest.raises(RuntimeArtifactManifestError, match="authority_mismatch"):
        _verify(archive, repo, authorized_sha)


def test_git_replacement_ref_cannot_rewrite_exact_commit(tmp_path: Path) -> None:
    repo, authorized_sha = _repository(tmp_path)
    expected = _build(repo, authorized_sha)
    service_path = repo / SOURCES["reddog_grant_authority_service.py"]
    service_path.write_bytes(SERVICE.replace(b"return status()", b"return 0"))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "replacement-attacker")
    attacker_sha = _git(repo, "rev-parse", "HEAD").strip()
    _git(repo, "replace", authorized_sha, attacker_sha)

    archive = _build(repo, authorized_sha)
    assert archive == expected
    _verify(archive, repo, authorized_sha)


def test_expected_repository_root_digest_is_mandatory(tmp_path: Path) -> None:
    repo, sha = _repository(tmp_path)
    archive = _build(repo, sha)

    with pytest.raises(RuntimeArtifactManifestError, match="authority_mismatch"):
        validate_grant_service_archive_git_provenance(
            archive, repo_root=repo,
            expected_repo_root_digest="sha256:" + "0" * 64,
            expected_source_commit_sha=sha, expected_object_format="sha1",
            expected_sources=SOURCES,
            expected_source_policy_digest=grant_service_git_source_policy_digest(
                SOURCES
            ),
        )


def test_non_mapping_manifest_has_stable_contract_error(tmp_path: Path) -> None:
    repo, sha = _repository(tmp_path)
    archive = canonical_archive_bytes({
        ARCHIVE_MANIFEST: b"[]", "__main__.py": ARCHIVE_MAIN,
        "reddog_grant_authority_service.py": b"def main():\n    return 2\n",
    })

    with pytest.raises(RuntimeArtifactManifestError, match="manifest_invalid"):
        _verify(archive, repo, sha)


def test_low_level_builder_rejects_unbound_extra_source(tmp_path: Path) -> None:
    repo, sha = _repository(tmp_path)
    tree = exact_git_tree_manifest(repo, sha)
    service_path = SOURCES["reddog_grant_authority_service.py"]
    object_id = tree.blobs[service_path]
    service = read_exact_git_blob(
        repo, object_id, object_format=tree.object_format,
        max_bytes=1024 * 1024,
    )
    bindings = {
        "reddog_grant_authority_service.py": {
            "source_path": service_path, "source_object_id": object_id,
        },
        "unused.py": {"source_path": service_path, "source_object_id": object_id},
    }

    with pytest.raises(RuntimeArtifactManifestError, match="source_binding_invalid"):
        build_git_provenance_grant_service_archive(
            {"__main__.py": ARCHIVE_MAIN,
             "reddog_grant_authority_service.py": service},
            source_commit_sha=sha, source_object_format=tree.object_format,
            source_bindings=bindings,
        )


def _build(repo: Path, sha: str) -> bytes:
    return build_grant_service_archive_from_git(
        repo_root=repo, source_commit_sha=sha, sources=SOURCES,
    )


def _verify(
    archive: bytes, repo: Path, expected_sha: str,
    *, sources: dict[str, str] | None = None,
):
    policy = SOURCES if sources is None else sources
    object_format = exact_git_tree_manifest(repo, expected_sha).object_format
    return validate_grant_service_archive_git_provenance(
        archive, repo_root=repo,
        expected_repo_root_digest=raw_digest(
            str(repo.resolve()).encode("utf-8")
        ),
        expected_source_commit_sha=expected_sha,
        expected_object_format=object_format,
        expected_sources=policy,
        expected_source_policy_digest=grant_service_git_source_policy_digest(
            policy
        ),
    )


def _repository(
    tmp_path: Path, *, extra: dict[str, bytes] | None = None,
) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    files = {
        SOURCES["reddog_grant_authority_service.py"]: SERVICE,
        SOURCES["helpers/__init__.py"]: b"from .runtime import status\n",
        SOURCES["helpers/runtime.py"]: b"def status():\n    return 2\n",
        **(extra or {}),
    }
    _git(repo, "init")
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "config", "user.name", "Grant Archive Tests")
    for relative, body in files.items():
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "fixture")
    return repo, _git(repo, "rev-parse", "HEAD").strip()


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ("git", *args), cwd=repo, capture_output=True, text=True,
        check=True, timeout=30,
    ).stdout
