"""Bounded owner acquisition policy for long-lived RedDog query callers."""

from __future__ import annotations

import os
from typing import Mapping

from holo_index.authority_worktree import AUTHORITY_REPO_ROOT_ENV

from .holo_query_service_supervisor import DEFAULT_OWNER_PORT
from .reddog_holoindex_owner_replica_route import (
    QUERY_REPLICA_ROOT_ENV,
    QUERY_REPLICA_ROUTE_FILE_ENV,
)


OWNER_PORT_SHARD_COUNT = 64
MAX_OWNER_ATTEMPTS = 2
_QUERY_ROUTE_NAMES = (
    AUTHORITY_REPO_ROOT_ENV,
    QUERY_REPLICA_ROOT_ENV,
    QUERY_REPLICA_ROUTE_FILE_ENV,
)
_USER_ROUTE_NAMES = (
    AUTHORITY_REPO_ROOT_ENV,
    QUERY_REPLICA_ROUTE_FILE_ENV,
)


def _exact_environment(value: Mapping[str, str]) -> dict[str, str]:
    selected: dict[str, str] = {}
    for name in _QUERY_ROUTE_NAMES:
        item = value.get(name)
        if item is None:
            continue
        if type(item) is not str:
            raise ValueError("holoindex_query_environment_invalid")
        selected[name] = item
    return selected


def _windows_user_route_environment() -> dict[str, str]:
    """Read only the two non-secret HKCU route values on Windows."""

    if os.name != "nt":
        return {}
    try:
        import winreg

        values: dict[str, str] = {}
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            "Environment",
            0,
            winreg.KEY_QUERY_VALUE,
        ) as key:
            for name in _USER_ROUTE_NAMES:
                try:
                    value, value_type = winreg.QueryValueEx(key, name)
                except OSError:
                    continue
                if value_type == winreg.REG_SZ and type(value) is str and value.strip():
                    values[name] = value
        return values
    except (ImportError, OSError):
        return {}


def build_owner_query_environment(
    *,
    process_environment: Mapping[str, str] | None = None,
    user_environment: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return private query configuration with current user route precedence."""

    process = _exact_environment(
        os.environ if process_environment is None else process_environment
    )
    user = _exact_environment(
        _windows_user_route_environment()
        if user_environment is None
        else user_environment
    )
    authority = user.get(AUTHORITY_REPO_ROOT_ENV, "")
    if authority.strip():
        process[AUTHORITY_REPO_ROOT_ENV] = authority
    route_file = user.get(QUERY_REPLICA_ROUTE_FILE_ENV, "")
    if route_file.strip():
        process[QUERY_REPLICA_ROUTE_FILE_ENV] = route_file
        process.pop(QUERY_REPLICA_ROOT_ENV, None)
    return process


def owner_port_for_attempt(
    attempt: int, *, process_id: int | None = None,
) -> int:
    """Select one bounded process shard; the port grants no authority."""

    pid = os.getpid() if process_id is None else process_id
    if type(attempt) is not int or not 1 <= attempt <= MAX_OWNER_ATTEMPTS:
        raise ValueError("owner_attempt_invalid")
    if type(pid) is not int or pid <= 0:
        raise ValueError("owner_process_invalid")
    offset = pid % OWNER_PORT_SHARD_COUNT
    if attempt == 2:
        offset = (
            offset + 1 + (pid // OWNER_PORT_SHARD_COUNT) % (OWNER_PORT_SHARD_COUNT - 1)
        ) % OWNER_PORT_SHARD_COUNT
    return DEFAULT_OWNER_PORT + offset


__all__ = [
    "MAX_OWNER_ATTEMPTS",
    "OWNER_PORT_SHARD_COUNT",
    "build_owner_query_environment",
    "owner_port_for_attempt",
]
