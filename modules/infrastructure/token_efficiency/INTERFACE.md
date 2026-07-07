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

## Not Implemented (Future Phases)

| Component | Phase | Status |
|-----------|-------|--------|
| M2M fidelity gate | P2 | SPECIFIED_NOT_IMPLEMENTED |
| Token telemetry | P3 | SPECIFIED_NOT_IMPLEMENTED |
| Compute governor | P4 | SPECIFIED_NOT_IMPLEMENTED |
| RTK adapter | P5 | SPECIFIED_NOT_IMPLEMENTED |
| Compression seam | P6 | SPECIFIED_NOT_IMPLEMENTED |
