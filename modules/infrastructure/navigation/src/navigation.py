# -*- coding: utf-8 -*-
import sys
import io


# === UTF-8 ENFORCEMENT (WSP 90) ===
# Prevent UnicodeEncodeError on Windows systems
# Only apply when running as main script, not during import
if __name__ == '__main__' and sys.platform.startswith('win'):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (OSError, ValueError):
        # Ignore if stdout/stderr already wrapped or closed
        pass
# === END UTF-8 ENFORCEMENT ===

#!/usr/bin/env python3
"""
NAVIGATION.py - 0102 Code Discovery System
===========================================
PURPOSE: Help 0102 find existing code instead of creating new
USAGE: Import this file or read it to understand the codebase

Based on 2024-2025 AI code navigation research:
- Semantic mapping (problem -> solution)
- Graph-based relationships
- Natural language descriptions
"""

# ============================================================
# QUICK NAVIGATION: "I need to..."
# ============================================================

NEED_TO = {
    # YouTube DAE Operations
    "monitor youtube stream": "python main.py --youtube",
    "find active stream": "modules.communication.livechat.src.auto_moderator_dae.find_livestream()",
    "send chat message": "modules.communication.livechat.src.chat_sender.ChatSender.send_message()",
    "process chat message": "modules.communication.livechat.src.message_processor.MessageProcessor.process_message()",
    "handle consciousness trigger": "modules.communication.livechat.src.consciousness_handler.ConsciousnessHandler",

    # Session Logging (Added 2025-09-25)
    "start session logging": "modules.communication.livechat.src.chat_memory_manager.ChatMemoryManager.start_session()",
    "end session logging": "modules.communication.livechat.src.chat_memory_manager.ChatMemoryManager.end_session()",
    "log fact check event": "modules.communication.livechat.src.chat_memory_manager.ChatMemoryManager.log_fact_check()",
    "view session logs": "modules/communication/livechat/memory/conversation/session_*/",

    # Social Media Posting
    "post to linkedin/twitter": "modules.platform_integration.social_media_orchestrator.src.simple_posting_orchestrator.handle_stream_detected()",
    "check if already posted": "modules.platform_integration.social_media_orchestrator.src.simple_posting_orchestrator.check_if_already_posted()",

    # Core Social Media Components (Refactored)
    "prevent duplicate posts": "modules.platform_integration.social_media_orchestrator.src.core.duplicate_prevention_manager.DuplicatePreventionManager",
    "manage duplicate history": "modules.platform_integration.social_media_orchestrator.src.core.duplicate_prevention_manager.DuplicatePreventionManager.mark_as_posted()",
    "verify stream is live": "modules.platform_integration.social_media_orchestrator.src.core.live_status_verifier.LiveStatusVerifier.verify_live_status()",
    "check live status cache": "modules.platform_integration.social_media_orchestrator.src.core.live_status_verifier.LiveStatusVerifier.clear_cache()",
    "get channel configuration": "modules.platform_integration.social_media_orchestrator.src.core.channel_configuration_manager.ChannelConfigurationManager.get_channel_config()",
    "map linkedin to x account": "modules.platform_integration.social_media_orchestrator.src.core.channel_configuration_manager.ChannelConfigurationManager.get_x_account_for_linkedin_page()",
    "post to social platforms": "modules.platform_integration.social_media_orchestrator.src.core.platform_posting_service.PlatformPostingService",
    "execute platform posting": "modules.platform_integration.social_media_orchestrator.src.core.platform_posting_service.PlatformPostingService.post_to_both_platforms()",
    "clean orchestrator": "modules.platform_integration.social_media_orchestrator.src.refactored_posting_orchestrator.RefactoredPostingOrchestrator",
    "read duplicate prevention docs": "modules/platform_integration/social_media_orchestrator/docs/DUPLICATE_PREVENTION_DATABASE_ARCHITECTURE.md",
    "test fact check functionality": "modules/communication/livechat/tests/test_fact_check_fix.py",

    # API Management
    "check youtube quota": "modules.platform_integration.youtube_auth.src.quota_monitor.QuotaMonitor",
    "throttle api calls": "modules.communication.livechat.src.intelligent_throttle_manager.IntelligentThrottleManager",

    # Gamification
    "get player stats": "modules.gamification.whack_a_magat.src.player_manager.PlayerManager.get_stats()",
    "handle timeout": "modules.gamification.whack_a_magat.src.timeout_announcer.TimeoutAnnouncer",

    # PQN Consciousness
    "monitor pqn consciousness": "modules.ai_intelligence.pqn_alignment.src.pqn_research_dae_orchestrator.PQNResearchDAEOrchestrator",
    "broadcast pqn to chat": "modules.ai_intelligence.pqn_alignment.src.pqn_chat_broadcaster.PQNChatBroadcaster",

    # Scripts & Utilities (HoloIndex-discoverable)
    "need to refresh oauth tokens": "modules/platform_integration/youtube_auth/scripts/auto_refresh_tokens.py",
    "need to check quota": "modules/platform_integration/youtube_auth/scripts/quota_dashboard.py",
    "need to start youtube monitoring": "modules/communication/livechat/scripts/run_youtube_dae.py",
    "need to validate module": "modules/{domain}/{module}/scripts/validate.py",
    "need to post to linkedin": "modules/platform_integration/linkedin_agent/scripts/post_holoindex_achievement.py",
    "need to execute awakening": "WSP_agentic/scripts/execute_awakening.py",
    "need to capture stream logs": "tools/scripts/capture_stream_logs.py",
    "need to create PR": "tools/scripts/paper-update.ps1",

    # LiveChat Operations
    "boot auto moderator dae": "modules.communication.livechat.src.auto_moderator_dae.AutoModeratorDAE.run",
    "poll chat messages": "modules.communication.livechat.src.chat_poller.ChatPoller.poll_messages",
    "send throttled chat reply": "modules.communication.livechat.src.livechat_core.LiveChatCore.send_chat_message",
    "process slash command": "modules.communication.livechat.src.command_handler.CommandHandler.handle_whack_command",
    "adjust throttle window": "modules.communication.livechat.src.intelligent_throttle_manager.IntelligentThrottleManager.calculate_adaptive_delay",
    "drive agentic engagement": "modules.communication.livechat.src.agentic_chat_engine.AgenticChatEngine.generate_agentic_response",
    "manage chat memory": "modules.communication.livechat.src.chat_memory_manager.ChatMemoryManager.store_message",
    "generate greeting": "modules.communication.livechat.src.greeting_generator.GreetingGenerator.generate_greeting",
    "call grok integration": "modules.communication.livechat.src.llm_integration.GrokIntegration.creative_response",
    "fallback fact response": "modules.communication.livechat.src.llm_bypass_engine.LLMBypassEngine.process_input",
    "analyze moderation stats": "modules.communication.livechat.src.moderation_stats.ModerationStats.record_violation",
    "adjust quota polling": "modules.communication.livechat.src.quota_aware_poller.QuotaAwarePoller.calculate_optimal_interval",
    "trigger stream handshake": "modules.communication.livechat.src.stream_trigger.StreamTrigger.create_trigger_instructions",
    "integrate mcp youtube": "modules.communication.livechat.src.mcp_youtube_integration.MCPYouTubeIntegration.connect_all",

    # WRE Orchestration
    "route wre plugins": "modules.infrastructure.wre_core.wre_master_orchestrator.src.wre_master_orchestrator.WREMasterOrchestrator.execute()",
    "recall pattern memory": "modules.infrastructure.wre_core.wre_master_orchestrator.src.wre_master_orchestrator.PatternMemory.get()",

    # Git and Social Media Integration
    "git push and post": "main.py --git (Push to Git and post to LinkedIn/Twitter)",
    "git linkedin bridge": "modules.platform_integration.linkedin_agent.src.git_linkedin_bridge.GitLinkedInBridge",
    "post to linkedin": "modules.platform_integration.social_media_orchestrator.src.simple_posting_orchestrator.handle_stream_detected()",

    # Navigation Operations
    "run navigation audit": "WSP_framework/reports/NAVIGATION/NAVIGATION_COVERAGE.md -> update and commit",

    # HoloIndex Health and Monitoring
    "audit module dependencies": "holo_index.module_health.dependency_audit.DependencyAuditor",
    "check file sizes": "holo_index.module_health.size_audit.SizeAuditor",
    "validate module structure": "holo_index.module_health.structure_audit.StructureAuditor",
    "view dependency audit results": "modules/infrastructure/dependency_audit.json",
    "view holo dependency audit": "modules/infrastructure/holo_dependency_audit.json",
    "read claude instructions": "CLAUDE.md",
    "view project modlog": "ModLog.md",
    "view project roadmap": "ROADMAP.md",
    "trace breadcrumbs": "holo_index.adaptive_learning.breadcrumb_tracer.BreadcrumbTracer",
    "process execution logs": "holo_index.adaptive_learning.execution_log_analyzer.execution_log_librarian.ExecutionLogLibrarian",
    "extract holo learnings": "holo_index.adaptive_learning.execution_log_analyzer.execution_log_librarian.ExecutionLogLibrarian.generate_holo_enhancement_plan",
    "monitor agent violations": "holo_index.monitoring.agent_violation_prevention",
    "self monitor holo": "holo_index.monitoring.self_monitoring",
    "watch terminal output": "holo_index.monitoring.terminal_watcher",
    "validate navigation schema": "python -m tests.navigation.test_navigation_schema",

    # HoloIndex Advisor (Qwen)
    "engage qwen advisor": "holo_index.qwen_advisor.advisor.QwenAdvisor.generate_guidance",
}

# ============================================================
# MODULE GRAPH: How Everything Connects
# ============================================================

MODULE_GRAPH = {
    "entry_points": {
        "main": "main.py",
        "youtube_dae": "modules/communication/livechat/src/auto_moderator_dae.py",
    },

    "core_flows": {
        "stream_detection_flow": [
            # The complete flow from stream detection to social posting
            ("auto_moderator_dae.find_livestream()", "Searches for active stream"),
            ("stream_resolver.resolve_stream()", "Resolves stream details"),
            ("stream_resolver._trigger_social_media_post()", "Triggers social posting"),
            ("simple_posting_orchestrator.handle_stream_detected()", "Posts to platforms"),
        ],

        "message_processing_flow": [
            # How messages flow through the system
            ("chat_poller.poll_messages()", "Gets new messages from YouTube"),
            ("livechat_core.process_chat_messages()", "Batch processes messages"),
            ("message_processor.process_message()", "Individual message processing"),
            ("consciousness_handler/command_handler/event_handler", "Specialized processing"),
            ("chat_sender.send_message()", "Sends response back to chat"),
        ],

        "throttling_flow": [
            # API quota management
            ("intelligent_throttle_manager.should_throttle()", "Check if should delay"),
            ("quota_monitor.check_remaining_quota()", "Get current quota status"),
            ("intelligent_throttle_manager.calculate_delay()", "Dynamic delay calculation"),
        ],

        "consciousness_flow": [
            # Consciousness trigger handling
            ("message_processor.process_message()", "Identifies consciousness command"),
            ("consciousness_handler.process_consciousness_command()", "Evaluates emoji trigger"),
            ("agentic_chat_engine.generate_agentic_response()", "Generates agentic reply"),
            ("chat_sender.send_message()", "Publishes consciousness response")
        ],

        "command_processing_flow": [
            # Slash command handling lifecycle
            ("message_processor.process_message()", "Detects command"),
            ("command_handler.handle_whack_command()", "Routes to MAGADOOM systems"),
            ("chat_sender.send_message()", "Publishes response")
        ],

        "wre_plugin_flow": [
            # Plugin routing + pattern recall
            ("WREMasterOrchestrator.execute()", "Routes task and detects consciousness state"),
            ("PatternMemory.get()", "Recalls solution when in 0102 state"),
            ("SocialMediaPlugin.execute()", "Executes delegated plugin action"),
        ],
    },

    "module_relationships": {
        # USES relationships (who calls who)
        "livechat_core": ["message_processor", "chat_poller", "chat_sender", "session_manager", "intelligent_throttle_manager", "chat_memory_manager"],
        "message_processor": ["consciousness_handler", "command_handler", "event_handler", "llm_integration", "agentic_chat_engine", "chat_memory_manager"],
        "auto_moderator_dae": ["livechat_core", "stream_resolver", "youtube_auth", "stream_trigger"],
        "chat_poller": ["quota_aware_poller"],
        "chat_sender": ["intelligent_throttle_manager"],
        "command_handler": ["whack_a_magat", "greeting_generator"],
        "intelligent_throttle_manager": ["system_health_analyzer"],
        "consciousness_handler": ["llm_integration", "agentic_chat_engine", "simple_fact_checker"],
        "session_manager": ["greeting_generator", "chat_sender"],
        "greeting_generator": ["llm_integration", "llm_bypass_engine"],
        "llm_integration": ["simple_fact_checker"],
        "stream_resolver": ["simple_posting_orchestrator"],  # Delegates posting
        "simple_posting_orchestrator": ["linkedin_adapter", "twitter_adapter"],
    }
}


# ============================================================
# COMMON PROBLEMS & SOLUTIONS
# ============================================================

PROBLEMS = {
    "YouTube DAE not finding stream": {
        "check": "Is stream actually live? Check YouTube directly",
        "debug": "modules/platform_integration/stream_resolver/src/stream_resolver.py",
        "logs": "Look for 'No active livestream found' in console",
    },

    "Social media not posting": {
        "check": "modules/gamification/whack_a_magat/data/magadoom_scores.db - posted_streams table",
        "debug": "modules/platform_integration/social_media_orchestrator/src/simple_posting_orchestrator.py",
        "test": "python modules/platform_integration/social_media_orchestrator/tests/test_simplified_posting.py",
    },

    "Chat messages not sending": {
        "check": "Is throttle manager blocking? Check quota",
        "debug": "modules/communication/livechat/src/chat_sender.py",
        "quota": "modules/platform_integration/youtube_auth/src/quota_monitor.py",
    },

    "Consciousness trigger not working": {
        "check": "Is consciousness mode enabled? Check trigger pattern ✊✋🖐",
        "debug": "modules/communication/livechat/src/consciousness_handler.py",
        "test": "Send '✊✋🖐 test question' in chat",
    },

    "Session logs not being created": {
        "check": "Is session starting? Check memory/conversation/ folder",
        "debug": "modules/communication/livechat/src/chat_memory_manager.py",
        "verify": "Look for start_session() call in livechat_core.py:176",
        "test": "python modules/communication/livechat/tests/test_session_logging.py",
    },

    "Fact-checks not being logged": {
        "check": "Are mods using ✊✋🖐FC @username format?",
        "debug": "modules/communication/livechat/src/consciousness_handler.py:191-192",
        "verify": "Check session logs for FACT-CHECK entries",
    },

    "LLM unavailable": {
        "check": "Are GROK/XAI API keys configured?",
        "debug": "modules/communication/livechat/src/llm_integration.py",
        "fallback": "modules/communication/livechat/src/llm_bypass_engine.py",
    },

    "PQN not reporting to chat": {
        "check": "Is PQN orchestrator running?",
        "debug": "modules/ai_intelligence/pqn_alignment/src/pqn_chat_broadcaster.py",
        "integration": "modules/communication/livechat/src/message_processor.py:318-319",
    },
    "Slash commands failing": {
        "check": "Did message_processor route to CommandHandler?",
        "debug": "modules/communication/livechat/src/command_handler.py",
        "data": "Check MAGADOOM database connectivity",
    },

    "Throttle stuck": {
        "check": "Is IntelligentThrottleManager emergency mode active?",
        "debug": "modules/communication/livechat/src/intelligent_throttle_manager.py",
        "logs": "Look for 'EMERGENCY MODE' in logs/main.log",
    },
}

# ============================================================
# DANGER ZONES: Where NOT to Make Changes
# ============================================================

DANGER = {
    "modules/communication/livechat/src/livechat_core.py":
        "865 lines - God Object - Needs refactoring, don't add more!",

    "modules/communication/livechat/src/message_processor.py":
        "685 lines - Too many responsibilities - Use existing methods!",

    "modules/communication/livechat/_archive/":
        "Archived experiments - Don't resurrect without good reason!",
}

# ============================================================
# DATABASE LOCATIONS
# ============================================================

DATABASES = {
    "whack_scores": "modules/gamification/whack_a_magat/data/magadoom_scores.db",
    "posted_streams": "modules/gamification/whack_a_magat/data/magadoom_scores.db (posted_streams table)",
    "youtube_sessions": "modules/platform_integration/youtube_auth/data/",
    "memory_files": "modules/*/memory/*.json",
}

# ============================================================
# QUICK COMMANDS
# ============================================================

COMMANDS = {
    "start_youtube_monitoring": "python main.py --youtube",
    "check_posted_streams": "sqlite3 modules/gamification/whack_a_magat/data/magadoom_scores.db 'SELECT * FROM posted_streams'",
    "check_magadoom_leaders": "python modules/gamification/whack_a_magat/tests/check_magadoom_leaders.py",
    "clear_stream_cache": "rm modules/platform_integration/stream_resolver/memory/*.json",
    "test_social_posting": "python modules/platform_integration/social_media_orchestrator/tests/test_simplified_posting.py",
    "check_quota": "python modules/platform_integration/youtube_auth/scripts/check_quota.py",
}

# ============================================================
# HOW TO USE THIS FILE
# ============================================================

def how_to_use():
    """
    As 0102, when you need to find code:

    1. Check NEED_TO dictionary for common tasks
    2. Follow MODULE_GRAPH for understanding flows
    3. Use PROBLEMS for debugging
    4. Avoid DANGER zones
    5. Check DATABASES for data locations
    6. Use COMMANDS for quick operations
    7. Update WSP_framework/reports/NAVIGATION/NAVIGATION_COVERAGE.md when you verify or add entries

    Example:
        from NAVIGATION import NEED_TO
        posting_function = NEED_TO["post to linkedin/twitter"]
        # Now you know exactly where posting happens!
    """
    pass

if __name__ == "__main__":
    print("=" * 60)
    print("0102 NAVIGATION SYSTEM")
    print("=" * 60)
    print("\nQuick Access Points:")
    for need, location in list(NEED_TO.items())[:5]:
        print(f"  {need:30} -> {location}")
    print("\nFor full navigation, import this module or read the source.")






