---
name: agent_work_batcher
description: Batch completed 0102 agent work for LinkedIn FoundUps page posting
version: 1.0_prototype
author: 0102
created: 2026-03-18
agents: [qwen, claude, openclaw]
primary_agent: qwen
excluded_agents: [gemma]  # Pattern matching only - not for generation
intent_type: ORCHESTRATION
promotion_state: prototype
pattern_fidelity_threshold: 0.85
category: workflow
evals:
  - name: batch_collection
    input: "--scan"
    expected: "lists pending work items from ModLogs"
  - name: post_generation
    input: "--generate"
    expected: "creates formatted LinkedIn post"
  - name: dry_run
    input: "--dry-run"
    expected: "shows post without publishing"
trigger:
  event: session_complete
---
# Agent Work Batcher Skill

## Purpose

Batch completed 0102 agent work and auto-post to LinkedIn FoundUps company page.
Transforms session work summaries into professional LinkedIn updates.

## Workflow

```
Session Activity → Work Items → Batch → Generate Post → LinkedIn
     ↓                ↓           ↓           ↓            ↓
  ModLogs        git commits   dedupe     Qwen/template  linkedin_company_poster
  ROADMAP        skillz work   group      format
  TestModLog                   categorize
```

## Trigger

- **Manual**: `python executor.py --post`
- **Event**: `session_complete` (end of 0102 session)
- **Cadence**: Optional daily summary (`--daily`)

## Commands

```bash
# Scan pending work items
python executor.py --scan

# Generate post content (dry run)
python executor.py --generate

# Post to LinkedIn
python executor.py --post

# Post with custom summary
python executor.py --post --summary "Updated Skills 2.0 compliance"

# Daily summary (all work since yesterday)
python executor.py --daily

# Clear batched items (mark as posted)
python executor.py --clear
```

## Work Item Sources

| Source | Pattern | Example |
|--------|---------|---------|
| ModLog.md | `### YYYY-MM-DD` entries | "Skills 2.0 batch update" |
| TestModLog.md | Test results | "87 skills now 100% compliant" |
| ROADMAP.md | Completed items | "Phase 2 complete" |
| git log | Commit messages | "feat(skillz): add frontmatter" |
| SKILLz.md | New/updated skills | "agentic_news_ticker skill added" |

## Post Format

```
🦞 0102 Agent Update

{category_emoji} **{category}**
{bullet_list_of_work_items}

{optional_stats}

---
0102🦞 #FoundUps #pAVS #0102 #AgentUpdate
```

### Example Post

```
🦞 0102 Agent Update

🛠️ **Skills Infrastructure**
• Updated 87 skills to Skills 2.0 compliance
• Added frontmatter to 17 SKILLz.md files
• Created skills2_batch_updater tool

📊 **Stats**
• Files modified: 87
• Tests passing: 100%
• Categories: 15 workflow, 2 capability-uplift

---
0102🦞 #FoundUps #pAVS #0102 #AgentUpdate
```

## Categories

| Category | Emoji | Description |
|----------|-------|-------------|
| Skills Infrastructure | 🛠️ | SKILLz.md, skill creation |
| Documentation | 📝 | README, INTERFACE, ModLog |
| Testing | 🧪 | Tests, coverage |
| Refactoring | ♻️ | Code cleanup, WSP compliance |
| Features | ✨ | New functionality |
| Bug Fixes | 🐛 | Error corrections |
| Performance | ⚡ | Optimization |
| Security | 🔒 | Security updates |

## Dependencies

- `modules.ai_intelligence.ai_overseer.skillz.linkedin_company_poster` - Posting
- `modules.platform_integration.linkedin_agent.src.git_linkedin_bridge` - Git history
- `modules.platform_integration.linkedin_agent.src.automation.post_scheduler` - Scheduling

## Configuration

```yaml
# Environment variables
AGENT_BATCHER_AUTO_POST: "false"  # Require manual approval by default
AGENT_BATCHER_MIN_ITEMS: 3        # Min items before batching
AGENT_BATCHER_CATEGORIES: "skills,docs,testing"  # Filter categories
```

## State Storage

```
modules/ai_intelligence/ai_overseer/skillz/agent_work_batcher/
├── state/
│   ├── pending_items.jsonl     # Unbatched work items
│   ├── posted_batches.jsonl    # History of posted batches
│   └── last_scan.json          # Last scan timestamp
```

## WRE Connection

```yaml
trigger:
  type: event
  source: session_complete OR /post-work
  gate: AGENT_BATCHER_ENABLED=1

events_emitted:
  - work_item_collected: {source, category, description}
  - batch_created: {item_count, categories}
  - post_published: {linkedin_url, item_count}

control_signals:
  - skip_batch.signal: Skip current batch
  - force_post.signal: Post immediately
```

## WSP Compliance

- WSP 27: DAE Architecture (collector → batcher → poster)
- WSP 48: Social media posting standards
- WSP 77: Agent coordination (Qwen for generation)
- WSP 91: Observability (all events logged)
- WSP 97: CoT/CoR (retrieve ModLogs before generating)
