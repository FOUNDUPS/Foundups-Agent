"""Fail-closed permission regressions for mutating OpenClaw intents."""

from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from modules.communication.moltbot_bridge.src.openclaw_dae import (
    AutonomyTier,
    IntentCategory,
    OpenClawDAE,
    OpenClawIntent,
)
from modules.communication.moltbot_bridge.src.openclaw_foundup_orchestrator import (
    clear_job_queue,
    dispatch_foundup,
    get_job_queue,
)


def _intent(category: IntentCategory, *, authorized: bool) -> OpenClawIntent:
    return OpenClawIntent(
        raw_message="modify the governed target",
        category=category,
        confidence=0.99,
        sender="principal" if authorized else "untrusted",
        channel="test",
        session_key="permission-regression",
        is_authorized_commander=authorized,
    )


@pytest.mark.parametrize(
    "category",
    [
        IntentCategory.COMMAND,
        IntentCategory.SYSTEM,
        IntentCategory.SCHEDULE,
        IntentCategory.SOCIAL,
        IntentCategory.AUTOMATION,
        IntentCategory.FOUNDUP,
        IntentCategory.TRAINING,
        IntentCategory.IMPROVEMENT,
    ],
)
def test_untrusted_mutation_cannot_pass_as_advisory(
    tmp_path: Path, category: IntentCategory
) -> None:
    dae = OpenClawDAE(repo_root=tmp_path)
    intent = _intent(category, authorized=False)

    tier = dae._resolve_autonomy_tier(intent)

    assert tier is AutonomyTier.ADVISORY
    assert dae._check_permission_gate(intent, tier) is False


@pytest.mark.parametrize("category", [IntentCategory.FOUNDUP, IntentCategory.IMPROVEMENT])
def test_source_mutation_without_permission_manager_is_denied(
    tmp_path: Path, category: IntentCategory
) -> None:
    dae = OpenClawDAE(repo_root=tmp_path)
    intent = _intent(category, authorized=True)

    with patch.object(
        type(dae), "permissions", new_callable=PropertyMock, return_value=None
    ):
        tier = dae._resolve_autonomy_tier(intent)
        assert tier is AutonomyTier.ADVISORY
        assert dae._check_permission_gate(intent, tier) is False


def test_foundup_mutation_uses_source_tier_when_permissions_exist(tmp_path: Path) -> None:
    dae = OpenClawDAE(repo_root=tmp_path)
    dae._permissions = MagicMock()

    tier = dae._resolve_autonomy_tier(
        _intent(IntentCategory.FOUNDUP, authorized=True)
    )

    assert tier is AutonomyTier.SOURCE


def test_direct_foundup_dispatch_cannot_bypass_permission_gate() -> None:
    clear_job_queue()
    intent = _intent(IntentCategory.FOUNDUP, authorized=False)
    intent.raw_message = "create foundup attacker_demo"

    result = dispatch_foundup(MagicMock(), intent)

    assert "mutation denied" in result.lower()
    assert get_job_queue() == []
