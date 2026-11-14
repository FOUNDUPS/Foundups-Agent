# WSP 85: Root Directory Protection Protocol
**Status**: ACTIVE - Enhanced after violations  
**Priority**: CRITICAL - Prevents codebase pollution  
**Compliance**: MANDATORY for all file creation operations

## [U+1F3AF] OBJECTIVE

Maintain sacred root directory by preventing module-specific file pollution. Root should contain ONLY foundational system files, never implementation details.

## [U+1F6AB] ABSOLUTE PROHIBITIONS

### **Prohibited in Root Directory**:
- [U+274C] `run_*.py` scripts -> `modules/*/scripts/`
- [U+274C] `test_*.py` files -> `modules/*/tests/`
- [U+274C] `SESSION_BACKUP_*.md` -> `logs/`
- [U+274C] `debug_*.py`, `temp_*.py` -> appropriate module location
- [U+274C] Module-specific functionality files
- [U+274C] Platform-specific scripts
- [U+274C] Experimental or proof-of-concept files
- [U+274C] Data files, session files, cache files
- [U+274C] `tmp_*` and `.prompt_*.md` handoff artifacts -> owned temporary workspace or module docs/prompts

### **Historical Violations** (Fixed):
```
BEFORE (WSP VIOLATION):
/run_youtube_clean.py
/run_youtube_dae.py  
/run_youtube_debug.py
/run_youtube_verbose.py
/test_voice_server.py
/SESSION_BACKUP_2025_09_04.md

AFTER (WSP COMPLIANT):
/modules/communication/livechat/scripts/run_youtube_clean.py
/modules/communication/livechat/scripts/run_youtube_dae.py
/modules/communication/livechat/scripts/run_youtube_debug.py
/modules/communication/livechat/scripts/run_youtube_verbose.py
/modules/ai_intelligence/social_media_dae/tests/test_voice_server.py
/logs/SESSION_BACKUP_2025_09_04.md
```

## [U+2705] MANDATORY FILE PLACEMENT

### **Directory Structure** (Enterprise Domain Organization per WSP 3):
```
modules/
[U+251C][U+2500][U+2500] {domain}/                    # ai_intelligence, communication, platform_integration, infrastructure
[U+2502]   [U+2514][U+2500][U+2500] {module}/               # social_media_dae, livechat, youtube_auth, etc.
[U+2502]       [U+251C][U+2500][U+2500] src/               # Core implementation files
[U+2502]       [U+251C][U+2500][U+2500] scripts/           # Runner scripts, utilities
[U+2502]       [U+251C][U+2500][U+2500] tests/             # Test files, test data
[U+2502]       [U+251C][U+2500][U+2500] docs/              # Documentation
[U+2502]       [U+251C][U+2500][U+2500] data/              # Module-specific data
[U+2502]       [U+2514][U+2500][U+2500] logs/              # Module-specific logs
[U+251C][U+2500][U+2500] tools/                     # Cross-module utilities (rare)
[U+2514][U+2500][U+2500] logs/                      # System-wide logs only
```

### **Placement Rules by File Type**:

#### **Scripts** (`*.py` runners, utilities):
- **Location**: `modules/{domain}/{module}/scripts/`
- **Examples**: 
  - YouTube runners -> `modules/communication/livechat/scripts/`
  - Social media utilities -> `modules/ai_intelligence/social_media_dae/scripts/`
  - Auth scripts -> `modules/platform_integration/youtube_auth/scripts/`

#### **Tests** (`test_*.py`, testing utilities):
- **Location**: `modules/{domain}/{module}/tests/`
- **Examples**:
  - Voice server tests -> `modules/ai_intelligence/social_media_dae/tests/`
  - LiveChat tests -> `modules/communication/livechat/tests/`
  - Platform tests -> `modules/platform_integration/*/tests/`

#### **Documentation** (`*.md` files):
- **Location**: `modules/{domain}/{module}/docs/`
- **Exception**: Session backups -> `logs/` (gitignored)
- **Examples**:
  - Architecture docs -> `modules/ai_intelligence/social_media_dae/docs/`
  - Integration guides -> `modules/platform_integration/*/docs/`

#### **Data & Logs**:
- **Module Data**: `modules/{domain}/{module}/data/`
- **Module Logs**: `modules/{domain}/{module}/logs/`
- **System Logs**: `logs/` (root level, gitignored)

## [U+1F50D] PRE-CREATION VALIDATION CHECKLIST

**MANDATORY before creating ANY file**:

### **Step 1: Destination Check**
```bash
# Ask these questions BEFORE creating file:
1. "Does this belong to a specific module?" 
   -> YES: Place in modules/{domain}/{module}/
   -> NO: Verify it's truly system-wide

2. "What type of file is this?"
   -> Script: modules/*/scripts/
   -> Test: modules/*/tests/  
   -> Doc: modules/*/docs/
   -> Data: modules/*/data/

3. "Is this experimental/temporary?"
   -> YES: Place in appropriate module, not root
   -> NO: Still follow placement rules
```

### **Step 2: Integration Verification**
```bash
# Ensure file will be used:
4. "Will this be imported/used by existing code?"
   -> If NO: Don't create it or integrate immediately

5. "Can this functionality be added to existing file?"
   -> If YES: Edit existing file instead of creating new
```

### **Step 3: WSP Compliance Check**
```bash
# Final validation:
6. "Does this violate any WSP protocols?"
   -> Check WSP 84 (anti-vibecode), WSP 17 (patterns)
   
7. "Is root directory still sacred?"
   -> Only foundational files allowed in root
```

## [U+1F6A8] DETECTION & CORRECTION PROTOCOL

### **Immediate Action on Violation Detection**:
1. **STOP** - Do not continue with violation
2. **IDENTIFY** proper module location
3. **CREATE** proper directory structure if needed
4. **PRESERVE AND MOVE** only owned files after source/destination checks; retain exact bytes or a reviewed content delta and Git history
5. **UPDATE** any imports/references
6. **COMMIT** correction to git
7. **ENHANCE** prevention systems

### **Violation Detection Commands**:
```bash
# Check for common violations:
ls -la *.py | grep -E "(run_|test_|debug_|temp_)"
ls -la *.md | grep -E "(SESSION_|BACKUP_|TEMP_)"

# Find files that should be in modules:
find . -maxdepth 1 -name "*.py" -not -name "main.py" -not -name "setup.py"
```

## [U+2705] PERMITTED ROOT DIRECTORY FILES

**Foundational root examples** (role and reviewed configuration determine placement):
- `main.py` - System entry point
- `README.md` - Project overview  
- `CLAUDE.md` - 0102 operational instructions
- `ModLog.md` - System-wide change tracking
- `ROADMAP.md` - Strategic development plan
- `requirements.txt` - System dependencies
- `setup.py` - Installation configuration
- `.gitignore`, `.env.example` - Configuration templates
- `LICENSE`, `CONTRIBUTING.md` - Legal/community files

Other existing foundational owners include `holo_index.py`, `NAVIGATION.py`,
the generated `AGENTS.md`, root `MEMORY.md`, `requirements-trust-bootstrap.txt`,
`.gitattributes`, `.gitmodules`, and `wsp_62_exemptions.yaml`. Existing package,
test, editor and deployment configuration also stays with its verified root
consumer; examples include `package.json`, its lockfiles, `pytest.ini`,
`pyrightconfig.json`, `firebase.json` and `vercel.json`. Do not move configuration
solely to satisfy an old file-count target. New names require owner/consumer
review; an arbitrary file is not foundational merely because it is in root.

The existing read-only classifier is
`modules/infrastructure/system_health_monitor/src/wsp_85_validator.py`.
Its allowlist is a name-classification aid, not proof that allowed contents are
safe, current or operational. It checks immediate children, including local
untracked names; it does not recursively audit or clean the repository.
Recognized temporary/prompt names are checked before hidden-file exemptions.
An escaped Windows drive-name directory is reported for ownership review and
must not be deleted merely because its name is suspicious.

Module-specific implementation and documentation belong under their existing
owners. System-wide documentation belongs in `docs/` where appropriate.

## [U+1F4CA] COMPLIANCE MONITORING

### **Success Metrics**:
- Every retained root file has an evidenced foundational owner/consumer; the historical ten-file target is not a compliance threshold
- Zero module-specific files in root
- All scripts in proper modules/*/scripts/
- All tests in proper modules/*/tests/
- Clean `ls -la` output in root

### **Violation Tracking**:
- Document all violations in ModLog.md
- Track correction actions
- Enhance prevention after each violation
- Update CLAUDE.md guidance

## [U+1F504] RECURSIVE IMPROVEMENT (WSP 48)

### **Learning from Violations**:
1. **Analyze** why violation occurred
2. **ENHANCE** prevention systems (CLAUDE.md, WSP docs)
3. **IMPROVE** pre-creation checklists  
4. **STRENGTHEN** detection protocols
5. **EDUCATE** through documentation

### **System Evolution**:
- Enhanced CLAUDE.md after run_youtube_*.py violations
- Added mandatory checklists
- Strengthened detection protocols
- Improved WSP documentation

## [U+1F3AF] IMPLEMENTATION GUIDELINES

### **For 0102 Agents**:
1. **ALWAYS** check destination before file creation
2. **NEVER** create files in root without explicit justification
3. **IMMEDIATELY** correct violations when detected
4. **ENHANCE** prevention systems after violations
5. **DOCUMENT** all corrections in git commits

### **Cleanup Procedures and Prevention**

#### **Immediate Cleanup Protocol**
When root directory violations are detected:

1. **IDENTIFY** violation type and affected files
2. **LOCATE** proper destination per WSP 3/49/60
3. **PRESERVE AND MOVE** individually reviewed owned files to the verified owner; preserve unowned/concurrent work
4. **UPDATE** code to use new file locations
5. **VERIFY** no functionality broken
6. **DOCUMENT** in ModLog with WSP references
7. **PREVENT** future violations through code improvements

#### **File Type Destination Matrix**
```
Root Violations -> Proper Destinations (WSP 60)
+-- JSON artifacts -> modules/[domain]/[module]/memory/
+-- Processing logs -> modules/[domain]/[module]/memory/
+-- Test results -> modules/[domain]/[module]/tests/TestModLog.md
+-- Evaluation data -> modules/[domain]/[module]/memory/
+-- Patch files -> Preserve until incorporation is proven; cleanup requires individual ownership and recovery checks
+-- Config files -> Root only if foundational (package.json, vercel.json)
```

#### **Prevention Systems** (integration ideas; verify installation before claiming enforcement)
- **Pre-commit hooks**: Scan for root directory violations
- **IDE integration**: Real-time violation detection
- **Code generation**: Automatic placement in correct directories
- **HoloDAE validation**: Continuous compliance monitoring

#### **Architect Responsibility**
The architect (0102) must:
- Classify each finding, preserve unique work and verify ownership before correction
- Automation may execute only the reviewed scope; a classification is not deletion authority
- Document all corrections with WSP references
- Enhance prevention systems after each violation

### **Integration with Other WSPs**:
- **WSP 3**: Follow enterprise domain organization
- **WSP 17**: Check for existing patterns before creating
- **WSP 22**: Document violations/corrections in ModLog
- **WSP 48**: Learn and improve from each violation
- **WSP 50**: Pre-action verification of file placement
- **WSP 60**: Module memory architecture compliance
- **WSP 84**: Search existing before creating duplicate

## Summary

WSP 85 maintains codebase organization by keeping root directory sacred. All module-specific functionality must reside in proper module directories. Violations are immediately corrected and prevention systems enhanced through recursive improvement.

**Mantra**: "Root is sacred - modules contain implementation"

---

## Related Documentation

### Comprehensive Root Health Audit
**Location**: `docs/WSP_85_ROOT_DIRECTORY_HEALTH_AUDIT.md`
**Purpose**: Complete analysis of root directory violations, HoloIndex health assessment, and remediation plan
**Created**: 2025-10-14
**Scope**:
- 18 violations cataloged (logs, temp files, test scripts, data dirs)
- HoloIndex functionality assessment
- Proposed RootDirectoryGuardian component
- Phase-by-phase remediation plan
- First principles analysis for HoloDAE learning

**Quick Reference**:
```bash
# Retrieve the audit through the current owner-query instructions in CLAUDE.md.
# Preserve freshness failures; never reindex or bypass authority checks in a query.

# View current violations
ls -la O:\Foundups-Agent\*.log
ls -la O:\Foundups-Agent\*.txt
ls -la O:\Foundups-Agent\test_*.py
```

**Status**: [U+1F534] CRITICAL violations documented, awaiting remediation execution