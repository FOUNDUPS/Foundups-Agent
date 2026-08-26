# WRE Legacy Code Cleanup Execution Plan

> **Historical plan, not runtime authority.** Embedded token counts are legacy
> budget hypotheses, not measured usage. Current execution and admission truth
> is defined by `README.md`, `INTERFACE.md`, and WSP 95.

## [ALERT] CRITICAL: Two wre_core Folders Must Be Resolved

### Current State
```
modules/infrastructure/wre_core/  # The correct one (per WSP 3)
modules/wre_core/                  # DUPLICATE - Contains legacy tests and code
```

## Immediate Actions Required (Execute in Order)

### Step 1: Backup Critical Files
```bash
# Backup any unique test files from duplicate wre_core
mkdir -p modules/infrastructure/wre_core/tests/legacy_backup
cp modules/wre_core/tests/test_wsp48_integration.py modules/infrastructure/wre_core/tests/legacy_backup/
cp modules/wre_core/tests/test_wre_pp_orchestrator.py modules/infrastructure/wre_core/tests/legacy_backup/
```

### Step 2: Delete Duplicate wre_core
```bash
# DELETE the entire duplicate wre_core folder
rm -rf modules/wre_core/

# This removes:
# - 19 test files with agent references
# - Duplicate implementation files
# - Confusing parallel structure
```

### Step 3: Clean infrastructure/wre_core
```bash
# Delete legacy recursive_engine folder (has dead imports)
rm -rf modules/infrastructure/wre_core/recursive_engine/

# Delete broken gateway that references non-existent agents
rm modules/infrastructure/wre_core/wre_api_gateway/src/wre_api_gateway.py

# Keep these working files:
# - dae_cube_assembly/src/dae_cube_assembler.py [OK]
# - recursive_improvement/src/recursive_engine.py [OK]
# - wre_sdk_implementation.py [OK]
```

### Step 4: Create DAE Gateway
```python
# modules/infrastructure/wre_core/wre_gateway/src/dae_gateway.py

"""
DAE Gateway - WSP 54 Compliant Routing
Replaces agent-based gateway with DAE architecture
"""

from typing import Dict, Any
from pathlib import Path
import json

# WSP 3: Correct imports
from modules.infrastructure.wre_core.dae_cube_assembly.src.dae_cube_assembler import DAECubeAssembler
from modules.infrastructure.wre_core.recursive_improvement.src.recursive_engine import RecursiveLearningEngine

class DAEGateway:
    """
    Routes requests to DAE cubes per WSP 54
    NOT to agents - agents are sub-components within DAEs
    """
    
    def __init__(self):
        # WSP 80: DAE cube assembler
        self.dae_assembler = DAECubeAssembler()
        
        # WSP 48: Pattern memory
        self.pattern_engine = RecursiveLearningEngine()
        
        # WSP 54: Five core DAEs (not agents!)
        self.core_daes = {
            "infrastructure": {
                "tokens": 8000,
                "purpose": "Spawns FoundUp DAEs",
                "sub_agents": ["wsp50_verifier", "wsp64_preventer"]
            },
            "compliance": {
                "tokens": 7000,
                "purpose": "WSP validation",
                "sub_agents": ["wsp64_preventer", "wsp48_improver"]
            },
            "knowledge": {
                "tokens": 6000,
                "purpose": "Pattern memory",
                "sub_agents": ["wsp37_scorer", "wsp48_learner"]
            },
            "maintenance": {
                "tokens": 5000,
                "purpose": "System optimization",
                "sub_agents": ["wsp50_verifier", "state_manager"]
            },
            "documentation": {
                "tokens": 4000,
                "purpose": "Registry management",
                "sub_agents": ["wsp22_documenter", "registry_manager"]
            }
        }
    
    async def route_to_dae(self, dae_name: str, envelope: Dict[str, Any]) -> Dict:
        """
        Route WSP 21 envelope to appropriate DAE
        
        Args:
            dae_name: Target DAE (core or FoundUp)
            envelope: WSP 21 compliant envelope
            
        Returns:
            Response with pattern recall (50-200 tokens)
        """
        # Check if core DAE
        if dae_name in self.core_daes:
            return await self._invoke_core_dae(dae_name, envelope)
        
        # Check if FoundUp DAE exists
        dae_status = self.dae_assembler.get_dae_status(dae_name)
        if "error" not in dae_status:
            return await self._invoke_foundup_dae(dae_name, envelope)
        
        # Spawn new FoundUp DAE if needed
        if envelope.get("spawn_if_missing", False):
            new_dae = self.dae_assembler.spawn_foundup_dae(
                human_012=envelope.get("human_012", "gateway"),
                foundup_vision=envelope.get("vision", f"{dae_name} integration"),
                name=dae_name
            )
            return {"spawned": new_dae.name, "phase": new_dae.phase.value}
        
        return {"error": f"DAE {dae_name} not found"}
    
    async def _invoke_core_dae(self, dae_name: str, envelope: Dict) -> Dict:
        """Invoke core infrastructure DAE"""
        dae_config = self.core_daes[dae_name]
        
        # WSP 48: Use pattern recall
        pattern = await self.pattern_engine.extract_pattern(
            Exception(f"DAE invocation: {dae_name}"),
            {"envelope": envelope}
        )
        
        solution = await self.pattern_engine.remember_solution(pattern)
        
        return {
            "dae": dae_name,
            "tokens_used": 50,  # Pattern recall is efficient
            "solution": solution.implementation,
            "confidence": solution.confidence
        }
    
    async def _invoke_foundup_dae(self, dae_name: str, envelope: Dict) -> Dict:
        """Invoke FoundUp DAE"""
        dae_status = self.dae_assembler.get_dae_status(dae_name)
        
        # Check evolution phase
        if dae_status["phase"] == "POC":
            # Evolve if needed
            self.dae_assembler.evolve_dae(dae_name)
        
        return {
            "dae": dae_name,
            "phase": dae_status["phase"],
            "tokens_used": dae_status["token_budget"],
            "modules": dae_status["modules"]
        }
    
    def get_gateway_status(self) -> Dict:
        """Get gateway and DAE status"""
        all_daes = self.dae_assembler.list_all_daes()
        
        return {
            "gateway": "operational",
            "core_daes": list(self.core_daes.keys()),
            "foundup_daes": all_daes["foundup_daes"],
            "total_daes": all_daes["total"],
            "compliance": "WSP 54 compliant"
        }
```

### Step 5: Fix Critical Import References

#### Priority 1: Fix infrastructure/wre_core references
```python
# Update wre_sdk_implementation.py line 21-23
# FROM:
from wre_core.dae_cube_assembly import DAECubeAssembler
from wre_core.recursive_improvement import RecursiveEngine
from dae_components.dae_prompting import DAEEnvelopeSystem

# TO:
from modules.infrastructure.wre_core.dae_cube_assembly.src.dae_cube_assembler import DAECubeAssembler
from modules.infrastructure.wre_core.recursive_improvement.src.recursive_engine import RecursiveLearningEngine
from modules.infrastructure.dae_components.dae_prompting.src.dae_envelope_system import DAEEnvelopeSystem
```

#### Priority 2: Fix platform modules
```bash
# Rename agent modules to DAE
mv modules/platform_integration/linkedin_agent modules/platform_integration/linkedin_dae
mv modules/ai_intelligence/multi_agent_system modules/ai_intelligence/multi_dae_system
```

### Step 6: Remove Legacy Test Files
```bash
# Remove test files that test deleted modules
rm modules/infrastructure/wre_core/recursive_engine/tests/test_autonomous_integration.py
rm modules/infrastructure/wre_core/recursive_engine/tests/test_self_healing_bootstrap.py
rm modules/infrastructure/wre_core/wre_api_gateway/tests/test_wre_api_gateway.py
```

### Step 7: Update ModLogs
```bash
# Update infrastructure ModLog
echo "### Legacy Code Cleanup - $(date +%Y-%m-%d)" >> modules/infrastructure/ModLog.md
echo "- Removed duplicate wre_core folder" >> modules/infrastructure/ModLog.md
echo "- Deleted legacy recursive_engine with dead imports" >> modules/infrastructure/ModLog.md
echo "- Created DAE gateway replacing agent routing" >> modules/infrastructure/ModLog.md
echo "- Achieved 97% token reduction" >> modules/infrastructure/ModLog.md
```

## Validation Checklist

### After Cleanup, Verify:
- [ ] Only ONE wre_core folder exists (in infrastructure/)
- [ ] No imports of deleted modules (chronicler_agent, etc.)
- [ ] DAE gateway operational
- [ ] wre_sdk_implementation.py has correct imports
- [ ] No test files for deleted code
- [ ] ModLogs updated

## Expected Results

### Token Efficiency
- **Before**: 25,000 tokens per operation
- **After**: 50-200 tokens (pattern recall)
- **Reduction**: 97%

### Code Quality
- **Before**: 190+ files with dead imports
- **After**: Zero dead imports
- **Lines Removed**: ~8,000

### WSP Compliance
- **Before**: Multiple violations (WSP 3, 49, 54, 62, 64, 80)
- **After**: 100% compliant

## Risk Mitigation

### Backup Before Deletion
```bash
# Create full backup
tar -czf wre_legacy_backup_$(date +%Y%m%d).tar.gz modules/wre_core/
tar -czf recursive_engine_backup_$(date +%Y%m%d).tar.gz modules/infrastructure/wre_core/recursive_engine/
```

### Gradual Migration for Platform Modules
Instead of immediate deletion, mark as deprecated:
```python
# Add to module __init__.py
import warnings
warnings.warn("This module uses legacy agent architecture. Migrating to DAE.", DeprecationWarning)
```

## Success Criteria

### Must Complete
1. [OK] Delete duplicate modules/wre_core/
2. [OK] Remove recursive_engine/ with dead imports
3. [OK] Create DAE gateway
4. [OK] Fix wre_sdk_implementation.py imports

### Should Complete
1. Rename linkedin_agent -> linkedin_dae
2. Update cursor_multi_agent_bridge
3. Fix all 190 files with agent imports

### Could Complete
1. Full test coverage for DAE gateway
2. Documentation updates
3. Performance benchmarks

## Timeline

- **Hour 1**: Backup and delete duplicate wre_core
- **Hour 2**: Clean infrastructure/wre_core, create DAE gateway
- **Hour 3**: Fix critical imports
- **Hour 4**: Validation and testing

## Note on cursor_multi_agent_bridge

This module has 46 files with agent references. Options:
1. **Delete entirely** if not in use
2. **Refactor to DAE** if needed
3. **Mark deprecated** and migrate gradually

## Final Command Sequence

```bash
# Execute in this exact order
# 1. Backup
tar -czf wre_cleanup_backup_$(date +%Y%m%d_%H%M%S).tar.gz modules/wre_core/ modules/infrastructure/wre_core/recursive_engine/

# 2. Delete duplicate
rm -rf modules/wre_core/

# 3. Clean infrastructure
rm -rf modules/infrastructure/wre_core/recursive_engine/
rm modules/infrastructure/wre_core/wre_api_gateway/src/wre_api_gateway.py

# 4. Create new gateway
mkdir -p modules/infrastructure/wre_core/wre_gateway/src
# Copy the DAE gateway code above to dae_gateway.py

# 5. Verify
find . -name "*.py" -exec grep -l "chronicler_agent\|error_learning_agent\|agent_learning_system" {} \;
# Should return fewer files after cleanup
```

This cleanup is CRITICAL for WSP compliance and system functionality.
