"""
Theory-archive-informed PQN harness.

This module treats the 2026-03-15 theory archive as an input manifest for
simulation and detector planning. It does not promote the archive to ontology.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from .detector.api import run_detector_with_spectral_analysis
from .theory_archive import get_theory_archive_context


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _read_document(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _extract_target_resonance_hz(texts: List[str]) -> float:
    for text in texts:
        match = re.search(r"\b7\.05\b", text)
        if match:
            return 7.05
    return 7.05


def _mentions_theta_band(texts: List[str]) -> bool:
    return any("theta" in text.lower() for text in texts)


def _detect_observables(texts: List[str]) -> List[str]:
    combined = "\n".join(texts).lower()
    observables: List[str] = []
    if "gap ratio" in combined or "spectral statistics" in combined or "r_bar" in combined:
        observables.append("spectral_gap_ratio")
    if "otoc" in combined or "lyapunov" in combined:
        observables.append("otoc_growth_proxy")
    if "lindblad" in combined or "decoherence" in combined:
        observables.append("lindblad_decoherence_proxy")
    if "projection" in combined or "pi_classical" in combined:
        observables.append("classical_projection")
    if "eta" in combined or "detection signal" in combined:
        observables.append("detection_signal_eta")
    return observables


def build_theory_archive_harness_spec(repo_root: str = "") -> Dict[str, Any]:
    """
    Build a non-dogmatic experiment specification from the theory archive.

    The archive is treated as a source of hypotheses, target observables, and
    control requirements, not as accepted runtime truth.
    """
    context = get_theory_archive_context(repo_root=repo_root)
    root = Path(repo_root) if repo_root else _repo_root()

    document_texts: List[str] = []
    for doc in context["documents"].values():
        path = root / doc["relative_path"]
        if path.exists():
            document_texts.append(_read_document(path))

    target_resonance_hz = _extract_target_resonance_hz(document_texts)
    observables = _detect_observables(document_texts)
    theta_band_hz = [4.0, 8.0] if _mentions_theta_band(document_texts) else []

    return {
        "mode": "archive_informed_non_dogmatic",
        "archive_ready": context["archive_ready"],
        "matched_null_required": True,
        "target_resonance_hz": target_resonance_hz,
        "theta_band_hz": theta_band_hz,
        "observables": observables,
        "detector_surface": "run_detector_with_spectral_analysis",
        "implementation_targets": context["implementation_targets"],
        "constraints": context["constraints"],
        "experiment_matrix": [
            {
                "name": "matched_null_control",
                "script": ".....",
                "seed": 0,
                "purpose": "control",
            },
            {
                "name": "archive_informed_probe",
                "script": "^^^&&&#^&##",
                "seed": 0,
                "purpose": "probe",
            },
        ],
    }


def run_theory_archive_detector_harness(config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Run one archive-informed detector harness pass.

    This is intentionally conservative: it routes through the existing detector
    surface and returns an interpretation block that states the archive remains
    a hypothesis source.
    """
    config = dict(config or {})
    spec = build_theory_archive_harness_spec(repo_root=config.get("repo_root", ""))

    out_dir = config.get(
        "out_dir",
        "modules/ai_intelligence/pqn_alignment/artifact_results/theory_archive_harness",
    )

    detector_config = {
        "script": config.get("script", spec["experiment_matrix"][1]["script"]),
        "steps": int(config.get("steps", 240)),
        "steps_per_sym": int(config.get("steps_per_sym", 40)),
        "dt": float(config.get("dt", 0.5 / spec["target_resonance_hz"])),
        "seed": int(config.get("seed", 0)),
        "out_dir": out_dir,
        "geom_win": int(config.get("geom_win", 64)),
        "reso_win": int(config.get("reso_win", 256)),
    }

    detector_result = run_detector_with_spectral_analysis(detector_config)

    return {
        "mode": spec["mode"],
        "spec": spec,
        "detector_config": detector_config,
        "detector_result": detector_result,
        "interpretation": {
            "archive_informed": True,
            "validated_truth": False,
            "matched_null_required": True,
            "note": (
                "Theory archive consumed as hypothesis input only. Results require "
                "matched-null comparison before any stronger claim."
            ),
        },
    }
