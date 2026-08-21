"""Crash, ownership, and retained-identity production-binding regressions."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

from modules.ai_intelligence.ai_gateway.src.model_autoresearch_configured_gateway_evidence import (
    DirectoryConfiguredGatewayReceiptStore,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_production_binding_claims import (
    load_or_create_claim,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_production_binding_artifact_durability import (
    open_interrupted_posix_publication,
    publish_held_artifact,
    seal_staged_artifact,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_production_binding_outputs import (
    claim_output_transaction,
    cleanup_output_transaction,
)
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_single_model_production_binding import (
    bind_authenticated_single_model_promotion_to_runtime,
)
from modules.ai_intelligence.ai_gateway.tests.test_model_autoresearch_single_model_production_binding import (
    REPO_ROOT,
    _authenticated_gate,
    _external_bundle,
    _production_applied,
    _production_inputs,
    _stored_payloads,
)


def _claim_inputs(tmp_path: Path) -> dict:
    store = DirectoryConfiguredGatewayReceiptStore(
        tmp_path / "store", repo_root=REPO_ROOT
    )
    return {
        "publication_identity": SimpleNamespace(binding_digest="sha256:" + "a" * 64),
        "authority_use": SimpleNamespace(receipt_store=store),
        "selection_output": tmp_path / "runtime" / "selection.json",
        "runtime_output": tmp_path / "runtime" / "binding.json",
    }


def test_claim_receipt_race_loads_one_exact_winner_token(tmp_path):
    inputs = _claim_inputs(tmp_path)
    with ThreadPoolExecutor(max_workers=8) as pool:
        claims = list(pool.map(lambda _value: load_or_create_claim(inputs), range(24)))
    assert len({claim.token for claim in claims}) == 1
    assert len({claim.selection_stage for claim in claims}) == 1


def test_subprocess_death_after_claim_reuses_exact_owned_markers(tmp_path):
    inputs = _claim_inputs(tmp_path)
    code = _claim_crash_script(inputs)
    completed = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT, check=False)
    assert completed.returncode == 23
    transaction = claim_output_transaction(inputs)
    assert transaction.selection_stage.is_file()
    assert transaction.runtime_stage.is_file()
    cleanup_output_transaction(transaction)


def test_provider_bundle_retry_is_zero_callback(tmp_path, monkeypatch):
    authenticated, benchmark, policy, authority_use = _authenticated_gate(tmp_path)
    import modules.ai_intelligence.ai_gateway.src.model_autoresearch_production_binding_runner as runner

    real_execute = runner.execute_production_binding
    attempts, provider_calls = [], []

    def fail_before_execution(*, inputs, bundle):
        attempts.append(True)
        if len(attempts) == 1:
            raise OSError("crash-after-durable-provider-bundle")
        return real_execute(inputs=inputs, bundle=bundle)

    def provider(preview):
        provider_calls.append(preview.selection_receipt_id)
        return _external_bundle(preview, authenticated, benchmark, policy)

    monkeypatch.setattr(runner, "execute_production_binding", fail_before_execution)
    inputs = _production_inputs(
        tmp_path, authenticated, benchmark, authority_use, provider
    )
    with pytest.raises(OSError, match="crash-after-durable-provider-bundle"):
        bind_authenticated_single_model_promotion_to_runtime(**inputs)
    result = bind_authenticated_single_model_promotion_to_runtime(**inputs)
    assert result.runtime_binding.accepted
    assert len(provider_calls) == 1


def test_unreadable_provider_receipt_fails_closed_before_second_callback(
    tmp_path, monkeypatch
):
    authenticated, benchmark, policy, authority_use = _authenticated_gate(tmp_path)
    import modules.ai_intelligence.ai_gateway.src.model_autoresearch_production_binding_runner as runner

    real_execute = runner.execute_production_binding
    provider_calls = []

    def fail_once(*, inputs, bundle):
        monkeypatch.setattr(runner, "execute_production_binding", real_execute)
        raise OSError("crash-after-provider-receipt")

    def provider(preview):
        provider_calls.append(preview.selection_receipt_id)
        return _external_bundle(preview, authenticated, benchmark, policy)

    monkeypatch.setattr(runner, "execute_production_binding", fail_once)
    inputs = _production_inputs(
        tmp_path, authenticated, benchmark, authority_use, provider
    )
    with pytest.raises(OSError, match="crash-after-provider-receipt"):
        bind_authenticated_single_model_promotion_to_runtime(**inputs)
    real_load = authority_use.receipt_store.load

    def unreadable(receipt_id):
        if receipt_id.startswith("single-model-production-provider:"):
            raise OSError("transient-store-error")
        return real_load(receipt_id)

    monkeypatch.setattr(authority_use.receipt_store, "load", unreadable)
    with pytest.raises(ValueError, match="provider_receipt_unreadable"):
        bind_authenticated_single_model_promotion_to_runtime(**inputs)
    assert len(provider_calls) == 1


@pytest.mark.parametrize("death_at_seal", [1, 2])
def test_process_death_after_supply_resumes_without_provider_callback(
    tmp_path, death_at_seal
):
    completed = subprocess.run(
        [sys.executable, "-c", _supply_crash_script(tmp_path, death_at_seal)],
        cwd=REPO_ROOT,
        check=False,
    )
    assert completed.returncode == 40 + death_at_seal
    authenticated, benchmark, policy, authority_use = _authenticated_gate(tmp_path)
    provider_calls = []
    inputs = _production_inputs(
        tmp_path,
        authenticated,
        benchmark,
        authority_use,
        lambda preview: provider_calls.append(preview),
    )
    result = bind_authenticated_single_model_promotion_to_runtime(**inputs)
    assert result.runtime_binding.accepted
    assert provider_calls == []


def test_competing_bindings_reserve_before_provider_callback(tmp_path):
    authenticated, benchmark, policy, authority_use = _authenticated_gate(tmp_path)
    calls = []

    def invoke(index):
        def provider(preview):
            calls.append(index)
            time.sleep(0.05)
            return _external_bundle(preview, authenticated, benchmark, policy)

        inputs = _production_inputs(
            tmp_path / str(index), authenticated, benchmark, authority_use, provider
        )
        try:
            bind_authenticated_single_model_promotion_to_runtime(**inputs)
            return "ok"
        except ValueError as error:
            return str(error)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(invoke, range(2)))
    assert len(calls) == 1
    assert results.count("ok") == 1
    assert sum("authority_binding_conflict" in item for item in results) == 1


def test_cleanup_preserves_foreign_stage_replacement(tmp_path, monkeypatch):
    authenticated, benchmark, policy, authority_use = _authenticated_gate(tmp_path)
    import modules.ai_intelligence.ai_gateway.src.model_autoresearch_production_binding_runner as runner

    real_persist = runner.persist_provider_bundle
    replacement = b"foreign-replacement-must-survive"
    attacked = []

    def replace_after_persist(inputs, bundle):
        real_persist(inputs, bundle)
        stage = inputs["output_transaction"].selection_stage
        foreign = stage.with_name("foreign-stage")
        foreign.write_bytes(replacement)
        os.replace(foreign, stage)
        attacked.append(stage)
        raise OSError("after-provider-persistence")

    monkeypatch.setattr(runner, "persist_provider_bundle", replace_after_persist)
    inputs = _production_inputs(
        tmp_path,
        authenticated,
        benchmark,
        authority_use,
        lambda preview: _external_bundle(preview, authenticated, benchmark, policy),
    )
    with pytest.raises(ValueError, match="output_ownership_conflict"):
        bind_authenticated_single_model_promotion_to_runtime(**inputs)
    assert attacked[0].read_bytes() == replacement


@pytest.mark.parametrize("attack", ["replacement", "hardlink", "symlink"])
def test_postseal_substitution_never_reaches_applied_or_final(
    tmp_path, monkeypatch, attack
):
    authenticated, benchmark, policy, authority_use = _authenticated_gate(tmp_path)
    import modules.ai_intelligence.ai_gateway.src.model_autoresearch_production_binding_execution as execution
    import modules.ai_intelligence.ai_gateway.src.model_autoresearch_production_binding_artifact_durability as durability

    real_persist = execution.persist_terminal_receipt
    preserved = []

    def attack_before_terminal(inputs, bundle, transaction, sealed):
        stage = sealed[0].path
        if attack == "hardlink":
            other = stage.with_name("hardlink-preserved")
            os.link(stage, other)
            preserved.append(stage)
        else:
            original = stage.with_name("original-preserved")
            original_bytes = durability.verify_held_artifact(sealed[0])
            os.replace(stage, original)
            if attack == "replacement":
                stage.write_bytes(original_bytes)
            else:
                try:
                    stage.symlink_to(original)
                except OSError as error:
                    pytest.skip(f"file symlink unavailable: {error}")
            preserved.append(stage)
        return real_persist(inputs, bundle, transaction, sealed)

    monkeypatch.setattr(execution, "persist_terminal_receipt", attack_before_terminal)
    inputs = _production_inputs(
        tmp_path,
        authenticated,
        benchmark,
        authority_use,
        lambda preview: _external_bundle(preview, authenticated, benchmark, policy),
    )
    with pytest.raises(ValueError, match="output_ownership_conflict"):
        bind_authenticated_single_model_promotion_to_runtime(**inputs)
    assert not _production_applied(_stored_payloads(authority_use))
    assert all(path.exists() or path.is_symlink() for path in preserved)
    assert not Path(inputs["selection_output_path"]).exists()
    assert not Path(inputs["runtime_binding_output_path"]).exists()


def test_foreign_final_is_preserved_after_applied_publish_conflict(
    tmp_path, monkeypatch
):
    authenticated, benchmark, policy, authority_use = _authenticated_gate(tmp_path)
    import modules.ai_intelligence.ai_gateway.src.model_autoresearch_production_binding_outputs as outputs

    real_publish = outputs.publish_held_artifact
    foreign = b"operator-owned-final"
    injected = []

    def occupy_final(held, final):
        if not injected:
            final.write_bytes(foreign)
            injected.append(final)
        return real_publish(held, final)

    monkeypatch.setattr(outputs, "publish_held_artifact", occupy_final)
    inputs = _production_inputs(
        tmp_path,
        authenticated,
        benchmark,
        authority_use,
        lambda preview: _external_bundle(preview, authenticated, benchmark, policy),
    )
    with pytest.raises(ValueError, match="output_ownership_conflict"):
        bind_authenticated_single_model_promotion_to_runtime(**inputs)
    assert _production_applied(_stored_payloads(authority_use))
    assert injected[0].read_bytes() == foreign
    assert not Path(inputs["runtime_binding_output_path"]).exists()


def test_store_process_death_midwrite_never_exposes_partial_final(tmp_path):
    root = tmp_path / "atomic-store"
    receipt_id = "atomic-crash-receipt"
    code = _store_crash_script(root, receipt_id)
    completed = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT, check=False)
    assert completed.returncode == 29
    store = DirectoryConfiguredGatewayReceiptStore(root, repo_root=REPO_ROOT)
    assert not store._path(receipt_id).exists()
    receipt = SimpleNamespace(
        receipt_id=receipt_id,
        to_dict=lambda: {"receipt_id": receipt_id, "value": "complete"},
    )
    assert store.append(receipt) == receipt_id
    assert store.load(receipt_id)["value"] == "complete"


@pytest.mark.skipif(os.name == "nt", reason="POSIX hard-link publication only")
def test_posix_process_death_after_link_resumes_exact_publication(tmp_path):
    stage, final = tmp_path / "stage.json", tmp_path / "final.json"
    stage.write_text('{"value":"exact"}\n', encoding="utf-8", newline="\n")
    sealed = seal_staged_artifact(stage)
    proof = sealed.proof
    sealed.close()
    code = f"import os; os.link({str(stage)!r}, {str(final)!r}); os._exit(47)"
    completed = subprocess.run([sys.executable, "-c", code], check=False)
    assert completed.returncode == 47
    held = open_interrupted_posix_publication(stage, final, proof)
    assert held is not None
    try:
        publish_held_artifact(held, final)
    finally:
        held.close()
    assert not stage.exists()
    assert final.read_text(encoding="utf-8") == '{"value":"exact"}\n'


@pytest.mark.skipif(os.name == "nt", reason="POSIX hard-link creation only")
def test_posix_process_death_after_claim_link_repairs_pending_name(tmp_path):
    target = tmp_path / "claim.json"
    payload = b'{"claim":"exact"}\n'
    code = f"""
import os
from pathlib import Path
from modules.ai_intelligence.ai_gateway.src import model_autoresearch_configured_gateway_atomic_create as atomic
atomic._remove_owned_temporary=lambda *args,**kwargs:os._exit(48)
atomic.atomic_create_bytes(Path({str(target)!r}),{payload!r},root=Path({str(tmp_path)!r}))
"""
    completed = subprocess.run([sys.executable, "-c", code], check=False)
    assert completed.returncode == 48
    from modules.ai_intelligence.ai_gateway.src.model_autoresearch_configured_gateway_atomic_create import (
        atomic_create_bytes,
    )

    assert atomic_create_bytes(target, payload, root=tmp_path) is False
    assert target.read_bytes() == payload
    assert target.stat().st_nlink == 1


def test_recovery_closes_interrupted_artifact_when_payload_is_invalid(
    tmp_path, monkeypatch
):
    import modules.ai_intelligence.ai_gateway.src.model_autoresearch_production_binding_recovery as recovery

    held = SimpleNamespace(closed=False, close=lambda: setattr(held, "closed", True))
    monkeypatch.setattr(
        recovery.artifact_durability,
        "open_interrupted_posix_publication",
        lambda *_args: held,
    )
    monkeypatch.setattr(
        recovery.artifact_durability,
        "read_held_json",
        lambda *_args: (_ for _ in ()).throw(ValueError("invalid-json")),
    )
    monkeypatch.setattr(
        recovery.artifact_durability,
        "open_verified_artifact",
        lambda *_args: (_ for _ in ()).throw(OSError("no-candidate")),
    )

    with pytest.raises(ValueError, match="terminal_artifact_missing"):
        recovery._load_artifact(
            tmp_path / "final.json",
            tmp_path / "stage.json",
            "sha256:" + "0" * 64,
            SimpleNamespace(),
        )

    assert held.closed is True


def test_recovery_closes_selection_when_runtime_proof_is_invalid(tmp_path, monkeypatch):
    import modules.ai_intelligence.ai_gateway.src.model_autoresearch_production_binding_recovery as recovery

    selection = _closing_artifact()
    monkeypatch.setattr(recovery, "_load_artifact", lambda *_args: ({}, selection))
    proof_calls = []

    def parse_proof(_value):
        if proof_calls:
            raise ValueError("runtime-proof-invalid")
        proof_calls.append(True)
        return SimpleNamespace()

    monkeypatch.setattr(recovery.artifact_durability, "proof_from_dict", parse_proof)
    with pytest.raises(ValueError, match="runtime-proof-invalid"):
        recovery._recover_verified_terminal(
            {}, _recovery_transaction(tmp_path), _recovery_receipt()
        )
    assert selection.closed is True


def test_recovery_closes_both_artifacts_when_trusted_time_fails(tmp_path, monkeypatch):
    import modules.ai_intelligence.ai_gateway.src.model_autoresearch_production_binding_recovery as recovery

    selection, runtime = _closing_artifact(), _closing_artifact()
    artifacts = iter((selection, runtime))
    monkeypatch.setattr(
        recovery, "_load_artifact", lambda *_args: ({}, next(artifacts))
    )
    monkeypatch.setattr(
        recovery.artifact_durability,
        "proof_from_dict",
        lambda _value: SimpleNamespace(),
    )
    monkeypatch.setattr(
        recovery,
        "trusted_campaign_authority_time",
        lambda _context: (_ for _ in ()).throw(ValueError("trusted-time-failed")),
    )
    inputs = {"authority_use": SimpleNamespace()}
    with pytest.raises(ValueError, match="trusted-time-failed"):
        recovery._recover_verified_terminal(
            inputs, _recovery_transaction(tmp_path), _recovery_receipt()
        )
    assert selection.closed is True
    assert runtime.closed is True


def _closing_artifact():
    artifact = SimpleNamespace(closed=False)
    artifact.close = lambda: setattr(artifact, "closed", True)
    return artifact


def _recovery_transaction(tmp_path):
    return SimpleNamespace(
        selection_output=tmp_path / "selection-final.json",
        selection_stage=tmp_path / "selection-stage.json",
        runtime_output=tmp_path / "runtime-final.json",
        runtime_stage=tmp_path / "runtime-stage.json",
    )


def _recovery_receipt():
    return SimpleNamespace(
        selection_source=None,
        selection_digest="sha256:" + "1" * 64,
        selection_proof={},
        runtime_source=None,
        runtime_digest="sha256:" + "2" * 64,
        runtime_proof={},
        verified_evidence_bundle={},
    )


def _claim_crash_script(inputs: dict) -> str:
    store = inputs["authority_use"].receipt_store.root
    return f"""
import os
from pathlib import Path
from types import SimpleNamespace
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_configured_gateway_evidence import DirectoryConfiguredGatewayReceiptStore
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_production_binding_outputs import claim_output_transaction
store=DirectoryConfiguredGatewayReceiptStore(Path({str(store)!r}), repo_root=Path({str(REPO_ROOT)!r}))
inputs={{'publication_identity':SimpleNamespace(binding_digest={"sha256:" + "a" * 64!r}),'authority_use':SimpleNamespace(receipt_store=store),'selection_output':Path({str(inputs["selection_output"])!r}),'runtime_output':Path({str(inputs["runtime_output"])!r})}}
claim_output_transaction(inputs)
os._exit(23)
"""


def _store_crash_script(root: Path, receipt_id: str) -> str:
    return f"""
import os
from pathlib import Path
from types import SimpleNamespace
from modules.ai_intelligence.ai_gateway.src import model_autoresearch_configured_gateway_atomic_create as atomic
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_configured_gateway_evidence import DirectoryConfiguredGatewayReceiptStore
def die(descriptor, path, payload):
    os.write(descriptor, payload[:7]); os.fsync(descriptor); os._exit(29)
atomic._write_temporary=die
store=DirectoryConfiguredGatewayReceiptStore(Path({str(root)!r}), repo_root=Path({str(REPO_ROOT)!r}))
rid={receipt_id!r}
store.append(SimpleNamespace(to_dict=lambda:{{'receipt_id':rid,'value':'complete'}}))
"""


def _supply_crash_script(root: Path, death_at_seal: int) -> str:
    return f"""
import os
from pathlib import Path
import modules.ai_intelligence.ai_gateway.src.model_autoresearch_production_binding_execution as execution
from modules.ai_intelligence.ai_gateway.src.model_autoresearch_single_model_production_binding import bind_authenticated_single_model_promotion_to_runtime
from modules.ai_intelligence.ai_gateway.tests.test_model_autoresearch_single_model_production_binding import _authenticated_gate, _external_bundle, _production_inputs
root=Path({str(root)!r})
authenticated,benchmark,policy,authority_use=_authenticated_gate(root)
real=execution.durability._fsync_regular_file
count=[0]
def die(path):
    count[0]+=1
    if count[0]=={death_at_seal}:
        os._exit({40 + death_at_seal})
    return real(path)
provider=lambda preview:_external_bundle(preview,authenticated,benchmark,policy)
execution.durability._fsync_regular_file=die
bind_authenticated_single_model_promotion_to_runtime(**_production_inputs(root,authenticated,benchmark,authority_use,provider))
"""
