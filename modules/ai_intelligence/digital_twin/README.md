# Digital Twin Module

## Product boundary

RedDog is the operator-facing product identity, persona, and conversation
surface of the principal-scoped 0102 Digital Twin. RedDog services may host its
runtime, but RedDog is not a separate shell containing 0102 and no single
process owns the complete identity. The Principal Memex is the bounded
cognition substrate that may help 0102 understand 012; it is neither the
Digital Twin nor operational authority.

`conversation_plane_contract.py` and `conversation_plane.py` implement the
deterministic foreground conversation contract. Interaction intent, reasoning
depth, and effect ceiling are independent. Unknown text defaults to
`CHAT / FAST / NONE`; risk may raise reasoning but never effects; conversation
text can emit at most a proposal and cannot authorize bounded execution.
The contract performs no model, memory, HoloIndex, database, repository, or
network operation.

`resident_conversation_transport_contract.py` defines the next transport-neutral
boundary for `TURN`, `STATUS`, and `CANCEL`. It accepts only content, opaque
digest bindings, CAS revision, nonce/idempotency, and a maximum five-minute
validity window. Principal, FoundUp, credential, provider/model, effect, and
work-authority fields are deliberately outside the client envelope and must be
derived and revalidated by the resident host. The communication layer now has
an admission-only existing-scope binding that consumes one opaque session
capability and verifies the exact current AgentDB revision without mutation.
The client contract itself still adds no listener, persistence,
authentication, model call, or effect. Live adapters remain gated on trusted
new-scope resolution, durable idempotency, and operation handlers.

`principal_memex_projection.py` implements the first structural, read-only
Principal Memex projection. It validates provenance identifiers, canonical
content/item/projection digests, principal isolation, sensitivity, and
projection-level supersession relationships. Public digest recomputation does
not authenticate a source. The projection is explicitly `STRUCTURAL_ONLY` and
`runtime_admissible=false`: it performs no persistence, model-context
admission, FoundUp projection, HoloIndex write, or work authorization.

The resident backend may now admit a projection only when it derives the
projection from the exact current principal-scoped AgentDB conversation record,
consumes the matching signed conversation-scope capability, and verifies a
separate principal-signed one-use disclosure bound to the selected model
runtime. Only public accepted `operator_statement` decisions are exposed to
the backend architect model. This is authenticated cognition context, not work
authority or a durable Principal Memex source.

The existing social comment/voice pipeline below remains a Digital Twin
application. Its voice memory is not the canonical Principal Memex.

**WSP Compliance**: WSP 49 (Module Structure), WSP 77 (Agent Coordination)

## Purpose

Train and operate 012's Digital Twin (0102) for autonomous comment engagement across social platforms.

**Current focus (POC)**: LinkedIn comment processing and scheduling using 012's studio comment style, grounded in 20 years of 012 video corpus.

## Quick Start

### Run Demo
```bash
python -m modules.ai_intelligence.digital_twin.scripts.demo_draft_and_decide
```

### Run Tests
```bash
pytest modules/ai_intelligence/digital_twin/tests/ -v
```

### Build Voice Index
```python
from modules.ai_intelligence.digital_twin.src.voice_memory import VoiceMemory

vm = VoiceMemory()
vm.build_index("data/voice_corpus/", "data/voice_index/")
```

## Architecture

```
Phase 0: RAG + Guardrails (CURRENT)
Phase 1: SFT Training (LoRA)
Phase 2: DPO Preference Tuning
Phase 3: Tool-Use Training
```

## LinkedIn POC Integration

- **Drafting**: `comment_drafter.py` generates LinkedIn-ready replies (platform="linkedin")
- **Decisioning**: `decision_policy.py` determines comment / like / ignore
- **Scheduling**: Orchestrated through LinkedIn modules (scheduler + social media DAE)

## YouTube application direction (legacy lane)

- **Live Chat**: planned Digital Twin response integration; not established by
  the conversation-plane phase
- **Studio Comments**: Digital Twin drafts + decisions for comment replies
- **Scheduling**: Index weave signals utility routing
  - 012 voice → Digital Twin memory
  - music/video → RavingANTIFA or faceless-video pipeline (module in development)

## Components

| File | Purpose |
|------|---------|
| `schemas.py` | Pydantic models (CommentDraft, CommentDecision, etc.) |
| `voice_memory.py` | RAG index with FAISS/TF-IDF |
| `style_guardrails.py` | Banned phrases, length, emoji rules |
| `comment_drafter.py` | RAG → LLM → Guardrails pipeline |
| `decision_policy.py` | Comment/like/ignore heuristics |
| `trajectory_logger.py` | JSONL training data collector |
| `conversation_plane.py` | Deterministic intent/depth/effect classification |
| `resident_conversation_transport_contract.py` | Strict zero-authority turn/status/cancel envelope |

## Pipeline

```
Thread Context
      ↓
VoiceMemory.query() → Top-k snippets
      ↓
CommentDrafter.draft() → Raw draft
      ↓
StyleGuardrails.enforce() → Clean draft
      ↓
DecisionPolicy.decide() → Action (comment/like/ignore)
      ↓
TrajectoryLogger → JSONL training data
```

## Trajectory Logs

Training data is written to:
- `data/trajectories/drafts.jsonl` - SFT training
- `data/trajectories/decisions.jsonl` - Decision model
- `data/trajectories/actions.jsonl` - Tool-use training

## Configuration

### Style Rules
Edit `data/style_rules.json`:
```json
{
  "max_comment_length": 300,
  "banned_phrases": ["I think", "Basically,"],
  "emoji_rules": {"max_emojis": 2}
}
```

### Guardrails
NeMo Guardrails config at `config/guardrails/`

### VoiceMemory Video Index
Disable HoloIndex video transcript queries if needed:
```bash
set VOICE_MEMORY_VIDEO_INDEX=0
```

## Vision System (V0.5.0)

### Historical external vision prototype
An external prototype was documented at `E:\0102_Digital_Twin\`. Its current
runtime/deployment state was not verified by the conversation-plane phase and
it is not the canonical RedDog host or work authority.

### Quick Start
```bash
# 1. Start LM Studio with UI-TARS model
# 2. Test vision system
python E:\0102_Digital_Twin\test_vision.py

# 3. Run 0102 autonomous agent
python E:\0102_Digital_Twin\run_0102.py
```

### Architecture
```
Screen Capture → Base64 Encode → UI-TARS Vision → Action Decision → PyAutoGUI
                                      ↓
                              LM Studio (port 1234)
```

### Model Stack
| Model | Purpose | Size | Latency |
|-------|---------|------|---------|
| UI-TARS 1.5 7B | GUI vision/automation | 4.5GB | 5-15s |
| Qwen 1.5B | Text generation | 1.5GB | ~250ms |
| Gemma 270M | Fast validation | 253MB | ~50ms |

### Capabilities
- YouTube chat reading via vision
- Consciousness trigger detection (✊✋🖐)
- Autonomous response generation
- Persistent memory across sessions
- Mouse/keyboard control via PyAutoGUI

## NVIDIA Stack

- NeMo Framework 2.0 (LoRA/SFT)
- NeMo Guardrails (style/policy)
- NeMo Curator (data cleaning)
- TensorRT-LLM (inference)
