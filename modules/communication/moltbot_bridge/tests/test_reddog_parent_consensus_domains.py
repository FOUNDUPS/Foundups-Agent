"""Explicit dual reviewer domains; disposable signatures, no runtime enrollment."""

from copy import deepcopy
import pytest

from .reddog_reviewer_authority_test_support import fixture, artifact, canonical, digest, sign
from modules.communication.moltbot_bridge.src import reddog_reviewer_designation_contract as contract
from modules.communication.moltbot_bridge.src import reddog_signer_owner_e0_principal_records as records


def dual():
    effect, designation, issuer, _ = fixture()
    parent = dict(effect, schema_version=contract.PARENT_AUTHORITY_SCHEMA,
                  privilege=contract.PARENT_PRIVILEGE,
                  decision_schema_version=contract.PARENT_DECISION_SCHEMA)
    endorsed = dict(designation, schema_version=contract.PARENT_DESIGNATION_SCHEMA,
                    privilege=contract.PARENT_PRIVILEGE,
                    decision_schema_version=contract.PARENT_DECISION_SCHEMA,
                    owner_authority_digest=digest(parent))
    sign(endorsed, issuer, contract.PARENT_SIGNING_PREFIX)
    value = artifact(effect, designation)
    value.update(schema_version=records.SCHEMA_VERSION_V3,
                 reviewer_authorizations=[designation, endorsed])
    return effect, parent, value


def test_dual_domains_parse_without_cross_domain_fallback():
    effect, parent, value = dual()
    assert contract.validate_reviewer_designation_authority(effect) == effect
    assert contract.validate_parent_reviewer_designation_authority(parent) == parent
    _, grants = records.parse_principal_artifact(canonical(value).encode('ascii'))
    assert len(grants) == 2
    assert contract.select_reviewer_designation(grants, contract.PRIVILEGE)['privilege'] == contract.PRIVILEGE
    assert contract.select_reviewer_designation(grants, contract.PARENT_PRIVILEGE)['privilege'] == contract.PARENT_PRIVILEGE
    with pytest.raises(ValueError):
        contract.validate_reviewer_designation_authority(parent)


@pytest.mark.parametrize('case', ['duplicate', 'third', 'unknown', 'mixed', 'legacy', 'empty'])
def test_dual_domains_reject_ambiguous_or_legacy_widening(case):
    _, _, value = dual()
    grants = value['reviewer_authorizations']
    if case == 'duplicate': grants[1] = deepcopy(grants[0])
    elif case == 'third': grants.append(deepcopy(grants[0]))
    elif case == 'unknown': grants[1]['privilege'] = 'any_reviewer'
    elif case == 'mixed': grants[1]['decision_schema_version'] = contract.DECISION_SCHEMA
    elif case == 'legacy': value['schema_version'] = records.SCHEMA_VERSION_V2
    else: value['reviewer_authorizations'] = []
    with pytest.raises(ValueError):
        records.parse_principal_artifact(canonical(value).encode('ascii'))


def test_v12_preserves_both_explicit_authorities(monkeypatch, tmp_path):
    from .test_reddog_parent_consent_owner_versions import owner_fixture, legacy
    from modules.communication.moltbot_bridge.src import reddog_signer_system_service_manifest_selection_loader as loader
    values, owner = owner_fixture(monkeypatch, tmp_path)
    _, parent, _ = dual()
    parent.update(**{key: owner['parent_consent_authority'][key]
                    for key in ('policy_digest', 'repo_full_name', 'foundup_id')})
    owner.update(schema_version=loader.SCHEMA_VERSION_V12, parent_reviewer_designation_authority=parent)
    original = owner['model_verifier_authority']
    owner['model_verifier_authority'] = dict(schema_version='reddog_model_verifier_selection_authority.v1',
        issued_at=original['issued_at'], expires_at=original['expires_at'], entries=[dict(
            selection_receipt_id='model_selection_receipt:' + 'a' * 64,
            selection_receipt_digest='sha256:' + 'b' * 64, inputs=original['inputs'])])
    legacy._write(values, owner)
    assert loader._load_owner_config(values['owner_config_path'], repo=values['repo']) == owner
    owner['parent_reviewer_designation_authority']['privilege'] = contract.PRIVILEGE
    legacy._write(values, owner)
    with pytest.raises(ValueError):
        loader._load_owner_config(values['owner_config_path'], repo=values['repo'])


@pytest.mark.parametrize('method', [contract.reviewer_designation_authority_digest, contract.reviewer_designation_signing_input])
@pytest.mark.parametrize('base', [object, dict])
def test_designation_dispatch_never_calls_untrusted_get(method, base):
    calls = []
    class Trap(base):
        def get(self, *args):
            calls.append(args)
            raise AssertionError('arbitrary dispatch')
    with pytest.raises(ValueError):
        method(Trap())
    assert calls == []
