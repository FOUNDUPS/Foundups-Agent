"""
OBS WebSocket Controller for antifaFM Autonomous Broadcasting

Controls OBS Studio programmatically to stream antifaFM radio to YouTube.

IMPORTANT: Uses obsws-python (OBS WebSocket v5 protocol for OBS 28+)
NOT obs-websocket-py which is for v4 protocol (OBS 27 and below)

Requirements:
1. OBS Studio 28+ with WebSocket server enabled
2. In OBS: Tools -> WebSocket Server Settings -> Enable WebSocket Server
3. Note the port (default 4455) and password (or disable auth for testing)

Usage:
    from obs_controller import OBSController

    controller = OBSController(host='192.168.0.10')
    await controller.connect()
    await controller.add_radio_source()  # Adds to current scene
    await controller.start_streaming()

Install: pip install obsws-python
"""

import asyncio
import logging
import os
import time
from typing import Optional, Dict, Any, Tuple

from modules.platform_integration.antifafm_broadcaster.src.obs_logging_guard import (
    create_obs_req_client,
    install_obs_logging_guard,
)

logger = logging.getLogger(__name__)

# Use obsws-python (v5 protocol for OBS 28+)
OBS_CLIENT = None
try:
    install_obs_logging_guard()
    import obsws_python as obs
    OBS_CLIENT = "obsws_python"
except ImportError:
    logger.warning("obsws-python not installed. Run: pip install obsws-python")


class OBSController:
    """Autonomous OBS controller for antifaFM streaming."""

    def __init__(
        self,
        host: str = None,
        port: int = None,
        password: str = None
    ):
        self.host = host or os.getenv("OBS_WEBSOCKET_HOST", "localhost")
        self.port = int(port or os.getenv("OBS_WEBSOCKET_PORT", 4455))
        self.password = password if password is not None else os.getenv("OBS_WEBSOCKET_PASSWORD", "")
        self.ws = None
        self.connected = False
        self.last_start_error: Optional[str] = None

        # antifaFM configuration
        self.radio_source_name = "antifaFM Radio"
        self.radio_url = "https://a12.asurahosting.com/listen/antifafm/radio.mp3"

    async def connect(self) -> bool:
        """Connect to OBS WebSocket server."""
        if OBS_CLIENT is None:
            logger.error("No OBS WebSocket client available. Run: pip install obsws-python")
            return False

        try:
            self.ws = create_obs_req_client(
                obs,
                host=self.host,
                port=self.port,
                password=self.password,
            )
            self.connected = True
            logger.info(f"[OBS] Connected to OBS on {self.host}:{self.port}")
            return True

        except Exception as e:
            logger.error(f"[OBS] Connection failed: {e}")
            logger.info("[OBS] Make sure OBS is running and WebSocket server is enabled")
            logger.info("[OBS] In OBS: Tools -> WebSocket Server Settings -> Enable")
            return False

    def disconnect(self):
        """Disconnect from OBS."""
        self.connected = False
        self.ws = None
        logger.info("[OBS] Disconnected")

    async def get_version(self) -> Optional[str]:
        """Get OBS version info."""
        if not self.connected:
            return None
        try:
            result = self.ws.get_version()
            return result.obs_version
        except Exception as e:
            logger.error(f"[OBS] GetVersion failed: {e}")
            return None

    async def get_current_scene(self) -> Optional[str]:
        """Get the current program scene name."""
        if not self.connected:
            return None
        try:
            result = self.ws.get_current_program_scene()
            return result.scene_name
        except Exception as e:
            logger.error(f"[OBS] get_current_scene failed: {e}")
            return None

    async def add_radio_source(self) -> bool:
        """Add antifaFM Radio source to current scene."""
        if not self.connected:
            return False

        try:
            scene_name = await self.get_current_scene()
            if not scene_name:
                logger.error("[OBS] Could not get current scene")
                return False

            # Check if source already exists
            inputs = self.ws.get_input_list()
            existing = [inp['inputName'] for inp in inputs.inputs]

            if self.radio_source_name in existing:
                logger.info(f"[OBS] Radio source already exists, updating settings...")
                self.ws.set_input_settings(
                    self.radio_source_name,
                    {
                        'input': self.radio_url,
                        'is_local_file': False,
                        'restart_on_activate': True,
                    },
                    True  # overlay
                )
            else:
                logger.info(f"[OBS] Creating radio source: {self.radio_source_name}")
                # create_input(sceneName, inputName, inputKind, inputSettings, sceneItemEnabled)
                self.ws.create_input(
                    scene_name,
                    self.radio_source_name,
                    'ffmpeg_source',
                    {
                        'input': self.radio_url,
                        'is_local_file': False,
                        'restart_on_activate': True,
                        'hw_decode': False,
                    },
                    True
                )

            # Ensure not muted and volume at 100%
            self.ws.set_input_mute(self.radio_source_name, False)
            self.ws.set_input_volume(self.radio_source_name, vol_mul=1.0)

            logger.info(f"[OBS] Radio source configured: {self.radio_url}")
            return True

        except Exception as e:
            logger.error(f"[OBS] add_radio_source failed: {e}")
            return False

    async def add_image_source(
        self,
        source_name: str,
        image_path: str,
        width: int = 1920,
        height: int = 1080,
    ) -> bool:
        """Add an image source to current scene."""
        if not self.connected:
            return False

        try:
            scene_name = await self.get_current_scene()
            if not scene_name:
                return False

            # Check if already exists
            inputs = self.ws.get_input_list()
            existing = [inp['inputName'] for inp in inputs.inputs]

            if source_name in existing:
                logger.info(f"[OBS] Image source exists, updating: {source_name}")
                self.ws.set_input_settings(
                    source_name,
                    {'file': image_path},
                    True
                )
            else:
                logger.info(f"[OBS] Creating image source: {source_name}")
                self.ws.create_input(
                    scene_name,
                    source_name,
                    'image_source',
                    {'file': image_path},
                    True
                )

            logger.info(f"[OBS] Image source added: {image_path}")
            return True

        except Exception as e:
            logger.error(f"[OBS] add_image_source failed: {e}")
            return False

    async def add_video_source(
        self,
        source_name: str,
        video_path: str,
        loop: bool = True,
    ) -> bool:
        """Add a video source (looping) to current scene."""
        if not self.connected:
            return False

        try:
            scene_name = await self.get_current_scene()
            if not scene_name:
                return False

            inputs = self.ws.get_input_list()
            existing = [inp['inputName'] for inp in inputs.inputs]

            settings = {
                'local_file': video_path,
                'is_local_file': True,
                'looping': loop,
                'restart_on_activate': True,
                'hw_decode': False,
            }

            if source_name in existing:
                logger.info(f"[OBS] Video source exists, updating: {source_name}")
                self.ws.set_input_settings(source_name, settings, True)
            else:
                logger.info(f"[OBS] Creating video source: {source_name}")
                self.ws.create_input(
                    scene_name,
                    source_name,
                    'ffmpeg_source',
                    settings,
                    True
                )

            logger.info(f"[OBS] Video source added: {video_path}")
            return True

        except Exception as e:
            logger.error(f"[OBS] add_video_source failed: {e}")
            return False

    async def add_color_source(
        self,
        source_name: str = "Background",
        color: int = 0xFF000000,  # Black (ARGB)
        width: int = 1920,
        height: int = 1080,
    ) -> bool:
        """Add a solid color background source."""
        if not self.connected:
            return False

        try:
            scene_name = await self.get_current_scene()
            if not scene_name:
                return False

            inputs = self.ws.get_input_list()
            existing = [inp['inputName'] for inp in inputs.inputs]

            settings = {
                'color': color,
                'width': width,
                'height': height,
            }

            if source_name in existing:
                self.ws.set_input_settings(source_name, settings, True)
            else:
                self.ws.create_input(
                    scene_name,
                    source_name,
                    'color_source_v3',
                    settings,
                    True
                )

            logger.info(f"[OBS] Color source added: {source_name}")
            return True

        except Exception as e:
            logger.error(f"[OBS] add_color_source failed: {e}")
            return False

    async def check_radio_playing(self) -> Dict[str, Any]:
        """Check if radio source is playing."""
        if not self.connected:
            return {"playing": False, "error": "not connected"}

        try:
            status = self.ws.get_media_input_status(self.radio_source_name)
            return {
                "playing": status.media_state == "OBS_MEDIA_STATE_PLAYING",
                "state": status.media_state,
                "cursor": status.media_cursor,
            }
        except Exception as e:
            return {"playing": False, "error": str(e)}

    async def restart_radio(self) -> bool:
        """Restart the radio source."""
        if not self.connected:
            return False

        try:
            self.ws.trigger_media_input_action(
                self.radio_source_name,
                'OBS_WEBSOCKET_MEDIA_INPUT_ACTION_RESTART'
            )
            logger.info("[OBS] Radio restarted")
            return True
        except Exception as e:
            logger.error(f"[OBS] restart_radio failed: {e}")
            return False

    async def start_streaming(self, verify_timeout_s: Optional[float] = None) -> bool:
        """
        Start OBS streaming output and verify it becomes active.

        OBS can accept StartStream while still waiting for YouTube's
        "Create broadcast and start streaming" confirmation dialog.
        This method polls output status and only reports success once
        output_active is true.
        """
        if not self.connected:
            self.last_start_error = "not_connected"
            return False

        try:
            self.last_start_error = None
            # Check if already streaming
            status = self.ws.get_stream_status()
            if status.output_active:
                logger.info("[OBS] Already streaming")
                return True

            # Start stream
            self.ws.start_stream()
            verify_timeout_s = float(
                verify_timeout_s
                if verify_timeout_s is not None
                else os.getenv("ANTIFAFM_OBS_START_VERIFY_SECONDS", "20")
            )
            poll_interval_s = float(os.getenv("ANTIFAFM_OBS_START_POLL_SECONDS", "0.5"))

            if verify_timeout_s <= 0:
                logger.info("[OBS] Start stream requested (verification skipped)")
                return True

            deadline = time.monotonic() + verify_timeout_s
            last_status = None
            while time.monotonic() < deadline:
                await asyncio.sleep(max(0.1, poll_interval_s))
                try:
                    last_status = self.ws.get_stream_status()
                except Exception as status_error:
                    logger.warning(f"[OBS] Could not read stream status during startup: {status_error}")
                    continue

                if last_status.output_active:
                    logger.info(
                        "[OBS] Streaming started and verified "
                        f"(duration={last_status.output_duration}ms bytes={last_status.output_bytes})"
                    )
                    return True

            reconnecting = bool(getattr(last_status, "output_reconnecting", False))
            output_bytes = getattr(last_status, "output_bytes", 0)
            output_duration = getattr(last_status, "output_duration", 0)

            self.last_start_error = "stream_output_inactive_after_start"
            logger.error(
                "[OBS] Start stream request was accepted but output never became active "
                f"within {verify_timeout_s:.1f}s "
                f"(reconnecting={reconnecting}, bytes={output_bytes}, duration={output_duration}ms)."
            )
            logger.error(
                "[OBS] Likely waiting on YouTube broadcast setup modal in OBS. "
                "If visible, click 'Create broadcast and start streaming'."
            )

            try:
                from modules.ai_intelligence.ai_overseer.src.preflight_resolution import (
                    on_preflight_fail,
                )

                on_preflight_fail(
                    component="obs_start",
                    severity="critical",
                    payload={
                        "error_code": "stream_output_inactive_after_start",
                        "source_file": "antifafm_broadcaster/src/obs_controller.py",
                        "source_function": "OBSController.start_streaming",
                        "verify_timeout_s": verify_timeout_s,
                        "poll_interval_s": poll_interval_s,
                        "output_bytes": output_bytes,
                        "output_duration_ms": output_duration,
                        "reconnecting": reconnecting,
                        "likely_cause": "youtube_broadcast_modal_or_binding",
                        "requires_012": True,
                        "automation_candidate": True,
                        "safe_autonomous_actions": [
                            "verify_broadcast_binding",
                            "verify_stream_service_rtmp_custom",
                        ],
                        "unsafe_actions": [
                            "click_youtube_studio_modal",
                            "browser_automation",
                            "credential_refresh",
                        ],
                        "remediation": [
                            "verify_broadcast_stream_binding",
                            "verify_obs_stream_service_config",
                            "escalate_012_modal_intervention",
                        ],
                    },
                    source="antifafm_broadcaster/src/obs_controller.py:start_streaming",
                )
            except Exception:
                pass

            return False

        except Exception as e:
            self.last_start_error = str(e)
            logger.error(f"[OBS] Start streaming failed: {e}")
            return False

    def _read_stream_service(self) -> Tuple[str, Dict[str, Any]]:
        """Read current OBS stream service settings."""
        response = self.ws.get_stream_service_settings()

        service_type = getattr(response, "stream_service_type", None)
        settings = getattr(response, "stream_service_settings", None)

        if isinstance(response, dict):
            service_type = service_type or response.get("streamServiceType") or response.get("stream_service_type")
            settings = settings or response.get("streamServiceSettings") or response.get("stream_service_settings")

        return str(service_type or ""), settings if isinstance(settings, dict) else {}

    async def ensure_stream_service_custom(self, server_url: str, stream_key: str) -> bool:
        """
        Configure OBS streaming service to custom RTMP(S) mode.

        This bypasses OBS's YouTube account-managed setup modal and allows
        full startup automation through WebSocket + YouTube API.
        """
        if not self.connected:
            self.last_start_error = "not_connected"
            return False

        desired_server = (server_url or "").strip().rstrip("/")
        desired_key = (stream_key or "").strip()
        if not desired_server or not desired_key:
            self.last_start_error = "missing_stream_service_config"
            logger.error("[OBS] Missing stream server/key for custom service configuration")
            return False

        try:
            current_type, current_settings = self._read_stream_service()
            current_server = str(current_settings.get("server", "")).strip().rstrip("/")
            current_key = str(current_settings.get("key", "")).strip()

            if (
                current_type == "rtmp_custom"
                and current_server == desired_server
                and current_key == desired_key
            ):
                logger.info("[OBS] Stream service already set to custom RTMPS target")
                return True

            self.ws.set_stream_service_settings(
                "rtmp_custom",
                {
                    "server": desired_server,
                    "key": desired_key,
                    "use_auth": False,
                },
            )

            new_type, new_settings = self._read_stream_service()
            new_server = str(new_settings.get("server", "")).strip().rstrip("/")
            new_key = str(new_settings.get("key", "")).strip()
            if new_type != "rtmp_custom" or new_server != desired_server or new_key != desired_key:
                self.last_start_error = "stream_service_config_mismatch"
                logger.error("[OBS] Stream service did not persist expected custom RTMPS settings")
                return False

            masked_key = f"{desired_key[:4]}..." if len(desired_key) >= 4 else "***"
            logger.info(
                "[OBS] Stream service configured: "
                f"type=rtmp_custom server={desired_server} key={masked_key}"
            )
            return True
        except Exception as e:
            self.last_start_error = str(e)
            logger.error(f"[OBS] Failed configuring custom stream service: {e}")
            return False

    def get_last_start_error(self) -> Optional[str]:
        """Return last start_streaming failure reason, if any."""
        return self.last_start_error

    async def stop_streaming(self) -> bool:
        """Stop OBS streaming."""
        if not self.connected:
            return False

        try:
            self.ws.stop_stream()
            logger.info("[OBS] Streaming stopped")
            return True
        except Exception as e:
            logger.error(f"[OBS] Stop streaming failed: {e}")
            return False

    async def get_stream_status(self) -> Dict[str, Any]:
        """Get current streaming status."""
        if not self.connected:
            return {"connected": False}

        try:
            status = self.ws.get_stream_status()
            return {
                "connected": True,
                "streaming": status.output_active,
                "bytes_sent": status.output_bytes,
                "duration": status.output_duration,
                "reconnecting": status.output_reconnecting,
            }
        except Exception as e:
            return {"connected": True, "error": str(e)}

    async def list_inputs(self) -> list:
        """List all inputs (sources) in OBS."""
        if not self.connected:
            return []

        try:
            result = self.ws.get_input_list()
            return [
                {"name": inp['inputName'], "kind": inp['inputKind']}
                for inp in result.inputs
            ]
        except Exception as e:
            logger.error(f"[OBS] list_inputs failed: {e}")
            return []

    async def get_scene_item_id(self, source_name: str) -> Optional[int]:
        """Get scene item ID for a source in current scene."""
        if not self.connected:
            return None

        try:
            scene_name = await self.get_current_scene()
            if not scene_name:
                return None

            result = self.ws.get_scene_item_id(scene_name, source_name)
            return result.scene_item_id
        except Exception as e:
            logger.error(f"[OBS] get_scene_item_id failed for {source_name}: {e}")
            return None

    async def set_source_position(
        self,
        source_name: str,
        x: float,
        y: float,
        width: float = None,
        height: float = None,
        scale_x: float = None,
        scale_y: float = None,
    ) -> bool:
        """Set position and optionally size of a source."""
        if not self.connected:
            return False

        try:
            scene_name = await self.get_current_scene()
            item_id = await self.get_scene_item_id(source_name)

            if not scene_name or not item_id:
                logger.error(f"[OBS] Could not find scene item: {source_name}")
                return False

            transform = {
                "positionX": x,
                "positionY": y,
            }

            if width is not None:
                transform["boundsWidth"] = width
                transform["boundsType"] = "OBS_BOUNDS_SCALE_INNER"
            if height is not None:
                transform["boundsHeight"] = height
                transform["boundsType"] = "OBS_BOUNDS_SCALE_INNER"
            if scale_x is not None:
                transform["scaleX"] = scale_x
            if scale_y is not None:
                transform["scaleY"] = scale_y

            self.ws.set_scene_item_transform(scene_name, item_id, transform)
            logger.info(f"[OBS] Positioned {source_name} at ({x}, {y})")
            return True

        except Exception as e:
            logger.error(f"[OBS] set_source_position failed: {e}")
            return False

    async def set_source_bounds(
        self,
        source_name: str,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> bool:
        """Set position and bounds (size) of a source."""
        if not self.connected:
            return False

        try:
            scene_name = await self.get_current_scene()
            item_id = await self.get_scene_item_id(source_name)

            if not scene_name or not item_id:
                logger.error(f"[OBS] Could not find scene item: {source_name}")
                return False

            transform = {
                "positionX": x,
                "positionY": y,
                "boundsWidth": width,
                "boundsHeight": height,
                "boundsType": "OBS_BOUNDS_SCALE_INNER",
            }

            self.ws.set_scene_item_transform(scene_name, item_id, transform)
            logger.info(f"[OBS] Set bounds for {source_name}: ({x},{y}) {width}x{height}")
            return True

        except Exception as e:
            logger.error(f"[OBS] set_source_bounds failed: {e}")
            return False

    async def list_scene_items(self) -> list:
        """List all scene items in current scene with their positions."""
        if not self.connected:
            return []

        try:
            scene_name = await self.get_current_scene()
            if not scene_name:
                return []

            result = self.ws.get_scene_item_list(scene_name)
            items = []
            for item in result.scene_items:
                items.append({
                    "id": item.get("sceneItemId"),
                    "name": item.get("sourceName"),
                    "index": item.get("sceneItemIndex"),
                })
            return items

        except Exception as e:
            logger.error(f"[OBS] list_scene_items failed: {e}")
            return []

    async def set_source_order(self, source_name: str, index: int) -> bool:
        """Set the z-order (layer) of a source. 0 = bottom, higher = front."""
        if not self.connected:
            return False

        try:
            scene_name = await self.get_current_scene()
            item_id = await self.get_scene_item_id(source_name)

            if not scene_name or not item_id:
                return False

            self.ws.set_scene_item_index(scene_name, item_id, index)
            logger.info(f"[OBS] Set {source_name} to index {index}")
            return True

        except Exception as e:
            logger.error(f"[OBS] set_source_order failed: {e}")
            return False


async def test_obs_connection():
    """Test OBS WebSocket connection."""
    print("=" * 50)
    print("OBS WebSocket Connection Test")
    print("=" * 50)

    # Use environment or defaults
    host = os.getenv("OBS_WEBSOCKET_HOST", "localhost")
    controller = OBSController(host=host)

    print(f"\nConnecting to OBS on {controller.host}:{controller.port}...")
    if await controller.connect():
        version = await controller.get_version()
        print(f"OBS Version: {version}")

        scene = await controller.get_current_scene()
        print(f"Current Scene: {scene}")

        status = await controller.get_stream_status()
        print(f"Stream Status: {status}")

        # List inputs
        inputs = await controller.list_inputs()
        print(f"\nInputs ({len(inputs)}):")
        for inp in inputs:
            print(f"  - {inp['name']} ({inp['kind']})")

        # Check radio status
        radio = await controller.check_radio_playing()
        print(f"\nRadio Status: {radio}")

        controller.disconnect()
        print("\nOBS connection test PASSED!")
    else:
        print("\nOBS connection test FAILED!")
        print("\nTo enable OBS WebSocket:")
        print("1. Open OBS Studio")
        print("2. Tools -> WebSocket Server Settings")
        print("3. Enable WebSocket Server")
        print("4. Set port (default 4455)")
        print("5. Optionally set password")


async def setup_antifafm_stream():
    """Set up complete antifaFM streaming configuration."""
    print("=" * 50)
    print("antifaFM Stream Setup")
    print("=" * 50)

    from pathlib import Path

    host = os.getenv("OBS_WEBSOCKET_HOST", "localhost")
    controller = OBSController(host=host)

    if not await controller.connect():
        print("Failed to connect to OBS")
        return False

    # Add radio source
    print("\n[1] Adding radio source...")
    await controller.add_radio_source()

    # Add background video
    print("\n[2] Adding background video...")
    video_path = Path(__file__).parent.parent / "assets" / "backgrounds" / "January 18 2026.mp4"
    if video_path.exists():
        await controller.add_video_source("antifaFM Background", str(video_path), loop=True)
    else:
        print(f"Video not found: {video_path}")
        # Add black background instead
        await controller.add_color_source("antifaFM Background", 0xFF000000)

    # Check status
    print("\n[3] Checking status...")
    status = await controller.get_stream_status()
    radio = await controller.check_radio_playing()

    print(f"Stream: {'ACTIVE' if status.get('streaming') else 'NOT STREAMING'}")
    print(f"Radio: {'PLAYING' if radio.get('playing') else 'NOT PLAYING'}")

    if not status.get('streaming'):
        print("\n[4] Start streaming? (call controller.start_streaming())")

    controller.disconnect()
    return True


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--setup":
        asyncio.run(setup_antifafm_stream())
    else:
        asyncio.run(test_obs_connection())
