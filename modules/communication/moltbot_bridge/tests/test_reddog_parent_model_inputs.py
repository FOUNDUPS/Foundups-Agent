"""Actual protected-loader/Ed25519 model join; OS owner reads use labeled seams."""

from copy import deepcopy
from pathlib import Path
import pytest

from .test_reddog_parent_consent_owner_versions import owner_fixture, legacy
from .test_reddog_parent_consensus_domains import dual
from .reddog_parent_model_test_support import model_inputs
from modules.communication.moltbot_bridge.src import reddog_signer_system_service_owner_inputs as inputs
from modules.communication.moltbot_bridge.src import reddog_signer_system_service_manifest_selection_loader as loader
from modules.communication.moltbot_bridge.src.reddog_parent_consensus_model_evidence import verified_model_evidence
from modules.communication.moltbot_bridge.src.reddog_model_verifier_selection_inputs import SelectionReadBudget
from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_verified_admission import verified_runtime_binding_receipt


def fixture(monkeypatch, tmp_path):
    values, owner = owner_fixture(monkeypatch, tmp_path)
    now = owner['model_verifier_authority']['issued_at'] + 1
    records, authority = model_inputs(monkeypatch, owner['runtime_root'], now=now)
    _, parent, _ = dual()
    parent.update(**{key: owner['parent_consent_authority'][key] for key in ('policy_digest', 'repo_full_name', 'foundup_id')})
    owner.update(schema_version=loader.SCHEMA_VERSION_V12, parent_reviewer_designation_authority=parent,
                 model_verifier_authority=authority)
    legacy._write(values, owner)
    return values, owner, records, now


def check(values, owner, records, now):
    return verified_model_evidence(owner_path=values['owner_config_path'], repo=values['repo'],
        owner_id=owner['config_id'], artifacts=records, clock=lambda: now)


def test_actual_v12_loader_three_signed_selections_share_one_bounded_pass(monkeypatch, tmp_path):
    values, owner, records, now = fixture(monkeypatch, tmp_path)
    assert loader._load_owner_config(values['owner_config_path'], repo=values['repo']) == owner
    reads, real_read = [], inputs.secure_read_confined_bytes
    def read(path, **kwargs):
        result = real_read(path, **kwargs)
        reads.append((str(path), len(result[0])))
        return result
    monkeypatch.setattr(inputs, 'secure_read_confined_bytes', read)
    author, resolver = check(values, owner, records, now)
    bindings = {author.model_runtime_binding_digest}
    for identity, record in records['reviewers'].items():
        receipt = verified_runtime_binding_receipt(record['binding'])
        evidence = resolver.resolve(identity, receipt.selection_receipt_id, receipt.runtime_binding_receipt_id)
        assert evidence is not None
        bindings.add(evidence.model_runtime_binding_digest)
    assert len(bindings) == 3 and len(reads) == 18
    assert sum(size for _, size in reads) < 8 * 1024 * 1024


@pytest.mark.parametrize('fault', ['duplicate_id', 'duplicate_digest', 'missing', 'extra', 'substitute', 'file', 'rotate'])
def test_selected_model_inputs_reject_mismatched_or_changed_authority(monkeypatch, tmp_path, fault):
    values, owner, records, now = fixture(monkeypatch, tmp_path)
    entries = owner['model_verifier_authority']['entries']
    if fault == 'duplicate_id': entries[1]['selection_receipt_id'] = entries[0]['selection_receipt_id']
    elif fault == 'duplicate_digest': entries[1]['selection_receipt_digest'] = entries[0]['selection_receipt_digest']
    elif fault == 'missing': entries.pop()
    elif fault == 'extra': entries.append(dict(entries[0], selection_receipt_id='model_selection_receipt:' + 'f'*64, selection_receipt_digest='sha256:'+'e'*64))
    elif fault == 'substitute': entries[1]['inputs'] = deepcopy(entries[0]['inputs'])
    elif fault == 'file': Path(entries[0]['inputs']['policy']['path']).write_bytes(b'{}')
    if fault != 'file': legacy._write(values, owner)
    if fault in ('duplicate_id', 'duplicate_digest', 'missing', 'extra', 'file'):
        with pytest.raises(ValueError): check(values, owner, records, now)
        return
    _, resolver = check(values, owner, records, now)
    if fault == 'rotate':
        owner['model_verifier_authority']['expires_at'] -= 1
        legacy._write(values, owner)
    record = records['reviewers']['reviewer:test']
    receipt = verified_runtime_binding_receipt(record['binding'])
    assert resolver.resolve('reviewer:test', receipt.selection_receipt_id, receipt.runtime_binding_receipt_id) is None


@pytest.mark.parametrize('limit', ['reads', 'bytes'])
def test_shared_budget_never_resets_between_selected_records(limit):
    budget = SelectionReadBudget()
    if limit == 'reads': budget.reads = 54
    else: budget.bytes = 8 * 1024 * 1024
    with pytest.raises(ValueError): budget.begin()


@pytest.mark.parametrize('fault', [None, 'selection_digest', 'owner', 'expiry'])
def test_actual_v12_current_generation_model_gate(monkeypatch, tmp_path, fault):
    from modules.communication.moltbot_bridge.src import reddog_signer_current_generation_runtime_binding as gate
    from modules.communication.moltbot_bridge.src.reddog_runtime_artifact_manifest_contract import digest
    from modules.ai_intelligence.ai_gateway.src.model_runtime_binding_digest import canonical_model_runtime_binding_digest
    values, owner, records, now = fixture(monkeypatch, tmp_path)
    pair = records['author']
    fields = dict(model_selection_receipt_id=pair['selection']['receipt_id'],
        model_selection_digest=digest(pair['selection']),
        model_runtime_binding_receipt_id=pair['binding']['receipt_id'],
        model_runtime_binding_digest=canonical_model_runtime_binding_digest(pair['binding']))
    work = dict(work_order_id='work:actual-v12', **fields,
        model_selection_receipt=pair['selection'], model_runtime_binding_receipt=pair['binding'])
    authority = dict(fields, work_order_digest=digest(work))
    selected = dict(owner_config_id=owner['config_id'], selection_expires_at=now+10, manifest_expires_at=now+10)
    if fault == 'selection_digest': authority['model_selection_digest'] = 'sha256:'+'f'*64
    elif fault == 'owner': selected['owner_config_id'] = 'other-owner'
    elif fault == 'expiry': selected['selection_expires_at'] = now
    result = gate._validated_model_values(values['repo'],
        dict(owner_authority_config_path=str(values['owner_config_path'])), selected, work, authority, lambda: now, now)
    assert bool(result) is (fault is None)
    if result:
        assert result['model_work_order_digest'] == digest(work)
        assert result['model_valid_until'] > now
