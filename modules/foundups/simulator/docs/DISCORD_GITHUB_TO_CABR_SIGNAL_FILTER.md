# Discord / GitHub to CABR Signal Filter

**Status**: Canonical spec
**Owner**: 0102 (Worker N)
**Slice**: `FOUNDUPS_THRESHOLD_GAMING_AND_SUMO_PATTERN_SENTINEL_SPEC_PHASE1`
**Date**: 2026-04-06
**Parent**: WSP 29 (CABR Engine), WSP 26 Section 4.10

---

## 1. Problem

Discord activity and GitHub activity need to feed CABR's `part_score` without:
- turning raw message counts into direct payouts
- collapsing Un and Dao routing
- creating a message-farming incentive
- bypassing the 3V verification pipeline

Currently, `cabr_estimator.py:update_participation()` takes `tasks_completed`, `tasks_total`, `active_agents`, and `verifications` — all FAM pipeline signals. Discord and GitHub are not wired in at all. The `governance_engagement` (0.15) and `cross_foundup_collaboration` (0.15) terms are hardcoded placeholders.

This document specifies how raw events become verified signals before they reach CABR.

---

## 2. Event Sources

### 2.1 Discord Events

| Event | Raw Signal | FoundUp Scope | Example |
|-------|-----------|---------------|---------|
| `message_sent` | User posted in a channel | Per-FoundUp (by channel prefix) or server-wide | Message in #autopost-work |
| `reaction_added` | User reacted to a message | Per-FoundUp or server-wide | React in #swarm-general |
| `thread_created` | User started a thread | Per-FoundUp | Thread in #swarm-work |
| `voice_joined` | User joined voice channel | Per-FoundUp | Join swarm-voice |
| `role_acquired` | User gained a role | Server-wide | Gained @swarm-contributor |

### 2.2 GitHub Events

| Event | Raw Signal | FoundUp Scope | Example |
|-------|-----------|---------------|---------|
| `pr_merged` | Code merged to protected branch | Per-repo (maps to FoundUp) | PR merged in FOUNDUPS/science-swarm-hub |
| `issue_closed` | Issue resolved | Per-repo | Issue closed with linked PR |
| `review_submitted` | PR review with comments | Per-repo | Substantive review on autopost PR |
| `commit_pushed` | Commits pushed to branch | Per-repo | Push to science-swarm-hub |
| `issue_created` | New issue filed | Per-repo | Bug report in autopost |

### 2.3 FAM Events (already wired)

| Event | Raw Signal | Status |
|-------|-----------|--------|
| `task_claimed` | Agent claimed a task | LIVE in FAM pipeline |
| `proof_submitted` | Task proof submitted | LIVE |
| `verification_recorded` | Verifier confirmed proof | LIVE |
| `payout_triggered` | Task completed, paid | LIVE |

---

## 3. Signal Filter Architecture

### 3.1 Filter Pipeline

```
Raw Events (Discord bot, GitHub webhook, FAM pipeline)
  │
  ▼
┌─────────────────────────────────────────────┐
│  STAGE 1: DEDUPLICATION                     │
│  - Same event from multiple sources → 1     │
│  - Idempotent by event_id                   │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  STAGE 2: CLASSIFICATION                    │
│  - Map event to FoundUp (by channel prefix  │
│    or repo name)                            │
│  - Map event to signal type                 │
│  - Map event to participant                 │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  STAGE 3: QUALITY GATE                      │
│  - Discard bot messages (by role)           │
│  - Discard empty/trivial signals            │
│  - Apply minimum thresholds                 │
│  - Apply rate limits per participant        │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  STAGE 4: WEIGHTING                         │
│  - Apply WSP 26 Section 4.10 signal weights │
│  - Discount repeated same-type signals      │
│  - Apply diminishing returns curve          │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│  STAGE 5: SENTINEL CHECK                    │
│  - Pass through ParticipationSentinel       │
│  - Pass through ThresholdSentinel           │
│  - Flagged signals get reduced weight or    │
│    excluded                                 │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
Verified Participation Signal → cabr_estimator.py:update_participation()
```

### 3.2 Signal Schema

```python
@dataclass
class VerifiedParticipationSignal:
    """A filtered, weighted participation signal ready for CABR."""

    participant_id: str          # Discord user ID or GitHub username
    foundup_id: str              # Which FoundUp this activity is for (or "ecosystem")
    signal_type: str             # "community", "code", "task", "verification", "governance"
    source: str                  # "discord", "github", "fam"
    raw_event_count: int         # How many raw events were aggregated
    weighted_score: float        # After quality gate + weighting + sentinel
    epoch: int                   # Which epoch this signal belongs to
    sentinel_flags: List[str]    # Any sentinel alerts raised (may be empty)
    timestamp: str               # ISO timestamp
```

---

## 4. Quality Gate Rules

### 4.1 Discord Quality Gate

| Rule | Rationale | Threshold |
|------|-----------|-----------|
| Minimum message length | Prevents "." or emoji-only farming | >10 characters (after stripping mentions/links) |
| Rate limit per channel per hour | Prevents flood farming | Max 20 messages/hour credited |
| Bot messages excluded | Bots are not participants | Filter by @Beneficial AI role or bot flag |
| Diminishing returns | 5th message in same channel same day is worth less than 1st | `weight = 1.0 / (1 + 0.3 * n)` where n = prior messages today |
| Thread creation bonus | Threads indicate substantive engagement | 2x weight vs. regular message |
| Voice channel minimum | Prevents join-and-leave | >5 minutes in channel |
| Reaction deduplication | One reaction per message per user | Deduplicate by (user, message_id) |

### 4.2 GitHub Quality Gate

| Rule | Rationale | Threshold |
|------|-----------|-----------|
| PR must be merged (not just opened) | Open PRs are not contributions | Only `pr_merged` counts |
| Review must have comments | Empty approvals are rubber-stamps | >0 review comments |
| Issue must be closed with linked PR | Issue-only farming is easy | `issue_closed` only if linked to merged PR |
| Commit count capped per PR | Prevents commit-splitting | Max 10 commits credited per PR |
| Self-merge excluded | Merging your own PR without review | Merger != author (unless solo maintainer) |

### 4.3 FAM Quality Gate

FAM events are already quality-gated by the task pipeline (V1→V2→V3). No additional filtering needed. FAM signals pass through at full weight.

---

## 5. Signal Weighting

### 5.1 WSP 26 Section 4.10 Alignment

WSP 26 defines engagement signal weights for the Play FoundUps dApp:

| Action | CABR Weight | Surface |
|--------|-------------|---------|
| Follow | 0.05 | PWA |
| Vote | 0.10 | PWA |
| Endorse | 0.25 | PWA |
| Advise | 0.30 | PWA |
| Stake UPS | 0.40 | PWA |
| Team (allocate 0102) | 0.50 | PWA |
| Promote | Multiplier | Any |

Discord and GitHub signals map to this hierarchy:

### 5.2 Discord Signal Weights

| Discord Event | Maps To | Weight | Rationale |
|--------------|---------|--------|-----------|
| Message in #[prefix]-general | Follow-level engagement | 0.05 | Passive discussion |
| Message in #[prefix]-work | Advise-level engagement | 0.15 | Active work coordination |
| Thread in #[prefix]-work | Advise-level (bonus) | 0.20 | Substantive topic creation |
| Reaction to announcement | Vote-level engagement | 0.05 | Light signal |
| Voice channel participation (>5 min) | Advise-level | 0.15 | Synchronous work coordination |
| Server-wide activity (#general, #off-topic) | Follow-level | 0.02 | Community presence, low signal |

### 5.3 GitHub Signal Weights

| GitHub Event | Maps To | Weight | Rationale |
|-------------|---------|--------|-----------|
| PR merged | Team-level engagement | 0.40 | Direct code contribution |
| PR review with comments | Endorse-level | 0.25 | Peer review |
| Issue closed with linked PR | Advise-level | 0.20 | Problem identification + resolution |
| Issue created (substantive) | Vote-level | 0.10 | Problem identification |

### 5.4 FAM Signal Weights

| FAM Event | Maps To | Weight | Rationale |
|----------|---------|--------|-----------|
| Task completed + verified | Team-level | 0.50 | Full 3V pipeline |
| Verification performed | Endorse-level | 0.25 | Peer verification |
| Task claimed | Vote-level | 0.10 | Intent to contribute |

---

## 6. FoundUp Scoping

### 6.1 Per-FoundUp Activity Routing

Discord channels map to FoundUps by prefix:

| Channel Prefix | FoundUp ID | Example |
|---------------|-----------|---------|
| `swarm-` | `science_swarm_hub` | #swarm-general, #swarm-work |
| `m2j-` | `move2japan` | #m2j-general, #m2j-work |
| `antifafm-` | `antifafm` | #antifafm-general, #antifafm-work |
| `autopost-` | `autopost` | #autopost-general, #autopost-work |
| `geoze-` | `geoze` | #geoze-general, #geoze-work |
| (no prefix — #general, #off-topic) | `ecosystem` | Server-wide, no FoundUp credit |

GitHub repos map to FoundUps by org/repo:

| Repo | FoundUp ID |
|------|-----------|
| `FOUNDUPS/science-swarm-hub` | `science_swarm_hub` |
| `FOUNDUPS/autopost` | `autopost` |
| `FOUNDUPS/Foundups-Agent` | `ecosystem` (core infrastructure) |

### 6.2 Cross-FoundUp Signal

Activity that spans multiple FoundUps (e.g., a PR in Foundups-Agent that affects autopost routing) feeds the `cross_foundup_collaboration` term in `part_score`. This replaces the current hardcoded 0.15 placeholder.

Calculation:
```python
cross_foundup = min(1.0, unique_foundups_contributed / 3)
# Contribute to 3+ FoundUps in an epoch → max cross-FoundUp score
```

### 6.3 Governance Signal

Governance engagement (currently hardcoded 0.15 placeholder) is fed by:
- Discord: Participation in #operator-log discussions, voting on proposals
- GitHub: Issue triage, label management, milestone review
- FAM: Treasury governance votes (WSP 29 Section 3.2)

Until FAM governance is live, this term is fed by:
```python
governance = min(1.0, (operator_log_messages + issue_triage_actions) / 10)
```

---

## 7. What This Does NOT Do

1. **Does not mint tokens from Discord activity.** Signals feed `part_score`, which feeds CABR, which controls UPS flow rate. No direct minting.
2. **Does not reward raw message count.** Quality gate + diminishing returns + sentinel filtering ensure volume alone has minimal impact.
3. **Does not bypass 3V for Dao.** Only FAM pipeline signals (V1→V2→V3 verified) feed Dao distributions. Discord/GitHub signals feed Un/community engagement only (see: `UN_VS_DAO_PARTICIPATION_BOUNDARY.md`).
4. **Does not create a new token.** Uses existing UPS + F_i economics.
5. **Does not require a Discord bot implementation.** This is a spec for the signal filter layer. The event collection mechanism (YAGPDB logging, Discord bot, webhook) is a separate implementation decision.

---

## 8. Implementation Notes

### 8.1 Event Collection (Out of Scope but Noted)

Event collection is the prerequisite for this filter. Options:
- **YAGPDB message logging** → export to CSV/JSON per epoch
- **Custom Discord bot** → emit events to FAM event stream
- **GitHub webhooks** → already planned for #[prefix]-github channels; same payload can feed the filter

The filter itself is agnostic to collection method. It takes raw events in a standard schema and outputs verified signals.

### 8.2 Epoch Alignment

All signals are aggregated per epoch. Discord/GitHub events within an epoch window are batched, filtered, weighted, and passed to `cabr_estimator.py:update_participation()` at epoch boundary.

### 8.3 File Location

```
modules/foundups/simulator/economics/signal_filter.py  ← NEW
```

Alongside `participation_sentinel.py` and the new `threshold_sentinel.py`.

---

*This filter is Layer 1 in the implementation order defined in `THRESHOLD_GAMING_SENTINEL_SPEC.md`. It must be built and tested before any sentinel can consume Discord/GitHub signals.*
