"""Private selective union of existing main policy and head runtime cases."""
import shutil, subprocess
from pathlib import Path
import pytest

@pytest.mark.skipif(not shutil.which("node"), reason="Node is required for Mall state runtime coverage")
def test_mall_product_state_and_service_worker_runtime():
    member = Path(__file__).resolve().parent.parent
    repo_root = member.parent.parent
    assert not (member / "playback-probe").exists(), "Preview-only /member/playback-probe/ must not be committed under public/"
    assert "/member/playback-probe/" not in (member / "index.html").read_text(encoding="utf-8"), "Only the preview exporter may inject its staged probe loader"
    for script, expected in [
        (Path(__file__).with_name("mall_product_state_vm.mjs"), "Mall product state and service worker runtime: 30 passed."),
        (repo_root / "modules/foundups/pfmall/tests/fixtures/hpc_iphone_playback_probe_vm.mjs", "HPC iPhone playback probe runtime: 7 passed.")
    ]:
        result = subprocess.run(["node", str(script)], capture_output=True, text=True, encoding="utf-8", timeout=30)
        assert result.returncode == 0, result.stdout + result.stderr
        assert expected in result.stdout, result.stdout + result.stderr
        if script.name == "mall_product_state_vm.mjs":
            assert "PASS VOTE collection selection does not grant member application admission" in result.stdout
