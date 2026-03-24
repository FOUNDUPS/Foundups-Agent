#!/usr/bin/env python3
"""
OpenClaw Bridge - Webhook Receiver

FastAPI server that receives messages from OpenClaw Gateway
and routes them through the OpenClaw DAE (Frontal Lobe) into
WRE-routed execution with WSP as the governing rails.

Architecture:
  OpenClaw Gateway (Node.js) -> POST /webhook/openclaw (legacy: /webhook/moltbot)
  -> OpenClawDAE.process() -> Intent -> Preflight -> Plan
  -> Permission Gate -> Execute (WRE) -> Validate -> Remember

WSP 73: Digital Twin Architecture Integration
WSP 46: WRE Protocol (execution cortex)
WSP 50: Pre-Action Verification
"""

import os
import logging
import time
from datetime import datetime
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("openclaw_bridge")


# ---------------------------------------------------------------------------
# Rate Limiting: Token Bucket (WSP 95 - DoS Protection)
# ---------------------------------------------------------------------------

class TokenBucket:
    """Token bucket rate limiter for webhook endpoints."""

    def __init__(self, rate: float, capacity: float):
        """
        Args:
            rate: Tokens added per second
            capacity: Maximum tokens in bucket
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()

    def consume(self, tokens: float = 1.0) -> bool:
        """
        Try to consume tokens from bucket.

        Returns:
            True if tokens consumed, False if rate limited.
        """
        now = time.time()
        elapsed = now - self.last_update
        self.last_update = now

        # Add tokens based on elapsed time
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


class WebhookRateLimiter:
    """Per-sender + per-channel rate limiting for webhook endpoints."""

    def __init__(self):
        # Config from env (default: 10 req/min per sender, 60 req/min per channel)
        self.sender_rate = float(os.getenv("OPENCLAW_RATE_SENDER_PER_SEC", "0.167"))  # 10/min
        self.sender_capacity = float(os.getenv("OPENCLAW_RATE_SENDER_BURST", "5"))
        self.channel_rate = float(os.getenv("OPENCLAW_RATE_CHANNEL_PER_SEC", "1.0"))  # 60/min
        self.channel_capacity = float(os.getenv("OPENCLAW_RATE_CHANNEL_BURST", "20"))

        self._sender_buckets: Dict[str, TokenBucket] = {}
        self._channel_buckets: Dict[str, TokenBucket] = {}
        self._last_cleanup = time.time()

    def _cleanup_stale_buckets(self) -> None:
        """Remove stale buckets to prevent memory growth."""
        now = time.time()
        if now - self._last_cleanup < 300:  # Cleanup every 5 min
            return
        self._last_cleanup = now

        # Remove buckets not used in 10 minutes
        stale_threshold = now - 600
        self._sender_buckets = {
            k: v for k, v in self._sender_buckets.items()
            if v.last_update > stale_threshold
        }
        self._channel_buckets = {
            k: v for k, v in self._channel_buckets.items()
            if v.last_update > stale_threshold
        }

    def check(self, sender: str, channel: str) -> tuple:
        """
        Check rate limits for sender and channel.

        Returns:
            (allowed: bool, reason: str or None)
        """
        self._cleanup_stale_buckets()

        # Get or create sender bucket
        if sender not in self._sender_buckets:
            self._sender_buckets[sender] = TokenBucket(
                self.sender_rate, self.sender_capacity
            )

        # Get or create channel bucket
        if channel not in self._channel_buckets:
            self._channel_buckets[channel] = TokenBucket(
                self.channel_rate, self.channel_capacity
            )

        # Check sender rate limit
        if not self._sender_buckets[sender].consume():
            logger.warning(
                "[RATE-LIMIT] Sender rate limit exceeded: %s", sender
            )
            return False, f"sender rate limit exceeded (max {self.sender_rate * 60:.0f}/min)"

        # Check channel rate limit
        if not self._channel_buckets[channel].consume():
            logger.warning(
                "[RATE-LIMIT] Channel rate limit exceeded: %s", channel
            )
            return False, f"channel rate limit exceeded (max {self.channel_rate * 60:.0f}/min)"

        return True, None


# Global rate limiter instance
_rate_limiter: Optional[WebhookRateLimiter] = None


def get_rate_limiter() -> WebhookRateLimiter:
    """Get or create the rate limiter singleton."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = WebhookRateLimiter()
    return _rate_limiter


def is_rate_limiting_enabled() -> bool:
    """Check if rate limiting is enabled via env."""
    return os.getenv("OPENCLAW_RATE_LIMIT_ENABLED", "1") != "0"


def _emit_rate_limited_event(sender: str, channel: str, reason: str) -> None:
    """Emit rate_limited event to AI Overseer correlator."""
    try:
        from modules.ai_intelligence.ai_overseer.src.ai_overseer import AIIntelligenceOverseer
        from pathlib import Path
        overseer = AIIntelligenceOverseer(Path("O:/Foundups-Agent"))
        overseer.ingest_security_event(
            event_type="rate_limited",
            sender=sender,
            channel=channel,
            details={"reason": reason},
        )
    except Exception as exc:
        logger.debug("[RATE-LIMIT] Failed to emit event to overseer: %s", exc)


# Lazy-initialized OpenClaw DAE singleton
_openclaw_dae = None


def _get_openclaw_dae():
    """Get or create the OpenClaw DAE singleton (lazy init)."""
    global _openclaw_dae
    if _openclaw_dae is None:
        from .openclaw_dae import OpenClawDAE
        _openclaw_dae = OpenClawDAE()
    return _openclaw_dae


class MoltbotMessage(BaseModel):
    """Inbound message from OpenClaw Gateway (legacy name retained for compatibility)."""
    message: str
    sessionKey: str = "default"
    channel: str = "unknown"
    sender: str = "unknown"
    metadata: dict = {}


class OpenClawMessage(MoltbotMessage):
    """Alias for OpenClaw naming."""


class FoundupsResponse(BaseModel):
    """Response to send back via OpenClaw."""
    text: str
    deliver: bool = True
    channel: Optional[str] = None
    to: Optional[str] = None


# FastAPI app
app = FastAPI(
    title="OpenClaw Bridge",
    description="Bridge between OpenClaw and Foundups Agent (legacy Moltbot compatible)",
    version="0.1.0"
)


def get_webhook_token() -> str:
    """
    Get webhook token from environment.

    Priority:
    1. OpenClaw_Pass from .env (loaded via dotenv)
    2. FOUNDUPS_WEBHOOK_TOKEN env var
    3. Insecure default (development only)
    """
    # Try loading .env if dotenv available
    try:
        from dotenv import load_dotenv
        from pathlib import Path
        env_path = Path(__file__).parent.parent.parent.parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=False)
    except ImportError:
        pass

    # Priority: OpenClaw_Pass > FOUNDUPS_WEBHOOK_TOKEN > insecure default
    token = os.environ.get("OpenClaw_Pass") or os.environ.get("FOUNDUPS_WEBHOOK_TOKEN")
    if not token:
        logger.warning("No webhook token configured (OpenClaw_Pass or "
                       "FOUNDUPS_WEBHOOK_TOKEN) - using insecure default")
        return "dev-token-change-me"
    return token


def verify_token(
    authorization: Optional[str],
    x_moltbot_token: Optional[str],
    x_openclaw_token: Optional[str]
) -> bool:
    """Verify incoming request token (OpenClaw preferred, Moltbot legacy)."""
    expected = get_webhook_token()
    
    # Check Authorization: Bearer <token>
    if authorization and authorization.startswith("Bearer "):
        if authorization[7:] == expected:
            return True
    
    # Check x-openclaw-token header
    if x_openclaw_token == expected:
        return True

    # Check x-moltbot-token header (legacy)
    if x_moltbot_token == expected:
        return True
    
    return False


async def process_with_holoindex(message: str, context: dict) -> str:
    """
    LEGACY: Direct HoloIndex-only routing.
    Kept for backward compatibility. New requests go through OpenClawDAE.
    """
    try:
        from holo_index.core import HoloIndex
        holo = HoloIndex()
        results = holo.search(message, limit=3)
        code_hits = results.get("code", [])
        if code_hits:
            context_text = "\n".join([r.get("content", "")[:200] for r in code_hits[:2]])
            return f"Based on my knowledge:\n\n{context_text}\n\n[HoloIndex Direct]"
        return f"No results found for: {message[:100]}"
    except Exception as e:
        logger.error(f"HoloIndex fallback error: {e}")
        return f"I encountered an issue processing your request. Please try again."


async def process_via_openclaw_dae(
    message: str,
    sender: str,
    channel: str,
    session_key: str,
    metadata: dict,
) -> str:
    """
    Route message through the OpenClaw DAE (Frontal Lobe).

    Full autonomy loop:
    Ingress -> Intent -> Preflight -> Plan -> Permission -> Execute -> Validate -> Remember
    """
    dae = _get_openclaw_dae()
    return await dae.process(
        message=message,
        sender=sender,
        channel=channel,
        session_key=session_key,
        metadata=metadata,
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "openclaw_bridge",
        "legacy_service": "moltbot_bridge",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/webhook/openclaw")
@app.post("/webhook/moltbot")
async def receive_openclaw_message(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_moltbot_token: Optional[str] = Header(None, alias="x-moltbot-token"),
    x_openclaw_token: Optional[str] = Header(None, alias="x-openclaw-token")
):
    """
    Receive message from OpenClaw Gateway.
    
    Expected payload from OpenClaw hooks.mappings transform:
    {
        "message": "user's message",
        "sessionKey": "session-id",
        "channel": "whatsapp|telegram|etc",
        "sender": "phone/user-id",
        "metadata": {...}
    }
    """
    # Verify token
    if not verify_token(authorization, x_moltbot_token, x_openclaw_token):
        raise HTTPException(status_code=401, detail="Invalid token")

    # Parse body
    try:
        body = await request.json()
        msg = MoltbotMessage(**body)
    except Exception as e:
        logger.error(f"Failed to parse message: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")

    # Rate limit check (WSP 95 - DoS protection)
    if is_rate_limiting_enabled():
        limiter = get_rate_limiter()
        allowed, reason = limiter.check(msg.sender, msg.channel)
        if not allowed:
            logger.warning(
                "[DAEMON][OPENCLAW-RATELIMIT] event=rate_limited sender=%s channel=%s reason=%s",
                msg.sender, msg.channel, reason
            )
            # Emit to AI Overseer correlator
            _emit_rate_limited_event(msg.sender, msg.channel, reason)
            raise HTTPException(status_code=429, detail=reason)

    logger.info(f"Received from {msg.channel}/{msg.sender}: {msg.message[:50]}...")

    # Gateway Continuity Layer: Create messaging continuity context for this request
    messaging_continuity_ctx = None
    enriched_metadata = dict(msg.metadata) if msg.metadata else {}
    enriched_metadata["source_surface"] = "messaging"

    # Derive unique session_key to avoid child ID collision when sessionKey is missing/default
    effective_session_key = msg.sessionKey
    if not effective_session_key or effective_session_key == "default":
        # Will be overwritten below if continuity context is created
        effective_session_key = f"webhook_{hash(f'{msg.sender}_{msg.channel}') % 100000:05d}"

    try:
        from .continuity_context import ContinuityManager
        messaging_continuity_ctx = ContinuityManager.from_messaging(
            platform=msg.channel,
            sender=msg.sender,
            channel=msg.channel,
            metadata=msg.metadata,
        )
        # Propagate messaging context as parent for OpenClaw processing
        enriched_metadata["parent_continuity_id"] = messaging_continuity_ctx.continuity_id

        # Derive unique session_key from messaging continuity to avoid child ID collision
        if not msg.sessionKey or msg.sessionKey == "default":
            effective_session_key = f"msg_{messaging_continuity_ctx.continuity_id[:12]}"

        # Record messaging ingress breadcrumb for cross-surface tracking
        try:
            from modules.infrastructure.database.src.agent_db import AgentDB
            db = AgentDB()
            db.add_breadcrumb(
                session_id=effective_session_key,
                action="messaging_ingress",
                agent_id="0102",
                data={
                    "platform": msg.channel,
                    "message_preview": msg.message[:50] if msg.message else "",
                },
                continuity_id=messaging_continuity_ctx.continuity_id,
                runtime_surface=messaging_continuity_ctx.surface.value,
                sender_normalized=messaging_continuity_ctx.sender_normalized,
            )
        except Exception:
            pass  # Breadcrumb recording is optional
    except Exception as ctx_exc:
        logger.debug(f"Messaging continuity context creation skipped: {ctx_exc}")

    # Route through OpenClaw DAE (Frontal Lobe) -> WRE -> Domain DAEs
    try:
        response_text = await process_via_openclaw_dae(
            message=msg.message,
            sender=msg.sender,
            channel=msg.channel,
            session_key=effective_session_key,
            metadata=enriched_metadata,
        )
    except Exception as exc:
        logger.error(f"OpenClaw DAE failed, falling back to HoloIndex: {exc}")
        context = {
            "channel": msg.channel,
            "sender": msg.sender,
            "sessionKey": msg.sessionKey,
            "metadata": msg.metadata,
        }
        response_text = await process_with_holoindex(msg.message, context)
    
    # Return response for OpenClaw to deliver
    response = FoundupsResponse(
        text=response_text,
        deliver=True,
        channel=msg.channel,  # Reply on same channel
        to=msg.sender         # Reply to sender
    )
    
    return JSONResponse(
        status_code=200,
        content=response.model_dump()
    )


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("OPENCLAW_BRIDGE_PORT") or os.environ.get("MOLTBOT_BRIDGE_PORT", 18800))
    logger.info(f"Starting OpenClaw Bridge on port {port}")
    
    uvicorn.run(app, host="127.0.0.1", port=port)
