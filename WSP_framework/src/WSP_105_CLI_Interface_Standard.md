# WSP 105: CLI Interface Standard (Typeball Architecture)

**Status**: ACTIVE
**Version**: 2.0 (Digital Twin Mappings)
**Date**: 2026-02-28
**Author**: 0102 (CLI Standardization)

---

## Executive Summary

WSP 103 establishes standards for command-line interfaces (CLIs) across the Foundups ecosystem. It explicitly defines the "Typeball Architecture," converting OpenClaw operations and UI-TARS vision predictions into standardized, per-site CLIs for Digital Twin execution on behalf of 012.

**Key Principle**: Every site capability must be compiled into deterministic CLI endpoints (a "Typeball"), treating the DOM purely as an execution substrate.

---

## Scope

This WSP applies to:

- Digital Twin OpenClaw/IronClaw Site CLIs ("Typeballs")
- Module launch scripts (`scripts/launch.py`)
- Any Python script invoked by agents for orchestration operations

**Related WSPs**:

- WSP 77: Agent Coordination (task dispatch logic)
- WSP 91: DAEMON Observability (telemetry output)
- WSP 73: 012 Digital Twin Architecture

---

## Typeball CLI Architecture (Per-Site Capability Map)

Every target external site gets its own generic CLI build mapping, referred to conceptually as a "Typeball." The typeball acts as a compiler translating 012's intentions into programmatic DOM steps or Vision-based (UI-TARS) interactions.

### The Linguistic Metaphor

- **Glyphs** = API/CLI commands (atomic capabilities like clicking, typing, extracting).
- **Kerning** = Preconditions (authentication state, roles, visible panels).
- **Word** = Action chain / Multi-step sequences (e.g., login + navigate).
- **Sentence** = Agent task plan (goal → subgoals → commands).
- **Typewriter** = The executor engine (Playwright / Selenium / UI-TARS fallback) handling retries, delays, and telemetry.

### The Two-Stage CLI Generation Pipeline

The Digital Twin does NOT vibe-navigate sites repeatedly. Sites are mapped once into structured limits, then executed via strict policies.

#### Stage 1: UI → Capability Map (UITars/DOM)

1. **Crawl**: Enter start URL + authenticated session.
2. **Snapshot**: Capture DOM snapshots, visible text, forms, links, SVGs, modals.
3. **Normalize**: Map selectors (stable data-testids, unique IDs, relative anchor chains).
4. **Action Detection**: Detect capabilities (`click`, `upload`, `submit`, `filter`, `download`).
5. **Output**: Generates `<site_slug>/site_map.json` and human-skim `<site_slug>/site_map.md`.

_Rules_: Site capability graphs must treat state (modals, pagination) as first-class, not visual layouts.

#### Stage 2: Capability Map → CLI Specification

1. **Namespace Generation**: Produce CLI grammar that mirrors site capabilities directly (e.g., `oclaw twitter do follow --user @user`).
2. **Contracts**: Establish args, validations, side effects for every command.
3. **Policies & Safety**: Inject read-only mode boundaries, `--dry-run`, and wait conditions.
4. **Outputs**: Generates `<site_slug>/commands.yaml` + Python execution adapter + `runlog.jsonl`.

---

## Foundational `--json` Agent Interfaces

All generated CLI commands, including legacy `launch.py` instances, MUST support JSON-based programmatic communication.

| Flag        | Purpose                           | Output Structure                               |
| ----------- | --------------------------------- | ---------------------------------------------- |
| `--json`    | Machine-readable output           | JSON stdout strictly                           |
| `--dry-run` | **MANDATORY**: Test plan          | Print plan without executing side effects      |
| `--confirm` | **MANDATORY**: Destructive action | Proceed with destructive state limits bypassed |
| `--help`    | Usage documentation               | Human-readable manual                          |
| `--status`  | Active connection/pid             | `{"running": true, "auth": "chrome-profile"}`  |

### Output JSON Format

```json
{
  "success": true,
  "status": "completed",
  "data": {
    "result": "...",
    "state_hash": "...",
    "screenshots": ["/tmp_screenshots/action_post.png"]
  },
  "error": null
}
```

---

## Engine Router Contract (Fallback Strategies)

Agents are logic-agnostic, not runtime-agnostic. WSP 103 mandates Python as the core orchestrator, dictating strict adherence to an Engine Adapter Contract that determines _how_ interactions transpire based on snapshot confidence.

### The Engine Selection Router

| Priority         | Engine               | Use Case                                                                                                      |
| ---------------- | -------------------- | ------------------------------------------------------------------------------------------------------------- |
| **1 (Primary)**  | Playwright (DOM/CDP) | DOM + Accessibility tree is intact. Requires speed, strong wait determinism, trace artifacts.                 |
| **2 (Compat)**   | Selenium             | Legacy sites, Enterprise grid restrictions. "Good enough" selector maps.                                      |
| **3 (Fallback)** | UI-TARS (Vision)     | DOM hostile (canvas, shadow dom, shifting IDs). Repeated selector failures; acts on screen pixels explicitly. |

### Adapter Input Contract (JSON Schema)

```json
{
  "goal_step": "string - intent",
  "context": "URL/Session state",
  "selectors": "Array of fallback candidate selectors",
  "assertions": "Regex/Status checks to verify success",
  "limits": { "timeout": 30000, "read_only": true }
}
```

_Verification of success equals state assertions (element visible, URL regex match), not merely "no exceptions thrown."_

---

## Typeball Project Structure

Generated Typeballs are stored within the module executing the interface logic.

```text
/typeballs/<site_slug>/
  site_map.json            # UITars capability graph (pages, states, actions)
  selectors.json           # robust selector sets + fallbacks
  commands.yaml            # CLI spec (args, validation, side effects)
  policies.yaml            # confirm rules, read-only zones, rate limits
  flows/                   # reusable multi-step macros (yaml)
  cli/                     # generated Python implementation
  fixtures/                # test creds + mock data (no secrets committed)
  logs/                    # jsonl audit trails & screenshot before/afters
```

---

## The Master `oclaw` Syntax

The universal CLI interface invoked by 0102 agents operates identically irrespective of language implementation underlying it:

```bash
# Typeball installation/generation
oclaw typeball install <site_slug>

# Auditing and mapping
oclaw site scan --url https://<target> --auth chrome-profile
oclaw site map build --from scan_output/
oclaw cli gen --map site_map.json --persona digital-twin-012

# Standard Orchestration
oclaw <site_slug> help
oclaw <site_slug> do <command> [args] --dry-run
oclaw <site_slug> do <command> [args] --confirm
oclaw <site_slug> flow run <flow_name> ...
```

---

## Non-Negotiables & Validations

1. **Dry-runs**: `--dry-run` must always be supported to dump execution plans without causing side effects.
2. **Confirm Actions**: `--confirm` defaults to FALSE. Any destructive action (posts, deletes, money flow) throws a validation error unless provided.
3. **Audit Log**: Every step must generate `jsonl` logs + screen clippings (`screenshots_pre`, `screenshots_post`).
4. **Testing**: Regression tests per command using recorded fixtures.
5. **No Secrets**: Use `WSP_71_Secrets_Management_Protocol.md`, openclaw secret injects or Vault. Never commit keys to the typeball directories.

---

**Protocol Status**: ACTIVE
**Catalog Location**: `holo_index/docs/AGENT_CLI_CATALOG.md`
**Compliance**: `python holo_index.py --check-cli-compliance`
