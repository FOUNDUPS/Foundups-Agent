# WSP Framework Annexes

Purpose: This folder holds non-protocol governance references used by numbered WSP protocols.

Naming Rule:
- Only canonical numbered protocols in `WSP_framework/src/` use the `WSP_##_...` prefix.
- Annexes in this folder use plain names without `WSP_`.

Current Annexes:
- `MODULE_CONCATENATION_GATE.md`
- `MODULE_DECISION_MATRIX.md`
- `MODULE_PLACEMENT_GUIDE.md`
- `ORCHESTRATION_HIERARCHY_ANNEX.md`

Canonical Mapping:
- Cross-module execution-plane concatenation -> `WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md`
- Domain routing and placement policy -> `WSP_framework/src/WSP_3_Enterprise_Domain_Organization.md`
- Module structure and placement sanity gate -> `WSP_framework/src/WSP_49_Module_Directory_Structure_Standardization_Protocol.md`
- Orchestration tier responsibilities -> `WSP_framework/src/WSP_46_Windsurf_Recursive_Engine_Protocol.md`

Exception:
- `WSP_framework/src/WSP_MODULE_VIOLATIONS.md` remains in `src` as the active WSP 47 operational log and historical corpus target.
