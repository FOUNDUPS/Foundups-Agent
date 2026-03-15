from pathlib import Path
from unittest.mock import patch

from modules.communication.moltbot_bridge.src.openclaw_dae import (
    IntentCategory,
    OpenClawDAE,
)


PROJECT_ROOT = Path(__file__).resolve().parents[4]


def test_classify_launch_holodae_as_system_runtime():
    dae = OpenClawDAE(repo_root=PROJECT_ROOT)

    intent = dae.classify_intent(
        message="launch holodae",
        sender="012",
        channel="discord",
        session_key="runtime-1",
    )

    assert intent.category == IntentCategory.SYSTEM
    assert intent.metadata["classification_method"] == "deterministic_dae_runtime"


def test_classify_status_social_media_as_monitor_runtime():
    dae = OpenClawDAE(repo_root=PROJECT_ROOT)

    intent = dae.classify_intent(
        message="status social media dae",
        sender="012",
        channel="discord",
        session_key="runtime-2",
    )

    assert intent.category == IntentCategory.MONITOR
    assert intent.metadata["classification_method"] == "deterministic_dae_runtime"


def test_execute_system_routes_to_dae_runtime_adapter():
    dae = OpenClawDAE(repo_root=PROJECT_ROOT)
    intent = dae.classify_intent(
        message="launch holodae",
        sender="012",
        channel="discord",
        session_key="runtime-3",
    )

    with patch(
        "modules.communication.moltbot_bridge.src.dae_runtime_adapter.handle_dae_runtime_intent",
        return_value="DAE runtime launch `holodae` -> starting.",
    ) as mocked:
        response = dae._execute_system(intent)

    mocked.assert_called_once()
    assert "holodae" in response


def test_execute_monitor_routes_to_dae_runtime_adapter():
    dae = OpenClawDAE(repo_root=PROJECT_ROOT)
    intent = dae.classify_intent(
        message="list launchable daes",
        sender="012",
        channel="discord",
        session_key="runtime-4",
    )

    with patch(
        "modules.communication.moltbot_bridge.src.dae_runtime_adapter.handle_dae_runtime_intent",
        return_value="Launchable DAEs:\n- holodae: running=False enabled=True domain=ai_intelligence name=HoloDAE",
    ) as mocked:
        response = dae._execute_monitor(intent)

    mocked.assert_called_once()
    assert "Launchable DAEs" in response
