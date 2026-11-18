#!/usr/bin/env python3
"""One-shot RedDog judgment verifier bridge for the Foundups advisory extension.

Reads JSON from stdin and writes JSON to stdout. Pure local verifier: no network,
no subprocess, no filesystem read/write, no HoloIndex mutation. Evidence reading is
limited to the direct-read hit bodies supplied by the extension.

Input:
  {
    "prompt": "...",
    "output": "<final RedDog markdown>",
    "scorecard": {...},
    "direct_read_hits": [{"location": "repo/path.py", "content": "..."}]
  }

Output:
  {
    "ok": true,
    "prompt_has_determine": true|false,
    "answer_block_found": true|false,
    "verified": true|false,
    "refuted_count": int,
    "claims": [...],
    "index_gap_event": null|{...}
  }
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import PurePosixPath
from typing import Any, Dict, Mapping, Optional

REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.communication.moltbot_bridge.src.reddog_adversarial_verifier_panel import (  # noqa: E402
    build_index_gap_event,
    verify_answer_set,
)
from modules.communication.moltbot_bridge.src.reddog_determine_answer_contract import (  # noqa: E402
    is_determine_list_wellformed,
    parse_determine_questions,
)
from modules.communication.moltbot_bridge.src.reddog_repair_evidence_guard import (  # noqa: E402
    extract_determine_answers,
)

_LINE_REF_RE = re.compile(r"^(?P<path>.+):(?P<line>[1-9][0-9]*)$")


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


def _normalize_path(value: Any) -> str:
    raw = str(value or "").replace("\\", "/").strip()
    if not raw:
        return ""
    if raw.startswith("/") or raw.startswith("~"):
        return ""
    parts = []
    for part in PurePosixPath(raw).parts:
        if part in ("", "."):
            continue
        if part == "..":
            return ""
        parts.append(part)
    return "/".join(parts)


def _hit_map(hits: Any) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not isinstance(hits, list):
        return out
    for hit in hits:
        if not isinstance(hit, Mapping):
            continue
        loc = _normalize_path(hit.get("location"))
        content = hit.get("content")
        if loc and isinstance(content, str) and content:
            out[loc.lower()] = content
    return out


def _match_hit(path: str, hits: Mapping[str, str]) -> Optional[str]:
    want = _normalize_path(path).lower()
    if not want:
        return None
    if want in hits:
        return hits[want]
    for loc, content in hits.items():
        if loc.endswith("/" + want) or want.endswith("/" + loc):
            return content
    return None


def _window_for_ref(norm_ref: str, hits: Mapping[str, str]) -> Optional[str]:
    m = _LINE_REF_RE.match(str(norm_ref or ""))
    if not m:
        return None
    content = _match_hit(m.group("path"), hits)
    if not content:
        return None
    line_no = int(m.group("line"))
    lines = content.splitlines()
    if line_no < 1 or line_no > len(lines):
        return None
    start = max(0, line_no - 4)
    end = min(len(lines), line_no + 3)
    return "\n".join(lines[start:end])


def _summary(report: Mapping[str, Any]) -> dict:
    claims = report.get("claims") if isinstance(report, Mapping) else []
    if not isinstance(claims, list):
        claims = []
    verified_count = 0
    needs_count = 0
    note_count = 0
    for claim in claims:
        if not isinstance(claim, Mapping):
            continue
        verdict = str(claim.get("verdict") or "")
        if verdict in ("OBSERVED_VERIFIED", "INFERRED"):
            verified_count += 1
        elif verdict == "NEEDS_VERIFICATION":
            needs_count += 1
        notes = claim.get("notes")
        if isinstance(notes, list):
            note_count += len(notes)
    return {
        "verified_count": verified_count,
        "needs_verification_count": needs_count,
        "support_note_count": note_count,
    }


def main() -> int:
    try:
        payload = _read_stdin_json()
    except (json.JSONDecodeError, ValueError):
        return _out(ok=False, reason="invalid_json")

    prompt = payload.get("prompt")
    output = payload.get("output")
    if not isinstance(prompt, str) or not isinstance(output, str):
        return _out(ok=False, reason="missing_prompt_or_output")

    scorecard = payload.get("scorecard")
    if not isinstance(scorecard, Mapping):
        scorecard = {}

    questions = parse_determine_questions(prompt)
    prompt_has_determine = bool(questions and is_determine_list_wellformed(questions))
    answers = extract_determine_answers(output)
    if not prompt_has_determine:
        return _out(
            ok=True,
            prompt_has_determine=False,
            answer_block_found=answers is not None,
            applied=False,
            verified=True,
            refuted_count=0,
            claims=[],
            index_gap_event=build_index_gap_event(scorecard),
        )
    if answers is None:
        return _out(
            ok=True,
            prompt_has_determine=True,
            answer_block_found=False,
            applied=True,
            verified=False,
            refuted_count=len(questions),
            claims=[],
            index_gap_event=build_index_gap_event(scorecard),
            reason="missing_determine_answers_block",
        )

    hits = _hit_map(payload.get("direct_read_hits"))
    report = verify_answer_set(
        answers,
        scorecard=scorecard,
        read_evidence=lambda ref: _window_for_ref(ref, hits),
    ).to_dict()
    summary = _summary(report)
    return _out(
        ok=True,
        prompt_has_determine=True,
        answer_block_found=True,
        applied=True,
        verified=report.get("verified") is True,
        refuted_count=report.get("refuted_count", 0),
        claims=report.get("claims", []),
        index_gap_event=report.get("index_gap_event"),
        **summary,
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # fail-closed: never crash the extension path
        sys.stdout.write(json.dumps({"ok": False, "reason": "verifier_exception",
                                     "detail": type(exc).__name__}, ensure_ascii=True))
        sys.stdout.write("\n")
        raise SystemExit(0)
