"""Data-only contracts for governed RedDog candidate acceptance."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .reddog_holoindex_acceptance_guards import ModelCopyLimits


DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@dataclass(frozen=True)
class CandidateAcceptanceConfig:
    candidate_root: Path
    authority_root: Path
    owner_runtime_root: Path
    canonical_store: Path
    isolated_store: Path
    receipt_path: Path
    expected_sha: str
    real_mode: bool = False
    model_name: str = DEFAULT_MODEL_NAME
    port: int = 8127
    timeout_seconds: float = 900.0
    max_receipt_bytes: int = 256 * 1024
    model_limits: ModelCopyLimits = ModelCopyLimits(
        max_files=4096,
        max_file_bytes=1024 * 1024 * 1024,
        max_total_bytes=2 * 1024 * 1024 * 1024,
    )


@dataclass(frozen=True)
class CandidateAcceptanceResult:
    verdict: str
    status: str
    error: str = ""
    receipt_published: bool = False
    generation_id: str = ""
    freshness_receipt_digest: str = ""


@dataclass
class CandidateAcceptanceState:
    error: str = ""
    generation_id: str = ""
    receipt_digest: str = ""
    candidate_digest: str = ""
    authority_digest: str = ""
    runtime_digest: str = ""
    runtime_site_packages: tuple[str, ...] = ()
    runtime_executable_proof: Any = None
    model_digest: str = ""
    model_files: int = 0
    model_bytes: int = 0
    query_count: int = 0
    activation_query_count: int = 0
    activation_query_receipt_digest: str = ""
    semantic_store_proof_unchanged: bool = False
    owned_handoff: tuple[str, str] | None = None
    owner_session_digest: str = ""
    canonical_before: Any = None
    canonical_unchanged: bool = False
    environment_changed: bool = False
    environment_present: bool = False
    environment_value: str = ""


__all__ = [
    "CandidateAcceptanceConfig",
    "CandidateAcceptanceResult",
    "CandidateAcceptanceState",
    "DEFAULT_MODEL_NAME",
]
