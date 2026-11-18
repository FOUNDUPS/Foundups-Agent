"""Explicit one-shot OpenRouter model catalog candidate refresh."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.ai_intelligence.ai_gateway.src.model_openrouter_direct_discovery import (  # noqa: E402
    discover_openrouter_model_catalog,
)
from modules.ai_intelligence.ai_gateway.src.model_provider_catalog_snapshot import (  # noqa: E402
    build_discovery_invocation,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Perform one explicit, bounded OpenRouter model-list refresh."
    )
    parser.add_argument("--mode", choices=("manual", "scheduled"), required=True)
    parser.add_argument("--schedule-id")
    parser.add_argument("--scheduled-for-ms", type=int)
    parser.add_argument("--expires-at-ms", type=int)
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--attempt-path", type=Path, required=True)
    parser.add_argument("--candidate-path", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        invocation = build_discovery_invocation(
            mode=args.mode,
            schedule_id=args.schedule_id,
            scheduled_for_ms=args.scheduled_for_ms,
            expires_at_ms=args.expires_at_ms,
        )
    except ValueError:
        parser.error(
            "manual mode requires null schedule fields; scheduled mode requires all schedule fields"
        )
    result = asyncio.run(
        discover_openrouter_model_catalog(
            invocation,
            repo_root=REPO_ROOT,
            runtime_root=args.runtime_root,
            attempt_path=args.attempt_path,
            candidate_path=args.candidate_path,
        )
    )
    print(json.dumps(result.receipt.to_dict(), sort_keys=True, separators=(",", ":")))
    return 0 if result.receipt.outcome == "COMPLETED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
