"""Linux-only helpers for root-authority socket substitution tests."""

from __future__ import annotations

import os
import socket
from pathlib import Path

from modules.communication.moltbot_bridge.src.foundup_verified_outcome_root_authority_client import (
    build_root_authority_socket_exchange,
)


def exchange_before_non_root_listener_substitution(
    socket_path: Path, *, repo_root: Path, attacker_uid: int, attacker_gid: int,
):
    """Pin a valid root socket, then replace it with a non-root listener."""

    parent = socket_path.parent
    parent.mkdir(mode=0o755, exist_ok=True)
    root_server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    root_server.bind(str(socket_path))
    root_server.listen(1)
    os.chown(socket_path, 0, attacker_gid)
    os.chmod(socket_path, 0o660)
    exchange = build_root_authority_socket_exchange(
        repo_root=repo_root, socket_path=socket_path, expected_server_uid=0,
    )
    root_server.close()
    socket_path.unlink()
    os.chmod(parent, 0o777)
    child, ready = _spawn_attacker_listener(
        socket_path, uid=attacker_uid, gid=attacker_gid
    )
    assert os.read(ready, 1) == b"R"
    os.close(ready)
    return exchange, child


def reap_listener(child: int) -> None:
    _pid, status = os.waitpid(child, 0)
    assert status == 0


def _spawn_attacker_listener(path: Path, *, uid: int, gid: int) -> tuple[int, int]:
    read_fd, write_fd = os.pipe()
    child = os.fork()
    if child == 0:
        try:
            os.close(read_fd)
            os.setgroups([])
            os.setgid(gid)
            os.setuid(uid)
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
                server.bind(str(path))
                server.listen(1)
                os.write(write_fd, b"R")
                connection, _ = server.accept()
                connection.close()
        finally:
            os.close(write_fd)
            os._exit(0)
    os.close(write_fd)
    return child, read_fd


__all__ = ["exchange_before_non_root_listener_substitution", "reap_listener"]
