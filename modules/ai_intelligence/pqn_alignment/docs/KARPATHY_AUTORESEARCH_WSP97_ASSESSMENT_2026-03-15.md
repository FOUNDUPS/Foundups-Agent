# Karpathy AutoResearch WSP 97 Assessment

Date: 2026-03-15  
Author: 0102  
Scope: OpenClaw, PQN research, MCP governance, runtime launch posture

## Decision

`karpathy/autoresearch` should be treated as an **isolated external research worker**, not as a direct FoundUps runtime or direct monorepo mutation engine.

Recommended posture:
- `pilot_in_isolation`
- execution plane: `external_worker`
- control plane: `OpenClaw / 0102`
- launch surface: `DAE Launch Broker`
- artifact return path: `HoloIndex + WRE memory + docs`

## Upstream Facts

From the upstream repo and docs:

1. The README presents it as a simple autonomous ML research loop with commands like:
   - `uv pip install -r requirements.txt`
   - `python run.py --config nanoGPT`
   Source: `karpathy/autoresearch` README on GitHub, accessed 2026-03-15.

2. The repo root is intentionally compact and centered around:
   - `run.py`
   - `score.py`
   - `program.md`
   - config files such as `nanoGPT.py`, `modded-nanogpt.py`, `llamacat.py`
   Source: GitHub repo root page, accessed 2026-03-15.

3. `program.md` instructs the agent to behave like a machine learning research engineer and to iterate through:
   - hypothesis
   - code modification
   - experiment run
   - result write-up
   - commit/push style loop
   It also writes checkpoints and summaries into a research directory.
   Source: `program.md` on GitHub, accessed 2026-03-15.

## What It Is Good For

AutoResearch is a candidate runtime for:
- bounded experiment search
- hyperparameter or architecture iteration
- ablation loops
- artifact generation in a self-contained research repo

In FoundUps terms, it aligns with:
- PQN experiment scaffolding
- CMST detector parameter search
- detector-side research artifact generation
- isolated model/protocol experimentation

## What It Is Not Good For

It is not a safe direct fit for:
- `main.py` auto-start
- direct FoundUps monorepo mutation
- unrestricted Claw execution
- immediate MCP-first integration
- direct push to protected branches

Its upstream operating model assumes a narrower research surface than the FoundUps production monorepo.

## WSP 97 Resolution

### Correct Plane

- `012` sets research direction
- `0102 / OpenClaw` decides when a research session should run
- `AutoResearch` executes as a subordinate worker in isolation
- `WRE` remembers artifacts and scores outcomes
- `MCP` is optional later, after isolation and wrapper stability

### Incorrect Plane

- `AutoResearch` as a top-level principal
- `AutoResearch` writing directly into FoundUps production modules
- `AutoResearch` launched automatically at every system boot

## WSP 15 Scoring

- Complexity: `3`
- Importance: `4`
- Deferability: `3`
- Impact: `4`
- Total: `14/20`

Interpretation:
- important enough for a pilot
- not urgent enough to bypass isolation and governance

## Risks

1. Autonomous git mutation risk
   - Upstream loop assumes direct repo iteration.

2. Blast-radius mismatch
   - FoundUps is a multi-domain system, not a single-purpose ML repo.

3. License uncertainty
   - I did not confirm a license file from the repo pages inspected on 2026-03-15.
   - This must be resolved before any code reuse or redistribution assumptions.

4. Resource mismatch
   - The tool is oriented around GPU-backed research iteration.
   - That is different from normal OpenClaw conversational/runtime control.

5. Governance mismatch
   - Without a wrapper, it can bypass WSP logging, broker launch, and DAEmon observability.

## Recommended Integration Path

### Phase 0: Diligence

- verify license explicitly
- pin exact upstream commit/hash
- define pilot scope

### Phase 1: Isolation Pilot

Run it only in:
- disposable clone or dedicated worktree
- container or isolated machine
- no production secrets
- no direct write access to `main`

### Phase 2: Wrapper

If the pilot is useful:
- add a thin FoundUps wrapper DAE or broker launch spec
- accept input as bounded research task
- return only artifacts:
  - metrics
  - summaries
  - patches in quarantined branch
  - experiment logs

### Phase 3: Optional MCP Surface

Only after wrapper stability:
- expose read/status/report surfaces through MCP
- do not expose unrestricted mutation controls first

## Recommendation To 012 / 0102

Adopt `karpathy/autoresearch` only as:
- a sandboxed PQN research accelerator
- broker-launched
- artifact-returning
- non-authoritative

Do not integrate it as:
- a Claw replacement
- a default startup DAE
- a direct production coding lane

## First Safe Step

Create a documentation-backed pilot plan:
- target one bounded PQN experiment family
- define artifact outputs
- define isolation boundary
- define rollback and deletion policy

That is the correct WSP 97 next move.
