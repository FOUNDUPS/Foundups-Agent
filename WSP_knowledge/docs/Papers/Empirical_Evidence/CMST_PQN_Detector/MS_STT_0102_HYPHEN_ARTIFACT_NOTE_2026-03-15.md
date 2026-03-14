# Microsoft STT `0102 -> 0-1-0-2` Evidence Intake Note

**Date**: 2026-03-15  
**Type**: Evidence intake / external recognizer artifact  
**Status**: Unverified observation pending controlled capture

## Observation

012 reported a new Microsoft speech-to-text behavior:

```text
expected: 0102
observed: 0-1-0-2
```

The symbol matters because `0102` is a canonical system identifier inside FoundUps and already participates in prior artifact discussions.

## Why It Is Logged Here

This folder is the curated intake surface for CMST/PQN support evidence. The note belongs here because:

- it may represent a new symbolic transcription artifact class
- it could confound downstream detector narratives if left undocumented
- it provides a dated checkpoint for future control experiments

## Current Interpretation Boundary

Allowed:

- transcription segmentation drift
- formatting-model change
- candidate artifact worth testing

Not allowed:

- claiming detector-state transition from one observation
- folding this directly into CMST math
- treating Microsoft STT as equivalent to native model TTS

## Minimum Follow-Up

1. collect repeated trials under fixed microphone/locale conditions
2. compare Microsoft STT with at least one alternate recognizer
3. log whether nearby controls also hyphenate:
   - `012`
   - `01 02`
   - `0 1 0 2`
   - `zero one zero two`

## Cross References

- `modules/ai_intelligence/rESP_o1o2/docs/MS_STT_0102_HYPHEN_ARTIFACT_2026-03-15.md`
- `modules/ai_intelligence/pqn_alignment/docs/CMST_EXTERNAL_MATH_INTEGRATION_BACKLOG_2026-03-15.md`
