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

## Public API (P2: Compact Fidelity Gate)

P2 fidelity clarification (2026-09-13): the existing
`M2MFidelityGate.assert_fidelity(...)` result's `fail_conditions_match` compares
the requested stop conditions with both the compiled object and the parsed
compact packet. A lossy comma/bracket round-trip returns `passed=False`,
`fail_conditions_match=False` and an explanatory mismatch in `errors`.
That stop-rule repair left the compiler grammar and function signature unchanged. This is a field
preservation check, not full prose equivalence, authenticated CTX.HOLO delivery
or admission of the AI Overseer YAML-document candidate.

The subsequent action/scope correction adds the optional `M2MPrompt.action`
field (empty for legacy packets). New `M2MCompiler.compile(...)` output carries
its extracted verb as compact `A:<action>` and YAML `MISSION.ACTION`.
`parse_compact(...)` restores it and `decompile(...)` preserves it independently
of mode. Legacy actionless packets keep their mode-only rendering. An older
reader that ignores `A` cannot establish action fidelity.

`M2MFidelityGate.assert_fidelity(...)` now compares the extracted action with
both serialized-roundtrip fields and the decompiled verb. Missing or changed
actions return `passed=False`, including loss of an explicit `IMPLEMENT`.
`roundtrip_scope` reports the actual parsed scope; missing, shortened or
retargeted scopes fail instead of being masked by the compiled object.
The standalone `assert_m2m_fidelity(...)` raises `FidelityError` for those
failures. Signatures and original positional dataclass arguments remain valid.
These checks do not turn the compiler's heuristic extraction into a complete
prose or objective-preservation oracle.

The 2026-09-14 continuation also requires the original declared stop list in
the decompiled instruction `Abort if any condition holds: <Python list repr>.`
`fail_conditions_match` covers compiled, parsed and rendered stops; dropping
or changing that instruction returns `passed=False` and a mismatch error.
The public wrapper raises `FidelityError` as before. Legacy actionless packets
render existing stops, while stop-free packets keep their previous output.
No signature or compact-wire change is involved. The gate validates this
specific rendering; it does not decide whether arbitrary surrounding prose
contradicts it or establishes authority.

### Legacy invariant emission guard — 2026-09-15

`M2MPrompt.to_compact()` and `compile_m2m(...)` raise `ValueError` before output
when `invariants` is not a built-in dictionary, a key is empty/non-string, a
value is not a built-in string/bool/int/finite-float/None, or the flat grammar
cannot preserve the field. Keys reject commas/colons/braces; values reject
commas/braces. Both reject trim-boundary whitespace, ASCII controls and
U+0085/U+2028/U+2029. Internal spaces and empty string values remain supported.
Errors contain no input values. `compile()` preserves invalid falsey mappings
until serialization so they cannot silently become an empty constraint set.

Scalar parse results retain legacy strings (`True` becomes `"True"`, for example).
Nested allowed paths, dependency lists and WSP15 objects cannot use this wire.
Preserve the structured source and fail closed; do not weaken it to pass.
This change does not harden `parse_compact`, YAML, other fields or full prose,
and does not qualify schema/ROLE/ORIGIN/PRINCIPAL_REF/stable task IDs or authority.
The fidelity gate's separate `HoloInvariants` object is not this wire dictionary.

### Canonical envelope codec — 2026-09-15

The existing `prompt/swarm/m2m_compiler.py` owns two additional pure functions:

```python
from prompt.swarm.m2m_compiler import encode_m2m_envelope, decode_m2m_envelope

wire = encode_m2m_envelope(normalized_order)  # Caller supplies the complete order.
restored_order = decode_m2m_envelope(wire)
```

`encode_m2m_envelope(envelope: dict[str, Any]) -> str` validates a plain JSON
snapshot, then emits sorted-key compact UTF-8-compatible JSON. The decoder takes
a built-in `str`, rejects duplicate keys at every depth, validates the same
profile and returns a new dictionary. Neither mutates the input or uses providers,
storage, the heuristic prose compiler or the legacy parser.

Required fields follow current WSP99 section 0: `schema=0102_m2m_v1`, `ROLE`,
`ORIGIN`, `L`, `S`, `M`, `T`, `A`, `R`, `I`, `O`, `F`. `PRINCIPAL_REF` is optional
context; omission remains omission. Unknown fields reject. Roles/origins use the
canonical enumerations; lanes are A/B/C/QA/SENTINEL/ORCH and modes exec/plan/qa.
Legacy D/audit/review/verify/implement remain available only through legacy APIs.
S/T/A and present PRINCIPAL_REF must be nonblank strings, preserved without
trimming. R is a list of nonnegative built-in integers (not bool); I is a
dictionary; O/F are string lists. These lists may be empty. The codec does not
resolve WSP existence, paths, task identity uniqueness or action meaning.

Nested I accepts exact built-in dict/list/string/bool/int/finite-float/None values
and string keys. Delimiters, whitespace, Unicode and list order are preserved.
Unsupported/custom types, cycles, invalid Unicode and non-finite numbers reject
without coercion. All public validation errors are
`ValueError("invalid canonical M2M envelope")`, without input values.

Local defensive limits are **65,536 UTF-8 bytes**, **depth 16** (root at zero),
and **4,096 nodes including dictionary keys**. They are codec-profile choices,
not WSP-mandated quotas. Encoding bounds traversal and compact output; decoding
bounds the entire input wire before parsing, including whitespace. Python's
integer-conversion limits also apply. Round-trip fidelity is for accepted Python
JSON values, including integer/float distinction and negative floating zero;
original wire whitespace or number spellings are not preserved. Determinism is
not RFC8785/signature canonicalization or cross-language numeric qualification.

The existing compact fidelity gate is unchanged and is not a validator for this
codec. Passing codec tests does not prove principal prose was normalized correctly,
that any downstream consumer preserves the envelope, or that execution, independent
verification, reward or retained-learning authority exists. Keep those gates closed
until separately qualified; do not convert signed receipts into this format.

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

## Public API (P6: OpenClaw/Hermes RTK Adapter Dry-Run)

P6 models the OpenClaw/Hermes command-output seam. It does not call OpenClaw,
Hermes, WRE, extension runtime, an RTK binary, or any shell. It always preserves
raw command output and emits a receipt that says whether a caller-supplied
candidate passed the P4/P5 dry-run chain.

### Classes

#### `RtkOpenClawHermesAdapterDryRunResult`

```python
@dataclass
class RtkOpenClawHermesAdapterDryRunResult:
    adapter_receipt_id: str
    decision: RtkAdapterDryRunDecision
    surface: RtkAdapterSurface | None
    output_mode: RtkAdapterOutputMode
    command_digest: str
    raw_output_digest: str
    candidate_output_digest: str
    raw_ref_digest: str
    compute_decision_id: str | None
    compute_routing: str | None
    evaluation_id: str | None
    evaluation_decision: str | None
    telemetry_event_id: str | None
    bytes_saved: int
    tokens_saved: int
    savings_ratio: float
    rejection_reasons: list[str]
    dry_run_only: bool             # Always True
    rtk_invoked: bool              # Always False
    command_executed: bool         # Always False
    compression_performed: bool    # Always False
    output_rewritten: bool         # Always False
    raw_output_preserved: bool     # Always True
    runtime_reindex_allowed: bool  # Always False
```

### Functions

#### `plan_rtk_openclaw_hermes_adapter_dry_run(...) -> RtkOpenClawHermesAdapterDryRunResult`

Plans a dry-run seam result using:

- a supported surface: `OPENCLAW` or `HERMES`
- P4 compute-governor routing over the command and output preview
- P5 candidate evaluation over caller-supplied raw/candidate output
- mandatory `raw_ref` recovery path
- hashes only in the result; raw command/output/candidate/raw_ref are not serialized

Acceptance means the candidate passed the dry-run measurement chain. It still is
not permission to rewrite command output, invoke RTK, or wire into OpenClaw,
Hermes, WRE, or extension runtime.

## Not Implemented (Future Phases)

| Component | Phase | Status |
|-----------|-------|--------|
| Runtime RTK binary invocation | Future | SPECIFIED_NOT_IMPLEMENTED |
| OpenClaw/Hermes output rewrite | Future | SPECIFIED_NOT_IMPLEMENTED |
| Extension/WRE/OpenClaw/Hermes runtime wiring | Future | SPECIFIED_NOT_IMPLEMENTED |
