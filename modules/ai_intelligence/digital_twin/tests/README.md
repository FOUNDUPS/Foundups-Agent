# Digital Twin Tests

## Offline VoiceLoRATrainer security, masking, and split controls (2026-11-16)

`test_lora_trainer.py` verifies `src/lora_trainer.py` strictly offline using synthetic
JSONL files in `tmp_path` and deterministic in-memory stub tokenizers/models/trainers
(zero model downloads, zero network calls, zero GPU/CUDA, zero training runs):

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
python -B -m pytest -q -p no:cacheprovider \
modules/ai_intelligence/digital_twin/tests/test_lora_trainer.py
```

Coverage (`105 passed` in `test_lora_trainer.py`, `258 passed` across `digital_twin/tests/`):
`trust_remote_code=False` and `local_files_only=True` enforcement (including config
rejection and post-init mutation), locked `require_verified_speaker=True` and
`require_explicit_admission=True` invariants across `VoiceTrainingConfig` and all
validator/loader entrypoints, CUDA/4-bit and CLI `--confirm-consent` gates,
line-numbered fail-closed JSONL parsing (including `NaN`/`Infinity` rejection),
direct-loader rejection of unlabeled or `NemoDataBuilder`/`lora_data_converter`-shaped
first-person rows lacking any of the 5 required explicit admission proofs
(`training_eligible=True`, allowed verbatim provenance, boolean `consent=True`,
verified principal speaker, and non-placeholder `group_id`), removal of the
`__row_{idx}__` ungrouped fallback in `_split_grouped_examples`, read-only
`inspect_sft_record()` diagnostic preservation of `speaker=None, speaker_status="unknown"`
and `t_start=None, timestamp_status="unknown"` without inventing `"012"` or `0.0`,
contradictory cross-container metadata, summaries mislabeled as verbatim transcripts
(`gemini*` models, summary payloads, 3rd-person summary phrasing), missing/blank/
`"unknown"`/unverified/mixed/non-012 speaker rejection, invalid/colon-overflow/
inverted/dangling/nonmonotonic timestamp rejection, `-100` prompt and padding masking
when `pad_token_id == eos_token_id` (both right and left padding), overlong-prompt
truncation fail-closed guard against all-`-100` `NaN` loss, deterministic
`video_id`/`source_id` group-disjoint train/eval splitting, `Trainer`
`eval_dataset` + `eval_strategy="epoch"` wiring, and WSP 62 file/function bounds
(`<= 500` lines, `<= 50` lines/function across both `lora_trainer.py` and
`lora_record_validator.py`). Passing offline contract tests validate structural
contracts only and do not execute or certify live QLoRA model training.

## Ready-only reply retrieval

The bounded cross-owner selection is
`modules/communication/video_comments/tests/test_reply_memory_readiness.py`.
Its 23 controls compile complete VoiceMemory/VideoContentIndex/reply definitions
with synthetic collections, embeddings and Gateway judgments. Constructor and
model-loader spies guard cold omission; warm results, cache preservation,
cooperative cancellation and unchanged legacy defaults are positive controls.
Run only through the existing credential-free EffectGuard owner. The four
legacy `test_voice_memory.py` build/corpus tests can initialize ML dependencies
and are not automatically offline-safe or part of this selection.

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

## AntifaFM station reply coverage

`test_comment_drafter.py` includes the station-only factory and decision contract
alongside the three legacy drafter tests. Run it offline with:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
python -B -m pytest -q -p no:cacheprovider \
modules/ai_intelligence/digital_twin/tests/test_comment_drafter.py
```

The fixture backend returns controlled chat-completion JSON through the actual
`LocalLLM.generate_station_json()` wrapper. Cases check source/policy separation,
listener-initiation and missing-context skips, the 2,400-character context bound,
source binding, intent/action validation, malformed output, generation failures,
AI disclosure, unsupported claims/links, optional station links, and exact
280-character acceptance versus 281-character review. A genuinely missing model
path confirms that the station path returns review instead of mock/template text.
All decisions carry source metadata and `no_publication_performed=True`.

Result on 2026-10-18: **39 passed**. These are contract tests, not evidence that an
actual model correctly understands each conversation, resists every injection,
or produces factually accurate replies. No live local-model inference, network
request, or publication is required. See `TestModLog.md` for the recorded result
and separate guarded real-import smoke check.

## Expected Behavior
- Comment drafting returns structured `CommentDraft` with bounded length.
- Station drafting returns a dictionary with `skip`, `draft_reply`, or
  `review_required`; unavailable or invalid generation has an empty reply and
  never falls back to the legacy mock path.
- Guardrails strip fillers and report violations consistently.
- Decision policy respects thresholds and cooldown logic.
- Unknown/ambiguous conversation defaults to `CHAT / FAST / NONE`; security,
  money, privacy, contradiction, or irreversible risk can raise reasoning only.

## Integration Requirements
- Some tests may require optional dependencies (faiss, sentence-transformers).
- When optional deps are missing, tests should fall back to TF‑IDF paths.
