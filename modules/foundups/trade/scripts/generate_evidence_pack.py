#!/usr/bin/env python3
"""Generate Trade PoC Simulation Evidence Pack

Runs simulation harness with multiple seeds and bar counts to generate
a machine-readable evidence pack for review.

Slice: TRADE_POC_SIMULATION_EVIDENCE_PACK_PHASE1

Usage:
    python scripts/generate_evidence_pack.py [--output PATH]
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from simulation_harness import SimulationHarness


SEEDS = [42, 123, 456, 789, 1000]
BAR_COUNTS = [100, 500, 1000]


def run_single(seed: int, bars: int) -> Dict[str, Any]:
    """Run single simulation and return result."""
    harness = SimulationHarness(seed=seed, bars=bars)
    summary = harness.run()

    return {
        "seed": seed,
        "bars": bars,
        "run_id": summary.run_id,
        "initial_capital": summary.initial_capital,
        "final_equity": round(summary.final_equity, 6),
        "total_trades": summary.total_trades,
        "gross_pnl": round(summary.gross_pnl, 6),
        "max_drawdown": round(summary.max_drawdown, 6),
        "sharpe_like_ratio": round(summary.sharpe_like_ratio, 6) if summary.sharpe_like_ratio else None,
        "invariant_violations": summary.invariant_violations,
        "violations": [v.to_dict() for v in summary.violations],
    }


def verify_determinism(seed: int, bars: int) -> Dict[str, Any]:
    """Verify determinism by running twice and comparing JSON output."""
    harness1 = SimulationHarness(seed=seed, bars=bars)
    json1 = harness1.to_json()

    harness2 = SimulationHarness(seed=seed, bars=bars)
    json2 = harness2.to_json()

    identical = json1 == json2

    return {
        "seed": seed,
        "bars": bars,
        "determinism_pass": identical,
        "json_length": len(json1),
    }


def generate_evidence_pack() -> Dict[str, Any]:
    """Generate complete evidence pack."""
    run_results: List[Dict[str, Any]] = []
    determinism_results: List[Dict[str, Any]] = []

    print("Running evidence pack generation...")
    print(f"Seeds: {SEEDS}")
    print(f"Bar counts: {BAR_COUNTS}")
    print()

    for seed in SEEDS:
        for bars in BAR_COUNTS:
            print(f"  Running seed={seed} bars={bars}...", end=" ")
            result = run_single(seed, bars)
            run_results.append(result)

            det = verify_determinism(seed, bars)
            determinism_results.append(det)

            status = "PASS" if result["invariant_violations"] == 0 else "FAIL"
            print(f"{status} (trades={result['total_trades']}, violations={result['invariant_violations']})")

    total_runs = len(run_results)
    total_violations = sum(r["invariant_violations"] for r in run_results)
    all_deterministic = all(d["determinism_pass"] for d in determinism_results)

    aggregate = {
        "total_runs": total_runs,
        "seeds_tested": len(SEEDS),
        "bar_counts_tested": len(BAR_COUNTS),
        "total_invariant_violations": total_violations,
        "all_deterministic": all_deterministic,
        "runs_with_violations": sum(1 for r in run_results if r["invariant_violations"] > 0),
        "average_trades": round(sum(r["total_trades"] for r in run_results) / total_runs, 2),
        "average_max_drawdown": round(sum(r["max_drawdown"] for r in run_results) / total_runs, 6),
    }

    pack = {
        "evidence_pack_version": "1.0.0",
        "slice": "TRADE_POC_SIMULATION_EVIDENCE_PACK_PHASE1",
        "aggregate": aggregate,
        "run_results": run_results,
        "determinism_verification": determinism_results,
        "truth_boundary": {
            "is_simulation": True,
            "no_money_mode": True,
            "dry_run_mode": True,
            "real_execution_performed": False,
            "network_calls": False,
            "wallet_signing": False,
            "order_placement": False,
        },
    }

    return pack


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate Trade PoC Simulation Evidence Pack")
    parser.add_argument("--output", type=str, default=None, help="Output JSON file path")
    args = parser.parse_args()

    pack = generate_evidence_pack()

    print()
    print("=" * 60)
    print("EVIDENCE PACK SUMMARY")
    print("=" * 60)
    print(f"Total runs: {pack['aggregate']['total_runs']}")
    print(f"Seeds tested: {pack['aggregate']['seeds_tested']}")
    print(f"Bar counts tested: {pack['aggregate']['bar_counts_tested']}")
    print(f"Total invariant violations: {pack['aggregate']['total_invariant_violations']}")
    print(f"All deterministic: {pack['aggregate']['all_deterministic']}")
    print(f"Runs with violations: {pack['aggregate']['runs_with_violations']}")
    print()

    if pack['aggregate']['total_invariant_violations'] == 0 and pack['aggregate']['all_deterministic']:
        print("EVIDENCE PACK STATUS: PASS")
    else:
        print("EVIDENCE PACK STATUS: FAIL")

    json_output = json.dumps(pack, sort_keys=True, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_output)
        print(f"\nEvidence pack written to: {args.output}")
    else:
        print("\n--- JSON OUTPUT ---")
        print(json_output)

    return 0 if pack['aggregate']['total_invariant_violations'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
