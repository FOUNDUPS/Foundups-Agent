#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Member Mall catalog exporter — generates public/member/mall-catalog.json
from canonical p.fMALL manifest/tile truth + presentation overrides.

Usage:
    python -m modules.foundups.pfmall.member_catalog_export

This replaces hand-maintained catalog duplication with a single
generated artifact. The Firebase Mall remains static-hostable;
it just consumes a generated file instead of a hand-edited one.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

from modules.foundups.pfmall.api import get_default_shell, list_foundups, reset_default_shell
from modules.foundups.pfmall.member_presentation import get_presentation

logger = logging.getLogger("pfmall_export")

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_PATH = _REPO_ROOT / "public" / "member" / "mall-catalog.json"

# Fields from the tile that the member Mall consumes.
_TILE_FIELDS = [
    "foundup_id",
    "name",
    "tagline",
    "description",
    "category",
    "tier",
    "lifecycle_stage",
    "launch_readiness",
    "token_symbol",
    "routing_prefix",
]


def build_mall_catalog(shell=None) -> List[Dict[str, Any]]:
    """Build the member Mall catalog from canonical pfmall truth.

    Returns a list of dicts matching the shape consumed by
    public/member/index.html: tile fields + presentation overrides.
    """
    tiles = list_foundups(shell=shell)
    catalog = []
    for tile in tiles:
        entry: Dict[str, Any] = {}
        for field in _TILE_FIELDS:
            entry[field] = tile.get(field, "")
        # Merge presentation overrides
        presentation = get_presentation(tile["foundup_id"])
        entry.update(presentation)
        catalog.append(entry)
    return catalog


def export_mall_catalog(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    shell=None,
) -> Path:
    """Generate and write mall-catalog.json.

    Args:
        output_path: Where to write the JSON file.
        shell: Optional PfmallShell instance (uses default if None).

    Returns:
        Path to the written file.
    """
    catalog = build_mall_catalog(shell=shell)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
        f.write("\n")
    logger.info(
        "[PFMALL-EXPORT] Wrote %d entries to %s",
        len(catalog),
        output_path,
    )
    return output_path


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    path = export_mall_catalog()
    print(f"Generated {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
