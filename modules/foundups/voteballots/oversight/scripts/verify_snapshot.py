"""Verify the public Oversight source inventory without changing files."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath


def safe_relative(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or ":" in value:
        raise ValueError("Snapshot contains an invalid relative path")
    return path


def forbidden_source_path(path: PurePosixPath) -> bool:
    parts = [part.lower() for part in path.parts]
    if any(part in {".git", "credentials", "secrets"} or part == ".env" or part.startswith(".env.") for part in parts):
        return True
    name = parts[-1]
    return (
        path.suffix.lower() in {".pem", ".key", ".pfx", ".p12", ".jks", ".keystore", ".kdbx"}
        or name.startswith(("client_secret", "oauth_token"))
    )


def git(checkout: Path, *args: str) -> bytes:
    return subprocess.check_output(
        ["git", "-C", str(checkout), *args], stderr=subprocess.DEVNULL
    )


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def verify(source_checkout: Path | None = None) -> dict:
    workstream = Path(__file__).resolve().parents[1]
    site = workstream / "site"
    manifest = json.loads((workstream / "source-snapshot.json").read_text("utf-8"))
    entries = manifest["files"]
    paths = [entry["source_path"] for entry in entries]
    errors: list[str] = []
    if paths != sorted(set(paths)) or len(entries) != manifest["file_count"]:
        errors.append("Manifest inventory must be unique, sorted and complete")

    actual = sorted(p.relative_to(site).as_posix() for p in site.rglob("*") if p.is_file())
    if actual != paths:
        errors.append("Export file inventory differs from the manifest")

    source_tree = None
    if source_checkout is not None:
        source_checkout = source_checkout.resolve()
        head = git(source_checkout, "rev-parse", "HEAD").decode().strip()
        if head != manifest["source"]["snapshot_commit"]:
            errors.append("Source checkout HEAD differs from the pinned snapshot")
        tracked = sorted(filter(None, git(source_checkout, "ls-files", "-z").decode().split("\0")))
        if tracked != paths:
            errors.append("Source tracked-file inventory differs from the manifest")
        source_tree = {}
        for row in git(source_checkout, "ls-tree", "-r", "-z", "--full-tree", "HEAD").decode().split("\0"):
            if not row:
                continue
            metadata, name = row.split("\t", 1)
            mode, kind, blob = metadata.split()
            if kind != "blob":
                errors.append("Source tree entry is not a file: " + name)
            source_tree[name] = (mode, blob)
        if sorted(source_tree) != paths:
            errors.append("Source HEAD tree inventory differs from the manifest")
        if git(source_checkout, "status", "--porcelain").strip():
            errors.append("Source checkout has uncommitted or untracked changes")

    total_bytes = 0
    mirror_pairs = 0
    for entry in entries:
        source_path = safe_relative(entry["source_path"])
        if forbidden_source_path(source_path):
            errors.append("Forbidden private source path: " + source_path.as_posix())
            continue
        recorded_blob = entry["source_git_blob_sha1"]
        recorded_mode = entry["git_mode"]
        if not isinstance(recorded_blob, str) or not re.fullmatch(r"[0-9a-f]{40}", recorded_blob):
            errors.append("Invalid source Git blob ID: " + source_path.as_posix())
        if recorded_mode not in ("100644", "100755"):
            errors.append("Invalid source Git file mode: " + source_path.as_posix())
        if source_tree is not None and source_tree.get(source_path.as_posix()) != (recorded_mode, recorded_blob):
            errors.append("Source HEAD blob/mode metadata differs: " + source_path.as_posix())
        expected_export = "site/" + source_path.as_posix()
        if entry["export_path"] != expected_export:
            errors.append("Invalid export mapping: " + source_path.as_posix())
            continue
        target = workstream.joinpath(*safe_relative(expected_export).parts)
        if target.is_symlink() or not target.resolve().is_relative_to(site.resolve()):
            errors.append("Export path escapes its source tree: " + source_path.as_posix())
            continue
        if not target.is_file():
            errors.append("Missing export: " + source_path.as_posix())
            continue
        data = target.read_bytes()
        total_bytes += len(data)
        if len(data) != entry["size_bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
            errors.append("Export bytes changed: " + source_path.as_posix())
        if recorded_blob not in (git_blob_sha1(data), git_blob_sha1(data.replace(b"\r\n", b"\n"))):
            errors.append("Source Git blob cannot be derived from export bytes: " + source_path.as_posix())
        if source_checkout is not None:
            original = source_checkout.joinpath(*source_path.parts)
            if not original.is_file() or original.is_symlink() or original.read_bytes() != data:
                errors.append("Source/export byte mismatch: " + source_path.as_posix())
        if source_path.parts[:2] == ("dist", "web"):
            root_copy = site / "dist" / Path(*source_path.parts[2:])
            if root_copy.is_file():
                mirror_pairs += 1
                if root_copy.read_bytes() != data:
                    errors.append("Root/web mirror mismatch: " + source_path.as_posix())

    inventory = "".join(e["sha256"] + "  " + e["source_path"] + "\n" for e in entries).encode()
    digest = hashlib.sha256(inventory).hexdigest()
    if digest != manifest["inventory_sha256"]:
        errors.append("Manifest inventory digest differs")
    if total_bytes != manifest["total_size_bytes"]:
        errors.append("Export byte count differs")
    return {
        "ok": not errors,
        "file_count": len(entries),
        "total_size_bytes": total_bytes,
        "inventory_sha256": digest,
        "root_web_mirror_pairs": mirror_pairs,
        "source_checkout_compared": source_checkout is not None,
        "source_head_blob_modes_compared": source_tree is not None,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-checkout", type=Path)
    args = parser.parse_args()
    try:
        result = verify(args.source_checkout)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        result = {"ok": False, "error_type": type(error).__name__}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
