# shared_utilities

**Domain:** infrastructure (ai_intelligence | communication | platform_integration | infrastructure | monitoring | development | foundups | gamification | blockchain)
**Status:** Prototype (POC | Prototype | MVP | Production)
**WSP Compliance:** Compliant (Compliant | In Progress | Non-Compliant)

## [OVERVIEW] Module Overview

**Purpose:** Infrastructure utilities providing shared functionality across all enterprise domains. Extracted from vibecoded implementations to enable WSP 3 functional distribution.

**Key Capabilities:**
- Session management and caching utilities
- Data validation and ID masking utilities
- Intelligent delay calculation and throttling utilities
- YouTube channel registry (shared rotation + scheduling metadata)
- Cross-cutting concerns for infrastructure layer

The local LLM adapter distinguishes installed models from exact resident
instances through native `/api/v1/models`. Generic resolution remains
probe/borrow-only. Explicit callers may use one node/port-wide, bounded-lock
model transaction that borrows an existing instance or, only when node
residency is empty and native context limits admit it, loads one exact model.
The transaction journals interrupted-load intent outside the repository,
invokes one caller-bounded operation, unloads only proven ownership, verifies
cleanup, and returns content-free, content-addressed lifecycle evidence.
Structural receipts require the existing signed provenance layer for
adversarial trust. No path starts/stops the server, downloads a model, guesses
an ID, invokes `lms`, evicts an existing model, or falls back implicitly.

**Dependencies:**
- Standard library utilities plus optional `openai`/`llama_cpp` adapters for
  explicitly selected local LLM backends.

## [STATUS] Current Status & Scoring

### MPS + LLME Scores
**Last Scored:** 2025-09-25
**Scored By:** WSP 49 Compliance Fixer

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **Complexity** | 3 | Standard module complexity |
| **Importance** | 3 | Core functionality |
| **Deferability** | 2 | Should be addressed soon |
| **Impact** | 3 | Affects module usability |
| **MPS Total** | 11 | **Priority Classification:** P2 |

**LLME Semantic Score:** BBB
- **B (Present State):** 1 - relevant - Basic structure exists
- **B (Local Impact):** 1 - relevant - Used by domain modules
- **B (Systemic Importance):** 1 - conditional - Important for domain completeness

**LLME Target:** BCC - Full compliance and integration

## [ROADMAP] Module Roadmap

### Phase Progression: null -> 001 -> 011 -> 111

#### [COMPLETE] Completed Phases
- [x] **Phase 0 (null):** Module concept and planning
  - [x] MPS/LLME initial scoring
  - [x] WSP structure creation
  - [x] Domain placement decision

#### [COMPLETE] Completed Phases
- [x] **Phase 1:** Basic structure compliance
  - [x] Create missing src/ directory
  - [x] Create missing tests/ directory
  - [x] Create README.md template
  - [x] Create INTERFACE.md template
- [x] **Phase 2:** Functional implementation
  - [x] Session utilities implementation (session_utils.py)
  - [x] Validation utilities implementation (validation_utils.py)
  - [x] Delay utilities implementation (delay_utils.py)
  - [x] Integration testing
  - [x] Documentation completion

#### [CURRENT] Current Phase: WSP 62 Optimization
- [ ] **Phase 3:** Performance and scalability
  - [ ] Code size optimization (<200 lines per utility)
  - [ ] Performance benchmarking
  - [ ] Comprehensive test coverage (>90%)

### Runtime Artifact Safety Decomposition

`runtime_artifact_safety.py` is an inherited compatibility host for path
validation, descriptor-confined I/O, cross-process locking, and telemetry
redaction. New consumers must reuse its public API rather than add parallel
safety policies. A dedicated parity migration must separate redaction,
confined reads/writes, and remaining policy seams; the platform lock backend is
now extracted to `runtime_operation_locking.py` while preserving Windows
extended-length paths, Linux descriptor verification, and the existing public
imports. Its temporary exact WSP 62 no-growth ceiling is recorded in
`wsp_62_exemptions.yaml`.

## [API] Public API & Usage

### Exported Functions/Classes
```python
# Session utilities
from modules.infrastructure.shared_utilities import (
    SessionUtils, load_session_cache, save_session_cache, try_cached_stream
)

# Validation utilities
from modules.infrastructure.shared_utilities import (
    ValidationUtils, mask_sensitive_id, validate_api_client
)

# Delay utilities
from modules.infrastructure.shared_utilities import (
    DelayUtils, calculate_enhanced_delay
)

# Usage patterns
session_utils = SessionUtils()
cache = session_utils.load_cache()

validation_utils = ValidationUtils()
masked_id = validation_utils.mask_sensitive_id("UC123456789", "channel")

delay_utils = DelayUtils()
delay = delay_utils.calculate_enhanced_delay(active_users=50, consecutive_failures=2)

# YouTube channel registry
from modules.infrastructure.shared_utilities.youtube_channel_registry import (
    get_channels, get_channel_ids, add_channel
)
channels = get_channels()
ids = get_channel_ids(role="live_check")
```

### Integration Patterns
**For Other Modules:**
```python
# Infrastructure utilities are designed for enterprise-wide use
from modules.infrastructure.shared_utilities import SessionUtils, ValidationUtils, DelayUtils

# Example: Using in a domain module
class MyDomainService:
    def __init__(self):
        self.session_utils = SessionUtils()
        self.validation_utils = ValidationUtils()
        self.delay_utils = DelayUtils()
```

**WSP 11 Compliance:** [OK] Compliant - Public API fully defined with usage examples

## [MODLOG] ModLog (Chronological History)

### 2025-10-13 - WSP 3 Surgical Refactoring Implementation
- **By:** 0102_grok (Surgical Refactoring Agent)
- **Changes:**
  - Implemented SessionUtils class for session management and caching
  - Implemented ValidationUtils class for ID masking and API validation
  - Implemented DelayUtils class for intelligent delay calculation
  - Added comprehensive backward compatibility functions
  - Created integration tests and documentation
- **Impact:** Module now provides enterprise-wide infrastructure utilities, extracted from vibecoded implementations
- **WSP Compliance:** Achieved WSP 3, 49, 62 compliance through functional distribution
- **LLME Transition:** BCC -> CCC (full implementation achieved)

### 2025-09-25 - WSP 49 Compliance Fix
- **By:** WSP 49 Violation Fixer
- **Changes:** Created missing src/, tests/, README.md, INTERFACE.md
- **Impact:** Module now compliant with WSP 49 structure requirements
- **LLME Transition:** BBB -> BCC (structure compliance achieved)

## [COMPLIANCE] WSP Compliance Checklist

### Structure Compliance (WSP 49)
- [x] **Directory Structure:** modules/[domain]/[module_name]/
- [x] **Required Files:**
  - [x] README.md (this file)
  - [x] src/__init__.py (implemented with exports)
  - [x] src/session_utils.py (implemented)
  - [x] src/validation_utils.py (implemented)
  - [x] src/delay_utils.py (implemented)
  - [x] tests/__init__.py (created)
  - [x] tests/test_session_utils.py (created)
  - [x] tests/README.md (created)
  - [ ] requirements.txt (no external dependencies)

### Testing Compliance (WSP 13)
- [x] **Test Coverage:** ~70% (SessionUtils fully tested, others partially)
- [x] **Test Documentation:** tests/README.md complete
- [x] **Test Patterns:** Follows established module patterns
- [x] **Last Test Run:** 2025-10-13 - SessionUtils tests pass

### Interface Compliance (WSP 11)
- [x] **Public API Defined:** __init__.py exports all utilities
- [x] **Interface Documentation:** Usage examples provided
- [x] **Backward Compatibility:** [OK] Full backward compatibility maintained

---

**Template Version:** 1.0
**Last Updated:** 2025-10-13
**WSP Framework Compliance:** WSP 3, 11, 13, 49, 62 Compliant (Surgical Refactoring Complete)
