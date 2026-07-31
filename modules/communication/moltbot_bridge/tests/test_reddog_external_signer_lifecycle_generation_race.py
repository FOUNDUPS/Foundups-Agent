"""Generation-race regressions for external signer lifecycle admission."""

from __future__ import annotations

from pathlib import Path

import pytest

from modules.communication.moltbot_bridge.src.reddog_external_signer_lifecycle_admission import (
    ExternalSignerLifecycleAdmissionError,
    create_external_signer_lifecycle_admission_boundary,
)
from modules.communication.moltbot_bridge.src.reddog_signer_runtime_generation_anchor import (
    SignerRuntimeGenerationBinding,
)
from modules.communication.moltbot_bridge.tests.reddog_signer_generation_test_support import (
    create_lifecycle_generation_authority,
)
from modules.communication.moltbot_bridge.tests.test_reddog_external_signer_lifecycle_admission import (
    _Clocks,
    _Healthcheck,
    _Observer,
    _PolicyBoundary,
    _SelectionBoundary,
    _health,
    _observation,
    _runtime,
    _sha,
)


def _next_binding(values: dict[str, object]) -> SignerRuntimeGenerationBinding:
    return SignerRuntimeGenerationBinding(
        generation=2,
        manifest_id=_sha("d"),
        artifact_generation_digest=_sha("e"),
        config_digest=str(values["config_digest"]),
        config_raw_digest=str(values["config_raw_digest"]),
        run_packet_digest=str(values["run_packet_digest"]),
    )


def _boundary(tmp_path: Path, observer):
    repo, packet_path, values = _runtime(tmp_path)
    authority, reader_boundary, writer = create_lifecycle_generation_authority(
        repo, values, return_writer=True
    )
    policy = _PolicyBoundary()
    selection = _SelectionBoundary(values)
    boundary = create_external_signer_lifecycle_admission_boundary(
        repo_root=repo,
        manifest_boundary=selection,
        generation_reader_authority=authority,
        generation_reader_authority_boundary=reader_boundary,
        os_policy_authority=policy,
        os_policy_authority_boundary=policy,
        requester_principal_id="github:mjtrout",
        os_observer=observer(writer, values),
        healthcheck_runner=_Healthcheck(_health(packet_path)),
        trusted_clock=_Clocks().wall,
    )
    return boundary, writer, values, selection


def test_generation_advance_during_observation_rejects_admission(
    tmp_path: Path,
) -> None:
    def observer(writer, values):
        base = _Observer(_observation())

        def advance(policy, *, observed_at_epoch):
            current = writer.load()
            writer.activate(
                _next_binding(values), expected_revision=current.revision
            )
            return base(policy, observed_at_epoch=observed_at_epoch)

        return advance

    boundary, _, _, selection = _boundary(tmp_path, observer)
    with pytest.raises(ExternalSignerLifecycleAdmissionError):
        boundary.admit(selection)


def test_generation_advance_before_consumption_invalidates_capability(
    tmp_path: Path,
) -> None:
    boundary, writer, values, selection = _boundary(
        tmp_path, lambda _writer, _values: _Observer(_observation())
    )
    capability = boundary.admit(selection)
    current = writer.load()
    writer.activate(_next_binding(values), expected_revision=current.revision)

    with pytest.raises(ExternalSignerLifecycleAdmissionError):
        boundary.consume(capability)
