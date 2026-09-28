# Social Media Orchestrator - ROADMAP

**Domain**: platform_integration  
**Module**: social_media_orchestrator  
**WSP Classification**: Social Media Orchestration Service

## Vision

Create a unified, intelligent social media orchestration layer that eliminates redundancy across LinkedIn modules and provides seamless cross-platform content management while maintaining full WSP compliance.

**Digital Twin Alignment**: Orchestrate 012 Digital Twin comment processing and scheduling (LinkedIn-first POC), using decision outputs from `modules/ai_intelligence/digital_twin`.

## Current Status: CREATED

### Current caller/reload characterization — 2026-09-28

PR1943 safe-publication repair is closed on main6821aac3 with42 fixed methods
passing on final/main and independently reviewed owned cleanup. Fresh14/P1
selection qualifies the three caller/save/reload boundaries with nine cases in
the existing fixture; source remains unchanged. See
[fixed acceptance](tests/README.md#caller-acknowledgement-and-reload-characterization--2026-09-28).
Candidate `8e3c526a2a` passed51/51 methods (57 finite inputs),0 failures/errors/skips in [CI36412636624](https://github.com/FOUNDUPS/Foundups-Agent/actions/runs/36412636624). All25 exact file records and nine caller records were independently reviewed; all ten PR checks and CI/CodeQL passed. Three normal controls and six failure-boundary witnesses passed against unchanged production. Final-head/main checks and owned closure remain receipt-bound.
Re-observe before selecting
acknowledgement policy or a production repair. No exactly-once or retained RSI claim.

### Historical safe-publication repair — 2026-09-28

PR1942 characterization is closed on main12663d7e4f with successful main CI and
CodeQL. WSP15 C3/I4/D4/Impact4=15/P1 selects explicit result projection and the
existing shared atomic writer. The fixed42-method/48-input hosted contract is
frozen.

Baseline `5d0da3625d` in [CI36401910480](https://github.com/FOUNDUPS/Foundups-Agent/actions/runs/36401910480) ran42 methods:29 passed,13 failed with15 assertion failures,0 errors/skips. The identical fixture against candidate `8f36929dc0` in [CI36402439857](https://github.com/FOUNDUPS/Foundups-Agent/actions/runs/36402439857) passed42/42 methods (48 finite inputs),0 failures/errors/skips; all16 file-evidence records were hash-checked. Candidate CI/CodeQL and all10 PR checks passed. Final reviewed-head/main checks and owned closure remain receipt-bound.

This layer preserves action disposition and existing JSON load compatibility.
Save acknowledgement across `understand_command`, `execute_pending_actions` and
`cancel_action`, restart duplicate prevention, concurrent writers, independent
delivery and retained RSI require separately scored work. Atomic publication
alone does not close them.

### Historical persistence qualification — 2026-09-28

WSP15 C2/I4/D4/Impact4=14/P1 selects a six-case real-file characterization of the
existing scheduler. Preserve its source and reuse the current fixture: two
valid round-trip controls and four witnesses for typed response serialization,
unreadable replacement and future-schedule loss on reload. Scope is disposable
test data only. A green characterization can demonstrate a defect.

Candidate `e8e06ea86f` passed all 32 methods / 38 fixed inputs in [CI36390957294](https://github.com/FOUNDUPS/Foundups-Agent/actions/runs/36390957294), with zero failures/errors/skips. All six exact file-evidence records were verified: two valid controls and four serialization/reload defect witnesses. CI and CodeQL passed; final integrated-head and merged-main validation remain receipt-bound.

After exact hosted/main qualification and independent closure, re-observe and
rescore before selecting a production repair. A repair needs explicit durable
representation, previous-file preservation, load compatibility and save-failure
acknowledgement contracts; in-memory success is not a durable receipt.

### In-memory scheduler repair — closed 2026-09-28

PR1936 closed the qualification below:13/13 witnesses passed on the reviewed PR
and exact merged main `cd7e62d680`. Nine witnesses demonstrate misleading success;
the four controls do not establish external delivery. That 15/P1 in-memory repair is now closed. PR1941 is merged/main-verified at `6acb3f55c2`: the frozen26 methods/32 inputs passed on final PR CI36380808132 and main CI36381188667; both CodeQL runs passed. Its owned branch/worktree were retired after recovery preservation.

Freeze 26 methods/32 fixed input cases, then compare unchanged and repaired source
through the existing hosted CI owner. Reject unsupported actions and incomplete
or incoherent posting responses; preserve exact response objects and terminal
no-retry behavior. Validate and snapshot unique nonempty targets before effects.
Duplicate targets, including duplicates produced by overlapping natural-language
matches, reject explicitly rather than silently posting to a substituted list.
Baseline CI36379506634 confirms21 failing methods/27 assertion failures and5
passing controls with no errors/skips. The same26-method fixture is unchanged
for candidate validation: `9bc31ed6e0` passes all 26 methods/32 inputs in
CI36380266749, with0 failures/errors/skips and green CI/CodeQL. Final integrated
PR head/main convergence is recorded in the canonical backlog closure receipt.
Source review also tightened exact response/string types and preserved posting
classification across the await; those safeguards are source-reviewed, not
additional independent test scenarios. Durable save/replay, independent
delivery evidence, runtime admission and retained RSI remain separate.

### Scheduler evidence qualification — 2026-09-28

The historical phase checklist below is not a current whole-module completion
claim. RSI source review at `ab9ab47a8` found that logging-only action branches
report success, and `execute_pending_actions` marks any non-raising stream
response executed, including failure/partial/empty responses. These observations
must not feed verified-success or retained-learning metrics.

WSP 15 C2/I4/D4/Impact4 = **14/P1** selects a bounded qualification in the
existing scheduler test owner. Thirteen fixed cases exercise the unchanged leaf
behind inert dependencies and record action/result/error, awaited calls, save
requests and logs. The eight legacy test bodies remain unqualified. Hosted
execution and independent review are required before calling the observations
reproduced; preparation alone is not a test result.

Next, re-observe and select the smallest result-contract repair supported by
those observations. Preserve partial-result information and distinguish local
attempt completion, provider-reported success and independently verified effect.
Do not implement posting, a second scheduler or an outcome store as collateral
work. Persistence failures and external delivery remain separate qualifications.
See [test execution guidance](tests/README.md) and the
[canonical RSI queue](../../../docs/roadmaps/rsi_swarm_backlog.json).

**Phase**: Initial Implementation  
**WSP Compliance**: WSP 3, WSP 11, WSP 22, WSP 49  
**Created**: 2025-01-10

## Implementation Phases

### Phase 1: Foundation (CURRENT)
- [x] WSP 49 compliant module structure
- [x] Core architecture design
- [x] Interface documentation per WSP 11
- [ ] Core orchestrator implementation
- [ ] OAuth coordinator development
- [ ] Platform adapter framework
- [ ] Digital Twin comment routing into LinkedIn adapter (POC)

### Phase 2: Platform Integration
- [ ] Twitter adapter implementation using existing x_twitter module
- [ ] LinkedIn adapter consolidating linkedin_agent, linkedin_scheduler, linkedin_proxy
- [ ] Content orchestrator with cross-platform formatting
- [ ] Authentication flow unification

### Phase 3: Advanced Features
- [ ] Intelligent scheduling engine
- [ ] Cross-platform content optimization
- [ ] Analytics and metrics collection
- [ ] Advanced error handling and recovery

### Phase 4: Testing & Validation
- [ ] Hello World tests for both platforms
- [ ] Integration testing with existing modules
- [ ] Performance benchmarking
- [ ] WSP compliance validation

### Phase 5: Production Readiness
- [ ] Documentation completion
- [ ] Security audit
- [ ] Rate limiting and throttling
- [ ] Monitoring and alerting

## Key Objectives

### 1. WSP Violation Resolution
- **Problem**: LinkedIn module fragmentation violates WSP 3
- **Solution**: Unified orchestrator consolidating 3 LinkedIn modules into 1
- **Impact**: Cleaner architecture, easier maintenance

### 2. Redundancy Elimination
- **Problem**: Duplicate OAuth, scheduling, content logic across modules
- **Solution**: Shared components with single responsibility
- **Impact**: Code reuse, consistency, reduced bugs

### 3. Interface Standardization
- **Problem**: Empty INTERFACE.md files violate WSP 11
- **Solution**: Complete interface documentation with examples
- **Impact**: Better developer experience, clear contracts

### 4. Cross-Platform Harmony
- **Problem**: Inconsistent patterns between Twitter and LinkedIn modules
- **Solution**: Unified adapter pattern with consistent interfaces
- **Impact**: Predictable behavior, easier testing

## Technical Architecture

### Core Components
```
social_media_orchestrator/
+-- src/
[U+2502]   +-- social_media_orchestrator.py    # Main orchestration service
[U+2502]   +-- oauth_coordinator.py            # Unified OAuth management
[U+2502]   +-- content_orchestrator.py         # Content generation/formatting
[U+2502]   +-- scheduling_engine.py            # Advanced scheduling
[U+2502]   +-- platform_adapters/
[U+2502]       +-- twitter_adapter.py          # Twitter integration
[U+2502]       +-- linkedin_adapter.py         # LinkedIn integration
+-- tests/
[U+2502]   +-- test_twitter_hello_world.py     # Twitter basic functionality
[U+2502]   +-- test_linkedin_hello_world.py    # LinkedIn basic functionality
+-- memory/                             # Operational patterns
```

### Integration Strategy
1. **Gradual Migration**: Existing modules remain functional during transition
2. **Adapter Pattern**: Clean abstraction over existing implementations
3. **Backward Compatibility**: Maintain existing APIs where possible
4. **Test-Driven**: Hello World tests validate basic functionality

## Dependencies

### Internal
- `modules/platform_integration/x_twitter/` - Twitter implementation
- `modules/platform_integration/linkedin_*` - LinkedIn implementations (to be consolidated)
- `modules/ai_intelligence/banter_engine/` - Content generation
- `modules/infrastructure/oauth_management/` - Authentication infrastructure

### External
- `tweepy` - Twitter API client
- `linkedin-api` - LinkedIn API client
- `asyncio` - Asynchronous operations
- `aiohttp` - HTTP client for API calls

## Success Metrics

### Code Quality
- [ ] Zero WSP violations
- [ ] 100% interface documentation coverage
- [ ] Complete test coverage for hello world scenarios

### Functionality
- [ ] Twitter hello world test passes
- [ ] LinkedIn hello world test passes
- [ ] Cross-platform posting works
- [ ] OAuth flow unified

### Architecture
- [ ] LinkedIn module count reduced from 3 to 1
- [ ] Code duplication eliminated
- [ ] Consistent error handling across platforms

## Risk Mitigation

### Breaking Changes
- **Risk**: Existing LinkedIn integrations may break
- **Mitigation**: Adapter layer maintains compatibility, gradual migration

### Authentication Complexity
- **Risk**: Unifying different OAuth flows may introduce bugs
- **Mitigation**: Extensive testing, fallback mechanisms

### Performance Impact  
- **Risk**: Additional abstraction layer may slow operations
- **Mitigation**: Async design, connection pooling, performance monitoring

## Future Enhancements

### Additional Platforms
- YouTube integration
- Instagram/Meta platform support
- Discord/community platform support

### Advanced Features
- AI-powered content optimization
- Sentiment analysis and engagement prediction
- Advanced analytics dashboard
- Multi-account management

### WSP Evolution
- Integration with WSP 74 (Agentic Enhancement)
- WSP 75 (Token-Based Development) compliance
- Advanced modularization patterns

## Completion Criteria

1. [OK] WSP 49 structure implemented
2. [OK] Interface documentation complete
3. ⏳ Core orchestrator functional
4. ⏳ Twitter hello world test passes
5. ⏳ LinkedIn hello world test passes  
6. ⏳ OAuth coordinator operational
7. ⏳ ModLog updated per WSP 22
8. ⏳ Integration with existing modules validated

**Target Completion**: End of current development session  
**Next Review**: After Phase 2 completion
