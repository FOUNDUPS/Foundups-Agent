# Token Efficiency Module - INTERFACE

**Contract**: `docs/contracts/REDDOG_WSP99_RTK_TOKEN_EFFICIENCY_CONTRACT_PHASE1.md`
**WSP**: WSP_97, WSP_99

## Public API (P1: Bypass Classifier)

### Classes

#### `BypassClass(Enum)`

Classification categories.

```python
class BypassClass(Enum):
    BYPASS_SECURITY = "BYPASS_SECURITY"
    BYPASS_AUTH = "BYPASS_AUTH"
    BYPASS_PROVENANCE = "BYPASS_PROVENANCE"
    BYPASS_SIGNING = "BYPASS_SIGNING"
    BYPASS_PERMISSION = "BYPASS_PERMISSION"
    BYPASS_RECEIPT = "BYPASS_RECEIPT"
    ALLOW_COMPRESSION = "ALLOW_COMPRESSION"
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"
```

#### `BypassDecision`

M2M-formatted classification decision.

```python
@dataclass
class BypassDecision:
    # M2M envelope
    m2m_version: str           # "1.0"
    sender: str                # "0102-BYPASS"
    receiver: str              # "0102-ORCH"
    timestamp: str             # ISO8601
    
    # Classification
    classification: BypassClass
    bypassed: bool
    bypass_reason: str | None
    
    # Matched patterns (audit trail)
    matched_classes: list[BypassClass]
    matched_patterns: list[str]
    
    # Context (no raw content)
    command_hash: str
    output_length: int
    output_hash: str
    confidence: float
    
    # Serialization
    def to_m2m_compact(self) -> str: ...
    def to_m2m_yaml(self) -> str: ...
    def as_dict(self) -> dict: ...
```

#### `BypassClassifier`

Main classifier class.

```python
class BypassClassifier:
    def classify(
        self,
        command: str,
        output: str,
        *,
        command_hash: str = "",
        output_hash: str = "",
    ) -> BypassDecision:
        """Classify command output for bypass decision."""
        ...
    
    def should_bypass(self, content: str) -> tuple[bool, str | None]:
        """Check if content should bypass compression.
        
        Returns:
            (True, class_name) if matches bypass class
            (False, None) if safe to compress
            (True, "CLASSIFICATION_ERROR") on error
        """
        ...
    
    def get_matched_classes(self, content: str) -> list[BypassClass]:
        """Return all bypass classes matching the content."""
        ...
```

### Functions

#### `get_bypass_classifier() -> BypassClassifier`

Get or create the bypass classifier singleton.

## Invariants

1. **Fail-closed**: Unknown commands -> NEEDS_HUMAN_REVIEW (bypassed)
2. **Content-first**: Output content overrides command classification
3. **Priority order**: SECURITY > AUTH > SIGNING > PERMISSION > RECEIPT > PROVENANCE
4. **No raw storage**: Only hashes and lengths, never raw content
5. **M2M output**: All decisions in WSP-99 M2M format

## Public API (P3: Telemetry Service)

### Classes

#### `TokenCompressionEvent`

Telemetry event for token compression measurement.

```python
@dataclass
class TokenCompressionEvent:
    event_id: str
    timestamp: int
    source_layer: SourceLayer
    operation: Operation
    content_type: ContentType
    input_bytes: int
    input_estimated_tokens: int
    output_bytes: int
    output_estimated_tokens: int
    bytes_saved: int
    tokens_saved: int
    savings_ratio: float
    compression_status: CompressionStatus
    bypass_decision: str | None
    fidelity_status: str | None
    raw_ref_present: bool
    ctx_holo_present: bool
    index_gap_detected: bool
    runtime_reindex_allowed: bool  # Always False
    no_command_execution: bool     # Always True
    no_rtk_invocation: bool        # Always True
    no_secret_persistence: bool    # Always True
    
    def to_m2m_compact(self) -> str: ...
    def to_m2m_yaml(self) -> str: ...
    def to_dict(self) -> dict: ...
```

### Functions

#### `estimate_tokens(text: str) -> int`

Estimate token count from text (4 chars/token).

#### `build_token_compression_event(...) -> TokenCompressionEvent`

Build validated event with computed savings.

#### `validate_token_event(event) -> ValidationResult`

Validate event against invariants.

#### `summarize_token_events(events) -> TelemetrySummary`

Aggregate metrics from event list.

### Enums

- `SourceLayer`: WSP99_M2M, RTK_EVALUATION, BYPASS_CLASSIFIER, FIDELITY_GATE, UNKNOWN
- `Operation`: COMPILE, DECOMPILE, CLASSIFY, EVALUATE, BYPASS, FIDELITY_CHECK
- `ContentType`: M2M_PROMPT, TOOL_OUTPUT, RAW_REF, UNKNOWN
- `CompressionStatus`: COMPRESSED, BYPASSED, UNCHANGED, ERROR, NOT_APPLICABLE

## Public API (P5: RTK Evaluation Dry-Run)

P5 evaluates caller-supplied candidate output. It does not invoke RTK, execute a
command, or authorize runtime compression.

### Classes

#### `RtkEvaluationDryRunResult`

```python
@dataclass
class RtkEvaluationDryRunResult:
    evaluation_id: str
    decision: RtkDryRunDecision
    command_digest: str
    raw_output_digest: str
    candidate_output_digest: str
    raw_ref_digest: str
    telemetry_event_id: str | None
    input_bytes: int
    candidate_bytes: int
    bytes_saved: int
    tokens_saved: int
    savings_ratio: float
    bypass_class: str | None
    rejection_reasons: list[str]
    dry_run_only: bool            # Always True
    rtk_invoked: bool             # Always False
    command_executed: bool        # Always False
    compression_performed: bool   # Always False
    raw_content_persisted: bool   # Always False
    runtime_reindex_allowed: bool # Always False
```

### Functions

#### `evaluate_rtk_candidate_dry_run(...) -> RtkEvaluationDryRunResult`

Evaluates a candidate compressed output using:

- a P4 compute decision whose routing is `ALLOW_EVALUATION_DRY_RUN`
- content-level bypass classification over both raw and candidate output
- a mandatory `raw_ref` recovery path
- in-memory `RTK_EVALUATION` telemetry

Acceptance means the candidate is measurable and safe for dry-run evaluation.
It is not permission to wire RTK into OpenClaw, Hermes, WRE, or extension runtime.

## Not Implemented (Future Phases)

| Component | Phase | Status |
|-----------|-------|--------|
| RTK adapter | P6 | SPECIFIED_NOT_IMPLEMENTED |
| Compression seam | P6 | SPECIFIED_NOT_IMPLEMENTED |
