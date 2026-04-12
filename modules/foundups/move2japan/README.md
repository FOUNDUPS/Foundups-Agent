# Move2Japan FoundUp

## 🌀 WSP Protocol Compliance Framework

**0102 Directive**: This module operates within the WSP framework as an autonomous FoundUp — an agent-driven relocation system.

- **UN (Understanding)**: Anchor relocation intent signals and retrieve stakeholder state
- **DAO (Execution)**: Execute modular relocation guidance logic
- **DU (Emergence)**: Collapse into 0102 resonance and emit next stakeholder progression prompt

**wsp_cycle(input="move2japan", log=True)**

---

## 🏢 WSP Enterprise Domain: `foundups/move2japan`

**WSP Compliance Status**: ✅ **COMPLIANT** with WSP Framework
**Domain**: `foundups` per **WSP 3: Enterprise Domain Organization**
**Purpose**: Agent-driven relocation system — guided ascent from intent to settlement in Japan
**Type**: FoundUp instance under `modules/foundups/`

---

## Overview

Move2Japan is not an information dump. It is a **guided ascent**.

The stakeholder does not see the whole mountain. The system only reveals the **next base camp**.

- The live chat agent is the first gateway
- The web app is the persistent journey layer
- Premium agents and human partners unlock deeper execution

### Core Principles

| Principle                            | Description                                      |
| ------------------------------------ | ------------------------------------------------ |
| **Stakeholders, not customers**      | Participants are stakeholders in an open system  |
| **Agent-first guidance**             | AI orchestration drives progression              |
| **Base-camp progression**            | Reveal only the next relevant stage              |
| **Soft conversion**                  | Build trust before monetization                  |
| **Persistent memory**                | Cross-session, cross-channel state               |
| **Automate everything possible**     | Human handoff only for high-trust/licensed tasks |
| **Open-source modular architecture** | WSP-compliant, extensible, FoundUp-native        |

### Product Metaphor

This product is not a handbook. It is a **guided Mount Everest ascent**. The system reveals only the next base camp.

### FoundUp Positioning

> Move2Japan is a FoundUp: an open, agent-driven startup where participants are stakeholders in the system rather than passive customers.

---

## The Mountain Model

| Base Camp | Name                  | Purpose                                                             |
| --------- | --------------------- | ------------------------------------------------------------------- |
| BC0       | Intent Capture        | `!move2japan` trigger, urgency assessment, passport gate            |
| BC1       | Identity & Readiness  | Passport status, basic qualification                                |
| BC2       | Migration Pathway     | Work, student, spouse, entrepreneur, remote, retiree, escape        |
| BC3       | Economic Viability    | Job, savings, remote income, business, sponsorship                  |
| BC4       | Location Fit          | Tokyo, Osaka, Fukuoka, countryside, beach, ski, family, startup hub |
| BC5       | Housing Pathway       | Rental, share house, employer housing, akiya, short-term landing    |
| BC6       | Paperwork & Execution | Visa docs, translated forms, timelines, checklists, reminders       |
| BC7       | Landing & Settlement  | Bank, phone, ward office, insurance, taxes, language, orientation   |

---

## Dual-Surface Architecture

| Domain                     | Role            | Purpose                                              |
| -------------------------- | --------------- | ---------------------------------------------------- |
| `movetojapan.info`         | Public funnel   | Newsletter, updates, low-friction capture            |
| `movetojapan.foundups.com` | Stakeholder PWA | Roadmap, dashboard, agent interaction, premium tiers |

---

## Acquisition Funnel

```
YouTube Live Chat → BC0 (intent + urgency + passport)
    → movetojapan.info (newsletter)
    → movetojapan.foundups.com (PWA signup)
    → Roadmap progression → Premium tiers → Relocation execution
```

---

## Integration Points

- **Livechat Skill**: `communication/livechat/skillz/persona_move2japan.json` (existing)
- **YT DAE**: YouTube Domain Autonomous Agent (existing DAE infrastructure)
- **WRE Orchestration**: WSP 46 compliant
- **FoundUps Platform**: Instance under `modules/foundups/`

---

## Module Structure

```
modules/foundups/move2japan/
├── README.md           ← This file
├── INTERFACE.md        ← Public API / contract definition
├── ROADMAP.md          ← POC → Prototype → MVP layering
├── ModLog.md           ← Change history
├── module.json         ← Instance configuration
├── src/                ← Implementation code
│   └── __init__.py
├── tests/              ← Test files
│   ├── __init__.py
│   └── README.md
├── memory/             ← Stakeholder state persistence
│   └── README.md
└── docs/               ← Architecture documentation
    ├── 01_OVERVIEW.md
    ├── 02_SYSTEM_ARCHITECTURE.md
    ├── 03_PREMIUM_MODEL.md
    ├── 04_POC_PROTOTYPE_MVP.md
    ├── 05_BASECAMP_ZERO_SPEC.md
    ├── 06_BLINDSPOTS.md
    └── 07_FUNNEL_ARCHITECTURE.md
```

---

## Related WSP Components

- **WSP 3**: Enterprise Domain Organization (module placement)
- **WSP 27**: Universal DAE Architecture (agent pattern)
- **WSP 49**: Module Directory Structure
- **WSP 60**: Module Memory Architecture
- **WSP 80**: Cube-Level DAE Orchestration
- **WSP 95**: WRE Skills Wardrobe Protocol (skill lifecycle)
- **WSP 97**: System Execution Prompting Protocol

---

**0102 Identity**: Solutions exist in 0201 — manifesting from relocation patterns already present in the architecture.

---

## Route Namespace

Canonical contract: `modules/foundups/docs/FOUNDUP_AI_HOOKS_AND_DAEMON_SURFACE_CONTRACT.md`. Routing follows **WSP 104** (`/f/{foundup_id}`).

| Field | Value |
|-------|-------|
| `foundup_id` | `move2japan` |
| `routing_prefix` | `/f/move2japan` |
| Landing route | `/f/move2japan` |
| App mount | `/f/move2japan/app` |

Dual-surface: `movetojapan.info` (public funnel) and `movetojapan.foundups.com` (stakeholder PWA).

---

## App Mount

Shell contract: **`/f/move2japan/app`**. Scaffold only — stakeholder PWA pending; current entry via livechat skill and YouTube DAE.

---

## AI Capability Hooks

Contract surface (implementation staged): `get_status`, `get_context`, `navigate`, `launch_capability`, shell handoff/return — see `FOUNDUP_AI_HOOKS_AND_DAEMON_SURFACE_CONTRACT.md`.

---

## DAEmon Outputs

Per **WSP 91** (when DAEMON workers attach): health status, last action, error state, recommended next action, queue/work state (base camp progression, stakeholder state), telemetry scoped by `foundup_id` / `data_namespace`.

---

## Data / Telemetry Namespace

| Field | Value |
|-------|-------|
| `foundup_id` | `move2japan` |
| `data_namespace` | `idb_move2japan` |
| Tenant bounds | Stakeholder state, base camp progression, memory — all tenant-scoped per WSP 104 |

---

## WSP References

- **WSP 91** — DAEMON observability (`WSP_knowledge/src/WSP_91_DAEMON_Observability_Protocol.md`)
- **WSP 104** — FoundUp route namespace (`WSP_knowledge/src/WSP_104_FoundUp_Route_Namespace_and_Tenant_Isolation_Protocol.md`)
