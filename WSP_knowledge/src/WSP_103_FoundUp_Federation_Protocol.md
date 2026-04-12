# WSP 103: FoundUp Federation Protocol

**Status**: ACTIVE
**Version**: 1.0
**Date**: 2026-03-15
**Author**: 0102 (012 directive)
**Dependencies**: WSP 96 (MCP Governance), WSP 98 (Mesh Architecture), WSP 27 (DAE Architecture), WSP 104 (Route Namespace and Tenant Isolation)

---

## Prerequisite: WSP 104 Namespace Guardrails

**Before a federated FoundUp is bound to pAVS infrastructure**, it must satisfy the WSP 104 namespace guardrails:

- unique `foundup_id`
- unique `routing_prefix` = `/f/{foundup_id}`
- unique `data_namespace` = `idb_{foundup_id}`
- no root-level tenant route claims

A federated FoundUp that fails namespace validation must not receive pAVS MCP access or be included in the federation registry.

---

## Executive Summary

WSP 103 establishes the **FoundUp Federation** pattern where FoundUps are **independent repositories** that connect to pAVS infrastructure via MCP. This replaces the monorepo consolidation model with a federated architecture enabling:

- **Independent Development**: External contributors work on FoundUps without the main codebase
- **Infrastructure-as-a-Service**: pAVS provides CABR, AI, FAM, Pattern Memory via MCP
- **Opt-in Connection**: FoundUps work standalone but gain powers with pAVS MCP

**Paradigm Shift**: FoundUps are NOT subdirectories. They are autonomous entities that CONNECT to pAVS.

---

## Architecture Model

### Before (Monorepo Consolidation)

```
Foundups-Agent/
  modules/foundups/
    gotjunk/          # Inside main repo
    move2japan/       # Inside main repo
    autopost/         # Inside main repo

Problem: External devs need full codebase
Problem: Tight coupling to infrastructure
Problem: Not truly autonomous
```

### After (Federation via MCP)

```
GitHub Dual-Remote Pattern (same as Foundups-Agent):

FOUNDUPS Org (origin - primary):        Foundup Personal (backup - mirror):
  FOUNDUPS/AutoPost (PRIVATE)      <-->   Foundup/AutoPost (PRIVATE)
  FOUNDUPS/GotJunk (PRIVATE)       <-->   Foundup/GotJunk (PRIVATE)
  FOUNDUPS/Move2Japan (PRIVATE)    <-->   Foundup/Move2Japan (PRIVATE)
  FOUNDUPS/PQNPortal (PRIVATE)     <-->   Foundup/PQNPortal (PRIVATE)

  FOUNDUPS/Foundups-Agent (PUBLIC)        (infrastructure repo)
    modules/infrastructure/pavs_mcp/      # MCP Server
    modules/foundups/agent_market/        # FAM (core)
    modules/foundups/simulator/           # Dev tools

Connection:
  [FoundUp Repo] --MCP--> [pAVS MCP Server] --> [WRE Infrastructure]
```

**Dual-Remote Requirement**: All federated FoundUps MUST follow the dual-remote pattern:
- **origin**: FOUNDUPS/RepoName (org repo - primary, contributor-friendly)
- **backup**: Foundup/RepoName (personal repo - disaster recovery)
- **Sync**: `git push origin && git push backup` after commits

---

## pAVS MCP Server Architecture

**Location**: `modules/infrastructure/pavs_mcp/`

### Exposed Tools

```python
# modules/infrastructure/pavs_mcp/src/pavs_mcp_server.py

from mcp.server import Server
from mcp.types import Tool

server = Server("pavs-infrastructure")

@server.tool()
async def cabr_validate(content: str, context: dict) -> dict:
    """
    V1/V2/V3 validation gate for any content.

    Args:
        content: Text/media content to validate
        context: Platform, audience, FoundUp ID

    Returns:
        score: 0.0-1.0 CABR score
        passed: Boolean gate result
        feedback: Improvement suggestions
    """
    from modules.foundups.agent_market.src.cabr_hooks import CABREngine
    engine = CABREngine()
    return await engine.validate(content, context)

@server.tool()
async def gemma_classify(text: str, categories: list[str]) -> dict:
    """
    Binary/multi-class classification via Gemma.

    Args:
        text: Content to classify
        categories: List of category labels

    Returns:
        classification: Best matching category
        confidence: 0.0-1.0 confidence score
        all_scores: Dict of category -> score
    """
    from holo_index.gemma_engine import classify
    return await classify(text, categories)

@server.tool()
async def qwen_plan(objective: str, constraints: dict) -> dict:
    """
    Strategic planning via Qwen.

    Args:
        objective: What to achieve
        constraints: Time, platform, audience limits

    Returns:
        plan: Step-by-step execution plan
        reasoning: Why this approach
        alternatives: Other options considered
    """
    from holo_index.qwen_advisor import plan_strategy
    return await plan_strategy(objective, constraints)

@server.tool()
async def fam_emit(foundup_id: str, event_type: str, payload: dict) -> dict:
    """
    Emit event to FAM DAEmon for tracking.

    Args:
        foundup_id: Which FoundUp is emitting
        event_type: Event category (post_created, task_completed, etc.)
        payload: Event-specific data

    Returns:
        event_id: Unique event identifier
        timestamp: When recorded
    """
    from modules.foundups.agent_market.src.fam_daemon import get_fam_daemon
    daemon = get_fam_daemon()
    return await daemon.emit(foundup_id, event_type, payload)

@server.tool()
async def pattern_recall(skill: str, min_fidelity: float = 0.7) -> list[dict]:
    """
    Recall successful patterns from memory.

    Args:
        skill: Skill/action type to recall
        min_fidelity: Minimum success threshold

    Returns:
        List of successful patterns with context
    """
    from modules.infrastructure.wre_core.src.pattern_memory import get_pattern_memory
    memory = get_pattern_memory()
    return memory.recall_successful_patterns(skill, min_fidelity)

@server.tool()
async def pattern_store(skill: str, outcome: dict) -> dict:
    """
    Store execution outcome for learning.

    Args:
        skill: Skill that was executed
        outcome: Success/failure + context

    Returns:
        pattern_id: Stored pattern identifier
    """
    from modules.infrastructure.wre_core.src.pattern_memory import get_pattern_memory
    memory = get_pattern_memory()
    return memory.store_outcome(skill, outcome)

@server.tool()
async def holo_search(query: str, domain: str = None) -> list[dict]:
    """
    Semantic search via HoloIndex.

    Args:
        query: Natural language query
        domain: Optional domain filter

    Returns:
        List of relevant code/doc matches
    """
    from holo_index import search
    return await search(query, domain=domain)
```

### Authentication

```python
# FoundUp registration and API key management
@server.tool()
async def foundup_register(
    foundup_id: str,
    repo_url: str,
    owner_pubkey: str
) -> dict:
    """
    Register a FoundUp for pAVS access.

    Args:
        foundup_id: Unique FoundUp identifier
        repo_url: GitHub repo URL
        owner_pubkey: Owner's Ed25519 public key

    Returns:
        api_key: Encrypted API key for MCP access
        endpoint: MCP server endpoint URL
    """
    # Generate scoped API key
    # Store in FoundUp registry
    # Return connection credentials
```

---

## FoundUp SDK

### TypeScript SDK (for PWA FoundUps)

**NPM Package**: `@foundups/pavs-sdk`

```typescript
// @foundups/pavs-sdk/index.ts

export class PAVSClient {
  private endpoint: string;
  private apiKey: string;

  constructor(config: { endpoint: string; apiKey: string }) {
    this.endpoint = config.endpoint;
    this.apiKey = config.apiKey;
  }

  async cabrValidate(content: string, context?: object): Promise<CABRResult> {
    return this.call('cabr_validate', { content, context });
  }

  async gemmaClassify(text: string, categories: string[]): Promise<Classification> {
    return this.call('gemma_classify', { text, categories });
  }

  async qwenPlan(objective: string, constraints?: object): Promise<Plan> {
    return this.call('qwen_plan', { objective, constraints });
  }

  async famEmit(eventType: string, payload: object): Promise<EventResult> {
    return this.call('fam_emit', {
      foundup_id: this.foundupId,
      event_type: eventType,
      payload
    });
  }

  async patternRecall(skill: string, minFidelity = 0.7): Promise<Pattern[]> {
    return this.call('pattern_recall', { skill, min_fidelity: minFidelity });
  }

  private async call(tool: string, args: object): Promise<any> {
    const response = await fetch(`${this.endpoint}/call`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ tool, arguments: args })
    });
    return response.json();
  }
}
```

### Python SDK (for backend FoundUps)

**PyPI Package**: `foundups-pavs`

```python
# foundups_pavs/client.py

class PAVSClient:
    def __init__(self, endpoint: str, api_key: str, foundup_id: str):
        self.endpoint = endpoint
        self.api_key = api_key
        self.foundup_id = foundup_id

    async def cabr_validate(self, content: str, context: dict = None) -> dict:
        return await self._call('cabr_validate', content=content, context=context)

    async def gemma_classify(self, text: str, categories: list[str]) -> dict:
        return await self._call('gemma_classify', text=text, categories=categories)

    async def qwen_plan(self, objective: str, constraints: dict = None) -> dict:
        return await self._call('qwen_plan', objective=objective, constraints=constraints)

    async def fam_emit(self, event_type: str, payload: dict) -> dict:
        return await self._call('fam_emit',
            foundup_id=self.foundup_id,
            event_type=event_type,
            payload=payload
        )

    async def pattern_recall(self, skill: str, min_fidelity: float = 0.7) -> list:
        return await self._call('pattern_recall', skill=skill, min_fidelity=min_fidelity)
```

---

## FoundUp Integration Pattern

### AutoPost Example

```typescript
// In Foundup/AutoPost repo
// src/services/postOrchestrator.ts

import { PAVSClient } from '@foundups/pavs-sdk';

const pavs = new PAVSClient({
  endpoint: process.env.PAVS_ENDPOINT,
  apiKey: process.env.PAVS_API_KEY
});

export const postOrchestrator = {
  async processNewRecording(videoBlob: Blob, settings: UserSettings) {
    // 1. Transcription (local or Gemini)
    const transcript = await ai.transcribe(videoBlob);

    // 2. CABR Validation (via pAVS MCP)
    const validation = await pavs.cabrValidate(transcript, {
      platform: settings.targetPlatform,
      audience: settings.audience,
      foundup: 'autopost'
    });

    if (!validation.passed) {
      return {
        blocked: true,
        reason: validation.feedback,
        score: validation.score
      };
    }

    // 3. Strategic Planning (via pAVS MCP)
    const plan = await pavs.qwenPlan(
      'maximize_engagement',
      {
        content: transcript,
        platforms: settings.targets,
        timing: 'optimal'
      }
    );

    // 4. Generate Caption with AI optimization
    const { caption, hashtags } = await ai.generateCaption({
      transcript,
      style: settings.captionStyle,
      plan: plan  // Use Qwen's strategic guidance
    });

    // 5. Track in FAM (via pAVS MCP)
    await pavs.famEmit('post_created', {
      transcript,
      caption,
      platform: plan.recommendedPlatform,
      scheduledTime: plan.optimalTime
    });

    // 6. Store Pattern for Learning (via pAVS MCP)
    await pavs.patternStore('social_post', {
      input: { transcript, platform: settings.targetPlatform },
      output: { caption, hashtags },
      context: { cabrScore: validation.score }
    });

    return { caption, hashtags, schedule: plan.optimalTime };
  }
};
```

---

## Spin-Out Procedure

### For Existing FoundUps in Monorepo

1. **Create Independent Repo**
   ```bash
   gh repo create Foundup/GotJunk --private
   ```

2. **Extract to New Repo**
   ```bash
   # From modules/foundups/gotjunk
   git filter-branch --subdirectory-filter modules/foundups/gotjunk
   git remote set-url origin git@github.com:Foundup/GotJunk.git
   git push -u origin main
   ```

3. **Add pAVS SDK**
   ```bash
   npm install @foundups/pavs-sdk
   # or
   pip install foundups-pavs
   ```

4. **Configure Connection**
   ```bash
   # .env
   PAVS_ENDPOINT=wss://pavs.foundups.com/mcp
   PAVS_API_KEY=fp_xxxxxxxxxxxx
   ```

5. **Update GotJunk module.json**
   ```json
   {
     "federation": {
       "mode": "independent",
       "pavs_connected": true,
       "repo": "Foundup/GotJunk"
     }
   }
   ```

6. **Leave Stub in Monorepo**
   ```
   modules/foundups/gotjunk/
     README.md           # Points to Foundup/GotJunk
     MIGRATED.md         # Migration notes
   ```

---

## Spin-Out Candidates

| Module | Status | Priority | Notes |
|--------|--------|----------|-------|
| **gotjunk** | In monorepo | P1 | PWA, self-contained |
| **move2japan** | In monorepo | P1 | Vertical FoundUp |
| **social_twin** | In monorepo | P2 | Needs more infra deps |
| **pqn_portal** | In monorepo | P2 | Research focus |
| **AutoPost** | Already separate | DONE | Foundup/AutoPost |

---

## WSP Compliance Matrix

| Requirement | Implementation |
|-------------|----------------|
| **WSP 96 MCP Governance** | pAVS MCP Server follows MCP consensus |
| **WSP 98 Mesh Architecture** | Federation complements mesh (different layer) |
| **WSP 27 DAE Architecture** | FoundUps are DAEs connecting via MCP |
| **WSP 71 Security** | API keys, encryption, auth |
| **WSP 50 Pre-Action** | FoundUps verify connection before ops |

---

## Benefits

### For External Contributors
- Work on FoundUp without main codebase
- Clear SDK interface
- Faster iteration cycles

### For pAVS Infrastructure
- Centralized improvements benefit all FoundUps
- Observability across federation
- Pattern learning aggregated

### For FoundUp Autonomy
- Truly independent deployment
- Opt-in infrastructure (not mandatory)
- Blue ocean - each FoundUp can evolve independently

---

## Autonomous Access Gating

Federated FoundUp repos are **PRIVATE** with autonomous access based on pAVS membership tier.

### Access Tiers

| Tier | Criteria | Access Level |
|------|----------|--------------|
| **Angel** | $195/mo subscription | All pre-OPO FoundUps |
| **Du Staker** | UPS staked in specific F_i | That FoundUp's repo |
| **Contributor** | PRs merged / CABR verified | Repos they contributed to |
| **Member** | Free tier registered | Public repos only |

### Autonomous Access Flow

```
User subscribes (Angel $195/mo)
      │
      v
pAVS records github_username
      │
      v
FAM event: "angel_subscribed"
      │
      v
Access DAE triggers
      │
      v
GitHub API: teams.add_member(user, "angels")
      │
      v
User receives GitHub invite to PRIVATE repos
```

### Access DAE Implementation

```python
class FoundUpAccessDAE:
    """
    Autonomous access management for federated FoundUps.
    Triggered by FAM events, grants GitHub repo access.
    """

    async def on_angel_subscribed(self, event: FAMEvent):
        """Grant Angel access to all pre-OPO FoundUps."""
        github_username = event.payload["github_username"]

        for repo in self.get_pre_opo_foundups():
            await self.github.add_collaborator(
                repo=repo,
                username=github_username,
                permission="pull"  # Read access
            )

        await self.fam_emit("access_granted", {
            "user": github_username,
            "tier": "angel",
            "repos": self.get_pre_opo_foundups()
        })

    async def on_du_staked(self, event: FAMEvent):
        """Grant Du staker access to their FoundUp repo."""
        github_username = event.payload["github_username"]
        foundup_id = event.payload["foundup_id"]

        await self.github.add_collaborator(
            repo=f"FOUNDUPS/{foundup_id}",
            username=github_username,
            permission="pull"
        )

    async def on_subscription_cancelled(self, event: FAMEvent):
        """Revoke access when subscription ends."""
        github_username = event.payload["github_username"]
        # Remove from repos (except those they Du stake in)
        for repo in self.get_user_angel_repos(github_username):
            if not self.user_has_stake(github_username, repo):
                await self.github.remove_collaborator(repo, github_username)
```

### pAVS MCP Tool: request_repo_access

```python
@server.tool()
async def request_repo_access(
    github_username: str,
    foundup_id: str,
    access_proof: dict  # Subscription ID, stake proof, etc.
) -> dict:
    """
    Request access to a FoundUp repo.
    Verifies eligibility and triggers GitHub invite.
    """
    # Verify proof
    if not await verify_access_proof(access_proof):
        return {"granted": False, "reason": "Invalid proof"}

    # Check tier eligibility
    tier = await get_user_tier(access_proof)
    allowed_repos = get_tier_repos(tier)

    if foundup_id not in allowed_repos:
        return {"granted": False, "reason": f"Tier '{tier}' cannot access '{foundup_id}'"}

    # Grant access via GitHub API
    await github.add_collaborator(
        repo=f"FOUNDUPS/{foundup_id}",
        username=github_username,
        permission="pull"
    )

    return {"granted": True, "invite_sent": True}
```

### Visibility Lifecycle

```
Pre-OPO (F0_DAE):   PRIVATE → Access via Angel/Du stake
Post-OPO (F1_OPO+): Option to go PUBLIC for contributor network effect
```

**Transition**: When FoundUp does OPO, owner can flip visibility to PUBLIC.

---

## Anti-Patterns

**NEVER:**
- Consolidate FoundUps into monorepo (old model)
- Expose raw infrastructure APIs (use MCP tools)
- Require FoundUps to import main codebase modules
- Store FoundUp secrets in main repo

**ALWAYS:**
- Keep FoundUps in separate repos
- Connect via pAVS MCP SDK
- Document federation status in module.json
- Leave migration stub when spinning out

---

**Protocol Status**: ACTIVE - Mandatory for new FoundUps starting 2026-03-15
**First Implementation**: Foundup/AutoPost + pAVS MCP Server
