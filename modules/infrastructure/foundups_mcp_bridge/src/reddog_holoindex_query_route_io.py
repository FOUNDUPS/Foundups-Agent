"""Confined private-file I/O for the RedDog Holo query route."""

from __future__ import annotations

import hmac
import os
import stat
from pathlib import Path
from typing import Callable

from modules.infrastructure.shared_utilities.runtime_artifact_confined_byte_reader import (
    secure_read_confined_bytes_impl,
)
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)
from modules.infrastructure.shared_utilities.runtime_operation_locking import (
    exclusive_runtime_lock,
    validated_lock_timeout,
)

from .reddog_holoindex_acceptance_guards import (
    _normalized,
    _reject_link_components,
    _reject_overlap,
)
from .reddog_holoindex_query_route_contract import (
    JOURNAL_MAX_BYTES,
    ROUTE_MAX_BYTES,
    ROUTE_SCHEMA_VERSION,
    QueryRouteJournal,
    QueryRouteStateProof,
    encode_route_journal,
    parse_route_journal_bytes,
    parse_route_record_bytes,
    route_record_mapping,
)
from .reddog_private_json_publication import atomic_publish_private_json_proven


class QueryRouteStoreError(RuntimeError):
    """Stable fail-closed route-store error."""


def _fail(code: str) -> None:
    raise QueryRouteStoreError(code)


class QueryRouteRuntimeIO:
    """Bounded, private, confined persistence below route-state policy."""

    def __init__(
        self, route_path: Path | str, *, runtime_root: Path | str,
        canonical_store: Path | str, repo_roots: tuple[Path | str, ...],
        lock_timeout_seconds: float,
        replace_text: Callable[[Path, str], None],
        create_runtime_root: bool,
    ) -> None:
        if type(repo_roots) is not tuple or not repo_roots:
            _fail("QUERY_ROUTE_STORE_REPO_ROOTS_INVALID")
        if type(lock_timeout_seconds) is not float or not callable(replace_text):
            _fail("QUERY_ROUTE_STORE_LOCK_TIMEOUT_INVALID")
        if type(create_runtime_root) is not bool:
            _fail("QUERY_ROUTE_STORE_RUNTIME_ROOT_MODE_INVALID")
        self.repo_roots = tuple(_normalized(item) for item in repo_roots)
        for repo_root in self.repo_roots:
            _reject_link_components(repo_root)
            if not repo_root.is_dir():
                _fail("QUERY_ROUTE_STORE_REPO_ROOTS_INVALID")
        self.canonical_store = _normalized(canonical_store)
        _reject_link_components(self.canonical_store)
        if not self.canonical_store.is_dir():
            _fail("QUERY_ROUTE_STORE_CANONICAL_INVALID")
        self.runtime_root = validate_runtime_root_path(
            runtime_root, repo_root=self.repo_roots[0]
        )
        _reject_overlap(self.runtime_root, (*self.repo_roots, self.canonical_store))
        if create_runtime_root:
            self.runtime_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        elif not self.runtime_root.is_dir():
            _fail("QUERY_ROUTE_STORE_RUNTIME_ROOT_INVALID")
        _reject_link_components(self.runtime_root)
        self.route_path = self._runtime_path(route_path)
        self.journal_path = self._runtime_path(
            self.route_path.with_name(self.route_path.name + ".journal")
        )
        self.lock_path = self._runtime_path(
            self.route_path.with_name(self.route_path.name + ".activation.lock")
        )
        self.lock_timeout_seconds = validated_lock_timeout(lock_timeout_seconds)
        self._atomic_replace_text = replace_text

    def lock(self):
        return exclusive_runtime_lock(
            self.lock_path, timeout_seconds=self.lock_timeout_seconds
        )

    def publish_initial(self, payload: QueryRouteStateProof) -> None:
        atomic_publish_private_json_proven(
            self.route_path, route_record_mapping(payload.record),
            allowed_root=self.runtime_root,
            canonical_store=self.canonical_store,
            repo_roots=self.repo_roots, max_bytes=ROUTE_MAX_BYTES,
            expected_schema=ROUTE_SCHEMA_VERSION,
            reject_absolute_paths=False,
        )

    def read_route(self) -> QueryRouteStateProof:
        self._runtime_path(self.route_path)
        if not self.route_path.exists():
            _fail("QUERY_ROUTE_NOT_INITIALIZED")
        try:
            return parse_route_record_bytes(
                self._read_bytes(self.route_path, ROUTE_MAX_BYTES)
            )
        except QueryRouteStoreError:
            raise
        except Exception as exc:
            raise QueryRouteStoreError("QUERY_ROUTE_INVALID") from exc

    def read_journal(self) -> QueryRouteJournal | None:
        self._runtime_path(self.journal_path)
        if not self.journal_path.exists():
            return None
        try:
            return parse_route_journal_bytes(
                self._read_bytes(self.journal_path, JOURNAL_MAX_BYTES)
            )
        except QueryRouteStoreError:
            raise
        except Exception as exc:
            raise QueryRouteStoreError("QUERY_ROUTE_JOURNAL_INVALID") from exc

    def write_route(self, proof: QueryRouteStateProof) -> QueryRouteStateProof:
        self._replace_text(self.route_path, proof.encoded.decode("ascii"))
        observed = self.read_route()
        if not hmac.compare_digest(observed.digest, proof.digest):
            _fail("QUERY_ROUTE_REPLACE_UNPROVEN")
        return observed

    def write_journal(self, journal: QueryRouteJournal) -> None:
        encoded = encode_route_journal(journal)
        self._replace_text(self.journal_path, encoded.decode("ascii"))
        observed = self.read_journal()
        if observed is None or encode_route_journal(observed) != encoded:
            _fail("QUERY_ROUTE_JOURNAL_REPLACE_UNPROVEN")

    def _runtime_path(self, path: Path | str) -> Path:
        target = validate_runtime_artifact_path(
            path, repo_root=self.repo_roots[0], allowed_root=self.runtime_root
        )
        if target == self.runtime_root:
            _fail("QUERY_ROUTE_STORE_PATH_INVALID")
        _reject_link_components(target)
        return target

    def _read_bytes(self, path: Path, maximum: int) -> bytes:
        self._runtime_path(path)
        try:
            payload, _offset = secure_read_confined_bytes_impl(
                path, allowed_root=self.runtime_root, max_bytes=maximum + 1
            )
        except FileNotFoundError:
            raise
        except Exception as exc:
            raise QueryRouteStoreError("QUERY_ROUTE_STORE_READ_FAILED") from exc
        if len(payload) > maximum:
            _fail("QUERY_ROUTE_STORE_SIZE_INVALID")
        self._require_private_file(path)
        return payload

    def _replace_text(self, path: Path, text: str) -> None:
        self._runtime_path(path)
        try:
            self._atomic_replace_text(path, text)
        except Exception as exc:
            raise QueryRouteStoreError("QUERY_ROUTE_ATOMIC_REPLACE_FAILED") from exc
        self._runtime_path(path)
        self._require_private_file(path)

    @staticmethod
    def _require_private_file(path: Path) -> None:
        metadata = os.lstat(path)
        if not stat.S_ISREG(metadata.st_mode) or int(getattr(metadata, "st_nlink", 1)) != 1:
            _fail("QUERY_ROUTE_PRIVATE_FILE_INVALID")
        if os.name != "nt" and stat.S_IMODE(metadata.st_mode) & 0o077:
            _fail("QUERY_ROUTE_PRIVATE_FILE_PERMISSIONS_INVALID")


__all__ = ["QueryRouteRuntimeIO", "QueryRouteStoreError"]
