"""
dns_ops policy engine — extracted for testability.

Domain allowlist, record-type allowlist, approval gate.
All fail-closed: empty allowlist = deny all.
"""

import json
import os
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


def env_truthy(key: str, default: str = "0") -> bool:
    return os.getenv(key, default).strip().lower() in ("1", "true", "yes")


def env_set(key: str, default: str = "") -> Set[str]:
    raw = os.getenv(key, default).strip()
    if not raw:
        return set()
    return {v.strip().lower() for v in raw.split(",") if v.strip()}


def extract_base_domain(domain: str) -> str:
    """Extract registrable domain: www.foundups.com -> foundups.com"""
    parts = domain.lower().strip(".").split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return domain.lower()


def check_domain_policy(domain: str, allowed: Set[str]) -> Tuple[bool, str]:
    """Check if domain is in allowlist. Fail-closed: empty set = deny all."""
    base = extract_base_domain(domain)
    if not allowed:
        return False, "DNS_OPS_ALLOWED_DOMAINS is empty — fail-closed: all domains denied"
    if base in allowed:
        return True, f"domain {base} in allowlist"
    return False, f"domain {base} not in allowlist {allowed}"


def check_record_type_policy(record_type: str, allowed: Set[str]) -> Tuple[bool, str]:
    """Check if record type is in allowlist."""
    rt = record_type.strip().lower()
    if rt in allowed:
        return True, f"record type {rt.upper()} allowed"
    return False, f"record type {rt.upper()} not in allowlist {allowed}"


class ApprovalGate:
    """Queue write operations for 012 approval.

    Agents submit proposed changes. 012 approves/denies via CLI.
    Agents cannot approve their own submissions.
    """

    def __init__(self, queue_path: Path):
        self.queue_path = queue_path

    def submit(self, proposed_change: Dict[str, Any]) -> str:
        """Write proposed change to approval queue. Returns approval_id."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        name = proposed_change.get("name", "unknown")
        rtype = proposed_change.get("record_type", "UNK")
        action = proposed_change.get("action", "change")
        approval_id = f"dns_{action}_{ts}_{name}_{rtype}"

        entry = {
            "approval_id": approval_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
            "proposed_change": proposed_change,
            "submitted_by": "mcp_agent",
        }
        with open(self.queue_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str, ensure_ascii=False) + "\n")

        return approval_id

    def list_pending(self) -> List[Dict[str, Any]]:
        """List all pending approvals."""
        if not self.queue_path.exists():
            return []
        pending = []
        for line in self.queue_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("status") == "pending":
                pending.append(entry)
        return pending

    def get_entry(self, approval_id: str) -> Optional[Dict[str, Any]]:
        """Find a specific approval entry."""
        if not self.queue_path.exists():
            return None
        for line in self.queue_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("approval_id") == approval_id:
                return entry
        return None

    def update_status(self, approval_id: str, status: str,
                      reason: Optional[str] = None) -> bool:
        """Update status of an approval entry. Returns True if found and updated."""
        if not self.queue_path.exists():
            return False

        lines = self.queue_path.read_text(encoding="utf-8").splitlines()
        updated = False
        new_lines = []

        for line in lines:
            if not line.strip():
                new_lines.append(line)
                continue
            entry = json.loads(line)
            if entry.get("approval_id") == approval_id:
                entry["status"] = status
                entry["resolved_at"] = datetime.now(timezone.utc).isoformat()
                entry["resolved_by"] = "012_operator"
                if reason:
                    entry["reason"] = reason
                updated = True
            new_lines.append(json.dumps(entry, default=str, ensure_ascii=False))

        if updated:
            self.queue_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        return updated
