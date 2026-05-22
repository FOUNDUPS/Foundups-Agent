"""CLI entrypoint for the Portfolio Data Validator (Phase 1).

Usage:
    python -m modules.foundups.portfolio_validator --check

Exit codes:
    0 = all rules pass (no drift detected)
    1 = one or more rule violations (drift detected); structured report printed
    2 = canonical source file missing or unreadable (fail-closed input error)

This CLI is intentionally READ-ONLY. No ``--fix`` or ``--update`` flag is
exposed in Phase 1; remediation is a separate slice
(``PORTFOLIO_DATA_GENERATOR_PHASE1``).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .src.validator import (
    SourceError,
    find_repo_root,
    load_sources,
    run_validation,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m modules.foundups.portfolio_validator",
        description=(
            "Read-only drift detector for public/f/portfolio_data.json "
            "against canonical registry/catalog/manifest sources."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run all rules and report violations (default action).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the full report as a JSON document on stdout.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help=(
            "Override repo root detection. Defaults to walking up from this "
            "package until a directory with modules/, WSP_framework/, and "
            "public/ is found."
        ),
    )
    return parser


def _print_text_report(report) -> None:
    print("PORTFOLIO_DATA_VALIDATOR_PHASE1 report")
    print("-" * 60)
    print(
        f"registry_total              : {report.stats.get('registry_total')}"
    )
    print(
        "registry_portfolio_eligible : "
        f"{report.stats.get('registry_portfolio_eligible')}"
    )
    print(
        f"projection_total            : {report.stats.get('projection_total')}"
    )
    print(f"errors                      : {report.error_count}")
    print(f"warnings                    : {report.warning_count}")
    print("-" * 60)
    if not report.violations:
        print("OK - no drift detected.")
        return
    for v in report.violations:
        print(
            f"[{v.severity.upper()}] {v.rule_id} entity={v.entity!r} "
            f"field={v.field!r} source={v.source}"
        )
        print(f"    expected: {v.expected!r}")
        print(f"    actual  : {v.actual!r}")
        print(f"    -> {v.message}")


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        repo_root = args.repo_root or find_repo_root()
        sources = load_sources(repo_root)
    except SourceError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    report = run_validation(sources)

    if args.json:
        json.dump(report.to_dict(), sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        _print_text_report(report)

    return 1 if report.has_errors or report.warning_count > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
