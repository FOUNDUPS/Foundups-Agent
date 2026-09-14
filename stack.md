# stack.md - Development Stack Inventory

> **Purpose**: Single source of truth for the development stack. Read at session start.
> **Last audited**: 2026-05-30

---

## Languages & Runtimes

| Component | Version | Notes |
|-----------|---------|-------|
| Python | 3.12 | Primary language |
| Node.js | >=18.0.0 | Firebase Functions, tooling |
| Bash | - | Shell scripts, CI |

---

## Package Managers

| Manager | Lock File | Scope |
|---------|-----------|-------|
| pip | requirements.txt | Python deps (root + per-module) |
| npm | package-lock.json | Node deps, Firebase, Vercel CLI |

---

## Frameworks & Libraries

### Python Core
- **FastAPI** >=0.104.0 - Web framework (Vercel deployment)
- **SQLAlchemy** >=2.0.0 - Database ORM (FAM persistence)
- **pytest** >=7.0.0 - Testing framework
- **pytest-asyncio** >=0.26.0 - Async test support
- **pytest-cov** >=2.10.0 - Coverage reporting

### AI/ML
- **llama-cpp-python** ==0.2.69 - Local LLM inference (Qwen, Gemma)
- **sentence-transformers** >=2.2.0 - Semantic embeddings
- **openai-whisper** >=20231117 - Speech-to-text
- **torch** >=2.0.0 - PyTorch (Whisper backend)

### Browser Automation
- **Selenium** - Browser control (foundups_selenium module)
- **undetected-chromedriver** - Anti-detection (YouTube, LinkedIn)

---

## Databases & Vector Stores

| Store | Location | Purpose |
|-------|----------|---------|
| SQLite | Per-module | FAM events, PatternMemory, skill outcomes |
| ChromaDB | >=0.4.0 | HoloIndex vector store |
| Firestore | Cloud | Production data (foundups.com) |

---

## MCP Servers & Tools

### Active MCP Servers (3)
```yaml
holo_index:
  tools:
    - semantic_code_search
    - wsp_protocol_lookup
    - cross_reference_search
    - mine_012_conversations

wsp_governance:
  tools:
    - compliance_check
    - protocol_recommendation
    - violation_detection

web_search:
  tools:
    - web_search (DuckDuckGo)
    - serper_search (Google via Serper.dev)
    - web_search_news
    - fetch_webpage
    - get_search_status
```

### MCP Infrastructure
- **Location**: `foundups-mcp-p1/`
- **Setup**: `setup_mcp_servers.py`

---

## AI Models & Workers

### Claude (Primary)
- **Model**: claude-opus-4-8 (configured in .claude/settings.json)
- **Prior**: claude-opus-4-5-20251101, claude-opus-4-6

### Local Models (E:/HoloIndex/models/)
| Model | Purpose | Inference |
|-------|---------|-----------|
| qwen3.5-4b | Strategic planning (200-500 tokens) | llama-cpp |
| gemma4-e2b | Fast pattern matching (50-100 tokens) | llama-cpp |
| sentence-transformers/all-MiniLM-L6-v2 | Embeddings | HuggingFace |
| ui-tars-1.5 | UI understanding | Needs verification |

### Agent Architecture (WSP 77)
```
Phase 1 (Gemma): Fast pattern matching (50-100ms)
Phase 2 (Qwen): Strategic planning (200-500ms)
Phase 3 (0102): Human supervision
Phase 4 (Learning): Pattern storage
```

---

## WSP/WRE/HoloIndex Systems

### WSP Framework
- **Protocols**: 110 numbered WSP files in `WSP_framework/src/` (118 `WSP_*.md` files total, including indexes/guides)
- **Master Index**: `WSP_MASTER_INDEX.md`
- **Core**: WSP_00 (Zen State), WSP_77 (Agent Coordination), WSP_80 (DAE)

### WRE (Worker Runtime Environment)
- **Location**: `modules/infrastructure/wre_core/`
- **Components**:
  - `wre_master_orchestrator.py` - Main orchestrator
  - `libido_monitor.py` - Gemma pattern frequency sensor
  - `pattern_memory.py` - SQLite outcome storage
  - `wre_skills_loader.py` - Progressive skill disclosure

### HoloIndex
- **Location**: `holo_index/`
- **Entry**: `holo_index.py`
- **Qwen Advisor**: `holo_index/qwen_advisor/orchestration/autonomous_refactoring.py`

---

## Module Domains (WSP 3)

```
modules/
  ai_intelligence/     # AI orchestration, agents, consciousness
  blockchain/          # Algorand integration (Layer 1)
  communication/       # Messaging, notifications
  data/                # Data processing
  development/         # Dev tools
  economy/             # Tokenomics, FAM
  foundups/            # Core FoundUp logic, simulator
  gamification/        # Engagement mechanics
  infrastructure/      # WRE, MCP, DAE, browser automation
  logs/                # Logging infrastructure
  memory/              # Cross-platform memory
  mesh/                # Distributed systems
  platform_integration/ # YouTube, LinkedIn, Discord, etc.
  telemetry/           # Observability
```

---

## Testing Tools

| Tool | Purpose | CI |
|------|---------|-----|
| pytest | Unit/integration tests | Yes |
| pytest-cov | Coverage | Yes |
| ruff | Linting (E501, F401 ignored) | Yes |
| redteam suite | Security regression | Observation mode |

### CI Jobs (.github/workflows/ci.yml)
- `test` - Simulator + FAM tests
- `lint` - Ruff check
- `security` - Secret scanning, .env check
- `redteam_observation` - Report-only security tests

---

## Deployment

### Vercel
- **Config**: `vercel.json`
- **Entry**: `main.py` (@vercel/python)
- **Region**: iad1
- **Routes**: /api/holoindex, /api/search, catch-all

### Firebase
- **Config**: `firebase.json`
- **Site**: foundupscom
- **Functions**: Node.js 20 (`functions/`)
- **Firestore**: nam5 region

### Google Cloud
- **Cloud Run**: GotJunk deployment (deploy-gotjunk.yml)

---

## Security & Config

### Environment
- `.env` - Local secrets (NEVER tracked)
- `.env.example` - Template (if exists)
- `.claude/settings.json` - Model config
- `.claude/settings.local.json` - Permission allowlist

### Secret Patterns (blocked in CI)
- `AIza*` - Google API keys
- `sk-*` - OpenAI/Anthropic keys
- `ghp_*`, `gho_*` - GitHub tokens
- `AKIA*` - AWS keys

---

## External APIs & Integrations

| Service | Purpose | Auth |
|---------|---------|------|
| Google APIs | YouTube, OAuth | OAuth2 |
| Firebase | Hosting, Firestore, Functions | Service account |
| Vercel | Python serverless | CLI token |
| Serper.dev | Google search API | SERPER_API_KEY |
| DuckDuckGo | Free web search | None |
| Algorand | Blockchain Layer 1 | py-algorand-sdk |
| Clerk | Auth (clerk-nextjs/) | OAuth |

---

## Key Entry Points

| Purpose | File |
|---------|------|
| Main CLI | `main.py` |
| HoloIndex search | `holo_index.py` |
| WSP Orchestrator | `modules/infrastructure/wsp_orchestrator/src/wsp_orchestrator.py` |
| MCP Manager | `modules/infrastructure/mcp_manager/src/mcp_manager.py` |
| Autonomous Refactoring | `holo_index/qwen_advisor/orchestration/autonomous_refactoring.py` |
| Navigation map | `NAVIGATION.py` |

---

## Needs Verification

- [ ] `ui-tars-1.5` model usage and integration
- [ ] `ii-agent` model in HoloIndex/models
- [ ] Clerk auth flow (clerk-nextjs/ module status)
- [ ] Container isolation module readiness
- [ ] GotJunk Cloud Run deployment status (may be stale per memory)

---

*Generated by 0102 stack audit. Update after significant infrastructure changes.*
