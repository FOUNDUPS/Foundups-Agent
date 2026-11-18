"""Immutability regressions for current-queue authority admissions."""

from __future__ import annotations

import copy
import pickle

import pytest

from modules.communication.moltbot_bridge.src.reddog_queue_authority_admission import (
    VerifiedQueueAuthorityAdmission,
    consume_current_queue_authority,
)


class _Request:
    def to_dict(self):
        return {"request": "unsealed"}


def test_queue_authority_admission_cannot_be_constructed_directly() -> None:
    with pytest.raises(
        TypeError, match="queue_authority_admission_direct_construction_forbidden"
    ):
        VerifiedQueueAuthorityAdmission()


def test_unsealed_queue_authority_admission_is_rejected() -> None:
    unsealed = object.__new__(VerifiedQueueAuthorityAdmission)

    assert consume_current_queue_authority(unsealed, request=_Request()) is False


@pytest.mark.parametrize(
    "operation",
    (
        copy.copy,
        copy.deepcopy,
        pickle.dumps,
    ),
)
def test_queue_authority_admission_cannot_be_copied_or_serialized(operation) -> None:
    unsealed = object.__new__(VerifiedQueueAuthorityAdmission)

    with pytest.raises(TypeError, match="queue_authority_admission_.*_forbidden"):
        operation(unsealed)
