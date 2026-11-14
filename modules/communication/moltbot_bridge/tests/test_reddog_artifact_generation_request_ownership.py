"""Architecture boundary for resident artifact-request derivation."""

from pathlib import Path


ROOT = Path(__file__).parents[1] / "src"
BOOTSTRAP = ROOT / "reddog_main_resident_queue_serial_loop_bootstrap.py"
PILOT_HANDLER = ROOT / "reddog_resident_queue_bounded_worker_pilot_handler.py"


def test_bounded_worker_stage_is_the_only_artifact_request_derivation_owner() -> None:
    bootstrap_source = BOOTSTRAP.read_text(encoding="utf-8")
    handler_source = PILOT_HANDLER.read_text(encoding="utf-8")

    assert "_derive_artifact_generation_request_from_chain" not in bootstrap_source
    assert "artifact_generation_request=artifact_generation_request" in bootstrap_source
    assert handler_source.count("def _derive_artifact_generation_request(") == 1
