# Shield Interface Contract

**Module**: `modules/foundups/shield`  
**Version**: 0.1.0 (SPECIFIED)  
**Status**: Interface contracts defined, no runtime implementation  

---

## Overview

This document defines the future public contracts for Shield. All contracts are in SPECIFIED state - they define expected behavior but have no implementation.

---

## 1. AutoCase Contract (Future)

### 1.1 Document Classification Request

```python
@dataclass
class AutoCaseRequest:
    """Request for document classification."""
    
    session_id: str
    """Ephemeral session identifier (not user PII)."""
    
    document_hint: str
    """User-provided hint about document type (optional)."""
    
    extracted_text_preview: str
    """First 500 chars of extracted text (redacted)."""
    
    metadata_only: bool = True
    """If True, only extract safe metadata. Default: True."""
```

### 1.2 Document Classification Response

```python
@dataclass
class AutoCaseResponse:
    """Response from document classification."""
    
    document_type: str
    """Classified document type (e.g., 'legal_notice', 'bill', 'contract')."""
    
    urgency: str
    """Urgency level: 'immediate', 'soon', 'routine', 'informational'."""
    
    deadlines: List[Deadline]
    """Extracted deadline information (dates only, no content)."""
    
    suggested_actions: List[str]
    """Generic action suggestions (not legal advice)."""
    
    confidence: float
    """Classification confidence 0.0-1.0."""
    
    disclaimers: List[str]
    """Required disclaimers (always includes 'not legal advice')."""
```

### 1.3 Deadline Structure

```python
@dataclass
class Deadline:
    """Safe deadline metadata."""
    
    date: str
    """ISO date string."""
    
    days_remaining: int
    """Days until deadline."""
    
    action_type: str
    """Generic action type: 'respond', 'pay', 'appear', 'file'."""
```

---

## 2. Action Plan Contract (Future - Prototype Phase)

### 2.1 Action Plan Request

```python
@dataclass
class ActionPlanRequest:
    """Request for action plan generation."""
    
    session_id: str
    document_type: str
    urgency: str
    deadlines: List[Deadline]
    user_preferences: Dict[str, Any]
    """User preferences (time availability, budget constraints)."""
```

### 2.2 Action Plan Response

```python
@dataclass
class ActionPlanResponse:
    """Generated action plan (not legal advice)."""
    
    steps: List[ActionStep]
    """Ordered action steps."""
    
    timeline: str
    """Suggested timeline summary."""
    
    resources: List[Resource]
    """Relevant public resources (legal aid, government sites)."""
    
    disclaimers: List[str]
```

---

## 3. Defense Twin Contract (Future - MVP Phase)

### 3.1 Twin Session

```python
@dataclass
class DefenseTwinSession:
    """Persistent defense twin session."""
    
    twin_id: str
    """Unique twin identifier."""
    
    created_at: datetime
    started_cases: List[str]
    """Case identifiers (not content)."""
    
    active_deadlines: List[Deadline]
    """Aggregated active deadlines."""
```

---

## 4. Truth Boundaries

All interfaces MUST enforce:

| Boundary | Enforcement |
|----------|-------------|
| No raw document storage | Reject if `metadata_only=False` not explicitly authorized |
| No PID/PII storage | Strip before any persistence |
| No legal advice | Include disclaimer in every response |
| No payment processing | Interface has no payment fields |

---

## 5. Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-05-25 | Initial interface specification (SPECIFIED, no impl) |
