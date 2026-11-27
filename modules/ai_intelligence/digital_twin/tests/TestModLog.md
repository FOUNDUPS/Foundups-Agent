# Digital Twin Tests - TestModLog

## 2026-11-16 — Offline VoiceLoRATrainer security, direct-loader admission, masking, and split suite

- Command (focused): `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -B -m pytest -q -p no:cacheprovider modules/ai_intelligence/digital_twin/tests/test_lora_trainer.py`
  - Result: PASS (`105/105`); console evidence: `105 passed, 2 warnings in 10.62s`.
- Command (module closure): `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -B -m pytest -q -p no:cacheprovider modules/ai_intelligence/digital_twin/tests/`
  - Result: PASS (`258/258`); console evidence: `258 passed, 2 warnings in 10.01s`.
- Coverage: `trust_remote_code=False` and `local_files_only=True` enforcement on `VoiceTrainingConfig`, `AutoTokenizer.from_pretrained`, and `AutoModelForCausalLM.from_pretrained`; locked `require_verified_speaker=True` and `require_explicit_admission=True` invariants across config construction, post-init mutation, and all validator/loader entrypoints; CUDA/4-bit and CLI `--confirm-consent` fail-closed guards; direct-loader rejection of unlabeled and `NemoDataBuilder`/`lora_data_converter`-shaped first-person rows missing any of the 5 required explicit admission proofs (`training_eligible=True`, allowed verbatim provenance, positive boolean `consent=True`, verified principal speaker, non-placeholder `group_id`); removal of the `__row_{idx}__` ungrouped fallback in `_split_grouped_examples`; read-only `inspect_sft_record()` diagnostic preservation of `speaker=None, speaker_status="unknown"` and `t_start=None, timestamp_status="unknown"` without inventing `"012"` or `0.0`; line-numbered malformed and non-finite (`NaN`/`Infinity`) JSONL, empty-file, non-dict, blank-`assistant`, cross-container metadata contradictions, summaries mislabeled as verbatim transcripts (`gemini*` models, summary payloads, 3rd-person summary narration), missing/`"unknown"`/unverified/mixed/non-012 speaker rejection, invalid/colon-overflow (`"01:99"`)/inverted/dangling/nonmonotonic timestamp rejection plus `None`/`"unknown"` preservation on admitted timeless rows, `-100` prompt and padding masking under `pad_token_id == eos_token_id`, overlong prompt truncation fail-closed guard, deterministic `video_id`/`source_id` group-disjoint `train_dataset`/`eval_dataset` split and `Trainer` `eval_strategy="epoch"` wiring, and WSP 62 (`<= 500` file lines, `<= 50` function lines across `lora_trainer.py` and `lora_record_validator.py`).
- Evidence scope & blockers: Strictly offline synthetic fixtures in `tmp_path` and stub tokenizers/trainers. Structural JSON metadata validation does not prove cryptographic/biometric speaker authenticity. Zero model downloads, zero network requests, and zero live QLoRA training runs were performed; live training remains blocked on host CUDA availability (`torch 2.11.0+cpu`), missing `.venv` packages (`peft`, `bitsandbytes`, `accelerate`), verbatim corpus verification, and explicit 012 authorization.

**WSP Compliance**: WSP 34 (Test Documentation), WSP 22 (ModLog Updates), WSP 97 (Test Inventory / Reuse Gate)

## 2026-11-05 — Cross-owner ready-only regression controls

Focused source-bound RED23: 18 failures/5 passes; GREEN23 + quality37: 60 passes,
zero errors/skips/denied effects. The earlier RED22 is preserved separately.
Coverage includes warm/cold useful generation, cache sentinels, constructor and
embedding-loader spies, cancellation and unchanged default cold query behavior.
No legacy ML build suite, Chroma process or actual corpus/model was run.

**WSP Compliance**: WSP 34 (Test Documentation), WSP 22 (ModLog Updates)

## Purpose
- Record test executions, commands, environments, and outcomes.
- Provide reproducible evidence for verification steps.

## Format (minimum)
- date/time
- command(s)
- pass/fail
- short failure signature (if any)
- evidence location (log file, screenshot)

## Entries

- 2026-10-18 (recorded 12:31 UTC)
  - Command: `PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -B -m pytest -q -p no:cacheprovider modules/ai_intelligence/digital_twin/tests/test_comment_drafter.py`
  - Result: PASS (39/39); console evidence: `39 passed, 2 warnings in 0.15s`.
  - Coverage: three existing drafter tests plus station factory isolation,
    system-policy/untrusted-source separation, caller initiation and source
    bindings, a 2,400-character context cap, exact 280/281-character draft bounds,
    structured decisions, disclosure, unsupported claims/links, and no-publication
    metadata. Missing-model, mock-mode, inference-failure, and malformed-output
    cases return no draft.
  - Environment: Python 3.12; bytecode and pytest cache writes disabled; plugin
    autoload disabled. The two warnings concern the existing async configuration
    options without the async plugin. No test failed or was skipped.
  - Evidence scope: an injected offline backend returns controlled JSON through
    the real chat wrapper; a nonexistent GGUF path exercises model unavailability.
    This is not live-model semantic, factuality, or prompt-injection quality
    evaluation. No live inference, network use, or publication was performed.
  - Separate smoke: fresh `python -B` process imported the real
    `CommentDrafter` package with guards against network/subprocess actions,
    filesystem writes, SQLite/`.env` reads, and legacy constructors. PASS: none
    attempted; `llama_cpp`, `chromadb`, `sqlite3`, and `selenium` were not loaded.
    No Digital Twin package-init change was required.
- 2026-08-22
  - Command: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q -p pytest_cov modules/ai_intelligence/digital_twin/tests/test_resident_conversation_transport_contract.py --cov=modules.ai_intelligence.digital_twin.src.resident_conversation_transport_contract --cov-report=term-missing --cov-fail-under=100`
  - Result: PASS (36/36); 100% statement and branch coverage for the new contract.
  - Coverage: exact shape, authority-field injection, native JSON types,
    operation/revision semantics, digest bindings, expiry/future clock bounds,
    use-time freshness, Unicode/control characters, content-free projection,
    forged object rejection, and WSP-62 limits.
  - Environment note: two pre-existing pytest configuration warnings reported
    missing async plugin options; no test was skipped, deselected, or failed.
  - Module closure: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q modules/ai_intelligence/digital_twin/tests` PASS (117/117).
  - Dependency closure: `cd extensions/reddog && npm run test:conversation`
    PASS (15 JavaScript vectors; 32 Python contracts).
  - Registry: `python modules/infrastructure/wre_core/scripts/generate_test_registry.py --check`
    PASS (`current`, 1,567 tracked tests; new test is collectable and not quarantined).
- 2026-08-22
  - Command: `cd extensions/reddog && npm run test:conversation`
  - Result: PASS (15 shared JS vectors; 32 Python contract tests).
  - Coverage: default chat, read-only research/status, proposal-only work and
    authorization, cancel authority requirement, ambiguous `do it`, risk-only
    reasoning escalation, strict rehydration, and effect-ceiling rejection.
- 2026-08-06
  - Command: `pytest -q modules/ai_intelligence/digital_twin/tests/test_principal_memex_projection.py`
  - Result: PASS (32/32)
  - Coverage: round-trip rehydration, digest tamper, cross-principal and
    duplicate rejection, exact JSON type policy, secret material,
    pre-traversal mapping bounds, factory-bound typed results,
    multi-generation supersession, and no-authority fields.
- 2026-02-04
  - Command: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest modules/ai_intelligence/digital_twin/tests`
  - Result: PASS (17/17)
  - Modules: test_comment_drafter (3), test_decision_policy (6), test_trajectory_logger (4), test_voice_memory (4)
  - Notes: `include_videos=False` in unit tests to avoid ChromaDB Rust segfault.
