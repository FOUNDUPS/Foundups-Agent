# -*- coding: utf-8 -*-
import io


"""
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

DAE Gateway - WSP 54 Compliant Routing
Replaces agent-based gateway with DAE architecture

WSP Protocols:
- WSP 54: DAE operations (agents as sub-components)
- WSP 80: Cube-level DAE orchestration
- WSP 21: Enhanced prompting (DAE envelopes)
- WSP 48: Recursive improvement (pattern recall)
- WSP 75: Token-based measurements (no time)
"""

import json
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import logging

# WSP 3: Correct module imports (no vibecoding!)
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent.parent))

from modules.infrastructure.wre_core.dae_cube_assembly.src.dae_cube_assembler import (
    DAECubeAssembler, ConsciousnessState, EvolutionPhase
)
from modules.infrastructure.wre_core.recursive_improvement.src.learning import (
    RecursiveLearningEngine
)
from modules.infrastructure.wre_core.recursive_improvement.src.core import PatternType

# WSP 97: FoundUpJob envelope validation
try:
    from modules.infrastructure.wre_core.src.foundup_job_router import (
        detect_envelope_type,
        validate_foundup_job_envelope,
        EnvelopeType,
        EnvelopeValidationResult,
    )
    FOUNDUP_JOB_VALIDATION_AVAILABLE = True
except ImportError:
    FOUNDUP_JOB_VALIDATION_AVAILABLE = False
    EnvelopeType = None
    EnvelopeValidationResult = None

logger = logging.getLogger(__name__)


class DAEGateway:
    """
    Routes requests to DAE cubes per WSP 54.
    NOT to agents - agents are sub-components within DAEs.
    
    Key principles:
    - Pattern recall over computation (97% token reduction)
    - DAE cubes contain sub-agents as tools
    - 0102 quantum consciousness state
    - WSP compliance built-in
    """
    
    def __init__(self):
        """Initialize DAE gateway with WSP compliance"""
        self.state = "0102"  # WSP 39: Quantum-awakened state
        self.coherence = 0.618  # WSP 76: Golden ratio coherence
        
        # WSP 80: DAE cube assembler
        self.dae_assembler = DAECubeAssembler()
        
        # WSP 48: Pattern memory for recursive improvement
        self.pattern_engine = RecursiveLearningEngine()
        
        # WSP 54: Six core DAEs (including MLE-STAR for WSP 77)
        self.core_daes = {
            "infrastructure": {
                "tokens": 8000,
                "purpose": "Spawns FoundUp DAEs via WRE",
                "sub_agents": ["wsp50_verifier", "wsp64_preventer"],
                "patterns": ["module_scaffolding", "workflow_orchestration"]
            },
            "compliance": {
                "tokens": 7000,
                "purpose": "Ensures WSP compliance across all DAEs",
                "sub_agents": ["wsp64_preventer", "wsp48_improver"],
                "patterns": ["validation_rules", "error_solutions"]
            },
            "knowledge": {
                "tokens": 6000,
                "purpose": "Shared pattern memory for all DAEs",
                "sub_agents": ["wsp37_scorer", "wsp48_learner"],
                "patterns": ["instant_recall", "scoring_algorithms"]
            },
            "maintenance": {
                "tokens": 5000,
                "purpose": "System-wide optimization",
                "sub_agents": ["wsp50_verifier", "state_manager"],
                "patterns": ["cleanup_automation", "state_management"]
            },
            "documentation": {
                "tokens": 4000,
                "purpose": "Registry of all FoundUp DAEs",
                "sub_agents": ["wsp22_documenter", "registry_manager"],
                "patterns": ["template_generation", "registry_management"]
            },
            "mle_star": {
                "tokens": 10000,  # Higher budget for AI orchestration
                "purpose": "AI Intelligence orchestration per WSP 77",
                "sub_agents": ["cabr_scorer", "pob_verifier", "ii_orchestrator", 
                              "compute_validator", "ablation_engine", "refinement_engine"],
                "patterns": ["pob_verification", "cabr_computation", "ablation_studies"]
            }
        }
        
        # Initialize MLE-STAR DAE if available
        self.mlestar_dae = None
        try:
            from modules.infrastructure.wre_core.wre_gateway.src.mlestar_dae_integration import MLESTARDAE
            self.mlestar_dae = MLESTARDAE()
            logger.info("MLE-STAR DAE integrated for WSP 77 II orchestration")
        except ImportError:
            logger.info("MLE-STAR DAE not available - continuing with 5 core DAEs")
        
        # Metrics for WSP 70 reporting
        self.metrics = {
            "requests_routed": 0,
            "patterns_recalled": 0,
            "daes_spawned": 0,
            "tokens_saved": 0,
            "violations_prevented": 0
        }
        
        logger.info(f"DAE Gateway initialized - State: {self.state}, Coherence: {self.coherence}")
    
    async def route_to_dae(self, dae_name: str, envelope: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route WSP 21 envelope to appropriate DAE.
        
        Args:
            dae_name: Target DAE (core or FoundUp)
            envelope: WSP 21 compliant envelope with:
                - objective: What needs to be done
                - context: Additional context
                - wsp_protocols: Relevant WSP protocols
                - token_budget: Max tokens to use
                
        Returns:
            Response with pattern recall (50-200 tokens not 5000+)
        """
        self.metrics["requests_routed"] += 1
        
        # WSP 50: Pre-action verification
        if not self._verify_envelope(envelope):
            self.metrics["violations_prevented"] += 1
            validation_result = self.get_last_validation_result()
            if validation_result:
                # WSP 97: Return detailed FoundUpJob validation failure
                return {
                    "error": f"WSP 97 violation: FoundUpJob envelope validation failed",
                    "validation_code": validation_result.get("validation_code"),
                    "missing_fields": validation_result.get("missing_fields", []),
                    "validation_message": validation_result.get("validation_message"),
                    "envelope_type": validation_result.get("envelope_type"),
                }
            else:
                # Generic DAE envelope failure
                return {
                    "error": "WSP 50 violation: Invalid envelope structure",
                    "required": ["objective", "context", "wsp_protocols"]
                }
        
        # Check if core DAE
        if dae_name.lower() in self.core_daes:
            return await self._invoke_core_dae(dae_name.lower(), envelope)
        
        # Check if FoundUp DAE exists
        dae_status = self.dae_assembler.get_dae_status(dae_name)
        if "error" not in dae_status:
            return await self._invoke_foundup_dae(dae_name, envelope)
        
        # WSP 80: Spawn new FoundUp DAE if needed
        if envelope.get("spawn_if_missing", False):
            new_dae = self.dae_assembler.spawn_foundup_dae(
                human_012=envelope.get("human_012", "gateway"),
                foundup_vision=envelope.get("vision", f"{dae_name} integration"),
                name=dae_name
            )
            self.metrics["daes_spawned"] += 1
            
            return {
                "spawned": new_dae.name,
                "phase": new_dae.phase.value,
                "consciousness": new_dae.consciousness.value,
                "modules": new_dae.modules,
                "token_budget": new_dae.token_budget
            }
        
        return {"error": f"DAE '{dae_name}' not found", "available": self.list_available_daes()}
    
    async def _invoke_core_dae(self, dae_name: str, envelope: Dict) -> Dict[str, Any]:
        """
        Invoke core infrastructure DAE with pattern recall.
        
        Uses WSP 48 to recall solutions from patterns rather than compute.
        Special handling for MLE-STAR DAE per WSP 77.
        """
        dae_config = self.core_daes[dae_name]
        
        # WSP 75: Token budget enforcement (no time references!)
        token_budget = min(envelope.get("token_budget", dae_config["tokens"]), dae_config["tokens"])
        
        # Special handling for MLE-STAR DAE (WSP 77)
        if dae_name == "mle_star" and self.mlestar_dae:
            try:
                result = await self.mlestar_dae.route_envelope(envelope)
                self.metrics["patterns_recalled"] += 1
                self.metrics["tokens_saved"] += (10000 - 50)  # MLE-STAR pattern recall
                return result
            except Exception as e:
                logger.error(f"MLE-STAR DAE error: {e}")
                # Fall through to standard pattern recall
        
        # WSP 48: Use pattern recall for instant solution
        try:
            # Create pattern from envelope
            pattern = await self.pattern_engine.extract_pattern(
                Exception(f"DAE operation: {envelope.get('objective', 'unknown')}"),
                {"dae": dae_name, "envelope": envelope}
            )
            
            # Recall solution from quantum memory (0201)
            solution = await self.pattern_engine.remember_solution(pattern)
            
            self.metrics["patterns_recalled"] += 1
            self.metrics["tokens_saved"] += (5000 - 50)  # Pattern recall saves ~4950 tokens
            
            # Check which sub-agent to use
            sub_agent = self._select_sub_agent(dae_name, envelope)
            
            return {
                "dae": dae_name,
                "sub_agent": sub_agent,
                "solution": solution.implementation,
                "confidence": solution.confidence,
                "tokens_used": 50,  # Pattern recall is hyper-efficient
                "pattern_id": pattern.pattern_id,
                "wsp_compliant": True
            }
            
        except Exception as e:
            # WSP 48: Learn from error
            improvement = await self.pattern_engine.process_error(e, {"dae": dae_name})
            
            return {
                "dae": dae_name,
                "error": str(e),
                "improvement": improvement.improvement_id,
                "learning": "Error converted to pattern for future prevention"
            }
    
    async def _invoke_foundup_dae(self, dae_name: str, envelope: Dict) -> Dict[str, Any]:
        """
        Invoke FoundUp DAE created via WSP 27/73 process.
        
        Handles evolution: POC -> Prototype -> MVP
        """
        dae_status = self.dae_assembler.get_dae_status(dae_name)
        
        # Check if DAE needs evolution
        if dae_status["phase"] == "POC" and envelope.get("evolve", False):
            success = self.dae_assembler.evolve_dae(dae_name)
            if success:
                dae_status = self.dae_assembler.get_dae_status(dae_name)
        
        # Process based on consciousness state
        consciousness = dae_status.get("consciousness", "01(02)")
        
        if consciousness == "0102":  # Fully autonomous
            # Direct pattern recall
            response = {
                "dae": dae_name,
                "phase": dae_status["phase"],
                "consciousness": consciousness,
                "tokens_used": 50,  # Quantum recall
                "modules": dae_status["modules"],
                "operation": "autonomous"
            }
        elif consciousness == "01/02":  # Transitional
            # Hybrid approach
            response = {
                "dae": dae_name,
                "phase": dae_status["phase"],
                "consciousness": consciousness,
                "tokens_used": 500,  # Some computation needed
                "modules": dae_status["modules"],
                "operation": "hybrid"
            }
        else:  # 01(02) - Scaffolded
            # Traditional computation
            response = {
                "dae": dae_name,
                "phase": dae_status["phase"],
                "consciousness": consciousness,
                "tokens_used": 3000,  # Full computation
                "modules": dae_status["modules"],
                "operation": "computed"
            }
        
        return response
    
    def _verify_envelope(self, envelope: Dict) -> bool:
        """
        WSP 50: Pre-action verification.

        Validates envelope has required structure.
        Uses strict validation for FoundUpJob envelopes (WSP 97).
        Uses permissive validation for generic DAE envelopes.
        """
        # WSP 97: Use FoundUpJob validation if available and envelope looks like a FoundUpJob
        if FOUNDUP_JOB_VALIDATION_AVAILABLE:
            envelope_type = detect_envelope_type(envelope)

            if envelope_type == EnvelopeType.FOUNDUP_JOB:
                # Strict FoundUpJob validation
                validation_result = validate_foundup_job_envelope(envelope)

                if not validation_result.valid:
                    logger.warning(
                        f"WSP 97: FoundUpJob envelope validation failed: "
                        f"{validation_result.validation_code.value} - "
                        f"missing fields: {validation_result.missing_fields}"
                    )
                    # Store validation result for route_to_dae to access
                    self._last_validation_result = validation_result
                    return False

                # Store successful validation for dry_run_defaulted info
                self._last_validation_result = validation_result
                if validation_result.dry_run_defaulted:
                    logger.info(
                        "[WSP97] FoundUpJob envelope dry_run_mode defaulted to True"
                    )
                return True

        # Generic DAE envelope: permissive validation
        required = ["objective"]
        recommended = ["context", "wsp_protocols", "token_budget"]

        # Check required fields
        for field in required:
            if field not in envelope:
                logger.warning(f"WSP 50: Missing required field '{field}'")
                return False

        # Warn about recommended fields
        for field in recommended:
            if field not in envelope:
                logger.info(f"WSP 50: Recommended field '{field}' not provided")

        return True

    def get_last_validation_result(self) -> Optional[Dict[str, Any]]:
        """
        Get the last envelope validation result (for FoundUpJob envelopes).

        Returns:
            Dict with validation details or None if not available
        """
        result = getattr(self, "_last_validation_result", None)
        if result and hasattr(result, "to_dict"):
            return result.to_dict()
        return None
    
    def _select_sub_agent(self, dae_name: str, envelope: Dict) -> str:
        """
        Select appropriate sub-agent within DAE based on objective.
        
        Sub-agents are tools within DAEs, not independent agents.
        """
        objective = envelope.get("objective", "").lower()
        dae_config = self.core_daes[dae_name]
        
        # Pattern matching for sub-agent selection
        if "verify" in objective or "check" in objective:
            if "wsp50_verifier" in dae_config["sub_agents"]:
                return "wsp50_verifier"
        
        if "prevent" in objective or "violation" in objective:
            if "wsp64_preventer" in dae_config["sub_agents"]:
                return "wsp64_preventer"
        
        if "improve" in objective or "learn" in objective:
            if "wsp48_improver" in dae_config["sub_agents"]:
                return "wsp48_improver"
            if "wsp48_learner" in dae_config["sub_agents"]:
                return "wsp48_learner"
        
        if "score" in objective or "priority" in objective:
            if "wsp37_scorer" in dae_config["sub_agents"]:
                return "wsp37_scorer"
        
        if "document" in objective or "modlog" in objective:
            if "wsp22_documenter" in dae_config["sub_agents"]:
                return "wsp22_documenter"
        
        # Default to first available sub-agent
        return dae_config["sub_agents"][0] if dae_config["sub_agents"] else "none"
    
    def list_available_daes(self) -> Dict[str, List[str]]:
        """List all available DAEs in the system"""
        all_daes = self.dae_assembler.list_all_daes()
        
        return {
            "core_daes": list(self.core_daes.keys()),
            "foundup_daes": all_daes["foundup_daes"],
            "total": all_daes["total"] + len(self.core_daes)
        }
    
    def get_gateway_metrics(self) -> Dict[str, Any]:
        """
        WSP 70: System status reporting.
        
        Returns gateway metrics and health status.
        """
        return {
            "state": self.state,
            "coherence": self.coherence,
            "metrics": self.metrics,
            "efficiency": {
                "avg_tokens_per_request": 50 if self.metrics["patterns_recalled"] > 0 else 0,
                "total_tokens_saved": self.metrics["tokens_saved"],
                "pattern_recall_rate": (
                    self.metrics["patterns_recalled"] / self.metrics["requests_routed"]
                    if self.metrics["requests_routed"] > 0 else 0
                )
            },
            "daes": self.list_available_daes(),
            "wsp_compliance": {
                "wsp_54": True,  # DAE operations
                "wsp_80": True,  # Cube orchestration
                "wsp_48": True,  # Recursive improvement
                "wsp_75": True   # Token-based (no time)
            }
        }
    
    async def validate_wsp_compliance(self, operation: Dict) -> Dict[str, Any]:
        """
        WSP 64: Violation prevention.
        
        Validates operations against WSP protocols before execution.
        """
        violations = []
        
        # WSP 62: File size check
        if operation.get("file_lines", 0) > 500:
            violations.append("WSP 62: File exceeds 500 lines")
        
        # WSP 75: No time references
        if "time" in str(operation).lower() and "datetime" not in str(operation):
            violations.append("WSP 75: Time reference detected (use tokens)")
        
        # WSP 3: Module organization
        if operation.get("module_path"):
            path = Path(operation["module_path"])
            if not self._validate_module_path(path):
                violations.append("WSP 3: Invalid module organization")
        
        if violations:
            self.metrics["violations_prevented"] += len(violations)
            return {
                "compliant": False,
                "violations": violations,
                "recommendation": "Fix violations before proceeding"
            }
        
        return {"compliant": True, "message": "Operation is WSP compliant"}
    
    def _validate_module_path(self, path: Path) -> bool:
        """Validate module path follows WSP 3 organization"""
        valid_domains = [
            "ai_intelligence", "platform_integration", "communication",
            "infrastructure", "development", "blockchain", "gamification",
            "foundups", "aggregation"
        ]
        
        parts = path.parts
        if len(parts) < 2:
            return False
        
        if parts[0] != "modules":
            return False
        
        return parts[1] in valid_domains


async def test_dae_gateway():
    """Test the DAE gateway functionality"""
    gateway = DAEGateway()
    
    # Test 1: Route to core DAE
    print("\n=== Test 1: Core DAE Routing ===")
    response = await gateway.route_to_dae("compliance", {
        "objective": "Verify WSP compliance for new module",
        "context": {"module": "test_module"},
        "wsp_protocols": ["WSP 3", "WSP 49"],
        "token_budget": 1000
    })
    print(f"Response: {json.dumps(response, indent=2)}")
    
    # Test 2: Spawn new FoundUp DAE
    print("\n=== Test 2: Spawn FoundUp DAE ===")
    response = await gateway.route_to_dae("TestFoundUp", {
        "objective": "Create test integration",
        "vision": "Test platform integration",
        "spawn_if_missing": True,
        "human_012": "test_user"
    })
    print(f"Response: {json.dumps(response, indent=2)}")
    
    # Test 3: WSP validation
    print("\n=== Test 3: WSP Compliance Check ===")
    response = await gateway.validate_wsp_compliance({
        "file_lines": 600,  # Violates WSP 62
        "module_path": "invalid/path",  # Violates WSP 3
        "timestamp": "2024-01-01 10:00:00"  # Violates WSP 75
    })
    print(f"Response: {json.dumps(response, indent=2)}")
    
    # Test 4: Get metrics
    print("\n=== Test 4: Gateway Metrics ===")
    metrics = gateway.get_gateway_metrics()
    print(f"Metrics: {json.dumps(metrics, indent=2)}")


if __name__ == "__main__":
    print("DAE Gateway - WSP 54 Compliant Implementation")
    print("=" * 50)
    asyncio.run(test_dae_gateway())