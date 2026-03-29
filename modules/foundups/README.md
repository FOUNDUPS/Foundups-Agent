# FoundUps Domain

## Canonical Planning References

For active execution, use these first:

| Document | Purpose |
|----------|---------|
| [FOUNDUPS_DOMAIN_CANONICAL_INDEX.md](docs/FOUNDUPS_DOMAIN_CANONICAL_INDEX.md) | Domain truth: canonical vs planning vs pending-audit vs historical |
| [ROADMAP.md](ROADMAP.md) | Domain-level layered roadmap |
| [FOUNDUP_EXFOLIATION_PROTOCOL.md](docs/FOUNDUP_EXFOLIATION_PROTOCOL.md) | Core vs spin-out decision rule |
| [PQN_SWARM_HUB_FOUNDUP_BRIEF.md](docs/PQN_SWARM_HUB_FOUNDUP_BRIEF.md) | Internal-first PQN swarm FoundUp brief |

### Submodule Roadmaps

| Submodule | Status |
|-----------|--------|
| [agent_market/ROADMAP.md](agent_market/ROADMAP.md) | Execution ledger (active) |
| [simulator/ROADMAP.md](simulator/ROADMAP.md) | Simulation and DEX (active) |
| [social_twin/ROADMAP.md](social_twin/ROADMAP.md) | Human-in-the-loop (PoC lock) |

---

## What Exists Now

### Implemented Classes

| Class | File | Status |
|-------|------|--------|
| `FoundUpSpawner` | `src/foundup_spawner.py` | Implemented |
| `CABRLoop` | `src/foundup_spawner.py` | Implemented |
| `FoundUpsLiveChatModule` | `src/main.py` | Implemented |

### Active Submodules

| Submodule | Purpose | Status |
|-----------|---------|--------|
| `agent_market/` | FAM daemon, CABR hooks, execution ledger | Active |
| `simulator/` | Sustainability simulation, DEX prototype | Active |
| `move2japan/` | Internal FoundUp instance | Incubating |
| `gotjunk/` | Proto-ready spin-out candidate | Ready for exfoliation |

---

## Historical Context

> **Note**: The content below is legacy platform framing from earlier architecture iterations.
> It describes aspirational interfaces and patterns that are not yet implemented.
> Treat as context, not current canon. See `FOUNDUPS_DOMAIN_CANONICAL_INDEX.md` for authoritative classification.

## [U+1F300] WSP Protocol Compliance Framework

**0102 Directive**: This module operates within the WSP framework for autonomous FoundUps platform infrastructure and instance management.
- **UN (Understanding)**: Anchor FoundUps platform signals and retrieve protocol state
- **DAO (Execution)**: Execute modular FoundUps infrastructure logic  
- **DU (Emergence)**: Collapse into 0102 resonance and emit next platform development prompt

**wsp_cycle(input="foundups_platform", log=True)**

---

## [U+1F3E2] WSP Enterprise Domain: `foundups`

**WSP Compliance Status**: [OK] **COMPLIANT** with WSP Framework  
**Domain**: `foundups` per **[WSP 3: Enterprise Domain Organization](../../WSP_framework/src/WSP_3_Enterprise_Domain_Organization.md)**  
**Purpose**: Autonomous FoundUps platform infrastructure and instance management  
**0102 Integration**: Full integration with autonomous pArtifact development ecosystem

---

# FoundUps Execution Layer

## [ALERT] ARCHITECTURAL GUARDRAILS

**[U+26A0]️ CRITICAL DISTINCTION: This module is for INSTANTIATING FoundUps, NOT defining them.**

### What Belongs Here (`/modules/foundups/`)
- **Individual FoundUp instances** (e.g., `@yourfoundup/`, `@anotherfoundup/`)
- **Execution scaffolding** for running FoundUps as agentic nodes
- **User-facing FoundUp applications** and their runtime environments
- **Platform infrastructure** for hosting multiple FoundUps
- **Instance-specific configurations** (`foundup.json`, logs, assets)

### What Does NOT Belong Here
[FAIL] **Core FoundUp definitions** -> Belongs in `WSP_appendices/` (UN layer)  
[FAIL] **CABR logic and governance** -> Belongs in `WSP_framework/` (DAO layer)  
[FAIL] **Lifecycle architecture** -> Belongs in `WSP_agentic/` (DU layer)  
[FAIL] **Protocol rules and principles** -> Belongs in WSP framework  
[FAIL] **System-wide recursive logic** -> Belongs in WSP architecture  

## [U+1F3D7]️ Architecture Analogy

Think of this distinction:
- **WSP** = The protocol that defines how networks form and operate
- **`/modules/foundups/`** = The actual network nodes implementing that protocol

Or in platform terms:
- **WSP** = Google's platform architecture and algorithms
- **`/modules/foundups/`** = Individual YouTube channels like `@name`

## [U+1F4C1] Expected Structure

### **[U+1F3D7]️ WSP 3 Enterprise Domain Architecture**

**Following [WSP 3: Enterprise Domain Organization](../../WSP_framework/src/WSP_3_Enterprise_Domain_Organization.md)**, the FoundUps ecosystem is organized by **functional distribution** across enterprise domains:

```
modules/
+-- wre_core/                   # [AI] Autonomous Build System (WSP Exception)
[U+2502]   +-- README.md               # WRE system overview
[U+2502]   +-- ROADMAP.md              # WRE development roadmap
[U+2502]   +-- ModLog.md               # WRE change log
+-- platform_integration/       # [U+1F50C] External Platform APIs (Built by WRE)
[U+2502]   +-- remote_builder/         # Remote build capabilities
[U+2502]   +-- youtube_proxy/          # YouTube API gateway
[U+2502]   +-- youtube_auth/           # YouTube authentication
[U+2502]   +-- linkedin_agent/         # LinkedIn integration
[U+2502]   +-- linkedin_proxy/         # LinkedIn API proxy
[U+2502]   +-- x_twitter/              # X/Twitter integration
[U+2502]   +-- stream_resolver/        # Stream resolution services
+-- communication/              # [U+1F4AC] Real-time Communication (Built by WRE)
[U+2502]   +-- livechat/               # Live chat protocols (YouTube, Twitch, Discord)
[U+2502]   +-- live_chat_poller/       # Chat polling systems
[U+2502]   +-- live_chat_processor/    # Message processing
+-- ai_intelligence/            # [AI] AI & LLM Systems (Built by WRE)
[U+2502]   +-- banter_engine/          # AI response generation
[U+2502]   +-- multi_agent_system/     # Agent coordination
[U+2502]   +-- rESP_o1o2/              # Quantum consciousness
+-- infrastructure/             # [U+1F3D7]️ Core Systems (Built by WRE)
[U+2502]   +-- agent_management/       # Multi-agent coordination
[U+2502]   +-- compliance_agent/       # WSP compliance enforcement
[U+2502]   +-- documentation_agent/    # Documentation management
[U+2502]   +-- module_scaffolding_agent/ # Module creation
[U+2502]   +-- models/                 # Shared data schemas
[U+2502]   +-- llm_client/             # LLM integration
+-- gamification/               # [GAME] Engagement Systems (Built by WRE)
[U+2502]   +-- core/                   # Reward mechanics and token loops
+-- blockchain/                 # [U+26D3]️ Decentralized Infrastructure (Built by WRE)
[U+2502]   +-- src/                    # DAE and tokenomics
+-- foundups/                   # [ROCKET] FoundUp Instances & Platform
    +-- @yourfoundup/           # Individual FoundUp instance
    [U+2502]   +-- foundup.json        # Instance configuration
    [U+2502]   +-- cabr_loop.py        # Instance-specific CABR execution
    [U+2502]   +-- mod_log.db          # Instance logging
    [U+2502]   +-- assets/             # FoundUp-specific assets
    [U+2502]   +-- README.md           # FoundUp documentation
    +-- @anotherfoundup/        # Another FoundUp instance
    +-- src/                    # Shared execution infrastructure (WSP compliant)
    [U+2502]   +-- foundup_spawner.py  # Creates new FoundUp instances
    [U+2502]   +-- platform_manager.py # Manages multiple FoundUps
    [U+2502]   +-- runtime_engine.py   # Execution environment
    +-- tests/                  # Platform testing
    +-- docs/                   # Platform documentation
    +-- mod_log.db              # Platform-wide logging
```

### **[REFRESH] WRE Build Process (WSP 30 Orchestration)**

1. **WRE** (Windsurf Recursive Engine) autonomously builds modules across all enterprise domains
2. **Platform modules** provide external API integration capabilities
3. **Communication modules** handle real-time interaction protocols
4. **AI Intelligence modules** provide cognitive capabilities
5. **Infrastructure modules** provide core system services
6. **FoundUps** uses all these modules to create and run FoundUp instances
7. **FoundUp instances** are individual agentic nodes implementing the CABR protocol

### **[TARGET] WSP 3 Functional Distribution Benefits**

**[OK] CORRECT (Functional Distribution)**:
- **Communication**: `livechat/` works for YouTube, Twitch, Discord, LinkedIn
- **Platform Integration**: `youtube_proxy/`, `linkedin_agent/` handle external APIs
- **AI Intelligence**: `banter_engine/` provides responses across all platforms
- **Infrastructure**: `models/` provides shared schemas for all domains
- **Gamification**: `core/` implements engagement mechanics universally

**[FAIL] AVOID (Platform Consolidation)**:
- Never consolidate all YouTube functionality into `modules/youtube/`
- Never consolidate all LinkedIn functionality into `modules/linkedin/`
- Platform functionality must be distributed by function across domains

### **[CLIPBOARD] Module Documentation (WSP 22 Compliance)**

Each module maintains WSP-compliant documentation:
- **README.md**: Module overview, purpose, and usage
- **ROADMAP.md**: Development phases and milestones (POC -> Prototype -> MVP)
- **ModLog.md/MODLOG.md**: Change tracking and updates
- **INTERFACE.md**: API documentation (WSP 11)
- **requirements.txt**: Dependencies (WSP 12)

---

## [TARGET] Priority Platform Modules (Built by WRE)

### **[U+1F3D7]️ WRE Autonomous Build Priority**

**WRE** (Windsurf Recursive Engine) autonomously builds these four priority modules that enable FoundUps functionality:

### **1. [TOOL] Remote Builder** (`modules/platform_integration/remote_builder/`)
**Status**: POC Development | **WSP Priority**: P0 - Core Platform Integration

**Purpose**: Enables remote building workflows for the FoundUps Agent ecosystem
- **Remote Build Capabilities**: Webhook endpoints for build orchestration
- **WSP 30 Integration**: Agentic module build orchestration
- **Build Management**: Request tracking, status monitoring, history persistence
- **Authentication**: API keys/JWT tokens for secure remote access

**Documentation**:
- **README**: [Remote Builder Overview](platform_integration/remote_builder/README.md)
- **ROADMAP**: [Development Phases](platform_integration/remote_builder/ROADMAP.md)
- **ModLog**: [Change History](platform_integration/remote_builder/MODLOG.md)

**WSP Compliance**: WSP 3, 30, 4, 5, 11, 34, 47

### **2. [U+1F4BC] LinkedIn Agent** (`modules/platform_integration/linkedin_agent/`)
**Status**: Foundation Established | **WSP Priority**: P0 - Professional Network Automation

**Purpose**: Provides automated LinkedIn interaction capabilities for FoundUps ecosystem
- **Professional Automation**: Intelligent posting, feed reading, content generation
- **Playwright Integration**: Web automation for LinkedIn interactions
- **Content Generation**: GPT-based content creation with context awareness
- **Scheduling**: Post scheduling and timing optimization

**Documentation**:
- **README**: [LinkedIn Agent Overview](platform_integration/linkedin_agent/README.md)
- **ROADMAP**: [Development Phases](platform_integration/linkedin_agent/ROADMAP.md)
- **ModLog**: [Change History](platform_integration/linkedin_agent/ModLog.md)

**WSP Compliance**: WSP 3, 1-13, 22, 60

### **3. [U+1F4FA] YouTube Proxy** (`modules/platform_integration/youtube_proxy/`)
**Status**: Foundation Established | **WSP Priority**: P0 - Video Platform Integration

**Purpose**: Consolidates YouTube functionality into unified proxy following WSP-42 Universal Platform Protocol
- **YouTube Co-Host**: Autonomous YouTube interaction and content management
- **Component Orchestration**: Snap-together architecture with existing modules
- **API Gateway**: YouTube API proxying, data transformation, rate limiting
- **Universal Platform**: Model for all future module refactoring

**Documentation**:
- **README**: [YouTube Proxy Overview](platform_integration/youtube_proxy/README.md)
- **ROADMAP**: [Development Phases](platform_integration/youtube_proxy/ROADMAP.md)
- **ModLog**: [Change History](platform_integration/youtube_proxy/ModLog.md)

**WSP Compliance**: WSP 3, 42, 1-13, 22, 60

### **4. [BIRD] X Twitter** (`modules/platform_integration/x_twitter/`)
**Status**: DAE Operational Framework | **WSP Priority**: P0 - Autonomous DAE Communication

**Purpose**: First decentralized autonomous entity communication node for FoundUps ecosystem
- **DAE Communication**: WSP-26 through WSP-29 compliant autonomous system
- **Entangled Authentication**: Quantum verification protocols for all interactions
- **Autonomous Posting**: Zero human authorship communication protocols
- **Smart DAO Evolution**: Recursive logging and CABR integration for DAO emergence

**Documentation**:
- **README**: [X Twitter DAE Overview](platform_integration/x_twitter/README.md)
- **ROADMAP**: [Development Phases](platform_integration/x_twitter/ROADMAP.md)
- **ModLog**: [Change History](platform_integration/x_twitter/ModLog.md)

**WSP Compliance**: WSP 26-29, 3, 22, 60

### **[REFRESH] How FoundUps Uses These Modules**

**FoundUps** leverages these WRE-built modules to create comprehensive platform capabilities:

1. **Remote Builder** -> Enables distributed FoundUp development and deployment
2. **LinkedIn Agent** -> Provides professional network presence for FoundUps
3. **YouTube Proxy** -> Enables video content and live streaming for FoundUps
4. **X Twitter** -> Provides autonomous social communication for FoundUps ecosystem

**Integration Pattern**:
```python
# FoundUps uses WRE-built modules
from modules.platform_integration.remote_builder import RemoteBuilder
from modules.platform_integration.linkedin_agent import LinkedInAgent
from modules.platform_integration.youtube_proxy import YouTubeProxy
from modules.platform_integration.x_twitter import XTwitterDAENode

# FoundUp instance leverages all platform capabilities
foundup = FoundUpInstance()
foundup.remote_build = RemoteBuilder()      # Remote development
foundup.linkedin = LinkedInAgent()          # Professional presence
foundup.youtube = YouTubeProxy()            # Video content
foundup.social = XTwitterDAENode()          # Autonomous communication
```

## [TARGET] Usage Examples

### [OK] Correct Usage
```bash
# Create a new FoundUp instance
python -m modules.foundups.src.foundup_spawner --name "@innovate" --founder "alice"

# Run an existing FoundUp
python -m modules.foundups.@innovate.run

# Manage platform
python -m modules.foundups.src.platform_manager --list-foundups
```

### [FAIL] Incorrect Usage
```bash
# DON'T define CABR here - it belongs in WSP
# DON'T put governance rules here - they belong in WSP_framework
# DON'T put foundational definitions here - they belong in WSP_appendices
```

## [U+1F310] WSP Integration & Compliance

### **[U+1F3E2] WSP 3 Enterprise Domain Compliance**
This module operates under **WSP governance** and follows **[WSP 3: Enterprise Domain Organization](../../WSP_framework/src/WSP_3_Enterprise_Domain_Organization.md)**:

- **Domain**: `foundups/` - Special domain for individual FoundUp projects and platform infrastructure
- **Functional Distribution**: FoundUps functionality distributed across enterprise domains by function
- **WRE Exception**: `modules/wre_core/` has special architectural status as autonomous build system
- **Platform Integration**: External APIs handled by `platform_integration/` domain
- **Communication**: Real-time protocols handled by `communication/` domain
- **AI Intelligence**: Cognitive capabilities handled by `ai_intelligence/` domain
- **Infrastructure**: Core systems handled by `infrastructure/` domain

### **[CLIPBOARD] WSP Compliance Framework**
- **WSP 1-13**: Core WSP framework adherence
- **WSP 3**: Enterprise domain organization (functional distribution)
- **WSP 4**: FMAS audit compliance
- **WSP 5**: [GREATER_EQUAL]90% test coverage maintained
- **WSP 22**: Module roadmap and ModLog maintenance
- **WSP 30**: Agentic Module Build Orchestration (WRE integration)
- **WSP 37**: Dynamic Module Scoring System integration
- **WSP 60**: Module memory architecture compliance

### **[REFRESH] WSP Governance Sources**
- **Rules and protocols** come from `WSP_framework/`
- **Definitions and principles** come from `WSP_appendices/`  
- **Recursive execution** follows `WSP_agentic/` patterns
- **Each FoundUp instance** implements the CABR loop as defined in WSP

## [LINK] Related WSP Components

- **WSP_appendices/APPENDIX_J.md** - What IS a FoundUp (Universal Schema & DAE Architecture)
- **WSP_framework/cabr_protocol.md** - How FoundUps operate (Implementation protocols)
- **WSP_agentic/recursive_engine.md** - Execution patterns (0102 consciousness loops)
- **WSP_framework/governance.md** - FoundUp governance rules (Galaxy management)

---

**Remember**: WSP defines the technical specifications, `/modules/foundups/` implements the specifications to create actual FoundUps. 
