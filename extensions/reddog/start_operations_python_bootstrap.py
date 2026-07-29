"""Execute RedDog control code from manifest-authenticated source bytes."""

from __future__ import annotations

import hashlib
import importlib.abc
import importlib.machinery
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


def _canonical_digest(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _relative_source(path: Path, source_root: Path) -> str:
    try:
        return path.resolve().relative_to(source_root).as_posix()
    except ValueError as exc:
        raise ImportError("runtime_source_outside_sealed_root") from exc


def _verified_bytes(
    path: Path,
    source_root: Path,
    digests: dict[str, str],
) -> bytes:
    relative = _relative_source(path, source_root)
    expected = digests.get(relative)
    if not expected:
        raise ImportError("runtime_source_not_manifest_bound")
    raw = path.read_bytes()
    observed = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
    if observed != expected:
        raise ImportError("runtime_source_digest_mismatch")
    return raw


class _VerifiedSourceLoader(importlib.machinery.SourceFileLoader):
    def __init__(
        self,
        name: str,
        path: str,
        source_root: Path,
        digests: dict[str, str],
    ) -> None:
        super().__init__(name, path)
        self._source_root = source_root
        self._digests = digests

    def get_code(self, fullname: str) -> Any:
        raw = _verified_bytes(Path(self.path), self._source_root, self._digests)
        return compile(raw, self.path, "exec")


class _VerifiedSourceFinder(importlib.abc.MetaPathFinder):
    def __init__(self, source_root: Path, digests: dict[str, str]) -> None:
        self._source_root = source_root
        self._digests = digests

    def find_spec(
        self,
        fullname: str,
        path: list[str] | None = None,
        target: ModuleType | None = None,
    ) -> importlib.machinery.ModuleSpec | None:
        spec = importlib.machinery.PathFinder.find_spec(fullname, path, target)
        if not spec or not spec.origin:
            return spec
        origin = Path(spec.origin).resolve()
        try:
            origin.relative_to(self._source_root)
        except ValueError:
            return spec
        _verified_bytes(origin, self._source_root, self._digests)
        spec.loader = _VerifiedSourceLoader(
            fullname, str(origin), self._source_root, self._digests
        )
        return spec


def _load_manifest(path: Path, expected_digest: str) -> dict[str, str]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if _canonical_digest(value) != expected_digest:
        raise ImportError("runtime_manifest_digest_mismatch")
    digests = value.get("required_runtime_sha256")
    if not isinstance(digests, dict) or not digests:
        raise ImportError("runtime_manifest_digest_map_missing")
    return {
        str(key): str(digest)
        for key, digest in digests.items()
        if isinstance(key, str) and isinstance(digest, str)
    }


def main(argv: list[str]) -> int:
    if len(argv) != 7:
        raise ValueError("runtime_bootstrap_argument_count")
    script, source, target, dependencies, manifest, expected = argv[1:]
    source_root = Path(source).resolve()
    digests = _load_manifest(Path(manifest), expected)
    sys.path.extend([str(source_root), str(Path(dependencies).resolve())])
    sys.meta_path.insert(0, _VerifiedSourceFinder(source_root, digests))
    raw = _verified_bytes(Path(script), source_root, digests)
    namespace = {
        "__name__": "__main__",
        "__file__": str(Path(script).resolve()),
        "__builtins__": __builtins__,
        "REDDOG_TARGET_REPO_ROOT": str(Path(target).resolve()),
    }
    exec(compile(raw, namespace["__file__"], "exec"), namespace)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
