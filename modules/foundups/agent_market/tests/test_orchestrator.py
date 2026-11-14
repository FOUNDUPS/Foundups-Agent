"""Tests for launch orchestrator."""

import pytest

from modules.foundups.agent_market.src.exceptions import ValidationError
from modules.foundups.agent_market.src.in_memory import InMemoryAgentMarket
from modules.foundups.agent_market.src.models import Foundup, TokenTerms
from modules.foundups.agent_market.src.orchestrator import LaunchOrchestrator, launch_foundup
from modules.foundups.agent_market.src.token_factory import (
    ChainAgnosticTokenFactory,
    ChainBackend,
    ChainType,
    TokenDeploymentResult,
)


def test_launch_foundup_happy_path_full():
    """launch_foundup executes full happy path with all options."""
    market = InMemoryAgentMarket()

    foundup = Foundup(
        foundup_id="f_launch_1",
        name="Launch Test Foundup",
        owner_id="owner_1",
        token_symbol="LAUNCH",
        immutable_metadata={"launch_model": "tokenized"},
        mutable_metadata={},
    )

    token_terms = TokenTerms(
        token_name="Launch Token",
        token_symbol="LAUNCH",
        max_supply=1_000_000,
        treasury_account="treasury_1",
        vesting_policy={"cliff": "6m", "duration": "24m"},
    )

    initial_task_params = {
        "task_id": "task_init_1",
        "title": "Initial Setup Task",
        "description": "Complete initial foundup setup",
        "acceptance_criteria": ["Setup complete", "Tests passing"],
        "reward_amount": 500,
    }

    result = launch_foundup(
        registry=market,
        token_adapter=market,
        repo_adapter=market,
        task_pipeline=market,
        foundup=foundup,
        token_terms=token_terms,
        repo_name="foundups-launch-test",
        initial_task_params=initial_task_params,
        actor_id="launcher_1",
        observability=market,
    )

    # Verify success
    assert result.success is True
    assert result.error is None

    # Verify foundup created
    assert result.foundup.foundup_id == "f_launch_1"
    stored_foundup = market.get_foundup("f_launch_1")
    assert stored_foundup.name == "Launch Test Foundup"

    # Verify token deployed
    assert result.token_address is not None
    assert "launch" in result.token_address.lower()

    # Verify repo provisioned
    assert result.repo_url is not None
    assert "foundups-launch-test" in result.repo_url

    # Verify initial task created in task pipeline
    assert result.initial_task is not None
    assert result.initial_task.title == "Initial Setup Task"
    assert result.initial_task.reward_amount == 500
    assert market.get_task("task_init_1").title == "Initial Setup Task"

    # Verify events recorded
    assert len(result.events) >= 4  # created, token, repo, task, complete
    event_types = [e.event_type for e in result.events]
    assert "launch.foundup_created" in event_types
    assert "launch.token_deployed" in event_types
    assert "launch.repo_provisioned" in event_types
    assert "launch.initial_task_created" in event_types
    assert "launch.complete" in event_types


def test_launch_foundup_minimal():
    """launch_foundup works with minimal required inputs."""
    market = InMemoryAgentMarket()

    foundup = Foundup(
        foundup_id="f_minimal",
        name="Minimal Foundup",
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
    assert result.token_address is None  # No token terms provided
    assert result.repo_url is None  # No repo name provided
    assert result.initial_task is None  # No task params provided

    # Should still have created and complete events
    event_types = [e.event_type for e in result.events]
    assert "launch.foundup_created" in event_types
    assert "launch.complete" in event_types


def test_launch_foundup_existing_foundup():
    """launch_foundup handles existing foundup gracefully."""
    market = InMemoryAgentMarket()

    # Pre-create foundup
    existing = Foundup(
        foundup_id="f_existing",
        name="Existing Foundup",
        owner_id="owner_1",
        token_symbol="EXIST",
        immutable_metadata={},
        mutable_metadata={},
    )
    market.create_foundup(existing)

    # Try to launch same foundup
    result = launch_foundup(
        registry=market,
        token_adapter=market,
        foundup=existing,
    )

    assert result.success is True
    event_types = [e.event_type for e in result.events]
    assert "launch.foundup_exists" in event_types
    assert "launch.foundup_created" not in event_types


def test_launch_orchestrator_emits_traceable_events():
    """LaunchOrchestrator emits auditable events with proper structure."""
    market = InMemoryAgentMarket()
    orchestrator = LaunchOrchestrator(
        registry=market,
        token_adapter=market,
        repo_adapter=market,
        observability=market,
    )

    foundup = Foundup(
        foundup_id="f_trace",
        name="Traceable Foundup",
        owner_id="owner_1",
        token_symbol="TRACE",
        immutable_metadata={},
        mutable_metadata={},
    )

    token_terms = TokenTerms(
        token_name="Trace Token",
        token_symbol="TRACE",
        max_supply=500_000,
        treasury_account="treasury_trace",
    )

    result = orchestrator.launch_foundup(
        foundup=foundup,
        token_terms=token_terms,
        repo_name="trace-repo",
        actor_id="tracer_1",
    )

    # Verify all events have required audit fields
    for event in result.events:
        assert event.event_id.startswith("launch_ev_")
        assert event.foundup_id == "f_trace"
        assert event.actor_id == "tracer_1"
        assert event.timestamp is not None
        assert isinstance(event.payload, dict)

    # Verify observability received events
    obs_events = market.query_events(foundup_id="f_trace")
    assert len(obs_events) > 0


def test_repo_provision_records_deterministic_metadata():
    """Repo provisioning adapter records deterministic repo metadata."""
    market = InMemoryAgentMarket()

    # Create foundup first
    foundup = Foundup(
        foundup_id="f_repo",
        name="Repo Test Foundup",
        owner_id="owner_1",
        token_symbol="REPO",
        immutable_metadata={},
        mutable_metadata={},
    )
    market.create_foundup(foundup)

    # Provision repo
    repo_url = market.provision_repo(
        foundup_id="f_repo",
        repo_name="test-repo",
        provider="github",
        default_branch="main",
    )

    assert repo_url == "https://github.com/foundups/test-repo"

    # Verify metadata stored
    metadata = market.get_repo_metadata("f_repo")
    assert metadata is not None
    assert metadata["foundup_id"] == "f_repo"
    assert metadata["repo_name"] == "test-repo"
    assert metadata["repo_url"] == "https://github.com/foundups/test-repo"
    assert metadata["provider"] == "github"
    assert metadata["default_branch"] == "main"


def test_repo_provision_different_providers():
    """Repo provisioning works with different providers."""
    market = InMemoryAgentMarket()

    for provider, foundup_id in [("github", "f_gh"), ("gitlab", "f_gl"), ("bitbucket", "f_bb")]:
        market.create_foundup(
            Foundup(
                foundup_id=foundup_id,
                name=f"{provider} Foundup",
                owner_id="owner_1",
                token_symbol=provider.upper()[:4],
                immutable_metadata={},
                mutable_metadata={},
            )
        )

        repo_url = market.provision_repo(
            foundup_id=foundup_id,
            repo_name=f"{provider}-repo",
            provider=provider,
        )

        assert provider in repo_url
        metadata = market.get_repo_metadata(foundup_id)
        assert metadata["provider"] == provider


def test_repo_provision_emits_event():
    """Repo provisioning emits auditable event."""
    market = InMemoryAgentMarket()

    market.create_foundup(
        Foundup(
            foundup_id="f_repo_ev",
            name="Event Test Foundup",
            owner_id="owner_1",
            token_symbol="EVNT",
            immutable_metadata={},
            mutable_metadata={},
        )
    )

    market.provision_repo("f_repo_ev", "event-repo", "github", "develop")

    events = market.query_events(foundup_id="f_repo_ev")
    repo_events = [e for e in events if e["event_type"] == "repo.provisioned"]
    assert len(repo_events) == 1
    assert repo_events[0]["payload"]["repo_name"] == "event-repo"
    assert repo_events[0]["payload"]["default_branch"] == "develop"


class RecordingChainBackend(ChainBackend):
    """Offline adapter double; records effects without contacting a chain."""

    def __init__(self, chain_type, connected=True, result_chain=None):
        self.declared_chain = chain_type
        self.connected = connected
        self.result_chain = result_chain
        self.calls = []

    @property
    def chain_type(self):
        return self.declared_chain

    def is_connected(self):
        if isinstance(self.connected, Exception):
            raise self.connected
        return self.connected

    def deploy_token(self, **kwargs):
        self.calls.append(("deploy", kwargs))
        return TokenDeploymentResult(
            success=True,
            chain_type=self.result_chain or self.declared_chain,
            token_address="offline_test_token",
        )

    def configure_vesting(self, token_address, config):
        self.calls.append(("vesting", token_address))
        return True

    def get_treasury_balance(self, token_address):
        return 0


@pytest.fixture
def token_factory_request():
    return (
        Foundup("f_backend", "Backend Test", "owner_1", "BACKEND"),
        TokenTerms("Backend Token", "BACKEND", 100, "test_treasury"),
    )


def run_token_operation(factory, operation, foundup, terms):
    if operation == "deploy":
        return factory.deploy_token(foundup, terms)
    return factory.configure_vesting("offline_test_token", terms)


@pytest.mark.parametrize("operation", ["deploy", "vesting"])
@pytest.mark.parametrize("hint", ["algorand", "unknown", "", "   ", 42])
def test_token_factory_rejects_unsupported_hint_without_fallback(
    operation, hint, token_factory_request
):
    factory = ChainAgnosticTokenFactory()
    mock = RecordingChainBackend(ChainType.MOCK)
    factory.register_backend(mock)
    foundup, terms = token_factory_request
    terms.chain_hint = hint

    with pytest.raises(ValidationError, match="chain"):
        run_token_operation(factory, operation, foundup, terms)

    assert mock.calls == []
    assert factory.get_deployment_status(foundup.foundup_id) is None


@pytest.mark.parametrize("operation", ["deploy", "vesting"])
@pytest.mark.parametrize("chain", [ChainType.EVM, ChainType.HEDERA, ChainType.SOLANA])
def test_token_factory_rejects_unregistered_backend(
    operation, chain, token_factory_request
):
    factory = ChainAgnosticTokenFactory()
    mock = RecordingChainBackend(ChainType.MOCK)
    factory.register_backend(mock)
    foundup, terms = token_factory_request
    terms.chain_hint = chain.value

    with pytest.raises(ValidationError, match="registered"):
        run_token_operation(factory, operation, foundup, terms)

    assert mock.calls == []


@pytest.mark.parametrize("operation", ["deploy", "vesting"])
@pytest.mark.parametrize(
    "connected", [False, ValueError("offline health-check failure")]
)
def test_token_factory_rejects_unavailable_backend(
    operation, connected, token_factory_request
):
    factory = ChainAgnosticTokenFactory()
    mock = RecordingChainBackend(ChainType.MOCK)
    backend = RecordingChainBackend(ChainType.EVM, connected=connected)
    factory.register_backend(mock)
    factory.register_backend(backend)
    foundup, terms = token_factory_request
    terms.chain_hint = "evm"

    with pytest.raises(ValidationError, match="backend"):
        run_token_operation(factory, operation, foundup, terms)

    assert backend.calls == mock.calls == []


@pytest.mark.parametrize("operation", ["deploy", "vesting"])
@pytest.mark.parametrize("registered", [False, True])
def test_token_factory_checks_configured_default(
    operation, registered, token_factory_request
):
    factory = ChainAgnosticTokenFactory(default_chain=ChainType.EVM)
    mock = RecordingChainBackend(ChainType.MOCK)
    backend = RecordingChainBackend(ChainType.EVM, connected=False)
    factory.register_backend(mock)
    if registered:
        factory.register_backend(backend)
    foundup, terms = token_factory_request

    with pytest.raises(ValidationError, match="backend"):
        run_token_operation(factory, operation, foundup, terms)

    assert backend.calls == mock.calls == []


@pytest.mark.parametrize("operation", ["deploy", "vesting"])
def test_token_factory_rejects_disconnected_mock(operation, token_factory_request):
    factory = ChainAgnosticTokenFactory()
    mock = RecordingChainBackend(ChainType.MOCK, connected=False)
    factory.register_backend(mock)
    foundup, terms = token_factory_request
    terms.chain_hint = "mock"

    with pytest.raises(ValidationError, match="disconnected"):
        run_token_operation(factory, operation, foundup, terms)

    assert mock.calls == []


@pytest.mark.parametrize("hint", [None, "mock", " MOCK "])
def test_token_factory_mock_remains_explicitly_identified(hint, token_factory_request):
    default = ChainType.MOCK if hint is None else ChainType.EVM
    factory = ChainAgnosticTokenFactory(default_chain=default)
    foundup, terms = token_factory_request
    terms.chain_hint = hint

    address = factory.deploy_token(foundup, terms)
    factory.configure_vesting(address, terms)
    result = factory.get_deployment_status(foundup.foundup_id)

    assert address.startswith("mock_token_")
    assert result.chain_type == ChainType.MOCK
    assert result.metadata["mock"] is True
    assert result.transaction_id.startswith("mock_tx_")
    assert result.explorer_url is None


@pytest.mark.parametrize("hint", [None, " EVM "])
def test_token_factory_dispatches_only_to_selected_backend(hint, token_factory_request):
    default = ChainType.EVM if hint is None else ChainType.MOCK
    factory = ChainAgnosticTokenFactory(default_chain=default)
    mock = RecordingChainBackend(ChainType.MOCK)
    backend = RecordingChainBackend(ChainType.EVM)
    factory.register_backend(mock)
    factory.register_backend(backend)
    foundup, terms = token_factory_request
    terms.chain_hint = hint

    address = factory.deploy_token(foundup, terms)
    factory.configure_vesting(address, terms)

    assert [call[0] for call in backend.calls] == ["deploy", "vesting"]
    assert mock.calls == []
    assert factory.get_deployment_status(foundup.foundup_id).chain_type == ChainType.EVM


@pytest.mark.parametrize("operation", ["deploy", "vesting"])
@pytest.mark.parametrize("changed_chain", [ChainType.MOCK, "evm"])
def test_token_factory_rejects_backend_identity_drift(
    operation, changed_chain, token_factory_request
):
    factory = ChainAgnosticTokenFactory()
    backend = RecordingChainBackend(ChainType.EVM)
    factory.register_backend(backend)
    backend.declared_chain = changed_chain
    foundup, terms = token_factory_request
    terms.chain_hint = "evm"

    with pytest.raises(ValidationError, match="mismatch"):
        run_token_operation(factory, operation, foundup, terms)

    assert backend.calls == []


@pytest.mark.parametrize("result_chain", [ChainType.MOCK, "evm"])
def test_token_factory_rejects_result_chain_mismatch(result_chain, token_factory_request):
    factory = ChainAgnosticTokenFactory()
    backend = RecordingChainBackend(ChainType.EVM, result_chain=result_chain)
    factory.register_backend(backend)
    foundup, terms = token_factory_request
    terms.chain_hint = "evm"

    with pytest.raises(ValidationError, match="mismatch"):
        factory.deploy_token(foundup, terms)

    assert len(backend.calls) == 1
    assert factory.get_deployment_status(foundup.foundup_id) is None


def test_token_factory_rejects_non_enum_backend_registration():
    factory = ChainAgnosticTokenFactory()

    with pytest.raises(ValidationError, match="ChainType"):
        factory.register_backend(RecordingChainBackend("evm"))

    assert factory.list_supported_chains() == ["mock:connected"]


@pytest.mark.parametrize("operation", ["deploy", "vesting"])
def test_token_factory_rejects_identity_drift_during_connectivity(
    operation, token_factory_request, monkeypatch
):
    factory = ChainAgnosticTokenFactory()
    backend = RecordingChainBackend(ChainType.EVM)
    factory.register_backend(backend)

    def change_chain():
        backend.declared_chain = ChainType.MOCK
        return True

    monkeypatch.setattr(backend, "is_connected", change_chain)
    foundup, terms = token_factory_request
    terms.chain_hint = "evm"

    with pytest.raises(ValidationError, match="mismatch"):
        run_token_operation(factory, operation, foundup, terms)

    assert backend.calls == []
    assert factory.get_deployment_status(foundup.foundup_id) is None


def test_launch_rejects_unavailable_chain_before_downstream_effects(token_factory_request):
    market = InMemoryAgentMarket()
    factory = ChainAgnosticTokenFactory()
    foundup, terms = token_factory_request
    terms.chain_hint = "evm"

    result = launch_foundup(
        registry=market,
        token_adapter=factory,
        repo_adapter=market,
        task_pipeline=market,
        foundup=foundup,
        token_terms=terms,
        repo_name="must-not-provision",
        initial_task_params={"task_id": "must-not-create"},
        observability=market,
    )

    assert result.success is False
    assert result.token_address is result.repo_url is result.initial_task is None
    assert [event.event_type for event in result.events] == [
        "launch.foundup_created", "launch.failed"
    ]
    assert factory.get_deployment_status(foundup.foundup_id) is None
    # Registry creation precedes token deployment; rollback is a separate boundary.
    assert market.get_foundup(foundup.foundup_id) == foundup


def test_launch_with_actual_mock_factory_stays_simulated(token_factory_request):
    market = InMemoryAgentMarket()
    factory = ChainAgnosticTokenFactory()
    foundup, terms = token_factory_request

    result = launch_foundup(registry=market, token_adapter=factory,
                           foundup=foundup, token_terms=terms)

    assert result.success is True
    assert result.token_address.startswith("mock_token_")
    assert factory.get_deployment_status(foundup.foundup_id).metadata == {"mock": True}


@pytest.mark.parametrize("bad_reward", [True, False, 1.5, "1", float("nan"), float("inf"), -1])
def test_initial_reward_refuses_before_any_launch_adapter_effect(token_factory_request, bad_reward):
    from unittest.mock import Mock

    foundup, terms = token_factory_request
    services = Mock()
    result = launch_foundup(
        registry=services, token_adapter=services, repo_adapter=services,
        task_pipeline=services, foundup=foundup, token_terms=terms,
        repo_name="must-not-provision", initial_task_params={"reward_amount": bad_reward},
    )
    assert result.success is False
    assert result.token_address is result.repo_url is result.initial_task is None
    assert services.mock_calls == []
    assert [event.event_type for event in result.events] == ["launch.failed"]
    assert result.error == "reward_amount must be a positive integer"
