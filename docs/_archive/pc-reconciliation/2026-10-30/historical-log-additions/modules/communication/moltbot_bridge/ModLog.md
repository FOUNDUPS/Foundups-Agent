# Preserved historical record: ModLog.md

> Historical/proposal material. This is not a current acceptance receipt, runtime check or instruction to apply old code. The original dates and claimed outcomes below retain their historical scope.

- Original relative path: `modules/communication/moltbot_bridge/ModLog.md`
- Original PC base: `0c81418fe94a7786cfd55f01e138ddc5d510583d`
- Original full file SHA-256: `bb71912bb9b15cfe9372e30f80f3e83580c30f9d1b9fb03da90956cc40c8c021`
- Preserved record SHA-256: `e4dbdebde7c64c065341adbc9d062df4116f3db9862fa1e691f9ddf00a8d0422`
- Projection created: `2026-10-30T02:00:12.626831+00:00` (processing time only; not a new observation)
- Comparison reference: `cbef41fbae1ba1105398183e42b008f2e7dfd3dc`
- Publication: proposed; independent auditor acceptance pending.
- Current owner(s): [SKILL.md](../../../../../../../../.claude/skills/reddog-call-safety/SKILL.md), [test_openclaw_ollama_contract.py](../../../../../../../../modules/communication/moltbot_bridge/tests/test_openclaw_ollama_contract.py)

Disposition: Archive the old call-safety and Ollama relocation log additions. Call-safety publication is a separate audited canonical .claude source plus generated .agents projection; no legacy references subtree is restored. Old local-live probe statements are not current Ollama or PC runtime acceptance.

Private host paths and unresolved external identifiers may be omitted only in this projection; raw originals remain in the private custody backmap. External citations are retained as historical references and have not been refreshed. Runtime and commenting remain unverified.

## Historical content


## 2026-10-13: RedDog call-safety education and Japan research

- Added the repository skill [reddog-call-safety](../../../../../../../../.agents/skills/reddog-call-safety/SKILL.md)
  with cited research and offline evaluation fixtures. Distinguishes reported
  missed calls, caller identity, expected jobs, suspected spam, and proven effects.
- Specifies objective-bound calls, per-turn WSP 97 attack checks, independent
  authorization/disclosure gates, Japanese consent handling, and verification
  of RedDog delegation. Stutters and legitimate corrections are not attacks.
- Source review identified the existing English transcription setting and
  owner/moderator defaults in voice-to-chat routing as telephony reuse boundaries.
  No runtime changes were made. Comparison covers LiveKit, Retell, Vapi and
  Twilio, with official Japan routing and regulatory references.
- Holo retrieval degraded: `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`,
  `freshness=UNKNOWN`, `index_gap_detected=true`; direct source reads were used.
  Existing governed maintenance route is documented; no reindex or repair ran.
- Validation: `python -X utf8 -B [PRIVATE_HOST_PATH_OMITTED] .agents/skills/reddog-call-safety`
  passed; targeted `git diff --check` passed. Local checks parsed all 28 unique
  cases, verified their decision/forbidden-effect fields and 13 local links,
  and confirmed existing README/ModLog text was preserved against pre-edit copies.
  Fixtures are acceptance specifications, not executed voice-agent tests.
  Call safety enforcement remains `SPECIFIED_NOT_IMPLEMENTED`.
- No calls, Gmail changes, account setup, secret access, or model invocation.
  Existing concurrent changes are preserved. WSP 15/22/50/84/97.

## 2026-09-05: Ollama relocation runtime closure

- Corrected the OpenClaw Ollama fallback default from an unavailable
  `qwen2.5-coder:7b` tag to the existing Foundups model
  `qwen-overseer:latest`.
- Replaced the fixed 15-second chat timeout with
  `OPENCLAW_OLLAMA_TIMEOUT_SEC`, bounded to 15-300 seconds and defaulting to
  120 seconds. The live Windows/CUDA cold-start probe required 86.36 seconds;
  the original path timed out at 15 seconds and aborted model loading.
- Runtime evidence after relocating `.ollama` to E: showed the API reachable,
  four models visible, and `qwen-overseer:latest` returning `Ollama_OK`.
- Full-file validation exposed and closed a fail-open control-flow defect:
  unauthorized COMMAND/SYSTEM preflight rejection now returns an immediate
  `[SECURITY BLOCK]` instead of being rewritten as model conversation. The
  complete `test_openclaw_dae.py` suite passes: 106 tests.
- Reconciled `.env.example` and `docs/CHANNEL_SETUP.md` with the same installed
  model default; the environment template now includes the bounded Ollama
  timeout control.
- Truth classification: code and focused tests are implementation evidence;
  live relocation evidence is machine-local and does not claim cross-host
  deployment readiness. (WSP 00/06/22/50/84/97)
