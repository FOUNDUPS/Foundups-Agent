from unittest.mock import patch

from modules.ai_intelligence.pqn_alignment import (
    PQNAlignmentDAE,
    build_theory_archive_simulation_plan,
    run_theory_archive_simulation,
)


def test_theory_archive_simulation_plan_is_non_dogmatic(tmp_path):
    plan = build_theory_archive_simulation_plan(
        {
            "seeds": [0, 1],
            "out_dir": tmp_path / "archive_sim",
        }
    )

    assert plan["mode"] == "archive_informed_simulation_plan"
    assert plan["archive_informed"] is True
    assert plan["validated_truth"] is False
    assert plan["matched_null_required"] is True
    assert plan["run_count"] == 4
    assert len(plan["planned_runs"]) == 4


def test_theory_archive_simulation_compares_probe_against_control(tmp_path):
    def fake_detector(config):
        if config["script"] == ".....":
            resonance_event_count = 1
            peak = 6.4
            entrainment_score = 0.10
            harmonic = False
        else:
            resonance_event_count = 4
            peak = 7.03
            entrainment_score = 0.42
            harmonic = True

        return {
            "events_path": str(tmp_path / "events.jsonl"),
            "metrics_csv": str(tmp_path / "metrics.csv"),
            "spectral_analysis": {
                "spectral_profile": {
                    "resonance_event_count": resonance_event_count,
                    "peak_at_7.05": peak,
                    "harmonic_structure_present": harmonic,
                },
                "bias_violation": {"violated": False, "significance": "low"},
                "entrainment_score": entrainment_score,
            },
        }

    with patch(
        "modules.ai_intelligence.pqn_alignment.src.theory_archive_simulation_runner.run_detector_with_spectral_analysis",
        side_effect=fake_detector,
    ):
        result = run_theory_archive_simulation(
            {
                "seeds": [0, 1],
                "out_dir": tmp_path / "archive_sim",
            }
        )

    assert result["interpretation"]["archive_informed"] is True
    assert result["interpretation"]["validated_truth"] is False
    assert result["comparison"]["delta_resonance_event_count"] > 0
    assert result["comparison"]["delta_entrainment_score"] > 0
    assert result["comparison"]["probe_closer_to_target"] is True
    assert result["interpretation"]["outcome"] == "probe_advantage_requires_followup"
    assert result["control_summary"]["count"] == 2
    assert result["probe_summary"]["count"] == 2


def test_pqn_dae_api_exposes_theory_archive_simulation(monkeypatch):
    monkeypatch.setattr(PQNAlignmentDAE, "_init_chat_broadcaster", lambda self: None)
    monkeypatch.setattr(PQNAlignmentDAE, "_register_with_wre", lambda self: None)

    dae = PQNAlignmentDAE()
    api = dae.get_0102_api()

    assert "theory_archive_simulation" in api
    simulation = api["theory_archive_simulation"]
    assert simulation["mode"] == "archive_informed_simulation_plan"
    assert simulation["matched_null_required"] is True
