"""v13 inherited parent/effect crypto paths, with existing labeled OS-owner seams."""
from . import test_reddog_parent_consensus_signer as signer
from .reddog_parent_consensus_test_support import setup
import pytest


@pytest.mark.parametrize('domain', ['parent', 'effect'])
def test_v13_parent_effect_actual_model_and_factory_path(monkeypatch, tmp_path, domain):
    def current_setup(*args, **kwargs):
        state = setup(*args, **kwargs)
        # The full v13 owner schema is separately exercised by custody tests.
        # This existing fixture replaces OS owner loading, not cryptographic checks.
        state.owner['schema_version'] = state.loader.SCHEMA_VERSION_V13
        return state
    monkeypatch.setattr(signer, 'setup', current_setup)
    signer.test_current_model_parent_effect_authority_reaches_actual_factory_signer(monkeypatch, tmp_path, domain)
