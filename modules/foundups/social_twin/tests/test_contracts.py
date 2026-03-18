"""Tests for Social Twin FoundUp contracts."""

from modules.foundups.social_twin.src import (
    MorningReviewPacket,
    OpportunityCandidate,
    QueueStatus,
    SocialTwinRole,
    default_social_twin_topology,
)


def test_default_topology_splits_orchestrator_and_engager():
    topology = default_social_twin_topology()

    assert topology.orchestrator.role == SocialTwinRole.ORCHESTRATOR
    assert topology.orchestrator.mutation_allowed is False
    assert topology.engager.role == SocialTwinRole.ENGAGER
    assert topology.engager.mutation_allowed is True
    assert topology.approval_required is True


def test_opportunity_candidate_defaults_to_scanned():
    item = OpportunityCandidate(
        platform="linkedin",
        source_post_id="post_1",
        author="Tan Le",
        source_url="https://www.linkedin.com/feed/update/test",
        source_text="AI should extend us, not replace us.",
    )

    assert item.status == QueueStatus.SCANNED
    assert item.recommended_voice == "0102"


def test_review_packet_holds_ranked_items():
    item = OpportunityCandidate(
        platform="linkedin",
        source_post_id="post_2",
        author="Mo Gawdat",
        source_url="https://www.linkedin.com/feed/update/test2",
        source_text="The future is humans and machines together.",
        alignment_keys=["foundups", "digital_twin"],
        score=9.2,
        status=QueueStatus.QUEUED,
    )

    packet = MorningReviewPacket(
        queue_id="mq_001",
        reviewer_channel="discord",
        items=[item],
    )

    assert packet.items[0].status == QueueStatus.QUEUED
    assert packet.items[0].alignment_keys == ["foundups", "digital_twin"]
