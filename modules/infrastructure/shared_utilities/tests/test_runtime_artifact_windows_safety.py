"""Windows-specific identity and stream falsifiers for runtime artifacts."""

from __future__ import annotations

import os
import stat
from dataclasses import replace
from pathlib import Path

import pytest

from modules.infrastructure.shared_utilities.runtime_artifact_confined_byte_reader import (
    confined_file_identity,
    secure_digest_confined_file_impl,
)
from modules.infrastructure.shared_utilities.runtime_artifact_windows_streams import (
    require_unnamed_data_stream_only,
)


pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows-specific safety")


@pytest.mark.parametrize("suffix", (".exe", ".cmd"))
def test_confined_digest_accepts_only_windows_execute_projection(
    tmp_path: Path, suffix: str,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    source = root / f"launcher{suffix}"
    source.write_bytes(b"launcher")
    expected = confined_file_identity(os.lstat(source))
    descriptor = os.open(source, os.O_RDONLY)
    try:
        assert stat.S_IMODE(os.fstat(descriptor).st_mode) != stat.S_IMODE(expected.mode)
    finally:
        os.close(descriptor)

    proof = secure_digest_confined_file_impl(
        source, allowed_root=root, expected_identity=expected, max_bytes=64,
    )

    assert proof.identity == expected
    tampered = replace(expected, mode=expected.mode ^ stat.S_IWUSR)
    with pytest.raises(ValueError, match="identity_mismatch"):
        secure_digest_confined_file_impl(
            source, allowed_root=root, expected_identity=tampered, max_bytes=64,
        )


@pytest.mark.parametrize("directory", (False, True))
def test_windows_stream_enumerator_rejects_named_payload(
    tmp_path: Path, directory: bool,
) -> None:
    source = tmp_path / ("artifact-dir" if directory else "artifact.bin")
    source.mkdir() if directory else source.write_bytes(b"primary")
    require_unnamed_data_stream_only(source)
    Path(str(source) + ":reddog_audit").write_bytes(b"alternate")

    with pytest.raises(ValueError, match="alternate_stream_rejected"):
        require_unnamed_data_stream_only(source)
