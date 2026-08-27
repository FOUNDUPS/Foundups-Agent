"""Adversarial tests for the secret-free Holo retrieval runtime identity."""

from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path

import pytest

from holo_index.query_receipt import digest_json
from modules.infrastructure.foundups_mcp_bridge.src import (
    reddog_holoindex_runtime_environment_binding as runtime,
)


DIGEST = "sha256:" + "a" * 64
REPLICA = {
    "query_replica_descriptor_digest": "sha256:" + "1" * 64,
    "query_replica_generation_id": "sha256:" + "2" * 64,
    "query_replica_id": "sha256:" + "3" * 64,
    "query_replica_path_identity_digest": "sha256:" + "4" * 64,
}
MODEL_ARTIFACTS = ({
    "relative_path": "models/model/model.safetensors",
    "size": 10,
    "digest": "sha256:" + "5" * 64,
},)


class _Distribution:
    def __init__(self, name: str, version: str = "1.0", marker: str = "a") -> None:
        self.metadata = {"Name": name}
        self.version = version
        self._files = {
            "METADATA": f"Name: {name}\nVersion: {version}\n",
            "WHEEL": "Wheel-Version: 1.0\nTag: py3-none-any\n",
            "RECORD": f"{name}.py,sha256={marker},1\n",
            "direct_url.json": "",
        }

    def read_text(self, name: str) -> str | None:
        return self._files.get(name)


def _source_root(tmp_path: Path, marker: str = "a") -> Path:
    source = tmp_path / "runtime.py"
    source.write_text(f"MARKER = {marker!r}\n", encoding="utf-8", newline="\n")
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    path = tmp_path / "scripts" / "reddog_backend_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "schema_version": "reddog_backend_manifest.v3",
        "required_runtime_sha256": {"runtime.py": source_digest},
    }), encoding="utf-8")
    return tmp_path


def _manifest(
    tmp_path: Path,
    *,
    distributions=(_Distribution("Alpha"), _Distribution("beta_pkg")),
    environment=None,
):
    return runtime.runtime_environment_manifest(
        source_root=_source_root(tmp_path),
        ranker_digest=DIGEST,
        replica_binding=REPLICA,
        replica_artifacts=MODEL_ARTIFACTS,
        distributions=distributions,
        environment={} if environment is None else environment,
    )


def test_manifest_is_deterministic_sorted_and_secret_free(tmp_path: Path) -> None:
    first = _manifest(tmp_path)
    second = runtime.runtime_environment_manifest(
        source_root=tmp_path,
        ranker_digest=DIGEST,
        replica_binding=REPLICA,
        replica_artifacts=MODEL_ARTIFACTS,
        distributions=(_Distribution("beta_pkg"), _Distribution("Alpha")),
        environment={"OPENAI_API_KEY": "fixture-secret"},
    )

    assert first == second
    assert first["schema_version"] == runtime.RUNTIME_ENVIRONMENT_SCHEMA
    assert first["distribution_count"] == 2
    assert first["replica_deployment_binding_complete"] is True
    assert first["model_artifact_closure"]["complete"] is True
    assert first["installed_distribution_bytes_verified"] is False
    serialized = json.dumps(first, sort_keys=True)
    assert "fixture-secret" not in serialized
    assert str(tmp_path) not in serialized
    assert first["contains_paths"] is False
    assert first["contains_environment_secrets"] is False


def test_distribution_record_or_source_manifest_change_changes_digest(
    tmp_path: Path,
) -> None:
    before = _manifest(tmp_path, distributions=(_Distribution("alpha"),))
    changed_record = runtime.runtime_environment_manifest(
        source_root=tmp_path,
        ranker_digest=DIGEST,
        replica_binding=REPLICA,
        replica_artifacts=MODEL_ARTIFACTS,
        distributions=(_Distribution("alpha", marker="b"),),
        environment={},
    )
    _source_root(tmp_path, marker="b")
    changed_source = runtime.runtime_environment_manifest(
        source_root=tmp_path,
        ranker_digest=DIGEST,
        replica_binding=REPLICA,
        replica_artifacts=MODEL_ARTIFACTS,
        distributions=(_Distribution("alpha"),),
        environment={},
    )

    assert digest_json(before) != digest_json(changed_record)
    assert digest_json(before) != digest_json(changed_source)


def test_source_byte_change_without_manifest_update_fails_closed(
    tmp_path: Path,
) -> None:
    root = _source_root(tmp_path)
    (root / "runtime.py").write_text("MARKER = 'tampered'\n", encoding="utf-8")
    with pytest.raises(
        runtime.RuntimeEnvironmentBindingError,
        match="RUNTIME_SOURCE_DIGEST_MISMATCH",
    ):
        runtime.runtime_environment_manifest(
            source_root=root,
            ranker_digest=DIGEST,
            replica_binding=REPLICA,
            replica_artifacts=MODEL_ARTIFACTS,
            distributions=(_Distribution("alpha"),),
            environment={},
        )


def test_replica_model_closure_is_required(tmp_path: Path) -> None:
    with pytest.raises(
        runtime.RuntimeEnvironmentBindingError,
        match="RUNTIME_REPLICA_BINDING_INCOMPLETE",
    ):
        runtime.runtime_environment_manifest(
            source_root=_source_root(tmp_path),
            ranker_digest=DIGEST,
            replica_binding={"query_replica_id": DIGEST},
            replica_artifacts=MODEL_ARTIFACTS,
            distributions=(_Distribution("alpha"),),
            environment={},
        )


def test_knobs_preserve_actual_presence_without_false_forcing() -> None:
    absent = runtime.retrieval_runtime_knobs({})
    explicit = runtime.retrieval_runtime_knobs({"HOLO_CACHE_SIZE": ""})

    assert absent["HOLO_CACHE_SIZE"] == {"present": False, "value": "100"}
    assert explicit["HOLO_CACHE_SIZE"] == {"present": True, "value": ""}
    assert absent["PYTHONHASHSEED"] == {"present": False, "value": ""}
    assert absent["CUDA_VISIBLE_DEVICES"] == {"present": False, "value": ""}
    assert absent["TORCH_DEVICE"] == {"present": False, "value": ""}
    assert absent["HOLO_USE_TURBOQUANT"] == {"present": False, "value": "0"}


def test_required_environment_is_verified_not_projected(tmp_path: Path) -> None:
    with pytest.raises(
        runtime.RuntimeEnvironmentBindingError,
        match="RUNTIME_REQUIRED_ENVIRONMENT_MISMATCH",
    ):
        runtime.runtime_environment_manifest(
            source_root=_source_root(tmp_path),
            ranker_digest=DIGEST,
            replica_binding=REPLICA,
            replica_artifacts=MODEL_ARTIFACTS,
            distributions=(_Distribution("alpha"),),
            environment={},
            required_environment={"TORCH_DEVICE": "cpu"},
        )


def test_distribution_metadata_total_is_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime, "_MAX_METADATA_TOTAL_BYTES", 16)
    with pytest.raises(
        runtime.RuntimeEnvironmentBindingError,
        match="RUNTIME_DISTRIBUTION_METADATA_LIMIT_EXCEEDED",
    ):
        runtime.distribution_environment_manifest((_Distribution("alpha"),))


def test_duplicate_normalized_distribution_names_fail_closed() -> None:
    with pytest.raises(
        runtime.RuntimeEnvironmentBindingError,
        match="RUNTIME_DISTRIBUTION_SET_INVALID",
    ):
        runtime.distribution_environment_manifest((
            _Distribution("alpha_pkg"), _Distribution("alpha-pkg"),
        ))


def test_injected_executable_symlink_is_not_resolved_before_proof(
    tmp_path: Path,
) -> None:
    link = tmp_path / "python-link"
    try:
        link.symlink_to(Path(getattr(sys, "_base_executable", sys.executable)))
    except OSError:
        pytest.skip("file symlink unavailable")
    with pytest.raises(
        runtime.RuntimeEnvironmentBindingError,
        match="RUNTIME_EXECUTABLE_UNPROVEN",
    ):
        runtime.runtime_environment_manifest(
            source_root=_source_root(tmp_path),
            ranker_digest=DIGEST,
            replica_binding=REPLICA,
            replica_artifacts=MODEL_ARTIFACTS,
            distributions=(_Distribution("alpha"),),
            environment={},
            executable_path=link,
        )


def test_site_packages_reparse_is_rejected_before_resolution(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    site_packages = tmp_path / "site-packages"
    site_packages.mkdir()
    monkeypatch.setattr(
        Path, "is_junction", lambda path: path == site_packages, raising=False,
    )
    with pytest.raises(
        runtime.RuntimeEnvironmentBindingError,
        match="RUNTIME_SITE_PACKAGES_INVALID",
    ):
        runtime.runtime_environment_manifest(
            source_root=_source_root(tmp_path),
            ranker_digest=DIGEST,
            replica_binding=REPLICA,
            replica_artifacts=MODEL_ARTIFACTS,
            distributions=(_Distribution("alpha"),),
            environment={},
            sys_path_entries=(str(site_packages),),
        )
