"""Voice cloning safety policy gate.

Enforces consent and whitelist requirements for voice cloning operations.
All voice cloning requests must pass through this gate before execution.

Policy Requirements:
    1. Explicit consent recorded for voice ID
    2. Voice ID on allowed_voices whitelist
    3. Emergency kill switch not engaged
    4. Audit logging for all requests

Usage:
    from modules.infrastructure.shared_utilities.voice_cloning_policy import (
        get_voice_policy,
        VoiceCloneRequest,
    )

    policy = get_voice_policy()

    # Check if cloning is allowed
    request = VoiceCloneRequest(
        voice_id="voice_012",
        requester="system",
        purpose="stream_tts",
    )

    result = policy.check(request)
    if result.allowed:
        # Proceed with voice cloning
        ...
    else:
        print(f"Denied: {result.reason}")
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set


@dataclass
class VoiceCloneRequest:
    """Voice cloning request for policy check."""

    voice_id: str
    requester: str
    purpose: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PolicyResult:
    """Result of policy check."""

    allowed: bool
    reason: str
    voice_id: str
    checked_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "voice_id": self.voice_id,
            "checked_at": self.checked_at.isoformat(),
        }


@dataclass
class VoiceConsent:
    """Recorded consent for voice cloning."""

    voice_id: str
    consented_by: str
    consented_at: datetime
    expires_at: Optional[datetime] = None
    scope: str = "all"  # "all", "internal", "stream"

    def is_valid(self) -> bool:
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True


class VoiceCloningPolicy:
    """Voice cloning policy enforcement."""

    def __init__(
        self,
        allowed_voices: Optional[Set[str]] = None,
        consent_store_path: Optional[Path] = None,
        audit_callback: Optional[Callable[[Dict], None]] = None,
    ):
        self._allowed_voices: Set[str] = allowed_voices or set()
        self._consents: Dict[str, VoiceConsent] = {}
        self._kill_switch_engaged: bool = False
        self._consent_store_path = consent_store_path
        self._audit_callback = audit_callback
        self._load_consents()

    def _load_consents(self) -> None:
        """Load consents from persistent storage."""
        if self._consent_store_path and self._consent_store_path.exists():
            try:
                data = json.loads(self._consent_store_path.read_text())
                for voice_id, consent_data in data.get("consents", {}).items():
                    self._consents[voice_id] = VoiceConsent(
                        voice_id=voice_id,
                        consented_by=consent_data["consented_by"],
                        consented_at=datetime.fromisoformat(consent_data["consented_at"]),
                        expires_at=(
                            datetime.fromisoformat(consent_data["expires_at"])
                            if consent_data.get("expires_at")
                            else None
                        ),
                        scope=consent_data.get("scope", "all"),
                    )
                self._allowed_voices = set(data.get("allowed_voices", []))
                self._kill_switch_engaged = data.get("kill_switch", False)
            except (json.JSONDecodeError, KeyError):
                pass

    def _save_consents(self) -> None:
        """Persist consents to storage."""
        if self._consent_store_path:
            data = {
                "consents": {
                    vid: {
                        "consented_by": c.consented_by,
                        "consented_at": c.consented_at.isoformat(),
                        "expires_at": c.expires_at.isoformat() if c.expires_at else None,
                        "scope": c.scope,
                    }
                    for vid, c in self._consents.items()
                },
                "allowed_voices": list(self._allowed_voices),
                "kill_switch": self._kill_switch_engaged,
            }
            self._consent_store_path.parent.mkdir(parents=True, exist_ok=True)
            self._consent_store_path.write_text(json.dumps(data, indent=2))

    def _audit(self, request: VoiceCloneRequest, result: PolicyResult) -> None:
        """Log audit event."""
        event = {
            "event": "voice_clone_policy_check",
            "voice_id": request.voice_id,
            "requester": request.requester,
            "purpose": request.purpose,
            "allowed": result.allowed,
            "reason": result.reason,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if self._audit_callback:
            self._audit_callback(event)

    def check(self, request: VoiceCloneRequest) -> PolicyResult:
        """Check if voice cloning request is allowed."""
        # 1. Kill switch check
        if self._kill_switch_engaged:
            result = PolicyResult(
                allowed=False,
                reason="Voice cloning disabled (kill switch engaged)",
                voice_id=request.voice_id,
            )
            self._audit(request, result)
            return result

        # 2. Whitelist check
        if request.voice_id not in self._allowed_voices:
            result = PolicyResult(
                allowed=False,
                reason=f"Voice '{request.voice_id}' not in allowed_voices whitelist",
                voice_id=request.voice_id,
            )
            self._audit(request, result)
            return result

        # 3. Consent check
        consent = self._consents.get(request.voice_id)
        if consent is None:
            result = PolicyResult(
                allowed=False,
                reason=f"No consent recorded for voice '{request.voice_id}'",
                voice_id=request.voice_id,
            )
            self._audit(request, result)
            return result

        if not consent.is_valid():
            result = PolicyResult(
                allowed=False,
                reason=f"Consent for voice '{request.voice_id}' has expired",
                voice_id=request.voice_id,
            )
            self._audit(request, result)
            return result

        # All checks passed
        result = PolicyResult(
            allowed=True,
            reason="Policy satisfied (whitelist + valid consent)",
            voice_id=request.voice_id,
        )
        self._audit(request, result)
        return result

    def record_consent(
        self,
        voice_id: str,
        consented_by: str,
        scope: str = "all",
        expires_at: Optional[datetime] = None,
    ) -> VoiceConsent:
        """Record consent for a voice ID."""
        consent = VoiceConsent(
            voice_id=voice_id,
            consented_by=consented_by,
            consented_at=datetime.utcnow(),
            expires_at=expires_at,
            scope=scope,
        )
        self._consents[voice_id] = consent
        self._save_consents()
        return consent

    def add_to_whitelist(self, voice_id: str) -> None:
        """Add voice ID to allowed whitelist."""
        self._allowed_voices.add(voice_id)
        self._save_consents()

    def remove_from_whitelist(self, voice_id: str) -> None:
        """Remove voice ID from whitelist."""
        self._allowed_voices.discard(voice_id)
        self._save_consents()

    def engage_kill_switch(self) -> None:
        """Emergency disable all voice cloning."""
        self._kill_switch_engaged = True
        self._save_consents()

    def disengage_kill_switch(self) -> None:
        """Re-enable voice cloning after emergency."""
        self._kill_switch_engaged = False
        self._save_consents()

    def is_kill_switch_engaged(self) -> bool:
        """Check if kill switch is currently engaged."""
        return self._kill_switch_engaged

    def get_allowed_voices(self) -> List[str]:
        """Get list of whitelisted voice IDs."""
        return sorted(self._allowed_voices)


# Singleton policy instance
_POLICY: Optional[VoiceCloningPolicy] = None


def _default_consent_path() -> Path:
    """Default consent store path."""
    return Path(os.getenv(
        "VOICE_CONSENT_STORE",
        "memory/voice_cloning_consents.json"
    ))


def get_voice_policy() -> VoiceCloningPolicy:
    """Get the singleton voice cloning policy."""
    global _POLICY
    if _POLICY is None:
        _POLICY = VoiceCloningPolicy(
            consent_store_path=_default_consent_path(),
        )
    return _POLICY


def reset_policy() -> None:
    """Reset policy (for testing)."""
    global _POLICY
    _POLICY = None
