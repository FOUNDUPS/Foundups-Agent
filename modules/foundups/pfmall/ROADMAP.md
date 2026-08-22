# p.fMALL Roadmap

## Current baseline

- Implemented: manifest discovery/validation, catalog and tile projection,
  route resolution, optional advisory overlays, a read-only Python/FastAPI
  surface, static shell UI, member catalog export, presentation policy, and
  verification-gap guarding.
- Implemented in `public/member/`: admitted-member PWA, video Mall,
  shell-local FAQ concierge, and bounded browser control dispatcher.
- Not implemented: authenticated resident RedDog conversation adapter,
  browser-to-OpenClaw policy admission, or browser-to-Hermes execution.

## P0 — Tier-0 retrieval repair

- [x] Add root `README.md` and `INTERFACE.md` with current authority truth.
- [x] Add a real-repository Holo regression for the registered PFMall module.
- [ ] After merge, rebuild and activate one exact-main Holo generation, then
  prove an owner query is `CURRENT`, gap-free, read-only, and digest-stable.

## P1 — Resident RedDog adapter

- [ ] Bind the Mall client to the authenticated resident conversation ingress;
  do not treat `pfmall-control-dispatcher.js` as that transport.
- [ ] Define durable replay/idempotency and new-conversation creation before
  any mutation-bearing request is admitted.
- [ ] Translate only bounded, authenticated RedDog projections into existing
  Mall presentation commands.
- [ ] Preserve OpenClaw as policy/control plane and Hermes as admitted worker
  execution; neither authority belongs in the browser.

## P1 — Runtime convergence and deployment hardening

- [ ] Resolve the inherited original pre-rebase `f06ca1f` module-suite
  baseline: 19 failing node IDs / 588 passing. The failures cover catalog
  enum/projection drift, stale member-entry/concierge expectations, a
  hard-coded `O:` fixture, and absent tracked media directories. This Tier-0
  slice reproduced all 19 at that baseline and does not repair or quarantine
  them. Its exact post-#1538 Git parent is `69b7f073`.
- [ ] Reconcile the Python catalog projection and `public/member/` catalog
  generation so one canonical source owns each field.
- [ ] Put authentication/rate limits in front of the FastAPI surface before any
  production exposure containing non-public data.
- [ ] Convert aspirational isolation/sentinel clauses into implemented,
  evidence-backed gates one bounded layer at a time.

## P2 — Structural remediation

- [ ] Plan a separate, import-compatible migration from flat root Python files
  to `src/` per WSP 49.
- [ ] Add module-local dependency and memory contracts per WSP 12/60.
- [ ] Run FMAS and complete dependency/import analysis before any move. No
  deletion or broad restructuring is part of the Tier-0 repair.
