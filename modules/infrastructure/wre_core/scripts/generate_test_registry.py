"""Generate or verify the canonical Git-tracked Python test registry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.infrastructure.wre_core.src.wre_test_registry import (  # noqa: E402
    MAX_FILES_PER_SHARD,
    REGISTRY_PATH,
    registry_payload,
)
from modules.infrastructure.wre_core.src.wre_test_registry_classification import (  # noqa: E402
    classify_test_file,
    shard_slug,
)


def tracked_test_paths(repo_root: Path) -> tuple[str, ...]:
    """Return every tracked Python ``test_*`` file in canonical order."""
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=repo_root, capture_output=True,
        check=True, timeout=60,
    )
    decoded = result.stdout.decode("utf-8", errors="strict")
    paths = []
    for value in decoded.split("\0"):
        path = PurePosixPath(value)
        if value and path.name.startswith("test_") and path.suffix == ".py":
            paths.append(path.as_posix())
    return tuple(sorted(paths))


def build_registry(repo_root: Path) -> dict[str, Any]:
    """Build deterministic registry content from tracked source."""
    entries = []
    for path in tracked_test_paths(repo_root):
        classified = classify_test_file(repo_root, path)
        entries.append({
            "id": "test::" + path.removesuffix(".py").replace("/", "::"),
            "path": path,
            "owner": classified.owner,
            "suite_class": classified.suite_class,
            "shard_id": shard_slug(classified.owner, classified.suite_class),
            "capabilities": list(classified.capabilities),
            "execution_type": classified.suite_class,
            "collectable": classified.collectable,
            "timeout_s": _timeout(classified.suite_class),
            "quarantine_reasons": list(classified.quarantine_reasons),
            "description": classified.description,
        })
    _assign_shards(entries)
    return registry_payload(entries)


def _assign_shards(entries: list[dict[str, Any]]) -> None:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for entry in entries:
        if entry["collectable"]:
            grouped.setdefault(
                (entry["owner"], entry["suite_class"]), []
            ).append(entry)
    for (owner, suite_class), rows in sorted(grouped.items()):
        ordered = sorted(rows, key=lambda item: item["path"])
        count = (len(ordered) + MAX_FILES_PER_SHARD - 1) // MAX_FILES_PER_SHARD
        base = shard_slug(owner, suite_class)
        for index, row in enumerate(ordered):
            part = index // MAX_FILES_PER_SHARD + 1
            row["shard_id"] = base if count == 1 else f"{base}-part-{part:02d}"


def canonical_bytes(payload: dict[str, Any]) -> bytes:
    text = json.dumps(payload, indent=2, ensure_ascii=True, allow_nan=False)
    return (text + "\n").encode("ascii")


def write_registry(repo_root: Path, payload: dict[str, Any]) -> None:
    target = repo_root / REGISTRY_PATH
    data = canonical_bytes(payload)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = ""
    try:
        with tempfile.NamedTemporaryFile(
            dir=target.parent, prefix=".test-registry-", suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = handle.name
            handle.write(data)
            handle.flush()
        Path(temporary).replace(target)
    finally:
        if temporary and Path(temporary).exists():
            Path(temporary).unlink()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    payload = build_registry(REPO_ROOT)
    expected = canonical_bytes(payload)
    target = REPO_ROOT / REGISTRY_PATH
    if args.write:
        write_registry(REPO_ROOT, payload)
        print(_summary(payload, "written"))
        return 0
    if not target.is_file() or target.read_bytes() != expected:
        print(_summary(payload, "stale"), file=sys.stderr)
        return 1
    print(_summary(payload, "current"))
    return 0


def _timeout(suite_class: str) -> int:
    return {"unit": 180, "integration": 600}.get(suite_class, 900)


def _summary(payload: dict[str, Any], status: str) -> str:
    return (
        f"test_registry={status} total={payload['total_tests']} "
        f"quarantined={payload['quarantined_tests']}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
