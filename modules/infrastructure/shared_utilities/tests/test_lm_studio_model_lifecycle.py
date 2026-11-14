"""Contract tests for exact LM Studio model residency and managed leases."""

from __future__ import annotations

import json
import urllib.error
from unittest.mock import patch

import pytest


LIFECYCLE = (
    "modules.infrastructure.shared_utilities.lm_studio_model_lifecycle"
)
TRANSPORT = "modules.infrastructure.shared_utilities.lm_studio_native_transport"


@pytest.fixture(autouse=True)
def _isolated_lifecycle_intent_runtime(tmp_path, monkeypatch):
    from modules.infrastructure.shared_utilities.lm_studio_lifecycle_intent import (
        LMStudioLifecycleIntentJournal,
    )

    runtime_root = tmp_path / "runtime"
    monkeypatch.setattr(
        f"{LIFECYCLE}.LMStudioLifecycleIntentJournal",
        lambda node_scope_digest: LMStudioLifecycleIntentJournal(
            node_scope_digest, runtime_root=runtime_root
        ),
    )
    return runtime_root


class _Response:
    def __init__(self, payload, status=200):
        self.payload = json.dumps(payload).encode("utf-8")
        self.status = status
        self.headers = {}
        self.url = "http://localhost:1234/api/v1/models"

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, limit=-1):
        return self.payload if limit < 0 else self.payload[:limit]

    def geturl(self):
        return self.url


def _inventory(instances=(), *, other_instances=(), max_context_length=131072):
    return {
        "models": [
            {
                "type": "llm",
                "key": "nvidia/nemotron-3.5-lightning",
                "max_context_length": max_context_length,
                "size_bytes": 42_000_000_000,
                "loaded_instances": [
                    {
                        "id": instance_id,
                        "config": {"context_length": 32768},
                    }
                    for instance_id in instances
                ],
            },
            {
                "type": "llm",
                "key": "other/large-model",
                "max_context_length": 32768,
                "size_bytes": 40_000_000_000,
                "loaded_instances": [
                    {"id": instance_id, "config": {"context_length": 32768}}
                    for instance_id in other_instances
                ],
            },
        ]
    }


def test_native_inventory_distinguishes_installed_from_resident():
    from modules.infrastructure.shared_utilities.lm_studio_model_lifecycle import (
        LMStudioResidencyState,
        inspect_lm_studio_model,
    )

    with patch(f"{TRANSPORT}._open_no_redirect", return_value=_Response(_inventory())):
        state = inspect_lm_studio_model("nvidia/nemotron-3.5-lightning")

    assert state.state is LMStudioResidencyState.INSTALLED_NOT_RESIDENT
    assert state.loaded_instances == ()


def test_native_inventory_reports_exact_resident_instance():
    from modules.infrastructure.shared_utilities.lm_studio_model_lifecycle import (
        LMStudioResidencyState,
        inspect_lm_studio_model,
    )

    with patch(
        f"{TRANSPORT}._open_no_redirect",
        return_value=_Response(_inventory(("nemotron-a",))),
    ):
        state = inspect_lm_studio_model("nvidia/nemotron-3.5-lightning")

    assert state.state is LMStudioResidencyState.RESIDENT
    assert state.loaded_instances[0].instance_id == "nemotron-a"


def test_managed_transaction_loads_calls_unloads_and_issues_receipt():
    from modules.infrastructure.shared_utilities.lm_studio_model_lifecycle import (
        execute_lm_studio_model_transaction,
        rehydrate_lm_studio_model_lifecycle_receipt,
    )

    calls = []
    responses = iter(
        [
            _Response(_inventory()),
            _Response({"type": "llm", "instance_id": "nemotron-owned", "status": "loaded", "load_config": {"context_length": 32768}}),
            _Response(_inventory(("nemotron-owned",))),
            _Response({"instance_id": "nemotron-owned"}),
            _Response(_inventory()),
        ]
    )

    def urlopen(request, **_kwargs):
        calls.append(request)
        response = next(responses)
        response.url = request.full_url
        return response

    with patch(f"{TRANSPORT}._open_no_redirect", side_effect=urlopen):
        result = execute_lm_studio_model_transaction(
            model_key="nvidia/nemotron-3.5-lightning",
            operation=lambda lease: {"instance": lease.instance_id},
            load_config={"context_length": 32768},
        )

    assert result.value == {"instance": "nemotron-owned"}
    assert result.lifecycle_receipt.residency_origin == "explicit_load"
    assert result.lifecycle_receipt.load_confirmed is True
    assert result.lifecycle_receipt.unload_confirmed is True
    assert result.lifecycle_receipt.no_server_launch_performed is True
    assert rehydrate_lm_studio_model_lifecycle_receipt(
        result.lifecycle_receipt.to_dict()
    ) == result.lifecycle_receipt
    assert [request.full_url for request in calls] == [
        "http://localhost:1234/api/v1/models",
        "http://localhost:1234/api/v1/models/load",
        "http://localhost:1234/api/v1/models",
        "http://localhost:1234/api/v1/models/unload",
        "http://localhost:1234/api/v1/models",
    ]


def test_borrowed_transaction_never_loads_or_unloads():
    from modules.infrastructure.shared_utilities.lm_studio_model_lifecycle import (
        execute_lm_studio_model_transaction,
    )

    calls = []

    def urlopen(request, **_kwargs):
        calls.append(request)
        response = _Response(_inventory(("nemotron-borrowed",)))
        response.url = request.full_url
        return response

    with patch(f"{TRANSPORT}._open_no_redirect", side_effect=urlopen):
        result = execute_lm_studio_model_transaction(
            model_key="nvidia/nemotron-3.5-lightning",
            operation=lambda lease: lease.instance_id,
        )

    assert result.value == "nemotron-borrowed"
    assert result.lifecycle_receipt.residency_origin == "preexisting"
    assert result.lifecycle_receipt.load_confirmed is False
    assert result.lifecycle_receipt.unload_confirmed is False
    assert len(calls) == 1


def test_borrow_only_rejects_installed_but_not_resident():
    from modules.infrastructure.shared_utilities.lm_studio_model_lifecycle import (
        LMStudioLeaseMode,
        execute_lm_studio_model_transaction,
    )

    with patch(f"{TRANSPORT}._open_no_redirect", return_value=_Response(_inventory())):
        with pytest.raises(ValueError, match="model_not_resident"):
            execute_lm_studio_model_transaction(
                model_key="nvidia/nemotron-3.5-lightning",
                mode=LMStudioLeaseMode.BORROW_ONLY,
                operation=lambda _lease: None,
            )


def test_borrowed_instance_with_conflicting_config_fails_before_inference():
    from modules.infrastructure.shared_utilities.lm_studio_model_lifecycle import (
        execute_lm_studio_model_transaction,
    )

    called = False

    def operation(_lease):
        nonlocal called
        called = True

    with patch(
        f"{TRANSPORT}._open_no_redirect",
        return_value=_Response(_inventory(("borrowed",))),
    ):
        with pytest.raises(RuntimeError, match="load_config_mismatch"):
            execute_lm_studio_model_transaction(
                model_key="nvidia/nemotron-3.5-lightning",
                load_config={"context_length": 65536},
                operation=operation,
            )

    assert called is False


def test_managed_load_rejects_other_resident_model_before_load():
    from modules.infrastructure.shared_utilities.lm_studio_model_lifecycle import (
        execute_lm_studio_model_transaction,
    )

    calls = []

    def urlopen(request, **_kwargs):
        calls.append(request)
        response = _Response(_inventory(other_instances=("other-resident",)))
        response.url = request.full_url
        return response

    with patch(f"{TRANSPORT}._open_no_redirect", side_effect=urlopen):
        with pytest.raises(RuntimeError, match="managed_capacity_occupied"):
            execute_lm_studio_model_transaction(
                model_key="nvidia/nemotron-3.5-lightning",
                operation=lambda _lease: None,
            )

    assert not any(request.full_url.endswith("/load") for request in calls)


def test_managed_load_rejects_context_above_native_model_maximum():
    from modules.infrastructure.shared_utilities.lm_studio_model_lifecycle import (
        execute_lm_studio_model_transaction,
    )

    with patch(
        f"{TRANSPORT}._open_no_redirect",
        return_value=_Response(_inventory(max_context_length=8192)),
    ):
        with pytest.raises(ValueError, match="exceeds_model_maximum"):
            execute_lm_studio_model_transaction(
                model_key="nvidia/nemotron-3.5-lightning",
                load_config={"context_length": 32768},
                operation=lambda _lease: None,
            )


def test_load_timeout_reobserves_once_and_never_blindly_retries():
    from modules.infrastructure.shared_utilities.lm_studio_model_lifecycle import (
        execute_lm_studio_model_transaction,
    )

    calls = []
    responses = iter(
        [
            _Response(_inventory()),
            TimeoutError("load timed out"),
            _Response(_inventory(("indeterminate",))),
        ]
    )

    def urlopen(request, **_kwargs):
        calls.append(request)
        response = next(responses)
        if isinstance(response, BaseException):
            raise response
        response.url = request.full_url
        return response

    with patch(f"{TRANSPORT}._open_no_redirect", side_effect=urlopen):
        with pytest.raises(RuntimeError, match="load_outcome_indeterminate"):
            execute_lm_studio_model_transaction(
                model_key="nvidia/nemotron-3.5-lightning",
                operation=lambda _lease: None,
            )

    assert sum(request.full_url.endswith("/load") for request in calls) == 1
    assert sum(request.full_url.endswith("/models") for request in calls) == 2


def test_load_stage_cancellation_is_quarantined_without_retry():
    from modules.infrastructure.shared_utilities.lm_studio_model_lifecycle import (
        execute_lm_studio_model_transaction,
    )

    calls = []
    responses = iter(
        [
            _Response(_inventory()),
            KeyboardInterrupt("cancelled while loading"),
            _Response(_inventory(("outcome-unknown",))),
        ]
    )

    def urlopen(request, **_kwargs):
        calls.append(request)
        response = next(responses)
        if isinstance(response, BaseException):
            raise response
        response.url = request.full_url
        return response

    with patch(f"{TRANSPORT}._open_no_redirect", side_effect=urlopen):
        with pytest.raises(RuntimeError, match="load_outcome_indeterminate"):
            execute_lm_studio_model_transaction(
                model_key="nvidia/nemotron-3.5-lightning",
                operation=lambda _lease: None,
            )

    assert sum(request.full_url.endswith("/load") for request in calls) == 1
    assert not any(request.full_url.endswith("/unload") for request in calls)


def test_operation_failure_still_unloads_transaction_owned_instance():
    from modules.infrastructure.shared_utilities.lm_studio_model_lifecycle import (
        execute_lm_studio_model_transaction,
    )

    responses = iter(
        [
            _Response(_inventory()),
            _Response({"type": "llm", "instance_id": "owned", "status": "loaded", "load_config": {"context_length": 32768}}),
            _Response(_inventory(("owned",))),
            _Response({"instance_id": "owned"}),
            _Response(_inventory()),
        ]
    )
    calls = []

    def urlopen(request, **_kwargs):
        calls.append(request)
        response = next(responses)
        response.url = request.full_url
        return response

    def fail(_lease):
        raise KeyboardInterrupt("cancelled")

    with patch(f"{TRANSPORT}._open_no_redirect", side_effect=urlopen):
        with pytest.raises(KeyboardInterrupt, match="cancelled"):
            execute_lm_studio_model_transaction(
                model_key="nvidia/nemotron-3.5-lightning",
                operation=fail,
                load_config={"context_length": 32768},
            )

    assert sum(request.full_url.endswith("/unload") for request in calls) == 1


def test_post_load_identity_mismatch_cleans_up_returned_instance():
    from modules.infrastructure.shared_utilities.lm_studio_model_lifecycle import (
        execute_lm_studio_model_transaction,
    )

    responses = iter(
        [
            _Response(_inventory()),
            _Response(
                {
                    "type": "llm",
                    "instance_id": "owned",
                    "status": "loaded",
                    "load_config": {"context_length": 32768},
                }
            ),
            _Response(_inventory(("different",))),
            _Response({"instance_id": "owned"}),
            _Response(_inventory(("different",))),
        ]
    )
    calls = []

    def urlopen(request, **_kwargs):
        calls.append(request)
        response = next(responses)
        response.url = request.full_url
        return response

    with patch(f"{TRANSPORT}._open_no_redirect", side_effect=urlopen):
        with pytest.raises(RuntimeError, match="loaded_instance_mismatch"):
            execute_lm_studio_model_transaction(
                model_key="nvidia/nemotron-3.5-lightning",
                operation=lambda _lease: None,
            )

    assert sum(request.full_url.endswith("/unload") for request in calls) == 1


def test_foreign_concurrent_post_load_residency_cleans_up_owned_instance():
    from modules.infrastructure.shared_utilities.lm_studio_model_lifecycle import (
        execute_lm_studio_model_transaction,
    )

    responses = iter(
        [
            _Response(_inventory()),
            _Response({"type": "llm", "instance_id": "owned", "status": "loaded"}),
            _Response(_inventory(("owned",), other_instances=("foreign",))),
            _Response({"instance_id": "owned"}),
            _Response(_inventory(other_instances=("foreign",))),
        ]
    )
    calls = []

    def urlopen(request, **_kwargs):
        calls.append(request)
        response = next(responses)
        response.url = request.full_url
        return response

    with patch(f"{TRANSPORT}._open_no_redirect", side_effect=urlopen):
        with pytest.raises(RuntimeError, match="managed_capacity_changed"):
            execute_lm_studio_model_transaction(
                model_key="nvidia/nemotron-3.5-lightning",
                operation=lambda _lease: None,
            )

    assert sum(request.full_url.endswith("/unload") for request in calls) == 1


def test_load_confirmation_journal_failure_unloads_known_instance(monkeypatch):
    from modules.infrastructure.shared_utilities.lm_studio_lifecycle_intent import (
        LMStudioLifecycleIntentJournal,
    )
    from modules.infrastructure.shared_utilities.lm_studio_model_lifecycle import (
        execute_lm_studio_model_transaction,
    )

    original = LMStudioLifecycleIntentJournal.transition

    def transition(self, intent, phase, **kwargs):
        if phase == "load_confirmed":
            raise OSError("injected journal failure")
        return original(self, intent, phase, **kwargs)

    monkeypatch.setattr(LMStudioLifecycleIntentJournal, "transition", transition)
    calls = []
    responses = iter(
        [
            _Response(_inventory()),
            _Response(
                {"type": "llm", "instance_id": "known", "status": "loaded"}
            ),
            _Response({"instance_id": "known"}),
            _Response(_inventory()),
        ]
    )

    def urlopen(request, **_kwargs):
        calls.append(request)
        response = next(responses)
        response.url = request.full_url
        return response

    with patch(f"{TRANSPORT}._open_no_redirect", side_effect=urlopen):
        with pytest.raises(OSError, match="journal failure"):
            execute_lm_studio_model_transaction(
                model_key="nvidia/nemotron-3.5-lightning",
                operation=lambda _lease: None,
            )

    assert sum(request.full_url.endswith("/unload") for request in calls) == 1


def test_authentication_is_forwarded_but_never_enters_receipt():
    from modules.infrastructure.shared_utilities.lm_studio_model_lifecycle import (
        execute_lm_studio_model_transaction,
    )

    requests = []

    def urlopen(request, **_kwargs):
        requests.append(request)
        response = _Response(_inventory(("borrowed",)))
        response.url = request.full_url
        return response

    with patch(f"{TRANSPORT}._open_no_redirect", side_effect=urlopen):
        result = execute_lm_studio_model_transaction(
            model_key="nvidia/nemotron-3.5-lightning",
            api_token="test-token-value",
            operation=lambda lease: lease.instance_id,
        )

    assert requests[0].get_header("Authorization") == "Bearer test-token-value"
    assert "test-token-value" not in json.dumps(result.lifecycle_receipt.to_dict())


def test_operation_lease_contains_no_api_credential():
    from modules.infrastructure.shared_utilities.lm_studio_model_lifecycle import (
        LMStudioModelLease,
    )

    lease = LMStudioModelLease("model", "instance", "http://localhost:1234")

    assert not hasattr(lease, "api_token")
    assert "token" not in repr(lease).lower()


def test_loopback_aliases_share_one_node_lock_identity():
    from modules.infrastructure.shared_utilities.lm_studio_native_transport import (
        lm_studio_node_identity,
    )

    assert lm_studio_node_identity("http://localhost:1234") == lm_studio_node_identity(
        "http://127.0.0.1:1234/v1"
    )


@pytest.mark.parametrize("observed_instance", ["owned-before-crash", "different"])
def test_process_restart_quarantines_residency_even_when_instance_id_matches(
    _isolated_lifecycle_intent_runtime, observed_instance
):
    from modules.infrastructure.shared_utilities import lm_studio_model_lifecycle as lm
    from modules.infrastructure.shared_utilities.lm_studio_lifecycle_intent import (
        LMStudioLifecycleIntentJournal,
    )
    from modules.infrastructure.shared_utilities.lm_studio_native_transport import (
        _model_state_from_inventory,
        lm_studio_node_identity,
    )

    scope = lm._digest(lm_studio_node_identity("http://localhost:1234"))
    first_process = LMStudioLifecycleIntentJournal(
        scope, runtime_root=_isolated_lifecycle_intent_runtime
    )
    intent = first_process.prepare("nvidia/nemotron-3.5-lightning", lm._digest({}))
    first_process.transition(intent, "load_confirmed", instance_id="owned-before-crash")
    restarted = LMStudioLifecycleIntentJournal(
        scope, runtime_root=_isolated_lifecycle_intent_runtime
    )
    state = _model_state_from_inventory(
        "nvidia/nemotron-3.5-lightning", _inventory(("owned-before-crash",))
    )
    with patch(
        f"{TRANSPORT}._open_no_redirect",
        return_value=_Response(_inventory((observed_instance,))),
    ) as request:
        with pytest.raises(RuntimeError, match="lifecycle_recovery_required"):
            lm._recover_prior_intent(
                restarted, state, "http://localhost:1234", None, 30.0
            )

    assert restarted.read().phase == "quarantined"
    assert request.call_count == 1


def test_process_restart_quarantines_unidentified_interrupted_load(
    _isolated_lifecycle_intent_runtime,
):
    from modules.infrastructure.shared_utilities import lm_studio_model_lifecycle as lm
    from modules.infrastructure.shared_utilities.lm_studio_lifecycle_intent import (
        LMStudioLifecycleIntentJournal,
    )
    from modules.infrastructure.shared_utilities.lm_studio_native_transport import (
        _model_state_from_inventory,
        lm_studio_node_identity,
    )

    scope = lm._digest(lm_studio_node_identity("http://localhost:1234"))
    journal = LMStudioLifecycleIntentJournal(
        scope, runtime_root=_isolated_lifecycle_intent_runtime
    )
    intent = journal.prepare("nvidia/nemotron-3.5-lightning", lm._digest({}))
    journal.transition(intent, "load_requested")
    state = _model_state_from_inventory(
        "nvidia/nemotron-3.5-lightning", _inventory(("unidentified",))
    )

    with patch(
        f"{TRANSPORT}._open_no_redirect",
        return_value=_Response(_inventory(("unidentified",))),
    ):
        with pytest.raises(RuntimeError, match="lifecycle_recovery_required"):
            lm._recover_prior_intent(
                journal, state, "http://localhost:1234", None, 30.0
            )

    assert journal.read().phase == "quarantined"


def test_intent_atomic_replace_failure_preserves_prior_complete_record(
    _isolated_lifecycle_intent_runtime,
):
    from modules.infrastructure.shared_utilities.lm_studio_lifecycle_intent import (
        LMStudioLifecycleIntentJournal,
    )

    journal = LMStudioLifecycleIntentJournal(
        "a" * 64, runtime_root=_isolated_lifecycle_intent_runtime
    )
    prepared = journal.prepare("nvidia/nemotron-3.5-lightning", "b" * 64)

    with patch(
        "modules.infrastructure.shared_utilities.runtime_atomic_replace._atomic_replace_path",
        side_effect=OSError("injected replace failure"),
    ):
        with pytest.raises(OSError, match="replace failure"):
            journal.transition(prepared, "load_requested")

    assert journal.read() == prepared
    assert list(_isolated_lifecycle_intent_runtime.glob("*.tmp")) == []


def test_non_loopback_base_url_is_rejected_before_network():
    from modules.infrastructure.shared_utilities.lm_studio_model_lifecycle import (
        inspect_lm_studio_model,
    )

    with patch(f"{TRANSPORT}._open_no_redirect") as urlopen:
        with pytest.raises(ValueError, match="base_url_invalid"):
            inspect_lm_studio_model(
                "nvidia/nemotron-3.5-lightning",
                base_url="https://example.com:1234",
            )

    urlopen.assert_not_called()


def test_authentication_failure_is_named_and_secret_free():
    from modules.infrastructure.shared_utilities.lm_studio_model_lifecycle import (
        LMStudioAuthenticationError,
        inspect_lm_studio_model,
    )

    error = urllib.error.HTTPError(
        "http://localhost:1234/api/v1/models", 401, "secret-token", {}, None
    )
    with patch(f"{TRANSPORT}._open_no_redirect", side_effect=error):
        with pytest.raises(LMStudioAuthenticationError) as exc:
            inspect_lm_studio_model(
                "nvidia/nemotron-3.5-lightning", api_token="secret-token"
            )

    assert "secret-token" not in str(exc.value)


def test_lifecycle_receipt_rejects_tamper():
    from modules.infrastructure.shared_utilities.lm_studio_model_lifecycle import (
        execute_lm_studio_model_transaction,
        rehydrate_lm_studio_model_lifecycle_receipt,
    )

    with patch(
        f"{TRANSPORT}._open_no_redirect",
        return_value=_Response(_inventory(("borrowed",))),
    ):
        result = execute_lm_studio_model_transaction(
            model_key="nvidia/nemotron-3.5-lightning",
            operation=lambda lease: lease.instance_id,
        )
    payload = result.lifecycle_receipt.to_dict()
    payload["instance_id"] = "tampered"

    with pytest.raises(ValueError, match="receipt_id_invalid"):
        rehydrate_lm_studio_model_lifecycle_receipt(payload)
