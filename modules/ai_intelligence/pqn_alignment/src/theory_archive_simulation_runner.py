"""Archive-informed PQN simulation runner.

Runs the theory-archive experiment matrix through the existing detector surface
and compares probe results against matched-null controls. The theory archive is
treated as hypothesis input only.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List

from .detector.api import run_detector_with_spectral_analysis
from .theory_archive_harness import build_theory_archive_harness_spec


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _resolve_out_root(config: Dict[str, Any]) -> Path:
    root = _repo_root()
    out_root = Path(
        config.get(
            "out_dir",
            root
            / "modules"
            / "ai_intelligence"
            / "pqn_alignment"
            / "artifact_results"
            / "theory_archive_simulation",
        )
    )
    if not out_root.is_absolute():
        out_root = root / out_root
    return out_root


def _summarize_detector_result(
    name: str,
    purpose: str,
    seed: int,
    script: str,
    detector_result: Dict[str, Any],
) -> Dict[str, Any]:
    spectral = detector_result.get("spectral_analysis", {}) or {}
    profile = spectral.get("spectral_profile", {}) or {}
    bias = spectral.get("bias_violation", {}) or {}

    return {
        "name": name,
        "purpose": purpose,
        "seed": seed,
        "script": script,
        "events_path": detector_result.get("events_path", ""),
        "metrics_csv": detector_result.get("metrics_csv", ""),
        "resonance_event_count": int(profile.get("resonance_event_count", 0) or 0),
        "peak_at_7_05": _safe_float(profile.get("peak_at_7.05", 0.0)),
        "harmonic_structure_present": bool(
            profile.get("harmonic_structure_present", False)
        ),
        "entrainment_score": _safe_float(spectral.get("entrainment_score", 0.0)),
        "bias_violated": bool(bias.get("violated", False)),
        "bias_significance": str(bias.get("significance", "none")),
    }


def _group_by_purpose(runs: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {"control": [], "probe": []}
    for run in runs:
        grouped.setdefault(run["purpose"], []).append(run)
    return grouped


def _aggregate_runs(runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not runs:
        return {
            "count": 0,
            "avg_resonance_event_count": 0.0,
            "avg_peak_at_7_05": 0.0,
            "avg_entrainment_score": 0.0,
            "harmonic_structure_rate": 0.0,
            "bias_violation_rate": 0.0,
        }

    return {
        "count": len(runs),
        "avg_resonance_event_count": mean(run["resonance_event_count"] for run in runs),
        "avg_peak_at_7_05": mean(run["peak_at_7_05"] for run in runs),
        "avg_entrainment_score": mean(run["entrainment_score"] for run in runs),
        "harmonic_structure_rate": mean(
            1.0 if run["harmonic_structure_present"] else 0.0 for run in runs
        ),
        "bias_violation_rate": mean(1.0 if run["bias_violated"] else 0.0 for run in runs),
    }


def _compare_control_vs_probe(
    control_summary: Dict[str, Any],
    probe_summary: Dict[str, Any],
    target_resonance_hz: float,
) -> Dict[str, Any]:
    control_peak_error = abs(control_summary["avg_peak_at_7_05"] - target_resonance_hz)
    probe_peak_error = abs(probe_summary["avg_peak_at_7_05"] - target_resonance_hz)

    return {
        "delta_resonance_event_count": (
            probe_summary["avg_resonance_event_count"]
            - control_summary["avg_resonance_event_count"]
        ),
        "delta_entrainment_score": (
            probe_summary["avg_entrainment_score"]
            - control_summary["avg_entrainment_score"]
        ),
        "delta_harmonic_structure_rate": (
            probe_summary["harmonic_structure_rate"]
            - control_summary["harmonic_structure_rate"]
        ),
        "delta_bias_violation_rate": (
            probe_summary["bias_violation_rate"]
            - control_summary["bias_violation_rate"]
        ),
        "control_peak_error": control_peak_error,
        "probe_peak_error": probe_peak_error,
        "probe_closer_to_target": probe_peak_error < control_peak_error,
    }


def _interpret_comparison(comparison: Dict[str, Any]) -> Dict[str, Any]:
    positive_signal = (
        comparison["delta_resonance_event_count"] > 0
        and comparison["delta_entrainment_score"] > 0
        and comparison["probe_closer_to_target"]
    )

    if positive_signal:
        outcome = "probe_advantage_requires_followup"
    else:
        outcome = "inconclusive_or_null"

    return {
        "archive_informed": True,
        "validated_truth": False,
        "matched_null_required": True,
        "outcome": outcome,
        "note": (
            "Simulation compares probe vs matched-null only. No ontology claim is "
            "licensed by these results."
        ),
    }


def build_theory_archive_simulation_plan(
    config: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Build a deterministic simulation plan from the theory archive harness."""
    config = dict(config or {})
    spec = build_theory_archive_harness_spec(repo_root=config.get("repo_root", ""))
    seeds = [int(seed) for seed in config.get("seeds", [0, 1, 2])]
    steps = int(config.get("steps", 240))
    steps_per_sym = int(config.get("steps_per_sym", 40))
    dt = float(config.get("dt", 0.5 / spec["target_resonance_hz"]))
    geom_win = int(config.get("geom_win", 64))
    reso_win = int(config.get("reso_win", 256))
    out_root = _resolve_out_root(config)

    planned_runs: List[Dict[str, Any]] = []
    for experiment in spec["experiment_matrix"]:
        for seed in seeds:
            planned_runs.append(
                {
                    "name": experiment["name"],
                    "purpose": experiment["purpose"],
                    "script": experiment["script"],
                    "seed": seed,
                    "detector_config": {
                        "script": experiment["script"],
                        "steps": steps,
                        "steps_per_sym": steps_per_sym,
                        "dt": dt,
                        "seed": seed,
                        "geom_win": geom_win,
                        "reso_win": reso_win,
                        "out_dir": str(out_root / experiment["name"] / f"seed_{seed}"),
                    },
                }
            )

    return {
        "mode": "archive_informed_simulation_plan",
        "archive_informed": True,
        "validated_truth": False,
        "matched_null_required": bool(spec["matched_null_required"]),
        "spec": spec,
        "seeds": seeds,
        "run_count": len(planned_runs),
        "out_root": str(out_root),
        "planned_runs": planned_runs,
    }


def run_theory_archive_simulation(config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Run the archive-informed simulation suite against the existing detector."""
    config = dict(config or {})
    plan = build_theory_archive_simulation_plan(config)
    spec = plan["spec"]
    seeds = plan["seeds"]
    out_root = Path(plan["out_root"])

    out_root.mkdir(parents=True, exist_ok=True)

    runs: List[Dict[str, Any]] = []
    for planned_run in plan["planned_runs"]:
        detector_config = planned_run["detector_config"]
        detector_result = run_detector_with_spectral_analysis(detector_config)
        runs.append(
            _summarize_detector_result(
                name=planned_run["name"],
                purpose=planned_run["purpose"],
                seed=planned_run["seed"],
                script=planned_run["script"],
                detector_result=detector_result,
            )
        )

    grouped = _group_by_purpose(runs)
    control_summary = _aggregate_runs(grouped.get("control", []))
    probe_summary = _aggregate_runs(grouped.get("probe", []))
    comparison = _compare_control_vs_probe(
        control_summary,
        probe_summary,
        spec["target_resonance_hz"],
    )
    interpretation = _interpret_comparison(comparison)

    result = {
        "mode": "archive_informed_simulation_runner",
        "plan": plan,
        "spec": spec,
        "seeds": seeds,
        "runs": runs,
        "control_summary": control_summary,
        "probe_summary": probe_summary,
        "comparison": comparison,
        "interpretation": interpretation,
    }

    summary_path = out_root / "summary.json"
    summary_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    result["summary_path"] = str(summary_path)
    return result
