"""Trade FoundUp CLI - Simulation Harness

Usage:
    python -m modules.foundups.trade --simulate [--seed N] [--bars N] [--json] [--output PATH]

Exit codes:
    0 = simulation completed and invariants passed
    1 = simulation completed but invariant violations were found
    2 = input/config error

WSP 97 Truth Boundary:
    - Simulation only
    - No real trading
    - No wallet signing
    - No network calls
    - No order placement

Slice: TRADE_POC_SIMULATION_HARNESS_PHASE1
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from simulation_harness import (
    SimulationHarness,
    DEFAULT_SEED,
    DEFAULT_BARS,
    DEFAULT_INITIAL_CAPITAL,
)


def main() -> int:
    """Main entry point for Trade CLI."""
    parser = argparse.ArgumentParser(
        description="Trade FoundUp PoC Simulation Harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m modules.foundups.trade --simulate
    python -m modules.foundups.trade --simulate --seed 42 --bars 100 --json
    python -m modules.foundups.trade --simulate --seed 123 --output result.json

WSP 97 Truth Boundary:
    All operations are simulation-only. No real trading, wallet signing,
    network calls, or order placement is performed.
        """,
    )

    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Run simulation harness",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Deterministic seed (default: {DEFAULT_SEED})",
    )
    parser.add_argument(
        "--bars",
        type=int,
        default=DEFAULT_BARS,
        help=f"Number of synthetic bars (default: {DEFAULT_BARS})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit canonical JSON to stdout",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Write JSON output to file path",
    )

    args = parser.parse_args()

    if not args.simulate:
        parser.print_help()
        print("\nError: --simulate flag required", file=sys.stderr)
        return 2

    if args.bars < 1:
        print("Error: --bars must be at least 1", file=sys.stderr)
        return 2

    if args.bars > 10000:
        print("Error: --bars must be at most 10000", file=sys.stderr)
        return 2

    try:
        harness = SimulationHarness(
            seed=args.seed,
            bars=args.bars,
            initial_capital=DEFAULT_INITIAL_CAPITAL,
        )

        summary = harness.run()

        if args.json:
            json_output = harness.to_json()
            print(json_output)
        else:
            print(f"Trade PoC Simulation Complete")
            print(f"  run_id: {summary.run_id}")
            print(f"  seed: {summary.seed}")
            print(f"  bars: {summary.bars}")
            print(f"  initial_capital: {summary.initial_capital:.2f}")
            print(f"  final_equity: {summary.final_equity:.2f}")
            print(f"  total_trades: {summary.total_trades}")
            print(f"  gross_pnl: {summary.gross_pnl:.2f}")
            print(f"  max_drawdown: {summary.max_drawdown:.4f}")
            if summary.sharpe_like_ratio is not None:
                print(f"  sharpe_like_ratio: {summary.sharpe_like_ratio:.4f}")
            print(f"  invariant_violations: {summary.invariant_violations}")

        if args.output:
            json_output = harness.to_json()
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(json_output)
            print(f"Output written to: {args.output}", file=sys.stderr)

        if summary.invariant_violations > 0:
            print(f"\nWARNING: {summary.invariant_violations} invariant violation(s) found", file=sys.stderr)
            for v in summary.violations:
                print(f"  [{v.bar_index}] {v.invariant}: {v.message}", file=sys.stderr)
            return 1

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
