"""
dns_ops approval CLI — 012 operator interface.

This CLI is NOT called by agents. 012 runs it directly to approve/deny
queued DNS mutations.

Usage:
    python approve.py --list
    python approve.py --approve <approval_id>
    python approve.py --deny <approval_id> --reason "not ready"
"""

import argparse
import json
import sys
from pathlib import Path

_SERVER_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SERVER_DIR))

from policy import ApprovalGate

QUEUE_PATH = _SERVER_DIR / "approval_queue.jsonl"


def main():
    parser = argparse.ArgumentParser(description="dns_ops approval queue — 012 operator CLI")
    parser.add_argument("--list", action="store_true", help="List pending approvals")
    parser.add_argument("--approve", type=str, metavar="ID", help="Approve a pending change")
    parser.add_argument("--deny", type=str, metavar="ID", help="Deny a pending change")
    parser.add_argument("--reason", type=str, default="", help="Reason for denial")
    parser.add_argument("--show", type=str, metavar="ID", help="Show details of a specific entry")
    args = parser.parse_args()

    gate = ApprovalGate(QUEUE_PATH)

    if args.list:
        pending = gate.list_pending()
        if not pending:
            print("[OK] No pending approvals.")
            return
        print(f"\n[PENDING] {len(pending)} approval(s):\n")
        for entry in pending:
            change = entry.get("proposed_change", {})
            print(f"  ID:     {entry['approval_id']}")
            print(f"  Action: {change.get('action', '?').upper()}")
            print(f"  Domain: {change.get('domain', '?')}")
            print(f"  Name:   {change.get('name', '?')}")
            print(f"  Type:   {change.get('record_type', '?')}")
            print(f"  Value:  {change.get('value', '(none)')}")
            print(f"  TTL:    {change.get('ttl', '?')}")
            print(f"  Time:   {entry.get('timestamp', '?')}")
            print()

    elif args.show:
        entry = gate.get_entry(args.show)
        if not entry:
            print(f"[ERROR] Approval ID not found: {args.show}")
            sys.exit(1)
        print(json.dumps(entry, indent=2, default=str))

    elif args.approve:
        entry = gate.get_entry(args.approve)
        if not entry:
            print(f"[ERROR] Approval ID not found: {args.approve}")
            sys.exit(1)
        if entry.get("status") != "pending":
            print(f"[ERROR] Entry is not pending (status={entry.get('status')})")
            sys.exit(1)

        change = entry.get("proposed_change", {})
        print(f"\n[APPROVE] About to approve:")
        print(f"  Action: {change.get('action', '?').upper()}")
        print(f"  Domain: {change.get('domain', '?')}")
        print(f"  Name:   {change.get('name', '?')}")
        print(f"  Type:   {change.get('record_type', '?')}")
        print(f"  Value:  {change.get('value', '(none)')}")

        confirm = input("\nType YES to confirm: ").strip()
        if confirm != "YES":
            print("[CANCELLED] Not approved.")
            return

        gate.update_status(args.approve, "approved")
        print(f"[OK] Approved: {args.approve}")
        print("[NOTE] Provider execution (GoDaddy API call) available in Phase 2.")

    elif args.deny:
        entry = gate.get_entry(args.deny)
        if not entry:
            print(f"[ERROR] Approval ID not found: {args.deny}")
            sys.exit(1)
        reason = args.reason or "denied by 012"
        gate.update_status(args.deny, "denied", reason=reason)
        print(f"[OK] Denied: {args.deny} (reason: {reason})")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
