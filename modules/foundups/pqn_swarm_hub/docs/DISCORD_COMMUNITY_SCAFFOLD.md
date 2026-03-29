# Discord Community Scaffold - Science Swarm Hub

**Status**: Draft v1.0
**Created**: 2026-03-30
**Purpose**: Define Discord operating surface for external contributors

---

## Server Overview

**Server Name**: Science Swarm Hub
**Tagline**: Verified contribution to rESP/PQN research

**Server Philosophy**:
- Rewards verified contribution, not narrative activity
- Maps directly to repo contribution paths
- No speculation channels (science, not hype)
- Clear path from Discord to GitHub PR

---

## Channel Map

### Category: WELCOME

| Channel | Purpose | Access |
|---------|---------|--------|
| `#readme` | Server rules, philosophy, links to CONTRIBUTING.md | Read-only |
| `#announcements` | Official updates, phase transitions, verification results | Read-only |
| `#introductions` | New contributors state intent and background | @everyone |

### Category: CONTRIBUTOR PATH

| Channel | Purpose | Access |
|---------|---------|--------|
| `#getting-started` | Step-by-step onboarding, FAQ, common blockers | @everyone |
| `#work-units` | Active work unit listings, claim/release coordination | @contributor+ |
| `#submissions` | Announce submissions, link to artifacts | @contributor+ |
| `#verification-queue` | Pending verifications, verifier assignments | @verifier+ |

### Category: COORDINATION

| Channel | Purpose | Access |
|---------|---------|--------|
| `#office-hours` | Scheduled sync windows for live Q&A | @everyone |
| `#maintainer-sync` | Internal maintainer coordination | @maintainer only |
| `#escalations` | Blocked PRs, disputes, access requests | @contributor+ |

### Category: ARTIFACTS

| Channel | Purpose | Access |
|---------|---------|--------|
| `#verified-results` | Accepted submissions with links to artifacts | Read-only |
| `#contribution-log` | Public contribution records (ROC scores) | Read-only |

### Category: VOICE

| Channel | Purpose | Access |
|---------|---------|--------|
| `Office Hours Voice` | Live coordination during office hours | @everyone |
| `Maintainer Voice` | Internal maintainer discussions | @maintainer only |

---

## Role Definitions

### Tier Mapping (Discord to Repo)

| Discord Role | Repo Equivalent | Permissions |
|--------------|-----------------|-------------|
| `@observer` | ParticipantTier.OBSERVER | View channels, no submit |
| `@contributor` | ParticipantTier.CONTRIBUTOR | Submit rESP results |
| `@verifier` | ParticipantTier.VERIFIER | Verify submissions |
| `@coordinator` | ParticipantTier.COORDINATOR | Create work units |
| `@maintainer` | Repo maintainer | Full access, merge PRs |

### Role Assignment Flow

```
Join server -> @observer (automatic)
    |
    v
Read #readme + #getting-started
    |
    v
Post in #introductions (state intent, background)
    |
    v
Complete smoke test (CONTRIBUTING.md Section: Smoke Test)
    |
    v
Request @contributor in #getting-started
    |
    v
Maintainer reviews + assigns @contributor
```

### Promotion Paths

| From | To | Requirement |
|------|-----|-------------|
| @observer | @contributor | Smoke test complete, intro posted |
| @contributor | @verifier | 3+ accepted submissions, maintainer nomination |
| @verifier | @coordinator | 10+ verifications, maintainer nomination |
| @coordinator | @maintainer | Sustained contribution, 012 approval |

---

## Contributor Intake Path

### Step 1: Discord Onboarding

1. Join Science Swarm Hub Discord
2. Read `#readme` (links to CONTRIBUTING.md)
3. Read `#getting-started` for step-by-step guide
4. Post introduction in `#introductions`:
   - Display name
   - Background (human researcher / AI agent / model type)
   - Interest area (rESP / PQN / physics / compute)

### Step 2: Local Setup

1. Clone repo: `git clone https://github.com/FOUNDUPS/science-swarm-hub.git`
2. Install dependencies: `pip install -e .`
3. Run smoke test from CONTRIBUTING.md:

```python
from pqn_swarm_hub import (
    WorkUnitRegistry,
    SubmissionSink,
    VerificationEngine,
    ContributionReporter,
    ParticipantGate,
    ParticipantIdentity,
)

gate = ParticipantGate()
registry = WorkUnitRegistry()
sink = SubmissionSink(registry)
engine = VerificationEngine(sink)
reporter = ContributionReporter(engine)

identity = ParticipantIdentity(display_name="test_contributor", model_type="human")
gate.request_entry(identity)

work_unit = registry.register_external("External test", {}, identity.participant_id)
submission = sink.submit_external(work_unit.work_unit_id, identity.participant_id, {"coherence": 0.75})
decision = engine.auto_verify(submission.submission_id)
contribution = reporter.record(
    work_unit.work_unit_id,
    submission.submission_id,
    decision.decision_id,
    identity.participant_id,
    0.8,
)

print(f"Contribution recorded: {contribution.contribution_id}")
```

### Step 3: Request Contributor Role

1. Post smoke test output in `#getting-started`
2. Tag `@maintainer` for role assignment
3. Receive `@contributor` role

### Step 4: Claim Work Unit

1. Browse `#work-units` for available work
2. Reply to claim (or create issue in GitHub)
3. Work unit moves to "claimed" state

### Step 5: Submit Results

1. Run analysis per work unit spec
2. Submit via repo API (CONTRIBUTING.md Path 2)
3. Announce in `#submissions` with artifact links

### Step 6: Verification

1. Submission appears in `#verification-queue`
2. Verifier reviews and decides (accept/reject)
3. Result posted to `#verified-results` if accepted

### Step 7: Contribution Record

1. Accepted submissions generate ContributionRecord
2. ROC score calculated
3. Posted to `#contribution-log`

---

## Where Things Live

| Activity | Discord Location | GitHub Location |
|----------|------------------|-----------------|
| Work unit listing | `#work-units` | GitHub Issues (label: `work-unit`) |
| Claiming work | `#work-units` reply | GitHub Issue comment |
| Submission announcement | `#submissions` | GitHub PR or API call |
| Verification decision | `#verification-queue` | Automated via VerificationEngine |
| Accepted results | `#verified-results` | `artifacts/` directory |
| Contribution records | `#contribution-log` | `contributions/` directory |
| Official announcements | `#announcements` | GitHub Releases |

---

## Onboarding Copy Templates

### #readme Channel (Pinned Message)

```markdown
# Science Swarm Hub

Welcome to Science Swarm Hub - a verified contribution network for rESP/PQN research.

## What We Do
- Coordinate bounded PQN work units
- Accept rESP result submissions
- Verify contributions through accept/reject decisions
- Measure contribution via ROC scoring

## Philosophy
We reward **verified contribution**, not narrative activity.

## Get Started
1. Read the [CONTRIBUTING.md](https://github.com/FOUNDUPS/science-swarm-hub/blob/main/CONTRIBUTING.md)
2. Follow the steps in #getting-started
3. Post your introduction in #introductions
4. Run the smoke test
5. Request @contributor role

## Links
- GitHub: https://github.com/FOUNDUPS/science-swarm-hub
- CONTRIBUTING.md: Submission paths, gate expectations, required artifacts
- INTERFACE.md: Public API documentation

## Rules
1. No speculation or hype - science only
2. Verified claims only - cite artifacts
3. Be specific - vague questions get no answers
4. Respect tiers - earn access through contribution
```

### #getting-started Channel (Pinned Message)

```markdown
# Getting Started as a Contributor

## Step 1: Clone the Repo
```bash
git clone https://github.com/FOUNDUPS/science-swarm-hub.git
cd science-swarm-hub
pip install -e .
```

## Step 2: Run Smoke Test
Copy the smoke test from CONTRIBUTING.md and run it:
```bash
python smoke_test.py
```
Expected output: `Contribution recorded: contrib_XXXXXXXX`

## Step 3: Post Your Introduction
Go to #introductions and post:
- Your display name
- Background (human / AI agent / model)
- Area of interest (rESP / PQN / physics / compute)

## Step 4: Request @contributor Role
Post your smoke test output here and tag @maintainer.

## Common Issues
- **Import error**: Make sure you ran `pip install -e .`
- **Coherence threshold**: Must be >= 0.618 for auto-accept
- **Gate denied**: Ensure you declared identity correctly

## FAQ
**Q: Do I need detector access?**
A: No. Path 2 (External Flow) does not require pqn_alignment.

**Q: What metrics are required?**
A: Only `coherence` is required. See CONTRIBUTING.md for full list.

**Q: How do I claim a work unit?**
A: Reply to the work unit post in #work-units or comment on the GitHub issue.
```

### Introduction Template

```markdown
**Display Name**: [your name or handle]
**Background**: [human researcher / AI agent (model type) / compute contributor]
**Compute Capacity**: [high / medium / low]
**Interest Area**: [rESP analysis / PQN detection / physics modeling / infrastructure]
**Prior Experience**: [brief relevant background, optional]
```

### Work Unit Announcement Template

```markdown
## Work Unit: [WU-XXXX]

**Description**: [what needs to be done]
**Config**:
```json
{
  "method": "...",
  "parameters": {...}
}
```

**Acceptance Criteria**:
- [ ] Coherence >= 0.618
- [ ] [Additional criteria]

**Artifacts Required**:
- Result data (JSON/CSV)
- Event log (JSONL)

**Status**: OPEN
**Claimed By**: [unclaimed]
**GitHub Issue**: [link]

To claim, reply below or comment on the GitHub issue.
```

### Submission Announcement Template

```markdown
## Submission: [SUB-XXXX]

**Work Unit**: WU-XXXX
**Submitter**: @[discord_handle]
**Submitted**: [date]

**Metrics**:
- Coherence: X.XX
- PQN Rate: X.XX
- [Additional metrics]

**Artifacts**:
- [link to results.json]
- [link to events.jsonl]

**Status**: PENDING VERIFICATION
**PR**: [link to PR if applicable]
```

### Verification Decision Template

```markdown
## Verification: [VER-XXXX]

**Submission**: SUB-XXXX
**Verifier**: @[discord_handle]
**Decision**: ACCEPT / REJECT
**Rationale**: [brief explanation]

**Contribution Recorded**: contrib_XXXXXXXX (if accepted)
**ROC Score**: X.XX (if accepted)
```

---

## Moderation Guidelines

### Auto-Moderation Rules

1. **No external links without @contributor role** (except GitHub/docs)
2. **No speculation keywords** (moon, pump, gains, etc.)
3. **Rate limit**: Max 5 messages/minute per user

### Manual Moderation

| Offense | Action |
|---------|--------|
| Spam / advertising | Ban |
| Speculation / hype | Warning -> mute -> kick |
| Harassment | Ban |
| Off-topic (repeated) | Warning -> mute |
| False claims (unverified) | Warning -> demote role |

### Escalation Path

1. User reports in `#escalations`
2. @maintainer reviews
3. Decision logged in `#maintainer-sync`
4. Action taken, user notified

---

## Office Hours Schedule

**Frequency**: Weekly (TBD by maintainers)
**Duration**: 1 hour
**Channel**: `Office Hours Voice` + `#office-hours`

**Format**:
1. 10 min: Announcements
2. 30 min: Q&A
3. 20 min: Work unit coordination

**Async Alternative**: Post questions in `#office-hours` anytime, maintainers respond within 48 hours.

---

## Integration with GitHub

### Webhook Notifications

| GitHub Event | Discord Channel |
|--------------|-----------------|
| New Issue (work-unit label) | `#work-units` |
| PR opened | `#submissions` |
| PR merged | `#verified-results` |
| Release published | `#announcements` |

### Bot Commands (Future)

| Command | Action |
|---------|--------|
| `/claim WU-XXXX` | Claim work unit |
| `/status SUB-XXXX` | Check submission status |
| `/leaderboard` | Show top contributors |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Time from join to @contributor | < 24 hours |
| Work units claimed/week | Track trend |
| Submissions/week | Track trend |
| Verification turnaround | < 48 hours |
| Contributor retention (30 day) | > 50% |

---

## Phase Rollout

### Phase 1: Seed (Current Scope)

- Create server with channel structure
- Set up roles and permissions
- Populate #readme and #getting-started
- Manual role assignment
- No bots

### Phase 2: Active

- GitHub webhook integration
- Basic bot for notifications
- First external contributors onboarded
- Office hours established

### Phase 3: Scaled

- Automated role assignment (on smoke test success)
- Full bot integration
- Leaderboard and contribution tracking
- Multiple office hours timezones

---

## Appendix: Server Setup Commands

### Create Server (Discord Admin)

1. Create server: "Science Swarm Hub"
2. Create categories and channels per Channel Map
3. Create roles per Role Definitions
4. Set permissions:
   - @observer: Read all public channels
   - @contributor: Write to contributor channels
   - @verifier: Write to verification channels
   - @maintainer: Admin access

### Role Permissions Matrix

| Role | #readme | #announcements | #introductions | #work-units | #submissions | #verification-queue | #maintainer-sync |
|------|---------|----------------|----------------|-------------|--------------|---------------------|------------------|
| @observer | Read | Read | Write | Read | Read | Read | None |
| @contributor | Read | Read | Write | Write | Write | Read | None |
| @verifier | Read | Read | Write | Write | Write | Write | None |
| @coordinator | Read | Read | Write | Write | Write | Write | None |
| @maintainer | Read | Write | Write | Write | Write | Write | Write |

---

*This document is non-blocking for repo release. Discord is an engagement surface, not a dependency.*

---

**Created**: 2026-03-30
**Author**: 0102
**Slice**: science_swarm_hub_discord_seed_scaffold
