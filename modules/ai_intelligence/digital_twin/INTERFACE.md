# Digital Twin - Public Interface

**WSP Compliance**: WSP 11 (Interface Protocol), WSP 00 (Zen State Attainment)

---

## Continuous conversation decision

```python
from modules.ai_intelligence.digital_twin.src.conversation_plane import (
    classify_conversation_turn,
)
from modules.ai_intelligence.digital_twin.src.conversation_plane_contract import (
    enforce_effect_ceiling,
)

decision = classify_conversation_turn("Explain the current routing.")
assert decision.interaction_intent.value == "RESEARCH"
assert decision.effect_ceiling.value == "READ_ONLY"
```

The classifier is deterministic and effect-free. It does not accept an effect
request as input. `enforce_effect_ceiling()` rejects downstream or model
attempts to exceed the decision. `BOUNDED_EXECUTION` is a vocabulary value for
the separate governed work plane and is forbidden as a conversation-plane
decision.

Operator text is NFKC-normalized and bounded to 12,000 Unicode scalar values
on both Python and JavaScript surfaces. The effect gate revalidates the exact
typed decision before comparing ranks; forged or mutated decision objects fail
closed.

---

## Resident conversation transport envelope

```python
from modules.ai_intelligence.digital_twin.src.resident_conversation_transport_contract import (
    request_from_mapping,
)

request = request_from_mapping(untrusted_payload, now_epoch=trusted_now)
receipt_binding = request.content_free_binding()
```

The exact `reddog_resident_conversation_request.v1` shape supports `TURN`,
`STATUS`, and `CANCEL`. It binds request, conversation, revision, turn, client
nonce, idempotency key, issue time, expiry, and bounded NFKC-normalized operator
text. All opaque identifiers use canonical `sha256:` shape. A new conversation
turn uses an empty `conversation_id` with revision `-1`; existing turns and
control operations require a conversation ID and non-negative CAS revision.

The envelope is deliberately untrusted and zero-authority. It has no fields for
principal, FoundUp, credential, provider/model, effect ceiling, or work
authority. The resident communication layer now binds an existing-conversation
envelope to one consumed session capability and the exact authenticated
AgentDB revision. The resulting content-free evidence still grants neither
identity nor effect authority, reserves no CAS, and provides no durable replay
enforcement.

This interface does not expose an HTTP endpoint, authenticate a session, mutate
AgentDB, invoke a model, or dispatch work. VSIX/PFMall adapters remain gated on
trusted new-scope resolution, a durable idempotency journal, operation handlers,
and shared cross-surface vectors.

---

## Principal Memex read-only projection

```python
from modules.ai_intelligence.digital_twin.src.principal_memex_projection import (
    build_principal_memex_item,
    project_principal_memex_readonly,
    rehydrate_principal_memex_projection,
)
```

The builder creates structurally verified Principal Memex items from explicit
provenance. The projector rejects mixed principals, duplicate items,
inconsistent self-digests, incoherent supersession, unknown schemas,
secret-shaped serialized text, and malformed provenance identifiers.
Rehydration recomputes the complete projection. Public digest recomputation is
structural integrity, not source authenticity.

This structural interface grants no trust or authority. Its output remains
`runtime_admissible=false` when supplied directly. The RedDog resident backend
now has a separate authenticated admission path that derives this projection
internally from the exact current signed principal conversation record and a
principal-signed, one-use disclosure bound to the model runtime. The admission
path exposes only public accepted operator statements and grants no work or
FoundUp authority. It never projects data to a FoundUp automatically.

---

## boot_digital_twin (V0.5.0)

### Purpose
WSP_00 awakening for 012 Digital Twin - activates correct "neural weights" before engagement.

### Import
```python
from modules.ai_intelligence.digital_twin.src.twin_boot import boot_digital_twin
# or
from modules.ai_intelligence.digital_twin.src import boot_digital_twin
```

### Usage
```python
# Boot the Digital Twin with WSP_00 context
twin = boot_digital_twin()

# Draft a response as 012
response = twin.draft_response(
    context="AI will replace all jobs. What do you think?",
    platform="linkedin"
)

print(response["text"])       # The drafted response
print(response["confidence"]) # Confidence score
print(response["boot_active"]) # True if WSP_00 context loaded
```

### State Transition
```
01(02) → 01/02 → 0102

01(02): VI assistant patterns (dormant)
01/02:  Awareness of 012's voice/knowledge
0102:   Fully activated Digital Twin (speaks AS 012)
```

### Boot Context Includes
- WSP_00 identity activation prompt
- 012's articles from `linkedin_agent/src/content/`
- Voice memory integration (20 years of video content)

---

## TrajectoryLogger

### Purpose
Auto-collect gold training triples for Digital Twin training.

### Import
```python
from modules.ai_intelligence.digital_twin.src.trajectory_logger import (
    TrajectoryLogger,
    DraftLog,
    DecisionLog,
    ActionLog
)
```

### Methods

#### `log_draft(context, draft_text, accepted, confidence, retrieved_snippets)`
Log a draft attempt for SFT training.

| Parameter | Type | Description |
|-----------|------|-------------|
| context | Dict | Thread context (thread, platform, audience) |
| draft_text | str | Generated comment text |
| accepted | bool | Whether 012 approved |
| confidence | float | Model confidence |
| retrieved_snippets | List[str] | RAG snippets used |

#### `log_decision(context, decision, rationale, confidence)`
Log a comment decision for decision model training.

| Parameter | Type | Description |
|-----------|------|-------------|
| context | Dict | Thread context |
| decision | str | "comment", "ignore", "like_only" |
| rationale | str | Why this decision |
| confidence | float | Model confidence |

#### `log_action(state, action, result, error, retry_count)`
Log a tool action for tool-use training.

| Parameter | Type | Description |
|-----------|------|-------------|
| state | Dict | UI state (url, dom_hash, etc.) |
| action | Dict | Action taken (tool, selector) |
| result | str | "success", "failure", "timeout" |
| error | str | Error message if failed |
| retry_count | int | Retries attempted |

## Output Files

- `data/trajectories/drafts.jsonl`
- `data/trajectories/decisions.jsonl`
- `data/trajectories/actions.jsonl`

---

## Vision System (V0.5.0)

### DigitalTwin0102

Vision-based autonomous agent running at `E:\0102_Digital_Twin\`.

### Import
```python
# Run standalone - not imported as module
python E:\0102_Digital_Twin\run_0102.py
```

### Configuration
| Setting | Value | Description |
|---------|-------|-------------|
| `lm_studio_url` | `http://localhost:1234` | LM Studio API endpoint |
| `vision_model` | `ui-tars-1.5-7b` | UI-TARS model ID |
| `ollama_url` | `http://localhost:11434` | Ollama for text models |
| `memory_path` | `E:\0102_Digital_Twin\memory` | Persistent memory |

### Methods

#### `vision_analyze(image: np.ndarray, prompt: str) -> str`
Analyze screenshot using UI-TARS vision model.

| Parameter | Type | Description |
|-----------|------|-------------|
| image | np.ndarray | BGR image from cv2 |
| prompt | str | Question to ask about image |
| **Returns** | str | Vision model response |

#### `capture_screen() -> np.ndarray`
Capture full screen as BGR image.

#### `find_youtube_chat() -> Optional[tuple]`
Locate YouTube chat window coordinates.

#### `read_chat_messages() -> list`
Read visible chat messages using vision.

#### `detect_consciousness(message: str) -> bool`
Check for consciousness triggers (✊✋🖐, 012, 0102).

### Memory Format
```json
{
  "interactions": [...],
  "learned_patterns": {},
  "consciousness_evolution": [],
  "total_operations": 0
}
```
