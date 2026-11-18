# Preserved historical record: CODEX_STORAGE_SELF_AUDIT_WSP97_20260905.md

> Historical/proposal material. This is not a current acceptance receipt, runtime check or instruction to apply old code. The original dates and claimed outcomes below retain their historical scope.

- Original relative path: `docs/audits/architecture/CODEX_STORAGE_SELF_AUDIT_WSP97_20260905.md`
- Original PC base: `0c81418fe94a7786cfd55f01e138ddc5d510583d`
- Original full file SHA-256: `b6ab5bd152eeccea7e9c2a0e9a02012d5f71d16b13e43cc8429b0f47e56dccf7`
- Preserved record SHA-256: `b6ab5bd152eeccea7e9c2a0e9a02012d5f71d16b13e43cc8429b0f47e56dccf7`
- Projection created: `2026-10-30T02:00:12.626831+00:00` (processing time only; not a new observation)
- Comparison reference: `cbef41fbae1ba1105398183e42b008f2e7dfd3dc`
- Publication: proposed; independent auditor acceptance pending.
- Current owner(s): [extract_brain_artifacts.py](../../../../../../../../modules/infrastructure/wre_core/scripts/extract_brain_artifacts.py)

Disposition: Publish only a sanitized historical storage audit projection. Preserve the raw host inventory privately. Keep the useful check-size, checkpoint, junction verification and recovery method; do not repeat relocation or regard September execution results as current machine observations.

Private host paths and unresolved external identifiers may be omitted only in this projection; raw originals remain in the private custody backmap. External citations are retained as historical references and have not been refreshed. Runtime and commenting remain unverified.

## Historical content

# Codex Storage Self-Audit and Remediation — 2026-09-05

## Decision

**PROCEED** with compression of the already relocated Codex archive and with
repository configuration reconciliation. **DO NOT MOVE** the live Codex
`sessions`, SQLite databases, credentials, plugins, or ChatGPT project store
while Codex Desktop is running.

Truth boundary: local filesystem measurements and executable checks are
machine-local operational evidence. They do not establish a supported
cross-host Codex data-directory contract.

## WSP 97 evidence loop

- Retrieve WSPs: WSP 00, 22, 50, 84, and 97 were read and applied.
- Retrieve evidence: measured the Codex profile without following the archive
  junction; inspected modification times, file counts, logical sizes, drive
  capacity, and repository path/model references.
- Research: the governed HoloIndex query failed closed with
  `HOLOINDEX_AUTHORITY_ROOT_HEAD_MISMATCH`, `freshness=UNKNOWN`, and
  `index_gap_detected=true`; no reindex was attempted. The official OpenAI
  configuration reference was then checked for supported storage controls.
- Micro pass: distinguish active state from inactive archived transcripts.
- Macro pass: preserve C: for live profile state, O: for agent history, and E:
  for local-AI/model state.
- Hard-think/dialectic: deleting transcripts gives more space but destroys
  history; moving live stores risks the active app; transparent archive
  compression preserves both content and logical paths.
- First principles: preserve bytes, avoid concurrent writers, and verify every
  storage transformation with counts, logical bytes, hashes, and application
  access.
- Execute: compress only `[PRIVATE_HOST_PATH_OMITTED]`, retain the C:
  junction, reconcile stale Foundups examples, and re-run code/runtime checks.

## Evidence inventory

| Codex path | Size | Files | Classification | Action |
|---|---:|---:|---|---|
| `archived_sessions` | 151.82 GiB | 781 | Inactive JSONL history | Already moved to O:; compress transparently |
| `sessions` | 6.16 GiB | 418 | Live and historical rollout state | Protect; several files are actively changing |
| `.chatgpt-projects` | 1.70 GiB | 23,483 | App-managed project material | Protect; unsupported internal layout |
| `logs_2.sqlite` | 0.56 GiB | 1 | Actively written database | Protect |
| `plugins` | 0.45 GiB | 1,663 | Installed runtime | Protect |
| `.sandbox-bin` | 0.29 GiB | 1 | Active Codex executable | Protect |
| `.tmp` | 0.14 GiB | 6,118 | Mostly July/August temporary material | Leave in place; low reward and undocumented ownership |

The archive is the bloat source: all 781 files are JSONL, and 454 files larger
than 100 MiB account for 150.38 GiB. A bounded sample of twelve large files
compressed to an average 18.4% of its original size. This supports filesystem
compression without inspecting or disclosing transcript content.

The live-session filename date is not a safe age signal. During this audit, a
rollout whose filename begins `2026-08-15` was actively modified on 2026-09-05.
Consequently, no session file is deleted, moved, or classified stale from its
name alone.

## Official product boundary

The [official OpenAI configuration reference](https://developers.openai.com/codex/config-reference/)
documents `history.max_bytes` and `history.persistence` specifically for
`history.jsonl`. It does not document a supported alternate location or size
cap for Codex Desktop rollout/session storage. `history.jsonl` is negligible
on this host, so changing those settings would not remediate the measured
bloat and was rejected.

## Repository reconciliation

- OpenClaw runtime/config already uses the installed
  `qwen-overseer:latest` model and a bounded 120-second cold-start timeout.
- `.env.example` and `moltbot_bridge/docs/CHANNEL_SETUP.md` were stale and have
  been reconciled to the same model; the example now exposes the timeout.
- The Antigravity brain extractor uses portable
  `Path.home() / ".gemini" / ...`, not a physical-drive literal. Its stable
  logical path resolves through the verified `.gemini` junction to O:, so no
  runtime code change is necessary.
- Existing logical C: references to `.gemini` or `.cursor` remain valid through
  verified junctions. Historical screenshots and audit evidence are not
  rewritten as if they had originally lived on O:.

## Remediation acceptance

- Archive junction remains `[PRIVATE_HOST_PATH_OMITTED]` ->
  `[PRIVATE_HOST_PATH_OMITTED]`.
- Archive file count and logical byte total remain exactly unchanged.
- Before/after SHA-256 probes match.
- O: archive directory retains the compressed attribute so future archived
  files inherit compression.
- C: live Codex state remains operational throughout.
- Final allocation recovery, application checks, code tests, and WSP 97 receipt
  validation are recorded after execution.

## Execution results

- NTFS reports **781 compressed files, 0 uncompressed files**.
- Logical content remained exactly **163,017,412,676 bytes** through both the
  O: destination and original C: junction.
- NTFS allocation is **104,407,281,664 bytes**, a reduction of
  **58,610,131,012 bytes (54.58 GiB)**, with a reported 1.6:1 ratio.
- Three large pre/post SHA-256 probes matched and all eight bounded workers
  reported zero failures.
- Final drive capacity: C: **177.40 GiB free**, E: **589.55 GiB free**, and O:
  **650.77 GiB free**.
- Runtime reconciliation: Ollama API reachable with four models and both
  `qwen-overseer:latest` and `gemma2:2b`; LM Studio CLI operational; Gemini
  extractor resolved to `[PRIVATE_HOST_PATH_OMITTED]`; Cursor config
  and Codex archive readable through their original paths.
- Final live code-path probe: `OpenClawDAE._execute_conversation()` selected
  `model=qwen-overseer:latest`, `timeout=120.0`, reported `engine=ollama`, and
  returned `0102: Final_PATH_RECONCILIATION_OK`.
- Code validation: complete `test_openclaw_dae.py` replay returned
  **106 passed, 2 warnings** in 47.90 seconds. The warnings are existing unknown
  pytest configuration options.
- Final classification: `VALIDATED_OPERATIONAL` for this machine's compressed
  archive, junction-backed storage topology, and tested Foundups paths.
- Both repository-bound WSP 97 v1.1 receipts validated as compliant with all
  seven mantra stages derived and no violations.
