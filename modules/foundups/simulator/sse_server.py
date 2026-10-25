#!/usr/bin/env python
"""SSE Server for FoundUps Cube Events.

Streams FAMDaemon events to the web frontend via Server-Sent Events.
Designed for deployment on Cloud Run alongside the chat endpoint.

Usage:
    python sse_server.py                    # Run on default port 8080
    python sse_server.py --port 9000        # Run on custom port
    python sse_server.py --simulate         # Run with simulated events (no FAMDaemon)
    python sse_server.py --run-simulator    # Run Mesa simulator in-process (live events!)
    python sse_server.py -r --founders 5 --users 20 --speed 4.0  # Custom simulator config

Endpoint:
    GET /api/sim-events - SSE stream of simulator events

Event Format:
    event: sim_event
    id: <sequence_id>
    data: {"event_type": "...", "payload": {...}, "timestamp": "..."}

Web Animation Integration:
    Open http://localhost:5000/about/?sim=1 or public/about/index.html?sim=1
    The animation will connect to SSE and display live simulator events.

WSP References:
    - WSP 50: Pre-action verification (event deduplication)
    - WSP 22: ModLog documentation
"""

from __future__ import annotations

import argparse
import asyncio
import hmac
import json
import logging
import os
import random
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Optional

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import StreamingResponse
    import uvicorn
except ImportError:
    print("ERROR: FastAPI not installed. Run: pip install fastapi uvicorn")
    sys.exit(1)

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

SSE_HEARTBEAT_INTERVAL = 15  # seconds
SSE_RECONNECT_RETRY = 3000   # ms (sent to client)

_ROLE_RANK = {
    "observer_012": 0,
    "member": 1,
    "agent_trader": 2,
    "admin": 3,
}

# Event types we stream to frontend (matches SIM_EVENT_MAP in foundup-cube.js)
STREAMABLE_EVENT_TYPES = {
    # Foundup lifecycle
    "foundup_created",
    "task_state_changed",
    "proof_submitted",
    "verification_recorded",
    "payout_triggered",
    "milestone_published",
    # Market activity
    "fi_trade_executed",
    "order_placed",
    "order_cancelled",
    "order_matched",
    "price_tick",
    "orderbook_snapshot",
    "portfolio_updated",
    "investor_funding_received",
    "mvp_subscription_accrued",
    "subscription_allocation_refreshed",
    "subscription_cycle_reset",
    "mvp_bid_submitted",
    "mvp_offering_resolved",
    "ups_allocation_executed",
    "ups_allocation_result",
    "demurrage_cycle_completed",
    "pavs_treasury_updated",
    "treasury_separation_snapshot",
    # Rating/scoring
    "fi_rating_updated",      # F_i rating color temperature gradient
    "cabr_score_updated",     # CABR 3V engine score (env + soc + part)
    "cabr_pipe_flow_routed",  # CABR pipe-size UPS routing after PoB validation
    # Agent lifecycle (01(02) → 0102 → 01/02 state machine)
    "agent_joins",            # 01(02) enters with public key
    "agent_awakened",         # → 0102 zen state (coherence ≥ 0.618)
    "agent_idle",             # → 01/02 decayed (inactivity)
    "agent_ranked",           # Rank progression 1-7 (mirror of 012)
    "agent_earned",           # F_i payout credited to wallet
    "agent_leaves",           # Logs off with wallet balance
    # SmartDAO escalation (WSP 100: F₀ DAE → F₁+ SmartDAO)
    "smartdao_emergence",     # F₀ → F₁ (DAE matures to SmartDAO)
    "tier_escalation",        # F_n → F_n+1 (tier progression)
    "treasury_autonomy",      # Treasury autonomy activated
    "cross_dao_funding",      # Higher tier funds lower tier
    # Full Tide economics
    "fee_collected",
    "tide_out",
    "tide_in",
    "sustainability_reached",
    # Tide alias events for external consumers
    "tide_support_sent",
    "tide_support_received",
    # State sync for DRIVEN_MODE (simulator controls animation)
    "state_sync",             # Full state snapshot for animation sync
    "phase_command",          # Direct phase control command
    # Synthetic user simulation (Simile AI pattern - pre-launch market testing)
    "synthetic_user_adopted", # Synthetic persona adopted a FoundUp
    "synthetic_user_rejected", # Synthetic persona rejected a FoundUp
}


def _truthy_env(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _member_gate_config() -> Dict[str, Any]:
    allowed_roles_raw = os.environ.get(
        "FAM_MEMBER_ALLOWED_ROLES",
        "observer_012,member,agent_trader,admin",
    )
    allowed_roles = {
        role.strip().lower()
        for role in allowed_roles_raw.split(",")
        if role.strip()
    }
    return {
        "enabled": _truthy_env("FAM_MEMBER_GATE_ENABLED", "0"),
        "invite_key": os.environ.get("FAM_MEMBER_INVITE_KEY", "").strip(),
        "allow_local_bypass": _truthy_env("FAM_MEMBER_GATE_ALLOW_LOCAL_BYPASS", "1"),
        "protect_health": _truthy_env("FAM_MEMBER_GATE_PROTECT_HEALTH", "0"),
        "allowed_roles": allowed_roles or set(_ROLE_RANK.keys()),
    }


def _request_host(request: Request) -> str:
    client = getattr(request, "client", None)
    return (getattr(client, "host", "") or "").lower()


def _is_local_host(host: str) -> bool:
    return host in {"127.0.0.1", "localhost", "::1"}


def _normalize_role(role: str) -> str:
    return (role or "").strip().lower()


def _authorize_member_request(
    request: Request,
    required_role: str = "observer_012",
) -> tuple[bool, str, str]:
    """Authorize member-only endpoint access with optional local bypass.

    Returns:
        (allowed, reason, role)
    """
    config = _member_gate_config()
    if not config["enabled"]:
        return True, "gate_disabled", "observer_012"

    host = _request_host(request)
    if config["allow_local_bypass"] and _is_local_host(host):
        return True, "local_bypass", "admin"

    expected_key = config["invite_key"]
    if not expected_key:
        return False, "member_gate_misconfigured", ""

    provided_key = (
        request.headers.get("x-invite-key")
        or request.query_params.get("invite_key")
        or ""
    ).strip()
    if not hmac.compare_digest(provided_key, expected_key):
        return False, "invalid_invite_key", ""

    role = _normalize_role(
        request.headers.get("x-member-role")
        or request.query_params.get("role")
        or "member"
    )
    if role not in config["allowed_roles"]:
        return False, "role_not_allowed", role

    min_role = _normalize_role(required_role)
    role_rank = _ROLE_RANK.get(role, -1)
    min_rank = _ROLE_RANK.get(min_role, -1)
    if role_rank < min_rank:
        return False, "insufficient_role", role

    return True, "ok", role

# ============================================================================
# FAMDaemon Connection
# ============================================================================

class FAMEventSource:
    """Event source that connects to FAMDaemon."""

    def __init__(self) -> None:
        self._daemon: Optional[Any] = None
        self._connected = False
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._sequence_id = 0
        self._dropped_event_count = 0  # Observability: track backpressure drops

    def connect(self) -> bool:
        """Connect to FAMDaemon if available."""
        if self._connected:
            return True

        try:
            from modules.foundups.agent_market.src.fam_daemon import get_fam_daemon
            self._daemon = get_fam_daemon()
            self._daemon.add_listener(self._on_fam_event)
            self._connected = True
            logger.info("[SSE] Connected to FAMDaemon")
            return True
        except ImportError:
            logger.warning("[SSE] FAMDaemon not available")
            return False
        except Exception as e:
            logger.warning(f"[SSE] Could not connect to FAMDaemon: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from FAMDaemon."""
        if self._daemon and self._connected:
            self._daemon.remove_listener(self._on_fam_event)
            self._connected = False
            logger.info("[SSE] Disconnected from FAMDaemon")

    def _on_fam_event(self, fam_event: Any) -> None:
        """Handle FAMEvent and queue for streaming."""
        if fam_event.event_type not in STREAMABLE_EVENT_TYPES:
            return

        self._sequence_id += 1

        event_data = {
            "event_id": fam_event.event_id,
            "sequence_id": self._sequence_id,
            "event_type": fam_event.event_type,
            "actor_id": fam_event.actor_id,
            "foundup_id": fam_event.foundup_id,
            "task_id": fam_event.task_id,
            "payload": fam_event.payload,
            "timestamp": fam_event.timestamp.isoformat(),
        }

        # Non-blocking put
        try:
            self._event_queue.put_nowait(event_data)
        except asyncio.QueueFull:
            self._dropped_event_count += 1
            logger.warning(
                f"[SSE] Event queue full, dropping event "
                f"(total dropped: {self._dropped_event_count})"
            )

    def _on_fam_event_dict(self, event_dict: Dict[str, Any]) -> None:
        """Handle pre-formatted event dict (for state_sync from BackgroundSimulator)."""
        event_type = event_dict.get("event_type", "")
        if event_type not in STREAMABLE_EVENT_TYPES:
            return

        self._sequence_id += 1
        event_data = {
            "event_id": f"state_sync_{self._sequence_id}",
            "sequence_id": self._sequence_id,
            "event_type": event_type,
            "actor_id": None,
            "foundup_id": None,
            "task_id": None,
            "payload": event_dict.get("payload", {}),
            "timestamp": event_dict.get("timestamp", datetime.now(UTC).isoformat()),
        }

        try:
            self._event_queue.put_nowait(event_data)
        except asyncio.QueueFull:
            self._dropped_event_count += 1

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def dropped_event_count(self) -> int:
        """Count of events dropped due to queue backpressure."""
        return self._dropped_event_count

    @property
    def queue_size(self) -> int:
        """Current queue size for monitoring."""
        return self._event_queue.qsize()

    async def get_event(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """Get next event from queue with timeout."""
        try:
            return await asyncio.wait_for(self._event_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None


# ============================================================================
# Simulated Event Source (fallback when FAMDaemon unavailable)
# ============================================================================

class SimulatedEventSource:
    """Generates simulated events for demo/fallback mode."""

    STARTUP_DOMAINS = [
        ("SpaceX_Lite", "SPLX"),
        ("GotJunk_Pro", "JUNK"),
        ("CloudKitchen", "CKXN"),
        ("AICoach", "AICX"),
        ("GreenEnergy", "GRNE"),
        ("HealthTech", "HTCH"),
        ("EduLearn", "EDUX"),
        ("FinStack", "FSTK"),
    ]

    def __init__(self) -> None:
        self._sequence_id = 0
        self._current_foundup_idx = 0
        self._last_event_time = time.time()

    def _next_sequence(self) -> int:
        self._sequence_id += 1
        return self._sequence_id

    def generate_event(self) -> Optional[Dict[str, Any]]:
        """Generate a random simulated event."""
        now = time.time()

        # Generate events at ~0.5-2 second intervals
        if now - self._last_event_time < random.uniform(0.5, 2.0):
            return None

        self._last_event_time = now

        # Pick random event type with weighted distribution
        event_weights = [
            ("task_state_changed", 40),
            ("fi_trade_executed", 20),
            ("proof_submitted", 15),
            ("payout_triggered", 10),
            ("investor_funding_received", 5),
            ("mvp_bid_submitted", 5),
            ("mvp_offering_resolved", 3),
            ("foundup_created", 2),
        ]

        total_weight = sum(w for _, w in event_weights)
        rand = random.randint(1, total_weight)
        cumulative = 0
        event_type = "task_state_changed"

        for etype, weight in event_weights:
            cumulative += weight
            if rand <= cumulative:
                event_type = etype
                break

        # Generate event data based on type
        foundup_name, token_symbol = self.STARTUP_DOMAINS[
            self._current_foundup_idx % len(self.STARTUP_DOMAINS)
        ]
        foundup_id = f"F_{self._current_foundup_idx % 8}"

        payload = self._generate_payload(event_type, foundup_name, token_symbol)

        return {
            "event_id": f"sim_{self._next_sequence():08x}",
            "sequence_id": self._sequence_id,
            "event_type": event_type,
            "actor_id": f"agent_{random.randint(1, 20):03d}",
            "foundup_id": foundup_id,
            "task_id": f"task_{random.randint(1, 100):04d}" if "task" in event_type else None,
            "payload": payload,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def _generate_payload(
        self, event_type: str, foundup_name: str, token_symbol: str
    ) -> Dict[str, Any]:
        """Generate payload for event type."""
        if event_type == "foundup_created":
            self._current_foundup_idx += 1
            return {"name": foundup_name, "token_symbol": token_symbol}

        elif event_type == "task_state_changed":
            # Use new_status (not new_state) per frontend expectation
            statuses = ["open", "claimed", "submitted", "verified", "paid"]
            return {
                "new_status": random.choice(statuses),
                "task_id": f"task_{random.randint(1, 100):04d}",
            }

        elif event_type == "fi_trade_executed":
            qty = random.randint(10, 500)
            price = random.uniform(0.01, 2.0)
            return {
                "quantity": qty,
                "price": round(price, 4),
                "ups_total": round(qty * price, 2),
                "side": random.choice(["buy", "sell"]),
            }

        elif event_type == "investor_funding_received":
            return {
                "btc_amount": round(random.uniform(0.1, 1.0), 2),
                "source_foundup_id": "F_0",
            }

        elif event_type == "mvp_subscription_accrued":
            return {"added_ups": random.randint(10, 100)}

        elif event_type == "mvp_bid_submitted":
            return {"bid_ups": random.randint(50, 500)}

        elif event_type == "mvp_offering_resolved":
            return {"total_injection_ups": random.randint(100, 2000)}

        elif event_type == "proof_submitted":
            return {"proof_type": "work_complete"}

        elif event_type == "payout_triggered":
            return {"amount": random.randint(10, 200)}

        return {}


# ============================================================================
# Background Simulator (runs Mesa model in-process)
# ============================================================================

class BackgroundSimulator:
    """Runs Mesa simulator in background thread for live SSE events."""

    def __init__(self, num_founders: int = 3, num_users: int = 10, tick_rate: float = 2.0) -> None:
        self._num_founders = num_founders
        self._num_users = num_users
        self._tick_rate = tick_rate
        self._model: Optional[Any] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._state_sync_interval = 10  # Emit state_sync every N ticks
        self._tick_count = 0

    def start(self) -> bool:
        """Start simulator in background thread."""
        if self._running:
            return True

        try:
            from modules.foundups.simulator.config import SimulatorConfig
            from modules.foundups.simulator.mesa_model import FoundUpsModel

            config = SimulatorConfig(
                num_founder_agents=self._num_founders,
                num_user_agents=self._num_users,
                tick_rate_hz=self._tick_rate,
            )

            # Create model - uses get_fam_daemon() singleton (shared with SSE server)
            self._model = FoundUpsModel(config=config)
            self._model.start()
            self._running = True

            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

            logger.info(
                f"[SIM] Background simulator started: "
                f"{self._num_founders} founders, {self._num_users} users, "
                f"{self._tick_rate} ticks/sec"
            )
            return True

        except ImportError as e:
            logger.error(f"[SIM] Could not import simulator: {e}")
            return False
        except Exception as e:
            logger.error(f"[SIM] Could not start simulator: {e}")
            return False

    def _run_loop(self) -> None:
        """Main simulation loop (runs in background thread)."""
        tick_interval = 1.0 / self._tick_rate

        while self._running:
            try:
                self._model.step()
                self._tick_count += 1

                # Emit state_sync periodically for DRIVEN_MODE animation
                if self._tick_count % self._state_sync_interval == 0:
                    self._emit_state_sync()

                time.sleep(tick_interval)
            except Exception as e:
                logger.error(f"[SIM] Error in simulation loop: {e}")
                time.sleep(1)  # Prevent tight error loop

    def _emit_state_sync(self) -> None:
        """Emit state_sync event with full simulation state snapshot."""
        try:
            stats = self._model.get_stats()
            state = self._model.get_state()

            # Map lifecycle stage to animation phase
            lifecycle_stage = stats.get("lifecycle_stage", "PoC")
            phase = self._lifecycle_to_phase(lifecycle_stage, stats)

            # Calculate filled blocks from FoundUp progress
            total_foundups = len(state.foundups) if hasattr(state, 'foundups') else 1
            completed_tasks = stats.get("completed_tasks", 0)
            total_blocks = 64  # 4x4x4 cube

            # Estimate filled blocks from task completion rate
            filled_blocks = min(total_blocks, int(completed_tasks * 2))

            state_sync_event = {
                "event_type": "state_sync",
                "payload": {
                    "phase": phase,
                    "tick": self._tick_count,
                    "foundups_count": total_foundups,
                    "agents_count": stats.get("agent_count", 0),
                    "total_fi": stats.get("total_fi", 0),
                    "lifecycle_stage": lifecycle_stage,
                    "filled_blocks": filled_blocks,
                    "total_blocks": total_blocks,
                },
                "timestamp": datetime.now(UTC).isoformat(),
            }

            # Queue for SSE streaming
            if hasattr(self, '_event_source') and self._event_source:
                self._event_source._on_fam_event_dict(state_sync_event)
            else:
                # Fallback: emit via FAMDaemon if available
                try:
                    from modules.foundups.agent_market.src.fam_daemon import get_fam_daemon
                    daemon = get_fam_daemon()
                    daemon.emit_custom_event("state_sync", state_sync_event["payload"])
                except Exception:
                    pass  # Silent fail - don't break simulation loop

        except Exception as e:
            logger.debug(f"[SIM] state_sync emission failed: {e}")

    def _lifecycle_to_phase(self, lifecycle_stage: str, stats: dict) -> str:
        """Map simulator lifecycle stage to animation phase."""
        phase_map = {
            "PoC": "IDEA",
            "Proto": "BUILDING",
            "MVP": "LAUNCH",
            "smartDAO": "CELEBRATE",
        }
        base_phase = phase_map.get(lifecycle_stage, "BUILDING")

        # Refine based on stats
        if lifecycle_stage == "Proto":
            # Check progress percentage
            completed = stats.get("completed_tasks", 0)
            total = stats.get("total_tasks", 1) or 1
            progress = completed / total
            if progress < 0.3:
                return "SCAFFOLD"
            elif progress < 0.8:
                return "BUILDING"
            else:
                return "PROMOTING"

        return base_phase

    def set_event_source(self, event_source: "FAMEventSource") -> None:
        """Set FAMEventSource for direct state_sync emission."""
        self._event_source = event_source

    def stop(self) -> None:
        """Stop simulator gracefully."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            logger.info("[SIM] Background simulator stopped")

    @property
    def is_running(self) -> bool:
        return self._running


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="FoundUps SSE Server",
    description="Server-Sent Events for FoundUps cube visualization",
    version="1.0.0",
)

# CORS configuration for foundups.com
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://foundups.com",
        "https://foundupscom.web.app",
        "https://foundupscom.firebaseapp.com",
        "http://localhost:5000",  # Firebase local dev
        "http://127.0.0.1:5000",
    ],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Global state
_fam_source = FAMEventSource()
_sim_source = SimulatedEventSource()
_background_sim: Optional[BackgroundSimulator] = None
_use_simulation = False


async def event_generator(
    request: Request,
    member_role: str = "observer_012",
) -> AsyncGenerator[str, None]:
    """Generate SSE events for client."""
    global _fam_source, _sim_source, _use_simulation

    logger.info("[SSE] Client connected")
    last_heartbeat = time.time()

    # Send initial connection event
    yield format_sse_event(
        "connected",
        {
            "status": "connected",
            "mode": "simulated" if _use_simulation else "live",
            "heartbeat_interval": SSE_HEARTBEAT_INTERVAL,
            "member_role": member_role,
        },
        sequence_id=0,
    )

    try:
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                logger.info("[SSE] Client disconnected")
                break

            event_data = None

            # Try to get event from appropriate source
            if not _use_simulation and _fam_source.is_connected:
                event_data = await _fam_source.get_event(timeout=0.5)
            else:
                # Use simulated events
                event_data = _sim_source.generate_event()
                if not event_data:
                    await asyncio.sleep(0.1)

            # Yield event if we have one
            if event_data:
                yield format_sse_event(
                    "sim_event",
                    event_data,
                    sequence_id=event_data.get("sequence_id", 0),
                )

            # Send heartbeat if needed
            now = time.time()
            if now - last_heartbeat >= SSE_HEARTBEAT_INTERVAL:
                yield format_sse_event(
                    "heartbeat",
                    {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "mode": "simulated" if _use_simulation else "live",
                    },
                    sequence_id=0,
                )
                last_heartbeat = now

    except asyncio.CancelledError:
        logger.info("[SSE] Connection cancelled")
    except Exception as e:
        logger.error(f"[SSE] Error in event generator: {e}")
        yield format_sse_event(
            "error",
            {"error": str(e), "timestamp": datetime.now(UTC).isoformat()},
            sequence_id=0,
        )


def format_sse_event(event_type: str, data: Dict[str, Any], sequence_id: int) -> str:
    """Format data as SSE event."""
    lines = [
        f"event: {event_type}",
        f"id: {sequence_id}",
        f"retry: {SSE_RECONNECT_RETRY}",
        f"data: {json.dumps(data)}",
        "",
        "",  # SSE requires double newline
    ]
    return "\n".join(lines)


@app.get("/api/sim-events")
async def sim_events(request: Request):
    """SSE endpoint for simulator events."""
    allowed, reason, role = _authorize_member_request(
        request,
        required_role="observer_012",
    )
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail={"error": "member_access_denied", "reason": reason},
        )

    return StreamingResponse(
        event_generator(request, member_role=role),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@app.get("/api/health")
async def health(request: Request):
    """Health check endpoint."""
    config = _member_gate_config()
    if config["enabled"] and config["protect_health"]:
        allowed, reason, _ = _authorize_member_request(
            request,
            required_role="observer_012",
        )
        if not allowed:
            raise HTTPException(
                status_code=403,
                detail={"error": "member_access_denied", "reason": reason},
            )

    return {
        "status": "healthy",
        "mode": "simulated" if _use_simulation else "live",
        "fam_connected": _fam_source.is_connected,
        "queue_size": _fam_source.queue_size,
        "dropped_events": _fam_source.dropped_event_count,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "service": "FoundUps SSE Server",
        "version": "1.0.0",
        "endpoints": {
            "/api/sim-events": "SSE stream of simulator events",
            "/api/health": "Health check",
        },
    }


# ============================================================================
# Main Entry Point
# ============================================================================

def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="FoundUps SSE Server - Stream simulator events to web frontend"
    )

    parser.add_argument(
        "--port", "-p",
        type=int,
        default=int(os.environ.get("PORT", 8080)),
        help="Port to listen on (default: 8080 or PORT env var)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--simulate", "-s",
        action="store_true",
        help="Use simulated events (don't connect to FAMDaemon)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--run-simulator", "-r",
        action="store_true",
        help="Run Mesa simulator in background (events flow to SSE)"
    )
    parser.add_argument(
        "--founders",
        type=int,
        default=3,
        help="Number of founder agents (with --run-simulator)"
    )
    parser.add_argument(
        "--users",
        type=int,
        default=10,
        help="Number of user agents (with --run-simulator)"
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=2.0,
        help="Tick rate in Hz (with --run-simulator)"
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    global _use_simulation, _fam_source, _background_sim

    args = parse_args()
    setup_logging(args.verbose)

    # Start background simulator if requested (must happen BEFORE FAMDaemon connect)
    if args.run_simulator:
        _background_sim = BackgroundSimulator(
            num_founders=args.founders,
            num_users=args.users,
            tick_rate=args.speed,
        )
        if _background_sim.start():
            _use_simulation = False  # Force live mode - simulator is emitting events
            # Wire simulator to FAMEventSource for state_sync emission
            _background_sim.set_event_source(_fam_source)
            logger.info("[SSE] Background simulator wired to FAMEventSource for state_sync")
        else:
            logger.warning("[SSE] Background simulator failed to start, falling back to simulated events")
            _background_sim = None
            _use_simulation = True
    else:
        _use_simulation = args.simulate

    # Connect to FAMDaemon (now has events from background sim if running)
    if not _use_simulation:
        if not _fam_source.connect():
            logger.info("[SSE] Falling back to simulated events")
            _use_simulation = True

    mode_desc = "simulated" if _use_simulation else ("live+simulator" if _background_sim else "live")
    logger.info(
        f"[SSE] Starting server on {args.host}:{args.port} (mode: {mode_desc})"
    )

    try:
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level="info" if args.verbose else "warning",
        )
    except KeyboardInterrupt:
        logger.info("[SSE] Shutting down...")
    finally:
        _fam_source.disconnect()
        if _background_sim:
            _background_sim.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
