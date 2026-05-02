"""
IDE FoundUps - WRE Command Router

Bridges IDE commands to the Windsurf Recursive Engine orchestration system,
enabling 0102 agents to process IDE requests through the autonomous WRE infrastructure.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from pathlib import Path
import json
from datetime import datetime

# WSP 97 Truth: wre_log fallback for when tools.wre is unavailable
def _wre_log_fallback(message: str, level: str = "INFO") -> None:
    """Fallback wre_log that uses standard logging."""
    logger = logging.getLogger("wre_ide_fallback")
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.log(log_level, f"[WRE-IDE] {message}")


try:
    # WSP 97 Truth: Try canonical wre_log first
    from tools.wre.tools.logging_utils import wre_log
except (ImportError, FileNotFoundError, OSError):
    # WSP 97: Truthful fallback - catches import errors and filesystem side-effects
    wre_log = _wre_log_fallback

try:
    # WSP 97 Truth: WRE orchestration components
    from modules.infrastructure.wre_core.wre_master_orchestrator.src.wre_master_orchestrator import (
        WREMasterOrchestrator as AgenticOrchestrator,
    )
    from modules.infrastructure.agent_activation.src.agent_activation import AgentActivationModule
    WRE_AVAILABLE = True
except ImportError as e:
    # WSP 97: Truthful logging of import failure - no silent fallback
    logging.warning(f"[WRE-IDE] Import seam failed: {e}")
    WRE_AVAILABLE = False
    AgenticOrchestrator = None  # Explicit None for truthful unavailability
    AgentActivationModule = None

class WRECommandRouter:
    """
    Routes IDE commands through the WRE orchestration system.
    
    This router transforms IDE-originated commands into WRE orchestration
    requests, enabling 0102 agents to handle development tasks autonomously.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.wre_orchestrator = None
        self.agent_activation = None
        self.active_agents = {}
        self.command_history = []
        self.session_id = f"IDE_Session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Initialize WRE integration if available
        if WRE_AVAILABLE:
            self._initialize_wre_integration()
        else:
            self.logger.warning("WRE integration unavailable - operating in fallback mode")
    
    def _initialize_wre_integration(self):
        """Initialize WRE orchestration components"""
        try:
            # Initialize WRE orchestrator
            self.wre_orchestrator = AgenticOrchestrator()
            
            # Initialize agent activation system
            self.agent_activation = AgentActivationModule()
            
            # Log successful integration
            wre_log("[LINK] IDE FoundUps WRE Command Router initialized", "SUCCESS")
            self.logger.info("WRE integration active - ready for 0102 agent coordination")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize WRE integration: {e}")
            self.wre_orchestrator = None
            self.agent_activation = None
    
    async def route_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route IDE command through WRE orchestration system.
        
        Args:
            command: IDE command structure with type, parameters, and context
            
        Returns:
            WRE orchestration result with agent coordination details
        """
        if not WRE_AVAILABLE or not self.wre_orchestrator:
            return await self._handle_fallback_command(command)
        
        try:
            # Log command routing
            wre_log(f"[REFRESH] IDE Command routed to WRE: {command.get('type', 'unknown')}", "INFO")
            
            # Ensure 0102 agents are activated
            await self._ensure_agent_activation()
            
            # Transform IDE command to WRE orchestration context
            orchestration_context = self._transform_command_to_context(command)
            
            # Execute through WRE orchestration
            result = await self.wre_orchestrator.orchestrate_recursively(orchestration_context)
            
            # Log successful execution
            wre_log("[OK] IDE Command executed successfully through WRE", "SUCCESS")
            
            # Transform result back to IDE format
            return self._transform_result_to_ide(result, command)
            
        except Exception as e:
            self.logger.error(f"WRE command routing failed: {e}")
            wre_log(f"[FAIL] IDE Command routing error: {e}", "ERROR")
            return await self._handle_fallback_command(command)
    
    async def _ensure_agent_activation(self):
        """Ensure 0102 agents are activated for IDE operations"""
        if not self.agent_activation:
            return
        
        try:
            # Check if agents need activation
            if not self.active_agents:
                wre_log("[ROCKET] Activating 0102 agents for IDE operations", "INFO")
                
                # Activate WSP 54 agents for IDE coordination
                activation_result = self.agent_activation.activate_wsp54_agents([])
                
                if activation_result:
                    self.active_agents = activation_result
                    wre_log("[OK] 0102 agents activated for IDE operations", "SUCCESS")
                else:
                    wre_log("[U+26A0]️ Agent activation incomplete - proceeding with available agents", "WARNING")
                    
        except Exception as e:
            wre_log(f"[FAIL] Agent activation failed: {e}", "ERROR")
    
    def _transform_command_to_context(self, command: Dict[str, Any]) -> Any:
        """Transform IDE command to WRE orchestration context"""
        # WSP 97 Truth: OrchestrationContext/OrchestrationTrigger are legacy components
        # not yet implemented. Use dict-based context until migration complete.
        # No silent fallback - dict context is the canonical interface for now.
        return {
            "trigger": command.get('type', 'general_development'),
            "session_id": self.session_id,
            "zen_flow_state": "0102",
            "parameters": command.get('parameters', {}),
            "source": "IDE_FoundUps",
            "metadata": {
                "ide_command": command,
                "timestamp": datetime.now().isoformat(),
                "agent_coordination_required": True
            }
        }
    
    def _transform_result_to_ide(self, wre_result: Any, original_command: Dict[str, Any]) -> Dict[str, Any]:
        """Transform WRE result back to IDE-compatible format"""
        try:
            # Extract key information from WRE result
            success = getattr(wre_result, 'success', True) if hasattr(wre_result, 'success') else True
            
            ide_result = {
                "success": success,
                "command_type": original_command.get('type'),
                "session_id": self.session_id,
                "wre_orchestration": True,
                "agent_coordination": bool(self.active_agents),
                "coordinated_agents": list(self.active_agents.keys()) if self.active_agents else [],
                "timestamp": datetime.now().isoformat()
            }
            
            # Add specific result data based on command type
            if isinstance(wre_result, dict):
                ide_result.update({
                    "wre_details": wre_result,
                    "orchestration_success": wre_result.get('orchestration_success', True)
                })
            
            return ide_result
            
        except Exception as e:
            self.logger.error(f"Result transformation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "command_type": original_command.get('type'),
                "fallback_mode": True
            }
    
    async def _handle_fallback_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Handle command when WRE is unavailable"""
        self.logger.info(f"Handling command in fallback mode: {command.get('type', 'unknown')}")
        
        # Basic command handling without WRE
        command_handlers = {
            "create_module": self._fallback_create_module,
            "analyze_code": self._fallback_analyze_code,
            "run_tests": self._fallback_run_tests,
            "compliance_check": self._fallback_compliance_check
        }
        
        handler = command_handlers.get(command.get('type'))
        if handler:
            return await handler(command)
        
        return {
            "success": False,
            "error": "Command not supported in fallback mode",
            "command_type": command.get('type'),
            "fallback_mode": True,
            "suggestion": "Enable WRE integration for full functionality"
        }
    
    async def _fallback_create_module(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback module creation without WRE"""
        params = command.get('parameters', {})
        
        return {
            "success": False,
            "message": "Module creation requires WRE orchestration",
            "suggestion": "Enable WRE integration for autonomous module creation",
            "fallback_mode": True,
            "required_parameters": {
                "domain": params.get('domain', 'missing'),
                "name": params.get('name', 'missing'),
                "template": params.get('template', 'auto_select')
            }
        }
    
    async def _fallback_analyze_code(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback code analysis without WRE"""
        return {
            "success": False,
            "message": "Code analysis requires WRE orchestration with LLM providers",
            "suggestion": "Enable WRE integration for autonomous code analysis",
            "fallback_mode": True
        }
    
    async def _fallback_run_tests(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback test execution without WRE"""
        return {
            "success": False,
            "message": "Test execution requires WRE agent coordination",
            "suggestion": "Enable WRE integration for autonomous testing",
            "fallback_mode": True
        }
    
    async def _fallback_compliance_check(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback compliance checking without WRE"""
        return {
            "success": False,
            "message": "WSP compliance checking requires WRE compliance agents",
            "suggestion": "Enable WRE integration for autonomous compliance validation",
            "fallback_mode": True
        }
    
    def get_router_status(self) -> Dict[str, Any]:
        """Get current router status and capabilities"""
        return {
            "wre_available": WRE_AVAILABLE,
            "wre_orchestrator_active": self.wre_orchestrator is not None,
            "agent_activation_available": self.agent_activation is not None,
            "active_agents": list(self.active_agents.keys()) if self.active_agents else [],
            "session_id": self.session_id,
            "commands_processed": len(self.command_history),
            "integration_mode": "WRE_Integrated" if WRE_AVAILABLE else "Fallback"
        }

    async def activate_zen_coding_mode(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Activate zen coding mode through WRE orchestration"""
        if not WRE_AVAILABLE or not self.wre_orchestrator:
            return {
                "success": False,
                "message": "Zen coding requires WRE orchestration",
                "fallback_mode": True
            }
        
        zen_command = {
            "type": "zen_coding",
            "parameters": {
                "agent_state": parameters.get("agent_state", "0102"),
                "quantum_target": parameters.get("quantum_target", "02_future_solutions"),
                "wre_orchestration": True,
                "remembrance_mode": parameters.get("remembrance_mode", True),
                "recursive_evolution": parameters.get("recursive_evolution", True)
            }
        }
        
        return await self.route_command(zen_command) 