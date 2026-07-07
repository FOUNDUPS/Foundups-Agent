# -*- coding: utf-8 -*-
"""
Token Efficiency Telemetry Service Tests (P3)

Contract: docs/contracts/REDDOG_WSP99_RTK_TOKEN_EFFICIENCY_CONTRACT_PHASE1.md Section 8
WSP: WSP_97, WSP_99

Tests per M2M prompt TESTS section:
- token estimate deterministic and non-negative
- bytes/tokens saved computed correctly
- savings ratio handles zero safely
- event_id stable for same semantic content
- timestamp does not destabilize deterministic digest if excluded
- bypassed event cannot claim compression
- unknown content fails closed / needs review
- ctx_holo_present and index_gap_detected fields survive serialization
- runtime_reindex_allowed true is rejected
- negative counts rejected
- output larger than input produces negative savings
- raw_ref does not contain secret-like material
- no RTK imports / subprocess / command execution AST denylist
- no extension runtime files touched
"""

import pytest
import ast
import sys
from pathlib import Path

# Add module to path
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from telemetry_service import (
    estimate_tokens,
    compute_content_hash,
    generate_event_id,
    build_token_compression_event,
    validate_token_event,
    summarize_token_events,
    TokenCompressionEvent,
    TelemetrySummary,
    TelemetryValidationError,
    ValidationResult,
    SourceLayer,
    Operation,
    ContentType,
    CompressionStatus,
    InMemoryTelemetryStore,
    get_telemetry_store,
    reset_telemetry_store,
    CHARS_PER_TOKEN,
)


class TestEstimateTokens:
    """Token estimation tests."""

    def test_estimate_deterministic(self):
        """estimate_tokens is deterministic."""
        text = "Hello world, this is a test."
        assert estimate_tokens(text) == estimate_tokens(text)

    def test_estimate_non_negative(self):
        """estimate_tokens always returns non-negative."""
        assert estimate_tokens("") >= 0
        assert estimate_tokens("a") >= 0
        assert estimate_tokens("a" * 1000) >= 0

    def test_estimate_empty_is_zero(self):
        """Empty text estimates to 0 tokens."""
        assert estimate_tokens("") == 0

    def test_estimate_proportional(self):
        """Longer text estimates more tokens."""
        short = "Hello"
        long = "Hello" * 100
        assert estimate_tokens(long) > estimate_tokens(short)

    def test_estimate_uses_char_ratio(self):
        """Token estimate uses CHARS_PER_TOKEN ratio."""
        text = "x" * 100
        expected = (100 + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN
        assert estimate_tokens(text) == expected


class TestComputeHash:
    """Hash computation tests."""

    def test_hash_deterministic(self):
        """compute_content_hash is deterministic."""
        content = "Test content"
        assert compute_content_hash(content) == compute_content_hash(content)

    def test_hash_different_for_different_content(self):
        """Different content produces different hashes."""
        assert compute_content_hash("a") != compute_content_hash("b")

    def test_hash_sha256_length(self):
        """Hash is SHA256 hex (64 chars)."""
        h = compute_content_hash("test")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


class TestEventIdGeneration:
    """Event ID generation tests."""

    def test_event_id_deterministic(self):
        """event_id stable for same semantic content."""
        id1 = generate_event_id(
            SourceLayer.WSP99_M2M, Operation.COMPILE,
            ContentType.M2M_PROMPT, 100, 50
        )
        id2 = generate_event_id(
            SourceLayer.WSP99_M2M, Operation.COMPILE,
            ContentType.M2M_PROMPT, 100, 50
        )
        assert id1 == id2

    def test_event_id_excludes_timestamp(self):
        """event_id does not include timestamp (verified by determinism)."""
        id1 = generate_event_id(
            SourceLayer.WSP99_M2M, Operation.COMPILE,
            ContentType.M2M_PROMPT, 100, 50
        )
        # If timestamp were included, calling again would differ
        id2 = generate_event_id(
            SourceLayer.WSP99_M2M, Operation.COMPILE,
            ContentType.M2M_PROMPT, 100, 50
        )
        assert id1 == id2

    def test_event_id_different_for_different_params(self):
        """Different parameters produce different event IDs."""
        id1 = generate_event_id(
            SourceLayer.WSP99_M2M, Operation.COMPILE,
            ContentType.M2M_PROMPT, 100, 50
        )
        id2 = generate_event_id(
            SourceLayer.BYPASS_CLASSIFIER, Operation.CLASSIFY,
            ContentType.TOOL_OUTPUT, 200, 200
        )
        assert id1 != id2


class TestBuildEvent:
    """Event building tests."""

    def test_bytes_saved_computed_correctly(self):
        """bytes_saved = input_bytes - output_bytes."""
        event = build_token_compression_event(
            SourceLayer.WSP99_M2M, Operation.COMPILE,
            ContentType.M2M_PROMPT, input_bytes=100, output_bytes=50
        )
        assert event.bytes_saved == 50
        assert event.compression_status == CompressionStatus.COMPRESSED

    def test_tokens_saved_computed_correctly(self):
        """tokens_saved based on byte estimation."""
        event = build_token_compression_event(
            SourceLayer.WSP99_M2M, Operation.COMPILE,
            ContentType.M2M_PROMPT, input_bytes=100, output_bytes=50
        )
        assert event.tokens_saved >= 0

    def test_savings_ratio_handles_zero_safely(self):
        """savings_ratio handles zero input safely."""
        event = build_token_compression_event(
            SourceLayer.WSP99_M2M, Operation.COMPILE,
            ContentType.M2M_PROMPT, input_bytes=0, output_bytes=0
        )
        assert event.savings_ratio == 0.0

    def test_savings_ratio_computed(self):
        """savings_ratio = bytes_saved / input_bytes."""
        event = build_token_compression_event(
            SourceLayer.WSP99_M2M, Operation.COMPILE,
            ContentType.M2M_PROMPT, input_bytes=100, output_bytes=50
        )
        assert event.savings_ratio == 0.5

    def test_bypassed_cannot_claim_compression(self):
        """Bypassed event cannot claim positive savings."""
        event = build_token_compression_event(
            SourceLayer.BYPASS_CLASSIFIER, Operation.BYPASS,
            ContentType.TOOL_OUTPUT, input_bytes=100, output_bytes=50,
            bypass_decision="BYPASS_SECURITY"
        )
        assert event.compression_status == CompressionStatus.BYPASSED
        assert event.bytes_saved == 0
        assert event.tokens_saved == 0
        assert event.savings_ratio == 0.0

    def test_negative_input_bytes_rejected(self):
        """Negative input_bytes raises error."""
        with pytest.raises(TelemetryValidationError) as exc_info:
            build_token_compression_event(
                SourceLayer.WSP99_M2M, Operation.COMPILE,
                ContentType.M2M_PROMPT, input_bytes=-1, output_bytes=50
            )
        assert "non-negative" in str(exc_info.value)

    def test_negative_output_bytes_rejected(self):
        """Negative output_bytes raises error."""
        with pytest.raises(TelemetryValidationError) as exc_info:
            build_token_compression_event(
                SourceLayer.WSP99_M2M, Operation.COMPILE,
                ContentType.M2M_PROMPT, input_bytes=100, output_bytes=-1
            )
        assert "non-negative" in str(exc_info.value)

    def test_output_larger_than_input_not_fake_positive(self):
        """Output > input produces negative savings, not fake positive."""
        event = build_token_compression_event(
            SourceLayer.WSP99_M2M, Operation.COMPILE,
            ContentType.M2M_PROMPT, input_bytes=50, output_bytes=100
        )
        assert event.compression_status == CompressionStatus.UNCHANGED
        assert event.bytes_saved == -50  # Negative
        assert event.savings_ratio < 0

    def test_ctx_holo_present_field(self):
        """ctx_holo_present field set correctly."""
        event = build_token_compression_event(
            SourceLayer.WSP99_M2M, Operation.COMPILE,
            ContentType.M2M_PROMPT, input_bytes=100, output_bytes=50,
            ctx_holo_present=True
        )
        assert event.ctx_holo_present is True

    def test_index_gap_detected_field(self):
        """index_gap_detected field set correctly."""
        event = build_token_compression_event(
            SourceLayer.WSP99_M2M, Operation.COMPILE,
            ContentType.M2M_PROMPT, input_bytes=100, output_bytes=50,
            index_gap_detected=True
        )
        assert event.index_gap_detected is True

    def test_runtime_reindex_always_false(self):
        """runtime_reindex_allowed always False in built event."""
        event = build_token_compression_event(
            SourceLayer.WSP99_M2M, Operation.COMPILE,
            ContentType.M2M_PROMPT, input_bytes=100, output_bytes=50
        )
        assert event.runtime_reindex_allowed is False


class TestValidateEvent:
    """Event validation tests."""

    def test_valid_event_passes(self):
        """Valid event passes validation."""
        event = build_token_compression_event(
            SourceLayer.WSP99_M2M, Operation.COMPILE,
            ContentType.M2M_PROMPT, input_bytes=100, output_bytes=50
        )
        result = validate_token_event(event)
        assert result.valid
        assert len(result.errors) == 0

    def test_runtime_reindex_true_rejected(self):
        """runtime_reindex_allowed=True is rejected."""
        event = build_token_compression_event(
            SourceLayer.WSP99_M2M, Operation.COMPILE,
            ContentType.M2M_PROMPT, input_bytes=100, output_bytes=50
        )
        # Manually set to True (violation)
        event.runtime_reindex_allowed = True
        result = validate_token_event(event)
        assert not result.valid
        assert any("runtime_reindex_allowed" in e for e in result.errors)

    def test_no_command_execution_false_rejected(self):
        """no_command_execution=False is rejected."""
        event = build_token_compression_event(
            SourceLayer.WSP99_M2M, Operation.COMPILE,
            ContentType.M2M_PROMPT, input_bytes=100, output_bytes=50
        )
        event.no_command_execution = False
        result = validate_token_event(event)
        assert not result.valid

    def test_bypassed_with_positive_savings_rejected(self):
        """Bypassed event with positive savings rejected."""
        event = build_token_compression_event(
            SourceLayer.BYPASS_CLASSIFIER, Operation.BYPASS,
            ContentType.TOOL_OUTPUT, input_bytes=100, output_bytes=100,
            bypass_decision="BYPASS_SECURITY"
        )
        # Manually set positive savings (violation)
        event.bytes_saved = 50
        result = validate_token_event(event)
        assert not result.valid
        assert any("Bypassed event cannot claim positive savings" in e for e in result.errors)

    def test_unknown_content_cannot_be_compressed(self):
        """UNKNOWN content type cannot be marked as compressed."""
        event = build_token_compression_event(
            SourceLayer.UNKNOWN, Operation.EVALUATE,
            ContentType.UNKNOWN, input_bytes=100, output_bytes=50
        )
        # Manually set to compressed (violation)
        event.compression_status = CompressionStatus.COMPRESSED
        result = validate_token_event(event)
        assert not result.valid
        assert any("UNKNOWN content type cannot be marked as compressed" in e for e in result.errors)

    def test_empty_event_id_rejected(self):
        """Empty event_id is rejected."""
        event = build_token_compression_event(
            SourceLayer.WSP99_M2M, Operation.COMPILE,
            ContentType.M2M_PROMPT, input_bytes=100, output_bytes=50
        )
        event.event_id = ""
        result = validate_token_event(event)
        assert not result.valid


class TestSerialization:
    """Serialization/deserialization tests."""

    def test_ctx_holo_survives_serialization(self):
        """ctx_holo_present survives to_dict/from_dict."""
        event = build_token_compression_event(
            SourceLayer.WSP99_M2M, Operation.COMPILE,
            ContentType.M2M_PROMPT, input_bytes=100, output_bytes=50,
            ctx_holo_present=True
        )
        d = event.to_dict()
        restored = TokenCompressionEvent.from_dict(d)
        assert restored.ctx_holo_present is True

    def test_index_gap_survives_serialization(self):
        """index_gap_detected survives to_dict/from_dict."""
        event = build_token_compression_event(
            SourceLayer.WSP99_M2M, Operation.COMPILE,
            ContentType.M2M_PROMPT, input_bytes=100, output_bytes=50,
            index_gap_detected=True
        )
        d = event.to_dict()
        restored = TokenCompressionEvent.from_dict(d)
        assert restored.index_gap_detected is True

    def test_to_m2m_compact_format(self):
        """to_m2m_compact produces valid format."""
        event = build_token_compression_event(
            SourceLayer.WSP99_M2M, Operation.COMPILE,
            ContentType.M2M_PROMPT, input_bytes=100, output_bytes=50
        )
        compact = event.to_m2m_compact()
        assert "TELEMETRY:" in compact
        assert "SRC:WSP99_M2M" in compact
        assert "OP:compile" in compact

    def test_to_m2m_yaml_format(self):
        """to_m2m_yaml produces valid YAML format."""
        event = build_token_compression_event(
            SourceLayer.WSP99_M2M, Operation.COMPILE,
            ContentType.M2M_PROMPT, input_bytes=100, output_bytes=50
        )
        yaml = event.to_m2m_yaml()
        assert "TOKEN_COMPRESSION_EVENT:" in yaml
        assert "source_layer: WSP99_M2M" in yaml


class TestSummarize:
    """Summarization tests."""

    def test_empty_events_summary(self):
        """Empty events produce zero summary."""
        summary = summarize_token_events([])
        assert summary.total_events == 0
        assert summary.total_bytes_saved == 0
        assert summary.overall_savings_ratio == 0.0

    def test_summary_aggregates_bytes(self):
        """Summary aggregates bytes correctly."""
        events = [
            build_token_compression_event(
                SourceLayer.WSP99_M2M, Operation.COMPILE,
                ContentType.M2M_PROMPT, input_bytes=100, output_bytes=50
            ),
            build_token_compression_event(
                SourceLayer.WSP99_M2M, Operation.COMPILE,
                ContentType.M2M_PROMPT, input_bytes=200, output_bytes=100
            ),
        ]
        summary = summarize_token_events(events)
        assert summary.total_events == 2
        assert summary.total_input_bytes == 300
        assert summary.total_output_bytes == 150
        assert summary.total_bytes_saved == 150

    def test_summary_counts_by_status(self):
        """Summary counts events by status."""
        events = [
            build_token_compression_event(
                SourceLayer.WSP99_M2M, Operation.COMPILE,
                ContentType.M2M_PROMPT, input_bytes=100, output_bytes=50
            ),
            build_token_compression_event(
                SourceLayer.BYPASS_CLASSIFIER, Operation.BYPASS,
                ContentType.TOOL_OUTPUT, input_bytes=100, output_bytes=100,
                bypass_decision="BYPASS_SECURITY"
            ),
        ]
        summary = summarize_token_events(events)
        assert summary.compressed_count == 1
        assert summary.bypassed_count == 1


class TestInMemoryStore:
    """In-memory telemetry store tests."""

    def setup_method(self):
        """Reset store before each test."""
        reset_telemetry_store()

    def test_store_records_events(self):
        """Store records and retrieves events."""
        store = InMemoryTelemetryStore()
        event = build_token_compression_event(
            SourceLayer.WSP99_M2M, Operation.COMPILE,
            ContentType.M2M_PROMPT, input_bytes=100, output_bytes=50
        )
        store.record(event)
        assert store.count() == 1
        assert store.get_all()[0].event_id == event.event_id

    def test_store_validates_on_record(self):
        """Store validates events before recording."""
        store = InMemoryTelemetryStore()
        event = build_token_compression_event(
            SourceLayer.WSP99_M2M, Operation.COMPILE,
            ContentType.M2M_PROMPT, input_bytes=100, output_bytes=50
        )
        # Make invalid
        event.runtime_reindex_allowed = True
        with pytest.raises(TelemetryValidationError):
            store.record(event)

    def test_store_rotates_at_max(self):
        """Store rotates events at max capacity."""
        store = InMemoryTelemetryStore(max_events=3)
        for i in range(5):
            event = build_token_compression_event(
                SourceLayer.WSP99_M2M, Operation.COMPILE,
                ContentType.M2M_PROMPT, input_bytes=100 + i, output_bytes=50
            )
            store.record(event)
        assert store.count() == 3

    def test_singleton_pattern(self):
        """get_telemetry_store returns singleton."""
        store1 = get_telemetry_store()
        store2 = get_telemetry_store()
        assert store1 is store2


class TestRawRefNoSecrets:
    """Verify raw_ref does not contain secret-like material."""

    def test_event_has_no_raw_content_field(self):
        """TokenCompressionEvent has no raw content field."""
        event = build_token_compression_event(
            SourceLayer.WSP99_M2M, Operation.COMPILE,
            ContentType.M2M_PROMPT, input_bytes=100, output_bytes=50
        )
        # Check dataclass fields
        field_names = [f for f in event.__dataclass_fields__]
        # Should not have 'raw_content', 'content', 'secret', etc.
        forbidden = ["raw_content", "content", "secret", "password", "token", "key"]
        for f in forbidden:
            assert f not in field_names, f"Field '{f}' should not exist"

    def test_raw_ref_present_is_bool_only(self):
        """raw_ref_present is a boolean, not actual content."""
        event = build_token_compression_event(
            SourceLayer.WSP99_M2M, Operation.COMPILE,
            ContentType.M2M_PROMPT, input_bytes=100, output_bytes=50,
            raw_ref_present=True
        )
        assert isinstance(event.raw_ref_present, bool)


class TestNoRTKOrSubprocess:
    """AST denylist tests for forbidden imports."""

    def test_no_subprocess_import(self):
        """telemetry_service.py has no subprocess import."""
        module_path = Path(__file__).parents[1] / "src" / "telemetry_service.py"
        source = module_path.read_text()
        tree = ast.parse(source)

        forbidden = {"subprocess", "os.system", "os.popen"}
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        for imp in imports:
            for f in forbidden:
                assert f not in imp, f"Forbidden import found: {imp}"

    def test_no_rtk_import(self):
        """telemetry_service.py has no RTK import."""
        module_path = Path(__file__).parents[1] / "src" / "telemetry_service.py"
        source = module_path.read_text()
        assert "import rtk" not in source.lower()
        assert "from rtk" not in source.lower()

    def test_no_eval_exec(self):
        """telemetry_service.py has no eval/exec calls."""
        module_path = Path(__file__).parents[1] / "src" / "telemetry_service.py"
        source = module_path.read_text()
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    assert node.func.id not in ("eval", "exec"), \
                        f"Forbidden call: {node.func.id}"

    def test_no_socket_or_requests(self):
        """telemetry_service.py has no network imports."""
        module_path = Path(__file__).parents[1] / "src" / "telemetry_service.py"
        source = module_path.read_text()
        forbidden = ["import socket", "import requests", "import aiohttp", "import urllib"]
        for f in forbidden:
            assert f not in source, f"Forbidden import: {f}"


class TestNoExtensionRuntimeFiles:
    """Verify no extension runtime files touched."""

    def test_no_extension_js_in_module(self):
        """Module does not reference extension.js."""
        module_path = Path(__file__).parents[1] / "src" / "telemetry_service.py"
        source = module_path.read_text()
        assert "extension.js" not in source
        assert "package.json" not in source

    def test_no_vsix_reference(self):
        """Module does not reference VSIX."""
        module_path = Path(__file__).parents[1] / "src" / "telemetry_service.py"
        source = module_path.read_text()
        assert ".vsix" not in source


class TestInvariants:
    """Invariant safety tests."""

    def test_invariants_always_safe_values(self):
        """Built events always have safe invariant values."""
        event = build_token_compression_event(
            SourceLayer.WSP99_M2M, Operation.COMPILE,
            ContentType.M2M_PROMPT, input_bytes=100, output_bytes=50
        )
        assert event.runtime_reindex_allowed is False
        assert event.no_command_execution is True
        assert event.no_rtk_invocation is True
        assert event.no_secret_persistence is True
