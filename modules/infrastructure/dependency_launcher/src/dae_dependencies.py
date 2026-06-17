"""
DAE Dependency Launcher - Auto-start Chrome + Edge + LM Studio for YouTube DAE
========================================================================

WSP Compliance:
    - WSP 27: DAE Architecture (Phase -1: Dependency initialization)
    - WSP 80: Cube-Level Orchestration (Cross-module dependency management)

Usage:
    from modules.infrastructure.dependency_launcher.src.dae_dependencies import ensure_dependencies
    
    # Call before DAE starts
    await ensure_dependencies()

Dependencies:
    1. Chrome with remote debugging port 9222 (for Selenium/UI-TARS)
    2. Edge with remote debugging port 9223 (for FoundUps Studio inbox)
    3. LM Studio on port 1234 (for UI-TARS vision model)
"""

import asyncio
import logging
import os
import subprocess
import socket
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Configuration
CHROME_PATH = os.getenv("CHROME_PATH", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
CHROME_DEBUG_PORT = int(os.getenv("FOUNDUPS_CHROME_PORT", "9222"))
CHROME_PROFILE = Path(os.getenv(
    "CHROME_PROFILE_PATH",
    "O:/Foundups-Agent/modules/platform_integration/browser_profiles/youtube_move2japan/chrome"
))
# FIX (2025-12-30): Added NOT_ENGAGED filter to show only unprocessed comments
# Without this filter, already-liked/hearted comments still appear and cause 0-comment detection
STUDIO_FILTER = "%5B%7B%22isDisabled%22%3Afalse%2C%22isPinned%22%3Atrue%2C%22name%22%3A%22SORT_BY%22%2C%22value%22%3A%22SORT_BY_MOST_RELEVANT%22%7D%2C%7B%22name%22%3A%22ENGAGED_STATUS%22%2C%22value%22%3A%5B%22COMMENT_CATEGORY_NOT_ENGAGED%22%5D%7D%2C%7B%22name%22%3A%22PARENT_ENTITY_CONTENT_TYPE%22%2C%22value%22%3A%5B%22PARENT_ENTITY_CONTENT_TYPE_WATCH%22%2C%22PARENT_ENTITY_CONTENT_TYPE_SHORT%22%2C%22PARENT_ENTITY_CONTENT_TYPE_CREATOR_POST%22%5D%7D%5D"
YOUTUBE_STUDIO_URL = f"https://studio.youtube.com/channel/UC-LSSlOZwpGIRIYihaz8zCw/comments/inbox?filter={STUDIO_FILTER}"

EDGE_DEBUG_PORT = int(os.getenv("FOUNDUPS_EDGE_PORT", os.getenv("EDGE_DEBUG_PORT", "9223")))
EDGE_PROFILE = Path(os.getenv(
    "EDGE_PROFILE_PATH",
    "O:/Foundups-Agent/modules/platform_integration/browser_profiles/youtube_foundups/edge"
))
FOUNDUPS_CHANNEL_ID = os.getenv("FOUNDUPS_CHANNEL_ID", "UCSNTUXjAgpd4sgWYP0xoJgw")
FOUNDUPS_STUDIO_URL = f"https://studio.youtube.com/channel/{FOUNDUPS_CHANNEL_ID}/comments/inbox?filter={STUDIO_FILTER}"

LM_STUDIO_PORT = int(os.getenv("LM_STUDIO_PORT", "1234"))

# UI-TARS model configuration for vision-based automation
# The model should be pre-downloaded in LM Studio
UI_TARS_MODEL_ID = os.getenv("UI_TARS_MODEL_ID", "lmstudio-community/UI-TARS-1.5-7B-GGUF")
UI_TARS_MODEL_FILE = os.getenv("UI_TARS_MODEL_FILE", "UI-TARS-1.5-7B-Q4_K_M.gguf")

# Gemma model configuration for fast pattern matching (WSP 77 Phase 1)
GEMMA_MODEL_ID = os.getenv("GEMMA_MODEL_ID", "gemma-270m")
GEMMA_MODEL_FILE = os.getenv("GEMMA_MODEL_FILE", "gemma-3-270m-it-Q4_K_M.gguf")

# Qwen model configuration for intelligent reasoning (WSP 77 Phase 2)
QWEN_MODEL_ID = os.getenv("QWEN_MODEL_ID", "qwen3.5-4b")
QWEN_MODEL_FILE = os.getenv("QWEN_MODEL_FILE", "Qwen3.5-4B-Q4_K_M.gguf")


def resolve_lm_studio_path() -> Optional[str]:
    """
    Resolve LM Studio executable path.

    Prefers explicit `LM_STUDIO_PATH`, then checks common install locations (including E:\\LM_studio).
    """
    candidates = [
        os.getenv("LM_STUDIO_PATH"),
        r"E:\LM_studio\LM Studio\LM Studio.exe",
        str(Path(os.getenv("LOCALAPPDATA", "")) / "Programs" / "LM Studio" / "LM Studio.exe"),
        r"C:\Users\user\AppData\Local\Programs\LM Studio\LM Studio.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


def resolve_edge_path() -> Optional[str]:
    """
    Resolve Microsoft Edge executable path.

    Prefers explicit `EDGE_PATH`, then checks common install locations.
    """
    candidates = [
        os.getenv("EDGE_PATH"),
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


# OBS Studio configuration for antifaFM streaming
OBS_WEBSOCKET_PORT = int(os.getenv("OBS_WEBSOCKET_PORT", "4455"))


def resolve_obs_path() -> Optional[str]:
    """
    Resolve OBS Studio shortcut or executable path.

    Uses Start Menu shortcut (has correct working directory) or falls back to exe.
    """
    # Start Menu shortcut is preferred - has correct working directory
    shortcut = r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\OBS Studio\OBS Studio (64bit).lnk"
    if Path(shortcut).exists():
        return shortcut

    # Fallback to direct exe (may have locale issues)
    candidates = [
        os.getenv("OBS_PATH"),
        r"C:\Program Files\obs-studio\bin\64bit\obs64.exe",
        r"C:\Program Files (x86)\obs-studio\bin\64bit\obs64.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


def is_obs_running() -> bool:
    """Check if OBS WebSocket is running."""
    return is_port_open(OBS_WEBSOCKET_PORT)


def launch_obs() -> Tuple[bool, str]:
    """
    Launch OBS Studio for antifaFM streaming.

    Returns:
        Tuple of (success, message)
    """
    if is_obs_running():
        logger.info(f"[DEPS] OBS already running (WebSocket port {OBS_WEBSOCKET_PORT})")
        return True, "OBS already running"

    obs_path = resolve_obs_path()
    if not obs_path:
        logger.warning("[DEPS] OBS executable not found (set OBS_PATH in .env)")
        logger.warning("[DEPS] Please start OBS manually")
        return False, "OBS executable not found"

    try:
        logger.info(f"[DEPS] Launching OBS: {obs_path}")

        # Use os.startfile to launch OBS the Windows way (respects working directory)
        # This is how Start Menu launches it - avoids locale/en-US.ini errors
        os.startfile(obs_path)

        # Wait for WebSocket to be ready
        logger.info("[DEPS] Waiting for OBS WebSocket (this may take 10-30 seconds)...")
        for i in range(60):  # 1 minute timeout
            time.sleep(1)
            if is_obs_running():
                logger.info(f"[DEPS] [OK] OBS WebSocket ready on port {OBS_WEBSOCKET_PORT}")
                return True, f"OBS started on port {OBS_WEBSOCKET_PORT}"
            if i % 10 == 0 and i > 0:
                logger.info(f"[DEPS] Still waiting for OBS... ({i}s)")

        logger.warning("[DEPS] OBS launched but WebSocket not responding")
        logger.warning("[DEPS] Enable WebSocket: OBS -> Tools -> WebSocket Server Settings")
        return False, "OBS launched but WebSocket not responding"

    except Exception as e:
        logger.error(f"[DEPS] Failed to launch OBS: {e}")
        return False, str(e)


def is_port_open(port: int, host: str = "127.0.0.1", timeout: float = 1.0) -> bool:
    """Check if a port is open (service running)."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False


def is_devtools_responding(port: int, timeout: float = 2.0) -> bool:
    """Check if Chrome/Edge DevTools protocol is actually responding.

    Just checking port open isn't enough - the browser might be hung or
    another process might be using the port. This makes HTTP requests
    to both /json/version AND /json (page list) to verify Selenium can connect.

    The "unable to discover open pages" error happens when /json/version works
    but /json fails - so we must check both.
    """
    try:
        import urllib.request
        import json as json_module

        # Step 1: Check /json/version (browser info)
        version_url = f"http://127.0.0.1:{port}/json/version"
        req = urllib.request.Request(version_url)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = response.read().decode('utf-8')
            if 'Browser' not in data and 'webSocketDebuggerUrl' not in data:
                logger.debug(f"[DEPS] DevTools version check failed - not Chrome/Edge")
                return False

        # Step 2: Check /json (page list) - this is what Selenium uses
        pages_url = f"http://127.0.0.1:{port}/json"
        req = urllib.request.Request(pages_url)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            pages_data = response.read().decode('utf-8')
            pages = json_module.loads(pages_data)
            if not isinstance(pages, list):
                logger.debug(f"[DEPS] DevTools pages check failed - invalid response")
                return False
            # Must have at least one page for Selenium to connect
            if len(pages) == 0:
                logger.debug(f"[DEPS] DevTools has 0 pages - browser may be starting")
                return False
            logger.debug(f"[DEPS] DevTools OK: {len(pages)} page(s) available")
            return True

    except Exception as e:
        logger.debug(f"[DEPS] DevTools check failed on port {port}: {e}")
        return False


def open_devtools_page(port: int, url: str = "about:blank", timeout: float = 3.0) -> bool:
    """Open a new normal page/tab via the DevTools HTTP endpoint - NON-DESTRUCTIVE.

    Used to RECOVER from the "unable to discover open pages" condition: DevTools
    /json/version works but /json (page list) is empty, so Selenium cannot attach.
    Instead of killing the operator's prepared browser, we ask DevTools to open a
    normal page target so Selenium has something to attach to.

    Uses the same urllib HTTP pattern as is_devtools_responding(). Tries
    HTTP PUT /json/new?<url> first (modern Chrome/Edge), falling back to GET
    /json/new?<url> for builds that still accept the legacy verb.

    Returns:
        True if DevTools reported a new target was created, False otherwise.
        Never raises, never kills any process.
    """
    try:
        import urllib.request
        import urllib.parse
        import json as json_module

        # /json/new?<url> ; url-quote so about:blank etc. survive transport
        new_url = f"http://127.0.0.1:{port}/json/new?{urllib.parse.quote(url, safe='')}"

        def _try(method: str) -> bool:
            req = urllib.request.Request(new_url, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = response.read().decode("utf-8")
            try:
                data = json_module.loads(body)
            except Exception:
                # Some builds return a bare page object string; treat any 2xx
                # body that mentions an id/target as success.
                return bool(body and ("id" in body or "targetId" in body))
            # A created target carries an id (and usually a webSocketDebuggerUrl)
            return isinstance(data, dict) and bool(
                data.get("id") or data.get("targetId") or data.get("webSocketDebuggerUrl")
            )

        # Modern Chrome (>=111) requires PUT for /json/new; older accepts GET.
        try:
            if _try("PUT"):
                logger.info(f"[DEPS] Opened new DevTools page on port {port} via PUT /json/new")
                return True
        except Exception as put_err:
            logger.debug(f"[DEPS] PUT /json/new failed on port {port}: {put_err}; trying GET")

        if _try("GET"):
            logger.info(f"[DEPS] Opened new DevTools page on port {port} via GET /json/new")
            return True

        logger.debug(f"[DEPS] /json/new did not report a new target on port {port}")
        return False

    except Exception as e:
        logger.debug(f"[DEPS] open_devtools_page failed on port {port}: {e}")
        return False


def is_chrome_running() -> bool:
    """Check if Chrome with debug port is running AND responding."""
    if not is_port_open(CHROME_DEBUG_PORT):
        return False
    # Verify DevTools is actually responding
    return is_devtools_responding(CHROME_DEBUG_PORT)

def is_edge_running() -> bool:
    """Check if Edge with debug port is running AND responding."""
    if not is_port_open(EDGE_DEBUG_PORT):
        return False
    # Verify DevTools is actually responding
    return is_devtools_responding(EDGE_DEBUG_PORT)


def is_lm_studio_running() -> bool:
    """Check if LM Studio API is running."""
    return is_port_open(LM_STUDIO_PORT)


def launch_chrome() -> Tuple[bool, str]:
    """
    Launch Chrome with remote debugging port and YouTube profile.
    
    Returns:
        Tuple of (success, message)
    """
    if is_chrome_running():
        logger.info(f"[DEPS] Chrome already running on port {CHROME_DEBUG_PORT} (DevTools responding)")
        return True, "Chrome already running"
    
    if not Path(CHROME_PATH).exists():
        logger.error(f"[DEPS] Chrome not found at: {CHROME_PATH}")
        return False, f"Chrome not found at {CHROME_PATH}"
    
    try:
        cmd = [
            CHROME_PATH,
            f"--remote-debugging-port={CHROME_DEBUG_PORT}",
            f"--user-data-dir={CHROME_PROFILE}",
            # CRITICAL: Anti-backgrounding flags (2025-12-30)
            # Prevents JavaScript/DOM throttling when window not focused
            # Without these, automation stops or becomes erratic when browser is in background
            "--disable-backgrounding-occluded-windows",  # Prevents throttling when behind other windows
            "--disable-renderer-backgrounding",           # Prevents renderer process backgrounding
            "--disable-background-timer-throttling",      # Prevents timer throttling in background tabs
            # FIX (2026-01-23): Prevent multi-tab issue from session restore
            "--no-restore-session-state",                 # Prevents restoring previous tabs
            YOUTUBE_STUDIO_URL
        ]

        logger.info(f"[DEPS] Launching Chrome with debug port {CHROME_DEBUG_PORT} (anti-backgrounding enabled)...")
        
        # Launch Chrome as detached process (won't block)
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        )
        
        # Wait for Chrome to be ready
        for i in range(30):  # 30 seconds timeout
            time.sleep(1)
            if is_chrome_running():
                logger.info(f"[DEPS] [OK] Chrome started on port {CHROME_DEBUG_PORT}")
                return True, f"Chrome started on port {CHROME_DEBUG_PORT}"
        
        logger.warning("[DEPS] Chrome launched but port not responding")
        return False, "Chrome launched but debug port not responding"
        
    except Exception as e:
        logger.error(f"[DEPS] Failed to launch Chrome: {e}")
        return False, str(e)


def launch_edge() -> Tuple[bool, str]:
    """
    Launch Edge with remote debugging port and FoundUps profile.

    Returns:
        Tuple of (success, message)
    """
    if is_edge_running():
        logger.info(f"[DEPS] Edge already running on port {EDGE_DEBUG_PORT} (DevTools responding)")
        return True, "Edge already running"

    edge_path = resolve_edge_path()
    if not edge_path:
        logger.error("[DEPS] Edge executable not found (set EDGE_PATH in .env)")
        return False, "Edge executable not found"

    try:
        EDGE_PROFILE.mkdir(parents=True, exist_ok=True)

        cmd = [
            edge_path,
            f"--remote-debugging-port={EDGE_DEBUG_PORT}",
            f"--user-data-dir={EDGE_PROFILE}",
            # CRITICAL: Anti-backgrounding flags (2025-12-30)
            # Prevents JavaScript/DOM throttling when window not focused
            # Without these, automation stops or becomes erratic when browser is in background
            "--disable-backgrounding-occluded-windows",  # Prevents throttling when behind other windows
            "--disable-renderer-backgrounding",           # Prevents renderer process backgrounding
            "--disable-background-timer-throttling",      # Prevents timer throttling in background tabs
            # FIX (2026-01-23): Prevent 3-tab issue from session restore
            "--no-restore-session-state",                 # Prevents restoring previous tabs
            FOUNDUPS_STUDIO_URL
        ]

        logger.info(f"[DEPS] Launching Edge with debug port {EDGE_DEBUG_PORT} (anti-backgrounding enabled)...")

        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        )

        for _ in range(30):
            time.sleep(1)
            if is_edge_running():
                logger.info(f"[DEPS] [OK] Edge started on port {EDGE_DEBUG_PORT}")
                return True, f"Edge started on port {EDGE_DEBUG_PORT}"

        logger.warning("[DEPS] Edge launched but port not responding")
        return False, "Edge launched but debug port not responding"

    except Exception as e:
        logger.error(f"[DEPS] Failed to launch Edge: {e}")
        return False, str(e)


def launch_lm_studio(load_model: bool = True) -> Tuple[bool, str]:
    """
    Launch LM Studio and optionally load all AI models.

    Models loaded (WSP 77 Agent Coordination):
    - UI-TARS: Vision-based automation
    - Gemma: Fast pattern matching (Phase 1)
    - Qwen: Intelligent reasoning (Phase 2)

    Args:
        load_model: Whether to auto-load models via API after LM Studio starts

    Returns:
        Tuple of (success, message)
    """
    if is_lm_studio_running():
        logger.info(f"[DEPS] LM Studio already running on port {LM_STUDIO_PORT}")
        # Even if running, try to load all models if requested
        if load_model:
            load_all_models()
        return True, "LM Studio already running"

    lm_studio_path = resolve_lm_studio_path()
    if not lm_studio_path:
        logger.warning("[DEPS] LM Studio executable not found (set LM_STUDIO_PATH in .env)")
        logger.warning("[DEPS] Please start LM Studio manually and load UI-TARS model")
        return False, "LM Studio executable not found"

    try:
        logger.info(f"[DEPS] Launching LM Studio: {lm_studio_path}")

        # Launch LM Studio as detached process
        subprocess.Popen(
            [lm_studio_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        )

        # Wait for API to be ready (LM Studio takes longer to start)
        logger.info("[DEPS] Waiting for LM Studio API (this may take 30-60 seconds)...")
        for i in range(120):  # 2 minute timeout
            time.sleep(1)
            if is_lm_studio_running():
                logger.info(f"[DEPS] [OK] LM Studio API ready on port {LM_STUDIO_PORT}")

                # Auto-load all AI models (UI-TARS, Gemma, Qwen)
                if load_model:
                    time.sleep(2)  # Brief pause for API to fully initialize
                    load_all_models()

                return True, f"LM Studio started on port {LM_STUDIO_PORT}"
            if i % 10 == 0 and i > 0:
                logger.info(f"[DEPS] Still waiting for LM Studio... ({i}s)")

        logger.warning("[DEPS] LM Studio launched but API not responding")
        logger.warning("[DEPS] Please ensure models are loaded in LM Studio (UI-TARS, Gemma, Qwen)")
        return False, "LM Studio launched but API not responding - load models manually"

    except Exception as e:
        logger.error(f"[DEPS] Failed to launch LM Studio: {e}")
        return False, str(e)


def _load_ui_tars_model() -> bool:
    """
    Load UI-TARS model in LM Studio via API.

    Uses the /v1/models/load endpoint to load the model.

    Returns:
        True if model loaded successfully
    """
    import requests

    base_url = f"http://127.0.0.1:{LM_STUDIO_PORT}"

    try:
        # First check what models are available
        resp = requests.get(f"{base_url}/v1/models", timeout=5)
        if resp.status_code == 200:
            models_data = resp.json()
            models = models_data.get("data", [])

            # Check if UI-TARS is already loaded
            for m in models:
                model_id = m.get("id", "")
                if "ui-tars" in model_id.lower() or "uitars" in model_id.lower():
                    logger.info(f"[DEPS] [OK] UI-TARS model already loaded: {model_id}")
                    return True

            logger.info(f"[DEPS] Available models: {[m.get('id') for m in models]}")

        # Try to load UI-TARS model
        # LM Studio uses POST /v1/models/load with model identifier
        load_payload = {
            "model": UI_TARS_MODEL_ID,
            "file": UI_TARS_MODEL_FILE,
        }

        logger.info(f"[DEPS] Loading UI-TARS model: {UI_TARS_MODEL_ID}")

        # Note: LM Studio 0.2.x uses /v1/models/load, newer versions may differ
        # Try multiple endpoints that LM Studio has used historically
        for endpoint in ["/v1/models/load", "/api/v0/models/load", "/api/models/load"]:
            try:
                resp = requests.post(f"{base_url}{endpoint}", json=load_payload, timeout=30)
                if resp.status_code in (200, 201, 202):
                    logger.info(f"[DEPS] [OK] UI-TARS model load initiated via {endpoint}")
                    return True
            except Exception:
                continue

        # If API loading fails, log instructions
        logger.warning("[DEPS] Could not auto-load UI-TARS model via API")
        logger.warning(f"[DEPS] Please manually load: {UI_TARS_MODEL_ID} / {UI_TARS_MODEL_FILE}")
        logger.warning("[DEPS] Or set LM Studio to auto-load this model on startup")
        return False

    except Exception as e:
        logger.warning(f"[DEPS] UI-TARS model load failed: {e}")
        return False


def _load_gemma_model() -> bool:
    """
    Load Gemma model in LM Studio via API for fast pattern matching.

    WSP 77 Phase 1: Gemma handles binary classification (50-100ms).

    Returns:
        True if model loaded successfully
    """
    import requests

    base_url = f"http://127.0.0.1:{LM_STUDIO_PORT}"

    try:
        # Check what models are available
        resp = requests.get(f"{base_url}/v1/models", timeout=5)
        if resp.status_code == 200:
            models_data = resp.json()
            models = models_data.get("data", [])

            # Check if Gemma is already loaded
            for m in models:
                model_id = m.get("id", "")
                if "gemma" in model_id.lower():
                    logger.info(f"[DEPS] [OK] Gemma model already loaded: {model_id}")
                    return True

        # Try to load Gemma model
        load_payload = {
            "model": GEMMA_MODEL_ID,
            "file": GEMMA_MODEL_FILE,
        }

        logger.info(f"[DEPS] Loading Gemma model: {GEMMA_MODEL_ID}")

        for endpoint in ["/v1/models/load", "/api/v0/models/load", "/api/models/load"]:
            try:
                resp = requests.post(f"{base_url}{endpoint}", json=load_payload, timeout=30)
                if resp.status_code in (200, 201, 202):
                    logger.info(f"[DEPS] [OK] Gemma model load initiated via {endpoint}")
                    return True
            except Exception:
                continue

        logger.warning("[DEPS] Could not auto-load Gemma model via API")
        logger.warning(f"[DEPS] Please manually load: {GEMMA_MODEL_ID} / {GEMMA_MODEL_FILE}")
        return False

    except Exception as e:
        logger.warning(f"[DEPS] Gemma model load failed: {e}")
        return False


def _load_qwen_model() -> bool:
    """
    Load Qwen model in LM Studio via API for intelligent reasoning.

    WSP 77 Phase 2: Qwen handles strategic reasoning (200-500ms).

    Returns:
        True if model loaded successfully
    """
    import requests

    base_url = f"http://127.0.0.1:{LM_STUDIO_PORT}"

    try:
        # Check what models are available
        resp = requests.get(f"{base_url}/v1/models", timeout=5)
        if resp.status_code == 200:
            models_data = resp.json()
            models = models_data.get("data", [])

            # Check if Qwen is already loaded
            for m in models:
                model_id = m.get("id", "")
                if "qwen" in model_id.lower():
                    logger.info(f"[DEPS] [OK] Qwen model already loaded: {model_id}")
                    return True

        # Try to load Qwen model
        load_payload = {
            "model": QWEN_MODEL_ID,
            "file": QWEN_MODEL_FILE,
        }

        logger.info(f"[DEPS] Loading Qwen model: {QWEN_MODEL_ID}")

        for endpoint in ["/v1/models/load", "/api/v0/models/load", "/api/models/load"]:
            try:
                resp = requests.post(f"{base_url}{endpoint}", json=load_payload, timeout=30)
                if resp.status_code in (200, 201, 202):
                    logger.info(f"[DEPS] [OK] Qwen model load initiated via {endpoint}")
                    return True
            except Exception:
                continue

        logger.warning("[DEPS] Could not auto-load Qwen model via API")
        logger.warning(f"[DEPS] Please manually load: {QWEN_MODEL_ID} / {QWEN_MODEL_FILE}")
        return False

    except Exception as e:
        logger.warning(f"[DEPS] Qwen model load failed: {e}")
        return False


def load_all_models() -> Dict[str, bool]:
    """
    Load all required models in LM Studio.

    Models:
    - UI-TARS: Vision-based automation
    - Gemma: Fast pattern matching (WSP 77 Phase 1)
    - Qwen: Intelligent reasoning (WSP 77 Phase 2)

    Returns:
        Dict with load status for each model
    """
    results = {}

    logger.info("[DEPS] Loading all AI models in LM Studio...")

    results['ui_tars'] = _load_ui_tars_model()
    results['gemma'] = _load_gemma_model()
    results['qwen'] = _load_qwen_model()

    loaded = sum(1 for v in results.values() if v)
    logger.info(f"[DEPS] Model loading complete: {loaded}/3 loaded")

    return results


async def ensure_dependencies(require_lm_studio: bool = True) -> Dict[str, bool]:
    """
    Ensure all dependencies are running before DAE starts.
    
    Args:
        require_lm_studio: Whether LM Studio is required (for UI-TARS vision)
    
    Returns:
        Dict with status of each dependency
    """
    results = {}
    
    logger.info("="*60)
    logger.info("[DEPS] CHECKING YOUTUBE DAE DEPENDENCIES")
    logger.info("="*60)
    
    # 1. Chrome with debug port
    chrome_ok, chrome_msg = launch_chrome()
    results['chrome'] = chrome_ok
    if not chrome_ok:
        logger.error(f"[DEPS] [ERROR] Chrome: {chrome_msg}")

    # 2. Edge with debug port (optional but recommended for FoundUps)
    edge_auto = os.getenv("YT_EDGE_AUTO_LAUNCH", "true").strip().lower() in ("1", "true", "yes", "y", "on")
    if edge_auto:
        edge_ok, edge_msg = launch_edge()
        results['edge'] = edge_ok
        if not edge_ok:
            logger.warning(f"[DEPS] [WARN] Edge: {edge_msg}")
    else:
        results['edge'] = is_edge_running()
        if results['edge']:
            logger.info("[DEPS] Edge detected (auto-launch disabled)")
    
    # 3. LM Studio for UI-TARS (optional but recommended)
    if require_lm_studio:
        lm_ok, lm_msg = launch_lm_studio()
        results['lm_studio'] = lm_ok
        if not lm_ok:
            logger.warning(f"[DEPS] [WARN] LM Studio: {lm_msg}")
            logger.warning("[DEPS] Comment engagement will use DOM-only mode (no vision verification)")
    else:
        results['lm_studio'] = is_lm_studio_running()
        if results['lm_studio']:
            logger.info("[DEPS] LM Studio detected (optional)")
    
    # Summary
    logger.info("="*60)
    logger.info("[DEPS] DEPENDENCY STATUS:")
    logger.info(f"  Chrome (port {CHROME_DEBUG_PORT}): {'READY' if results['chrome'] else 'NOT READY'}")
    logger.info(f"  Edge (port {EDGE_DEBUG_PORT}): {'READY' if results.get('edge') else 'NOT READY'}")
    logger.info(f"  LM Studio (port {LM_STUDIO_PORT}): {'READY' if results.get('lm_studio') else 'NOT RUNNING'}")
    logger.info("="*60)
    
    return results


def get_dependency_status() -> Dict[str, bool]:
    """Get current status of dependencies without launching."""
    return {
        'chrome': is_chrome_running(),
        'edge': is_edge_running(),
        'lm_studio': is_lm_studio_running(),
        'obs': is_obs_running()
    }


def connect_chrome_with_retry(
    max_retries: int = 3,
    retry_delay: float = 2.0,
    relaunch_on_fail: bool = True,
) -> Optional[any]:
    """
    Connect to Chrome with retry logic and DevTools verification.

    Handles timing races and stale browser states.

    NON-DESTRUCTIVE recovery (Phase 1): when DevTools is UP but exposes no
    discoverable page target (Selenium raises "unable to discover open pages"),
    we DO NOT taskkill the operator's prepared Chrome. Instead we open a normal
    tab via the DevTools HTTP endpoint (open_devtools_page) and retry the attach.
    If a tab cannot be opened, we log a clear actionable error and return None -
    NEVER killing the session. (See BROWSER_ATTACH_RECOVERY_NO_KILL_PHASE1.)

    NOTE (BROWSER_ATTACH_RECOVERY_DEVTOOLS_DOWN_PHASE2): the genuinely-DevTools-
    DOWN path (is_devtools_responding False twice) still taskkills+relaunches as
    a follow-up; that is out of scope for Phase 1 (no-page recovery).

    Args:
        max_retries: Maximum connection attempts
        retry_delay: Seconds between retries
        relaunch_on_fail: If True, attempt to relaunch Chrome on persistent failure
            (DevTools-DOWN path only; the no-page path never relaunches/kills)

    Returns:
        Selenium WebDriver or None if connection failed
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    port = CHROME_DEBUG_PORT
    devtools_failures = 0

    for attempt in range(1, max_retries + 1):
        # Step 1: Verify DevTools is responding (checks /json/version AND /json)
        if not is_devtools_responding(port):
            devtools_failures += 1
            logger.warning(f"[DEPS] Chrome DevTools not responding (attempt {attempt}/{max_retries})")

            # If DevTools failed twice, Chrome is likely DOWN (port not even
            # answering /json/version) - kill it. This is the DevTools-DOWN path,
            # distinct from the no-page path below. NOTE: still destructive;
            # tracked as BROWSER_ATTACH_RECOVERY_DEVTOOLS_DOWN_PHASE2.
            if devtools_failures >= 2 and relaunch_on_fail:
                logger.warning("[DEPS] DevTools DOWN twice (not just no-page) - "
                               "killing stale Chrome [PHASE2: make non-destructive]...")
                try:
                    subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"],
                                   capture_output=True, timeout=10)
                    time.sleep(2)
                except Exception:
                    pass
                logger.info("[DEPS] Relaunching Chrome...")
                launch_chrome()
                time.sleep(5)
                devtools_failures = 0  # Reset counter after relaunch
                continue

            if attempt < max_retries:
                time.sleep(retry_delay)
                continue
            elif relaunch_on_fail:
                logger.info("[DEPS] Attempting Chrome relaunch...")
                launch_chrome()
                time.sleep(3)
                if not is_devtools_responding(port):
                    logger.error("[DEPS] Chrome relaunch failed - DevTools not responding")
                    return None

        # Step 2: Attempt Selenium connection
        try:
            opts = Options()
            opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
            driver = webdriver.Chrome(options=opts)

            # Step 3: Verify connection is alive
            _ = driver.current_url
            logger.info(f"[DEPS] Chrome connected successfully (attempt {attempt})")
            return driver

        except Exception as e:
            error_str = str(e)
            logger.warning(f"[DEPS] Chrome connection failed (attempt {attempt}/{max_retries}): {e}")

            # "unable to discover open pages" = DevTools is UP but exposes no
            # page target. RECOVER NON-DESTRUCTIVELY: open a normal tab via the
            # DevTools HTTP endpoint, then retry the attach. NEVER taskkill the
            # operator's prepared Chrome here (NO_KILL contract, Phase 1).
            if "unable to discover open pages" in error_str:
                logger.info("[DEPS] Chrome up but no discoverable page - "
                            "opening a tab via DevTools (NO taskkill)...")
                if open_devtools_page(port):
                    # Re-check the page list, then retry the attach on next loop.
                    if is_devtools_responding(port):
                        logger.info("[DEPS] DevTools page now discoverable - retrying attach")
                    else:
                        logger.warning("[DEPS] Opened a tab but page list still not ready - "
                                       "retrying attach anyway")
                    if attempt < max_retries:
                        time.sleep(retry_delay)
                        continue
                    # Last attempt: try one immediate attach after opening the tab.
                    try:
                        opts = Options()
                        opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
                        driver = webdriver.Chrome(options=opts)
                        _ = driver.current_url
                        logger.info("[DEPS] Chrome connected after opening a recovery tab")
                        return driver
                    except Exception as e2:
                        logger.error("[DEPS] Chrome attach still failed after opening a tab: "
                                     f"{e2}. Open a normal tab in the debug Chrome (port "
                                     f"{port}), or relaunch with --remote-allow-origins. NO taskkill performed.")
                        return None
                # Opening a tab was not possible - clear actionable error, NO kill.
                logger.error(f"[DEPS] Chrome {port} up but no discoverable page and DevTools "
                             "/json/new could not open one. Open a normal tab in the debug "
                             "Chrome, or relaunch it with --remote-allow-origins. NO taskkill performed.")
                return None

            if attempt < max_retries:
                time.sleep(retry_delay)
            elif relaunch_on_fail and attempt == max_retries:
                logger.info("[DEPS] Final attempt - relaunching Chrome...")
                try:
                    subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"],
                                   capture_output=True, timeout=10)
                    time.sleep(2)
                except Exception:
                    pass
                launch_chrome()
                time.sleep(5)

                # One more try after relaunch
                try:
                    opts = Options()
                    opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
                    driver = webdriver.Chrome(options=opts)
                    _ = driver.current_url
                    logger.info("[DEPS] Chrome connected after relaunch")
                    return driver
                except Exception as e2:
                    logger.error(f"[DEPS] Chrome connection failed after relaunch: {e2}")

    return None


def connect_edge_with_retry(
    max_retries: int = 3,
    retry_delay: float = 2.0,
    relaunch_on_fail: bool = True,
) -> Optional[any]:
    """
    Connect to Edge with retry logic and DevTools verification.

    Handles timing races and stale browser states.

    NON-DESTRUCTIVE recovery (Phase 1): when DevTools is UP but exposes no
    discoverable page target ("unable to discover open pages"), we DO NOT
    taskkill the operator's prepared Edge. Instead we open a normal tab via the
    DevTools HTTP endpoint (open_devtools_page) and retry the attach; if a tab
    cannot be opened we log a clear actionable error and return None - NEVER
    killing the session. (See BROWSER_ATTACH_RECOVERY_NO_KILL_PHASE1.)

    NOTE (BROWSER_ATTACH_RECOVERY_DEVTOOLS_DOWN_PHASE2): the genuinely-DevTools-
    DOWN path still taskkills+relaunches as a follow-up (out of scope for Phase 1).

    Args:
        max_retries: Maximum connection attempts
        retry_delay: Seconds between retries
        relaunch_on_fail: If True, attempt to relaunch Edge on persistent failure
            (DevTools-DOWN path only; the no-page path never relaunches/kills)

    Returns:
        Selenium WebDriver or None if connection failed
    """
    from selenium import webdriver
    from selenium.webdriver.edge.options import Options as EdgeOptions

    port = EDGE_DEBUG_PORT
    devtools_failures = 0

    for attempt in range(1, max_retries + 1):
        # Step 1: Verify DevTools is responding (checks /json/version AND /json)
        if not is_devtools_responding(port):
            devtools_failures += 1
            logger.warning(f"[DEPS] Edge DevTools not responding (attempt {attempt}/{max_retries})")

            # If DevTools failed twice, Edge is likely DOWN (port not even
            # answering /json/version) - kill it. Distinct from the no-page path
            # below. NOTE: still destructive; tracked as
            # BROWSER_ATTACH_RECOVERY_DEVTOOLS_DOWN_PHASE2.
            if devtools_failures >= 2 and relaunch_on_fail:
                logger.warning("[DEPS] DevTools DOWN twice (not just no-page) - "
                               "killing stale Edge [PHASE2: make non-destructive]...")
                try:
                    subprocess.run(["taskkill", "/F", "/IM", "msedge.exe"],
                                   capture_output=True, timeout=10)
                    time.sleep(2)
                except Exception:
                    pass
                logger.info("[DEPS] Relaunching Edge...")
                launch_edge()
                time.sleep(5)
                devtools_failures = 0  # Reset counter after relaunch
                continue

            if attempt < max_retries:
                time.sleep(retry_delay)
                continue
            elif relaunch_on_fail:
                logger.info("[DEPS] Attempting Edge relaunch...")
                launch_edge()
                time.sleep(3)
                if not is_devtools_responding(port):
                    logger.error("[DEPS] Edge relaunch failed - DevTools not responding")
                    return None

        # Step 2: Attempt Selenium connection
        try:
            opts = EdgeOptions()
            opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
            driver = webdriver.Edge(options=opts)

            # Step 3: Verify connection is alive
            _ = driver.current_url
            logger.info(f"[DEPS] Edge connected successfully (attempt {attempt})")
            return driver

        except Exception as e:
            error_str = str(e)
            logger.warning(f"[DEPS] Edge connection failed (attempt {attempt}/{max_retries}): {e}")

            # "unable to discover open pages" = DevTools is UP but exposes no
            # page target. RECOVER NON-DESTRUCTIVELY: open a normal tab via the
            # DevTools HTTP endpoint, then retry the attach. NEVER taskkill the
            # operator's prepared Edge here (NO_KILL contract, Phase 1).
            if "unable to discover open pages" in error_str:
                logger.info("[DEPS] Edge up but no discoverable page - "
                            "opening a tab via DevTools (NO taskkill)...")
                if open_devtools_page(port):
                    if is_devtools_responding(port):
                        logger.info("[DEPS] DevTools page now discoverable - retrying attach")
                    else:
                        logger.warning("[DEPS] Opened a tab but page list still not ready - "
                                       "retrying attach anyway")
                    if attempt < max_retries:
                        time.sleep(retry_delay)
                        continue
                    try:
                        opts = EdgeOptions()
                        opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
                        driver = webdriver.Edge(options=opts)
                        _ = driver.current_url
                        logger.info("[DEPS] Edge connected after opening a recovery tab")
                        return driver
                    except Exception as e2:
                        logger.error("[DEPS] Edge attach still failed after opening a tab: "
                                     f"{e2}. Open a normal tab in the debug Edge (port "
                                     f"{port}), or relaunch with --remote-allow-origins. NO taskkill performed.")
                        return None
                # Opening a tab was not possible - clear actionable error, NO kill.
                logger.error(f"[DEPS] Edge {port} up but no discoverable page and DevTools "
                             "/json/new could not open one. Open a normal tab in the debug "
                             "Edge, or relaunch it with --remote-allow-origins. NO taskkill performed.")
                return None

            if attempt < max_retries:
                time.sleep(retry_delay)
            elif relaunch_on_fail and attempt == max_retries:
                logger.info("[DEPS] Final attempt - relaunching Edge...")
                try:
                    subprocess.run(["taskkill", "/F", "/IM", "msedge.exe"],
                                   capture_output=True, timeout=10)
                    time.sleep(2)
                except Exception:
                    pass
                launch_edge()
                time.sleep(5)

                # One more try after relaunch
                try:
                    opts = EdgeOptions()
                    opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
                    driver = webdriver.Edge(options=opts)
                    _ = driver.current_url
                    logger.info("[DEPS] Edge connected after relaunch")
                    return driver
                except Exception as e2:
                    logger.error(f"[DEPS] Edge connection failed after relaunch: {e2}")

    return None


# Quick test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("\n[INFO] Checking dependency status...")
    status = get_dependency_status()
    print(f"  Chrome (9222): {'READY' if status['chrome'] else 'NOT READY'}")
    print(f"  Edge (9223): {'READY' if status['edge'] else 'NOT READY'}")
    print(f"  LM Studio (1234): {'READY' if status['lm_studio'] else 'NOT READY'}")
    print(f"  OBS (4455): {'READY' if status['obs'] else 'NOT READY'}")

    if not all(status.values()):
        print("\n[INFO] Launching missing dependencies...")
        asyncio.run(ensure_dependencies())










