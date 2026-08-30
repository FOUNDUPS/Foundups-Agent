# RedDog Documentation Map

Status: canonical navigation entry point

Use this map before broad text search. A 2026-08-30 inventory found 376
Markdown/JSON/YAML files containing `RedDog` or `reddog`; that count includes
tests, receipts, audits, generated manifests, and historical evidence. It does
not mean RedDog has 376 canonical specifications.

## Read order

| Need | Canonical entry | Authority |
|---|---|---|
| What RedDog is becoming | `docs/REDDOG_OUTCOME_VISION.md` | Product North Star; future statements are not implementation claims |
| Current extension/runtime truth | `extensions/reddog/README.md` | Current product/runtime status |
| Public extension contract | `extensions/reddog/INTERFACE.md` | Supported interface and authority boundary |
| Delivery sequence and gaps | `extensions/reddog/ROADMAP.md` | Planned and completed product work |
| Recurring human connection | `extensions/reddog/docs/REDDOG_LICK_CONNECTION_HANDSHAKE.md` | Product contract; specified, not implemented |
| FoundUps/second-brain architecture | `docs/architecture/REDDOG_FOUNDUPS_SECOND_BRAIN_ARCHITECTURE.md` | Architecture decision context |
| Phase-1 alignment findings | `docs/audits/architecture/REDDOG_CANONICAL_ARCHITECTURE_ALIGNMENT_PHASE1.md` | Evidence audit, not runtime authority |
| Lick/Gemini/patent findings | `docs/audits/architecture/REDDOG_LICK_HANDSHAKE_AUDIT_PHASE1.md` | Evidence audit, not runtime authority |
| Public member digital-twin contract | `public/member/RED_DOG_DIGITAL_TWIN_CONTRACT.md` | Public-surface contract |
| FoundUps domain integration | `modules/foundups/docs/FOUNDUPS_DOMAIN_CANONICAL_INDEX.md` | FoundUps domain navigation |
| Sensitive evidence/secret boundary | `WSP_framework/src/WSP_71_Secrets_Management_Protocol.md` §2.3 | Security requirements that reference, but do not redefine, the Lick |
| Protocol-level digital-twin authority | `WSP_framework/src/WSP_73_012_Digital_Twin_Architecture.md` | WSP authority; product handshakes do not belong here |

## Ownership boundaries

- `extensions/reddog/` owns the RedDog product, interface, roadmap, product
  handshakes, and extension-local verification evidence.
- `docs/architecture/` owns cross-domain architectural decisions.
- `docs/audits/` owns point-in-time evidence and correction reports.
- `modules/foundups/` owns the FoundUps domain model and monorepo integration
  references.
- `public/member/` owns the public member-facing contract surface.
- `WSP_framework/` owns protocols only. A feature, product handshake, use case,
  or feasibility study is not a WSP merely because RedDog uses it.
- `WSP_knowledge/` may retain papers, patent material, evidence, and historical
  memory; those records are not current product implementation truth.

## RedDog operating chain

The canonical division of responsibility is:

`0102 Hub develops -> pfMALL presents -> AutoPost captures/routes -> RedDog operates`

The Lick runs at the RedDog engagement boundary. AutoPost can supply a
permissioned capture event, but it does not decide identity or grant authority.

## Historical and generated material

Treat these as evidence, not entry points:

- `WSP_knowledge/red_dog_external_state/` — external-state shelf and historical
  continuity material;
- `docs/audits/` — truthful at the audited base commit, potentially superseded;
- `extensions/reddog/docs/acceptance/` and test receipts — bounded verification
  evidence;
- generated manifests and index files — machine navigation/integrity data; and
- `archive/` and `_archive/` — retained history.

Do not move or concatenate these files merely to reduce search results. Link
them from the owning canonical document when they materially support a current
claim.

## Search fallback

When canonical semantic retrieval is unavailable, use scoped literal search:

```bash
rg -n -i "RedDog|reddog" extensions/reddog docs modules/foundups public/member WSP_framework/src/WSP_73_012_Digital_Twin_Architecture.md
```

Confirm status labels and base commits before treating an audit or receipt as
current truth.
