"""CLI for the scope-free Public FoundUp Catalog projector (Phase 1).

Usage:
    python -m modules.foundups.public_catalog_projector --generate   # write artifact
    python -m modules.foundups.public_catalog_projector --validate   # validate committed artifact
    python -m modules.foundups.public_catalog_projector --check      # generate in-memory + validate (no write)

Exit codes:
    0 = projection is SAFE (allowlist-only + derived-from-registry)
    1 = one or more fail-closed safety violations (leak guard tripped / drift)
    2 = canonical source file missing or unreadable (fail-closed input error)

``--generate`` derives the artifact from the registry and validates it before
writing; it refuses to write an unsafe projection (exit 1, nothing written).
``--validate`` re-validates the already-committed artifact against the registry.
The projection path NEVER reads public/member/mall-video-catalog.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .src.projector import (
    DEFAULT_PROJECTION_PATH,
    SourceError,
    find_repo_root,
    generate_projection,
    load_registry,
    validate_projection,
    write_projection,
    _read_json,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m modules.foundups.public_catalog_projector",
        description=(
            "Derive and validate a scope-free public FoundUp catalog from the "
            "canonical registry. Validates ALLOWLIST-ONLY (leak guard) + "
            "DERIVED-FROM-REGISTRY, fail-closed."
        ),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--generate",
        action="store_true",
        help="Derive the projection, validate it, and write the artifact (refuses to write if unsafe).",
    )
    mode.add_argument(
        "--validate",
        action="store_true",
        help="Validate the already-committed projection artifact against the registry.",
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="Derive in-memory and validate without writing (default).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the full validation report as JSON on stdout.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Override repo-root detection.",
    )
    return parser


def _print_text_report(report, mode: str, out_path=None) -> None:
    print(f"PUBLIC_CATALOG_PROJECTOR_PHASE1 report ({mode})")
    print("-" * 60)
    print(f"registry_total              : {report.stats.get('registry_total')}")
    print(
        "registry_portfolio_eligible : "
        f"{report.stats.get('registry_portfolio_eligible')}"
    )
    print(f"projection_total            : {report.stats.get('projection_total')}")
    print(f"allowlist_size              : {report.stats.get('allowlist_size')}")
    print(f"errors                      : {report.error_count}")
    print(f"is_safe                     : {report.is_safe}")
    if out_path is not None:
        print(f"artifact_written            : {out_path}")
    print("-" * 60)
    if not report.violations:
        print("OK - projection is SAFE (allowlist-only, derived-from-registry).")
        return
    for v in report.violations:
        print(
            f"[{v.severity.upper()}] {v.rule_id} entity={v.entity!r} "
            f"field={v.field!r}"
        )
        print(f"    expected: {v.expected!r}")
        print(f"    actual  : {v.actual!r}")
        print(f"    -> {v.message}")


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        repo_root = args.repo_root or find_repo_root()
        registry = load_registry(repo_root)

        if args.validate:
            mode = "validate"
            projection = _read_json(repo_root / DEFAULT_PROJECTION_PATH)
            out_path = None
        else:
            projection = generate_projection(registry)
            out_path = None
            mode = "generate" if args.generate else "check"
    except SourceError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    report = validate_projection(projection, registry)

    written_path = None
    if args.generate:
        if not report.is_safe:
            # Fail-closed: never write an unsafe projection.
            if args.json:
                json.dump(report.to_dict(), sys.stdout, indent=2, sort_keys=True)
                sys.stdout.write("\n")
            else:
                _print_text_report(report, mode)
            print(
                "REFUSING to write: projection failed fail-closed safety guards.",
                file=sys.stderr,
            )
            return 1
        written_path = write_projection(projection, repo_root)

    if args.json:
        json.dump(report.to_dict(), sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        _print_text_report(report, mode, out_path=written_path)

    return 0 if report.is_safe else 1


if __name__ == "__main__":
    raise SystemExit(main())
