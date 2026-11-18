"""Apply the reviewed aioresponses backport only in a disposable test runtime.

This is a local overlay on the released 0.7.9 wheel, not an upstream release.
The two runtime changes are from pnuckowski/aioresponses PR #292, commit
1a48e1f898035e3bedc981f06520842c55977706. See ../security/AIORESPONSES_COMPAT.md
for the MIT notice, evidence boundary, and removal condition.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import sys


SUPPORTED = {"aioresponses": "0.7.9", "aiohttp": "3.14.5"}
UPSTREAM_COMMIT = "1a48e1f898035e3bedc981f06520842c55977706"
WHEEL_SHA256 = "94f9617f841c5bd7ee088ed783284f2cf4e6acc85d3933d92fc2fc7bd572a1b0"
SPECS = {
    "core.py": {
        "before": "11d1772f0df21e940b4b536dc216f1de44a1d3d51a242e2379402739e5b9a815",
        "after": "bea51a1263e7559c38630f28055b3db546ec9ccf5d9e020704d400c91293fa29",
        "replacements": [
            (
                "        kwargs['writer'] = None\n",
                "        if 'stream_writer' in inspect.signature(response_class).parameters:\n"
                "            kwargs['stream_writer'] = Mock(output_size=0)\n"
                "        kwargs['writer'] = None\n",
            ),
        ],
    },
    "compat.py": {
        "before": "7f539c3860aeb858216aff8d0103d8ca51fc2d1301032c1f43c5b80393bda441",
        "after": "4b67252efbba5f1bc200c70d31462055435730c24b162ddeeb9877433f6b645b",
        "replacements": [
            (
                "from typing import Dict, Optional, Union  # noqa\n",
                "from typing import Dict, Optional, Union  # noqa\n"
                "from unittest.mock import Mock\n",
            ),
            (
                "    protocol = ResponseHandler(loop=loop)\n",
                "    protocol = ResponseHandler(loop=loop)\n"
                "    # Satisfies BaseProtocol's flow control hooks that\n"
                "    # fire when a large payload exceeds the StreamReader limit.\n"
                "    protocol._parser = Mock()\n"
                "    protocol._parser.feed_data.return_value = ([], False, b'')\n",
            ),
        ],
    },
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def installed_target() -> tuple[Path, dict[str, str]]:
    versions = {name: metadata.version(name) for name in SUPPORTED}
    if versions != SUPPORTED:
        raise RuntimeError(f"Unqualified dependency versions: {versions!r}")
    root = Path(metadata.distribution("aioresponses").locate_file("aioresponses"))
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError("Expected a regular installed aioresponses directory")
    root = root.resolve(strict=True)
    if not root.is_relative_to(Path(sys.prefix).resolve(strict=True)):
        raise RuntimeError("aioresponses is outside the selected interpreter prefix")
    return root, versions


def prepare(root: Path) -> list[tuple[Path, bytes]]:
    """Validate both original files and both final hashes before any write."""
    prepared = []
    for name, spec in SPECS.items():
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"Expected a regular source file: {name}")
        original = path.read_bytes()
        if digest(original) != spec["before"]:
            raise RuntimeError(f"Unqualified or already patched source: {name}")
        updated = original.decode("utf-8")
        for old, new in spec["replacements"]:
            if updated.count(old) != 1:
                raise RuntimeError(f"Non-unique backport anchor: {name}")
            updated = updated.replace(old, new)
        result = updated.encode("utf-8")
        if digest(result) != spec["after"]:
            raise RuntimeError(f"Backport differs from reviewed upstream source: {name}")
        prepared.append((path, result))
    return prepared


def apply_backport(receipt_path: Path) -> dict:
    root, versions = installed_target()
    if receipt_path.exists() or receipt_path.resolve().is_relative_to(root):
        raise RuntimeError("Receipt must be a new file outside the installed package")
    prepared = prepare(root)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    for path, result in prepared:
        path.write_bytes(result)
    if any(digest(path.read_bytes()) != SPECS[path.name]["after"] for path, _ in prepared):
        raise RuntimeError("Installed backport verification failed")
    receipt = {
        "scope": "Ephemeral CI test-tool overlay; application and aiohttp source unchanged",
        "versions": versions,
        "python": sys.version.split()[0],
        "interpreter": sys.executable,
        "helper_sha256": digest(Path(__file__).read_bytes()),
        "upstream_commit": UPSTREAM_COMMIT,
        "released_wheel_sha256": WHEEL_SHA256,
        "files": [{"path": str(path), "before_sha256": SPECS[path.name]["before"],
                   "after_sha256": SPECS[path.name]["after"]} for path, _ in prepared],
        "stock_distribution_record": "Retained; this separate receipt records the local overlay",
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = apply_backport(args.receipt)
    except (OSError, RuntimeError, metadata.PackageNotFoundError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
