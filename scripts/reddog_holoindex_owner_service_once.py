"""Manifest-authenticated entry point for the private Holo query owner."""

from __future__ import annotations

from modules.infrastructure.foundups_mcp_bridge.src.holo_query_service import main


if __name__ == "__main__":
    raise SystemExit(main())
