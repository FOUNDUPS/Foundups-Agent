# Moshpit Canonical Term WSP 97 Audit - Phase 1

**Date:** 2026-09-20  
**Status:** terminology canonicalization / no runtime activation  
**WSP lock:** WSP 00, WSP 22, WSP 50, WSP 60, WSP 97

## Decision

Canonical human-facing term: **Moshpit**  
Canonical machine token: **`moshpit`**

Do not introduce new active uses of:
- `Mosh Pit`
- `MOSH_PIT`
- `mosh_pit`

Historical evidence may retain old spellings when rewriting it would falsify the record.

## WSP 97 evidence

Repository retrieval found that the YUMORI/FoundUps implementation vocabulary had already converged on the concatenated form:

- `.agents/skills/yumori-moshpit/SKILL.md`
- `.claude/skills/yumori-moshpit/SKILL.md`
- `modules/foundups/esingularity/skillz/yumori_moshpit/SKILLz.md`
- `docs/012_moshpit/` corpus convention
- `MOSHPIT_SKILL_PATH` in eSingularity contract tests

The split form remained primarily in RedDog architecture prose, one architecture filename, and the not-yet-implemented Memex projection contract.

## Micro pass

The RedDog architecture document was named:

`MOSH_PIT_ACTIVITY_MEMORY_ARCHITECTURE.md`

and active documentation referred to **Mosh Pit**, while the YUMORI Skillz already used **Moshpit**.

The Memex projection specification used `mosh_pit`; search found no implemented runtime consumer requiring that token.

## Macro pass

Keeping multiple spellings fragments:
- literal repository search;
- HoloIndex term retrieval;
- STT/alias normalization;
- skill discovery;
- future route/projection identifiers;
- documentation linking.

Canonicalizing before the renderer is implemented avoids a later compatibility migration.

## Change

- Rename active architecture path to `MOSHPIT_ACTIVITY_MEMORY_ARCHITECTURE.md`.
- Change active prose to **Moshpit**.
- Change the specified projection token from `mosh_pit` to `moshpit`.
- Update active links and the existing identity-boundary path assertion.
- Preserve historical audit/receipt text where it is evidence of the state at that time.

## Truth boundary

OBSERVED:
- concatenated Moshpit identifiers already exist in active YUMORI/WRE code and skills;
- split RedDog terminology existed on main at the audited base;
- the unified Moshpit renderer remains not implemented.

NOT CLAIMED:
- no renderer was implemented;
- no memory database was created;
- no runtime API migration occurred;
- no historical evidence was rewritten;
- no public route or deployment changed.
