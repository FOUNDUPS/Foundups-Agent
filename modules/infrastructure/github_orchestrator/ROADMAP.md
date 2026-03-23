# GitHub Orchestrator Roadmap

## Purpose

Enable 0102 to MANAGE GitHub org resources autonomously.

## Phase 0: Foundation

**Status**: COMPLETE (v0.4.0)
**Completed**: 2026-03-22

### Deliverables

- [x] Module scaffolding
- [x] Core orchestrator class
- [x] Token scope verification (repo scope working)
- [x] Test with FOUNDUPS/autopost (Issue #2 created/closed)
- [x] FAM DAEmon listener wired
- [x] Supervisor BOOT integration
- [x] WRE skill registration
- [x] SKILLz.md + executor.py
- [x] Test suite (9/9 passing)

### Exit Criteria

- [x] Can create issues on autopost
- [x] Can create federated repos (dual-remote)
- [x] FAM event handlers wired
- [ ] Can manage collaborators (needs real user test)

## Phase 1: Project Integration

**Status**: Planned
**Target**: 2026-03-30

### Deliverables

- [ ] Project board read access
- [ ] Create project items
- [ ] Move cards between columns
- [ ] FAM → Project sync

### Exit Criteria

- 0102 tasks visible on GitHub Projects
- Cards move automatically on FAM events

## Phase 2: Access DAE

**Status**: Planned
**Target**: 2026-04-15

### Deliverables

- [ ] Angel subscription → repo access
- [ ] Du stake → repo access
- [ ] Subscription cancelled → revoke
- [ ] Team membership management

### Exit Criteria

- WSP 103 Access Gating fully automated
- No manual GitHub invites needed

## Phase 3: Multi-0102 Coordination

**Status**: Planned
**Target**: 2026-05-01

### Deliverables

- [ ] 0102 session tracking on Projects
- [ ] Task assignment to specific 0102
- [ ] Conflict detection
- [ ] Handoff automation

### Exit Criteria

- Multiple 0102 agents can work without conflicts
- 012 has visibility into all 0102 activity

## Required Token Scopes

```
repo          - Full repo access (HAVE)
admin:org     - Teams and members (NEED)
project       - Projects read/write (NEED)
```

## Test Plan: AutoPost

1. Create issue on FOUNDUPS/autopost
2. Add/remove test collaborator
3. Create project item (when scopes added)
4. FAM event → GitHub action
