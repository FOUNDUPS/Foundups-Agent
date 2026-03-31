"""Channel Partner Pool tests for genesis registration and distribution mechanics."""

from __future__ import annotations

import pytest

from modules.foundups.simulator.economics.channel_partner_pool import (
    CHANNEL_PARTNER_CAP,
    ChannelPartnerPool,
    RegistryState,
    reset_channel_partner_pool,
)


@pytest.fixture(autouse=True)
def reset_pool():
    """Reset pool singleton before each test."""
    reset_channel_partner_pool()
    yield
    reset_channel_partner_pool()


class TestRegistration:
    """Test partner registration mechanics."""

    def test_successful_registration_before_closure(self) -> None:
        pool = ChannelPartnerPool()

        success, msg = pool.register_partner("partner_1", display_name="Test Partner")

        assert success is True
        assert "registered successfully" in msg
        assert pool.partner_count == 1
        assert pool.get_partner("partner_1") is not None

    def test_duplicate_registration_rejected(self) -> None:
        pool = ChannelPartnerPool()
        pool.register_partner("partner_1")

        success, msg = pool.register_partner("partner_1")

        assert success is False
        assert "already registered" in msg
        assert pool.partner_count == 1

    def test_registration_beyond_cap_rejected(self) -> None:
        pool = ChannelPartnerPool()

        # Fill to cap
        for i in range(CHANNEL_PARTNER_CAP):
            success, _ = pool.register_partner(f"partner_{i}")
            assert success is True

        assert pool.partner_count == CHANNEL_PARTNER_CAP
        assert pool.is_at_cap is True
        assert pool.remaining_slots == 0

        # Try one more
        success, msg = pool.register_partner("partner_overflow")

        assert success is False
        assert "cap" in msg.lower()
        assert pool.partner_count == CHANNEL_PARTNER_CAP

    def test_registration_after_closure_rejected(self) -> None:
        pool = ChannelPartnerPool()
        pool.register_partner("partner_1")

        # Close registry
        pool.close_on_mainnet_genesis(
            event_id="genesis_001",
            timestamp="2026-04-01T00:00:00Z",
            foundup_id="foundups_f0",
        )

        # Try to register after closure
        success, msg = pool.register_partner("partner_2")

        assert success is False
        assert "closed" in msg.lower()
        assert pool.partner_count == 1

    def test_remaining_slots_tracks_correctly(self) -> None:
        pool = ChannelPartnerPool()

        assert pool.remaining_slots == CHANNEL_PARTNER_CAP

        pool.register_partner("partner_1")
        assert pool.remaining_slots == CHANNEL_PARTNER_CAP - 1

        pool.register_partner("partner_2")
        assert pool.remaining_slots == CHANNEL_PARTNER_CAP - 2


class TestClosure:
    """Test mainnet genesis closure mechanics."""

    def test_close_on_mainnet_genesis_succeeds(self) -> None:
        pool = ChannelPartnerPool()
        pool.register_partner("partner_1")

        result = pool.close_on_mainnet_genesis(
            event_id="genesis_001",
            timestamp="2026-04-01T00:00:00Z",
            foundup_id="foundups_f0",
        )

        assert result is True
        assert pool.is_closed is True
        assert pool._state == RegistryState.CLOSED
        assert pool._closure_event is not None
        assert pool._closure_event.foundup_id == "foundups_f0"

    def test_double_closure_rejected(self) -> None:
        pool = ChannelPartnerPool()

        pool.close_on_mainnet_genesis("genesis_001", "2026-04-01T00:00:00Z", "f0")
        result = pool.close_on_mainnet_genesis("genesis_002", "2026-04-02T00:00:00Z", "f1")

        assert result is False
        assert pool._closure_event.event_id == "genesis_001"

    def test_closure_is_permanent(self) -> None:
        pool = ChannelPartnerPool()
        pool.close_on_mainnet_genesis("genesis_001", "2026-04-01T00:00:00Z", "f0")

        # Verify state cannot be changed
        assert pool.is_closed is True

        # Registration should fail
        success, _ = pool.register_partner("partner_1")
        assert success is False


class TestDistribution:
    """Test epoch distribution mechanics."""

    def test_equal_split_allocation_across_partners(self) -> None:
        pool = ChannelPartnerPool()
        pool.register_partner("partner_1")
        pool.register_partner("partner_2")
        pool.register_partner("partner_3")

        result = pool.distribute_epoch(epoch=1, pool_amount=300.0)

        assert result.partner_count == 3
        assert result.per_partner_amount == pytest.approx(100.0, abs=1e-9)
        assert result.distributions["partner_1"] == pytest.approx(100.0, abs=1e-9)
        assert result.distributions["partner_2"] == pytest.approx(100.0, abs=1e-9)
        assert result.distributions["partner_3"] == pytest.approx(100.0, abs=1e-9)

    def test_conservation_of_pool_amount(self) -> None:
        pool = ChannelPartnerPool()
        for i in range(5):
            pool.register_partner(f"partner_{i}")

        pool_amount = 1000.0
        result = pool.distribute_epoch(epoch=1, pool_amount=pool_amount)

        total_distributed = sum(result.distributions.values())
        assert total_distributed == pytest.approx(pool_amount, abs=1e-9)

    def test_zero_partners_edge_case(self) -> None:
        pool = ChannelPartnerPool()

        result = pool.distribute_epoch(epoch=1, pool_amount=100.0)

        assert result.partner_count == 0
        assert result.per_partner_amount == 0.0
        assert len(result.distributions) == 0

    def test_single_partner_gets_full_amount(self) -> None:
        pool = ChannelPartnerPool()
        pool.register_partner("solo_partner")

        result = pool.distribute_epoch(epoch=1, pool_amount=500.0)

        assert result.partner_count == 1
        assert result.per_partner_amount == pytest.approx(500.0, abs=1e-9)
        assert result.distributions["solo_partner"] == pytest.approx(500.0, abs=1e-9)

    def test_cumulative_allocations_tracked(self) -> None:
        pool = ChannelPartnerPool()
        pool.register_partner("partner_1")
        pool.register_partner("partner_2")

        pool.distribute_epoch(epoch=1, pool_amount=200.0)
        pool.distribute_epoch(epoch=2, pool_amount=200.0)
        pool.distribute_epoch(epoch=3, pool_amount=200.0)

        partner = pool.get_partner("partner_1")
        assert partner.total_fi_allocated == pytest.approx(300.0, abs=1e-9)  # 100 * 3
        assert partner.epochs_participated == 3


class TestStatistics:
    """Test pool statistics."""

    def test_stats_reflect_pool_state(self) -> None:
        pool = ChannelPartnerPool()
        pool.register_partner("partner_1")
        pool.distribute_epoch(epoch=1, pool_amount=100.0)

        stats = pool.get_stats()

        assert stats["partner_count"] == 1
        assert stats["cap"] == CHANNEL_PARTNER_CAP
        assert stats["remaining_slots"] == CHANNEL_PARTNER_CAP - 1
        assert stats["is_closed"] is False
        assert stats["closure_event"] is None
        assert stats["total_distributed"] == pytest.approx(100.0, abs=1e-9)
        assert stats["epochs_distributed"] == 1

    def test_stats_include_closure_event(self) -> None:
        pool = ChannelPartnerPool()
        pool.close_on_mainnet_genesis("genesis_001", "2026-04-01T00:00:00Z", "f0")

        stats = pool.get_stats()

        assert stats["is_closed"] is True
        assert stats["closure_event"]["event_id"] == "genesis_001"
        assert stats["closure_event"]["foundup_id"] == "f0"
