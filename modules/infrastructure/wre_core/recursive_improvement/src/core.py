# -*- coding: utf-8 -*-
import sys
import io


import json
import traceback
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
import hashlib
import re
import time
import threading

# === UTF-8 ENFORCEMENT (WSP 90) ===
# Prevent UnicodeEncodeError on Windows systems
# Only apply when running as main script, not during import
if __name__ == '__main__' and sys.platform.startswith('win'):
    try:
        pass  # UTF-8 wrapping handled by entrypoint (WSP 90)
    except (OSError, ValueError):
        # Ignore if stdout/stderr already wrapped or closed
        pass
# === END UTF-8 ENFORCEMENT ===

class PatternType(Enum):
    """Types of patterns that can be extracted"""
    ERROR = "error"
    VIOLATION = "violation"
    PERFORMANCE = "performance"
    BEHAVIORAL = "behavioral"
    STRUCTURAL = "structural"

@dataclass
class ErrorPattern:
    """Represents an extracted error pattern"""
    pattern_id: str
    pattern_type: PatternType
    error_type: str
    error_message: str
    stack_trace: List[str]
    context: Dict[str, Any]
    frequency: int = 1
    first_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    last_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        result = asdict(self)
        result['pattern_type'] = self.pattern_type.value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ErrorPattern':
        """Create from dictionary"""
        data['pattern_type'] = PatternType(data['pattern_type'])
        return cls(**data)

@dataclass
class Solution:
    """Represents a solution to an error pattern"""
    solution_id: str
    pattern_id: str
    solution_type: str  # 'fix', 'prevention', 'optimization'
    description: str
    implementation: str
    confidence: float  # 0.0 to 1.0
    source: str  # 'quantum', 'learned', 'manual'
    effectiveness: float = 0.0  # Measured after application
    token_savings: int = 0  # Legacy unverified estimate; never measured usage
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Solution':
        """Create from dictionary"""
        return cls(**data)

@dataclass
class Improvement:
    """Represents an improvement to the system"""
    improvement_id: str
    pattern_id: str
    solution_id: str
    target: str  # WSP number, module path, etc.
    change_type: str  # 'update', 'add', 'remove', 'refactor'
    before_state: str
    after_state: str
    applied: bool = False
    applied_at: Optional[str] = None
    rollback_available: bool = True
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Improvement':
        """Create from dictionary"""
        return cls(**data)
