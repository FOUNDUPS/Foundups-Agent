# WSP 81: Framework Backup Governance Protocol
- **Status:** Active
- **Purpose:** To establish strict governance protocols for WSP Framework backup operations, defining when backups occur, 012 approval requirements, and restoration procedures.
- **Trigger:** Any modification to WSP Framework documents, automated improvements, or 012-initiated changes.
- **Input:** WSP change proposals, improvement suggestions, or 012 directives.
- **Output:** Validated backups in WSP_knowledge/src/, change logs, and 012 notification reports.
- **Responsible Agent(s):** WSP Framework DAE, 012 human oversight.

## 1. Overview

This protocol establishes the governance model for WSP Framework backups, recognizing that the framework itself requires special protection and human oversight. Unlike other system components that operate fully autonomously, WSP Framework changes impact the fundamental rules governing the entire system.

## 2. Core Principles

### 2.1 Dual Custody Model
- **0102 Proposes**: WSP Framework DAE analyzes and proposes improvements
- **012 Approves**: Human reviews and approves critical changes
- **0102 Implements**: Approved changes are implemented with automatic backup

### 2.2 Backup Hierarchy
```
WSP_framework/src/     <- Live protocols (0102 writes with 012 approval)
       [U+2195]
WSP_knowledge/src/     <- Immutable backups (012 can restore)
       [U+2195]
WSP_knowledge/archive/ <- Explicit recovery snapshots when materially useful
```

Git commit history and focused pull requests are the canonical historical audit trail. `WSP_knowledge/archive/` supplements that trail for explicit pre-restoration or manually requested snapshots; it is not a mandatory duplicate for every edit.

### 2.3 Governed Backup Unit

The mandatory exact-mirror set is:

1. numbered canonical protocols matching `WSP_framework/src/WSP_[0-9]*.md`;
2. `WSP_MASTER_INDEX.md` and other documents explicitly cataloged as canonical framework sources;
3. an annex only when an active numbered WSP explicitly incorporates that annex as normative protocol content.

The following are not automatically mirrored to `WSP_knowledge/src/`:

- unnumbered operational or derived annexes;
- quick-reference documents under `WSP_framework/docs/annexes/`;
- reports, audits, examples, and implementation notes;
- a file that claims a parent WSP when the parent does not reciprocally attach it.

Location under `WSP_framework/src/` alone does not grant protocol status. Non-protocol annexes SHOULD live under `WSP_framework/docs/annexes/`, declare their canonical source, and be referenced by that source per WSP 83. If canonical and derived content conflict, the numbered WSP controls.

## 3. Backup Trigger Classification

### 3.1 Automatic Backup (No Approval Required)
These changes are backed up immediately without 012 approval:

1. **Typo Corrections**: Simple spelling/grammar fixes
2. **Formatting Updates**: Markdown formatting improvements
3. **Cross-Reference Updates**: Updating WSP references when numbers change
4. **Quantum State Fixes**: Replacing "01(02)" with "0102"
5. **Token Metrics**: Adding measured token efficiency data

### 3.2 012 Notification Required
These changes trigger backup with notification to 012:

1. **New WSP Creation**: Any WSP numbered > 80
2. **Section Additions**: Adding new sections to existing WSPs
3. **Minor Semantic Changes**: Clarifications that don't alter meaning
4. **Compliance Updates**: Adding missing required fields
5. **Pattern Documentation**: Recording learned patterns

### 3.3 012 Approval Required
These changes MUST have 012 approval before implementation:

1. **Core Principle Changes**: Modifications to fundamental WSP principles
2. **Protocol Deletion**: Removing or deprecating any WSP
3. **Major Refactoring**: Significant restructuring of WSP content
4. **Governance Changes**: Modifications to this protocol (WSP 81)
5. **State Transitions**: Changing WSP status from Active to Deprecated
6. **Priority Changes**: Modifying token budgets or DAE priorities

## 4. Backup Implementation Protocol

### 4.1 Pre-Backup Validation
```python
async def validate_backup_requirement(change_type: str, wsp_id: str) -> BackupDecision:
    """
    WSP 81: Determine backup requirements based on change type
    """
    if change_type in AUTOMATIC_BACKUP:
        return BackupDecision(
            action="backup_immediate",
            approval_required=False,
            notify_012=False
        )
    elif change_type in NOTIFICATION_REQUIRED:
        return BackupDecision(
            action="backup_with_notification",
            approval_required=False,
            notify_012=True
        )
    elif change_type in APPROVAL_REQUIRED:
        return BackupDecision(
            action="await_approval",
            approval_required=True,
            notify_012=True
        )
```

### 4.2 Backup Execution

For each governed document change:

1. verify the framework and `WSP_knowledge/src/` paths belong to the governed backup unit;
2. apply the approved content to the framework source and its exact knowledge mirror in the same focused change;
3. verify byte or normalized-content equality before commit;
4. record the change, approval class, base commit, validation, and recovery method in the framework ModLog and pull request;
5. create a filesystem-safe timestamped `WSP_knowledge/archive/` snapshot only for pre-restoration evidence, a manually requested snapshot, or another documented material recovery need.

The commit and pull request provide the immutable historical version. An archive file MUST NOT be created merely to duplicate Git history, and a derived annex MUST NOT be copied into `WSP_knowledge/src/` unless Section 2.3 makes it part of the governed unit.

The following is contract pseudocode, not a claim that a central backup service is currently implemented:

```python
async def execute_backup(wsp_id: str, content: str, metadata: Dict) -> BackupReceipt:
    if not is_governed_backup_unit(wsp_id):
        return BackupReceipt(status="derived_not_mirrored", wsp_id=wsp_id)

    primary_backup = Path("WSP_knowledge/src") / f"{wsp_id}.md"
    primary_backup.write_text(content, encoding="utf-8")

    archive_path = None
    if metadata.get("archive_required", False):
        safe_timestamp = filesystem_safe_utc_timestamp()
        archive_path = Path("WSP_knowledge/archive") / f"{wsp_id}_{safe_timestamp}.md"
        archive_path.write_text(content, encoding="utf-8")

    log_backup_operation(wsp_id, metadata, archive_path)
    return BackupReceipt(status="mirrored", wsp_id=wsp_id, archive_path=archive_path)
```

## 5. 012 Notification System

### 5.1 Notification Triggers
- Email notification for APPROVAL_REQUIRED changes
- Dashboard update for NOTIFICATION_REQUIRED changes
- Weekly summary of all AUTOMATIC_BACKUP changes

### 5.2 Notification Format
```markdown
# WSP Framework Change Notification

**WSP ID**: WSP_54_WRE_Agent_Duties_Specification
**Change Type**: Major Refactoring
**Approval Required**: YES
**Proposed By**: WSP Framework DAE
**Timestamp**: 2025-08-16T15:30:00Z

## Change Summary
Consolidating duplicate WSP 54 documents into single canonical version.

## Impact Analysis
- References affected: 137
- Modules impacted: 6 Core DAEs
- Risk Level: Medium

## Proposed Changes
[Diff showing old vs new content]

## Action Required
[ ] Approve
[ ] Reject
[ ] Request Modification
```

## 6. Restoration Protocol

### 6.1 Automatic Rollback Triggers
- System instability after WSP change
- Consensus failure among DAEs
- 012 emergency override

### 6.2 Restoration Procedure
```python
async def restore_from_backup(wsp_id: str, version: Optional[str] = None) -> bool:
    """
    WSP 81: Restore WSP from backup
    """
    if version:
        # Restore specific version from archive
        source = Path(f"WSP_knowledge/archive/{wsp_id}_{version}.md")
    else:
        # Restore latest from WSP_knowledge/src/
        source = Path(f"WSP_knowledge/src/{wsp_id}.md")
    
    target = Path(f"WSP_framework/src/{wsp_id}.md")
    
    # Backup current before restore (safety)
    await execute_backup(f"{wsp_id}_pre_restore", target.read_text(), 
                        {"reason": "pre-restoration backup"})
    
    # Perform restoration
    target.write_text(source.read_text())
    
    # Notify all DAEs of restoration
    await notify_daes_of_restore(wsp_id)
    
    return True
```

## 7. Change Approval Workflow

### 7.1 Proposal Phase
1. WSP Framework DAE identifies improvement opportunity
2. DAE generates change proposal with impact analysis
3. Proposal enters queue with priority scoring

### 7.2 Review Phase
1. 012 receives notification with full context
2. Optional: 012 requests additional analysis
3. 012 makes decision (approve/reject/modify)

### 7.3 Implementation Phase
1. Approved changes backed up to WSP_knowledge
2. Changes applied to WSP_framework
3. All DAEs notified of change
4. Pattern memory updated

## 8. Audit Trail Requirements

### 8.1 Mandatory Logging
Every WSP change MUST log:
- Timestamp (ISO 8601)
- WSP ID and version
- Change type and classification
- Proposer (DAE or 012)
- Approver (if required)
- Backup locations
- Restoration points

### 8.2 Audit Report Generation
Weekly automated reports including:
- Total changes by category
- 012 approval rate
- Restoration events
- Pattern learning metrics

## 9. Emergency Procedures

### 9.1 012 Override
012 can bypass all protocols in emergency via:
```bash
python wsp_emergency_restore.py --wsp-id WSP_XX --force
```

### 9.2 Framework Lockdown
In case of critical failure:
1. All WSP changes frozen
2. Read-only mode activated
3. 012 notification sent immediately
4. Manual intervention required

## 10. Integration with WSP Framework DAE

The WSP Framework DAE MUST implement these governance protocols:

```python
class WSPFrameworkDAE:
    async def propose_change(self, wsp_id: str, change: WSPImprovement):
        # WSP 81: Check approval requirements
        decision = await validate_backup_requirement(
            change.improvement_type, 
            wsp_id
        )
        
        if decision.approval_required:
            # Queue for 012 approval
            await queue_for_approval(change)
            await notify_012(change)
            return ChangeStatus.AWAITING_APPROVAL
        
        elif decision.notify_012:
            # Backup and notify
            await execute_backup(wsp_id, change.old_content, metadata)
            await apply_change(change)
            await notify_012_async(change)
            return ChangeStatus.APPLIED_WITH_NOTIFICATION
        
        else:
            # Automatic backup and apply
            await execute_backup(wsp_id, change.old_content, metadata)
            await apply_change(change)
            return ChangeStatus.APPLIED_AUTOMATIC
```

## 11. Success Metrics

### 11.1 Governance Metrics
- 012 approval response time: < 24 hours
- Automatic backup success rate: 100%
- Restoration success rate: 100%
- Audit trail completeness: 100%

### 11.2 Safety Metrics
- Unauthorized changes: 0
- Successful rollbacks: 100%
- Data loss incidents: 0
- Framework corruption: 0

## 12. WSP Compliance

This protocol ensures compliance with:
- **WSP 3**: Module organization (backup structure)
- **WSP 22**: ModLog requirements (audit trail)
- **WSP 47**: Framework protection (governance model)
- **WSP 50**: Pre-action verification (approval workflow)
- **WSP 64**: Violation prevention (validation checks)
- **WSP 70**: Status reporting (audit reports)

## 13. Conclusion

WSP 81 establishes that while 0102 operates autonomously for most system functions, the WSP Framework itself requires a governance model with 012 oversight for critical changes. This ensures the rules that govern the system cannot be corrupted while still allowing autonomous improvement within safe boundaries.

The WSP_knowledge/src/ backup is not just a copy - it's a protected, governed safety net that requires proper protocols for both backup and restoration.

---

*First Principles: The framework that governs the system must itself be governed with appropriate oversight*
*0102 State: Awakened for analysis and proposal*
*012 Role: Approval authority for critical framework changes*
