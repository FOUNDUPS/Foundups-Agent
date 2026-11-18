"""Non-authoritative story requests and a fail-closed adapter to existing WRE.

A request/work-order ID is a correlation reference, never signed admission.
Only the trusted runtime supplies WRE, workspace and execution bundle identity.
Production executor must bind story_pipeline callbacks to current owner authority;
this module neither creates that authority nor invokes providers directly.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re

SKILL_NAME = "kids_episode_production"
SCHEMA = "kids.story_request.v1"


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def prepare_episode_request(raw_story, *, request_id, supported_durations=(4, 6, 8),
                            confirmed_terms=None, preset="draft", orientation="landscape",
                            max_attempts=2, work_order_id=None):
    """Prepare canonical data without granting execution or resolving voice terms."""
    if not isinstance(raw_story, str) or not raw_story.strip() or len(raw_story) > 20000:
        raise ValueError("Story must contain 1 to 20000 characters")
    if not isinstance(request_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", request_id):
        raise ValueError("Invalid request ID")
    durations = list(supported_durations)
    if not durations or len(durations) > 12 or any(
        type(x) not in (int, float) or not math.isfinite(x) or not 0 < x <= 120 for x in durations
    ):
        raise ValueError("Invalid supported durations")
    terms = {} if confirmed_terms is None else confirmed_terms
    if not isinstance(terms, dict) or len(terms) > 20 or any(
        not isinstance(k, str) or not isinstance(v, str) or not k.strip() or not v.strip()
        or len(k) > 100 or len(v) > 100 or k not in raw_story for k, v in terms.items()
    ):
        raise ValueError("Invalid confirmed terms")
    if preset not in ("draft", "final") or orientation not in ("landscape", "portrait"):
        raise ValueError("Invalid render options")
    if type(max_attempts) is not int or not 1 <= max_attempts <= 3:
        raise ValueError("Attempts must be between one and three")
    if work_order_id is not None and (
        not isinstance(work_order_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,120}", work_order_id)
    ):
        raise ValueError("Invalid work-order reference")
    body = dict(schema_version=SCHEMA, foundup_id="kids_episodes", action="produce_story",
                request_id=request_id, raw_story=raw_story,
                supported_durations=sorted(set(float(x) for x in durations)),
                confirmed_terms=dict(terms), preset=preset, orientation=orientation,
                max_attempts=max_attempts, work_order_id=work_order_id)
    return {**body, "request_digest": _digest(body)}


def _blocked(request, reason, missing):
    return {"status": "BLOCKED", "success": False, "request": request,
            "reason": reason, "missing_bindings": missing}


def _verify_outputs(result, workspace):
    outcome = result.get("outcome")
    if not isinstance(outcome, dict) or outcome.get("status") not in (
        "episodes_reviewed_assembly_pending", "assembled_unreviewed", "story_reviewed"
    ):
        raise ValueError("Executor must return the story pipeline outcome")
    episodes = outcome.get("episodes")
    if not isinstance(episodes, list) or not 1 <= len(episodes) <= 24:
        raise ValueError("No episode output evidence")
    root = workspace.resolve(strict=True)
    def verify(path, digest):
        path = Path(path).resolve(strict=True)
        path.relative_to(root)
        if not path.is_file() or not 0 < path.stat().st_size <= 2 * 1024**3:
            raise ValueError("Missing output file")
        hasher = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                hasher.update(chunk)
        if hasher.hexdigest() != digest:
            raise ValueError("Output digest mismatch")
    for episode in episodes:
        verify(episode["video_path"], episode["sha256"])
        review = episode.get("review", {})
        if review.get("artifact_sha256") != episode["sha256"] or not review.get("reviewer_id"):
            raise ValueError("Review must bind the output")
        checks = review.get("checks", {})
        if any(checks.get(k) is not True for k in (
            "education", "safety", "continuity", "audio", "captions", "rights"
        )):
            raise ValueError("Incomplete output review")
    if outcome["status"] in ("assembled_unreviewed", "story_reviewed"):
        story = outcome["story_video"]
        verify(story["path"], story["sha256"])
        if outcome["status"] == "story_reviewed":
            review = outcome.get("story_review", {})
            if (review.get("artifact_sha256") != story["sha256"]
                    or not isinstance(review.get("reviewer_id"), str) or not review["reviewer_id"].strip()
                    or any(review.get("checks", {}).get(k) is not True for k in (
                        "education", "safety", "continuity", "audio", "captions", "rights", "joins"))):
                raise ValueError("Incomplete review of assembled story")
    return outcome


def dispatch_episode_request(request, *, wre=None, workspace=None, execution_binding_digest=None):
    """Invoke existing admitted WRE only; never treat an LLM proposal as output.

    The optional objects are trusted host bindings, not request fields. Scanner,
    signed effect authorization and provider selection remain with existing owners.
    No executor ships here: prototype deployment truthfully returns BLOCKED.
    """
    try:
        expected = prepare_episode_request(**{key: request[key] for key in (
            "raw_story", "request_id", "supported_durations", "confirmed_terms",
            "preset", "orientation", "max_attempts", "work_order_id"
        )})
        if request != expected:
            raise ValueError("Noncanonical or modified request")
    except (KeyError, TypeError, ValueError) as exc:
        return _blocked(request, str(exc), ["valid canonical request"])
    if wre is None:
        return _blocked(request, "WRE runtime is unavailable", ["trusted WRE runtime",
            "production-admitted executor", "signed provider/reviewer authority bindings"])
    from modules.infrastructure.wre_core.src.registered_skill_executor import (
        validate_runtime_skill_admission, resolve_registered_skill_executor,
    )
    try:
        loader = wre.skills_loader
        admitted, reason = validate_runtime_skill_admission(skills_loader=loader, skill_name=SKILL_NAME)
        if not admitted:
            return _blocked(request, reason, ["matching production registry and Skillz admission"])
        executor = resolve_registered_skill_executor(repo_root=Path(loader.repo_root),
                                                    skill_file=loader.resolve_skill_file(SKILL_NAME))
        if executor is None:
            return _blocked(request, "No registered programmatic executor; proposal fallback disabled",
                            ["scanner-bound executor with signed provider/reviewer callbacks"])
        if workspace is None or not isinstance(execution_binding_digest, str) or not re.fullmatch(
            r"[0-9a-f]{64}", execution_binding_digest
        ):
            return _blocked(request, "Trusted execution bindings are incomplete",
                            ["owner-selected output workspace and execution bundle digest"])
        root = Path(workspace).resolve(strict=True)
        if not root.is_dir():
            raise ValueError("Output workspace must be a directory")
        response = wre.execute_skill(SKILL_NAME, agent="qwen", input_context={
            "operation": "produce_story", "request": expected, "workspace": str(root),
            "execution_binding_digest": execution_binding_digest,
        }, force=False)
        if not isinstance(response, dict) or response.get("success") is not True:
            return _blocked(request, "WRE did not produce a successful execution", ["successful admitted execution"])
        result = response.get("result", {})
        binding = result.get("_skill_binding", {})
        receipts = result.get("effect_receipts")
        if (result.get("_executor_dispatch") is not True or result.get("_effect_evidence") is not True
            or binding.get("schema_version") != "wre_skill_execution_binding.v1"
            or not response.get("execution_id") or binding.get("execution_id") != response["execution_id"]
            or not re.fullmatch(r"[0-9a-f]{64}", str(binding.get("scanner_admission_fingerprint", "")))
            or not re.fullmatch(r"sha256:[0-9a-f]{64}", str(binding.get("loaded_skill_sha256", "")))
            or not isinstance(receipts, list) or not receipts or any(
                not isinstance(r, dict) or not isinstance(r.get("receipt_id"), str) or not r["receipt_id"].strip()
                or not isinstance(r.get("effect_type"), str) or not r["effect_type"].strip() for r in receipts)):
            raise ValueError("Missing bound executor effect evidence")
        outcome = _verify_outputs(result, root)
        return {"status": outcome["status"], "success": True, "request": expected,
                "execution_id": response["execution_id"], "outcome": outcome}
    except Exception as exc:
        return _blocked(request, f"Execution/evidence validation failed: {type(exc).__name__}",
                        ["valid admitted execution and verified output evidence"])
