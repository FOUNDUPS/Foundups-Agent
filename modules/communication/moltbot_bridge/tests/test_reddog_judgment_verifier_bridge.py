import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "scripts" / "reddog_judgment_verifier_once.py"


def _run(payload: dict) -> dict:
    proc = subprocess.run(
        [sys.executable, "-B", str(SCRIPT)],
        input=json.dumps(payload).encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(ROOT),
        check=True,
        timeout=15,
    )
    lines = proc.stdout.decode("utf-8").strip().splitlines()
    assert lines, proc.stderr.decode("utf-8", errors="replace")
    return json.loads(lines[-1])


def _prompt() -> str:
    return (
        "Audit.\n\n"
        "Determine:\n"
        "1. Does build_foundup dispatch exist?\n"
    )


def _answer(evidence_refs):
    return (
        "## Determine Answers\n\n"
        "```json\n"
        + json.dumps(
            [
                {
                    "index": 1,
                    "question_text": "Does build_foundup dispatch exist?",
                    "answer": "yes",
                    "wsp97_label": "OBSERVED",
                    "evidence_refs": evidence_refs,
                }
            ],
            sort_keys=True,
        )
        + "\n```\n"
    )


def test_bridge_verifies_against_supplied_direct_read_hit() -> None:
    out = _run(
        {
            "prompt": _prompt(),
            "output": _answer(["modules/foundups/agent/src/hermes_foundup_job_executor.py:2"]),
            "scorecard": {
                "direct_read_fallback_used": True,
                "direct_read_paths": ["modules/foundups/agent/src/hermes_foundup_job_executor.py"],
            },
            "direct_read_hits": [
                {
                    "location": "modules/foundups/agent/src/hermes_foundup_job_executor.py",
                    "content": "class Builder:\n    def build_foundup(self):\n        return True\n",
                }
            ],
        }
    )
    assert out["ok"] is True
    assert out["applied"] is True
    assert out["verified"] is True
    assert out["verified_count"] == 1
    assert out["refuted_count"] == 0
    assert out["index_gap_event"]["event"] == "INDEX_GAP"


def test_bridge_refutes_missing_answer_block_for_determine_prompt() -> None:
    out = _run(
        {
            "prompt": _prompt(),
            "output": "## Decision\nNo canonical answer block.\n",
            "scorecard": {},
            "direct_read_hits": [],
        }
    )
    assert out["ok"] is True
    assert out["applied"] is True
    assert out["verified"] is False
    assert out["reason"] == "missing_determine_answers_block"
    assert out["refuted_count"] == 1


def test_bridge_refutes_unsupported_evidence_window() -> None:
    out = _run(
        {
            "prompt": _prompt(),
            "output": _answer(["modules/foundups/agent/src/hermes_foundup_job_executor.py:2"]),
            "scorecard": {},
            "direct_read_hits": [
                {
                    "location": "modules/foundups/agent/src/hermes_foundup_job_executor.py",
                    "content": "class Builder:\n    def extract_foundup(self):\n        return True\n",
                }
            ],
        }
    )
    assert out["verified"] is False
    assert out["refuted_count"] == 1
    assert "REFUTE_SUPPORT_NOT_FOUND" in out["claims"][0]["refutations"]


def test_bridge_refutes_scorecard_rejected_path() -> None:
    out = _run(
        {
            "prompt": _prompt(),
            "output": _answer(["modules/foundups/agent/src/hermes_foundup_job_executor.py:2"]),
            "scorecard": {
                "direct_read_rejected": [
                    {
                        "path": "modules/foundups/agent/src/hermes_foundup_job_executor.py",
                        "reason": "not_a_file",
                    }
                ]
            },
            "direct_read_hits": [
                {
                    "location": "modules/foundups/agent/src/hermes_foundup_job_executor.py",
                    "content": "class Builder:\n    def build_foundup(self):\n        return True\n",
                }
            ],
        }
    )
    assert out["verified"] is False
    assert "REFUTE_SCORECARD_CONTRADICTION" in out["claims"][0]["refutations"]


def test_bridge_noops_without_determine_prompt_but_still_emits_index_gap_event() -> None:
    out = _run(
        {
            "prompt": "Audit without numbered questions.",
            "output": "## Decision\nDone.\n",
            "scorecard": {"index_gap_detected": True, "direct_read_paths": ["modules/a.py"]},
            "direct_read_hits": [],
        }
    )
    assert out["ok"] is True
    assert out["applied"] is False
    assert out["verified"] is True
    assert out["index_gap_event"]["event"] == "INDEX_GAP"
