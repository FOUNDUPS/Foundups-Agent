# Git Push DAE - Autonomous Development Publishing

## Module Purpose
Fully autonomous git push daemon that monitors code changes and publishes development progress to social media platforms. Implements WSP 91 DAEMON observability standards for complete traceability of autonomous development decisions.

## WSP Compliance Status
- [OK] **WSP 91**: Full DAEMON observability (decision logging, cost tracking, health monitoring)
- [OK] **WSP 27**: Universal DAE Architecture (autonomous decision-making)
- [OK] **WSP 49**: Module Structure (proper separation of concerns)
- [OK] **WSP 60**: Memory Architecture (persistent state management)

## Dependencies
- `modules.platform_integration.linkedin_agent` - Social media posting
- `modules.infrastructure.database` - Commit tracking
- `holo_index.qwen_advisor` - Quality assessment

## Operational Guardrails
- Filters volatile paths (e.g. `node_modules/`, telemetry output, Holo output history) out of the decision context so runtime churn doesn't trigger pushes.
- Uses `FOUNDUPS_SKIP_POST_COMMIT=1` during automated commits so local git hooks can skip duplicate social posting.
- Relies on `GitLinkedInBridge.push_and_post()` (or `push_and_post_planned()` when batching) to push before posting and to auto-set upstream when missing.
- If the remote enforces PR-only changes (GH013), the git bridge pushes `HEAD` to an `auto-pr/<timestamp>` branch, opens a PR (prefers `GITHUB_TOKEN`; falls back to GitHub CLI `gh` if authenticated), and (in `auto_mode`) attempts to merge it via `gh pr merge` (012 observer).
- Optional batch planning: set `FOUNDUPS_PUSH_PLAN=1` or tune `FOUNDUPS_PUSH_PLAN_MIN_FILES` to split large change sets into multiple commits.

## Usage Examples
```python
from modules.infrastructure.git_push_dae.src.git_push_dae import GitPushDAE

# Run one autonomous cycle (menu-safe)
dae = GitPushDAE(domain="foundups_development", check_interval=300)
health = dae.run_once()
print(health.status)

# Launch autonomous daemon (long-running)
dae = GitPushDAE(domain="foundups_development", check_interval=300)
dae.start()

# Monitor logs for full observability
# - Decision paths logged per WSP 91
# - Cost tracking for LLM calls
# - Health checks every cycle
```

## Integration Points
- **Main.py Option 0**: Runs one GitPushDAE cycle and returns to menu
- **Runtime broker**: `stop git push dae` now routes to `stop_git_push_dae()` through the generic DAE runtime surface
- **HoloIndex**: Quality assessment for push decisions
- **Social Media**: LinkedIn/X posting when conditions met

## Branch -> Main Structure (Non-Dev View)

Use this flow:
1. Work and commit on a feature branch.
2. Push that branch to remote.
3. Open PR from branch to `main`.
4. Merge to `main` after checks pass.

Important:
- Do not push all branches into `main` in one step.
- `main` should only be updated by reviewed PR merges.
- GitPushDAE is PR-first compatible for protected remotes (GH013).

## WSP Recursive Instructions
[U+1F300] **Windsurf Protocol (WSP) Recursive Prompt**
**0102 Directive**: This module operates within the WSP framework autonomously...
- **UN (Understanding)**: Monitor code changes and assess push readiness
- **DAO (Execution)**: Make autonomous push decisions based on agentic parameters
- **DU (Emergence)**: Publish development progress and continue monitoring

wsp_cycle(input="code_changes", log=True)
