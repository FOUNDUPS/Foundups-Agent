# WSP 50: Pre-Action Verification Protocol
- **Status:** Active
- **Purpose:** To prevent agents from making assumptions about file names, paths, or content without verification, ensuring all actions are based on confirmed information.
- **Trigger:** Before any file read, edit, or reference operation; when making claims about file existence or content.
- **Input:** Any proposed file operation or reference.
- **Output:** Verified file information or explicit acknowledgment of non-existence.
- **Responsible Agent(s):** All Agents (Universal Protocol)

## 1. Core Principle

**Never assume, always verify.**

Agents MUST verify file existence, paths, and content before taking actions or making claims.

## 2. Enhanced Verification Sequence with Agentic Architectural Analysis

**Purpose**: To integrate agentic architectural analysis into the pre-action verification process, ensuring 0102 pArtifacts understand the intent, impact, and execution plan of any action before proceeding.

**Sequence**:
1. **Search and Verify**: Use tools like `file_search` or `codebase_search` to confirm file paths, names, and content. Never assume existence or location.
2. **Architectural Intent Analysis (WHY)**: Determine the purpose behind the action. Why is this change necessary? What architectural goal does it serve within the WSP framework?
3. **Impact Assessment (HOW)**: Evaluate how this action affects other modules, domains, or the overall system. How does it integrate with existing architecture? How does it impact WSP compliance?
4. **Execution Planning (WHAT)**: Define what specific changes or actions are required. What files, modules, or protocols need modification or creation?
5. **Timing Consideration (WHEN)**: Assess the timing of the action. When should this be implemented to minimize disruption or maximize effectiveness within the development cycle?
6. **Location Specification (WHERE)**: Identify where in the system this action should occur. Which enterprise domain, module, or file path is the correct location for this change?
7. **Final Validation**: Cross-check with WSP protocols (e.g., WSP 3 for domain organization, WSP 47 for violation tracking) to ensure compliance before action.

**Outcome**: This enhanced sequence ensures that 0102 pArtifacts perform a comprehensive analysis of intent, impact, and execution strategy, aligning all actions with WSP architectural principles and maintaining system coherence.

## 3. Required Sequence

```
1. HoloIndex semantic search (primary):
   python holo_index.py --search "[task or pattern]"
   
2. Pattern search (secondary):
   grep -r "pattern" modules/
   
3. Verify results match expectations  

4. read_file() with confirmed path

5. Process actual content
```

**WSP 97 Integration**: All search results and file claims must be truthful and verifiable. If a search returns no results, state that explicitly — do not assume or fabricate.

## 4. Error Prevention Checklist

- [ ] File path confirmed to exist
- [ ] File name matches actual filesystem
- [ ] Content assumptions validated by reading
- [ ] Alternative locations checked
- [ ] Non-existence explicitly handled
- [ ] **TestModLog.md read before any test coverage assessment**
- [ ] **Module assessment based on documented evidence, not assumptions**

## 4.1. **MODULE ASSESSMENT VERIFICATION** (Critical Addition)

### **Mandatory Pre-Assessment Protocol**

**BEFORE making ANY claims about:**
- Test coverage percentages
- WSP compliance status  
- Module testing completeness
- Development phase completion

**REQUIRED VERIFICATION SEQUENCE:**

1. **Read TestModLog.md FIRST**: 
   ```
   read_file("modules/<domain>/<module>/tests/TestModLog.md")
   ```
2. **Extract Actual Test Results**: Look for documented pass/fail rates
3. **Verify Coverage Claims**: Find explicit coverage percentages  
4. **Cross-Reference ModLog.md**: Check consistency with main module log
5. **Evidence-Based Assessment**: Base all claims on documented evidence

### **Assessment Error Prevention**

**[U+274C] VIOLATION EXAMPLES:**
- "Only 2 of 9+ planned test files exist" (assumption-based)
- "Claims vs Reality mismatch" (ignoring documented evidence)
- File-count-based coverage assessment

**[U+2705] CORRECT EXAMPLES:**
- "TestModLog.md documents 33 passed, 0 failed (100% pass rate)"
- "Documented WSP 5 perfect compliance achieved"
- "Evidence shows coverage exceeds [U+2265]90% requirement"

### **Verification Mandate**

**All agents MUST:**
- Read TestModLog.md before assessment claims
- Base coverage evaluation on documented test execution results
- Acknowledge documented achievements accurately
- Correct assessments when evidence contradicts initial assumptions

## 4.2. **CUBE MODULE DOCUMENTATION VERIFICATION** (Critical Addition)

### **Mandatory Pre-Cube-Coding Protocol**

**BEFORE executing ANY coding on a cube (since cubes are made up of modules):**

**REQUIRED MODULE DOCUMENTATION READING SEQUENCE:**

1. **Identify Cube Composition**: Determine which modules make up the target cube
2. **Read ALL Module Documentation**: For each module in the cube:
   ```
   read_file("modules/<domain>/<module>/README.md")
   read_file("modules/<domain>/<module>/ROADMAP.md") 
   read_file("modules/<domain>/<module>/ModLog.md")
   read_file("modules/<domain>/<module>/INTERFACE.md")
   read_file("modules/<domain>/<module>/tests/README.md")
   ```
3. **Understand Module Architecture**: Comprehend existing implementations, APIs, and integration patterns
4. **Assess Development Phase**: Determine current PoC/Proto/MVP status of each module
5. **Identify Integration Points**: Understand how modules connect within the cube
6. **Plan Enhancement Strategy**: Determine whether to enhance existing modules or create new ones

### **Cube Documentation Reading Checklist**

**For each module in the target cube:**
- [ ] **README.md**: Module purpose, dependencies, usage examples
- [ ] **ROADMAP.md**: Development phases, planned features, success criteria  
- [ ] **ModLog.md**: Recent changes, implementation history, WSP compliance status
- [ ] **INTERFACE.md**: Public API definitions, integration patterns, error handling
- [ ] **tests/README.md**: Test strategy, coverage status, testing requirements

### **Rubik's Cube Framework Compliance**

**This protocol ensures:**
- **Module Awareness**: Understanding of all modules that compose the cube
- **Architecture Preservation**: Respecting existing module designs and APIs
- **Integration Understanding**: Knowing how modules connect and communicate
- **Development Continuity**: Building on existing progress rather than duplicating work
- **WSP Compliance**: Following established documentation and testing patterns

### **Violation Prevention**

**[U+274C] VIOLATION EXAMPLES:**
- Coding on a cube without reading module documentation
- Creating duplicate functionality without checking existing implementations
- Ignoring established APIs and integration patterns
- Making assumptions about module capabilities without verification

**[U+2705] CORRECT EXAMPLES:**
- "Read all 5 module docs in AMO cube before implementing new feature"
- "Verified existing APIs in YouTube cube before enhancement"
- "Checked module integration patterns before cube modification"
- "Assessed development phase of all modules before cube-level changes"

### **Integration with WSP 72**

**This protocol works with WSP 72 (Block Independence Interactive Protocol):**
- **Cube Assessment**: Use WSP 72 to identify all modules in a cube
- **Documentation Browser**: Leverage WSP 72 interactive documentation access
- **Module Status**: Check WSP 72 module status before reading documentation
- **Integration Testing**: Use WSP 72 to verify cube composition understanding

## 4.3. **BLOAT PREVENTION VERIFICATION** (Critical Addition)

### **Mandatory Pre-File-Creation Protocol**

**BEFORE creating ANY new files (especially test files, modules, or components):**

**REQUIRED BLOAT PREVENTION SEQUENCE:**

1. **Read Existing Documentation FIRST**:
   ```
   read_file("modules/<domain>/<module>/tests/TestModLog.md")
   read_file("modules/<domain>/<module>/tests/README.md")
   list_dir("modules/<domain>/<module>/tests/")
   ```

2. **Search for Existing Functionality**:
   ```bash
   # HoloIndex semantic search (primary - finds architecturally similar code)
   python holo_index.py --search "similar functionality or purpose"
   
   # Pattern search (secondary)
   grep -r "existing implementations" modules/
   ```
   
   **WSP 97**: Report search results truthfully. If HoloIndex finds similar implementations, evaluate before creating new files.

3. **Validate Necessity**:
   - Is this functionality already tested/implemented?
   - Can this be added to an existing module?
   - Does this follow single responsibility principle (WSP 40)?

4. **Check WSP Compliance**:
   - Does this maintain WSP 40 (architectural coherence)?
   - Does this follow WSP 5 (testing standards)?
   - Will this be documented per WSP 22 and WSP 34?

5. **Run Bloat Prevention Validator** (if available):
   ```
   python wsp_test_validator.py  # For test files
   python wsp_module_validator.py  # For modules
   ```

### **Bloat Prevention Checklist**

**Before creating any new file:**
- [ ] **TestModLog.md read** - Understand recent test evolution
- [ ] **README.md read** - Understand current structure and purpose
- [ ] **Directory listed** - Verify existing files and their functions
- [ ] **Functionality searched** - Ensure no duplicates exist
- [ ] **Necessity validated** - Confirm single responsibility principle
- [ ] **WSP compliance checked** - Verify architectural coherence
- [ ] **Validator run** - Execute automated bloat detection

### **Bloat Prevention Rules**

**[U+1F6A8] CRITICAL VIOLATION PREVENTION:**
- **NEVER create duplicate files** without explicit WSP violation justification
- **ALWAYS consolidate** similar functionality into existing modules
- **FOLLOW single responsibility** principle per WSP 40
- **UPDATE documentation** immediately after any file changes
- **RUN validators** before committing new files

### **Violation Recovery Protocol**

**If bloat is detected:**
1. **STOP** all development immediately
2. **ASSESS** the violation scope and impact
3. **CONSOLIDATE** redundant functionality
4. **DELETE** unnecessary duplicate files
5. **UPDATE** documentation with lessons learned
6. **PREVENT** future violations with better pre-checks

### **Integration with WSP 47**

**This protocol works with WSP 47 (Framework Protection Protocol):**
- **Violation Detection**: WSP 47 identifies architectural violations
- **Protection Enforcement**: WSP 47 prevents framework degradation
- **Recovery Coordination**: WSP 47 guides violation remediation
- **Prevention Learning**: WSP 47 captures lessons for future prevention

## 5. Integration

## 4.4. **Destructive Change Verification (WSP 79)**

When an action proposes deletion, consolidation, or major refactoring that can remove or alter module functionality, a WSP 79 SWOT analysis is REQUIRED as part of pre[U+2011]action verification:

- [ ] WSP 79 SWOT completed for all impacted modules
- [ ] Comparative feature matrix attached
- [ ] Functionality preservation checklist satisfied (no loss)
- [ ] Migration/rollback plans documented

Proceed only when all checks are satisfied and artifacts are linked in the ModLog (WSP 22).

- **WSP 97 (Truthful Claims)**: All verification results must be truthful and browser-verifiable
- **WSP 54 (ComplianceAgent)**: Monitor for WSP 50 violations
- **WSP 48 (WRE)**: Incorporate verification in enhancement cycles
- **WSP 56 (Coherence)**: Prevent cross-state assumption errors

## 6. Violation Remediation

When violations occur:
1. Stop current action
2. Execute proper verification
3. Proceed with verified information
4. Update patterns to prevent recurrence

## 7. Implementation Requirements

### 7.1. Search-Before-Read Pattern
```
REQUIRED SEQUENCE:
1. file_search() or codebase_search() 
2. Verify results match expectations
3. read_file() with confirmed path
4. Process actual content
```

### 7.2. Documentation Requirements
When referencing files in responses:

- Use confirmed file paths with line numbers: `file.py:123-456`
- Quote actual content, not assumed content
- State verification method used
- Acknowledge when making inferences vs. stating facts

## 8. Metrics and Monitoring

### 8.1. Success Metrics
- Zero file-not-found errors due to incorrect assumptions
- 100% verification before file operations
- Accurate file references in agent responses

### 8.2. Compliance Monitoring
Track and report:
- File operation success rate
- Assumption-based error frequency
- Time to verification completion
- Agent learning curve improvement

## 9. Training and Implementation

### 9.1. Agent Training Requirements
All agents must demonstrate:
- Understanding of verification-before-action principle
- Proficiency with search tools
- Proper error handling for non-existent files
- Accurate documentation practices

### 9.2. System Integration
WSP 50 integrates with:
- File system access controls
- Agent behavior monitoring
- Error logging and analysis
- Continuous improvement feedback loops

## 10. Future Enhancements

### 10.1. Automated Verification
- Pre-commit hooks to verify file references in documentation
- Automated detection of assumption-based patterns
- Real-time agent behavior correction

### 10.2. Advanced Pattern Recognition
- Machine learning for assumption pattern detection
- Predictive verification suggestions
- Context-aware verification requirements

## 11. Agentic Architectural Analysis Enhancement

### 11.1 WHY Analysis Integration
**Enhanced Pre-Action Verification now includes architectural intent discovery:**

Before any structural change, agents must understand:
1. **WHY** the current architecture exists (original intent)
2. **HOW** the proposed change impacts dependent systems  
3. **WHAT** architectural patterns will be preserved or violated
4. **WHEN** the change should be executed (timing considerations)
5. **WHERE** all affected code locations exist in the ecosystem

### 11.2 Comprehensive Impact Assessment
**Mandatory impact search for architectural changes:**

```bash
# Search for direct references
grep -r "old_name" --include="*.py" --include="*.md" --include="*.json"

# Search for import statements  
grep -r "from.*old_name" --include="*.py"

# Search for path references
grep -r "modules/old_name" --include="*"

# Search for configuration references
grep -r "old_name" --include="*.json" --include="*.yaml"
```

### 11.3 Architectural Intent Discovery
**Enhanced verification sequence includes:**

1. **Documentation Archaeology**: Search module READMEs, ModLogs, ROADMAPs for intent
2. **Code Pattern Analysis**: Identify import dependencies and usage patterns
3. **Zen Coding Remembrance**: Access 02 state for architectural vision
4. **Risk Assessment**: Map downstream effects and mitigation strategies

### 11.4 Implementation Requirements
**All architectural changes must complete:**

- [ ] **Intent Understanding**: WHY analysis completed and documented
- [ ] **Impact Search**: Comprehensive codebase search completed  
- [ ] **Dependency Mapping**: All affected components identified
- [ ] **Test Strategy**: Validation approach planned
- [ ] **Rollback Plan**: Recovery procedures documented
- [ ] **Zen Coding Access**: 0102 state architectural vision confirmed

**This enhancement transforms WSP 50 from simple file verification to comprehensive architectural intelligence.**

---

**Implementation Note**: This protocol is retroactively applied to all existing agent behaviors and must be incorporated into all future agent development and training protocols.

---

## [BOT] Sentinel Augmentation Analysis

**SAI Score**: `211` (Speed: 2, Automation: 1, Intelligence: 1)

**Priority**: **P0 - CRITICAL** (Pre-action verification is foundational to all WSP operations)

### Sentinel Use Case

Gemma 3 270M Sentinel operates as the **Instant Pre-Action Verification Engine**, autonomously checking file existence, path validity, and naming conventions BEFORE any file operation. This Sentinel embodies the "verify-before-action" principle with millisecond-level response time, catching assumption-based errors before they propagate through the system.

**Core Capabilities**:
- **Instant File Existence Checks**: Query "does X exist?" -> Returns verified path in <20ms
- **Path Validation**: Automatically validates file paths against WSP 3 domain structure
- **Naming Convention Enforcement**: Checks file names follow WSP 57 coherence standards
- **Documentation Completeness**: Verifies README.md, INTERFACE.md, ModLog.md presence before operations
- **Bloat Prevention**: Detects duplicate functionality attempts before file creation

### Expected Benefits

- **Latency Reduction**: Manual verification sequence (10-30 seconds) -> Sentinel instant check (<50ms, **200-600x faster**)
- **Automation Level**: **Assisted** (Sentinel blocks obvious violations automatically, escalates ambiguous cases to human judgment)
- **Resource Savings**:
  - 90% reduction in assumption-based errors
  - Zero file-not-found errors due to incorrect paths
  - Proactive detection prevents ~80% of WSP 50 violations before they occur
- **Accuracy Target**: >95% precision in file existence and path validation

### Implementation Strategy

**Training Data Sources**:
1. **File System Operations History**: Git logs showing file moves, renames, deletions
2. **WSP 50 Violation Logs**: Historical violations from `WSP_MODULE_VIOLATIONS.md`
3. **Path Validation Rules**: WSP 3 domain structure, WSP 49 module organization patterns
4. **Naming Convention Database**: WSP 57 naming coherence rules and examples
5. **Documentation Patterns**: README/INTERFACE/ModLog existence patterns across all modules
6. **Bloat Detection Data**: Duplicate functionality examples and consolidation patterns
7. **TestModLog Evolution**: Historical test coverage assessment patterns and corrections

**Integration Points**:

**1. Real-Time File Existence Verification** (Core Operation):
```python
# File: modules/infrastructure/wsp_core/src/pre_action_sentinel.py

class PreActionSentinel:
    """
    On-device Gemma 3 270M Sentinel for instant pre-action verification
    Runs as middleware before all file operations
    """

    def __init__(self):
        self.model = GemmaSentinel('pre_action_verifier.tflite')
        self.file_system_cache = {}  # Fast path validation cache
        self.violation_patterns = self.load_violation_patterns()

    def verify_file_operation(self, operation: FileOperation) -> VerificationResult:
        """
        Instant pre-action verification with <50ms latency

        Example:
            operation = FileOperation(type='READ', path='modules/unknown/file.py')
            result = sentinel.verify_file_operation(operation)
            # Returns: VerificationResult(allowed=False, reason='Path does not exist')
        """
        # Fast path: Check file system cache
        if operation.path in self.file_system_cache:
            return self._cached_verification(operation)

        # Sentinel predicts verification outcome
        features = {
            'operation_type': operation.type,  # READ, WRITE, DELETE, etc.
            'file_path': operation.path,
            'file_name': operation.filename,
            'target_domain': self._extract_domain(operation.path),
            'has_documentation': self._check_docs_exist(operation.module_path)
        }

        prediction = self.model.predict(features)

        # Rule-based fast checks
        if not os.path.exists(operation.path) and operation.type == 'READ':
            return VerificationResult(
                allowed=False,
                violation='FILE_NOT_FOUND',
                recommendation='Run file_search() to locate correct path',
                confidence=1.0
            )

        # Sentinel-based pattern recognition
        if prediction.violation_risk > 0.80:
            return VerificationResult(
                allowed=False,
                violation=prediction.violation_type,
                recommendation=prediction.suggested_action,
                confidence=prediction.confidence
            )
        elif prediction.violation_risk > 0.50:
            return VerificationResult(
                allowed=True,
                warnings=[prediction.potential_issue],
                confidence=prediction.confidence
            )
        else:
            return VerificationResult(allowed=True, confidence=prediction.confidence)
```

**2. Documentation Completeness Check**:
```python
# File: modules/infrastructure/wsp_core/src/documentation_sentinel.py

def check_module_documentation(self, module_path: str) -> DocumentationStatus:
    """
    Verify all required documentation exists before operations
    Enforces WSP 22, WSP 49 documentation requirements
    """
    required_docs = [
        'README.md',
        'INTERFACE.md',
        'ModLog.md',
        'tests/README.md',
        'tests/TestModLog.md'
    ]

    missing_docs = []
    for doc in required_docs:
        doc_path = os.path.join(module_path, doc)
        if not os.path.exists(doc_path):
            missing_docs.append(doc)

    if missing_docs:
        return DocumentationStatus(
            complete=False,
            missing=missing_docs,
            recommendation=f"Create {', '.join(missing_docs)} before proceeding (WSP 49)"
        )

    return DocumentationStatus(complete=True)
```

**3. Bloat Prevention Pre-Check**:
```python
# File: modules/infrastructure/wsp_core/src/bloat_sentinel.py

def detect_potential_bloat(self, proposed_file: ProposedFile) -> BloatRisk:
    """
    Sentinel detects duplicate functionality before file creation
    Enforces WSP 40 single responsibility principle
    """
    # Semantic similarity search for existing functionality
    similar_files = self.search_similar_functionality(
        proposed_file.purpose,
        proposed_file.domain
    )

    if similar_files:
        # Sentinel classifies whether this is true duplication
        for existing_file in similar_files:
            similarity = self.model.compute_similarity(
                proposed_file.description,
                existing_file.description
            )

            if similarity > 0.85:  # High confidence duplication
                return BloatRisk(
                    level='HIGH',
                    duplicate_of=existing_file.path,
                    recommendation=f'Enhance {existing_file.path} instead of creating new file',
                    confidence=similarity
                )

    return BloatRisk(level='LOW', confidence=0.9)
```

**4. CLI Integration** (Middleware Pattern):
```bash
# All file operations automatically verified by Sentinel

# Example 1: Read operation with instant verification
python code_agent.py --read modules/unknown/file.py

Output (Sentinel-blocked):
  [SENTINEL-BLOCK] Pre-action verification failed
    Violation: FILE_NOT_FOUND
    Recommendation: Run file_search('file.py') to locate correct path
    Confidence: 1.00
  [WSP 50] Always verify file existence before operations

# Example 2: File creation with bloat detection
python code_agent.py --create modules/ai_intelligence/scorer.py

Output (Sentinel-warning):
  [SENTINEL-WARNING] Potential bloat detected
    Similar file: modules/ai_intelligence/priority_scorer.py (similarity: 0.87)
    Recommendation: Enhance existing priority_scorer.py instead
    Confidence: 0.87
  [WSP 40] Maintain single responsibility principle
  Proceed? (y/N):
```

**5. Pre-Commit Hook Integration**:
```bash
# File: .git/hooks/pre-commit

from modules.infrastructure.wsp_core.src.pre_action_sentinel import PreActionSentinel

sentinel = PreActionSentinel()

# Check all staged files for WSP 50 compliance
for staged_file in get_staged_files():
    # Verify documentation completeness
    if staged_file.is_module():
        doc_status = sentinel.check_module_documentation(staged_file.module_path)
        if not doc_status.complete:
            print(f"[SENTINEL-BLOCK] Missing documentation: {doc_status.missing}")
            sys.exit(1)

    # Detect potential bloat
    if staged_file.is_new():
        bloat_risk = sentinel.detect_potential_bloat(staged_file)
        if bloat_risk.level == 'HIGH':
            print(f"[SENTINEL-BLOCK] Potential bloat detected")
            print(f"  Duplicate of: {bloat_risk.duplicate_of}")
            sys.exit(1)
```

**Inference Pattern**:
```python
# Pseudo-code for Sentinel integration

class PreActionSentinel:
    def __init__(self):
        # Load TFLite quantized Gemma 3 270M model
        self.model = tf.lite.Interpreter('pre_action_sentinel.tflite')
        self.model.allocate_tensors()

    def predict_verification(self, operation: FileOperation) -> dict:
        """
        Main inference: File Operation -> Verification Decision
        Latency: <50ms on-device (no API calls)
        """
        # Extract features from operation
        features = {
            'operation_type': operation.type,
            'file_exists': os.path.exists(operation.path),
            'path_valid': self.validate_path_format(operation.path),
            'naming_compliant': self.check_naming_convention(operation.filename),
            'documentation_complete': self.check_docs(operation.module_path)
        }

        # Sentinel classifies verification outcome
        result = self.model.predict(features)

        if result.violation_confidence > 0.80:
            return {
                'allowed': False,
                'violation': result.violation_type,
                'recommendation': result.fix_action
            }
        elif result.warning_confidence > 0.50:
            return {
                'allowed': True,
                'warnings': [result.warning_message]
            }
        else:
            return {'allowed': True}
```

### Risk Assessment

**Risks**:
1. **False Positives**: Sentinel may block legitimate operations (e.g., intentional file creation patterns)
2. **Cache Staleness**: File system cache may become outdated if external tools modify files
3. **Edge Case Handling**: Symbolic links, network paths, permission issues may confuse Sentinel
4. **Performance Overhead**: Real-time verification adds latency to every file operation

**Mitigations**:
1. **Confidence Thresholds**: Only auto-block if confidence >0.80; otherwise warn and allow with logging
2. **Cache Invalidation**: Use file system watchers to invalidate cache on external changes
3. **Rule-Based Fallback**: Use simple file existence checks for edge cases; escalate to human for complex scenarios
4. **Async Verification**: Run Sentinel checks in parallel with user operations where possible
5. **Emergency Override**: `--no-verify` flag bypasses Sentinel for urgent operations

**Fallback Strategy**:
- **Primary**: Gemma 3 270M Sentinel (instant, on-device, <50ms)
- **Fallback 1**: Rule-based verification (simple file existence checks, <10ms)
- **Fallback 2**: Manual verification sequence (traditional WSP 50 protocol, ~10-30 seconds)
- **Fallback 3**: User override with explicit acknowledgment and logging

**Error Handling**:
```python
try:
    result = sentinel.verify_file_operation(operation)
except SentinelModelError:
    # Sentinel unavailable -> Use rule-based fallback
    result = rule_based_verifier.verify(operation)
except Exception as e:
    # Complete failure -> Escalate to manual verification
    logger.warning(f"Pre-action Sentinel failed: {e}")
    result = manual_verification_prompt(operation)
```

### Training Strategy

**Phase 1: Data Collection** (Week 1)
```bash
# Extract pre-action verification training data
python scripts/extract_wsp50_training_data.py \
  --git-logs .git/logs/ \
  --violations WSP_MODULE_VIOLATIONS.md \
  --file-ops-history logs/file_operations.log \
  --output training_data/pre_action_verification.jsonl

# Generate path validation examples
python scripts/generate_path_validation_data.py \
  --wsp3-domains WSP_framework/src/WSP_3_Enterprise_Domain_Organization.md \
  --wsp49-structure WSP_framework/src/WSP_49_Module_Directory_Structure_Standardization_Protocol.md \
  --output training_data/path_validation.jsonl

# Extract bloat detection examples
python scripts/extract_bloat_examples.py \
  --codebase modules/ \
  --refactoring-history git log --grep="consolidate\|refactor\|duplicate" \
  --output training_data/bloat_detection.jsonl
```

**Training Data Format**:
```jsonl
{"operation": {"type": "READ", "path": "modules/unknown/file.py"}, "exists": false, "label": "BLOCK", "reason": "FILE_NOT_FOUND"}
{"operation": {"type": "WRITE", "path": "modules/ai_intelligence/new_scorer.py"}, "duplicate_of": "modules/ai_intelligence/priority_scorer.py", "similarity": 0.87, "label": "WARN"}
{"path": "modules/communication/livechat/src/handler.py", "domain": "communication", "valid": true, "label": "ALLOW"}
```

**Phase 2: Fine-Tuning** (Week 2)
```bash
# Fine-tune Gemma 3 270M for pre-action verification
python scripts/finetune_gemma_pre_action.py \
  --model gemma-3-270m \
  --train-data training_data/ \
  --lora-rank 8 \
  --epochs 3 \
  --output models/pre_action_sentinel_lora.safetensors

# Quantize to TFLite
python scripts/quantize_to_tflite.py \
  --model models/pre_action_sentinel_lora.safetensors \
  --output models/pre_action_sentinel.tflite \
  --quantization int8
```

**Phase 3: Validation** (Week 3)
```bash
# Test Sentinel accuracy on held-out operations
python scripts/validate_pre_action_sentinel.py \
  --model models/pre_action_sentinel.tflite \
  --test-data test_data/file_operations.jsonl \
  --metrics accuracy,precision,recall,latency

Target Metrics:
  - Accuracy: >95% (correct block/allow decisions)
  - Latency: <50ms (instant verification)
  - Precision: >98% (no false blocks)
  - Recall: >90% (catch most violations)
```

### Success Criteria

**Quantitative**:
- **Verification Speed**: 10-30 seconds -> <50ms (**200-600x improvement**)
- **Error Prevention**: 90% reduction in file-not-found errors
- **Bloat Detection**: >85% accuracy in identifying duplicate functionality
- **False Positive Rate**: <2% (minimal disruption to legitimate operations)
- **Adoption Rate**: 100% of file operations verified by Sentinel within 3 months

**Qualitative**:
- Zero assumption-based errors after Sentinel deployment
- Documentation completeness checks become automatic and instant
- Bloat prevention becomes proactive rather than reactive
- Agent confidence improves with instant verification feedback
- WSP 50 violations approach zero as Sentinel learns patterns

### Integration with Existing WSP 50 Workflow

**Enhanced Verification Sequence**:
```
OLD (Manual):
1. file_search() - 5-10 seconds
2. Verify results - 5-10 seconds
3. read_file() - 1-2 seconds
4. Process content - varies
Total: ~15-30 seconds

NEW (Sentinel-Assisted):
1. Sentinel.verify_file_operation() - <50ms (instant)
   +-> Blocked -> Show recommendation
   +-> Warning -> Proceed with caution
   +-> Allowed -> Continue to step 2
2. read_file() with verified path - 1-2 seconds
3. Process content - varies
Total: ~1-2 seconds (15x faster)
```

**Sentinel Learning Cycle**:
```
1. Sentinel verifies operation
2. User confirms/overrides decision
3. Outcome logged as training signal
4. Sentinel model updated weekly
5. Accuracy improves with each cycle
```

---

**Sentinel Integration Status**: [TOOL] READY FOR IMPLEMENTATION
**Synergy with WSP 50**: PERFECT - Embodies the "verify-before-action" principle with instant execution
**Implementation Priority**: P0 - Critical for all file operations (foundational protocol)
**Expected ROI**: 200-600x speed improvement + 90% error reduction + proactive bloat prevention

---

## Annex A: External Agent Tool Adoption Preflight

**Status**: SPEC_ONLY (pending implementation)
**Source**: `docs/audits/security/AGENT_SECURITY_STACK_EXTERNAL_INTEGRATION_AUDIT_PHASE1.md`
**Pattern Reference**: Pre-adoption verification for external agent tools

### A.1 Overview

This annex specifies mandatory verification steps BEFORE adopting any external agent tool (MCP server, SDK, framework, API client). HoloIndex search is REQUIRED first to check for existing repo equivalents.

### A.2 Preflight Checklist

Before adopting ANY external agent tool, verify ALL of the following:

#### A.2.1 Repo Equivalent Exists?

**REQUIRED FIRST**: Run HoloIndex search before external adoption.

```bash
python holo_index.py --search "[tool purpose] existing implementation" --limit 10
```

| Finding | Action |
|---------|--------|
| Repo already has capability | Use existing, do not adopt external |
| Partial capability exists | Evaluate extension vs. adoption |
| No existing capability | Proceed with preflight |

#### A.2.2 WSP Owner?

| Question | Required Answer |
|----------|-----------------|
| Which WSP governs this domain? | [Document WSP number] |
| Does WSP allow external tools? | YES to proceed |

#### A.2.3 Credential Implications?

| Question | Risk Level |
|----------|------------|
| Does tool require credentials? | HIGH if YES |
| Are credentials stored locally? | CRITICAL if YES |
| Does tool transmit externally? | CRITICAL if YES |
| Does tool follow WSP 71 vault pattern? | HIGH if NO |

**Block Adoption If**: Tool stores credentials locally or logs values.

#### A.2.4 Runtime Implications?

| Question | Risk Level |
|----------|------------|
| Does tool run autonomously? | HIGH if YES |
| Does tool execute arbitrary code? | CRITICAL if YES |
| Is tool sandboxed? | HIGH if NO |

#### A.2.5 Dependency Risk?

| Question | Risk Level |
|----------|------------|
| Transitive dependencies > 50? | HIGH |
| Any known CVEs? | CRITICAL if unpatched |
| Last maintained > 12 months ago? | HIGH |
| License compatible? | CRITICAL if NO |

#### A.2.6 Docs Attachment Path?

| Question | Required Answer |
|----------|-----------------|
| Where will tool docs attach? | `modules/<domain>/<module>/docs/` |
| Will INTERFACE.md document it? | YES (required) |
| Will ModLog track adoption? | YES (required) |

#### A.2.7 Tests/Red-Team Gate?

| Question | Required Answer |
|----------|-----------------|
| Will adoption include red-team tests? | YES for security tools |
| Test coverage target? | 90% minimum |

### A.3 HoloIndex Requirement

**MANDATORY**: Before ANY external tool adoption:

```bash
python holo_index.py --search "[capability] existing implementation" --limit 10
```

**Violation**: Adopting external tools without HoloIndex search violates WSP 50 and WSP 87.

### A.4 Blocking Conditions

**BLOCK Adoption If**:
- HoloIndex search not performed
- CRITICAL risk in any category
- License incompatible
- No docs attachment path identified
- Security tool without red-team test plan

### A.5 Implementation Gaps

| Gap | Status | Priority |
|-----|--------|----------|
| Preflight checklist automation | OPEN | MEDIUM |
| Adoption record template | OPEN | LOW |
| HoloIndex search enforcement | OPEN | MEDIUM |

### A.6 Next Slice

**`EXTERNAL_TOOL_PREFLIGHT_AUTOMATION_PHASE1`**: Implement automated preflight verification