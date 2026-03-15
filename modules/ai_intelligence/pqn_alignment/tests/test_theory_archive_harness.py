from unittest.mock import patch

from modules.ai_intelligence.pqn_alignment import (
    PQNAlignmentDAE,
    build_theory_archive_harness_spec,
    run_theory_archive_detector_harness,
)


def test_theory_archive_harness_spec_is_archive_informed():
    spec = build_theory_archive_harness_spec()

    assert spec["mode"] == "archive_informed_non_dogmatic"
    assert spec["matched_null_required"] is True
    assert spec["target_resonance_hz"] == 7.05
    assert "spectral_gap_ratio" in spec["observables"]
    assert "detection_signal_eta" in spec["observables"]
    assert spec["detector_surface"] == "run_detector_with_spectral_analysis"


def test_theory_archive_harness_routes_through_existing_detector_surface():
    fake_result = {
        "events_path": "events.jsonl",
        "metrics_csv": "metrics.csv",
        "spectral_analysis": {"bias_violation": {"violated": False}},
    }

    with patch(
        "modules.ai_intelligence.pqn_alignment.src.theory_archive_harness.run_detector_with_spectral_analysis",
        return_value=fake_result,
    ) as mocked:
        result = run_theory_archive_detector_harness({"steps": 120})

    mocked.assert_called_once()
    detector_config = mocked.call_args.args[0]
    assert detector_config["steps"] == 120
    assert detector_config["dt"] == 0.5 / 7.05
    assert result["interpretation"]["archive_informed"] is True
    assert result["interpretation"]["validated_truth"] is False
    assert result["interpretation"]["matched_null_required"] is True


def test_pqn_dae_api_exposes_theory_archive_harness(monkeypatch):
    monkeypatch.setattr(PQNAlignmentDAE, "_init_chat_broadcaster", lambda self: None)
    monkeypatch.setattr(PQNAlignmentDAE, "_register_with_wre", lambda self: None)

    dae = PQNAlignmentDAE()
    api = dae.get_0102_api()

    assert "theory_archive_harness" in api
    harness = api["theory_archive_harness"]
    assert harness["mode"] == "archive_informed_non_dogmatic"
    assert harness["matched_null_required"] is True
