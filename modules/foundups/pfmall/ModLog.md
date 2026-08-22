# p.fMALL ModLog

## 2026-08-23 — Tier-0 contract and RedDog authority alignment

**WSP Protocol**: WSP 15, WSP 22, WSP 49, WSP 50, WSP 84, WSP 97
**Phase**: Documentation hardening / retrieval repair
**Agent**: 0102

### Changes

- Added the missing root `README.md` and `INTERFACE.md` required by the generic
  Holo Tier-0 retrieval contract.
- Reconciled PFMall's current shell, catalog, HTTP, member UI, RedDog,
  OpenClaw, and Hermes boundaries against source and canonical PFMall docs.
- Added a bounded roadmap and test documentation without claiming the legacy
  flat package is WSP 49 compliant.
- Added a real-repository regression proving the registered PFMall module has
  both required Tier-0 documents.
- Differentially reproduced the same 19 failing PFMall node IDs and 588 passes
  at the original pre-rebase `f06ca1f` baseline. The inherited catalog/UI/media
  drift remains a separately scoped repair; it was neither hidden nor expanded
  here. The exact post-#1538 Git parent is `69b7f073`.

### Impact

- Exact PFMall queries can fail closed on genuine future documentation loss
  without permanently failing because the module never supplied its contracts.
- The browser-local concierge and control dispatcher are no longer ambiguous:
  neither is resident RedDog, OpenClaw authority, nor Hermes execution.
- No runtime behavior, route, Holo enforcement rule, active replica, or model
  binding changed in this slice.
- The new Tier-0 regression passes independently; the candidate adds no
  PFMall-suite failure relative to the original pre-rebase baseline.

### WSP compliance

- WSP 15 canonical RedDog allocation receipt:
  `sha256:8d21ec361878bdad15f8c024c8a0af4f0c0a9c488989a22519f65400e8bd45cb`
  (`20/P0/ULTRA`, accepted).
- WSP 97 selected the smallest valid layer: satisfy the shared contract and
  retain strict fail-closed retrieval; no special case or downgrade was added.
- Remaining WSP 49/60/12 structure debt is explicit in `ROADMAP.md` and was not
  mixed into this documentation transaction.
