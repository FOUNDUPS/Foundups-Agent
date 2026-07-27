"""Adversarial tests for shared runtime artifact safety helpers."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from modules.infrastructure.shared_utilities import runtime_artifact_safety
from modules.infrastructure.shared_utilities.runtime_artifact_safety import (
    confined_runtime_operation_lock,
    redact_runtime_text,
    redact_runtime_value,
    secure_append_runtime_text,
    secure_read_confined_bytes,
    secure_read_confined_text,
    validate_runtime_artifact_path,
    validate_runtime_root_path,
)


def test_windows_runtime_mutex_uses_machine_global_namespace() -> None:
    name = runtime_artifact_safety._windows_runtime_mutex_name("a" * 64)
    assert name == "Global\\FoundupsRuntime-" + "a" * 64


def test_confined_runtime_operation_lock_uses_canonical_runtime_file(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repo.mkdir()
    lock_path = runtime / "authority.transaction.lock"

    with confined_runtime_operation_lock(
        lock_path,
        repo_root=repo,
        allowed_root=runtime,
    ):
        assert lock_path.is_file()

    assert lock_path.read_bytes() == b"\0"


def test_confined_runtime_operation_lock_persists_and_recovers_after_failure(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repo.mkdir()
    lock_path = runtime / "authority.transaction.lock"

    with pytest.raises(RuntimeError, match="injected"):
        with confined_runtime_operation_lock(
            lock_path,
            repo_root=repo,
            allowed_root=runtime,
        ):
            raise RuntimeError("injected")

    assert lock_path.is_file()
    with confined_runtime_operation_lock(
        lock_path,
        repo_root=repo,
        allowed_root=runtime,
    ):
        assert lock_path.is_file()
    assert lock_path.read_bytes() == b"\0"


def test_confined_runtime_operation_lock_rejects_repository_path(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    with pytest.raises(ValueError, match="inside_repo"):
        with confined_runtime_operation_lock(
            repo / "authority.transaction.lock",
            repo_root=repo,
            allowed_root=repo,
        ):
            raise AssertionError("unreachable")


def test_runtime_artifact_path_rejects_source_and_runtime_root_escape(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repo.mkdir()
    runtime.mkdir()

    with pytest.raises(ValueError, match="inside_repo"):
        validate_runtime_artifact_path(repo / "receipt.jsonl", repo_root=repo)
    with pytest.raises(ValueError, match="outside_runtime_root"):
        validate_runtime_artifact_path(
            tmp_path / "escape.jsonl",
            repo_root=repo,
            allowed_root=runtime,
        )

    assert validate_runtime_artifact_path(
        runtime / "receipt.jsonl",
        repo_root=repo,
        allowed_root=runtime,
    ) == (runtime / "receipt.jsonl").resolve()


@pytest.mark.parametrize("path", [r"\\?\C:\repo\receipt.jsonl", r"\\.\C:\device"])
def test_runtime_artifact_path_rejects_windows_device_prefix(
    tmp_path: Path,
    path: str,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(ValueError, match="invalid"):
        validate_runtime_artifact_path(path, repo_root=repo)


def test_runtime_artifact_path_resolves_symlink_before_confinement(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    outside = tmp_path / "outside"
    repo.mkdir()
    runtime.mkdir()
    outside.mkdir()
    link = runtime / "redirect"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is unavailable")

    with pytest.raises(ValueError, match="outside_runtime_root"):
        validate_runtime_artifact_path(
            link / "receipt.jsonl",
            repo_root=repo,
            allowed_root=runtime,
        )


def test_runtime_root_rejects_repo_ancestors_and_ambiguous_names(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    with pytest.raises(ValueError, match="contains_repo"):
        validate_runtime_root_path(tmp_path, repo_root=repo)
    with pytest.raises(ValueError, match="filesystem_root"):
        validate_runtime_root_path(Path(repo.anchor), repo_root=repo)
    with pytest.raises(ValueError, match="ambiguous_component"):
        validate_runtime_root_path(tmp_path / "runtime. ", repo_root=repo)
    with pytest.raises(ValueError, match="reserved_name"):
        validate_runtime_root_path(tmp_path / "NUL" / "runtime", repo_root=repo)
    with pytest.raises(ValueError, match="alternate_stream"):
        validate_runtime_root_path(tmp_path / "runtime:stream", repo_root=repo)


def test_runtime_append_rejects_hardlink_to_repository_file(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repo.mkdir()
    runtime.mkdir()
    source = repo / "main.py"
    source.write_text("original\n", encoding="utf-8")
    target = runtime / "receipt.jsonl"
    try:
        target.hardlink_to(source)
    except OSError:
        pytest.skip("hardlink creation is unavailable")

    with pytest.raises(ValueError, match="link_count"):
        secure_append_runtime_text(
            target,
            "mutated\n",
            repo_root=repo,
            allowed_root=runtime,
        )

    assert source.read_text(encoding="utf-8") == "original\n"


def test_runtime_append_rejects_descriptor_redirected_into_repository(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repo.mkdir()
    runtime.mkdir()
    redirected = repo / "redirected.jsonl"

    def open_redirected(_path: Path) -> tuple[int, bool]:
        return os.open(redirected, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600), True

    monkeypatch.setattr(runtime_artifact_safety, "_open_runtime_file", open_redirected)
    with pytest.raises(ValueError, match="inside_repo"):
        secure_append_runtime_text(
            runtime / "receipt.jsonl",
            "payload\n",
            repo_root=repo,
            allowed_root=runtime,
        )

    assert not redirected.exists()
    assert not (repo / "receipt.jsonl.lock").exists()


def test_runtime_append_never_writes_descriptor_redirected_to_existing_source(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    repo.mkdir()
    runtime.mkdir()
    source = repo / "main.py"
    source.write_text("original\n", encoding="utf-8")

    def open_source(_path: Path) -> tuple[int, bool]:
        return os.open(source, os.O_RDWR), False

    monkeypatch.setattr(runtime_artifact_safety, "_open_runtime_file", open_source)
    with pytest.raises(ValueError, match="inside_repo"):
        secure_append_runtime_text(
            runtime / "receipt.jsonl",
            "payload\n",
            repo_root=repo,
            allowed_root=runtime,
        )

    assert source.read_text(encoding="utf-8") == "original\n"


def test_runtime_text_redaction_normalizes_bounds_and_removes_secret_shapes() -> None:
    secret = "sk-1234567890abcdefghijkl"
    payload = (
        "[ERROR] api\u200b_key="
        + secret
        + " Authorization: Bearer bearer-secret-value "
        + "Authorization: Basic dXNlcjpwYXNzd29yZA== Cookie: session_id=cookie-secret "
        + "url=https://user:password@example.test/x?access_token=query-secret "
        + "AKIAABCDEFGHIJKLMNOP AIza0123456789abcdefghijklmnopqrstuv "
        + "jwt=eyJabcdefghijk.abcdefghijkl.abcdefghijkl "
        + "-----BEGIN PRIVATE KEY-----\nprivate-material\n-----END PRIVATE KEY-----"
        + ("x" * 5000)
    )

    result = redact_runtime_text(payload, max_chars=1200)

    assert result.replacements >= 5
    for forbidden in (
        secret,
        "bearer-secret-value",
        "password@example",
        "query-secret",
        "AKIAABCDEFGHIJKLMNOP",
        "AIza0123456789",
        "cookie-secret",
        "eyJabcdefghijk",
        "private-material",
    ):
        assert forbidden not in result.text
    assert "[REDACTED" in result.text


def test_runtime_text_redaction_covers_prefixed_keys_cookies_and_partial_private_key() -> None:
    secrets = (
        "openrouter-secret",
        "aws-secret",
        "my-password",
        "query-token",
        "cookie-one",
        "cookie-two",
        "private-material-without-end-marker",
        "opaque-token-value",
        "auth-token-value",
    )
    payload = (
        "[ERROR] OPENROUTER_API_KEY=openrouter-secret "
        "AWS_SECRET_ACCESS_KEY=aws-secret MY_PASSWORD=my-password\n"
        "https://example.test/?token=query-token\n"
        "Cookie: first=cookie-one; second=cookie-two\n"
        "token=opaque-token-value auth_token=auth-token-value\n"
        "-----BEGIN PRIVATE KEY-----\nprivate-material-without-end-marker"
    )

    result = redact_runtime_text(payload, max_chars=800)

    for secret in secrets:
        assert secret not in result.text
    assert result.replacements >= 5


def test_runtime_value_recursively_redacts_sensitive_mapping_keys_and_values() -> None:
    value = {
        "OPENROUTER_API_KEY": "mapping-secret",
        "nested": [
            {
                "message": "Authorization: Bearer nested-secret",
                "token": "opaque-mapping-token",
                "csrf_token": "csrf-mapping-token",
            }
        ],
    }

    redacted = redact_runtime_value(value)
    serialized = str(redacted)

    assert "mapping-secret" not in serialized
    assert "nested-secret" not in serialized
    assert "opaque-mapping-token" not in serialized
    assert "csrf-mapping-token" not in serialized
    assert "[REDACTED]" in serialized


def test_confined_read_rejects_descriptor_final_path_outside_root(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path / "repo"
    outside = tmp_path / "outside"
    repo.mkdir()
    outside.mkdir()
    source = repo / "daemon.log"
    source.write_text("safe", encoding="utf-8")
    outside_source = outside / "daemon.log"
    outside_source.write_text("outside-marker", encoding="utf-8")
    monkeypatch.setattr(
        runtime_artifact_safety,
        "_descriptor_final_path",
        lambda _descriptor: outside_source,
    )

    with pytest.raises(ValueError, match="outside_root"):
        secure_read_confined_bytes(source, allowed_root=repo)


def test_confined_text_read_uses_one_descriptor_and_enforces_size_limit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "runtime"
    root.mkdir()
    source = root / "events.jsonl"
    source.write_text("bounded payload", encoding="utf-8")
    real_open = runtime_artifact_safety.os.open
    open_calls: list[Path] = []

    def counted_open(path, flags, *args):
        open_calls.append(Path(path))
        return real_open(path, flags, *args)

    monkeypatch.setattr(runtime_artifact_safety.os, "open", counted_open)

    assert secure_read_confined_text(
        source,
        allowed_root=root,
        max_bytes=64,
    ) == "bounded payload"
    assert open_calls == [source.resolve()]
    with pytest.raises(ValueError, match="size_limit"):
        secure_read_confined_text(
            source,
            allowed_root=root,
            max_bytes=4,
        )


def test_confined_text_read_rejects_descriptor_metadata_change(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "runtime"
    root.mkdir()
    source = root / "events.jsonl"
    source.write_text("stable", encoding="utf-8")
    real_reader = runtime_artifact_safety._read_descriptor_text

    def mutate_timestamp(descriptor: int, size: int) -> str:
        payload = real_reader(descriptor, size)
        current = source.stat()
        os.utime(
            source,
            ns=(
                current.st_atime_ns,
                current.st_mtime_ns + 1_000_000_000,
            ),
        )
        return payload

    monkeypatch.setattr(
        runtime_artifact_safety,
        "_read_descriptor_text",
        mutate_timestamp,
    )

    with pytest.raises(ValueError, match="target_changed"):
        secure_read_confined_text(source, allowed_root=root)


def test_confined_text_read_rejects_descriptor_final_path_outside_root(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "runtime"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    source = root / "events.jsonl"
    source.write_text("safe", encoding="utf-8")
    outside_source = outside / "events.jsonl"
    outside_source.write_text("outside-marker", encoding="utf-8")
    monkeypatch.setattr(
        runtime_artifact_safety,
        "_descriptor_final_path",
        lambda _descriptor: outside_source,
    )

    with pytest.raises(ValueError, match="outside_root"):
        secure_read_confined_text(source, allowed_root=root)
