#!/usr/bin/env python3
"""
NAVIGATION.py - WSP 87 Code Navigation Protocol Implementation

This file maps problems to existing solutions to prevent vibecoding.
0102 agents MUST consult this file BEFORE creating any new code.

Status: ACTIVE curated map - Holo semantic retrieval remains fail-closed when stale
Last Updated: 2026-08-29 - Added inert RedDog query-runtime builder authority components
WSP Compliance: WSP 87 (Code Navigation), WSP 50 (Pre-Action Verification)

COVERAGE:
- ✅ GotJunk FoundUp (classification, location, storage)
- ✅ AI Intelligence (telemetry monitoring, event processing)
- ✅ Infrastructure (WSP orchestration, MCP management, WRE skills)
- ✅ HoloDAE Coordination (Qwen/Gemma agents, autonomous refactoring)
- ✅ Member Area (auth state, dashboard shell, navigation)

ACHIEVEMENTS:
- ✅ Surgical debugging: 93% token reduction, 80% time savings vs grep
- ✅ Code extraction: Actual TypeScript snippets from .tsx files
- ✅ Module detection: Correctly identifies all major domains
- ✅ Expanded coverage: 10 → 40+ semantic mappings
"""

# === NEED_TO: Problem -> Solution Mapping ===
# Direct mapping of problems to existing code solutions
NEED_TO = {
    # GotJunk Classification Logic
    "handle item classification": "modules/foundups/gotjunk/frontend/App.tsx:handleClassify()",
    "prevent duplicate item creation": "modules/foundups/gotjunk/frontend/App.tsx:handleClassify() - race condition guards",
    "race condition in classification": "modules/foundups/gotjunk/frontend/App.tsx:handleClassify() - isProcessingClassification guard",
    "onClassify event handling": "modules/foundups/gotjunk/frontend/components/ClassificationModal.tsx:onClassify prop",
    "classification modal duplicate prevention": "modules/foundups/gotjunk/frontend/App.tsx:pendingClassificationItem state management",

    # Generic duplicate prevention (existing implementations)
    "duplicate item prevention": "modules/platform_integration/social_media_orchestrator/src/core/duplicate_prevention_manager.py",
    "social media duplicate posting": "modules/platform_integration/social_media_orchestrator/src/core/duplicate_prevention_manager.py:DuplicatePreventionManager.mark_as_posted()",

    # Other common patterns
    "user location detection": "modules/foundups/gotjunk/frontend/App.tsx:getCurrentPositionPromise()",
    "geolocation with fallback": "modules/foundups/gotjunk/frontend/App.tsx:initializeApp() - location handling",
    "react state race conditions": "modules/foundups/gotjunk/frontend/App.tsx:handleClassify() - immediate state clearing",

    # FoundUps Cube Animation (Landing Page Visual)
    "cube animation rendering foundups": "public/js/foundup-cube.js - Full 4x4x4 cube animation with phases",
    "canvas cube isometric three.js": "public/js/foundup-cube.js - Canvas-based isometric cube rendering",
    "scaffolding wireframe building phases": "public/js/foundup-cube.js:drawPlanningCube() - IDEA/SCAFFOLD phase rendering",
    "cube block filling animation": "public/js/foundup-cube.js:fillRandomBlock() - Block materialize with particles",
    "cube agent rendering movement": "public/js/foundup-cube.js:drawAgents() - Founder/Builder/Promoter/Investor agents",
    "cube phase lifecycle IDEA SCAFFOLD BUILDING": "public/js/foundup-cube.js:PHASES - 120s animation loop",
    "cube ticker live chat messages": "public/js/foundup-cube.js:drawTicker() - Scrolling event messages",
    "cube ecosystem multi-cube zoom": "public/js/foundup-cube.js:drawEcosystemView() - Multiple cubes view",
    "cube WSP importance colors P0-P4": "public/js/foundup-cube.js:getWSPImportanceColor() - Red/Orange/Yellow/Green/Blue",
    "cube SSE simulator integration": "public/js/foundup-cube.js:initSSE() - Server-Sent Events bridge",

    # FoundUps Website - Member Area (Layer 1 Shell)
    "member area dashboard": "public/member/index.html - Authenticated member dashboard shell",
    "member area auth state": "public/member/index.html - Firebase onAuthStateChanged listener",
    "member area navigation": "public/member/index.html - Hash-based section routing (#dashboard, #wallet, etc.)",
    "member area styles": "public/member/css/member.css - Dark theme, glassmorphism, responsive",
    "invite code display member": "public/member/index.html - renderInviteCodes() with copy functionality",
    "member logout signout": "public/member/index.html - Firebase signOut() with redirect",
    "landing page signup redirect": "public/index.html - Redirects to /member/ after successful signup",
    "member area roadmap layers": "public/member/ROADMAP.md - Layer 1-6 module progression",

    # FoundUps Simulator (Mesa Model + SSE)
    "simulator mesa model foundups": "modules/foundups/simulator/mesa_model.py:FoundUpsModel - Agent-based simulation",
    "simulator SSE server events": "modules/foundups/simulator/sse_server.py - FastAPI SSE streaming to web animation",
    "simulator background run in-process": "modules/foundups/simulator/sse_server.py:BackgroundSimulator - Mesa in background thread",
    "simulator event bus FAM bridge": "modules/foundups/simulator/event_bus.py:EventBus - FAMDaemon event normalization",
    "simulator state store renderable": "modules/foundups/simulator/state_store.py:StateStore - Event-derived render state",
    "simulator founder agent qwen AI": "modules/foundups/simulator/agents/founder_agent.py:FounderAgent - Creates FoundUps",
    "simulator user agent gemma AI": "modules/foundups/simulator/agents/user_agent.py:UserAgent - Likes/stakes/follows",
    "simulator token economics engine": "modules/foundups/simulator/economics/token_economics.py - WSP 26 economic flow",
    "simulator deploy cloud run SSE": "modules/foundups/simulator/deploy-sse.sh - Cloud Run deployment script",
    "simulator cube view ASCII terminal": "modules/foundups/simulator/render/cube_view.py:CubeView - 3D ASCII cube animation",
    "simulator synthetic personas research": "modules/foundups/simulator/docs/SYNTHETIC_PERSONAS_RESEARCH.md - Simile AI market simulation integration",
    "synthetic user simulation AI": "modules/foundups/simulator/docs/SYNTHETIC_PERSONAS_RESEARCH.md - Pre-launch adoption testing with AI personas",
    "simile AI integration plan": "modules/foundups/simulator/docs/SYNTHETIC_PERSONAS_RESEARCH.md - $100M synthetic humanity company",
    "synthetic user agent": "modules/foundups/simulator/agents/synthetic_user_agent.py:SyntheticUserAgent - AI-generated user adoption simulation",
    "synthetic persona dataclass": "modules/foundups/simulator/agents/synthetic_user_agent.py:SyntheticPersona - Demographics, risk tolerance, pain points",
    "adoption decision evaluation": "modules/foundups/simulator/agents/synthetic_user_agent.py:AdoptionDecision - Would persona adopt? Confidence, reasons",
    "animation DRIVEN mode": "public/js/foundup-cube.js:FLAGS.DRIVEN_MODE - Simulator controls animation phases",
    "animation command API": "public/js/foundup-cube.js:command() - Direct control interface (setPhase, stateSync, etc.)",

    # FoundUps Agent Market (Outer Layer)
    "foundups agent market outer layer": "modules/foundups/agent_market/README.md",
    "foundup registry contract": "modules/foundups/agent_market/INTERFACE.md:FoundupRegistryService",
    "task proof verify payout pipeline": "modules/foundups/agent_market/src/in_memory.py:InMemoryAgentMarket",
    "task lifecycle open claimed submitted verified paid": "modules/foundups/agent_market/src/models.py:TaskStatus",
    "verified milestone distribution publish": "modules/foundups/agent_market/src/in_memory.py:InMemoryAgentMarket.publish_verified_milestone()",
    "agent market schema tests": "modules/foundups/agent_market/tests/test_schemas.py",
    "agent market permission checks": "modules/foundups/agent_market/tests/test_permissions.py",
    "openclaw execution arm foundup launch": "modules/foundups/agent_market/ARCHITECTURE.md",
    "openclaw dae frontal lobe": "modules/communication/moltbot_bridge/src/openclaw_dae.py:OpenClawDAE",
    "openclaw intent classification": "modules/communication/moltbot_bridge/src/openclaw_dae.py:OpenClawDAE.classify_intent()",
    "gemma intent classifier": "modules/communication/moltbot_bridge/src/gemma_intent_classifier.py:GemmaIntentClassifier",
    "openclaw gemma hybrid classification": "modules/communication/moltbot_bridge/src/gemma_intent_classifier.py:GemmaIntentClassifier.classify()",
    "openclaw permission gate": "modules/communication/moltbot_bridge/src/openclaw_dae.py:OpenClawDAE._check_permission_gate()",
    "openclaw autonomy tiers": "modules/communication/moltbot_bridge/src/openclaw_dae.py:OpenClawDAE._resolve_autonomy_tier()",
    "openclaw source tier permission": "modules/communication/moltbot_bridge/src/openclaw_dae.py:OpenClawDAE._check_source_permission()",
    "openclaw file path extraction": "modules/communication/moltbot_bridge/src/openclaw_dae.py:OpenClawDAE._extract_file_paths()",
    "openclaw source modification detection": "modules/communication/moltbot_bridge/src/openclaw_dae.py:OpenClawDAE._is_source_modification()",
    "openclaw execution command gate": "modules/communication/moltbot_bridge/src/openclaw_dae.py:OpenClawDAE._execute_command()",
    "agent permission manager": "modules/ai_intelligence/agent_permissions/src/agent_permission_manager.py:AgentPermissionManager",
    "agent permission check": "modules/ai_intelligence/agent_permissions/src/agent_permission_manager.py:AgentPermissionManager.check_permission()",
    "agent confidence tracker": "modules/ai_intelligence/agent_permissions/src/confidence_tracker.py:ConfidenceTracker",
    "openclaw security sentinel": "modules/ai_intelligence/ai_overseer/src/openclaw_security_sentinel.py:OpenClawSecuritySentinel",
    "openclaw skill safety guard": "modules/communication/moltbot_bridge/src/skill_safety_guard.py:SkillSafetyGuard",
    "openclaw honeypot defense": "modules/communication/moltbot_bridge/src/openclaw_dae.py:HoneypotDefense",
    "openclaw fam adapter": "modules/communication/moltbot_bridge/src/fam_adapter.py:FAMAdapter",
    "openclaw foundup launch": "modules/communication/moltbot_bridge/src/fam_adapter.py:FAMAdapter.launch_foundup()",
    "openclaw webhook receiver": "modules/communication/moltbot_bridge/src/webhook_receiver.py",
    "openclaw install setup": "modules/communication/moltbot_bridge/docs/INSTALL_OPENCLAW.md",
    "openclaw security tests": "modules/ai_intelligence/ai_overseer/tests/test_openclaw_security_sentinel.py",
    "openclaw dae tests": "modules/communication/moltbot_bridge/tests/test_openclaw_dae.py",
    "moltbot bridge digital twin": "modules/communication/moltbot_bridge/README.md",
    "reddog holo exact main postmerge controller": "modules/communication/moltbot_bridge/src/holoindex_postmerge_runtime_controller.py:run_holoindex_postmerge_runtime_once()",
    "reddog holo postmerge cli": "scripts/reddog_holoindex_postmerge_runtime_once.py",
    "reddog holo postmerge completion policy": "modules/communication/moltbot_bridge/src/holoindex_postmerge_supervisor_policy.py:validate_supervisor_holoindex_postmerge_completion()",
    "reddog holo query builder authority receipt": "modules/infrastructure/foundups_mcp_bridge/src/reddog_holoindex_query_runtime_builder_contract.py:builder_authority_receipt()",
    "reddog holo query builder process proof": "modules/infrastructure/foundups_mcp_bridge/src/reddog_holoindex_query_runtime_builder_process.py:prove_builder_process_authority()",
    "reddog holo query builder packaging proof": "modules/infrastructure/foundups_mcp_bridge/src/reddog_holoindex_query_runtime_builder_packaging.py:prove_builder_packaging_authority()",
    "reddog holo query builder packaging wheel admission": "modules/infrastructure/foundups_mcp_bridge/src/reddog_holoindex_query_runtime_builder_packaging_wheel.py:admit_pinned_builder_packaging_wheel()",
    "reddog holo query builder packaging source generation": "modules/infrastructure/foundups_mcp_bridge/src/reddog_holoindex_query_runtime_builder_packaging_source_materializer.py:materialize_pinned_builder_packaging_source()",
    "reddog holo query builder packaging source verification": "modules/infrastructure/foundups_mcp_bridge/src/reddog_holoindex_query_runtime_builder_packaging_source_verifier.py:verify_builder_packaging_source_generation()",
    "reddog holo query builder packaging source topology": "modules/infrastructure/foundups_mcp_bridge/src/reddog_holoindex_query_runtime_builder_packaging_source_topology_windows.py:pinned_builder_packaging_source_generation()",
    "reddog holo query builder pinned git proof": "modules/infrastructure/foundups_mcp_bridge/src/reddog_holoindex_query_runtime_builder_git.py:prove_pinned_git_authority()",
    "reddog holo query builder source proof": "modules/infrastructure/foundups_mcp_bridge/src/reddog_holoindex_query_runtime_builder_source.py:prove_builder_source_authority()",
    "reddog holo query builder scale proof": "modules/infrastructure/foundups_mcp_bridge/tests/test_reddog_holoindex_query_runtime_builder_scale.py",
    "reddog main readonly operational bootstrap": "modules/communication/moltbot_bridge/src/reddog_main_readonly_operational_bootstrap.py:run_reddog_main_readonly_operational_bootstrap()",
    "reddog main bootstrap result projection": "modules/communication/moltbot_bridge/src/reddog_main_readonly_operational_bootstrap_result.py:RedDogMainReadonlyBootstrapResult",
    "reddog authority profile typed rehydration": "modules/communication/moltbot_bridge/src/reddog_authority_profile_rehydration.py:rehydrate_authority_profile_runtime()",
    "reddog authenticated conversation scope": "modules/communication/moltbot_bridge/src/reddog_authenticated_conversation_scope_state.py",
    "reddog resident conversation request scope binding": "modules/communication/moltbot_bridge/src/reddog_resident_conversation_scope_binding.py:bind_resident_conversation_request_to_authenticated_scope()",
    "reddog resident conversation request idempotency": "modules/communication/moltbot_bridge/src/reddog_resident_conversation_request_journal.py:reserve_bound_resident_conversation_request()",
    "reddog resident conversation request journal store": "modules/communication/moltbot_bridge/src/reddog_resident_conversation_request_journal_store.py:AgentDbResidentConversationRequestJournal",
    "reddog resident conversation admission proof": "modules/communication/moltbot_bridge/src/reddog_conversation_scope_capability.py:consume_verified_scope_authority_for_request_journal()",
    "reddog current conversation session authority": "modules/communication/moltbot_bridge/src/reddog_conversation_session_authority_source.py:lease_current_generation_conversation_session()",
    "reddog trusted new conversation scope resolution": "modules/communication/moltbot_bridge/src/reddog_resident_conversation_new_scope_resolution.py:resolve_resident_conversation_new_scope_request()",
    "reddog current session new conversation scope admission": "modules/communication/moltbot_bridge/src/reddog_resident_conversation_new_scope_admission.py:create_current_generation_resident_conversation_scope()",
    "reddog durable first turn resolution link": "modules/communication/moltbot_bridge/src/reddog_resident_conversation_first_turn_resolution.py:resolve_current_generation_resident_conversation_first_turn()",
    "reddog first turn resolution contract": "modules/communication/moltbot_bridge/src/reddog_resident_conversation_first_turn_contract.py",
    "reddog current session conversation admission": "modules/communication/moltbot_bridge/src/reddog_resident_conversation_admission.py:reserve_current_generation_resident_conversation_request()",
    "moltbot bridge workspace skills": "modules/communication/moltbot_bridge/workspace/AGENTS.md",

    # M2M Compression (Machine-to-Machine 0102-0102 Documentation)
    "m2m compression scan batch promote": ".claude/skills/m2m/SKILL.md - /m2m skill commands",
    "m2m compression sentinel analysis": "modules/ai_intelligence/ai_overseer/src/m2m_compression_sentinel.py:M2MCompressionSentinel",
    "m2m compiler compress docs": "prompt/swarm/m2m_compiler.py - Doc compression for 0102 consumption",
    "m2m compression cache history": "modules/ai_intelligence/ai_overseer/memory/m2m_compression_cache.json",

    # AI Intelligence & Monitoring
    "monitor telemetry from HoloDAE": "modules/ai_intelligence/ai_overseer/src/holo_telemetry_monitor.py:HoloTelemetryMonitor",
    "tail JSONL telemetry logs": "modules/ai_intelligence/ai_overseer/src/holo_telemetry_monitor.py:HoloTelemetryMonitor.tail_log()",
    "ai overseer coordinate mission": "modules/ai_intelligence/ai_overseer/src/ai_overseer.py:AIIntelligenceOverseer.coordinate_mission()",
    "ai overseer check false positive": "modules/ai_intelligence/ai_overseer/src/ai_overseer.py:AIIntelligenceOverseer._is_known_false_positive()",
    "ai overseer record false positive": "modules/ai_intelligence/ai_overseer/src/ai_overseer.py:AIIntelligenceOverseer.record_false_positive()",
    "ricDAE MCP integration": "modules/ai_intelligence/ric_dae/src/mcp_tools.py:ResearchIngestionMCP",

    # Infrastructure & Orchestration
    "wsp orchestration": "modules/infrastructure/wsp_orchestrator/src/wsp_orchestrator.py:WSPOrchestrator",
    "coordinate qwen and gemma agents": "modules/infrastructure/wsp_orchestrator/src/wsp_orchestrator.py:WSPOrchestrator.route_to_agent()",
    "mcp server management": "modules/infrastructure/mcp_manager/src/mcp_manager.py:MCPManager",
    "auto-start mcp servers": "modules/infrastructure/mcp_manager/src/mcp_manager.py:MCPManager.ensure_server_running()",
    "codex lifecycle hooks": "modules/infrastructure/codex_hooks/src/codex_hooks.py:dispatch_hook()",
    "codex prompt secret guard": "modules/infrastructure/codex_hooks/src/codex_hooks.py:handle_user_prompt_submit()",
    "codex tool safety guard": "modules/infrastructure/codex_hooks/src/codex_hooks.py:handle_pre_tool_use()",
    "wre skills loading": "modules/infrastructure/wre_core/skillz/wre_skills_loader.py:WRESkillsLoader",
    "progressive disclosure for skills": "modules/infrastructure/wre_core/skillz/wre_skills_loader.py:WRESkillsLoader.load_skill_on_demand()",
    "skillz wardrobe": "modules/infrastructure/wre_core/skillz/wre_skills_loader.py:WRESkillsLoader - Wardrobe Skills = advanced prompting system (see WSP 96)",
    "wardrobe skills": "modules/infrastructure/wre_core/skillz/wre_skills_loader.py:WRESkillsLoader - Like clothing outfits the agent wears for specific tasks",
    "load skillz": "modules/infrastructure/wre_core/skillz/wre_skills_loader.py:WRESkillsLoader.load_skill_on_demand()",
    "wre skillz protocol": "WSP_framework/src/WSP_95_WRE_SKILLz_Wardrobe_Protocol.md - Micro Chain-of-Thought paradigm (canonical WSP 95)",
    "wre fmas finding contract": "modules/infrastructure/wre_core/src/fmas_finding_contract.py:FMASFinding",
    "wre wsp62 finding parser": "modules/infrastructure/wre_core/src/fmas_wsp62_contract.py:parse_wsp62_finding_text()",
    "wre wsp62 health audit": "modules/infrastructure/wre_core/src/fmas_health_triage.py:run_wsp62_health_audit()",
    "wre improvement job contract": "modules/infrastructure/wre_core/src/improvement_job_contract.py:ImprovementJob",
    "reddog improvement direction": "modules/infrastructure/wre_core/src/reddog_direction.py:RedDogDirector",

    # Centralized DAEmon (Cardiovascular System)
    "centralized daemon monitoring": "modules/infrastructure/dae_daemon/src/dae_daemon.py:CentralDAEmon",
    "dae registration heartbeat": "modules/infrastructure/dae_daemon/src/dae_registry.py:DAERegistry",
    "security killswitch detach": "modules/infrastructure/dae_daemon/src/killswitch.py:Killswitch",
    "dae event store dual-write": "modules/infrastructure/dae_daemon/src/event_store.py:DAEEventStore",
    "dae adapter non-invasive": "modules/infrastructure/dae_daemon/src/dae_adapter.py:CentralDAEAdapter",
    "dae dashboard centralized switch": "modules/infrastructure/cli/src/main_menu.py:_run_dae_dashboard()",
    "enable disable dae": "modules/infrastructure/dae_daemon/src/dae_daemon.py:CentralDAEmon.enable_dae()",

    # WSP Compliance & Pattern Memory
    "scan wsp violations": "modules/infrastructure/wsp_core/src/wsp_compliance_checker.py:WSPComplianceChecker.scan()",
    "check false positives": "modules/infrastructure/wsp_core/src/wsp_compliance_checker.py:WSPComplianceChecker._is_known_false_positive()",
    "pattern memory false positives": "modules/infrastructure/wre_core/src/pattern_memory.py:PatternMemory.is_false_positive()",
    "record learned false positive": "modules/infrastructure/wre_core/src/pattern_memory.py:PatternMemory.record_false_positive()",
    "github wsp automation": "modules/platform_integration/github_integration/src/wsp_automation.py:WSPAutomationManager",
    "wsp_00 zen state tracker": "modules/infrastructure/monitoring/src/wsp_00_zen_state_tracker.py",
    "wsp_00 awakening script": "WSP_agentic/scripts/functional_0102_awakening_v2.py",

    # Digital Twin (Core Components)
    "digital twin resident conversation transport": "modules/ai_intelligence/digital_twin/src/resident_conversation_transport_contract.py:request_from_mapping()",
    "digital twin voice memory": "modules/ai_intelligence/digital_twin/src/voice_memory.py:VoiceMemory",
    "build voice memory index": "modules/ai_intelligence/digital_twin/src/voice_memory.py:VoiceMemory.build_index()",
    "query voice memory": "modules/ai_intelligence/digital_twin/src/voice_memory.py:VoiceMemory.query()",
    "digital twin comment drafter": "modules/ai_intelligence/digital_twin/src/comment_drafter.py:CommentDrafter",
    "draft comment in 012 voice": "modules/ai_intelligence/digital_twin/src/comment_drafter.py:CommentDrafter.draft()",
    "digital twin local llm": "modules/ai_intelligence/digital_twin/src/comment_drafter.py:LocalLLM",
    "digital twin decision policy": "modules/ai_intelligence/digital_twin/src/decision_policy.py:DecisionPolicy",
    "decide comment action": "modules/ai_intelligence/digital_twin/src/decision_policy.py:DecisionPolicy.decide()",
    "digital twin style guardrails": "modules/ai_intelligence/digital_twin/src/style_guardrails.py:StyleGuardrails",
    "enforce style guardrails": "modules/ai_intelligence/digital_twin/src/style_guardrails.py:StyleGuardrails.enforce()",
    "nemo guardrails adapter": "modules/ai_intelligence/digital_twin/src/style_guardrails.py:get_nemo_guardrails()",
    "trajectory logging": "modules/ai_intelligence/digital_twin/src/trajectory_logger.py:TrajectoryLogger",
    "log draft trajectory": "modules/ai_intelligence/digital_twin/src/trajectory_logger.py:TrajectoryLogger.log_draft()",
    "log decision trajectory": "modules/ai_intelligence/digital_twin/src/trajectory_logger.py:TrajectoryLogger.log_decision()",
    "log action trajectory": "modules/ai_intelligence/digital_twin/src/trajectory_logger.py:TrajectoryLogger.log_action()",
    "digital twin schemas": "modules/ai_intelligence/digital_twin/src/schemas.py:CommentDraft",
    "digital twin tool plan schema": "modules/ai_intelligence/digital_twin/src/schemas.py:ToolPlan",
    "digital twin voice memory result schema": "modules/ai_intelligence/digital_twin/src/schemas.py:VoiceMemoryResult",
    "digital twin lora trainer": "modules/ai_intelligence/digital_twin/src/lora_trainer.py:VoiceLoRATrainer",
    "digital twin lora config": "modules/ai_intelligence/digital_twin/src/lora_trainer.py:VoiceTrainingConfig",
    "digital twin lora data converter": "modules/ai_intelligence/digital_twin/src/lora_data_converter.py:convert_sft_to_chatml()",
    "digital twin lora convert all": "modules/ai_intelligence/digital_twin/src/lora_data_converter.py:convert_all()",
    "add document to voice memory": "modules/ai_intelligence/digital_twin/src/voice_memory.py:VoiceMemory.add_document()",
    "voice memory stats": "modules/ai_intelligence/digital_twin/src/voice_memory.py:VoiceMemory.get_stats()",
    "holoindex video search integration": "modules/ai_intelligence/digital_twin/src/voice_memory.py:_get_video_index() - Lazy loads VideoContentIndex",

    # Digital Twin (Comment Drafter - RAG + LLM + Guardrails pipeline)
    "comment drafter production": "modules/ai_intelligence/digital_twin/src/comment_drafter.py:CommentDrafter.production() - Factory for full pipeline",
    "comment drafter local llm": "modules/ai_intelligence/digital_twin/src/comment_drafter.py:LocalLLM.generate() - Qwen 1.5B text generation",
    "comment entity correction": "modules/ai_intelligence/digital_twin/src/comment_drafter.py:LocalLLM._correct_entities() - Fix LLM name mistakes",

    # Digital Twin (Style Guardrails)
    "style guardrails enforce": "modules/ai_intelligence/digital_twin/src/style_guardrails.py:StyleGuardrails.enforce()",
    "style guardrails validate": "modules/ai_intelligence/digital_twin/src/style_guardrails.py:StyleGuardrails.is_valid()",

    # Digital Twin (Decision Policy - comment/reply/skip logic)
    "comment decision policy": "modules/ai_intelligence/digital_twin/src/decision_policy.py:DecisionPolicy.decide()",
    "estimate comment relevance": "modules/ai_intelligence/digital_twin/src/decision_policy.py:DecisionPolicy.estimate_relevance()",
    "estimate comment toxicity": "modules/ai_intelligence/digital_twin/src/decision_policy.py:DecisionPolicy.estimate_toxicity()",

    # Digital Twin (Schemas)
    "comment action enum": "modules/ai_intelligence/digital_twin/src/schemas.py:CommentAction - reply/like/heart/skip",
    "platform enum": "modules/ai_intelligence/digital_twin/src/schemas.py:Platform - youtube/linkedin/x",

    # Digital Twin (Trajectory Logger - audit trail)
    "trajectory logger": "modules/ai_intelligence/digital_twin/src/trajectory_logger.py:TrajectoryLogger",
    "log draft decision": "modules/ai_intelligence/digital_twin/src/trajectory_logger.py:TrajectoryLogger.log_draft()",
    "log action result": "modules/ai_intelligence/digital_twin/src/trajectory_logger.py:TrajectoryLogger.log_action()",

    # HoloDAE Coordination
    "holodae query processing": "holo_index/qwen_advisor/holodae_coordinator.py:HoloDAECoordinator.handle_holoindex_request()",
    "holodae filter false positives": "holo_index/qwen_advisor/holodae_coordinator.py:HoloDAECoordinator._filter_false_positive_results()",
    "qwen strategic analysis": "holo_index/qwen_advisor/holodae_coordinator.py:HoloDAECoordinator.qwen_analyze_context()",
    "qwen autonomous refactoring": "holo_index/qwen_advisor/orchestration/autonomous_refactoring.py:AutonomousRefactoringOrchestrator",
    "gemma pattern validation": "holo_index/qwen_advisor/orchestration/autonomous_refactoring.py:AutonomousRefactoringOrchestrator.gemma_validate_patterns()",

    # Browser Automation & Vision (Sprint A1, V4 complete) - ENHANCED: Multi-tier vision with UI-TARS + Gemini
    "route browser action": "modules/infrastructure/browser_actions/src/action_router.py:ActionRouter.execute()",
    "check driver availability": "modules/infrastructure/browser_actions/src/action_router.py:ActionRouter._ensure_vision()",
    "classify action complexity": "modules/infrastructure/browser_actions/src/action_router.py:ActionRouter.get_driver_for_action()",
    "multi-tier vision routing": "modules/infrastructure/browser_actions/src/action_router.py:ActionRouter._ensure_vision() - Tier 1 UI-TARS → Tier 2 Gemini fallback",
    "initialize ui-tars bridge": "modules/infrastructure/browser_actions/src/action_router.py:ActionRouter._ensure_ui_tars() - Local vision on LM Studio port 1234",
    "initialize gemini vision": "modules/infrastructure/browser_actions/src/action_router.py:ActionRouter._ensure_gemini_vision() - Cloud vision fallback",
    "multi-driver support": "modules/infrastructure/browser_actions/src/action_router.py:DriverType - SELENIUM, TARS, GEMINI, VISION, PLAYWRIGHT",
    "ui-tars bridge connect": "modules/infrastructure/foundups_vision/src/ui_tars_bridge.py:UITarsBridge.connect()",
    "vision executor workflow": "modules/infrastructure/foundups_vision/src/vision_executor.py:VisionExecutor.execute_workflow()",

    # Browser Session Management (Sprint V4 - migrated to foundups_selenium)
    "get browser instance": "modules/infrastructure/foundups_selenium/src/browser_manager.py:BrowserManager.get_browser()",
    "reuse browser session": "modules/infrastructure/foundups_selenium/src/browser_manager.py:BrowserManager.get_browser()",
    "browser singleton manager": "modules/infrastructure/foundups_selenium/src/browser_manager.py:get_browser_manager()",
    "close browser session": "modules/infrastructure/foundups_selenium/src/browser_manager.py:BrowserManager.close_browser()",
    "chrome profile management": "modules/infrastructure/foundups_selenium/src/browser_manager.py:BrowserManager._create_chrome_browser()",
    "youtube browser profile": "modules/infrastructure/foundups_selenium/src/browser_manager.py:BrowserManager._create_chrome_browser() - youtube_move2japan profile",

    # DAE Dependency Launcher (auto-start Chrome + LM Studio)
    "ensure dae dependencies": "modules/infrastructure/dependency_launcher/src/dae_dependencies.py:ensure_dependencies()",
    "launch chrome debug port": "modules/infrastructure/dependency_launcher/src/dae_dependencies.py:launch_chrome()",
    "launch lm studio": "modules/infrastructure/dependency_launcher/src/dae_dependencies.py:launch_lm_studio()",
    "check dependency status": "modules/infrastructure/dependency_launcher/src/dae_dependencies.py:get_dependency_status()",
    "chrome debug port 9222": "modules/infrastructure/dependency_launcher/src/dae_dependencies.py:is_chrome_running()",
    "lm studio port 1234": "modules/infrastructure/dependency_launcher/src/dae_dependencies.py:is_lm_studio_running()",

    # Pattern Learning (Sprint V6)
    "action pattern learning": "modules/infrastructure/foundups_vision/src/action_pattern_learner.py:ActionPatternLearner",
    "pattern learner singleton": "modules/infrastructure/foundups_vision/src/action_pattern_learner.py:get_learner()",
    "record action success": "modules/infrastructure/foundups_vision/src/action_pattern_learner.py:ActionPatternLearner.record_success()",
    "record action failure": "modules/infrastructure/foundups_vision/src/action_pattern_learner.py:ActionPatternLearner.record_failure()",
    "adaptive retry strategy": "modules/infrastructure/foundups_vision/src/action_pattern_learner.py:ActionPatternLearner.get_retry_strategy()",
    "recommend driver": "modules/infrastructure/foundups_vision/src/action_pattern_learner.py:ActionPatternLearner.recommend_driver()",
    "ab test drivers": "modules/infrastructure/foundups_vision/src/action_pattern_learner.py:ActionPatternLearner.start_ab_test()",
    "pattern metrics": "modules/infrastructure/foundups_vision/src/action_pattern_learner.py:ActionPatternLearner.get_metrics()",
    "record human validation": "modules/infrastructure/foundups_vision/src/action_pattern_learner.py:ActionPatternLearner.record_human_validation()",
    "012 feedback recommendations": "modules/infrastructure/foundups_vision/src/action_pattern_learner.py:ActionPatternLearner.get_012_recommendations()",
    "pre action learning display": "modules/infrastructure/foundups_vision/src/action_pattern_learner.py:ActionPatternLearner.display_pre_learning()",
    "post action learning display": "modules/infrastructure/foundups_vision/src/action_pattern_learner.py:ActionPatternLearner.display_post_learning()",

    # Documentation & Architecture (NEW - 2025-12-03)
    "daemon architecture": "docs/DAEMON_ARCHITECTURE_MAP.md - Complete daemon inventory and event queue design",
    "event queue orchestration": "docs/DAEMON_ARCHITECTURE_MAP.md - Unified event queue architecture",
    "daemon coordination": "docs/DAEMON_ARCHITECTURE_MAP.md - Inter-daemon communication patterns",
    "holodae gitpushdae youtube daemons": "docs/DAEMON_ARCHITECTURE_MAP.md - All daemon capabilities mapped",
    "git push social media flow": "docs/GIT_SOCIAL_MEDIA_EVENT_DRIVEN_ARCHITECTURE.md - Event-driven posting architecture",
    "architecture documentation index": "docs/README.md - Central catalog of all architecture docs",
    "session reports": "docs/README.md - Completed work sessions and sprints",
    "vision automation sprints": "docs/VISION_AUTOMATION_SPRINT_MAP.md - Vision automation roadmap (A1-A5, V1-V6)",

    # Testing & Validation (NEW - 2025-12-05)
    "test youtube studio vision": "modules/communication/video_comments/skillz/qwen_studio_engage/tests/ - Vision automation test suite",
    "test qwen studio engage": "modules/communication/video_comments/skillz/qwen_studio_engage/tests/test_qwen_studio_engage.py - Full autonomous flow test",
    "test gemini vision": "modules/communication/video_comments/skillz/qwen_studio_engage/tests/test_gemini_simple.py - Gemini Vision button detection",

    # WRE Skills - Autonomous Engagement (NEW - 2025-12-05)
    "autonomous youtube engagement": "modules/communication/video_comments/skillz/qwen_studio_engage/ - Agentic Studio comment engagement",
    "youtube studio skillz": "modules/communication/video_comments/skillz/qwen_studio_engage/SKILLz.md - Qwen+Gemma autonomous engagement",
    "studio comment like reply": "modules/communication/video_comments/skillz/qwen_studio_engage/executor.py - Vision-based engagement execution",
    "youtube studio ui reference": "modules/communication/video_comments/skillz/qwen_studio_engage/VISION_UI_REFERENCE.md - Precise Vision targeting",

    # YouTube Live Audio (Phase 1: Loopback, Phase 2: Archive) - NEW 2026-01-07
    "youtube live audio capture": "modules/platform_integration/youtube_live_audio/src/youtube_live_audio.py:SystemAudioCapture",
    "system audio loopback": "modules/platform_integration/youtube_live_audio/src/youtube_live_audio.py:SystemAudioCapture - WASAPI loopback capture",
    "youtube audio source": "modules/platform_integration/youtube_live_audio/src/youtube_live_audio.py:YouTubeLiveAudioSource",
    "stream audio chunks": "modules/platform_integration/youtube_live_audio/src/youtube_live_audio.py:YouTubeLiveAudioSource.stream_audio_chunks()",
    "video archive extractor": "modules/platform_integration/youtube_live_audio/src/youtube_live_audio.py:VideoArchiveExtractor",
    "list channel videos": "modules/platform_integration/youtube_live_audio/src/youtube_live_audio.py:VideoArchiveExtractor.list_channel_videos() - 0 API quota",
    "extract audio from video": "modules/platform_integration/youtube_live_audio/src/youtube_live_audio.py:VideoArchiveExtractor.extract_audio()",
    "stream video chunks": "modules/platform_integration/youtube_live_audio/src/youtube_live_audio.py:VideoArchiveExtractor.stream_video_chunks()",
    "audio chunk timestamp": "modules/platform_integration/youtube_live_audio/src/youtube_live_audio.py:AudioChunk.timestamp_ms - Video position for deep linking",

    # Voice Command Ingestion (STT + Batch Transcription) - NEW 2026-01-07
    "faster whisper stt": "modules/communication/voice_command_ingestion/src/voice_command_ingestion.py:FasterWhisperSTT",
    "transcribe audio whisper": "modules/communication/voice_command_ingestion/src/voice_command_ingestion.py:FasterWhisperSTT.transcribe()",
    "voice trigger detection": "modules/communication/voice_command_ingestion/src/voice_command_ingestion.py:TriggerDetector",
    "detect 0102 trigger": "modules/communication/voice_command_ingestion/src/voice_command_ingestion.py:TriggerDetector.detect() - Handles '0102' variations",
    "voice command ingestion": "modules/communication/voice_command_ingestion/src/voice_command_ingestion.py:VoiceCommandIngestion",
    "batch transcriber": "modules/communication/voice_command_ingestion/src/voice_command_ingestion.py:BatchTranscriber",
    "transcribe channel videos": "modules/communication/voice_command_ingestion/src/voice_command_ingestion.py:BatchTranscriber.transcribe_channel()",
    "transcript segment": "modules/communication/voice_command_ingestion/src/voice_command_ingestion.py:TranscriptSegment - video_id, timestamp, text, url",
    "save transcripts jsonl": "modules/communication/voice_command_ingestion/src/voice_command_ingestion.py:BatchTranscriber.save_transcripts_jsonl()",
    "what did 012 say": "modules/communication/voice_command_ingestion/src/voice_command_ingestion.py:TranscriptSegment.url - Deep link to exact video moment",

    # Transcript Index (Sprint 7-8) - Semantic Search for Digital Twin - NEW 2026-01-07
    "video transcript index": "modules/communication/voice_command_ingestion/src/transcript_index.py:VideoTranscriptIndex",
    "transcript semantic search": "modules/communication/voice_command_ingestion/src/transcript_index.py:VideoTranscriptIndex.search()",
    "index transcripts jsonl": "modules/communication/voice_command_ingestion/src/transcript_index.py:VideoTranscriptIndex.index_from_jsonl()",
    "search 012 transcripts": "modules/communication/voice_command_ingestion/src/transcript_index.py:search_012_transcripts() - MCP-compatible",
    "digital twin query": "modules/communication/voice_command_ingestion/src/transcript_index.py:search_012_transcripts() - What did 012 say about X?",

    # YouTube Channel Indexing (Menu Integration) - NEW 2026-01-08
    "youtube indexing": "modules/communication/voice_command_ingestion/scripts/index_channel.py:index_channel()",
    "index youtube channel": "modules/communication/voice_command_ingestion/scripts/index_channel.py:index_channel(channel_key, max_videos)",
    "index move2japan": "modules/communication/voice_command_ingestion/scripts/index_channel.py:index_channel('move2japan')",
    "index undaodu": "modules/communication/voice_command_ingestion/scripts/index_channel.py:index_channel('undaodu')",
    "index foundups": "modules/communication/voice_command_ingestion/scripts/index_channel.py:index_channel('foundups')",
    "youtube indexing menu": "modules/communication/voice_command_ingestion/scripts/index_channel.py:run_indexing_menu() - main.py option 1.8",
    "search video transcripts": "modules/communication/voice_command_ingestion/scripts/index_channel.py:search_transcripts(query)",
    # Video Indexer (Multimodal Content Intelligence) - NEW 2026-01-08
    "video indexer": "modules/ai_intelligence/video_indexer/src/video_indexer.py:VideoIndexer",
    "index video content": "modules/ai_intelligence/video_indexer/src/video_indexer.py:VideoIndexer.index_video()",
    "index channel videos": "modules/ai_intelligence/video_indexer/src/video_indexer.py:VideoIndexer.index_channel()",
    "search video content": "modules/ai_intelligence/video_indexer/src/video_indexer.py:VideoIndexer.search()",
    "audio analysis diarization": "modules/ai_intelligence/video_indexer/src/audio_analyzer.py:AudioAnalyzer",
    "extract video quotes": "modules/ai_intelligence/video_indexer/src/audio_analyzer.py:AudioAnalyzer.extract_quotes()",
    "identify video topics": "modules/ai_intelligence/video_indexer/src/audio_analyzer.py:AudioAnalyzer.identify_topics()",
    "visual frame analysis": "modules/ai_intelligence/video_indexer/src/visual_analyzer.py:VisualAnalyzer",
    "detect video shots": "modules/ai_intelligence/video_indexer/src/visual_analyzer.py:VisualAnalyzer.detect_shots()",
    "extract keyframes": "modules/ai_intelligence/video_indexer/src/visual_analyzer.py:VisualAnalyzer.extract_keyframes()",
    "multimodal alignment": "modules/ai_intelligence/video_indexer/src/multimodal_aligner.py:MultimodalAligner",
    "align audio visual moments": "modules/ai_intelligence/video_indexer/src/multimodal_aligner.py:MultimodalAligner.align_moments()",
    "detect video highlights": "modules/ai_intelligence/video_indexer/src/multimodal_aligner.py:MultimodalAligner.detect_highlights()",
    "generate clip candidates": "modules/ai_intelligence/video_indexer/src/clip_generator.py:ClipGenerator.generate_candidates()",
    "score viral potential": "modules/ai_intelligence/video_indexer/src/clip_generator.py:ClipGenerator._score_virality()",
    "video index storage": "modules/ai_intelligence/video_indexer/src/video_index_store.py:VideoIndexStore",

    # RedDog extension lane (012-facing)
    "foundups agent extension Copy MD Work Trail Run Trace": "extensions/reddog/extension.js",
    "foundups advisory workers extension Copy MD": "extensions/reddog/extension.js",
    "buildCopyMarkdown Redaction Gate Report Governed Handoff": "extensions/reddog/extension.js:buildCopyMarkdown symbol",
    "extension.js WSP_97 truth label compliance review": "extensions/reddog/extension.js",
    "RedDog external worker acceptance baseline": "extensions/reddog/docs/REDDOG_EXTERNAL_ACCEPTANCE_BASELINE_PHASE1.md",
    "advisory_model_once redaction gate bridge OpenRouter": "scripts/advisory_model_once.py",
    "Foundups Agent OpenRouter bridge redaction": "scripts/advisory_model_once.py",
}

# === MODULE_GRAPH: Module Relationships ===
MODULE_GRAPH = {
    "entry_points": {
        "gotjunk_main": "modules/foundups/gotjunk/frontend/App.tsx",
        "classification_flow": "modules/foundups/gotjunk/frontend/components/ClassificationModal.tsx",
        "ai_overseer": "modules/ai_intelligence/ai_overseer/src/ai_overseer.py",
        "holo_telemetry": "modules/ai_intelligence/ai_overseer/src/holo_telemetry_monitor.py",
        "holodae_coordinator": "holo_index/qwen_advisor/holodae_coordinator.py",
        "wsp_orchestrator": "modules/infrastructure/wsp_orchestrator/src/wsp_orchestrator.py",
    },

    "core_flows": [
        # GotJunk flows
        ("capture_photo", "modules/foundups/gotjunk/frontend/App.tsx:handleCapture()"),
        ("show_classification_modal", "modules/foundups/gotjunk/frontend/components/ClassificationModal.tsx"),
        ("handle_classification", "modules/foundups/gotjunk/frontend/App.tsx:handleClassify()"),
        ("save_to_storage", "modules/foundups/gotjunk/frontend/services/storage.ts"),

        # AI Intelligence flows
        ("tail_telemetry", "modules/ai_intelligence/ai_overseer/src/holo_telemetry_monitor.py:tail_log()"),
        ("process_ai_event", "modules/ai_intelligence/ai_overseer/src/ai_overseer.py:process_event()"),
        ("queue_event", "modules/ai_intelligence/ai_overseer/src/ai_overseer.py:queue_event()"),

        # HoloDAE coordination flows
        ("handle_holoindex_request", "holo_index/qwen_advisor/holodae_coordinator.py:handle_holoindex_request()"),
        ("qwen_analyze", "holo_index/qwen_advisor/holodae_coordinator.py:qwen_analyze_context()"),
        ("autonomous_refactor", "holo_index/qwen_advisor/orchestration/autonomous_refactoring.py"),

        # Infrastructure flows
        ("route_to_agent", "modules/infrastructure/wsp_orchestrator/src/wsp_orchestrator.py:route_to_agent()"),
        ("ensure_mcp_server", "modules/infrastructure/mcp_manager/src/mcp_manager.py:ensure_server_running()"),
        ("load_skill_on_demand", "modules/infrastructure/wre_core/skillz/wre_skills_loader.py:load_skill_on_demand()"),
    ],

    "module_relationships": {
        # GotJunk relationships
        "App.tsx": ["ClassificationModal.tsx", "storage.ts", "useViewport.ts"],
        "ClassificationModal.tsx": ["types.ts", "ActionSheetDiscount.tsx", "ActionSheetBid.tsx"],

        # AI Intelligence relationships
        "ai_overseer.py": ["holo_telemetry_monitor.py", "event_processor.py"],
        "holo_telemetry_monitor.py": ["ai_overseer.py"],

        # HoloDAE relationships
        "holodae_coordinator.py": ["pid_detective.py", "mcp_integration.py", "telemetry_formatter.py", "module_metrics.py", "monitoring_loop.py"],

        # Infrastructure relationships
        "wsp_orchestrator.py": ["mcp_manager.py", "wre_core"],
        "mcp_manager.py": ["mcp_servers"],
    }
}

# === PROBLEMS: Common Issues & Solutions ===
PROBLEMS = {
    "duplicate_classification_calls": {
        "symptoms": "Items created multiple times, race conditions",
        "debug": "Check isProcessingClassification flag and pendingClassificationItem state",
        "solution": "Use immediate state clearing + processing guard in handleClassify()",
        "location": "modules/foundups/gotjunk/frontend/App.tsx:handleClassify()"
    },

    "missing_location_data": {
        "symptoms": "Items saved without GPS coordinates",
        "debug": "Check navigator.geolocation permissions and error handling",
        "solution": "Use getCurrentPositionPromise() with proper fallbacks",
        "location": "modules/foundups/gotjunk/frontend/App.tsx:getCurrentPositionPromise()"
    },
}

# === WSP 27: DAE Architecture (Updated v2.0) ===
DAE_ARCHITECTURE = {
    "DAE definition": "WSP_framework/src/WSP_27_pArtifact_DAE_Architecture.md - Section 1: DAE = agentic entangled state executing Skills",
    "what is a DAE": "WSP_framework/src/WSP_27_pArtifact_DAE_Architecture.md - Section 1: Decentralized Autonomous Entity/Ecosystem",
    "rubik cube module model": "WSP_framework/src/WSP_27_pArtifact_DAE_Architecture.md - Section 1.1: Cube = modules forming a FoundUp, colors = WSP 15 MPS",
    "skills wardrobe IBM typewriter ball": "WSP_framework/src/WSP_27_pArtifact_DAE_Architecture.md - Section 1.2: Agents dress up in Skills (WSP 95)",
    "foundup creation 0-1-2 philosophy": "WSP_framework/src/WSP_27_pArtifact_DAE_Architecture.md - Section 2.2: 0=Pain, 1=Solution, 2=Outcome",
    "foundup vs startup": "WSP_framework/src/WSP_27_pArtifact_DAE_Architecture.md - Section 2.2: StartUp monetizes problems, FoundUp SOLVES problems",
    "four phase DAE cycle": "WSP_framework/src/WSP_27_pArtifact_DAE_Architecture.md - Section 2: -1 Signal, 0 Knowledge, 1 Protocol, 2 Agentic",
    "foundup evolution poc prototype mvp": "WSP_framework/src/WSP_27_pArtifact_DAE_Architecture.md - Section 2.4: Occam's Layers + WSP 30 build orchestration",
    "modular build framework": "WSP_framework/src/WSP_30_Agentic_Module_Build_Orchestration.md - PoC->Prototype->MVP with LLME progression",
    "occam layer building discipline": "WSP_framework/src/WSP_27_pArtifact_DAE_Architecture.md - Section 2.4: Simplest layer first, test, feedback, next layer",
    "WRE recursive engine": "WSP_framework/src/WSP_46_Windsurf_Recursive_Engine_Protocol.md - Central module building engine",
    "skills wardrobe protocol": "WSP_framework/src/WSP_95_WRE_SKILLz_Wardrobe_Protocol.md - Skills = executable instructions agents dress up in",
    "MPS priority scoring colors": "WSP_framework/src/WSP_15_Module_Prioritization_Scoring_System.md - P0 Red through P4 Blue",

    # WSP 26: Token Economics
    "UPS token conversion escape valve": "WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md - Section 3.7: UPS→FoundUp token conversion stops decay",
    "Gesell Freigeld demurrage": "WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md - Section 2: Economic Heritage (Gesell 1916, Worgl 1932)",
    "token decay formula": "WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md - Section 3.5: V(t) = V0 * e^(-lambda*t)",
    "BTC distributed reserve": "WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md - Section 4: Micro-wallet per FoundUp, BTC never leaves, decay frees backing",
    "BTC backing capacity model": "WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md - Section 4.4: Decay frees BTC for new UPS minting",
    "wallet implementation build on existing": "WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md - Section 4.3: MPC threshold sigs, BIP-32, not custom wallet",
    "agent wallet manager 0102": "WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md - Section 4.5: 0102 manages wallet on behalf of 012",
    "transaction fee revenue model": "WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md - Section 4.6: Fees on staking/unstaking/cash-out grow BTC reserve",
    "token release by tier": "WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md - Section 4.7: Staged release 0%-100% by FoundUp tier",
    "7 tier foundup classification": "WSP_framework/src/WSP_27_pArtifact_DAE_Architecture.md - Section 11: Tier 7 Genesis through Tier 1 Sovereign",
    "foundup tier progression factors": "WSP_framework/src/WSP_27_pArtifact_DAE_Architecture.md - Section 11.2: Weighted composite (swarm, CABR, tasks, revenue)",
    "adoption curve foundup tiers": "WSP_framework/src/WSP_27_pArtifact_DAE_Architecture.md - Section 11.4: Rogers diffusion mapped to Tier 7-1",
    "delegate emergent leadership": "WSP_framework/src/WSP_27_pArtifact_DAE_Architecture.md - Section 11.5: Headless FoundUp, delegates emerge at Tier 5+",
    "headless foundup governance": "WSP_framework/src/WSP_27_pArtifact_DAE_Architecture.md - Section 11.5: Founder starts as head, math distributes governance",
    "0102 agent experience platform": "WSP_framework/src/WSP_27_pArtifact_DAE_Architecture.md - Section 12: Placeholder (post-MVP) - agent XP, twin fidelity, roles",
    "twin fidelity digital twin": "WSP_framework/src/WSP_27_pArtifact_DAE_Architecture.md - Section 12.1: 0102 learns from 012, 97.5% = entangled twin (post-MVP detail)",
    "openclaw launch paradigm": "WSP_framework/src/WSP_27_pArtifact_DAE_Architecture.md - Section 12.2: Humans watch AI build, earn tokens, stake into FoundUps",
    "foundup death sunset protocol": "WSP_framework/src/WSP_27_pArtifact_DAE_Architecture.md - Section 13: 3-phase sunset (WARNING→WIND-DOWN→DISSOLUTION)",
    "play foundups dapp": "WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md - Section 4.5: 012 asks 0102 to discover and stake in FoundUps",

    # WSP 26: Token Pool Distribution Model
    "token pool distribution UN DAO DU": "WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md - Section 6: 80/20 stakeholder/network, UN/DAO/DU participant types",
    "three participant types 0 1 2": "WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md - Section 6.1: UN(0)=passive, DAO(1)=active, DU(2)=founder",
    "universal basic dividend": "WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md - Section 6.7: UN pool (60%) = dividend for geofenced beneficiaries",
    "participant classification CABR": "WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md - Section 6.5: Activity-based classification, not title-based",
    "geofenced foundup": "WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md - Section 6.1: Geographic proximity = automatic UN status",
    "inactive founder earnings": "WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md - Section 6.4: DU with un-activity earns only 4% of total pool",

    # WSP 29: CABR Engine
    "CABR oracle specification": "WSP_framework/src/WSP_29_CABR_Engine.md - Section 2: Oracle tiers T1-T4 for env/soc/part scores",
    "CABR FAM UPS minting bridge": "WSP_framework/src/WSP_29_CABR_Engine.md - Section 3: task completion → CABR → mint UPS",
    "dMRV integration": "WSP_framework/src/WSP_29_CABR_Engine.md - Section 2.5: Digital MRV Framework 3.0 attestation",
    "participation score definition": "WSP_framework/src/WSP_29_CABR_Engine.md - Section 2.4: FAM-derived part_score components",
    "anti-sybil agent identity": "WSP_framework/src/WSP_29_CABR_Engine.md - Section 6: Layered Sybil defense (L1-L5)",
    # WSP 26: 21M Token Model + Subscription + Blockchain (v3.0)
    "21M token model every foundup bitcoin": "WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md - Section 4.7.1: 21M fixed supply per FoundUp, divisible to 8 decimals",
    "ubiquitous gateway any token BTC": "WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md - Section 4.8: Any token → converted to BTC inside ecosystem",
    "subscription tiers freemium premium": "WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md - Section 4.9: Free→Spark($2.95)→Explorer($9.95)→Builder($19.95)→Founder($49.95)",
    "earned UPS vs allocated UPS": "WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md - Section 4.9: Labor (task completion) + Investment (subscription)",
    "engagement funnel CABR signals": "WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md - Section 4.10: Follow→Vote→Stake→Endorse→Advise→Team→Promote",
    "blockchain architecture 3 layer": "WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md - Section 4.11: Bitcoin(L0) + Algorand(L1) + Off-chain(L2)",
    "algorand quantum resistant falcon": "WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md - Section 4.11: Falcon-1024 NIST signatures, 10K TPS, State Proofs",
    "foundup token exit reverse conversion": "WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md - Section 3.7: FoundUp token→UPS costly (2-5% fee + decay resumes)",
    "no portfolio cap UPS is the cap": "WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md - Section 4.9: No artificial limit, stake wherever you have UPS",
    "subscription revenue BTC flywheel": "WSP_framework/src/WSP_26_FoundUPS_DAE_Tokenization.md - Section 4.9: Subscription→BTC reserve→backs UPS→self-reinforcing",

    # WSP 27: OBAI + Circular Lifecycle + Recursive Spawning (v3.0)
    "OBAI open beneficial AI 0102": "WSP_framework/src/WSP_27_pArtifact_DAE_Architecture.md - Section 1.4: OBAI = 0102 = Verification/Validation/Valuation Engine",
    "existing modules are foundups": "WSP_framework/src/WSP_27_pArtifact_DAE_Architecture.md - Section 1.5: Move2Japan, YT automation, PQN, LinkedIn = first FoundUps",
    "circular lifecycle OIF diagram": "WSP_framework/src/WSP_27_pArtifact_DAE_Architecture.md - Section 11.0: IDEA→PoC→TEAM→Soft-Proto→Proto→MVP→smartDAO→spawns IDEAS",
    "smartDAO open corp tier 1": "WSP_framework/src/WSP_27_pArtifact_DAE_Architecture.md - Section 11.0/11.1: Sovereign FoundUp = smartDAO fully autonomous",
    "crowdfunding phases tier transitions": "WSP_framework/src/WSP_27_pArtifact_DAE_Architecture.md - Section 11.0: Passive CF, CF1 (Tier 5→4), CF2 (Tier 3→2)",
    "recursive foundup spawning": "WSP_framework/src/WSP_27_pArtifact_DAE_Architecture.md - Section 14: Sovereign DAE spawns child FoundUps, cycle repeats",
    "21M tokens per tier release": "WSP_framework/src/WSP_27_pArtifact_DAE_Architecture.md - Section 11.1: Tier table with 21M token counts per stage",

    # WSP 29: CABR = OBAI
    "CABR is OBAI 0102 network": "WSP_framework/src/WSP_29_CABR_Engine.md - Overview: 0102s verify/validate/value = self-governing through math",

    # FAM (FoundUps Agent Market)
    "FAM task pipeline": "modules/foundups/agent_market/INTERFACE.md - open→claimed→submitted→verified→paid",
    "FAM launch orchestrator": "modules/foundups/agent_market/INTERFACE.md - LaunchOrchestrator.launch_foundup()",

    # MVP: Play FoundUps dApp
    "netflix foundup marketplace tiles": "WSP_framework/src/WSP_27_pArtifact_DAE_Architecture.md - Section 12.2: Netflix grid, 92s pitch videos, geofencing, GotJunk template",
    "gotjunk PWA template marketplace": "modules/foundups/gotjunk/ - React PWA with tile grid, map, geolocation, 50km geofence",
}

# === DANGER: Areas Requiring Caution ===
DANGER = {
    "modules/foundups/gotjunk/frontend/App.tsx:handleClassify()": "Race condition prone - always check isProcessingClassification before processing",
    "modules/foundups/gotjunk/frontend/App.tsx:pendingClassificationItem": "Must be cleared immediately to prevent duplicate processing",
}

# === DATABASES: Data Storage Locations ===
DATABASES = {
    "gotjunk_items": "IndexedDB via modules/foundups/gotjunk/frontend/services/storage.ts",
    "user_preferences": "localStorage in ClassificationModal.tsx",
}

# === SESSION BRIEFINGS: Architecture State Summaries for 0102 Continuity ===
SESSION_BRIEFINGS = {
    "2026-02-07 prototype architecture": "docs/0102_session_briefings/SESSION_BRIEFING_2026_02_07.md",
    "session briefing 0102 onboarding digest": "docs/0102_session_briefings/SESSION_BRIEFING_2026_02_07.md",
    "21M token blockchain OBAI circular lifecycle MVP marketplace summary": "docs/0102_session_briefings/SESSION_BRIEFING_2026_02_07.md",
}

# === COMMANDS: Operational Commands ===
COMMANDS = {
    "search_code": "python holo_index.py --search 'query'",
    "index_navigation": "python holo_index.py --index-code",
}
