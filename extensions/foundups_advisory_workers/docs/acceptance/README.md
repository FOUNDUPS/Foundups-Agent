# Foundups(R)Agent External Acceptance Artifacts

Store **redacted baseline records** from `REDDOG_EXTERNAL_ACCEPTANCE_BASELINE_PHASE1` runs here.

## Rules

- One JSON or Markdown file per run: `baseline_<test_id>_<YYYYMMDD>.md`
- Never commit raw env values, API keys, or unredacted blocked payloads
- Copy MD packets may be pasted in full only after local redaction review
- `installed_version_confirmed` must match `extension_version` before scoring

## Template

See `../REDDOG_EXTERNAL_ACCEPTANCE_BASELINE_PHASE1.md` section **Baseline Record Template**.

## Baseline pass (v0.3.21)

Record scores honestly. This pass measures usefulness; it does not require fixes in the same slice.

## Replacement pass (future)

Re-run the **same 15 prompts** after HoloIndex index-gap and dispatch improvements. Compare verdicts and rubric scores against baseline artifacts in this directory.
