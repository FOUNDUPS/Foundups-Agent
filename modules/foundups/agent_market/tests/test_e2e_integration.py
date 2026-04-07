"""End-to-end integration tests for FAM + OpenClaw flow.

Tests the complete flow:
  OpenClaw -> FAM Adapter -> LaunchOrchestrator -> Task Pipeline
  -> Proof -> Verification -> CABR Gate -> Distribution

WSP Compliance:
  WSP 5   : Test coverage
  WSP 11  : Interface contracts
  WSP 50  : Pre-action verification
"""

import pytest

from modules.foundups.agent_market.src.in_memory import InMemoryAgentMarket
from modules.foundups.agent_market.src.models import (
    Foundup,
    Proof,
    Task,
    TaskStatus,
    TokenTerms,
    Verification,
)
from modules.foundups.agent_market.src.orchestrator import (
    LaunchOrchestrator,
    launch_foundup,
)
from modules.foundups.agent_market.src.exceptions import CABRGateError


class TestE2ELaunchToDistribution:
    """End-to-end tests for complete FAM flow."""

    def test_full_flow_launch_to_cabr_gated_distribution(self):
        """
        Complete E2E: launch -> task -> proof -> verify -> CABR gate -> distribution.

        This is the golden path test for the FoundUps Agent Market.
        """
        # Setup: Create market with required roles
        market = InMemoryAgentMarket(
            actor_roles={
                "verifier_1": "verifier",
                "treasury_1": "treasury",
                "distribution_1": "distribution",
            }
        )

        # Step 1: Launch FoundUp via orchestrator
        foundup = Foundup(
            foundup_id="f_e2e_1",
            name="E2E Test FoundUp",
            owner_id="founder_1",
            token_symbol="E2E",
            immutable_metadata={"launch_model": "tokenized"},
            mutable_metadata={},
        )

        token_terms = TokenTerms(
            token_name="E2E Token",
            token_symbol="E2E",
            max_supply=1_000_000,
            treasury_account="treasury_e2e",
            vesting_policy={"cliff": "6m", "duration": "24m"},
        )

        initial_task_params = {
            "task_id": "task_e2e_init",
            "title": "Initial E2E Task",
            "description": "Complete the E2E test setup",
            "acceptance_criteria": ["Tests pass", "Docs updated"],
            "reward_amount": 500,
        }

        launch_result = launch_foundup(
            registry=market,
            token_adapter=market,
            repo_adapter=market,
            task_pipeline=market,
            foundup=foundup,
            token_terms=token_terms,
            repo_name="e2e-test-repo",
            initial_task_params=initial_task_params,
            actor_id="launcher_1",
            observability=market,
        )

        # Verify launch succeeded
        assert launch_result.success is True
        assert launch_result.foundup.foundup_id == "f_e2e_1"
        assert launch_result.token_address is not None
        assert launch_result.repo_url is not None
        assert launch_result.initial_task is not None
        assert launch_result.initial_task.task_id == "task_e2e_init"

        # Step 2: Claim initial task
        market.claim_task("task_e2e_init", "agent_1")
        assert market.get_task("task_e2e_init").status == TaskStatus.CLAIMED

        # Step 3: Submit proof
        proof = Proof(
            proof_id="proof_e2e_1",
            task_id="task_e2e_init",
            submitter_id="agent_1",
            artifact_uri="ipfs://e2e-proof-artifact",
            artifact_hash="sha256:e2e123",
        )
        market.submit_proof(proof)
        assert market.get_task("task_e2e_init").status == TaskStatus.SUBMITTED

        # Step 4: Verify proof
        verification = Verification(
            verification_id="ver_e2e_1",
            task_id="task_e2e_init",
            verifier_id="verifier_1",
            approved=True,
            reason="All acceptance criteria met",
        )
        market.verify_proof("task_e2e_init", verification)
        assert market.get_task("task_e2e_init").status == TaskStatus.VERIFIED

        # Step 5: Record CABR score (gate requirement)
        market.record_cabr_output(
            "f_e2e_1",
            {"score": 0.85, "window": "7d", "timestamp": "2026-02-07T12:00:00Z"},
        )

        # Step 6: Publish with CABR gate (should pass with score >= threshold)
        distribution = market.publish_verified_milestone(
            "task_e2e_init",
            "distribution_1",
            channel="moltbook",
            cabr_threshold=0.7,
        )
        assert distribution.task_id == "task_e2e_init"
        assert distribution.channel == "moltbook"

        # Step 7: Trigger payout
        payout = market.trigger_payout("task_e2e_init", "treasury_1")
        assert payout.amount == 500
        assert market.get_task("task_e2e_init").status == TaskStatus.PAID

        # Verify full trace
        trace = market.get_trace("task_e2e_init")
        assert trace["foundup"]["foundup_id"] == "f_e2e_1"
        assert trace["proof"]["proof_id"] == "proof_e2e_1"
        assert trace["verification"]["verification_id"] == "ver_e2e_1"
        assert trace["payout"]["payout_id"] == payout.payout_id

        # Verify events recorded
        events = market.query_events(foundup_id="f_e2e_1")
        event_types = [e["event_type"] for e in events]
        assert "launch.foundup_created" in event_types
        assert "launch.token_deployed" in event_types
        assert "launch.repo_provisioned" in event_types
        assert "launch.initial_task_created" in event_types
        assert "launch.complete" in event_types

    def test_e2e_cabr_gate_blocks_low_score(self):
        """E2E: distribution blocked when CABR score below threshold."""
        market = InMemoryAgentMarket(
            actor_roles={
                "verifier_1": "verifier",
                "distribution_1": "distribution",
            }
        )

        # Create and complete task through verification
        foundup = Foundup(
            foundup_id="f_cabr_block",
            name="CABR Block Test",
            owner_id="owner_1",
            token_symbol="CBT",
            immutable_metadata={},
            mutable_metadata={},
        )
        market.create_foundup(foundup)

        task = Task(
            task_id="task_cabr_block",
            foundup_id="f_cabr_block",
            title="CABR Gate Test Task",
            description="Test CABR blocking",
            acceptance_criteria=["Test"],
            reward_amount=100,
            creator_id="owner_1",
        )
        market.create_task(task)
        market.claim_task("task_cabr_block", "agent_1")
        market.submit_proof(
            Proof(
                proof_id="proof_cabr_block",
                task_id="task_cabr_block",
                submitter_id="agent_1",
                artifact_uri="ipfs://proof",
                artifact_hash="sha256:abc",
            )
        )
        market.verify_proof(
            "task_cabr_block",
            Verification(
                verification_id="ver_cabr_block",
                task_id="task_cabr_block",
                verifier_id="verifier_1",
                approved=True,
                reason="OK",
            ),
        )

        # Record LOW CABR score
        market.record_cabr_output(
            "f_cabr_block",
            {"score": 0.4, "window": "7d"},
        )

        # Attempt distribution with threshold 0.7 - should fail
        with pytest.raises(CABRGateError) as exc_info:
            market.publish_verified_milestone(
                "task_cabr_block",
                "distribution_1",
                cabr_threshold=0.7,
            )

        assert "0.40" in str(exc_info.value)
        assert "0.70" in str(exc_info.value)

    def test_e2e_cabr_gate_blocks_missing_score(self):
        """E2E: distribution blocked when CABR score missing."""
        market = InMemoryAgentMarket(
            actor_roles={
                "verifier_1": "verifier",
                "distribution_1": "distribution",
            }
        )

        # Create and complete task through verification
        foundup = Foundup(
            foundup_id="f_no_cabr",
            name="No CABR Test",
            owner_id="owner_1",
            token_symbol="NCT",
            immutable_metadata={},
            mutable_metadata={},
        )
        market.create_foundup(foundup)

        task = Task(
            task_id="task_no_cabr",
            foundup_id="f_no_cabr",
            title="No CABR Score Task",
            description="Test missing CABR",
            acceptance_criteria=["Test"],
            reward_amount=100,
            creator_id="owner_1",
        )
        market.create_task(task)
        market.claim_task("task_no_cabr", "agent_1")
        market.submit_proof(
            Proof(
                proof_id="proof_no_cabr",
                task_id="task_no_cabr",
                submitter_id="agent_1",
                artifact_uri="ipfs://proof",
                artifact_hash="sha256:abc",
            )
        )
        market.verify_proof(
            "task_no_cabr",
            Verification(
                verification_id="ver_no_cabr",
                task_id="task_no_cabr",
                verifier_id="verifier_1",
                approved=True,
                reason="OK",
            ),
        )

        # NO CABR score recorded - distribution should fail
        with pytest.raises(CABRGateError) as exc_info:
            market.publish_verified_milestone(
                "task_no_cabr",
                "distribution_1",
                cabr_threshold=0.5,
            )

        assert "missing" in str(exc_info.value).lower()

    def test_e2e_minimal_launch_no_token_no_repo(self):
        """E2E: minimal launch without token or repo."""
        market = InMemoryAgentMarket()

        foundup = Foundup(
            foundup_id="f_minimal_e2e",
            name="Minimal E2E",
            owner_id="owner_1",
            token_symbol="MIN",
            immutable_metadata={},
            mutable_metadata={},
        )

        result = launch_foundup(
            registry=market,
            token_adapter=market,
            foundup=foundup,
        )

        assert result.success is True
        assert result.token_address is None
        assert result.repo_url is None
        assert result.initial_task is None

        # Verify foundup exists
        stored = market.get_foundup("f_minimal_e2e")
        assert stored.name == "Minimal E2E"


class TestE2EOpenClawIntegration:
    """Tests for OpenClaw -> FAM adapter integration."""

    def test_fam_adapter_launch_request_parsing(self):
        """FAM adapter correctly parses launch intent."""
        from modules.communication.moltbot_bridge.src.fam_adapter import (
            FAMAdapter,
        )

        adapter = FAMAdapter(use_in_memory=True)

        # Test launch command parsing
        request = adapter.parse_launch_intent(
            "launch foundup test project with token TEST",
            "user_1",
        )

        assert request is not None
        assert request.foundup_name == "Test Project"
        assert request.token_symbol == "TEST"
        assert request.owner_id == "user_1"

    def test_fam_adapter_launch_execution(self):
        """FAM adapter executes launch via orchestrator."""
        from modules.communication.moltbot_bridge.src.fam_adapter import (
            FAMAdapter,
            FAMLaunchRequest,
        )

        adapter = FAMAdapter(use_in_memory=True)

        request = FAMLaunchRequest(
            foundup_name="Adapter Test",
            owner_id="adapter_user",
            token_symbol="ADT",
            token_name="Adapter Token",
            max_supply=500_000,
        )

        response = adapter.launch_foundup(request, actor_id="adapter_user")

        assert response.success is True
        assert response.foundup_id is not None
        assert "adt" in response.foundup_id.lower()
        assert response.token_address is not None
        assert len(response.events) >= 2  # created + complete

    def test_fam_adapter_handle_intent_launch(self):
        """handle_fam_intent correctly processes launch command."""
        from modules.communication.moltbot_bridge.src.fam_adapter import (
            handle_fam_intent,
        )

        response = handle_fam_intent(
            "launch foundup new venture token NVT",
            "commander_1",
        )

        assert "launched successfully" in response.lower() or "ID:" in response
        assert "nvt" in response.lower() or "NVT" in response

    def test_fam_adapter_handle_intent_help(self):
        """handle_fam_intent returns help for unknown commands."""
        from modules.communication.moltbot_bridge.src.fam_adapter import (
            handle_fam_intent,
        )

        response = handle_fam_intent("what is fam?", "user_1")

        assert "launch foundup" in response.lower()

    def test_fam_adapter_auto_symbol_when_missing_token(self):
        """Launch parser should auto-generate token symbol when none is supplied."""
        from modules.communication.moltbot_bridge.src.fam_adapter import FAMAdapter

        adapter = FAMAdapter(use_in_memory=True)
        request = adapter.parse_launch_intent("launch foundup solar cleanup", "user_2")

        assert request is not None
        assert request.token_symbol != "FUP"
        assert len(request.token_symbol) >= 3

    def test_fam_adapter_symbol_collision_resolution(self):
        """Auto token resolution should avoid duplicate symbols across launches."""
        from modules.communication.moltbot_bridge.src.fam_adapter import FAMAdapter, FAMLaunchRequest

        adapter = FAMAdapter(use_in_memory=True)
        req1 = FAMLaunchRequest(
            foundup_name="Solar Cleanup",
            owner_id="owner_a",
            token_symbol="AUTO",
        )
        req2 = FAMLaunchRequest(
            foundup_name="Solar Cleanup",
            owner_id="owner_b",
            token_symbol="AUTO",
        )

        resp1 = adapter.launch_foundup(req1, actor_id="owner_a")
        resp2 = adapter.launch_foundup(req2, actor_id="owner_b")

        assert resp1.success is True
        assert resp2.success is True
        assert resp1.foundup_id is not None
        assert resp2.foundup_id is not None
        assert resp1.foundup_id != resp2.foundup_id

        market = adapter._get_in_memory_market()
        sym1 = market.get_foundup(resp1.foundup_id).token_symbol
        sym2 = market.get_foundup(resp2.foundup_id).token_symbol
        assert sym1 != sym2


class TestE2EMoltbookDistribution:
    """Tests for Moltbook distribution adapter."""

    def test_moltbook_adapter_publish_milestone(self):
        """Moltbook adapter publishes milestone."""
        from modules.communication.moltbot_bridge.src.moltbook_distribution_adapter import (
            MoltbookDistributionAdapterStub,
        )

        adapter = MoltbookDistributionAdapterStub()

        result = adapter.publish_milestone(
            foundup_id="f_moltbook_test",
            task_id="task_moltbook_1",
            milestone_payload={
                "description": "Test milestone achieved",
                "proof_uri": "ipfs://test-proof",
            },
            actor_id="distributor_1",
        )

        assert result["post_id"].startswith("moltbook_post_")
        assert result["channel"] == "moltbook"
        assert result["status"] == "published"

    def test_moltbook_adapter_list_milestones(self):
        """Moltbook adapter lists published milestones."""
        from modules.communication.moltbot_bridge.src.moltbook_distribution_adapter import (
            MoltbookDistributionAdapterStub,
        )

        adapter = MoltbookDistributionAdapterStub()

        # Publish multiple milestones
        for i in range(3):
            adapter.publish_milestone(
                foundup_id="f_list_test",
                task_id=f"task_list_{i}",
                milestone_payload={"index": i},
                actor_id="distributor_1",
            )

        milestones = adapter.list_published_milestones("f_list_test")
        assert len(milestones) == 3

        # Verify ordering (most recent last)
        assert milestones[-1]["task_id"] == "task_list_2"

    def test_moltbook_adapter_get_status(self):
        """Moltbook adapter returns publish status."""
        from modules.communication.moltbot_bridge.src.moltbook_distribution_adapter import (
            MoltbookDistributionAdapterStub,
        )

        adapter = MoltbookDistributionAdapterStub()

        result = adapter.publish_milestone(
            foundup_id="f_status_test",
            task_id="task_status_1",
            milestone_payload={},
            actor_id="distributor_1",
        )

        status = adapter.get_publish_status(result["post_id"])
        assert status is not None
        assert status["foundup_id"] == "f_status_test"
        assert status["task_id"] == "task_status_1"
        assert status["status"] == "published"

        # Non-existent post
        assert adapter.get_publish_status("nonexistent") is None
