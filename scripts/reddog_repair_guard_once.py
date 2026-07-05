#!/usr/bin/env python3
"""One-shot RedDog repair-evidence GUARD bridge for the FoundUps advisory extension.

Reads JSON from stdin and writes JSON to stdout (mirrors advisory_model_once.py's contract).
Pure-text: no network, no repo mutation, no secrets. Two actions:

  {"action": "protect", "prompt": "...", "primary": "<primary markdown>"}
    -> {"ok": true, "has_determine": bool, "protected_context": "<text to prepend to the
        repair_minimal context>"}  (protected_context is "" when there is no Determine block)

  {"action": "guard", "prompt": "...", "primary": "<primary>", "repaired": "<merged repair>"}
    -> {"ok": true, "has_determine": bool, "preserved": bool, "keep_original": bool,
        "reason_codes": [...]}   (keep_original true => the extension must DISCARD the repaired
        output and keep the primary + its original validation failure)

The heavy lifting REUSES reddog_repair_evidence_guard (which reuses the Determine contract's
assert_repair_preserves); this script is a thin, fail-closed stdin/stdout adapter. Any error
returns ok=false with a reason; the caller MUST treat a non-ok guard result as keep_original.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.communication.moltbot_bridge.src.reddog_repair_evidence_guard import (  # noqa: E402
    build_protected_repair_context,
    extract_determine_answers,
    guard_repair_from_outputs,
)
from modules.communication.moltbot_bridge.src.reddog_determine_answer_contract import (  # noqa: E402
    is_determine_list_wellformed,
    parse_determine_questions,
)


def _out(**fields: object) -> int:
    sys.stdout.write(json.dumps(fields, ensure_ascii=True, sort_keys=True))
    sys.stdout.write("\n")
    return 0


def _read_stdin_json() -> dict:
    raw = sys.stdin.buffer.read()
    data = json.loads(raw.decode("utf-8", errors="replace"))
    if not isinstance(data, dict):
        raise json.JSONDecodeError("expected JSON object", "", 0)
    return data


def main() -> int:
    try:
        payload = _read_stdin_json()
    except (json.JSONDecodeError, ValueError):
        return _out(ok=False, reason="invalid_json")

    action = payload.get("action")
    prompt = payload.get("prompt")
    primary = payload.get("primary")
    if not isinstance(prompt, str) or not isinstance(primary, str):
        return _out(ok=False, reason="missing_prompt_or_primary")

    if action == "protect":
        questions = parse_determine_questions(prompt)
        primary_answers = extract_determine_answers(primary)
        if not questions or not is_determine_list_wellformed(questions) or not primary_answers:
            return _out(ok=True, has_determine=False, protected_context="")
        return _out(
            ok=True,
            has_determine=True,
            protected_context=build_protected_repair_context(primary_answers),
        )

    if action == "guard":
        repaired = payload.get("repaired")
        if not isinstance(repaired, str):
            return _out(ok=False, reason="missing_repaired")
        d = guard_repair_from_outputs(prompt, primary, repaired)
        return _out(
            ok=True,
            has_determine=d.has_determine,
            preserved=d.preserved,
            keep_original=d.keep_original,
            reason_codes=list(d.reason_codes),
        )

    return _out(ok=False, reason="unknown_action")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # fail-closed: never crash the extension repair path
        sys.stdout.write(json.dumps({"ok": False, "reason": "guard_exception",
                                     "detail": type(exc).__name__}, ensure_ascii=True))
        sys.stdout.write("\n")
        raise SystemExit(0)
