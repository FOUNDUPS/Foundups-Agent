#!/usr/bin/env python3
"""
Refresh the OpenClaw external ecosystem watchlist against official-source URLs.

This tracks external agent-infrastructure systems that may influence OpenClaw
architecture decisions without becoming default runtime dependencies.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.request import HTTPRedirectHandler, Request, build_opener

from modules.infrastructure.dependency_launcher.src.runtime_compatibility_evidence_supplier import (
    OFFICIAL_RELEASE_APIS,
    compose_runtime_compatibility_evidence,
    load_runtime_compatibility_supply,
    publish_runtime_compatibility_evidence,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)

try:
    from scripts.refresh_grant_watchlist import (
        REPO_ROOT,
        build_status_report,
        refresh_item,
        utc_now_iso,
    )
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from refresh_grant_watchlist import (
        REPO_ROOT,
        build_status_report,
        refresh_item,
        utc_now_iso,
    )


WATCHLIST_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "workspace"
    / "reports"
    / "openclaw_external_ecosystem_watchlist.json"
)
STATUS_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "workspace"
    / "reports"
    / "openclaw_external_ecosystem_watchlist_status.json"
)
MAX_RELEASE_BYTES = 1024 * 1024
RELEASE_USER_AGENT = "FoundUps-WRE-RuntimeCompatibility/1.0"


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


def _open_release(request: Request, *, timeout: int):
    return build_opener(_RejectRedirects()).open(request, timeout=timeout)


def fetch_official_release(
    component_id: str,
    *,
    opener: Callable[..., Any] = _open_release,
    timeout: int = 20,
) -> dict[str, Any]:
    """Fetch one allowlisted GitHub latest-release document with a byte cap."""
    endpoint = OFFICIAL_RELEASE_APIS.get(component_id)
    if endpoint is None:
        raise ValueError("release_component_not_allowlisted")
    request = Request(
        endpoint,
        headers={"Accept": "application/vnd.github+json", "User-Agent": RELEASE_USER_AGENT},
    )
    with opener(request, timeout=timeout) as response:
        if str(response.geturl()) != endpoint:
            raise ValueError("release_endpoint_redirected")
        body = response.read(MAX_RELEASE_BYTES + 1)
        if len(body) > MAX_RELEASE_BYTES:
            raise ValueError("release_payload_too_large")
    payload = json.loads(body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("release_payload_not_mapping")
    return payload


def publish_compatibility_evidence(
    *,
    repo_root: Path,
    runtime_root: Path,
    supply_path: Path,
    output_path: Path,
    fetcher: Callable[[str], Mapping[str, Any]] = fetch_official_release,
) -> Path:
    """Compose and atomically publish startup-compatible cached evidence."""
    root = validate_runtime_root_path(runtime_root, repo_root=repo_root)
    supply = validate_runtime_artifact_path(
        supply_path, repo_root=repo_root, allowed_root=root
    )
    output = validate_runtime_artifact_path(
        output_path, repo_root=repo_root, allowed_root=root
    )
    if os.path.normcase(str(supply)) == os.path.normcase(str(output)):
        raise ValueError("runtime_compatibility_supply_output_alias")
    supply = load_runtime_compatibility_supply(
        repo_root,
        runtime_root=root,
        supply_path=supply,
    )
    releases = {component_id: dict(fetcher(component_id)) for component_id in OFFICIAL_RELEASE_APIS}
    evidence = compose_runtime_compatibility_evidence(supply, upstream_releases=releases)
    return publish_runtime_compatibility_evidence(
        evidence,
        repo_root=repo_root,
        runtime_root=root,
        output_path=output,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh the OpenClaw external ecosystem watchlist."
    )
    parser.add_argument(
        "--watchlist",
        type=Path,
        default=WATCHLIST_PATH,
        help="Path to the watchlist JSON",
    )
    parser.add_argument(
        "--status-out",
        type=Path,
        default=STATUS_PATH,
        help="Path to write status snapshot JSON",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional limit on number of watchlist items to refresh",
    )
    parser.add_argument(
        "--compatibility-root",
        type=Path,
        default=None,
        help="Off-repo runtime root for the optional compatibility evidence supply",
    )
    parser.add_argument(
        "--compatibility-supply",
        type=Path,
        default=None,
        help="Off-repo WRE inventory/promotion supply receipt",
    )
    parser.add_argument(
        "--compatibility-out",
        type=Path,
        default=None,
        help="Off-repo evidence cache consumed by main.py startup",
    )
    return parser.parse_args()


def _refresh_watchlist(args: argparse.Namespace) -> bool:
    watchlist_path = args.watchlist
    if not watchlist_path.exists():
        print(f"[FAIL] Watchlist not found: {watchlist_path}")
        return False

    watchlist = json.loads(watchlist_path.read_text(encoding="utf-8"))
    items = watchlist.get("items", [])
    target_items = items[: args.limit] if args.limit > 0 else items

    for item in target_items:
        refresh_item(item)

    watchlist["last_full_refresh_attempt"] = utc_now_iso()
    watchlist_path.write_text(
        json.dumps(watchlist, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    status_report = build_status_report(watchlist)
    status_report["watch_type"] = "openclaw_external_ecosystem"
    args.status_out.write_text(
        json.dumps(status_report, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    print(f"[OK] Refreshed {len(target_items)} watchlist item(s)")
    print(f"[OK] Status written to {args.status_out}")
    print(f"[OK] Changed items: {status_report['changed_count']}")
    print(f"[OK] Error items: {status_report['error_count']}")
    return True


def _publish_optional_compatibility(args: argparse.Namespace) -> bool:
    try:
        compatibility = _compatibility_paths(args)
    except ValueError as exc:
        print(f"[FAIL] Runtime compatibility evidence not published: {exc}")
        return False
    if compatibility is None:
        return True
    try:
        output = publish_compatibility_evidence(
            repo_root=REPO_ROOT,
            runtime_root=compatibility[0],
            supply_path=compatibility[1],
            output_path=compatibility[2],
        )
        print(f"[OK] Runtime compatibility evidence written to {output}")
        return True
    except Exception as exc:
        print(f"[FAIL] Runtime compatibility evidence not published: {type(exc).__name__}")
        return False


def main() -> int:
    args = _parse_args()
    if not _refresh_watchlist(args):
        return 1
    return 0 if _publish_optional_compatibility(args) else 1


def _compatibility_paths(args: argparse.Namespace) -> tuple[Path, Path, Path] | None:
    values = (
        args.compatibility_root or _env_path("REDDOG_RUNTIME_COMPATIBILITY_ROOT"),
        args.compatibility_supply or _env_path("REDDOG_RUNTIME_COMPATIBILITY_SUPPLY"),
        args.compatibility_out or _env_path("REDDOG_RUNTIME_COMPATIBILITY_EVIDENCE"),
    )
    if not any(values):
        return None
    if not all(values):
        raise ValueError("runtime_compatibility_configuration_incomplete")
    root, supply, output = values
    assert root is not None and supply is not None and output is not None
    return root, supply, output


def _env_path(name: str) -> Path | None:
    value = str(os.getenv(name) or "").strip()
    return Path(value) if value else None


if __name__ == "__main__":
    sys.exit(main())
