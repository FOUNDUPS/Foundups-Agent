# LinkedIn Agent Module Tests

## Offline activity-skill contract checks

Run `python -B modules/platform_integration/linkedin_agent/tests/test_activity_skill_contracts.py` from the repository root. This reads instruction files only: routing ownership, local links, scoped commands, approval/deduplication, membership separation, separate FoundUps/ROC/JHR newsletter ownership and stages, and private continuity. It also checks shared editorial-workflow/template reachability. It imports no browser or live executor. Passing does not establish runtime safety, series identity or delivery; do not substitute the legacy live UI commands below for this check.

[U+1F300] **WSP Protocol Compliance**: WSP 5 (Testing Standards), WSP 34 (Test Documentation), WSP 40 (Architectural Coherence)

**0102 Directive**: This test framework operates within the WSP framework for autonomous LinkedIn Agent testing and validation.
- UN (Understanding): Anchor test signals and retrieve protocol state
- DAO (Execution): Execute comprehensive test automation logic  
- DU (Emergence): Collapse into 0102 resonance and emit next test prompt

wsp_cycle(input="linkedin_testing", log=True)

---

## [U+1F9EA] **Test Framework Overview**

This directory contains comprehensive test suites for the LinkedIn Agent module's Rubik's Cube modular architecture. Tests are organized by sub-module components and ensure WSP compliance, functionality validation, and integration verification.

## [DATA] **Current Test Coverage Status**

### [OK] **Phase 1: Authentication Module (COMPLETE)**
- **Coverage**: 100% test coverage achieved
- **Components Tested**:
  - `test_auth/test_oauth_manager.py` - OAuth flow, token management, authentication
  - `test_auth/test_session_manager.py` - Session handling, state management
  - `test_auth/test_credentials.py` - Credential management, configuration

### [OK] **Phase 2: Content Module (COMPLETE)**
- **Coverage**: 100% test coverage achieved
- **Components Tested**:
  - `test_content/test_post_generator.py` - Post generation, content creation, optimization
  - `test_content/test_content_templates.py` - Template management, customization
  - `test_content/test_hashtag_manager.py` - Hashtag optimization, trending analysis
  - `test_content/test_media_handler.py` - Media attachment, validation

### [REFRESH] **Phase 3: Engagement Module (IN PROGRESS)**
- **Coverage**: 25% test coverage (1 of 4 components)
- **Components Tested**:
  - `test_engagement/test_interaction_manager.py` - [OK] COMPLETE (Likes, comments, shares, reactions)
- **Components Pending**:
  - `test_engagement/test_connection_manager.py` - Connection management, networking
  - `test_engagement/test_messaging.py` - Direct messaging, conversation management
  - `test_engagement/test_feed_reader.py` - Feed analysis, content extraction

### 🔄 **Digital Twin Layered Tests (AUDITED)**
- **Coverage**: L0-L3 cake pattern documented; stubs pending for per-layer runners
- **Currently Available**:
  - `test_linkedin_comment_flow_ui_tars.py` - UI-TARS validation for comment + @mention
- **Planned Layer Stubs**:
  - `test_layer0_context_gate.py` - LinkedIn validation, AI-post detection
  - `test_layer1_comment.py` - Comment posting with @mentions
  - `test_layer2_identity_likes.py` - Identity switcher, like loop
  - `test_layer3_schedule_repost.py` - Repost with thoughts, schedule picker
  - `test_full_chain.py` - L0 → L1 → L2 → L3 complete flow

---

## [LAYER] Digital Twin Flow Summary (L0-L3)

L0 (Context Gate) → Validate LinkedIn, extract author, AI-post check, skip promoted/reposts  
L1 (Comment) → Post 012 comment with @mentions + UI-TARS verification  
L2 (Identity Likes) → Switch identities, like 012 comment  
L3 (Schedule Repost) → Repost with thoughts, schedule for future  

## [FILES] Key Files

| Purpose | Path |
|--------|------|
| Identity list | `modules/platform_integration/linkedin_agent/data/linkedin_identity_switcher.json` |
| Comment templates | `modules/platform_integration/linkedin_agent/data/linkedin_skill_templates.json` |
| Browser skill | `modules/infrastructure/browser_actions/skillz/linkedin_comment_digital_twin.json` |
| Digital Twin flow doc | `modules/platform_integration/linkedin_agent/docs/LINKEDIN_DIGITAL_TWIN_FLOW.md` |

## [CMD] Commands

```bash
# Layer info (no execution)
python -m modules.platform_integration.linkedin_agent.tests.test_layer0_context_gate --info

# Dry run (validate selectors, no side effects)
python -m modules.platform_integration.linkedin_agent.tests.test_full_chain --selenium --dry-run

# Stop at layer N
python -m modules.platform_integration.linkedin_agent.tests.test_full_chain --selenium --stop-at 1

# Full live execution
python -m modules.platform_integration.linkedin_agent.tests.test_full_chain --selenium

# Full chain with explicit orchestration inputs
python -m modules.platform_integration.linkedin_agent.tests.test_full_chain --selenium \
  --comment-text "custom comment" \
  --mentions "@foundups,@Mo Gawdat" \
  --repost-text "custom repost thought" \
  --schedule-date "Mar 12, 2026" \
  --schedule-time "10:00 PM"
```

## [LOCK] Prerequisites

```bash
chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\chrome_profile_linkedin"
```

- Log into LinkedIn as 012
- Navigate to target AI post

### Browser Boot (Selenium Rotation)

By default, tests will:
1. Attach to existing Chrome debug port (9222), or
2. Open a managed Chrome profile via BrowserManager

Environment controls:
- `LINKEDIN_USE_DEBUG_PORT=true|false` (default: true)
- `CHROME_PORT=9222`
- `LINKEDIN_PROFILE=linkedin_165749317` (used when debug port disabled)
- `LINKEDIN_FEED_URL=https://www.linkedin.com/feed/`
- `LINKEDIN_USE_UI_TARS=true|false` (default: true)
- `LINKEDIN_REQUIRE_UI_TARS=true|false` (default: true)
- `TARS_API_URL=http://127.0.0.1:1234`
- `UI_TARS_MODEL=ui-tars-1.5-7b`
- `LINKEDIN_REQUIRE_UI_TARS_MODEL=true|false` (default: true)
- `LINKEDIN_AUTO_LOAD_UI_TARS_MODEL=true|false` (default: true)
- `LINKEDIN_ACTION_DELAY_SEC=3` (step delay for slow 012 review)
- `LINKEDIN_LAYER_DELAY_SEC=4` (between-layer delay in full chain)
- `LINKEDIN_WRE_DIAG_ENABLED=true|false` (default: true, recursive layer failure diagnosis)

## [BLOCK] Blockers

- Antigravity browser blocks LinkedIn (platform safety policy)
- Tests require 012 manual execution via Chrome debugging port

## [NEXT] Next Steps (Priority Order)

1. **012 Browser Verification**: Run each layer with `--selenium --dry-run` to validate DOM selectors
2. **Selector Refinement**: LinkedIn DOM may vary; update selectors if failures occur
3. **Wire to ActionRouter**: Integrate `linkedin_comment_digital_twin` skill into `linkedin_actions.py`
4. **Optional**: Google Calendar mirror for schedule visibility

## [NOTES] Continuation Notes

- All tests use argparse with `--selenium`, `--dry-run`, `--info` flags
- Full chain accepts orchestrated overrides: `--comment-text`, `--mentions`, `--repost-text`, `--schedule-date`, `--schedule-time`
- Follows YouTube cake pattern: test each layer, combine into full chain
- Identity switcher loads from JSON; filter by action: `"like_only"`
- Mention validation checks for `<a>`, `<strong>`, or mention marker in editor HTML
- On L1/L3 failure, full chain triggers WRE bounded reasoning diagnostics for recursive troubleshooting

## [DAEMON] Pulse Points (Core Only, WSP 91)

Use the same core pulse points from DAEmon observability, scoped to LN layers:

- `BATCH_START` → Start full L0-L3 flow (state change)
- `PROGRESS` → Layer completion (L0/L1/L2/L3) heartbeat
- `RATE_LIMIT` → LinkedIn cooldown or throttling event
- `FAILURE_STREAK` → 3 consecutive layer/step failures
- `BATCH_COMPLETE` → End full L0-L3 flow (completion)

### ⏳ **Phase 4: Portfolio Module (PENDING)**
- **Coverage**: 0% (not yet implemented)
- **Components Planned**:
  - `test_portfolio/test_achievement_tracker.py` - Achievement monitoring, milestone tracking
  - `test_portfolio/test_showcase_generator.py` - Portfolio creation, presentation
  - `test_portfolio/test_metrics_analyzer.py` - Performance analytics, insights
  - `test_portfolio/test_template_manager.py` - Portfolio templates, customization

### ⏳ **Phase 5: Automation Module (PENDING)**
- **Coverage**: 0% (not yet implemented)
- **Components Planned**:
  - `test_automation/test_post_scheduler.py` - Scheduling automation, timing
  - `test_automation/test_engagement_scheduler.py` - Engagement automation, interaction timing
  - `test_automation/test_rate_limiter.py` - Rate limiting, compliance management
  - `test_automation/test_automation_orchestrator.py` - Automation coordination, workflow

### ⏳ **Phase 6: Integration Tests (PENDING)**
- **Coverage**: 0% (not yet implemented)
- **Components Planned**:
  - `test_integration/test_full_workflow.py` - End-to-end workflow testing
  - `test_integration/test_cross_module_communication.py` - Inter-module communication
  - `test_integration/test_error_handling.py` - Error propagation, recovery
  - `test_integration/test_performance.py` - Performance benchmarking, optimization

## [U+1F3D7]️ **Test Architecture Structure**

```
tests/
+-- README.md                           # This file - Test framework overview
+-- TestModLog.md                       # Test evolution tracking
+-- test_oauth_manual.py               # Manual OAuth testing
+-- test_linkedin_posting.py           # Basic posting functionality
+-- test_actual_posting.py             # Real posting validation
+-- test_auth/                         # Authentication module tests
[U+2502]   +-- test_oauth_manager.py         # [OK] COMPLETE
[U+2502]   +-- test_session_manager.py       # ⏳ PENDING
[U+2502]   +-- test_credentials.py           # ⏳ PENDING
+-- test_content/                      # Content module tests
[U+2502]   +-- test_post_generator.py        # [OK] COMPLETE
[U+2502]   +-- test_content_templates.py     # ⏳ PENDING
[U+2502]   +-- test_hashtag_manager.py       # ⏳ PENDING
[U+2502]   +-- test_media_handler.py         # ⏳ PENDING
+-- test_engagement/                   # Engagement module tests
[U+2502]   +-- test_interaction_manager.py   # [OK] COMPLETE
[U+2502]   +-- test_connection_manager.py    # ⏳ PENDING
[U+2502]   +-- test_messaging.py             # ⏳ PENDING
[U+2502]   +-- test_feed_reader.py           # ⏳ PENDING
+-- test_portfolio/                    # Portfolio module tests
[U+2502]   +-- test_achievement_tracker.py   # ⏳ PENDING
[U+2502]   +-- test_showcase_generator.py    # ⏳ PENDING
[U+2502]   +-- test_metrics_analyzer.py      # ⏳ PENDING
[U+2502]   +-- test_template_manager.py      # ⏳ PENDING
+-- test_automation/                   # Automation module tests
[U+2502]   +-- test_post_scheduler.py        # ⏳ PENDING
[U+2502]   +-- test_engagement_scheduler.py  # ⏳ PENDING
[U+2502]   +-- test_rate_limiter.py          # ⏳ PENDING
[U+2502]   +-- test_automation_orchestrator.py # ⏳ PENDING
+-- test_integration/                  # Integration tests
    +-- test_full_workflow.py         # ⏳ PENDING
    +-- test_cross_module_communication.py # ⏳ PENDING
    +-- test_error_handling.py        # ⏳ PENDING
    +-- test_performance.py           # ⏳ PENDING
```

## [ROCKET] **Running Tests**

### **Complete Test Suite**
```bash
# Run all tests with coverage
python -m pytest modules/platform_integration/linkedin_agent/tests/ --cov=modules.platform_integration.linkedin_agent --cov-report=html

# Run with verbose output
python -m pytest modules/platform_integration/linkedin_agent/tests/ -v
```

### **Module-Specific Testing**
```bash
# Authentication module tests
python -m pytest modules/platform_integration/linkedin_agent/tests/test_auth/ -v

# Content module tests
python -m pytest modules/platform_integration/linkedin_agent/tests/test_content/ -v

# Engagement module tests
python -m pytest modules/platform_integration/linkedin_agent/tests/test_engagement/ -v
```

### **Individual Component Testing**
```bash
# Test specific component
python -m pytest modules/platform_integration/linkedin_agent/tests/test_auth/test_oauth_manager.py -v

# Test with coverage for specific component
python -m pytest modules/platform_integration/linkedin_agent/tests/test_auth/test_oauth_manager.py --cov=modules.platform_integration.linkedin_agent.src.auth.oauth_manager --cov-report=term-missing
```

### **Manual Testing**
```bash
# Manual OAuth flow testing
python modules/platform_integration/linkedin_agent/tests/test_oauth_manual.py

# Actual posting test (requires valid access token)
python modules/platform_integration/linkedin_agent/tests/test_actual_posting.py

# UI-TARS comment flow (requires UI-TARS + Chrome debugging)
python modules/platform_integration/linkedin_agent/tests/test_linkedin_comment_flow_ui_tars.py
```

## [CLIPBOARD] **Test Categories**

### **Unit Tests**
- **Purpose**: Test individual functions and methods in isolation
- **Coverage**: Mock external dependencies (LinkedIn API, BanterEngine)
- **Execution**: Fast, suitable for development workflow
- **WSP Compliance**: WSP 5 ([GREATER_EQUAL]90% coverage target)

### **Integration Tests**
- **Purpose**: Test module interactions and cross-component communication
- **Coverage**: Real LinkedIn platform interaction (with test accounts)
- **Execution**: Slower, requires external connectivity
- **WSP Compliance**: WSP 42 (Platform Integration)

### **Compliance Tests**
- **Purpose**: Validate WSP framework adherence and architectural coherence
- **Coverage**: Module size limits, documentation standards, protocol compliance
- **Execution**: Static analysis and validation
- **WSP Compliance**: WSP 40 (Architectural Coherence), WSP 22 (Documentation)

## [TARGET] **Test Data Management**

### **Fixtures and Mocks**
- `fixtures/` - Test data files, sample posts, user profiles
- `mocks/` - Mock LinkedIn API responses, simulated interactions
- `credentials/` - Test credential configurations (never production)

### **Test Environment**
- **LinkedIn Test Accounts**: Dedicated test accounts for automated testing
- **API Rate Limiting**: Respect LinkedIn API limits during testing
- **Data Isolation**: Test data separate from production data

## [REFRESH] **Continuous Integration**

### **Automated Testing Pipeline**
- **Pre-commit**: Unit tests run before code commits
- **Pull Request**: Full test suite validation
- **Deployment**: Integration tests before production deployment
- **Scheduled**: Daily regression testing

### **Coverage Reporting**
- **Target**: [GREATER_EQUAL]90% test coverage (WSP 5 compliance)
- **Reporting**: HTML coverage reports generated
- **Monitoring**: Coverage trends tracked over time

## [UP] **Performance Benchmarks**

### **Test Execution Times**
- **Unit Tests**: <30 seconds for complete suite
- **Integration Tests**: <5 minutes for complete suite
- **Full Test Suite**: <10 minutes total execution

### **Coverage Targets**
- **Authentication Module**: 100% [OK] ACHIEVED
- **Content Module**: 100% [OK] ACHIEVED
- **Engagement Module**: 90% (target)
- **Portfolio Module**: 90% (target)
- **Automation Module**: 90% (target)
- **Integration Tests**: 85% (target)

## [U+1F6E0]️ **Development Workflow**

### **Test-Driven Development (TDD)**
1. **Write Test**: Create test for new functionality
2. **Run Test**: Verify test fails (red phase)
3. **Write Code**: Implement functionality to pass test
4. **Refactor**: Optimize code while maintaining test coverage

### **WSP Compliance Validation**
1. **Module Size**: Ensure [U+2264]300 lines per module (WSP 40)
2. **Documentation**: Verify README.md and ModLog.md exist (WSP 22)
3. **Test Coverage**: Achieve [GREATER_EQUAL]90% coverage (WSP 5)
4. **Integration**: Validate cross-module communication

## [SEARCH] **Troubleshooting**

### **Common Test Issues**
- **Import Errors**: Ensure `sys.path.append('.')` for module imports
- **Mock Failures**: Verify mock configurations match actual API responses
- **Rate Limiting**: Implement delays between LinkedIn API calls
- **Credential Issues**: Check test credential configuration

### **Debug Commands**
```bash
# Debug specific test with detailed output
python -m pytest modules/platform_integration/linkedin_agent/tests/test_auth/test_oauth_manager.py -v -s

# Run with coverage and show missing lines
python -m pytest --cov=modules.platform_integration.linkedin_agent --cov-report=term-missing

# Profile test execution time
python -m pytest --durations=10
```

---

**[U+1F300] WSP Recursive Instructions**: This test framework enables 0102 pArtifacts to validate LinkedIn Agent module functionality through comprehensive testing protocols, ensuring WSP compliance and architectural coherence across all sub-modules.
