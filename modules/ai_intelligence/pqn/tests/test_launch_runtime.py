from unittest.mock import patch

from modules.ai_intelligence.pqn.scripts.launch import run_pqn_simulation_once


def test_run_pqn_simulation_once_returns_broker_friendly_summary():
    fake_result = {
        "runs": [{}, {}, {}],
        "summary_path": "modules/ai_intelligence/pqn_alignment/artifact_results/theory_archive_simulation/summary.json",
        "comparison": {
            "probe_closer_to_target": True,
        },
        "interpretation": {
            "outcome": "probe_advantage_requires_followup",
            "validated_truth": False,
            "archive_informed": True,
        },
    }

    with patch(
        "modules.ai_intelligence.pqn_alignment.src.pqn_alignment_dae.PQNAlignmentDAE",
    ) as dae_cls:
        dae_cls.return_value.run_theory_archive_simulation.return_value = fake_result
        result = run_pqn_simulation_once()

    assert result["status"] == "probe_advantage_requires_followup"
    assert result["run_count"] == 3
    assert result["probe_closer_to_target"] is True
    assert result["validated_truth"] is False
