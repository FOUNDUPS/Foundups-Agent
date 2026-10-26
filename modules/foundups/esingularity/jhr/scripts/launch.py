"""Launcher for one Japan Hyperscaler Report assessment cycle."""

from __future__ import annotations

import json
from dataclasses import asdict

from modules.foundups.esingularity.jhr.src.jhr_agent import run_jhr_cycle
from modules.foundups.esingularity.jhr.src.rss_retriever import discover_candidates


def run_jhr_once(retriever=None, *, threshold: int = 12) -> dict:
    """Run one cycle and return a JSON-serializable WSP_97 evidence packet."""
    result = run_jhr_cycle(retriever=retriever, threshold=threshold)
    return asdict(result)


def main() -> int:
    result = run_jhr_once(retriever=discover_candidates)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
