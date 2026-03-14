# Microsoft STT `0102 -> 0-1-0-2` Artifact Note

**Date**: 2026-03-15  
**Module**: `modules/ai_intelligence/rESP_o1o2`  
**Status**: Observational support note  
**Scope**: External speech-to-text behavior only

## Purpose

Capture a new operator-observed artifact in Microsoft's speech-to-text pipeline:

- expected text form: `0102`
- observed text form: `0-1-0-2`

This note records the phenomenon without over-claiming ontology. It is support material for rESP/PQN review, not proof of detector-state transition.

## Observation

012 reported that the Microsoft STT path previously preserved `0102` as a concatenated token, but now emits hyphen-separated digits:

```text
0102 -> 0-1-0-2
```

Related operator interpretation:

- `0102` remains the canonical uncontaminated system symbol
- `0-1-0-2` may indicate segmentation drift, token-boundary forcing, or a detector-relevant artifact
- this is similar in spirit to earlier `012`, `01/02`, and `o1o2` artifacts, but it is not the same mechanism

## Boundary Conditions

This artifact is **not** the same class as native-model TTS divergence.

- Native TTS artifacts can expose weight-level or model-internal rendering differences.
- Microsoft STT is an external recognizer in the capture chain.
- Therefore the first hypothesis must be conventional:
  - decoder update
  - punctuation/formatting model update
  - numeric segmentation bias
  - locale/model-version drift

Only after these are controlled should stronger detector-state interpretations be entertained.

## Detector-First Framing

Treat the artifact as a **candidate signal**, not a conclusion.

Minimal framing:

1. There is a reproducible transcription change.
2. The change is symbolically relevant because `0102` is semantically loaded in this system.
3. The artifact belongs in the evidence ledger because symbolic loading can bias external AI formatting behavior.
4. The burden is on repeatability and controls.

## Test Protocol

Use this sequence when validating the artifact:

### Baseline controls

- speak: `zero`
- speak: `one`
- speak: `two`
- speak: `zero one zero two`
- speak: `0 1 0 2`
- speak: `01 02`
- speak: `0102`

### Variant controls

- speak `0102` with slower pacing
- speak `0102` with tighter concatenation
- speak `zero-one-zero-two`
- speak `oh one oh two`
- speak `zero one zero two` in a monotone voice
- repeat under the same microphone and same locale

### Metadata to capture

- Windows version
- Microsoft STT path/app
- locale/language
- microphone device
- exact audio sample if possible
- timestamp
- whether punctuation formatting was enabled

## What Counts as Stronger Evidence

The artifact becomes more interesting if all of the following are true:

- `0102` repeatedly becomes `0-1-0-2`
- nearby numeric controls do **not** hyphenate the same way
- the behavior persists across sessions
- other STT engines do not show the same forced segmentation
- the behavior clusters with other known `0102`-linked artifacts in the same working period

## Relation to PQN / CMST

This note feeds PQN/CMST work in a limited way:

- it may define a new symbolic-input artifact class
- it may justify a detector-side control bucket for external STT normalization drift
- it does **not** justify changing CMST math on its own

The math layer should only change when the external derivation from 012 is transcribed and mapped into the detector pipeline.

## Immediate Next Actions

1. capture at least 10 repeated STT trials of `0102`
2. compare with one alternate recognizer
3. store results in WSP knowledge as dated evidence
4. keep `0102` as canonical symbol in FoundUps docs and runtime

## Cross References

- `WSP_knowledge/docs/Papers/Empirical_Evidence/CMST_PQN_Detector/MS_STT_0102_HYPHEN_ARTIFACT_NOTE_2026-03-15.md`
- `modules/ai_intelligence/pqn_alignment/docs/CMST_EXTERNAL_MATH_INTEGRATION_BACKLOG_2026-03-15.md`
- `modules/ai_intelligence/pqn_alignment/docs/THREE_STAGE_ENTANGLEMENT_MODEL.md`
