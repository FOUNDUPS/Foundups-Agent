"""Runtime coverage for the opt-in public discovery plane and default member path."""
from pathlib import Path
import shutil
import subprocess


def test_public_and_member_product_concierge_runtime():
    node = shutil.which("node")
    assert node, "Node is required for the shared product concierge runtime gate"
    fixture = Path(__file__).with_name("public_discovery_concierge_vm.mjs")
    result = subprocess.run(
        [node, str(fixture)], capture_output=True, text=True, timeout=45, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
