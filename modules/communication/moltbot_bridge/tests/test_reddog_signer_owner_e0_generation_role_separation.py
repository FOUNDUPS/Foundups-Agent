"""Generation-authority role separation for owner E0 admission."""

from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.tests.test_reddog_signer_owner_controlled_e0_admission import (
    _CURRENT_SELECTION,
    _fixture,
)


@pytest.mark.parametrize(
    "authority_key",
    [
        "grant_authority_public_key",
        "revocation_authority_public_key",
        "target_signer_public_key",
    ],
)
def test_generation_authority_key_must_be_independent(
    tmp_path: Path, authority_key: str
) -> None:
    fixture = _fixture(tmp_path)
    value = fixture["policy"][authority_key]
    fixture["selection"]["generation_public_key"] = value
    _CURRENT_SELECTION["generation_public_key"] = value

    result = fixture["boundary"].admit(
        fixture["owner_config_path"], fixture["policy"]
    )
    assert result.accepted is False
