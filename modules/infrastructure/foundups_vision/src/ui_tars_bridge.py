"""
UI-TARS Bridge - Connection to UI-TARS Desktop for Vision-Based Browser Automation

WSP Compliance:
    - WSP 3: Infrastructure domain
    - WSP 77: AI Overseer integration (telemetry events)
    - WSP 91: DAEMON observability

UI-TARS Desktop Location: E:/HoloIndex/models/ui-tars-1.5
"""

import asyncio
import json
import logging
import math
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

UI_TARS_MODEL = os.getenv("UI_TARS_MODEL", "ui-tars-1.5-7b")
# Default paths
UI_TARS_PATH = Path(os.getenv("UI_TARS_PATH", "E:/HoloIndex/models/ui-tars-1.5"))
UI_TARS_TELEMETRY = UI_TARS_PATH / "telemetry"
SCREENSHOT_DIR = Path("modules/infrastructure/foundups_vision/memory/screenshots")


def _ui_tars_15_image_size(width: int, height: int) -> tuple[int, int]:
    """Explicit Qwen2.5-VL image grid for the verified UI-TARS1.5 profile.

    ByteDance UI-TARS README_coordinates.md specifies factor28 and these bounds.
    Pre-resize the submitted image so the decoder need not guess a hidden grid.
    """
    if not all(type(v) is int and v > 0 for v in (width, height)):
        raise ValueError("Invalid screenshot dimensions")
    if max(width, height) / min(width, height) > 200:
        raise ValueError("Unsupported screenshot aspect ratio")
    factor, minimum, maximum = 28, 100 * 28 * 28, 16384 * 28 * 28
    w, h = max(factor, round(width / factor) * factor), max(factor, round(height / factor) * factor)
    pixels = width * height
    if w * h > maximum:
        ratio = math.sqrt(pixels / maximum)
        # Avoid dropping an entire28px cell at an exact floating-point boundary.
        w, h = math.floor(width / ratio / factor + 1e-9) * factor, math.floor(height / ratio / factor + 1e-9) * factor
    elif w * h < minimum:
        ratio = math.sqrt(minimum / pixels)
        w, h = math.ceil(width * ratio / factor) * factor, math.ceil(height * ratio / factor) * factor
    return w, h


def _decode_ui_tars_point(output: str, *, coordinate_profile: str = "legacy_1000",
                          image_size: Optional[tuple[int, int]] = None) -> Dict[str, Any]:
    """Decode one literal click; never evaluate model text or guess its units."""
    if coordinate_profile not in {"legacy_1000", "ui_tars_1_5_qwen25vl"}:
        raise ValueError("Unknown UI-TARS coordinate profile")
    if not isinstance(output, str) or len(output) > 4096:
        raise ValueError("Invalid UI-TARS response")
    actions = re.findall(r"^[ \t]*Action:[ \t]*([^\r\n]+)$", output, re.MULTILINE)
    if len(actions) != 1:
        raise ValueError("Expected exactly one UI-TARS Action line")
    match = re.fullmatch(r"click\(\s*start_box\s*=\s*(['\"])(.*?)\1\s*\)", actions[0].strip())
    if not match:
        raise ValueError("Expected a literal UI-TARS click")
    body = match.group(2)
    number = r"(\d+(?:\.\d+)?)"
    point = rf"\(\s*{number}\s*,\s*{number}\s*\)"
    if coordinate_profile == "legacy_1000":
        coordinates = re.fullmatch(rf"<\|box_start\|>{point}<\|box_end\|>(?:{point})?", body)
        bounds = (1000, 1000)
    else:
        if (not isinstance(image_size, tuple) or len(image_size) != 2
                or not all(type(v) is int and v > 0 and v % 28 == 0 for v in image_size)):
            raise ValueError("UI-TARS1.5 requires explicit submitted image grid")
        coordinates = re.fullmatch(rf"{point}(?:\s*,?\s*{point})?", body)
        bounds = image_size
    if not coordinates:
        raise ValueError("Coordinates do not match the declared UI-TARS profile")
    values = [float(v) for v in coordinates.groups() if v is not None]
    if not all(math.isfinite(v) and 0 <= v <= bounds[i % 2] for i, v in enumerate(values)):
        raise ValueError("UI-TARS coordinate outside submitted grid")
    x, y = values[:2]
    if len(values) == 4:
        if values[2] < x or values[3] < y:
            raise ValueError("Inverted UI-TARS box")
        x, y = (x + values[2]) / 2, (y + values[3]) / 2
    normalized = x / bounds[0], y / bounds[1]
    if not all(0 <= v < 1 for v in normalized):
        raise ValueError("UI-TARS point is outside the clickable image")
    return {"box": (x, y), "normalized": normalized,
            "coordinate_profile": coordinate_profile, "model_image_size": bounds}


@dataclass
class ActionResult:
    """Result of a vision-based action."""
    success: bool
    action: str
    description: str
    duration_ms: int
    screenshot_before: Optional[str] = None
    screenshot_after: Optional[str] = None
    error: Optional[str] = None
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "action": self.action,
            "description": self.description,
            "duration_ms": self.duration_ms,
            "screenshot_before": self.screenshot_before,
            "screenshot_after": self.screenshot_after,
            "error": self.error,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class Screenshot:
    """Screenshot capture result."""
    path: str
    timestamp: datetime
    url: Optional[str] = None
    hash: Optional[str] = None
    width: int = 0
    height: int = 0


class UITarsConnectionError(Exception):
    """UI-TARS Desktop not running or unreachable."""
    pass


class ElementNotFoundError(Exception):
    """Vision model could not locate element."""
    pass


class ActionTimeoutError(Exception):
    """Action exceeded timeout."""
    pass


class UITarsBridge:
    """
    Bridge to UI-TARS Desktop for vision-based browser automation.
    
    UI-TARS provides:
    - Remote Browser Operator (vision-based browser control)
    - Screenshot → Element Detection → Action execution
    - MCP integration for tool calling
    
    Usage:
        bridge = UITarsBridge()
        result = await bridge.execute_action(
            action="click",
            description="blue Like button under the comment"
        )
    """

    def __init__(
        self,
        ui_tars_path: str = None,
        browser_port: int = 9222,
        observers: Optional[List[Callable[[str, Dict[str, Any]], None]]] = None,
    ) -> None:
        """
        Initialize UI-TARS bridge.
        
        Args:
            ui_tars_path: Path to UI-TARS Desktop installation
            browser_port: Chrome debugging port
            observers: Telemetry observers for AI Overseer integration
        """
        self.ui_tars_path = Path(ui_tars_path) if ui_tars_path else UI_TARS_PATH
        self.browser_port = browser_port
        self._observers = list(observers or [])
        self._connected = False
        self._session_id = None
        
        # Ensure directories exist
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        UI_TARS_TELEMETRY.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"[UI-TARS] Bridge initialized, path: {self.ui_tars_path}")
        self._emit_event("bridge_init", {"path": str(self.ui_tars_path), "port": browser_port})

    def _emit_event(self, event: str, payload: Dict[str, Any]) -> None:
        """Emit telemetry event to observers."""
        payload["timestamp"] = datetime.utcnow().isoformat() + "Z"
        for observer in self._observers:
            try:
                observer(event, payload)
            except Exception as e:
                logger.warning(f"[UI-TARS] Observer error: {e}")
        
        # Also write to telemetry file for AI Overseer
        try:
            telemetry_file = UI_TARS_TELEMETRY / "bridge_events.jsonl"
            with open(telemetry_file, "a", encoding="utf-8") as f:
                f.write(json.dumps({"event": event, **payload}) + "\n")
        except Exception as e:
            logger.debug(f"[UI-TARS] Telemetry write failed: {e}")

    def register_observer(self, observer: Callable[[str, Dict[str, Any]], None]) -> None:
        """Register a telemetry observer."""
        self._observers.append(observer)

    async def connect(self) -> bool:
        """
        Connect to UI-TARS Desktop.
        
        Returns:
            True if connected successfully
            
        Raises:
            UITarsConnectionError: If UI-TARS is not available
        """
        self._emit_event("connect_start", {"port": self.browser_port})
        
        # Check if UI-TARS path exists
        if not self.ui_tars_path.exists():
            error = f"UI-TARS not found at {self.ui_tars_path}"
            self._emit_event("connect_failed", {"error": error})
            raise UITarsConnectionError(error)

        # Check for UI-TARS process or API
        # For now, we'll use a file-based communication pattern
        # UI-TARS Desktop reads from telemetry/inbox and writes to telemetry/outbox
        inbox = UI_TARS_TELEMETRY / "inbox"
        outbox = UI_TARS_TELEMETRY / "outbox"
        inbox.mkdir(exist_ok=True)
        outbox.mkdir(exist_ok=True)

        # Health check LM Studio / Responses API (port 1234) if configured
        tars_base = os.getenv("TARS_API_URL", "http://127.0.0.1:1234").rstrip("/")
        if tars_base.endswith("/v1"):
            tars_base = tars_base[:-3]
        try:
            import requests  # lightweight check; ignore if missing
            # Use to_thread for health check to avoid blocking loop
            resp = await asyncio.to_thread(requests.get, f"{tars_base}/v1/models", timeout=2)
            if resp.status_code == 200:
                self._emit_event("lm_studio_ready", {"base_url": tars_base})
                logger.info(f"[UI-TARS] LM Studio ready at {tars_base}")
            else:
                self._emit_event("lm_studio_unreachable", {"base_url": tars_base, "status": resp.status_code})
                logger.warning(f"[UI-TARS] LM Studio unreachable ({resp.status_code}) at {tars_base}")
        except Exception as e:
            self._emit_event("lm_studio_unreachable", {"base_url": tars_base, "error": str(e)})
            logger.warning(f"[UI-TARS] LM Studio health check failed: {e}")

        self._connected = True
        self._session_id = f"session_{int(time.time())}"
        
        self._emit_event("connect_success", {"session_id": self._session_id})
        logger.info(f"[UI-TARS] Connected, session: {self._session_id}")
        
        return True

    async def capture_screenshot(self) -> Screenshot:
        """
        Capture current browser state.
        
        Returns:
            Screenshot object with image data and metadata
        """
        import hashlib
        
        timestamp = datetime.now()
        filename = f"screenshot_{timestamp.strftime('%Y%m%d_%H%M%S')}.png"
        filepath = SCREENSHOT_DIR / filename
        
        self._emit_event("screenshot_start", {"path": str(filepath)})
        
        try:
            # Use Chrome DevTools Protocol to capture screenshot
            # This requires browser with --remote-debugging-port=9222
            import requests
            
            # Get browser tabs
            tabs_url = f"http://127.0.0.1:{self.browser_port}/json"
            try:
                # Use to_thread for browse info check
                response = await asyncio.to_thread(requests.get, tabs_url, timeout=5)
                tabs = response.json()
            except Exception as e:
                logger.warning(f"[UI-TARS] Could not connect to browser: {e}")
                # Fallback: create placeholder
                self._emit_event("screenshot_failed", {"error": str(e)})
                return Screenshot(
                    path=str(filepath),
                    timestamp=timestamp,
                    url=None,
                    hash=None,
                )
            
            if tabs:
                # Get WebSocket URL for first tab
                ws_url = tabs[0].get("webSocketDebuggerUrl")
                current_url = tabs[0].get("url")
                
                # For now, use simple screenshot via pyautogui or similar
                # Full CDP implementation would require websocket connection
                logger.info(f"[UI-TARS] Browser URL: {current_url}")
                
                # Calculate hash for deduplication
                file_hash = hashlib.sha256(current_url.encode()).hexdigest()[:16] if current_url else None
                
                self._emit_event("screenshot_complete", {
                    "path": str(filepath),
                    "url": current_url,
                    "hash": file_hash,
                })
                
                return Screenshot(
                    path=str(filepath),
                    timestamp=timestamp,
                    url=current_url,
                    hash=file_hash,
                )
            
        except Exception as e:
            self._emit_event("screenshot_failed", {"error": str(e)})
            logger.error(f"[UI-TARS] Screenshot failed: {e}")
        
        return Screenshot(path=str(filepath), timestamp=timestamp)

    async def execute_action(
        self,
        action: str,
        description: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: int = 90,  # Increased for 7B vision model inference
        **kwargs  # Accept additional parameters like 'target'
    ) -> ActionResult:
        """
        Execute a vision-based action using LM Studio API.

        Args:
            action: Action type ('click', 'type', 'scroll', 'verify')
            description: Human-readable description of target element
            context: Additional context (video_id, comment_id, etc.)
            timeout: Max seconds to wait for action (default 90s for CPU inference)

        Returns:
            ActionResult with success status and details
        """
        start_time = time.time()
        context = context or {}

        self._emit_event("action_start", {
            "action": action,
            "description": description,
            "context": context,
        })

        try:
            # Ensure connected
            if not self._connected:
                await self.connect()

            # Get Selenium driver from context (passed by ActionRouter)
            driver = kwargs.get('driver') or context.get('driver')
            if not driver:
                raise Exception("No Selenium driver available for screenshot/click")

            # 1. Capture screenshot from Selenium (viewport screenshot; includes devicePixelRatio scaling)
            import base64
            from PIL import Image
            import io

            # driver.get_screenshot_as_png() is blocking, but it's localized to Selenium
            # It's better to wrap it as well if it's slow
            screenshot_bytes = await asyncio.to_thread(driver.get_screenshot_as_png)

            # Resize screenshot to speed up inference (1280px width max)
            img = Image.open(io.BytesIO(screenshot_bytes))
            original_screenshot_size = img.size  # Actual screenshot dimensions (with DPI scaling)
            resized_image_size = original_screenshot_size  # Will be set if resized
            coordinate_profile = (context or {}).get("coordinate_profile", "legacy_1000")
            if coordinate_profile not in {"legacy_1000", "ui_tars_1_5_qwen25vl"}:
                raise ValueError("Unknown UI-TARS coordinate profile")
            if coordinate_profile == "ui_tars_1_5_qwen25vl" and UI_TARS_MODEL != "ui-tars-1.5-7b":
                raise ValueError("UI-TARS1.5 profile requires the verified model identifier")

            if img.width > 1280:
                ratio = 1280 / img.width
                resized_image_size = (1280, int(img.height * ratio))
                img = img.resize(resized_image_size, Image.Resampling.LANCZOS)
                logger.info(f"[UI-TARS] Resized screenshot: {original_screenshot_size} -> {resized_image_size}")
            else:
                logger.info(f"[UI-TARS] Using original screenshot size: {original_screenshot_size}")

            if coordinate_profile == "ui_tars_1_5_qwen25vl":
                resized_image_size = _ui_tars_15_image_size(*img.size)
                if img.size != resized_image_size:
                    img = img.resize(resized_image_size, Image.Resampling.LANCZOS)

            # Convert back to PNG bytes
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            screenshot_bytes = img_buffer.getvalue()

            screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')

            # Derive screenshot-to-viewport scale (accounts for devicePixelRatio / Windows scaling)
            screenshot_scale = 1.0
            try:
                # Script execution is usually fast enough, but can be wrapped if driver is busy
                viewport = await asyncio.to_thread(driver.execute_script, 
                    "return {w: window.innerWidth || 0, h: window.innerHeight || 0, dpr: window.devicePixelRatio || 1, topLevel: window.top === window};"
                ) or {}
                vw = float(viewport.get("w") or 0)
                vh = float(viewport.get("h") or 0)
                if coordinate_profile == "ui_tars_1_5_qwen25vl":
                    if viewport.get("topLevel") is not True:
                        raise ValueError("UI-TARS1.5 requires an explicitly verified top-level viewport")
                    if (not all(isinstance(viewport.get(k), (int, float)) and not isinstance(viewport.get(k), bool) for k in ("w", "h"))
                            or not all(math.isfinite(v) and v > 0 for v in (vw, vh))):
                        raise ValueError("UI-TARS1.5 requires finite positive observed viewport geometry")
                    scale_x = original_screenshot_size[0] / vw
                    scale_y = original_screenshot_size[1] / vh
                    if not all(math.isfinite(v) and v > 0 for v in (scale_x, scale_y)):
                        raise ValueError("UI-TARS1.5 screenshot scale is invalid")
                    # Each screenshot axis may round by one physical pixel.
                    if abs(scale_x - scale_y) > 1 / vw + 1 / vh:
                        raise ValueError("UI-TARS1.5 screenshot and viewport geometry are inconsistent")
                    screenshot_scale = scale_x
                elif vw > 0 and vh > 0:
                    screenshot_scale = max(0.1, min(10.0, original_screenshot_size[0] / vw))
                logger.info(
                    f"[UI-TARS] Viewport: {int(vw)}x{int(vh)} dpr={viewport.get('dpr')} screenshot_scale={screenshot_scale:.3f}"
                )
            except Exception as e:
                if coordinate_profile == "ui_tars_1_5_qwen25vl":
                    raise ValueError(f"UI-TARS1.5 cannot verify viewport geometry: {e}") from e
                logger.debug(f"[UI-TARS] Viewport scale check failed: {e}")

            logger.info(f"[UI-TARS] Calling LM Studio API for: {action} - {description}")

            # 2. Call LM Studio API (CRITICAL: MUST NOT BLOCK LOOP)
            import requests
            tars_api_url = os.getenv("TARS_API_URL", "http://127.0.0.1:1234").rstrip("/")
            if tars_api_url.endswith("/v1"):
                tars_api_url = tars_api_url[:-3]

            # Build prompt for UI-TARS model (constrained: stay on page; avoid browser chrome)
            text = (context or {}).get("text") if action == "type" else None
            direction = (context or {}).get("direction") if action == "scroll" else None

            if action == "verify":
                goal = f"Locate (do not click) the {description} on the current page."
            elif action == "type":
                goal = f"Locate the input field for: {description}. You will not type; only locate the field."
            elif action == "scroll":
                goal = f"Locate the area related to: {description}. You will not scroll; only locate the best anchor point."
            else:
                goal = f"Find and click the {description} on the current page."

            coordinate_format = "(x,y)" if coordinate_profile == "ui_tars_1_5_qwen25vl" else "<|box_start|>(x,y)<|box_end|>"
            coordinate_rule = (f"Coordinates are absolute pixels over the provided {resized_image_size[0]}x{resized_image_size[1]} screenshot; do not normalize to1000."
                               if coordinate_profile == "ui_tars_1_5_qwen25vl" else "Coordinates are in a 1000x1000 grid over the provided screenshot.")
            prompt = f"""You are a GUI agent operating INSIDE the current web page content.
Do NOT click the browser address bar, tabs, extensions, or open new pages/tabs. Stay on the current page.

Task: {goal}

Output format (exactly):
Thought: <one short sentence>
Action: click(start_box='{coordinate_format}')

Rules:
- {coordinate_rule}
- Pick the center of the target.
- If the target is not visible or you are unsure, output:
  Thought: <one short sentence>
  Action: finished()"""

            # Wrap blocking requests.post in to_thread
            response = await asyncio.to_thread(
                requests.post,
                f"{tars_api_url}/v1/chat/completions",
                json={
                    "model": UI_TARS_MODEL,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/png;base64,{screenshot_base64}"}
                                }
                            ]
                        }
                    ],
                    "max_tokens": 300,
                    "temperature": 0.1,
                },
                timeout=timeout
            )

            if response.status_code != 200:
                raise Exception(f"LM Studio API error: {response.status_code} - {response.text}")

            # 3. Parse UI-TARS Desktop response format
            response_data = response.json()
            model_output = response_data['choices'][0]['message']['content']

            # Avoid noisy logs/TTS by default; enable with UI_TARS_VERBOSE_OUTPUT=true
            if os.getenv("UI_TARS_VERBOSE_OUTPUT", "false").lower() in {"1", "true", "yes"}:
                logger.info(f"[UI-TARS] Full model output: {model_output}")
            else:
                logger.debug(f"[UI-TARS] Model output (suppressed, set UI_TARS_VERBOSE_OUTPUT=true): {model_output[:200]}")

            # Parse UI-TARS Desktop format: "Action: click(start_box='<|box_start|>(x,y)<|box_end|>')"
            import re

            # Extract thought (optional)
            thought_match = re.search(r'Thought:\s*(.+?)(?=Action:|\Z)', model_output, re.DOTALL)
            thought = thought_match.group(1).strip() if thought_match else ""

            # Decode using the declared contract; grammar does not imply units.
            try:
                point = _decode_ui_tars_point(model_output,
                    coordinate_profile=coordinate_profile, image_size=resized_image_size)
            except ValueError as error:
                return ActionResult(success=False, action=action, description=description,
                    duration_ms=int((time.time() - start_time) * 1000),
                    error=str(error), confidence=0.0)
            box_x, box_y = point["box"]
            normalized_x, normalized_y = point["normalized"]
            # One mapping for both profiles, including DPR and any image resizing.
            resized_pixel_x, resized_pixel_y = normalized_x * resized_image_size[0], normalized_y * resized_image_size[1]
            screenshot_pixel_x = int(normalized_x * original_screenshot_size[0])
            screenshot_pixel_y = int(normalized_y * original_screenshot_size[1])
            if coordinate_profile == "ui_tars_1_5_qwen25vl":
                viewport_css_x, viewport_css_y = int(normalized_x * vw), int(normalized_y * vh)
            else:
                viewport_css_x = int(normalized_x * original_screenshot_size[0] / screenshot_scale)
                viewport_css_y = int(normalized_y * original_screenshot_size[1] / screenshot_scale)

            # [IFRAME AWARENESS] Check if we are currently switched into a frame
            # If so, we must adjust viewport_css coordinates to be relative to the frame's internal (0,0)
            try:
                frame_offset = {"x": 0, "y": 0} if coordinate_profile == "ui_tars_1_5_qwen25vl" else driver.execute_script(
                    """
                    const frame = window.frameElement;
                    if (!frame) return { x: 0, y: 0 };
                    const rect = frame.getBoundingClientRect();
                    return { x: rect.left, y: rect.top };
                    """
                ) or {"x": 0, "y": 0}
                
                if frame_offset["x"] != 0 or frame_offset["y"] != 0:
                    logger.info(f"[UI-TARS] Adjusting for frame offset: ({frame_offset['x']}, {frame_offset['y']})")
                    viewport_css_x -= int(frame_offset["x"])
                    viewport_css_y -= int(frame_offset["y"])
            except Exception as e:
                logger.debug(f"[UI-TARS] Frame offset check skipped: {e}")

            logger.info("[UI-TARS] Coordinate mapping:")
            logger.info(f"  Box ({coordinate_profile}, grid={point['model_image_size']}): ({box_x:.1f}, {box_y:.1f})")
            logger.info(f"  Resized image ({resized_image_size}): ({resized_pixel_x:.0f}, {resized_pixel_y:.0f})")
            logger.info(f"  Screenshot px ({original_screenshot_size}): ({screenshot_pixel_x}, {screenshot_pixel_y})")
            logger.info(f"  Local CSS px: ({viewport_css_x}, {viewport_css_y})")

            executed = None
            if action == "click":
                executed = driver.execute_script(
                    """
                    const x = arguments[0], y = arguments[1];
                    const el = document.elementFromPoint(x, y);
                    if (!el) return { ok: false, error: "No element at point" };

                    // [SENTINEL] Element validation
                    const id = (el.id || "").toLowerCase();
                    const cls = (el.className || "").toLowerCase();
                    const tag = (el.tagName || "").toLowerCase();
                    const html = (el.outerHTML || "").toLowerCase();
                    
                    const adSigs = ["ad", "sponsor", "promoted", "yt-ad", "renderer", "overlay", "overlay-container"];
                    const isAd = adSigs.some(sig => id.includes(sig) || cls.includes(sig));
                    const isYouTubeRenderer = (id.includes("renderer") || cls.includes("renderer")) && !id.includes("ad") && !cls.includes("ad");

                    if (isAd && !isYouTubeRenderer) {
                        return { ok: false, error: "SENTINEL: ABORTED - target looks like an AD or OVERLAY", tag: tag, id: id, className: cls };
                    }

                    el.click();
                    return { ok: true, tag: tag, id: id, className: cls };
                    """,
                    viewport_css_x,
                    viewport_css_y,
                )
                if executed and not executed.get("ok"):
                    logger.warning(f"[UI-TARS] Click ABORTED by browser sentinel: {executed.get('error')}")
                    logger.warning(f"[UI-TARS]   Element info: tag={executed.get('tag')}, id={executed.get('id')}, class={executed.get('className')}")
            elif action == "type":
                if not text:
                    raise Exception("Type action requires context.text")
                executed = driver.execute_script(
                    """
                    const x = arguments[0], y = arguments[1], text = arguments[2];
                    const el = document.elementFromPoint(x, y);
                    if (!el) return { ok: false, error: "No element at point" };

                    // [SENTINEL] Element validation (same as click)
                    const id = (el.id || "").toLowerCase();
                    const cls = (el.className || "").toLowerCase();
                    const adSigs = ["ad", "sponsor", "promoted", "yt-ad", "renderer", "overlay"];
                    const isAd = adSigs.some(sig => id.includes(sig) || cls.includes(sig));
                    const isYouTubeRenderer = (id.includes("renderer") || cls.includes("renderer")) && !id.includes("ad") && !cls.includes("ad");
                    if (isAd && !isYouTubeRenderer) {
                        return { ok: false, error: "SENTINEL: ABORTED - target looks like an AD", tag: el.tagName, id: id };
                    }

                    function findEditable(start) {
                      if (!start) return null;
                      const tag = (start.tagName || "").toUpperCase();
                      if (tag === "TEXTAREA" || tag === "INPUT") return start;
                      if (start.isContentEditable) return start;
                      const byClosest = start.closest?.("textarea, input, [contenteditable='true']");
                      if (byClosest) return byClosest;
                      const byQuery = start.querySelector?.("textarea, input, [contenteditable='true']");
                      if (byQuery) return byQuery;
                      return null;
                    }

                    const target = findEditable(el);
                    if (!target) return { ok: false, error: "No editable element near point", tag: el.tagName };

                    target.focus?.();
                    target.click?.();

                    const tag = (target.tagName || "").toUpperCase();
                    if (tag === "TEXTAREA" || tag === "INPUT") {
                      target.value = text;
                      target.dispatchEvent(new Event("input", { bubbles: true }));
                      target.dispatchEvent(new Event("change", { bubbles: true }));
                      return { ok: true, kind: tag };
                    }

                    if (target.isContentEditable) {
                      target.textContent = text;
                      target.dispatchEvent(new Event("input", { bubbles: true }));
                      return { ok: true, kind: "contenteditable" };
                    }

                    return { ok: false, error: "Target not editable", tag: target.tagName };
                    """,
                    viewport_css_x,
                    viewport_css_y,
                    text,
                )
            elif action == "scroll":
                delta = 800 if (direction or "down").lower() in ("down", "right") else -800
                executed = driver.execute_script(
                    "window.scrollBy(0, arguments[0]); return { ok: true, delta: arguments[0] };",
                    delta,
                )
            elif action == "verify":
                executed = {"ok": True}
            elif action == "find":
                # find = verify = locate element without clicking
                # Used by find_by_description in action_router
                executed = {"ok": True, "found": True}
            elif action == "diagnose":
                # Diagnose mode: DOM action failed, vision helps find what went wrong
                # Returns diagnosis info without executing action
                original_error = context.get("error", "unknown")
                original_action = context.get("original_action", "unknown")

                # Build diagnostic response
                executed = {
                    "ok": True,
                    "diagnosis": thought or "Element located via vision",
                    "element_found": True,
                    "suggested_selector": f"xpath://*[contains(text(), '{description[:20]}')]",  # Placeholder
                    "coordinates": {"x": normalized_x, "y": normalized_y},
                    "action_executed": False,  # Diagnosis only, no click
                }
                logger.info(f"[UI-TARS] Diagnosis complete: element at ({normalized_x}, {normalized_y})")
            else:
                raise Exception(f"Unsupported action: {action}")

            duration_ms = int((time.time() - start_time) * 1000)

            # Estimate confidence based on whether model provided thought
            confidence = 0.8 if thought and len(thought) > 20 else 0.6

            execution_ok = isinstance(executed, dict) and executed.get("ok") is True
            proposal_only = action in {"verify", "find", "diagnose"}
            result = ActionResult(
                success=execution_ok,
                action=action,
                description=description,
                duration_ms=duration_ms,
                confidence=confidence if execution_ok else 0.0,
                error=None if execution_ok else (
                    str(executed.get("error") or "Browser did not confirm action execution")
                    if isinstance(executed, dict) else "Browser did not confirm action execution"),
                metadata={
                    "coordinates": {"x": normalized_x, "y": normalized_y, "box": (box_x, box_y)},
                    "viewport_css": {"x": viewport_css_x, "y": viewport_css_y},
                    "executed": executed,
                    "action_executed": execution_ok and not proposal_only,
                    "proposal_only": proposal_only,
                    "thought": thought,
                    "tier": "ui-tars",
                    "coordinate_profile": coordinate_profile,
                    "coordinate_grid_size": point["model_image_size"],
                    "model_image_size": resized_image_size,
                    "original_screenshot_size": original_screenshot_size,
                    "observed_viewport": {"width": vw, "height": vh} if coordinate_profile == "ui_tars_1_5_qwen25vl" else None,
                },
            )

            self._emit_event("action_complete" if execution_ok else "action_failed", result.to_dict())
            return result

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)

            result = ActionResult(
                success=False,
                action=action,
                description=description,
                duration_ms=duration_ms,
                error=str(e),
            )

            self._emit_event("action_failed", {
                "action": action,
                "error": str(e),
                "duration_ms": duration_ms,
            })

            logger.error(f"[UI-TARS] Action failed: {e}")
            return result

    async def click(self, description: str, **kwargs) -> ActionResult:
        """Click an element by description."""
        return await self.execute_action("click", description, **kwargs)

    async def type_text(self, description: str, text: str, **kwargs) -> ActionResult:
        """Type text into an element."""
        context = kwargs.pop("context", {})
        context["text"] = text
        return await self.execute_action("type", description, context=context, **kwargs)

    async def scroll(self, description: str, direction: str = "down", **kwargs) -> ActionResult:
        """Scroll to/in an element."""
        context = kwargs.pop("context", {})
        context["direction"] = direction
        return await self.execute_action("scroll", description, context=context, **kwargs)

    async def verify(self, description: str, **kwargs) -> ActionResult:
        """Verify an element exists/state."""
        return await self.execute_action("verify", description, **kwargs)

    async def observe_page_state(
        self,
        driver,
        context: Optional[Dict[str, Any]] = None,
        timeout: int = 60,
    ) -> Dict[str, Any]:
        """
        Layer 5 OODA: Observe page state using UI-TARS vision.

        Captures screenshot and uses UI-TARS to describe what's visible on the page.
        Used by heartbeat OODA loop to determine if activity pivot is needed.

        Args:
            driver: Selenium WebDriver instance
            context: Additional context (e.g., expected_page, current_activity)
            timeout: Max seconds for vision inference

        Returns:
            Dict with page state observations:
            {
                "success": bool,
                "page_type": str,  # "youtube_studio", "youtube_live", "youtube_comments", etc.
                "indicators": List[str],  # ["live_stream_active", "comments_visible", etc.]
                "confidence": float,
                "raw_output": str,
                "error": Optional[str]
            }
        """
        import base64
        import io
        import time as time_module
        from PIL import Image

        start_time = time_module.time()
        context = context or {}

        self._emit_event("observe_start", {"context": context})

        try:
            # Ensure connected
            if not self._connected:
                await self.connect()

            # 1. Capture screenshot
            screenshot_bytes = await asyncio.to_thread(driver.get_screenshot_as_png)

            # Resize for faster inference
            img = Image.open(io.BytesIO(screenshot_bytes))
            original_size = img.size
            if img.width > 1280:
                ratio = 1280 / img.width
                img = img.resize((1280, int(img.height * ratio)), Image.Resampling.LANCZOS)
                logger.debug(f"[UI-TARS-OBSERVE] Resized: {original_size} -> {img.size}")

            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            screenshot_bytes = img_buffer.getvalue()
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')

            # 2. Build observation prompt
            prompt = """You are observing a web browser page to determine its current state.

Analyze the screenshot and respond in this exact format:
Page: <page_type>
Indicators: <comma-separated list of what you observe>
Confidence: <0.0-1.0>

Page types (choose one):
- youtube_studio_comments: YouTube Studio comments page
- youtube_live_chat: YouTube live stream with chat visible
- youtube_video: YouTube video page (not live)
- youtube_home: YouTube homepage
- youtube_shorts: YouTube Shorts tab
- google_oops: Google/YouTube error page (OOPS, sign-in required)
- browser_error: Browser error (disconnected, crashed)
- other: None of the above

Indicators (list all that apply):
- live_stream_active: Live stream indicator visible
- comments_visible: Comment section visible
- chat_visible: Live chat panel visible
- no_comments: No comments to process
- logged_in: User appears logged in
- logged_out: Sign-in prompt visible
- loading: Page is loading
- error_message: Error message visible
- studio_sidebar: YouTube Studio sidebar visible

Example response:
Page: youtube_studio_comments
Indicators: comments_visible, logged_in, studio_sidebar
Confidence: 0.9"""

            # 3. Call LM Studio API
            import requests
            tars_api_url = os.getenv("TARS_API_URL", "http://127.0.0.1:1234").rstrip("/")
            if tars_api_url.endswith("/v1"):
                tars_api_url = tars_api_url[:-3]

            response = await asyncio.to_thread(
                requests.post,
                f"{tars_api_url}/v1/chat/completions",
                json={
                    "model": UI_TARS_MODEL,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/png;base64,{screenshot_base64}"}
                                }
                            ]
                        }
                    ],
                    "max_tokens": 200,
                    "temperature": 0.1,
                },
                timeout=timeout
            )

            if response.status_code != 200:
                raise Exception(f"LM Studio API error: {response.status_code}")

            # 4. Parse response
            response_data = response.json()
            model_output = response_data['choices'][0]['message']['content']

            # Parse structured output
            import re
            page_match = re.search(r'Page:\s*(\S+)', model_output)
            indicators_match = re.search(r'Indicators:\s*(.+?)(?=Confidence:|$)', model_output, re.DOTALL)
            confidence_match = re.search(r'Confidence:\s*([\d.]+)', model_output)

            page_type = page_match.group(1).strip() if page_match else "unknown"
            indicators_raw = indicators_match.group(1).strip() if indicators_match else ""
            indicators = [i.strip() for i in indicators_raw.split(',') if i.strip()]
            confidence = float(confidence_match.group(1)) if confidence_match else 0.5

            duration_ms = int((time_module.time() - start_time) * 1000)

            result = {
                "success": True,
                "page_type": page_type,
                "indicators": indicators,
                "confidence": confidence,
                "duration_ms": duration_ms,
                "raw_output": model_output[:200],
                "error": None
            }

            self._emit_event("observe_complete", result)
            logger.info(f"[UI-TARS-OBSERVE] Page: {page_type}, Indicators: {indicators}, Confidence: {confidence:.2f} ({duration_ms}ms)")

            return result

        except Exception as e:
            duration_ms = int((time_module.time() - start_time) * 1000)
            result = {
                "success": False,
                "page_type": "error",
                "indicators": [],
                "confidence": 0.0,
                "duration_ms": duration_ms,
                "raw_output": "",
                "error": str(e)
            }
            self._emit_event("observe_failed", {"error": str(e), "duration_ms": duration_ms})
            logger.warning(f"[UI-TARS-OBSERVE] Failed: {e}")
            return result

    def close(self) -> None:
        """Close UI-TARS connection."""
        self._emit_event("bridge_close", {"session_id": self._session_id})
        self._connected = False
        self._session_id = None
        logger.info("[UI-TARS] Bridge closed")


# Factory function
def create_ui_tars_bridge(
    ui_tars_path: str = None,
    browser_port: int = 9222,
    observers: List[Callable] = None,
) -> UITarsBridge:
    """
    Create UI-TARS bridge instance.
    
    Args:
        ui_tars_path: Path to UI-TARS installation
        browser_port: Chrome debugging port
        observers: Telemetry observers
        
    Returns:
        Configured UITarsBridge instance
    """
    return UITarsBridge(
        ui_tars_path=ui_tars_path,
        browser_port=browser_port,
        observers=observers,
    )


# Test function
async def _test_bridge():
    """Test UI-TARS bridge functionality."""
    bridge = UITarsBridge()
    
    # Test connection
    await bridge.connect()
    
    # Test screenshot
    screenshot = await bridge.capture_screenshot()
    print(f"Screenshot: {screenshot.path}")
    
    # Test action
    result = await bridge.click("blue Like button")
    print(f"Action result: {result.success}, confidence: {result.confidence}")
    
    bridge.close()


if __name__ == "__main__":
    asyncio.run(_test_bridge())
