"""Runtime wiring tests for epoch ledger and Layer-D anchoring."""

from __future__ import annotations

import pytest
from types import SimpleNamespace

from modules.foundups.simulator.config import SimulatorConfig
from modules.foundups.simulator.economics.pool_distribution import (
    ActivityLevel,
    ParticipantType,
)
from modules.foundups.simulator.mesa_model import FoundUpsModel


def _prime_epoch_distribution_inputs(model: FoundUpsModel) -> None:
    """Ensure pool distribution has participants + stake base."""
    model.pool_distributor.register_participant(
        participant_id="anchor_participant_001",
        p_type=ParticipantType.UN,
        activity=ActivityLevel.UN,
    )
    model.state_store.get_state().total_stakes = 10_000


def test_layer_d_anchor_publishes_on_configured_cadence(tmp_path) -> None:
    """Anchor should publish only on configured epoch cadence."""
    model = FoundUpsModel(
        config=SimulatorConfig(
            num_founder_agents=0,
            num_user_agents=0,
            seed=17,
            agent_action_probability=0.0,
            layer_d_anchor_enabled=True,
            layer_d_anchor_every_n_epochs=2,
            layer_d_anchor_mode="mock",
            layer_d_anchor_db_path=str(tmp_path / "anchor_state.db"),
        )
    )
    _prime_epoch_distribution_inputs(model)

    for _ in range(3):
        model._apply_demurrage_cycle()

    stats = model.get_stats()
    assert stats["epochs_completed"] == 3
    assert stats["layer_d_anchor_enabled"] is True
    assert stats["layer_d_anchor_total_published"] == 1
    assert len(model._epoch_ledger.entries) == 3

    assert model._anchor_connector is not None
    records = model._anchor_connector.get_anchor_status("F_0")
    assert len(records) == 1
    assert records[0]["epoch"] == 2
    assert records[0]["status"] == "published"


def test_layer_d_anchor_disabled_records_epoch_without_publish() -> None:
    """Ledger recording should still happen when Layer-D publish is disabled."""
    model = FoundUpsModel(
        config=SimulatorConfig(
            num_founder_agents=0,
            num_user_agents=0,
            seed=23,
            agent_action_probability=0.0,
            layer_d_anchor_enabled=False,
        )
    )
    _prime_epoch_distribution_inputs(model)

    model._apply_demurrage_cycle()

    stats = model.get_stats()
    assert stats["epochs_completed"] == 1
    assert stats["layer_d_anchor_enabled"] is False
    assert stats["layer_d_anchor_total_published"] == 0
    assert len(model._epoch_ledger.entries) == 1


@pytest.mark.parametrize("selected", ["unknown", "", None, 1, "testnet", "mainnet"])
def test_layer_d_selected_mode_never_falls_back_to_mock(tmp_path, selected):
    config = SimpleNamespace(layer_d_anchor_enabled=True, layer_d_anchor_mode=selected,
        layer_d_anchor_db_path=str(tmp_path / "unused" / "anchor.db"))
    model = SimpleNamespace(_config=config)
    with pytest.raises(ValueError):
        FoundUpsModel._build_anchor_connector(model)
    assert not (tmp_path / "unused").exists()
