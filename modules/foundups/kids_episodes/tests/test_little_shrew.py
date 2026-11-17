"""Preset integration with the canonical compiler; no provider or account access."""
import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from modules.foundups.kids_episodes.src.little_shrew import SERIES_ROOT, build_pilot
from modules.foundups.kids_episodes.src.story_pipeline import compile_plan


def test_pilot_roundtrips_canonical_controller_contract():
    plan = build_pilot(request_id="shrew-pilot")
    assert compile_plan(plan["raw_story"], plan, request_id=plan["request_id"],
                        supported_durations=plan["supported_durations"]) == plan
    assert len(plan["episodes"]) == 3
    shots = [s for e in plan["episodes"] for s in e["shots"]]
    assert [s["beat_id"] for s in shots] == [f"b{i:02d}" for i in range(1, 10)]
    assert sum(s["edit_seconds"] for s in shots) == 45
    assert all(s["generation_seconds"] == 6 for s in shots)
    assert "all three babies" in plan["raw_story"]
    assert "everyone remains sheltered safely" in plan["raw_story"]
    assert plan["bible"]["source"]["image_status"] == "not_retrieved"
    for a, b in zip(plan["episodes"], plan["episodes"][1:]):
        assert a["end_state"] == b["start_state"]
        assert a["source_end"] == b["source_start"]
    assert all(c["text"].startswith("[") for e in plan["episodes"] for c in e["captions"])


@pytest.mark.parametrize("durations,expected", [((5,), 5), ((8, 4), 8), ((10, 6), 6)])
def test_provider_capability_selection(durations, expected):
    plan = build_pilot(request_id="caps", supported_durations=durations)
    assert plan["episodes"][0]["shots"][0]["generation_seconds"] == expected


@pytest.mark.parametrize("durations", [(), (4,), (True, 6), (float("nan"), 6), (121,), (-1, 6), ("6",)])
def test_unsupported_or_invalid_provider_rejected(durations):
    with pytest.raises(ValueError):
        build_pilot(request_id="invalid", supported_durations=durations)


def test_references_are_portable_hashed_and_reuse_one_rig():
    plan = build_pilot(request_id="assets")
    root = Path(__file__).resolve().parents[4]
    for ref in plan["bible"]["reference_assets"]:
        assert not Path(ref["path"]).is_absolute()
        assert hashlib.sha256((root / ref["path"]).read_bytes()).hexdigest() == ref["sha256"]
    ns = {"s": "http://www.w3.org/2000/svg"}
    rig = ET.parse(SERIES_ROOT / "character.svg").find("s:defs", ns)
    board = ET.parse(SERIES_ROOT / "storyboard.svg").find("s:defs", ns)
    assert ET.tostring(rig) == ET.tostring(board)
    assert len(rig.findall("s:g[@id='body']", ns)) == 1
    assert len(rig.findall("s:g/s:use[@href='#body']", ns)) == 4
