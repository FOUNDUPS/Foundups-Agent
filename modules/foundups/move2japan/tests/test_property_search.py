"""Run the actual browser-independent search adapter through the Node harness."""
from pathlib import Path
import subprocess


def test_public_property_search_contract():
    result = subprocess.run(
        ["node", str(Path(__file__).with_name("property_search.cjs"))],
        text=True, capture_output=True, timeout=20, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "12 property-search checks passed" in result.stdout
