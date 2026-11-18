#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bypass Classifier for Token Efficiency Stack (P1).

Classifies command outputs to determine which must remain raw/uncompressed.
Output format: WSP-99 M2M.

Contract: docs/contracts/REDDOG_WSP99_RTK_TOKEN_EFFICIENCY_CONTRACT_PHASE1.md Section 6
WSP: WSP_97, WSP_99

Bypass Classes (fail-closed):
    BYPASS_SECURITY    - CVE, vulnerability, exploit, security scan output
    BYPASS_AUTH        - tokens, keys, passwords, credentials, sessions
    BYPASS_PROVENANCE  - signed-by, verified, attestation, witness, git provenance
    BYPASS_SIGNING     - signatures, public/private keys, fingerprints
    BYPASS_PERMISSION  - ALLOW/DENY/GRANT/REVOKE, scope, principal
    BYPASS_RECEIPT     - receipt_id, work_order_id, settled_at, proof-of-compute
    ALLOW_COMPRESSION  - safe to compress
    NEEDS_HUMAN_REVIEW - unknown command or ambiguous output
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class BypassClass(Enum):
    """Bypass classification categories (Contract Section 6a)."""

    BYPASS_SECURITY = "BYPASS_SECURITY"
    BYPASS_AUTH = "BYPASS_AUTH"
    BYPASS_PROVENANCE = "BYPASS_PROVENANCE"
    BYPASS_SIGNING = "BYPASS_SIGNING"
    BYPASS_PERMISSION = "BYPASS_PERMISSION"
    BYPASS_RECEIPT = "BYPASS_RECEIPT"
    ALLOW_COMPRESSION = "ALLOW_COMPRESSION"
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"


# Pattern definitions per Contract Section 6a
BYPASS_PATTERNS: dict[BypassClass, list[re.Pattern]] = {
    BypassClass.BYPASS_SECURITY: [
        re.compile(r"CVE-\d{4}-\d+", re.IGNORECASE),
        re.compile(r"\bVULNERABILITY\b", re.IGNORECASE),
        re.compile(r"\bEXPLOIT\b", re.IGNORECASE),
        re.compile(r"\bCRITICAL:\s", re.IGNORECASE),
        re.compile(r"\bHIGH:\s", re.IGNORECASE),
        re.compile(r"\bsecurity\s+scan\b", re.IGNORECASE),
        re.compile(r"\bmalware\b", re.IGNORECASE),
        re.compile(r"\binjection\b", re.IGNORECASE),
        re.compile(r"\bXSS\b"),
        re.compile(r"\bSQLi\b", re.IGNORECASE),
    ],
    BypassClass.BYPASS_AUTH: [
        re.compile(r"\btoken\s*=", re.IGNORECASE),
        re.compile(r"\bkey\s*=", re.IGNORECASE),
        re.compile(r"\bpassword\s*=", re.IGNORECASE),
        re.compile(r"\bsecret\s*=", re.IGNORECASE),
        re.compile(r"\bcredential", re.IGNORECASE),
        re.compile(r"\bsession_id\s*=", re.IGNORECASE),
        re.compile(r"\bauth_token\b", re.IGNORECASE),
        re.compile(r"\bapi_key\b", re.IGNORECASE),
        re.compile(r"\baccess_token\b", re.IGNORECASE),
        re.compile(r"\brefresh_token\b", re.IGNORECASE),
        re.compile(r"\bBearer\s+[A-Za-z0-9_-]+"),
        re.compile(r"\bsk-[A-Za-z0-9]+"),  # OpenAI-style keys
        re.compile(r"\bAIza[A-Za-z0-9]+"),  # Google API keys
    ],
    BypassClass.BYPASS_PROVENANCE: [
        re.compile(r"\bsigned\s+by\b", re.IGNORECASE),
        re.compile(r"\bverified\b", re.IGNORECASE),
        re.compile(r"\battestation\b", re.IGNORECASE),
        re.compile(r"\bwitness\b", re.IGNORECASE),
        re.compile(r"\bcommit\s+[a-f0-9]{7,40}\b", re.IGNORECASE),
        re.compile(r"\bgit\s+diff\b", re.IGNORECASE),
        re.compile(r"\bgit\s+log\b", re.IGNORECASE),
        re.compile(r"\bauthor:\s", re.IGNORECASE),
        re.compile(r"\bcommitter:\s", re.IGNORECASE),
        re.compile(r"\bsigned-off-by:\s", re.IGNORECASE),
    ],
    BypassClass.BYPASS_SIGNING: [
        re.compile(r"\bsignature:", re.IGNORECASE),
        re.compile(r"-----BEGIN\s+[A-Z\s]+-----"),
        re.compile(r"-----END\s+[A-Z\s]+-----"),
        re.compile(r"\bpubkey:", re.IGNORECASE),
        re.compile(r"\bpublic[_-]?key\b", re.IGNORECASE),
        re.compile(r"\bprivate[_-]?key\b", re.IGNORECASE),
        re.compile(r"\bfingerprint:", re.IGNORECASE),
        re.compile(r"\bkey_epoch\b", re.IGNORECASE),
        re.compile(r"\bverifier\b", re.IGNORECASE),
        re.compile(r"\bssh-rsa\b"),
        re.compile(r"\bssh-ed25519\b"),
        re.compile(r"\becdsa-sha2\b"),
    ],
    BypassClass.BYPASS_PERMISSION: [
        re.compile(r"\bALLOW\b"),
        re.compile(r"\bDENY\b"),
        re.compile(r"\bGRANT\b"),
        re.compile(r"\bREVOKE\b"),
        re.compile(r"\bscope:", re.IGNORECASE),
        re.compile(r"\bprincipal[_-]?id\b", re.IGNORECASE),
        re.compile(r"\bdelegated[_-]?authority\b", re.IGNORECASE),
        re.compile(r"\bpermission[_-]?snapshot\b", re.IGNORECASE),
        re.compile(r"\brepo[_-]?scope\b", re.IGNORECASE),
        re.compile(r"\bfoundup[_-]?scope\b", re.IGNORECASE),
    ],
    BypassClass.BYPASS_RECEIPT: [
        re.compile(r"\breceipt_id:", re.IGNORECASE),
        re.compile(r"\bwork_order_id:", re.IGNORECASE),
        re.compile(r"\bsettled_at:", re.IGNORECASE),
        re.compile(r"\bproof[_-]?of[_-]?compute\b", re.IGNORECASE),
        re.compile(r"\baudit[_-]?chain\b", re.IGNORECASE),
        re.compile(r"\bexecution[_-]?receipt\b", re.IGNORECASE),
        re.compile(r"\bsigned[_-]?receipt\b", re.IGNORECASE),
    ],
}

# Commands that are inherently safe (allowlist)
SAFE_COMMAND_PREFIXES = frozenset([
    "ls",
    "dir",
    "cat",
    "head",
    "tail",
    "wc",
    "echo",
    "pwd",
    "cd",
    "tree",
    "find",
    "npm list",
    "pip list",
    "python --version",
    "node --version",
])

# Commands that always need bypass (denylist)
SENSITIVE_COMMAND_PREFIXES = frozenset([
    "git log",
    "git diff",
    "git show",
    "git blame",
    "security",
    "npm audit",
    "pip audit",
    "safety check",
    "bandit",
    "semgrep",
    "trivy",
    "grype",
    "snyk",
])


@dataclass
class BypassDecision:
    """M2M-formatted bypass classification decision (WSP-99)."""

    # M2M envelope
    m2m_version: str = "1.0"
    sender: str = "0102-BYPASS"
    receiver: str = "0102-ORCH"
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    # Classification result
    classification: BypassClass = BypassClass.NEEDS_HUMAN_REVIEW
    bypassed: bool = True
    bypass_reason: str | None = None

    # Matched patterns (for audit)
    matched_classes: list[BypassClass] = field(default_factory=list)
    matched_patterns: list[str] = field(default_factory=list)

    # Input context (no raw content stored)
    command_hash: str = ""
    output_length: int = 0
    output_hash: str = ""

    # Confidence
    confidence: float = 1.0

    def to_m2m_compact(self) -> str:
        """Serialize to M2M compact format (WSP-99 Section 2.1)."""
        parts = [
            f"L:BYPASS",
            f"S:{self.classification.value}",
            f"M:classify",
            f"T:{self.command_hash[:8] if self.command_hash else 'unknown'}",
            f"R:[97,99]",
        ]
        if self.bypassed:
            parts.append(f"I:{{bypassed:true,reason:{self.bypass_reason or 'default'}}}")
        else:
            parts.append("I:{bypassed:false}")
        parts.append(f"O:[{self.classification.value}]")
        return " ".join(parts)

    def to_m2m_yaml(self) -> str:
        """Serialize to M2M YAML format (WSP-99 Section 2.1)."""
        lines = [
            f"M2M_VERSION: {self.m2m_version}",
            f"SENDER: {self.sender}",
            f"RECEIVER: {self.receiver}",
            f"TS: {self.timestamp}",
            "",
            "CLASSIFICATION:",
            f"  CLASS: {self.classification.value}",
            f"  BYPASSED: {str(self.bypassed).lower()}",
        ]
        if self.bypass_reason:
            lines.append(f"  REASON: {self.bypass_reason}")
        if self.matched_classes:
            classes = ", ".join(c.value for c in self.matched_classes)
            lines.append(f"  MATCHED_CLASSES: [{classes}]")
        lines.extend([
            "",
            "CONTEXT:",
            f"  COMMAND_HASH: {self.command_hash}",
            f"  OUTPUT_LENGTH: {self.output_length}",
            f"  OUTPUT_HASH: {self.output_hash}",
            f"  CONFIDENCE: {self.confidence}",
        ])
        return "\n".join(lines)

    def as_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "m2m_version": self.m2m_version,
            "sender": self.sender,
            "receiver": self.receiver,
            "timestamp": self.timestamp,
            "classification": self.classification.value,
            "bypassed": self.bypassed,
            "bypass_reason": self.bypass_reason,
            "matched_classes": [c.value for c in self.matched_classes],
            "matched_patterns": self.matched_patterns,
            "command_hash": self.command_hash,
            "output_length": self.output_length,
            "output_hash": self.output_hash,
            "confidence": self.confidence,
        }


class BypassClassifier:
    """Classifier for token-efficiency bypass decisions (Contract Section 6b).

    Determines if command output should bypass compression.
    Fail-closed: if classification fails, default to bypass.

    Output format: WSP-99 M2M.
    """

    def __init__(self) -> None:
        self.patterns = BYPASS_PATTERNS
        self.safe_commands = SAFE_COMMAND_PREFIXES
        self.sensitive_commands = SENSITIVE_COMMAND_PREFIXES

    def classify(
        self,
        command: str,
        output: str,
        *,
        command_hash: str = "",
        output_hash: str = "",
    ) -> BypassDecision:
        """Classify command output for bypass decision.

        Args:
            command: The executed command string
            output: The command output (stdout/stderr)
            command_hash: Pre-computed hash of command (optional)
            output_hash: Pre-computed hash of output (optional)

        Returns:
            BypassDecision in M2M format
        """
        decision = BypassDecision(
            command_hash=command_hash or self._hash(command),
            output_length=len(output),
            output_hash=output_hash or self._hash(output),
        )

        command_lower = command.lower().strip()

        # Check output content FIRST - content patterns take priority
        # This ensures sensitive output is detected even from "safe" commands
        matched_classes: list[BypassClass] = []
        matched_patterns: list[str] = []

        for bypass_class, patterns in self.patterns.items():
            for pattern in patterns:
                if pattern.search(output):
                    matched_classes.append(bypass_class)
                    matched_patterns.append(pattern.pattern)
                    break  # One match per class is enough

        if matched_classes:
            # Multiple matches -> use highest priority
            priority_order = [
                BypassClass.BYPASS_SECURITY,
                BypassClass.BYPASS_AUTH,
                BypassClass.BYPASS_SIGNING,
                BypassClass.BYPASS_PERMISSION,
                BypassClass.BYPASS_RECEIPT,
                BypassClass.BYPASS_PROVENANCE,
            ]
            for pclass in priority_order:
                if pclass in matched_classes:
                    decision.classification = pclass
                    break
            else:
                decision.classification = matched_classes[0]

            decision.bypassed = True
            decision.bypass_reason = f"pattern_match:{decision.classification.value}"
            decision.matched_classes = matched_classes
            decision.matched_patterns = matched_patterns
            decision.confidence = 0.95 if len(matched_classes) == 1 else 0.99
            return decision

        # No output patterns found - check command-level classification
        # Sensitive command prefix -> bypass with provenance
        for prefix in self.sensitive_commands:
            if command_lower.startswith(prefix):
                decision.classification = BypassClass.BYPASS_PROVENANCE
                decision.bypassed = True
                decision.bypass_reason = f"sensitive_command:{prefix}"
                decision.confidence = 1.0
                return decision

        # Safe command prefix -> allow compression
        for prefix in self.safe_commands:
            if command_lower.startswith(prefix):
                decision.classification = BypassClass.ALLOW_COMPRESSION
                decision.bypassed = False
                decision.bypass_reason = None
                decision.confidence = 0.9
                return decision

        # Unknown command with no bypass patterns -> needs human review
        decision.classification = BypassClass.NEEDS_HUMAN_REVIEW
        decision.bypassed = True  # Fail-closed
        decision.bypass_reason = "unknown_command"
        decision.confidence = 0.5
        return decision

    def should_bypass(self, content: str) -> tuple[bool, str | None]:
        """Check if content should bypass compression (Contract Section 6b).

        Returns:
            (True, class_name) if content matches a bypass class
            (False, None) if compression is allowed
            (True, "CLASSIFICATION_ERROR") if classification fails
        """
        try:
            for bypass_class, patterns in self.patterns.items():
                for pattern in patterns:
                    if pattern.search(content):
                        return True, bypass_class.value
            return False, None
        except Exception:
            return True, "CLASSIFICATION_ERROR"

    def get_matched_classes(self, content: str) -> list[BypassClass]:
        """Return all bypass classes that match the content."""
        matched = []
        for bypass_class, patterns in self.patterns.items():
            for pattern in patterns:
                if pattern.search(content):
                    matched.append(bypass_class)
                    break
        return matched

    @staticmethod
    def _hash(content: str) -> str:
        """Generate content hash (SHA256 prefix)."""
        import hashlib
        return hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()[:16]


# Module-level singleton
_classifier: BypassClassifier | None = None


def get_bypass_classifier() -> BypassClassifier:
    """Get or create the bypass classifier singleton."""
    global _classifier
    if _classifier is None:
        _classifier = BypassClassifier()
    return _classifier
