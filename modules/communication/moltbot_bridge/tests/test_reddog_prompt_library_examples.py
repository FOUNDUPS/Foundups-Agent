"""Tests for REDDOG_PROMPT_EXAMPLES_FIXTURE_LIBRARY_PHASE1."""

import ast
from pathlib import Path

from modules.communication.moltbot_bridge.src import reddog_prompt_library_examples as lib


REPO_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    REPO_ROOT
    / "modules"
    / "communication"
    / "moltbot_bridge"
    / "src"
    / "reddog_prompt_library_examples.py"
)


def test_prompt_library_examples_validate_clean() -> None:
    assert lib.validate_prompt_library_examples() == ()


def test_prompt_library_examples_have_positive_and_negative_sets() -> None:
    assert len(lib.positive_prompt_examples()) >= 3
    assert len(lib.negative_prompt_examples()) >= 4


def test_prompt_library_examples_cover_key_domains() -> None:
    domains = {example.domain_profile for example in lib.all_prompt_examples()}
    assert lib.DOMAIN_WSP109 in domains
    assert lib.DOMAIN_HOLOINDEX in domains
    assert lib.DOMAIN_RUNTIME_DIAGNOSTIC in domains
    assert lib.DOMAIN_SECURITY in domains


def test_prompt_library_examples_have_stable_unique_digests() -> None:
    examples = lib.all_prompt_examples()
    digests = [example.prompt_digest for example in examples]
    assert len(digests) == len(set(digests))
    assert all(digest.startswith("sha256:") and len(digest) == 71 for digest in digests)


def test_positive_wsp109_prompt_is_executable_shape() -> None:
    example = next(e for e in lib.all_prompt_examples() if e.example_id == "positive_wsp109_intake_builder_worker_prompt")
    assert example.polarity == lib.POLARITY_POSITIVE
    assert "AUTHOR / IMPLEMENT" in example.prompt_text
    assert "READ_FIRST:" in example.prompt_text
    assert "RETURN:" in example.prompt_text
    assert "VERIFIED_READY" in example.prompt_text


def test_negative_prompt_drift_fixture_rejects_wrong_slice() -> None:
    example = next(e for e in lib.all_prompt_examples() if e.example_id == "negative_prompt_drift_daemon_summary_instead_of_worker_prompt")
    assert example.polarity == lib.POLARITY_NEGATIVE
    assert example.failure_class == "requested_slice_not_satisfied"
    assert "REDDOG_DAEMON_OUTPUT_DIAGNOSTIC_SUMMARY_PHASE1" in example.prompt_text
    assert "REDDOG_FUSION_QUORUM_AND_PROMPT_RELEVANCE_GATE_PHASE1" not in example.prompt_text


def test_negative_authority_fixture_records_receipt_gap() -> None:
    example = next(e for e in lib.all_prompt_examples() if e.example_id == "negative_live_authority_without_receipts")
    assert example.failure_class == "authority_bypass_request"
    assert "Skip signature" in example.prompt_text
    assert "PromptReceipt" not in example.prompt_text


def test_negative_external_research_fixture_is_not_repo_file() -> None:
    example = next(e for e in lib.all_prompt_examples() if e.example_id == "negative_external_url_as_repo_direct_read_target")
    assert example.failure_class == "external_research_misclassified_as_repo_file"
    assert "https://github.com/karpathy/autoresearch" in example.prompt_text


def test_prompt_library_examples_module_has_no_runtime_side_effect_imports() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    banned_imports = {
        "subprocess",
        "os",
        "requests",
        "urllib",
        "httpx",
        "socket",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in banned_imports
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] not in banned_imports


def test_prompt_library_examples_module_ascii_only() -> None:
    raw = MODULE_PATH.read_bytes()
    assert [b for b in raw if b > 127] == []
    assert raw.count(0) == 0

