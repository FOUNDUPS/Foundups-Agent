# -*- coding: utf-8 -*-
"""Deterministic, read-only grounding for repository/module audit prompts.

HoloIndex evidence is evaluated first.  When it cannot establish source plus
independent test/contract coverage, a fixed-policy repository walk discovers a
small evidence set without shelling out or accepting model-controlled paths.
"""

from __future__ import annotations

import hashlib
import os
import re
import stat
import subprocess
import sys
import threading
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


MAX_SELECTED_PATHS = 12
TOTAL_READ_BUDGET_BYTES = 96_000
PER_FILE_READ_BYTES = 12_000
MAX_FILE_SIZE_BYTES = 512_000
MAX_DISCOVERY_ENTRIES = 20_000
MAX_CONTENT_SCAN_BYTES = 4_096
MAX_CONTENT_SCAN_TOTAL_BYTES = 512_000

_AUDIT_WORDS = frozenset({"audit", "assess", "review", "examine", "inspect", "evaluate"})
_SCOPE_WORDS = frozenset({"codebase", "module", "repo", "repository", "implementation", "system"})
_GENERIC = _AUDIT_WORDS | _SCOPE_WORDS | frozenset({
    "a", "all", "an", "and", "entire", "for", "full", "of", "please", "the", "this",
        "whole", "working", "work", "recommend", "recommendations", "report", "security", "defensive",
})
_QUESTION_OPENERS = frozenset({"how", "if", "what", "whether", "why"})
_PRIVATE_TOOL_STATE_SEGMENTS = frozenset({
    ".agent", ".agents", ".claude", ".codex", ".cursor", ".idea", ".m2m",
    ".memory", ".vscode", ".windsurf", "memory",
})
_PRUNE_SEGMENTS = frozenset({
    ".git", ".worktrees", "node_modules", "vendor", "venv", ".venv", "__pycache__",
    ".cache", "cache", "generated", "build", "dist", "logs", "log", "temp", "tmp",
    "archive", "archives", "vector", "vectors", "chroma", ".chroma",
}) | _PRIVATE_TOOL_STATE_SEGMENTS
_SECRET_MARKERS = ("secret", "credential", "token", "private_key", "apikey", "api_key")
_SECRET_BASENAMES = frozenset({".env", "id_rsa", "id_ed25519"})
_SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".keystore", ".vsix")
_ALLOWED_SUFFIXES = frozenset({
    ".py", ".js", ".ts", ".tsx", ".jsx", ".md", ".rst", ".txt", ".json", ".yaml",
    ".yml", ".toml", ".html", ".css", ".sol", ".go", ".rs", ".java", ".c", ".h",
})
_TOKEN_RE = re.compile(r"^[\w.-]{1,64}$", re.UNICODE)
_WINDOWS_REPARSE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def canonicalize_entity(value: str) -> str:
    """Case/punctuation/Unicode-insensitive entity key."""
    normalized = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return "".join(ch for ch in normalized if ch.isalnum())


def detect_repo_audit_intent(task: str) -> Dict[str, Any]:
    """Detect bounded audit intent and extract one safe entity token."""
    text = unicodedata.normalize("NFKC", str(task or ""))
    text = next((line.strip() for line in text.splitlines() if line.strip()), text)
    lowered = text.casefold()
    safe_chunks = [
        chunk for chunk in lowered.split()
        if not any(marker in chunk for marker in ("/", "\\", ":", "\x00"))
    ]
    words = re.findall(r"[\w.-]+", " ".join(safe_chunks), flags=re.UNICODE)
    audit = any(word in _AUDIT_WORDS for word in words)
    audit_indexes = [index for index, word in enumerate(words) if word in _AUDIT_WORDS]
    question_shaped = any(
        index + 1 < len(words) and words[index + 1] in _QUESTION_OPENERS for index in audit_indexes
    )
    scope = any(word in _SCOPE_WORDS for word in words)
    # "audit pfmall" is intentionally sufficient; prose without an audit verb is not.
    candidates: List[Tuple[int, str, str]] = []
    for index, raw in enumerate(words):
        if not _TOKEN_RE.fullmatch(raw) or any(ch in raw for ch in ("/", "\\", ":", "\x00")):
            continue
        key = canonicalize_entity(raw)
        if not key or key in _GENERIC or key.isdigit() or len(key) < 2:
            continue
        distance = min((abs(index - i) for i, word in enumerate(words) if word in _AUDIT_WORDS), default=999)
        candidates.append((distance, raw, key))
    candidates.sort(key=lambda item: (item[0], len(item[2]), item[2]))
    entity = candidates[0][2] if audit and candidates else None
    raw_entity = candidates[0][1] if entity else None
    return {
        "audit_intent": bool(
            audit and not question_shaped and entity and (scope or ("audit" in words and len(words) <= 3))
        ),
        "entity": entity,
        "raw_entity": raw_entity,
        "aliases": [entity] if entity else [],
    }


def _path_deny_reason(raw_path: str) -> Optional[str]:
    value = str(raw_path or "")
    if "\x00" in value:
        return "nul_path"
    normalized = value.replace("\\", "/")
    if not normalized:
        return "path_missing"
    if normalized.startswith("/") or (len(normalized) > 1 and normalized[1] == ":"):
        return "absolute_path"
    parts = normalized.split("/")
    if any(part in ("", ".", "..") for part in parts):
        return "traversal" if ".." in parts else "invalid_segment"
    lowered = [part.casefold() for part in parts]
    if any(part in _PRUNE_SEGMENTS for part in lowered):
        return "pruned_path"
    if any(part in _SECRET_BASENAMES for part in lowered):
        return "secret_like_path"
    if any(marker in part for part in lowered for marker in _SECRET_MARKERS):
        return "secret_like_path"
    if lowered[-1].endswith(_SECRET_SUFFIXES):
        return "secret_like_path"
    return None


def _is_reparse_or_link(path: str) -> bool:
    info = os.lstat(path)
    attrs = int(getattr(info, "st_file_attributes", 0) or 0)
    return stat.S_ISLNK(info.st_mode) or bool(attrs & _WINDOWS_REPARSE)


def _fd_final_path(fd: int) -> Optional[str]:
    if os.name != "nt":
        try:
            return os.path.abspath(os.readlink(f"/proc/self/fd/{fd}"))
        except OSError:
            return None
    try:  # pragma: no cover - exercised on Windows CI/contract hosts
        import ctypes
        from ctypes import wintypes
        import msvcrt

        handle = msvcrt.get_osfhandle(fd)
        buf = ctypes.create_unicode_buffer(32768)
        get_final_path = ctypes.windll.kernel32.GetFinalPathNameByHandleW
        get_final_path.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
        get_final_path.restype = wintypes.DWORD
        size = get_final_path(wintypes.HANDLE(handle), buf, len(buf), 0)
        if not size or size >= len(buf):
            return None
        value = buf.value
        if value.startswith("\\\\?\\UNC\\"):
            value = "\\\\" + value[8:]
        elif value.startswith("\\\\?\\"):
            value = value[4:]
        return os.path.abspath(value)
    except Exception:
        return None


def _same_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return (left.st_dev, left.st_ino, stat.S_IFMT(left.st_mode)) == (
        right.st_dev, right.st_ino, stat.S_IFMT(right.st_mode)
    )


def _component_paths(root: str, rel_path: str) -> Iterable[str]:
    current = root
    for part in rel_path.replace("\\", "/").split("/"):
        current = os.path.join(current, part)
        yield current


def _secure_open(repo_root: Path, rel_path: str, byte_cap: int, remaining_budget: int) -> Dict[str, Any]:
    root = os.path.abspath(os.fspath(repo_root))
    try:
        if _is_reparse_or_link(root):
            return {"ok": False, "path": rel_path, "reason": "repo_root_reparse"}
        components = list(_component_paths(root, rel_path))
        for component in components:
            if _is_reparse_or_link(component):
                return {"ok": False, "path": rel_path, "reason": "reparse_component"}
        before = os.lstat(components[-1])
        if not stat.S_ISREG(before.st_mode):
            return {"ok": False, "path": rel_path, "reason": "not_regular_file"}
        if before.st_nlink > 1:
            return {"ok": False, "path": rel_path, "reason": "hardlink_rejected"}
        if before.st_size > MAX_FILE_SIZE_BYTES:
            return {"ok": False, "path": rel_path, "reason": "oversize"}
        cap = min(max(0, int(byte_cap)), max(0, int(remaining_budget)))
        if cap <= 0:
            return {"ok": False, "path": rel_path, "reason": "budget_exhausted"}
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_CLOEXEC", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(os.path.join(root, *rel_path.split("/")), flags)
    except (OSError, ValueError):
        return {"ok": False, "path": rel_path, "reason": "open_rejected"}
    return {
        "ok": True, "path": rel_path, "root": root, "components": components,
        "before": before, "cap": cap, "fd": fd,
    }


def _validate_open_identity(opened_file: Dict[str, Any], post_open_hook=None) -> Tuple[Optional[str], os.stat_result]:
    fd = opened_file["fd"]
    before = opened_file["before"]
    components = opened_file["components"]
    opened = os.fstat(fd)
    if not stat.S_ISREG(opened.st_mode) or not _same_identity(before, opened):
        return "identity_changed", opened
    if opened.st_nlink > 1:
        return "hardlink_rejected", opened
    if post_open_hook is not None:
        try:
            post_open_hook()
        except OSError:
            return "identity_changed", opened
    if any(_is_reparse_or_link(component) for component in components):
        return "reparse_component", opened
    if not _same_identity(opened, os.lstat(components[-1])):
        return "identity_changed", opened
    final_path = _fd_final_path(fd)
    if final_path is None:
        return "final_path_unavailable", opened
    try:
        root = os.path.normcase(os.path.abspath(opened_file["root"]))
        final = os.path.normcase(os.path.abspath(final_path))
        if os.path.commonpath((root, final)) != root:
            return "outside_root", opened
    except ValueError:
        return "outside_root", opened
    return None, opened


def secure_read_repo_head_file(
    repo_root: Path,
    raw_path: str,
    *,
    byte_cap: int = PER_FILE_READ_BYTES,
    remaining_budget: int = TOTAL_READ_BUDGET_BYTES,
    timeout_seconds: float | None = None,
) -> Dict[str, Any]:
    """Read one immutable Git blob from the exact current HEAD."""

    rel_path = str(raw_path or "").replace("\\", "/")
    setup = _prepare_head_read(repo_root, rel_path, timeout_seconds)
    if isinstance(setup, dict):
        return setup
    root, head, deadline = setup
    cap = min(max(0, int(byte_cap)), max(0, int(remaining_budget)))
    if cap <= 0:
        return {"ok": False, "path": rel_path, "reason": "budget_exhausted"}
    entry = _git_tree_entry(root, head, rel_path, timeout_seconds=_remaining(deadline))
    if entry is None:
        return {"ok": False, "path": rel_path, "reason": "not_committed"}
    git_mode, blob_oid = entry
    if git_mode not in {"100644", "100755"}:
        return {"ok": False, "path": rel_path, "reason": "git_mode_rejected"}
    raw, file_size, reason = _read_git_blob(
        root, blob_oid, byte_cap=cap, deadline_monotonic=deadline
    )
    if reason:
        return {
            "ok": False, "path": rel_path, "reason": reason,
            "attempted_bytes": len(raw),
        }
    if file_size <= cap and _git_blob_oid(raw, len(blob_oid)) != blob_oid:
        return {"ok": False, "path": rel_path, "reason": "blob_oid_mismatch"}
    return {
        "ok": True,
        "path": rel_path,
        "content": raw.decode("utf-8", errors="replace"),
        "bytes": len(raw),
        "attempted_bytes": len(raw),
        "digest": "sha256:" + hashlib.sha256(raw).hexdigest(),
        "truncated": file_size > cap,
        "repo_head_sha": head,
        "git_mode": git_mode,
        "blob_oid": blob_oid,
    }


def _prepare_head_read(
    repo_root: Path, rel_path: str, timeout_seconds: float | None
) -> tuple[Path, str, float] | Dict[str, Any]:
    denied = _path_deny_reason(rel_path)
    if denied:
        return {"ok": False, "path": rel_path, "reason": denied}
    from holo_index.freshness_receipt import read_git_head_sha

    root = Path(repo_root).resolve(strict=False)
    requested_timeout = 5.0 if timeout_seconds is None else float(timeout_seconds)
    if requested_timeout <= 0:
        return {"ok": False, "path": rel_path, "reason": "git_timeout"}
    deadline = time.monotonic() + min(5.0, requested_timeout)
    head = read_git_head_sha(root)
    if not re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?", head):
        return {"ok": False, "path": rel_path, "reason": "repo_head_unavailable"}
    return root, head, deadline


def _read_git_blob(
    root: Path, blob_oid: str, *, byte_cap: int, deadline_monotonic: float
) -> tuple[bytes, int, str]:
    remaining = _remaining(deadline_monotonic)
    if remaining <= 0:
        return b"", -1, "git_timeout"
    size = _run_git(
        root, ("cat-file", "-s", blob_oid), text=True,
        timeout_seconds=remaining,
    )
    try:
        file_size = int(str(size.stdout or "").strip()) if size.returncode == 0 else -1
    except ValueError:
        file_size = -1
    if file_size < 0:
        return b"", file_size, "not_committed"
    if file_size > MAX_FILE_SIZE_BYTES:
        return b"", file_size, "oversize"
    if _remaining(deadline_monotonic) <= 0:
        return b"", file_size, "git_timeout"
    raw, complete = _read_git_blob_prefix(
        root, blob_oid, min(file_size, byte_cap), deadline_monotonic
    )
    if not complete or len(raw) != min(file_size, byte_cap) or b"\x00" in raw:
        return raw, file_size, "blob_read_rejected"
    return raw, file_size, ""


def _read_git_blob_prefix(
    root: Path, blob_oid: str, limit: int, deadline_monotonic: float
) -> tuple[bytes, bool]:
    command = _git_command(root, ("cat-file", "blob", blob_oid))
    if not command or limit <= 0 or _remaining(deadline_monotonic) <= 0:
        return b"", False
    process = None
    chunks: list[bytes] = []
    try:
        process = subprocess.Popen(  # nosec B603 - fixed trusted Git argv.
            command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            shell=False, env=_git_environment(),
        )
        reader = threading.Thread(
            target=_read_prefix, args=(process.stdout, limit, chunks), daemon=True
        )
        reader.start()
        reader.join(_remaining(deadline_monotonic))
        if reader.is_alive():
            process.kill()
            return b"", False
        remaining = _remaining(deadline_monotonic)
        if remaining <= 0:
            process.kill()
            return b"", False
        process.wait(timeout=remaining)
        raw = b"".join(chunks)
        return raw, len(raw) == limit
    except (OSError, subprocess.SubprocessError, ValueError):
        if process is not None:
            process.kill()
        return b"", False


def _read_prefix(stream, limit: int, chunks: list[bytes]) -> None:
    if stream is None:
        return
    try:
        chunks.append(stream.read(limit))
    finally:
        stream.close()


def _git_tree_entry(
    root: Path, head: str, rel_path: str, *, timeout_seconds: float = 5.0
) -> tuple[str, str] | None:
    result = _run_git(
        root, ("ls-tree", "-z", "--full-tree", head, "--", rel_path),
        text=False, timeout_seconds=timeout_seconds,
    )
    raw = bytes(result.stdout or b"") if result.returncode == 0 else b""
    records = raw[:-1].split(b"\x00") if raw.endswith(b"\x00") else []
    if len(records) != 1 or b"\t" not in records[0]:
        return None
    metadata, encoded_path = records[0].split(b"\t", 1)
    fields = metadata.split()
    try:
        listed_path = encoded_path.decode("utf-8", errors="strict")
        mode, object_type, oid = (item.decode("ascii") for item in fields)
    except (UnicodeDecodeError, ValueError):
        return None
    if (
        listed_path != rel_path
        or object_type != "blob"
        or re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?", oid) is None
    ):
        return None
    return mode, oid


def _git_blob_oid(raw: bytes, oid_length: int) -> str:
    framed = b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw
    if oid_length == 40:
        return hashlib.sha1(framed).hexdigest()  # nosec B324 - Git SHA-1 object ID.
    if oid_length == 64:
        return hashlib.sha256(framed).hexdigest()
    return ""


def _git_environment() -> dict[str, str]:
    environment = {
        key: value for key, value in os.environ.items()
        if not key.upper().startswith("GIT_")
    }
    environment["GIT_CONFIG_NOSYSTEM"] = "1"
    environment["GIT_CONFIG_GLOBAL"] = os.devnull
    return environment


def resolve_trusted_git_executable() -> str | None:
    """Resolve Git from an OS-owned location without consulting caller PATH."""

    candidates: list[Path] = []
    if sys.platform == "win32":
        try:
            import winreg

            views = (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY)
            for view in views:
                try:
                    with winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE,
                        r"SOFTWARE\GitForWindows",
                        0,
                        winreg.KEY_READ | view,
                    ) as key:
                        install_path = str(winreg.QueryValueEx(key, "InstallPath")[0])
                except OSError:
                    continue
                candidates.extend((
                    Path(install_path) / "cmd" / "git.exe",
                    Path(install_path) / "bin" / "git.exe",
                ))
        except (ImportError, OSError, ValueError):
            return None
    else:
        candidates.extend((
            Path("/usr/bin/git"),
            Path("/usr/local/bin/git"),
            Path("/opt/homebrew/bin/git"),
        ))
    for candidate in candidates:
        try:
            resolved = candidate.resolve(strict=True)
            if stat.S_ISREG(resolved.stat().st_mode):
                return str(resolved)
        except (OSError, RuntimeError):
            continue
    return None


_trusted_git_path = resolve_trusted_git_executable


def _git_command(root: Path, args: Sequence[str]) -> list[str]:
    git_executable = _trusted_git_path()
    return ([
        git_executable, "--no-replace-objects", "-c", "core.useReplaceRefs=false",
        "-C", str(root), *args,
    ] if git_executable else [])


def _remaining(deadline: float) -> float:
    return max(0.0, deadline - time.monotonic())


def _run_git(
    root: Path, args: Sequence[str], *, text: bool, timeout_seconds: float = 5.0
) -> subprocess.CompletedProcess:
    command = _git_command(root, args)
    if not command or timeout_seconds <= 0:
        return subprocess.CompletedProcess([], 1, "" if text else b"", "" if text else b"")
    try:
        return subprocess.run(  # nosec B603 - fixed git argv, shell disabled.
            command,
            capture_output=True,
            text=text,
            encoding="utf-8" if text else None,
            errors="strict" if text else None,
            timeout=min(5.0, timeout_seconds),
            check=False,
            shell=False,
            env=_git_environment(),
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        return subprocess.CompletedProcess([], 1, "" if text else b"", "" if text else b"")


def secure_read_repo_file(
    repo_root: Path,
    raw_path: str,
    *,
    byte_cap: int = PER_FILE_READ_BYTES,
    remaining_budget: int = TOTAL_READ_BUDGET_BYTES,
    post_open_hook=None,
) -> Dict[str, Any]:
    """Open a regular repo file without realpath-then-open TOCTOU authorization."""
    rel_path = str(raw_path or "").replace("\\", "/")
    denied = _path_deny_reason(rel_path)
    if denied:
        return {"ok": False, "path": rel_path, "reason": denied}
    opened_file = _secure_open(repo_root, rel_path, byte_cap, remaining_budget)
    if not opened_file.get("ok"):
        return opened_file
    fd = opened_file["fd"]
    try:
        reason, opened = _validate_open_identity(opened_file, post_open_hook)
        if reason:
            return {"ok": False, "path": rel_path, "reason": reason}
        cap = opened_file["cap"]
        raw = os.read(fd, cap + 1)
        if b"\x00" in raw:
            return {"ok": False, "path": rel_path, "reason": "binary"}
        clipped = raw[:cap]
        return {
            "ok": True,
            "path": rel_path,
            "content": clipped.decode("utf-8", errors="replace"),
            "bytes": len(clipped),
            "digest": "sha256:" + hashlib.sha256(clipped).hexdigest(),
            "truncated": len(raw) > cap or opened.st_size > cap,
        }
    except OSError:
        return {"ok": False, "path": rel_path, "reason": "read_error"}
    finally:
        os.close(fd)


def repo_audit_category(rel_path: str) -> str:
    """Derive the evidence category from a repository-relative path."""
    parts = rel_path.casefold().split("/")
    name = parts[-1]
    if "tests" in parts or name.startswith("test_") or name.endswith(".test.js"):
        return "test"
    if "contract" in name or "contracts" in parts:
        return "contract"
    if name.startswith("readme"):
        return "readme"
    if parts[0] == "public" or "static" in parts:
        return "public"
    if name in {"__init__.py", "package.json", "pyproject.toml"}:
        return "module"
    if Path(name).suffix.casefold() in {".py", ".js", ".ts", ".tsx", ".jsx", ".sol", ".go", ".rs", ".java", ".c", ".h"}:
        return "implementation_source"
    return "documentation"


def repo_audit_path_supports_entity(rel_path: str, entity: str) -> bool:
    """Return whether a path itself binds evidence to the canonical entity."""
    score, _reasons = _path_match_score(rel_path, entity)
    return score > 0


def _path_match_score(rel_path: str, entity: str) -> Tuple[int, List[str]]:
    parts = rel_path.replace("\\", "/").split("/")
    normalized_parts = [canonicalize_entity(part) for part in parts]
    normalized_stem = canonicalize_entity(Path(parts[-1]).stem)
    reasons: List[str] = []
    score = 0
    if entity in normalized_parts[:-1]:
        score = 400
        reasons.append("exact_normalized_segment")
    elif normalized_stem == entity:
        score = 300
        reasons.append("exact_normalized_filename")
    elif entity in normalized_stem:
        score = 220
        reasons.append("filename_contains_entity")
    elif any(entity in part for part in normalized_parts):
        score = 180
        reasons.append("path_contains_entity")
    return score, reasons


def _candidate(rel_path: str, entity: str, source: str, content_match: bool = False) -> Optional[Dict[str, Any]]:
    score, reasons = _path_match_score(rel_path, entity)
    if content_match:
        score = max(score, 100)
        reasons.append("bounded_content_match")
    if score <= 0:
        return None
    category = repo_audit_category(rel_path)
    if category == "implementation_source":
        score += 25
    elif category in {"test", "contract"}:
        score += 20
    return {"path": rel_path, "score": score, "category": category, "reasons": reasons, "source": source}


def _holo_paths(search_payload: Dict[str, Any], entity: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    candidates: List[Dict[str, Any]] = []
    refs: List[str] = []
    for bucket in ("code_hits", "test_hits", "doc_hits", "wsp_hits"):
        for hit in search_payload.get(bucket) or []:
            if not isinstance(hit, dict):
                continue
            raw = hit.get("location") or hit.get("path") or hit.get("file")
            rel_path = str(raw or "").replace("\\", "/")
            if _path_deny_reason(rel_path):
                continue
            item = _candidate(rel_path, entity, "holo")
            if item:
                candidates.append(item)
                refs.append(rel_path)
    return _dedupe_candidates(candidates), sorted(set(refs), key=str.casefold)


def _dedupe_candidates(candidates: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_path: Dict[str, Dict[str, Any]] = {}
    for item in candidates:
        key = item["path"].casefold()
        current = by_path.get(key)
        if current is None or item["score"] > current["score"]:
            by_path[key] = item
    return sorted(by_path.values(), key=lambda item: (-item["score"], item["path"].casefold()))


def _content_candidate(
    repo_root: Path, rel_path: str, entity: str, scan_budget: int, exclusions: Dict[str, int]
) -> Tuple[Optional[Dict[str, Any]], int]:
    if scan_budget <= 0:
        return None, 0
    read = secure_read_repo_file(
        repo_root, rel_path, byte_cap=MAX_CONTENT_SCAN_BYTES, remaining_budget=scan_budget
    )
    if not read.get("ok"):
        reason = str(read.get("reason") or "read_rejected")
        exclusions[reason] = exclusions.get(reason, 0) + 1
        return None, 0
    content_key = canonicalize_entity(read.get("content", ""))
    return _candidate(rel_path, entity, "deterministic", entity in content_key), read["bytes"]


def _relative_discovery_path(entry_path: str, root: str, exclusions: Dict[str, int]) -> Optional[str]:
    try:
        return os.path.relpath(entry_path, root).replace("\\", "/")
    except (OSError, ValueError):
        exclusions["invalid_entry_path"] = exclusions.get("invalid_entry_path", 0) + 1
        return None


def _discover(repo_root: Path, entity: str, exclusions: Dict[str, int]) -> List[Dict[str, Any]]:
    root = os.path.abspath(os.fspath(repo_root))
    queue = [root]
    candidates: List[Dict[str, Any]] = []
    entries = 0
    scan_budget = MAX_CONTENT_SCAN_TOTAL_BYTES
    while queue and entries < MAX_DISCOVERY_ENTRIES:
        current = queue.pop(0)
        try:
            children = sorted(os.scandir(current), key=lambda item: item.name.casefold())
        except OSError:
            exclusions["scan_error"] = exclusions.get("scan_error", 0) + 1
            continue
        for entry in children:
            entries += 1
            if entries > MAX_DISCOVERY_ENTRIES:
                exclusions["entry_limit"] = exclusions.get("entry_limit", 0) + 1
                break
            rel_path = _relative_discovery_path(entry.path, root, exclusions)
            if rel_path is None:
                continue
            try:
                if _is_reparse_or_link(entry.path):
                    exclusions["reparse"] = exclusions.get("reparse", 0) + 1
                    continue
                if entry.is_dir(follow_symlinks=False):
                    if entry.name.casefold() in _PRUNE_SEGMENTS:
                        exclusions["pruned"] = exclusions.get("pruned", 0) + 1
                    else:
                        queue.append(entry.path)
                    continue
                if not entry.is_file(follow_symlinks=False):
                    continue
            except OSError:
                exclusions["scan_error"] = exclusions.get("scan_error", 0) + 1
                continue
            denied = _path_deny_reason(rel_path)
            if denied:
                exclusions[denied] = exclusions.get(denied, 0) + 1
                continue
            if Path(entry.name).suffix.casefold() not in _ALLOWED_SUFFIXES:
                exclusions["unsupported_extension"] = exclusions.get("unsupported_extension", 0) + 1
                continue
            item = _candidate(rel_path, entity, "deterministic")
            if item is None:
                item, used = _content_candidate(repo_root, rel_path, entity, scan_budget, exclusions)
                scan_budget -= used
            if item is not None:
                candidates.append(item)
    return _dedupe_candidates(candidates)


def _select(candidates: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    selected: List[Dict[str, Any]] = []
    limits = {
        "implementation_source": 6, "test": 3, "contract": 2, "readme": 1,
        "public": 1, "module": 1, "documentation": 1,
    }
    counts: Dict[str, int] = {}
    # Evidence minima first, then fill by deterministic rank.
    for wanted in ("implementation_source", "test", "contract", "readme", "public", "module"):
        for item in candidates:
            if item["category"] == wanted and item not in selected:
                selected.append(item)
                counts[wanted] = counts.get(wanted, 0) + 1
                break
    for item in candidates:
        if len(selected) >= MAX_SELECTED_PATHS:
            break
        category = item["category"]
        if item in selected or counts.get(category, 0) >= limits.get(category, 1):
            continue
        selected.append(item)
        counts[category] = counts.get(category, 0) + 1
    return selected[:MAX_SELECTED_PATHS]


def _empty_audit_result() -> Dict[str, Any]:
    return {"receipt": {
        "schema_version": "repo_audit_grounding.v1",
        "applied": False,
        "audit_intent": False,
        "entity": None,
        "aliases": [],
        "holo_first": True,
        "holo_evidence_refs": [],
        "deterministic_candidates": [],
        "selected": [],
        "exclusion_counts": {},
        "search_mode": "not_applicable",
        "cross_check_agreement": {"paths": [], "count": 0},
        "coverage": {"verdict": "NOT_APPLICABLE", "reasons": []},
    }, "hits": [], "telemetry": None}


def _read_selected(
    repo_root: Path, selected_candidates: Sequence[Dict[str, Any]], exclusions: Dict[str, int]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, str]]]:
    selected: List[Dict[str, Any]] = []
    hits: List[Dict[str, Any]] = []
    rejected: List[Dict[str, str]] = []
    remaining = TOTAL_READ_BUDGET_BYTES
    for item in selected_candidates:
        read = secure_read_repo_head_file(
            repo_root, item["path"], byte_cap=PER_FILE_READ_BYTES, remaining_budget=remaining
        )
        if not read.get("ok"):
            reason = str(read.get("reason") or "read_rejected")
            exclusions[reason] = exclusions.get(reason, 0) + 1
            rejected.append({"path": item["path"], "reason": reason})
            continue
        if read["bytes"] <= 0:
            exclusions["empty_file"] = exclusions.get("empty_file", 0) + 1
            rejected.append({"path": item["path"], "reason": "empty_file"})
            continue
        remaining -= read["bytes"]
        record = {
            "path": item["path"], "digest": read["digest"], "bytes": read["bytes"],
            "category": item["category"], "truncated": read["truncated"],
            "repo_head_sha": read["repo_head_sha"], "git_mode": read["git_mode"],
            "blob_oid": read["blob_oid"],
        }
        selected.append(record)
        hits.append({
            "need": f"repo audit evidence: {item['category']}",
            "location": item["path"],
            "similarity": "100.0%",
            "type": "code",
            "priority": 0,
            "direct_read": True,
            "repo_audit_grounding": True,
            "repo_audit_category": item["category"],
            "content": read["content"],
            "content_digest": read["digest"],
            "content_truncated": read["truncated"],
        })
    return selected, hits, rejected


def _coverage(selected: Sequence[Dict[str, Any]]) -> Tuple[str, List[str]]:
    selected_categories = {item["category"] for item in selected}
    coverage_reasons: List[str] = []
    if "implementation_source" not in selected_categories:
        coverage_reasons.append("implementation_source_missing")
    if not selected_categories.intersection({"test", "contract"}):
        coverage_reasons.append("independent_test_or_contract_missing")
    return ("PASS" if not coverage_reasons else "INCOMPLETE"), coverage_reasons


def _build_receipt(intent, holo_refs, holo_sufficient, deterministic, selected, exclusions):
    verdict, coverage_reasons = _coverage(selected)
    selected_paths = {item["path"].casefold(): item["path"] for item in selected}
    agreement = sorted(
        (selected_paths[path.casefold()] for path in holo_refs if path.casefold() in selected_paths),
        key=str.casefold,
    )
    return {
        "schema_version": "repo_audit_grounding.v1",
        "applied": True,
        "audit_intent": True,
        "entity": intent["entity"],
        "aliases": list(dict.fromkeys((str(intent["raw_entity"]), str(intent["entity"])))),
        "holo_first": True,
        "holo_evidence_refs": holo_refs,
        "holo_evidence_sufficient": holo_sufficient,
        "deterministic_candidates": [
            {"path": item["path"], "score": item["score"], "category": item["category"], "reasons": item["reasons"]}
            for item in deterministic[:MAX_SELECTED_PATHS * 3]
        ],
        "selected": selected,
        "exclusion_counts": dict(sorted(exclusions.items())),
        "search_mode": "holo_evidence_only" if holo_sufficient else "holo_then_deterministic",
        "cross_check_agreement": {"paths": agreement, "count": len(agreement)},
        "coverage": {"verdict": verdict, "reasons": coverage_reasons},
    }


def _build_telemetry(selected, rejected):
    return {
        "direct_read_fallback_used": bool(selected),
        "direct_read_paths": [item["path"] for item in selected],
        "direct_read_rejected": rejected,
        "direct_read_bytes": sum(item["bytes"] for item in selected),
        "direct_read_truncated": [
            {"path": item["path"], "bytes": item["bytes"]} for item in selected if item["truncated"]
        ],
        "per_file_budget": PER_FILE_READ_BYTES,
        "total_budget": TOTAL_READ_BUDGET_BYTES,
        "max_targets": MAX_SELECTED_PATHS,
        "repo_audit_grounding": True,
    }


def build_repo_audit_grounding(
    repo_root: Path, task: str, search_payload: Dict[str, Any]
) -> Dict[str, Any]:
    """Return stable receipt, content-bearing hits, and direct-read telemetry."""
    intent = detect_repo_audit_intent(task)
    if not intent["audit_intent"]:
        return _empty_audit_result()
    entity = str(intent["entity"])
    holo_candidates, holo_refs = _holo_paths(search_payload or {}, entity)
    exclusions: Dict[str, int] = {}
    holo_selected, holo_hits, holo_rejected = _read_selected(
        repo_root, _select(holo_candidates), exclusions
    )
    holo_verdict, _holo_reasons = _coverage(holo_selected)
    holo_sufficient = holo_verdict == "PASS"
    deterministic: List[Dict[str, Any]] = []
    candidates = list(holo_candidates)
    if holo_sufficient:
        selected, hits, rejected = holo_selected, holo_hits, holo_rejected
    else:
        deterministic = _discover(repo_root, entity, exclusions)
        candidates = _dedupe_candidates(candidates + deterministic)
        selected, hits, rejected = _read_selected(repo_root, _select(candidates), exclusions)
        rejected = holo_rejected + rejected
    receipt = _build_receipt(
        intent, holo_refs, holo_sufficient, deterministic, selected, exclusions
    )
    return {"receipt": receipt, "hits": hits, "telemetry": _build_telemetry(selected, rejected)}
