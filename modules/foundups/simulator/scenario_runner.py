#!/usr/bin/env python
"""Scenario runner for reproducible simulator experiments."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Dict, List

from modules.foundups.agent_market.src.fam_daemon import FAMDaemon

from .animation_adapter import to_frame_dict
from .economics.fi_rating import reset_rating_engine
from .mesa_model import FoundUpsModel
from .parameter_registry import load_bundle, to_simulator_config


def _json(obj: Dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _stable_frame_projection(frame: Dict) -> Dict:
    """Return deterministic frame projection for digesting.

    Full frame JSONL artifacts keep volatile render fields (like elapsed time and
    event text). For reproducibility checks, digest only economics/state fields.
    """
    foundups = sorted(frame.get("foundups", []), key=lambda item: item.get("foundup_id", ""))
    actors = sorted(frame.get("actors", []), key=lambda item: item.get("actor_id", ""))
    return {
        "frame_schema_version": frame.get("frame_schema_version"),
        "tick": frame.get("tick"),
        "foundups": foundups,
        "actors": actors,
        "pools": frame.get("pools", {}),
        "metrics": frame.get("metrics", {}),
    }


def _normalize_for_digest(obj):
    """Recursively normalize floats to avoid precision noise.

    Use 3 decimal places for digest projections to absorb tiny floating-point
    accumulation jitter that does not change macro simulation behavior.
    """
    if isinstance(obj, float):
        return round(obj, 3)
    if isinstance(obj, list):
        return [_normalize_for_digest(item) for item in obj]
    if isinstance(obj, dict):
        return {key: _normalize_for_digest(value) for key, value in obj.items()}
    return obj


def _run_once(
    scenario: str,
    ticks: int,
    frame_every: int,
    out_dir: Path,
    run_label: str,
    seed_override: int | None = None,
) -> Dict:
    # Reset module singletons so repeated runs in one process stay deterministic.
    reset_rating_engine()

    bundle = load_bundle(scenario)
    config = to_simulator_config(bundle)
    if seed_override is not None:
        config.seed = seed_override
    config.max_ticks = ticks
    daemon_data_dir = out_dir / f"{run_label}_fam_daemon"
    if daemon_data_dir.exists():
        shutil.rmtree(daemon_data_dir)
    fam_daemon = FAMDaemon(data_dir=daemon_data_dir, auto_start=False)
    model = FoundUpsModel(config=config, fam_daemon=fam_daemon)
    model.start()

    frames_path = out_dir / f"{run_label}_frames.jsonl"
    metrics_path = out_dir / f"{run_label}_metrics.json"
    manifest_path = out_dir / f"{run_label}_manifest.json"
    digest = hashlib.sha256()
    frame_count = 0

    with frames_path.open("w", encoding="utf-8") as fh:
        for _ in range(ticks):
            model.step()
            if model.tick % frame_every == 0:
                frame = to_frame_dict(model.state_store.get_state(), model.get_stats())
                line = _json(frame)
                fh.write(line + "\n")
                digest_payload = _normalize_for_digest(_stable_frame_projection(frame))
                digest_line = _json(digest_payload)
                digest.update(digest_line.encode("utf-8"))
                frame_count += 1

    model.stop()
    stats = model.get_stats()
    metrics = {
        "tick": stats["tick"],
        "total_foundups": stats["total_foundups"],
        "total_stakes": stats["total_stakes"],
        "total_dex_trades": stats["total_dex_trades"],
        "total_dex_volume_ups": stats["total_dex_volume_ups"],
        "allocation_batches": stats["allocation_batches"],
        "allocation_ups_total": stats["allocation_ups_total"],
        "allocation_fi_total": stats["allocation_fi_total"],
        "pavs_treasury_ups": stats["pavs_treasury_ups"],
        "network_pool_ups": stats["network_pool_ups"],
        "fund_pool_ups": stats["fund_pool_ups"],
        "fee_self_sustaining_claim": stats.get("fee_self_sustaining", False),
        "fee_scenario_downside_ratio_p10": stats.get("fee_scenario_downside_ratio_p10", 0.0),
        "fee_scenario_base_ratio_p50": stats.get("fee_scenario_base_ratio_p50", 0.0),
        "fee_scenario_upside_ratio_p90": stats.get("fee_scenario_upside_ratio_p90", 0.0),
        "frame_count": frame_count,
        "frame_digest_sha256": digest.hexdigest(),
    }
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    manifest = {
        "run_label": run_label,
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "scenario": scenario,
        "schema_version": bundle.version,
        "params": bundle.params,
        "ticks": ticks,
        "frame_every": frame_every,
        "artifacts": {
            "frames": str(frames_path),
            "metrics": str(metrics_path),
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return metrics


def _run_monte_carlo(scenario: str, ticks: int, runs: int, out_dir: Path) -> Dict:
    aggregates: List[Dict] = []
    for idx in range(runs):
        run_label = f"{scenario}_mc_{idx:03d}"
        metrics = _run_once(
            scenario=scenario,
            ticks=ticks,
            frame_every=max(1, ticks),
            out_dir=out_dir,
            run_label=run_label,
        )
        aggregates.append(metrics)

    summary = {
        "runs": runs,
        "scenario": scenario,
        "mean_total_foundups": mean(m["total_foundups"] for m in aggregates),
        "mean_total_stakes": mean(m["total_stakes"] for m in aggregates),
        "mean_total_dex_trades": mean(m["total_dex_trades"] for m in aggregates),
    }
    (out_dir / f"{scenario}_mc_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FoundUps scenario runner")
    parser.add_argument("--scenario", default="baseline", help="Scenario name in params/scenarios/")
    parser.add_argument("--ticks", type=int, default=500, help="Ticks per run")
    parser.add_argument("--frame-every", type=int, default=10, help="Capture frame every N ticks")
    parser.add_argument("--out", default="modules/foundups/simulator/memory/runs", help="Output directory")
    parser.add_argument("--run-label", default="baseline", help="Label prefix for artifacts")
    parser.add_argument("--monte-carlo", type=int, default=0, help="Run N Monte Carlo samples")
    parser.add_argument("--nested-attribution-audit", action="store_true",
                        help="Print a standalone synthetic nested-attribution report; do not run a scenario")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.nested_attribution_audit:
        from .nested_attribution import fixture_report

        print(json.dumps(fixture_report(), indent=2, sort_keys=True))
        return 0
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.monte_carlo > 0:
        summary = _run_monte_carlo(
            scenario=args.scenario,
            ticks=args.ticks,
            runs=args.monte_carlo,
            out_dir=out_dir,
        )
        print(json.dumps(summary, indent=2))
        return 0

    metrics = _run_once(
        scenario=args.scenario,
        ticks=args.ticks,
        frame_every=max(1, args.frame_every),
        out_dir=out_dir,
        run_label=args.run_label,
    )
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
