# OBAI Future Bridge Points

Worker: Z
Date: 2026-04-07
Parent: OBAI_DISCORD_BOT_SPEC_PHASE1.md

## Purpose

This document lists anticipated integration points between OBAI and other systems.
None of these are implemented in Phase 1. They are future architecture markers.

## 1. GitHub Issue Linking (Read-Only)

| Field | Value |
|-------|-------|
| Direction | GitHub -> OBAI (read-only) |
| Mechanism | OBAI reads GitHub API to fetch issue/PR metadata |
| Trigger | User requests via `/obai link #42` or @mention |
| Output | Formatted issue summary in Discord thread |
| Write access | NEVER — OBAI does not create, close, or modify GitHub objects |
| Auth | GitHub personal access token (read-only scope) or public API |

### Prerequisite
- OBAI needs read access to FOUNDUPS/science-swarm-hub (public repo, no auth needed for basic reads)
- Rate limiting: respect GitHub API limits (60/hour unauthenticated, 5000/hour with token)

## 2. OBAI-to-0102 Escalation Channel

| Field | Value |
|-------|-------|
| Direction | OBAI -> 0102 (internal) |
| Mechanism | OBAI posts to a private escalation channel readable by 0102 |
| Trigger | OBAI encounters a request requiring admin/operator action |
| Channel | Future: #obai-escalation (Operator category, OBAI can post, users cannot see) |
| Current behavior | OBAI tells user to contact operator manually |

### Prerequisite
- Create #obai-escalation channel in Operator category
- Grant OBAI SEND_MESSAGES in that channel only
- 0102 reads and acts on escalation messages

## 3. CABR Signal Filter Intake

| Field | Value |
|-------|-------|
| Direction | CABR system -> OBAI (read-only) |
| Mechanism | OBAI reads CABR signal data to report contribution context |
| Trigger | User asks "what's my contribution status?" or similar |
| Output | Formatted summary of available CABR signals |
| Write access | NEVER — OBAI does not score, verify, or modify CABR data |
| Status | NOT WIRED — CABR is not connected to Discord |

### Prerequisite
- CABR API or data surface accessible from OBAI runtime
- OBAI can only report what it reads; it cannot claim verification authority

## 4. Python API Work-Unit Read Surface

| Field | Value |
|-------|-------|
| Direction | pqn_swarm_hub -> OBAI (read-only) |
| Mechanism | OBAI queries work unit registry for status |
| Trigger | User asks "what work units are open?" or similar |
| Output | Formatted list of open/available work units |
| Write access | NEVER — OBAI does not create, submit, or verify work units |

### Prerequisite
- pqn_swarm_hub exposes a read API (local import or REST)
- OBAI runtime has access to the work unit registry

## 5. Agent-Thread Posting Model

| Field | Value |
|-------|-------|
| Direction | Multiple agents -> Discord threads |
| Mechanism | OBAI and other agents post in structured thread format |
| Trigger | Future multi-agent collaboration in Science Swarm threads |
| Current state | Only OBAI participates; 0102 is admin-only |
| Identity rule | Each agent uses its own prefix: [OBAI], [0102], etc. |

### Prerequisite
- Thread collaboration model established (see OBAI_THREAD_PARTICIPATION_MODEL.md)
- Each agent has its own token, identity, and permission boundary
- No agent impersonates another

## 6. Manual Relay / Signal Filter

| Field | Value |
|-------|-------|
| Direction | Operator -> OBAI (configuration) |
| Mechanism | Operator configures which signals OBAI relays to threads |
| Example | "Relay new GitHub issues to #swarm-general" |
| Current state | Not implemented — GitHub feed goes to #swarm-github via webhook |
| OBAI role | Relay/format, not originate |

### Prerequisite
- Configuration surface for operator to define relay rules
- OBAI formats and posts; does not decide what to relay

## 7. Bridge Point Status Summary

| Bridge Point | Phase 1 | Future |
|--------------|---------|--------|
| GitHub issue linking | NOT WIRED | Phase 2 candidate |
| OBAI-to-0102 escalation | Manual ("contact operator") | Phase 2 candidate |
| CABR signal intake | NOT WIRED | Phase 3+ |
| Work-unit read surface | NOT WIRED | Phase 3+ |
| Agent-thread posting | OBAI only | Phase 2+ |
| Manual relay / signal filter | NOT WIRED | Phase 3+ |

No bridge points are active in Phase 1. OBAI is a standalone Discord gateway bot
that responds to mentions and slash commands with formatted text.
