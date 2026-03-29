# WSP 15: Module Prioritization Scoring (MPS) System
- **Status:** Active
- **Purpose:** To provide a consistent, objective methodology for evaluating and ranking modules and approved work items to guide development priorities.
- **Trigger:** When planning a new development cycle; when a new module is proposed; when approved work items need ordering across queue, backlog, or recall surfaces.
- **Input:** A module, work item, or scored bundle to be evaluated, including internally-proposed modules, externally-triaged tasks, user-submitted goals, and domain-specific prioritization variants explicitly defined by other WSPs.
- **Output:** A priority score (P0-P4) recorded in the appropriate planning artifact for the domain, such as `modules_to_score.yaml`, queue/backlog artifacts, or a variant-specific output contract.
- **Responsible Agent(s):** ScoringAgent

The **Module Prioritization Scoring (MPS) System** provides a consistent, objective methodology for evaluating and ranking modules. The same 4-dimension scaffold may also be applied to approved non-module work items through explicit domain variants such as memory prioritization. This is augmented by the **LLME Semantic Triplet Rating** (see `WSP 11`), which provides a qualitative layer for understanding a module's state, local impact, and systemic importance. This combined approach enables the development team to:

-   Focus efforts on the highest-value modules first.
-   Make informed decisions about resource allocation.
-   Create a defensible, transparent roadmap.
-   Balance immediate needs with long-term architectural goals.
-   Communicate priorities clearly to all stakeholders.
-   Align development effort with desired semantic states of modules (as defined by LLME).

## 1.5. External Input Integration

The MPS System processes both internal proposals and external feedback sources to ensure comprehensive priority assessment:

### 1.5.1 Input Source Types

**Internal Sources:**
- Module proposals from 0102 pArtifacts and development agents
- WSP framework enhancement requirements
- Technical debt and refactoring needs
- Architectural improvement proposals

**External Sources:**
- **User-Submitted Goals**: High-priority objectives from 012 Rider and external stakeholders
- **System Alert Responses**: Modules required to address automated monitoring alerts
- **Strategic Planning Input**: Modules derived from external roadmap reviews and planning sessions
- **Feedback Channel Input**: Tasks generated from designated feedback mechanisms (e.g., `feedback.md`, API endpoints)
- **Compliance Requirements**: Modules needed to meet external regulatory or platform changes

### 1.5.2 External Input Processing Workflow

1. **Input Standardization**: TriageAgent (WSP 54) converts external feedback into WSP-compliant task format
2. **Impact Assessment**: Initial evaluation of external requirements and system implications
3. **MPS Application**: External tasks scored using standard 4-question methodology (Complexity, Importance, Deferability, Impact)
4. **Priority Integration**: External tasks integrated into development roadmap alongside internal proposals
5. **Recursive Feedback**: Results of external input processing feed back into WSP 48 self-improvement cycles

## 2. Scoring Criteria (MPS Dimensions)

Each module receives a score from 1 (lowest) to 5 (highest) in four dimensions. The LLME score provides qualitative context for these dimensions.

### A. Complexity (1-5)

-   **Definition**: How difficult is the module to implement or refactor correctly?
-   **LLME Influence**: A module's 'Present State' (Digit A) can influence this. A dormant module (`A=0`) might be more complex to activate.

| Score | Complexity Level | Description                                                      |
| ----- | ---------------- | ---------------------------------------------------------------- |
| 1     | Trivial          | Simple code, few dependencies, well-understood patterns          |
| 2     | Low              | Straightforward implementation with minimal challenges           |
| 3     | Moderate         | Requires careful design, some complex logic or integration       |
| 4     | High             | Significant challenges, complex algorithms or interactions       |
| 5     | Very High        | Extremely complex, cutting-edge techniques, major integration work |

### B. Importance (1-5)

-   **Definition**: How essential is this module to the system's core functions?
-   **LLME Influence**: 'Local Impact' (Digit B) and 'Systemic Importance' (Digit C) directly inform this. A module with `B=2` or `C=2` is inherently important.

| Score | Importance Level | Description                                                      |
| ----- | ---------------- | ---------------------------------------------------------------- |
| 1     | Optional         | Nice-to-have, system works without it                            |
| 2     | Helpful          | Enhances system but not required for core operations             |
| 3     | Important        | System functions suboptimally without it                         |
| 4     | Critical         | System faces significant limitations without it                  |
| 5     | Essential        | System cannot function in a meaningful way without it            |

### C. Deferability (1-5)

-   **Definition**: How urgent is the development of this module? (A lower score means it is *more* deferrable).
-   **LLME Influence**: An active module (`A=1` or `A=2`) may be less deferrable than a dormant one (`A=0`), unless activating it is the urgent task.

| Score | Deferability Level   | Description                                                      |
| ----- | -------------------- | ---------------------------------------------------------------- |
| 1     | Highly Deferrable    | Can be postponed indefinitely with minimal impact                |
| 2     | Deferrable           | Can be delayed for several release cycles                        |
| 3     | Moderate             | Should be implemented within next 1-2 releases                   |
| 4     | Difficult to Defer   | Needed in the next release to maintain progress                  |
| 5     | Cannot Defer         | Blocking further progress; must be implemented immediately       |

### D. Impact (1-5)

-   **Definition**: How much value will this module deliver to users or the system?
-   **LLME Influence**: 'Local Impact' (Digit B) and 'Systemic Importance' (Digit C) directly inform this. An 'emergent' state (`A=2`) could also signify high impact.

| Score | Impact Level     | Description                                                      |
| ----- | ---------------- | ---------------------------------------------------------------- |
| 1     | Minimal          | Little noticeable improvement to users or system                 |
| 2     | Minor            | Some value, but limited in scope or effect                       |
| 3     | Moderate         | Clear benefits visible to users or significant internal improvements |
| 4     | Major            | Substantial value enhancement, highly visible improvements       |
| 5     | Transformative   | Game-changing capability that redefines system value             |

## 3. Scoring Process

1.  **Assess MPS**: For each module or approved work item, assign scores (1-5) for Complexity, Importance, Deferability, and Impact.
2.  **Assign LLME**: Assign or review the module's current and target LLME score (e.g., "112") when the scored object is a module and LLME is applicable.
3.  **Calculate Score**: Sum the four MPS dimensions: `MPS Score = Complexity + Importance + Deferability + Impact`.
4.  **Document**: Maintain scores and rationale in the appropriate planning artifact for the domain:
    - `modules_to_score.yaml` for module planning
    - queue/backlog artifacts for scored work items
    - variant-specific output contracts for explicit MPS derivatives such as `MPS-M`

## 4. Priority Classification

The total MPS score (range: 4-20) and the LLME score determine priority.

| MPS Score Range | Priority | Action Guideline & LLME Considerations                                                                     |
| --------------- | -------- | ---------------------------------------------------------------------------------------------------------- |
| 16-20           | P0       | **Critical**. Work begins immediately. Modules with LLME `X22` or target `X22` are paramount.                |
| 13-15           | P1       | **High**. Important for near-term roadmap. Use LLME to sequence P1s (e.g., prioritize a `011` -> `122` evolution). |
| 10-12           | P2       | **Medium**. Valuable but not urgent. LLME can help differentiate P2s.                                      |
| 7-9             | P3       | **Low**. Can be deferred. Typically low current and target LLME.                                           |
| 4-6             | P4       | **Backlog**. Reconsidered in future planning. Candidates for deprecation if LLME remains `000`.            |

## 5. HoloDAE Issue Evaluation Adaptation (0102 Implementation)

### 5.1 MPS-Based Issue Evaluation Algorithm
**Implementation Location**: `O:\Foundups-Agent\holo_index\qwen_advisor\issue_mps_evaluator.py`
**Agent**: 0102 (Arbitrator over Qwen findings)
**Created**: 2025-09-27

The MPS system has been adapted for automated issue evaluation in HoloDAE, where:
- **Qwen (HoloDAE)** finds issues and suggests complexity ratings
- **0102** uses MPS algorithm to arbitrate and decide actions autonomously
- **012** observes but doesn't approve - fully autonomous system

### 5.2 Issue Type MPS Mappings

| Issue Type | Complexity | Importance | Deferability | Impact | Total MPS | Action |
|------------|------------|------------|--------------|--------|-----------|--------|
| VIBECODE | 2 (Low) | 4 (Critical) | 5 (Cannot defer) | 4 (Major) | 15 (P1) | Fix in batch |
| WSP_VIOLATION | 1 (Trivial) | 4 (Critical) | 4 (Difficult) | 3 (Moderate) | 12 (P2) | Schedule |
| DEAD_CODE | 1 (Trivial) | 2 (Helpful) | 2 (Deferrable) | 2 (Minor) | 7 (P3) | Can defer |
| DUPLICATE | 3 (Moderate) | 3 (Important) | 3 (Moderate) | 3 (Moderate) | 12 (P2) | Schedule |
| ARCHITECTURE | 4 (High) | 5 (Essential) | 3 (Moderate) | 5 (Transform) | 17 (P0) | Fix now |
| DEPENDENCY | 3 (Moderate) | 4 (Critical) | 4 (Difficult) | 4 (Major) | 15 (P1) | Fix in batch |

### 5.3 0102 Arbitration Logic

The implementation allows 0102 to autonomously decide based on MPS scores:
- **P0 (16-20)**: Fix immediately - critical issues that block progress
- **P1 (13-15)**: Batch fixes - high priority within current session
- **P2 (10-12)**: Schedule for sprint - medium priority planned work
- **P3 (7-9)**: Add to backlog - can defer with minimal impact
- **P4 (4-6)**: Reconsider later - very low priority

### 5.4 Integration with HoloDAE

**Usage in autonomous_holodae.py**:
```python
from holo_index.qwen_advisor.issue_mps_evaluator import IssueMPSEvaluator

evaluator = IssueMPSEvaluator()
evaluation = evaluator.evaluate_issue(issue_type, description, confidence)

# 0102 decides based on evaluation.priority
if evaluation.priority == IssueSeverity.P0_CRITICAL:
    # Fix immediately
elif evaluation.priority == IssueSeverity.P1_HIGH:
    # Add to batch queue
```

### 5.5 Future Improvements for 0102

Location for enhancement: `holo_index\qwen_advisor\issue_mps_evaluator.py`

Potential improvements:
1. **Context-aware scoring**: Adjust scores based on current module being worked on
2. **Learning from outcomes**: Track fix success rates to refine scores
3. **Dynamic thresholds**: Adjust P0-P4 boundaries based on workload
4. **Integration with AgentDB**: Store evaluation history for pattern learning
5. **Confidence calibration**: Better mapping of Qwen confidence to score adjustments 
6. **Reusable Template Library (`skills.md`)**: Keep platform-agnostic prompt templates so Qwen/Grok/Claude/UI‑TARS can draft posts or docs consistently before we run MPS scoring.

## 6. Memory Prioritization Scoring (MPS-M) (WSP 60)

MPS-M adapts MPS for memory recall. It scores memory cards (WSP/README/ModLog/INTERFACE/generated) so HoloIndex and AI_overseer can surface the right memory first.

### 6.1 Dimensions (Memory)

-   **Complexity -> Reconstruction Cost**: How hard it is to re-derive.
-   **Importance -> Correctness/Safety Impact**: Consequence if missing or wrong.
-   **Deferability -> Time Sensitivity**: How quickly it goes stale.
-   **Impact -> Decision Leverage**: How strongly it drives "what to do next."

`MPS-M = C + I + D + Im` (range 4-20). Map P0-P4 the same as WSP 15.

### 6.2 Trust Weighting

Apply trust weighting to the MPS-M score before ordering:
-   WSP > INTERFACE/README > ModLog > generated memory card

`effective_score = MPS-M * trust_weight` (see WSP 60).

### 6.3 Usage

-   Run MPS for modules when planning changes.
-   Run MPS-M for memory bundles when responding to queries (HoloIndex output contract).
-   Record scores in the owning artifact surface for that domain rather than forcing every use case through `modules_to_score.yaml`.
