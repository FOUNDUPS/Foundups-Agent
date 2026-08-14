"""Root-owned WSP 71 resolver supply for the signer system service."""

from __future__ import annotations

import stat
import sys
from dataclasses import dataclass
from pathlib import Path

from modules.infrastructure.secrets_mcp.src.op_cli_secret_resolver import (
    DEFAULT_MAX_SECRET_CHARS,
    DEFAULT_OP_TIMEOUT_SECONDS,
    OpCliCommandRunner,
    OpCliSecretResolver,
)


SYSTEM_SERVICE_OP_EXECUTABLE = Path("/usr/bin/op")
SYSTEM_SERVICE_SECRET_TTL_SECONDS = 60


@dataclass(frozen=True, slots=True)
class SystemServiceWsp71ResolverFactory:
    """Create one resolve-per-sign client after signer admission."""

    owner_config_id: str
    runner: OpCliCommandRunner | None = None

    def __call__(self) -> OpCliSecretResolver:
        if not _sha256(self.owner_config_id):
            raise ValueError("system_service_owner_config_id_invalid")
        _require_root_owned_executable(SYSTEM_SERVICE_OP_EXECUTABLE)
        return OpCliSecretResolver(
            op_executable=str(SYSTEM_SERVICE_OP_EXECUTABLE),
            timeout_s=DEFAULT_OP_TIMEOUT_SECONDS,
            ttl_seconds=SYSTEM_SERVICE_SECRET_TTL_SECONDS,
            max_secret_chars=DEFAULT_MAX_SECRET_CHARS,
            session_id="reddog-signer:" + self.owner_config_id[7:23],
            runner=self.runner,
        )


def build_system_service_wsp71_resolver_factory(
    *, owner_config_id: str,
) -> SystemServiceWsp71ResolverFactory:
    """Bind production resolver construction to root-selected authority."""

    return SystemServiceWsp71ResolverFactory(owner_config_id=owner_config_id)


def _require_root_owned_executable(path: Path) -> None:
    if not sys.platform.startswith("linux"):
        raise ValueError("system_service_wsp71_linux_required")
    if not path.is_absolute() or path.is_symlink():
        raise ValueError("system_service_op_executable_invalid")
    try:
        metadata = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise ValueError("system_service_op_executable_unavailable") from exc
    mode = stat.S_IMODE(metadata.st_mode)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != 0
        or mode & 0o022
        or not mode & 0o111
    ):
        raise ValueError("system_service_op_executable_untrusted")
    _require_root_owned_ancestry(path.parent)


def _require_root_owned_ancestry(path: Path) -> None:
    for directory in (path, *path.parents):
        try:
            metadata = directory.stat(follow_symlinks=False)
        except OSError as exc:
            raise ValueError("system_service_op_ancestry_unavailable") from exc
        if (
            directory.is_symlink()
            or not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != 0
            or stat.S_IMODE(metadata.st_mode) & 0o022
        ):
            raise ValueError("system_service_op_ancestry_untrusted")


def _sha256(value: object) -> bool:
    text = value if isinstance(value, str) else ""
    return bool(
        len(text) == 71
        and text.startswith("sha256:")
        and all(char in "0123456789abcdef" for char in text[7:])
    )


__all__ = [
    "SYSTEM_SERVICE_OP_EXECUTABLE",
    "SYSTEM_SERVICE_SECRET_TTL_SECONDS",
    "SystemServiceWsp71ResolverFactory",
    "build_system_service_wsp71_resolver_factory",
]
