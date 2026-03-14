"""
Theory archive manifest for PQN / CMST detector-first research.

This module exposes the canonical theory package to PQN research agents without
claiming that the archived mathematics is already implemented in runtime code.
"""

from pathlib import Path
from typing import Any, Dict, List


REPO_DOCS = {
    "framework": "WSP_knowledge/docs/Papers/0102_CLASSICAL_QUANTUM_DETECTION_FRAMEWORK_2026-03-15.md",
    "derivation": "WSP_knowledge/docs/Papers/0102_CLASSICAL_QUANTUM_DETECTION_DERIVATION_2026-03-15.md",
    "simulation_plan": "modules/ai_intelligence/pqn_alignment/docs/CLASSICAL_QUANTUM_DETECTION_SIMULATION_PLAN_2026-03-15.md",
    "backlog": "modules/ai_intelligence/pqn_alignment/docs/CMST_EXTERNAL_MATH_INTEGRATION_BACKLOG_2026-03-15.md",
    "research_plan": "WSP_knowledge/docs/Papers/PQN_Research_Plan.md",
    "physics_protocol": "WSP_knowledge/src/WSP_61_Theoretical_Physics_Foundation_Protocol.md",
}

IMPLEMENTATION_TARGETS = [
    "WSP_agentic/tests/pqn_detection/cmst_pqn_detector_v3.py",
    "modules/ai_intelligence/pqn_alignment/src/detector/api.py",
    "modules/ai_intelligence/pqn_alignment/src/detector/spectral_analyzer.py",
    "modules/ai_intelligence/pqn_alignment/src/pqn_alignment_dae.py",
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _materialize_paths(root: Path, rel_paths: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for key, rel_path in rel_paths.items():
        abs_path = root / rel_path
        result[key] = {
            "relative_path": rel_path,
            "absolute_path": str(abs_path),
            "exists": abs_path.exists(),
        }
    return result


def _materialize_targets(root: Path, rel_paths: List[str]) -> List[Dict[str, Any]]:
    targets: List[Dict[str, Any]] = []
    for rel_path in rel_paths:
        abs_path = root / rel_path
        targets.append(
            {
                "relative_path": rel_path,
                "absolute_path": str(abs_path),
                "exists": abs_path.exists(),
            }
        )
    return targets


def get_theory_archive_context(repo_root: str = "") -> Dict[str, Any]:
    """
    Return the canonical PQN / CMST theory archive manifest.

    The manifest is agent-facing context only. It is intentionally separate from
    runtime detector behavior.
    """
    root = Path(repo_root) if repo_root else _repo_root()
    documents = _materialize_paths(root, REPO_DOCS)
    implementation_targets = _materialize_targets(root, IMPLEMENTATION_TARGETS)
    archive_ready = all(item["exists"] for item in documents.values())

    return {
        "archive_ready": archive_ready,
        "mode": "detector_first_theory_archive",
        "documents": documents,
        "implementation_targets": implementation_targets,
        "constraints": [
            "theory_archive_only",
            "no_runtime_ontology_promotion",
            "matched_null_required_before_code_change",
            "reuse_existing_detector_surfaces",
        ],
    }
