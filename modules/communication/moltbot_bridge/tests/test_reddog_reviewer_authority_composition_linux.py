"""Mandatory isolated Linux-root qualification; no mocked ownership or generation."""

import json
import os
from pathlib import Path
import sys
import tempfile
import pytest

# Privileged fixtures require the dedicated runner, never an automatic unit shard.
# The existing static registry quarantines module-level guarded raises.
if (not sys.platform.startswith("linux") or os.geteuid() != 0
        or not os.environ.get("RSI_REVIEWER_TEST_ROOT")):
    raise RuntimeError("dedicated_root_linux_fixture_required")

from modules.communication.moltbot_bridge.tests.reddog_reviewer_linux_test_support import linux_fixture


@pytest.mark.parametrize("case", ["positive", "wrong_uid", "writable_owner", "symlink_owner", "stale_generation"])
def test_real_linux_reviewer_authority(monkeypatch, case):
    assert sys.platform.startswith("linux") and os.geteuid() == 0, "dedicated_root_linux_job_required"
    base = Path(os.environ["RSI_REVIEWER_TEST_ROOT"]).resolve()
    assert base.parent == Path("/root") and base.name.startswith("rsi-reviewer-")
    with tempfile.TemporaryDirectory(prefix="case-", dir=base) as directory:
        verify, call, owner = linux_fixture(monkeypatch, Path(directory))
        # This positive runs before every negative so broken fixture setup cannot pass it.
        assert verify(**call) is True
        path = call["owner_config_path"]
        if case == "wrong_uid":
            os.chown(path, 1, 1)
        elif case == "writable_owner":
            path.chmod(0o422)
        elif case == "symlink_owner":
            real = path.with_name("actual-owner.json")
            path.rename(real)
            path.symlink_to(real)
        elif case == "stale_generation":
            anchor = Path(owner["anchor_path"])
            value = json.loads(anchor.read_text(encoding="utf-8"))
            value["generation"] = 999
            anchor.write_text(json.dumps(value), encoding="utf-8")
        assert verify(**call) is (case == "positive")
