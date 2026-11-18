"""Pure five-tile planning contract, not a queue, approval or runtime executor.

Compose video + activity work around existing story_pipeline outputs. WRE/FAM
must independently admit any resulting work; a plan digest is only identity.
"""
from __future__ import annotations

import hashlib
import json
import re

# Stable criterion IDs map to EDUIT's TILE_PRODUCTION_RSI contract.
CHECKS = (
    "causality", "continuity", "sound_word_action", "science_age",
    "phone_tablet_controls", "touch_mouse_keyboard", "fullscreen_feedback",
    "pause_resume_reset", "solvability_scoring", "privacy_rights",
    "video_game_pair", "independent_output_review",
)
CONTRACT = "eduit.tile_acceptance.v1"


def _identifier(value, name):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", value):
        raise ValueError(f"Invalid {name}")
    return value


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


def prepare_tile_batch(*, batch_id, brief_sha256, tile_ids, max_repairs=2):
    """Return a bounded advisory DAG for exactly five ordered composite tiles.

    brief_sha256 identifies the agreed story/constraints, never verifies agreement.
    IDs are content IDs within kids_episodes/eduit, not new FoundUp identities.
    Repair counts are per tile; no model/host/credential is selected here.
    """
    _identifier(batch_id, "batch ID")
    if not isinstance(brief_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", brief_sha256):
        raise ValueError("Invalid brief digest")
    if not isinstance(tile_ids, (list, tuple)) or len(tile_ids) != 5:
        raise ValueError("A batch requires five tile IDs")
    ids = [_identifier(value, "tile ID") for value in tile_ids]
    if len(set(ids)) != 5:
        raise ValueError("Tile IDs must be unique")
    if type(max_repairs) is not int or not 0 <= max_repairs <= 3:
        raise ValueError("Repair limit must be 0..3")
    tickets = []
    for index, tile_id in enumerate(ids):
        build, review = f"{tile_id}:build", f"{tile_id}:review"
        tickets.extend([
            dict(id=build, role="author", tile_id=tile_id,
                 depends_on=[] if index == 0 else [f"{ids[index-1]}:review"],
                 requires=["video", "game", "cue_sheet", "continuity_state",
                           "learning_goal", "canonical_story_binding", "composite_manifest"],
                 max_repairs=max_repairs),
            dict(id=review, role="independent_verifier", tile_id=tile_id,
                 depends_on=[build], requires=list(CHECKS), max_repairs=0),
        ])
    tickets.append(dict(id="batch:joins", role="independent_verifier", tile_id=None,
                        depends_on=[f"{x}:review" for x in ids],
                        requires=["ordered_story_joins", "next_navigation", "retained_regressions"],
                        max_repairs=0))
    body = dict(schema_version="kids.tile_batch.v1", status="PLANNED_NOT_ADMITTED",
                batch_id=batch_id, brief_sha256=brief_sha256,
                foundup_id="kids_episodes", educational_context="eduit",
                acceptance_contract=CONTRACT, tile_ids=ids, tickets=tickets,
                runtime_activation=False)
    return {**body, "plan_sha256": _digest(body)}


def check_review_record(*, author_id, reviewer_id, artifact_sha256, record):
    """Check completeness of a local review record, NOT reviewer authentication.

    Return missing/failed criteria. Every check needs grade >=4 and evidence.
    Unknown/not-run evidence blocks readiness. Trusted runtime must separately
    verify identity, independence, evidence bytes, authority and artifact hashes.
    """
    _identifier(author_id, "author")
    _identifier(reviewer_id, "reviewer")
    if author_id == reviewer_id:
        return ["independent_output_review"]
    if not isinstance(artifact_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", artifact_sha256):
        raise ValueError("Invalid composite artifact digest")
    if not isinstance(record, dict) or record.get("artifact_sha256") != artifact_sha256:
        return ["artifact_binding"]
    if record.get("reviewer_id") != reviewer_id or record.get("contract") != CONTRACT:
        return ["review_binding"]
    checks = record.get("checks")
    if not isinstance(checks, dict):
        return list(CHECKS)
    failed = []
    for name in CHECKS:
        check = checks.get(name)
        if (not isinstance(check, dict) or type(check.get("grade")) is not int
                or not 4 <= check["grade"] <= 5
                or check.get("observed") is not True
                or not isinstance(check.get("evidence"), str)
                or not check["evidence"].strip() or len(check["evidence"]) > 2000):
            failed.append(name)
    return failed
