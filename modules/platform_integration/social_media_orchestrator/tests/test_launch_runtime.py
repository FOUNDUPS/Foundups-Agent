import asyncio
import threading
import time

from modules.platform_integration.social_media_orchestrator.scripts import launch as social_launch


def test_stop_social_media_dae_returns_not_running():
    social_launch._social_media_instance = None
    social_launch._social_media_status.clear()

    result = social_launch.stop_social_media_dae()

    assert result["status"] == "not_running"


def test_social_media_dae_stop_interrupts_wait(monkeypatch):
    dae = social_launch.SocialMediaDAE(cadence_minutes=15)
    dae._trigger_available = False
    dae._trigger_mixin = None

    async def runner():
        task = asyncio.create_task(dae.run())
        await asyncio.sleep(0.01)
        dae.stop()
        await asyncio.wait_for(task, timeout=0.5)

    asyncio.run(runner())

    assert dae.active is False


def test_run_social_media_dae_supports_stop_hook(monkeypatch):
    class FakeSocialMediaDAE:
        def __init__(self, cadence_minutes=15):
            self.cadence_minutes = cadence_minutes
            self.active = False

        async def run(self):
            self.active = True
            while self.active:
                await asyncio.sleep(0.01)

        def stop(self):
            self.active = False

    social_launch._social_media_instance = None
    social_launch._social_media_status.clear()
    monkeypatch.setattr(social_launch, "SocialMediaDAE", FakeSocialMediaDAE)

    thread = threading.Thread(target=social_launch.run_social_media_dae.__wrapped__, daemon=True)
    thread.start()

    deadline = time.time() + 2.0
    while time.time() < deadline and social_launch._social_media_instance is None:
        time.sleep(0.01)

    assert social_launch._social_media_instance is not None
    while time.time() < deadline and not social_launch._social_media_instance.active:
        time.sleep(0.01)

    result = social_launch.stop_social_media_dae()
    assert result["status"] == "stopping"

    thread.join(timeout=2.0)
    assert not thread.is_alive()
    assert social_launch._social_media_instance is None
