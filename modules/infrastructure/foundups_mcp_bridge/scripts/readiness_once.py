"""One bounded official-client readiness probe for the loopback MCP server."""

from __future__ import annotations

import argparse
import json
import logging
import os

from .launch import verify_mcp_readiness


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--timeout", required=True, type=float)
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    result = verify_mcp_readiness(
        args.host, args.port,
        auth_token=os.getenv("FOUNDUPS_MCP_AUTH_TOKEN", ""),
        timeout_sec=max(1.0, min(args.timeout, 30.0)),
    )
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
