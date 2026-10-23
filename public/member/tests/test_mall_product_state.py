"""Behavioral storage and worker-cache boundaries for a product in the Mall shell."""
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(not shutil.which("node"), reason="Node is required for Mall state runtime coverage")
def test_mall_product_state_and_service_worker_runtime():
    """Execute actual owners with adversarial storage, routes and public responses."""
    script = Path(__file__).with_name("mall_product_state_vm.mjs")
    result = subprocess.run(["node", str(script)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Mall product state and service worker runtime: 17 passed." in result.stdout
