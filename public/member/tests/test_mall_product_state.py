"""Behavioral storage and worker-cache boundaries for a product in the Mall shell."""
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(not shutil.which("node"), reason="Node is required for Mall state runtime coverage")
def test_mall_product_state_and_service_worker_runtime():
    """Execute actual owners with adversarial storage, routes, public responses, and HPC probe allowlists."""
    member_dir = Path(__file__).resolve().parent.parent
    repo_root = member_dir.parent.parent
    assert not (member_dir / "playback-probe").exists(), (
        "Preview-only /member/playback-probe/ must not be committed under public/"
    )
    script = Path(__file__).with_name("mall_product_state_vm.mjs")
    result = subprocess.run(["node", str(script)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Mall product state and service worker runtime: 23 passed." in result.stdout

    probe_vm = (
        repo_root
        / "modules"
        / "foundups"
        / "pfmall"
        / "tests"
        / "fixtures"
        / "hpc_iphone_playback_probe_vm.mjs"
    )
    probe_result = subprocess.run(["node", str(probe_vm)], capture_output=True, text=True, timeout=30)
    assert probe_result.returncode == 0, probe_result.stdout + probe_result.stderr
    assert "HPC iPhone playback probe runtime: 6 passed." in probe_result.stdout
