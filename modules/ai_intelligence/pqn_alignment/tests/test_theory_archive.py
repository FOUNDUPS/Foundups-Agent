from modules.ai_intelligence.pqn_alignment import (
    PQNAlignmentDAE,
    get_theory_archive_context,
)


def test_theory_archive_manifest_exists():
    context = get_theory_archive_context()

    assert context["archive_ready"] is True
    assert context["mode"] == "detector_first_theory_archive"
    assert "framework" in context["documents"]
    assert "simulation_plan" in context["documents"]
    assert context["documents"]["framework"]["exists"] is True
    assert context["documents"]["simulation_plan"]["exists"] is True


def test_theory_archive_targets_reference_live_detector_surfaces(monkeypatch):
    monkeypatch.setattr(PQNAlignmentDAE, "_init_chat_broadcaster", lambda self: None)
    monkeypatch.setattr(PQNAlignmentDAE, "_register_with_wre", lambda self: None)

    dae = PQNAlignmentDAE()
    api = dae.get_0102_api()

    assert "theory_archive" in api
    context = api["theory_archive"]
    assert context["archive_ready"] is True

    target_paths = {item["relative_path"] for item in context["implementation_targets"]}
    assert "WSP_agentic/tests/pqn_detection/cmst_pqn_detector_v3.py" in target_paths
    assert "modules/ai_intelligence/pqn_alignment/src/detector/api.py" in target_paths
