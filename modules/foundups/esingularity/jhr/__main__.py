"""Standalone JHR assessment entry point."""
from pathlib import Path

from .agent import run_once


def main() -> int:
    repo_root = Path(__file__).resolve().parents[4]
    result = run_once(repo_root)
    print(
        f"JHR status={result.status} score={result.significance_score} "
        f"evidence={result.evidence_count} publish_candidate={result.publish_candidate} "
        "public_published=False"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
