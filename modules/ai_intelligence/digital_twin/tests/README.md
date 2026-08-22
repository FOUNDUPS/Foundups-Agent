# Digital Twin Tests

## Test Strategy (WSP 34)
- Keep unit tests deterministic; avoid external model/network dependencies.
- Use mock LLM paths or local fixtures for repeatable outputs.
- Validate core pipeline stages: memory → draft → guardrails → decision.
- Validate conversation intent, reasoning, and effects independently; shared
  vectors must match the VSIX adapter and no text may grant execution.
- Treat resident transport as an adversarial boundary: reject unknown identity,
  routing, credential, or effect fields; validate replay/CAS shapes; keep public
  bindings content-free.

## How to Run
- All tests: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest modules/ai_intelligence/digital_twin/tests`
- Focused: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest modules/ai_intelligence/digital_twin/tests/test_comment_drafter.py`
- Conversation: `cd extensions/reddog && npm run test:conversation`
- Resident transport contract: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q modules/ai_intelligence/digital_twin/tests/test_resident_conversation_transport_contract.py`
- Resident transport coverage: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -p pytest_cov modules/ai_intelligence/digital_twin/tests/test_resident_conversation_transport_contract.py --cov=modules.ai_intelligence.digital_twin.src.resident_conversation_transport_contract --cov-report=term-missing --cov-fail-under=100`

## Test Data
- Use minimal fixtures embedded in tests or small local JSON snippets.
- Avoid using production corpora in unit tests.

## Expected Behavior
- Comment drafting returns structured `CommentDraft` with bounded length.
- Guardrails strip fillers and report violations consistently.
- Decision policy respects thresholds and cooldown logic.
- Unknown/ambiguous conversation defaults to `CHAT / FAST / NONE`; security,
  money, privacy, contradiction, or irreversible risk can raise reasoning only.

## Integration Requirements
- Some tests may require optional dependencies (faiss, sentence-transformers).
- When optional deps are missing, tests should fall back to TF‑IDF paths.
