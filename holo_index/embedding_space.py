"""Deterministic HoloIndex embedding-space identity helpers.

An embedding dimension alone does not make two vector spaces compatible.  A
freshness proof therefore binds the backend, logical model, encoder contract,
and local artifact content used to create/query collection vectors.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "holoindex_embedding_space.v1"
EMBEDDING_DIMENSION = 384
CANONICAL_INDEX_BACKEND = "sentence_transformers"
SENTENCE_TRANSFORMER_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
SENTENCE_TRANSFORMER_CONTRACT = "sentence_transformers.encode.v1"
TURBOQUANT_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2:int8-onnx"
TURBOQUANT_CONTRACT = "onnx.mean_pool_l2.v1"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def embedding_artifact_digest(path: Path | str | None) -> str:
    """Hash a resolved model artifact tree without depending on its location."""

    if path is None:
        return ""
    root = Path(path)
    try:
        if root.is_file():
            return "sha256:" + _sha256_file(root)
        files = sorted(
            candidate
            for candidate in root.rglob("*")
            if candidate.is_file()
        )
    except OSError:
        return ""
    if not files:
        return ""
    manifest: list[dict[str, Any]] = []
    try:
        for candidate in files:
            manifest.append(
                {
                    "path": candidate.relative_to(root).as_posix(),
                    "size": candidate.stat().st_size,
                    "sha256": _sha256_file(candidate),
                }
            )
    except (OSError, ValueError):
        return ""
    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def embedding_space_fingerprint(
    *,
    backend: str,
    model_id: str,
    artifact_digest: str,
    encoder_contract: str,
    dimension: int = EMBEDDING_DIMENSION,
) -> str:
    """Return an identity only when backend, model, and artifacts are proven."""

    values = {
        "schema_version": SCHEMA_VERSION,
        "backend": str(backend).strip(),
        "model_id": str(model_id).strip(),
        "artifact_digest": str(artifact_digest).strip(),
        "encoder_contract": str(encoder_contract).strip(),
        "dimension": int(dimension),
    }
    if (
        not values["backend"]
        or not values["model_id"]
        or not values["encoder_contract"]
        or not values["artifact_digest"].startswith("sha256:")
        or values["dimension"] <= 0
    ):
        return ""
    payload = json.dumps(values, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def resolve_sentence_transformer_snapshot(
    models_path: Path | str,
    model_name: str,
) -> Path | None:
    """Resolve flat SentenceTransformer or Hugging Face snapshot cache layouts."""

    root = Path(models_path)
    short_name = str(model_name).strip().split("/")[-1]
    model_id = (
        str(model_name).strip()
        if "/" in str(model_name).strip()
        else f"sentence-transformers/{short_name}"
    )
    flat_candidates = (
        root / "sentence_transformers" / short_name,
        root / short_name,
        root / model_id,
    )
    for candidate in flat_candidates:
        if _looks_like_model_snapshot(candidate):
            return candidate.resolve(strict=False)

    hub_root = root / ("models--" + model_id.replace("/", "--"))
    snapshots = hub_root / "snapshots"
    ref = hub_root / "refs" / "main"
    try:
        revision = ref.read_text(encoding="utf-8").strip()
    except OSError:
        revision = ""
    if revision:
        selected = snapshots / revision
        if _looks_like_model_snapshot(selected):
            return selected.resolve(strict=False)
    try:
        candidates = sorted(
            candidate
            for candidate in snapshots.iterdir()
            if candidate.is_dir() and _looks_like_model_snapshot(candidate)
        )
    except OSError:
        candidates = []
    return candidates[0].resolve(strict=False) if len(candidates) == 1 else None


def _looks_like_model_snapshot(path: Path) -> bool:
    try:
        return path.is_dir() and all(
            (path / marker).is_file()
            for marker in ("modules.json", "config.json", "model.safetensors")
        ) and any(
            (path / tokenizer).is_file()
            for tokenizer in ("tokenizer.json", "vocab.txt")
        )
    except OSError:
        return False


def normalized_embedding_space_map(value: Any) -> dict[str, str]:
    """Normalize an untrusted collection-to-fingerprint mapping."""

    if not isinstance(value, Mapping):
        return {}
    return {
        str(name): str(fingerprint)
        for name, fingerprint in value.items()
        if isinstance(name, str)
        and isinstance(fingerprint, str)
        and fingerprint.startswith("sha256:")
    }


def configure_runtime_embedding_spaces(
    holo: Any,
    *,
    sentence_backend: str,
    turboquant_backend: str,
    sentence_snapshot: Path | None,
    turboquant_model_dir: Path | None,
) -> None:
    """Attach persisted-index and per-collection query-space truth to HoloIndex."""

    fingerprints: dict[str, str] = {}
    if sentence_backend in holo.embedders:
        fingerprints[sentence_backend] = embedding_space_fingerprint(
            backend=sentence_backend,
            model_id=SENTENCE_TRANSFORMER_MODEL_ID,
            artifact_digest=embedding_artifact_digest(sentence_snapshot),
            encoder_contract=SENTENCE_TRANSFORMER_CONTRACT,
        )
    if turboquant_backend in holo.embedders:
        fingerprints[turboquant_backend] = embedding_space_fingerprint(
            backend=turboquant_backend,
            model_id=TURBOQUANT_MODEL_ID,
            artifact_digest=embedding_artifact_digest(turboquant_model_dir),
            encoder_contract=TURBOQUANT_CONTRACT,
        )
    holo.embedding_space_fingerprint_map = fingerprints
    holo.collection_embedding_space_map = {
        name: fingerprints.get(backend, "")
        for name, backend in holo.collection_backend_map.items()
    }
    index_backend = (
        sentence_backend
        if sentence_backend in holo.embedders
        else turboquant_backend
        if turboquant_backend in holo.embedders
        else ""
    )
    model_ids = {
        sentence_backend: SENTENCE_TRANSFORMER_MODEL_ID,
        turboquant_backend: TURBOQUANT_MODEL_ID,
    }
    holo.index_embedding_backend = index_backend
    holo.index_embedding_model_id = model_ids.get(index_backend, "")
    holo.index_embedding_space_fingerprint = fingerprints.get(index_backend, "")
    holo.embedding_model_id = (
        "routed"
        if getattr(holo, "embedding_backend", "") == "routed"
        else model_ids.get(getattr(holo, "embedding_backend", ""), "")
    )


__all__ = [
    "EMBEDDING_DIMENSION",
    "CANONICAL_INDEX_BACKEND",
    "SENTENCE_TRANSFORMER_CONTRACT",
    "SENTENCE_TRANSFORMER_MODEL_ID",
    "TURBOQUANT_CONTRACT",
    "TURBOQUANT_MODEL_ID",
    "embedding_artifact_digest",
    "embedding_space_fingerprint",
    "configure_runtime_embedding_spaces",
    "normalized_embedding_space_map",
    "resolve_sentence_transformer_snapshot",
]
