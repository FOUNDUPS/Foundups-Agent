#!/usr/bin/env python3
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

WSP 85 Violation Prevention Script
Automatically detects and prevents root directory pollution

WSP 85 Compliance:
- Monitors root directory for prohibited files
- Provides guidance on correct file placement
- Enforces WSP 85 Anti-Pollution Protocol
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Tuple

class WSP85Validator:
    """WSP 85 Root Directory Protection Validator"""
    
    # WSP 85 ABSOLUTE PROHIBITIONS in root directory
    PROHIBITED_PATTERNS = [
        "run_*.py",
        "test_*.py",
        "*_test.py",
        "check_*.py",
        "fix_*.py",
        "verify_*.py",
        "diagnose_*.py",
        "inspect_*.py",
        "approve_*.py",
        "get_*.py",
        "close_*.py",
        "execute_*.py",
        "batch_*.py",
        "check_*.sh",
        "fix_*.sh",
        "verify_*.sh",
        "SESSION_BACKUP_*.md",
        "*_temp.py",
        "*_debug.py",
        "temp_*",
        "debug_*"
    ]
    
    # WSP 85 ALLOWED files in root directory
    ALLOWED_ROOT_FILES = {
        "main.py",
        "README.md",
        "CLAUDE.md",
        "ModLog.md",
        "ROADMAP.md",
        "requirements.txt",
        ".gitignore",
        ".env",
        ".env.example",
        ".coveragerc",
        ".coverage",
        ".firebaserc",
        ".mcp.json",
        "CONTRIBUTING.md",
        "Dockerfile",
        "LICENSE",
        "NAVIGATION.py",
        "firebase.json",
        "firestore.indexes.json",
        "firestore.rules",
        "holo_index.py",
        "package-lock.json",
        "package.json",
        "pnpm-lock.yaml",
        "pyrightconfig.json",
        "pytest.ini",
        "vercel.json",
    }
    
    # WSP 85 PROHIBITED directories in root
    PROHIBITED_ROOT_DIRS = {
        "debug",
        "backup"
    }
    
    # WSP 85 CORRECT placement guidelines
    PLACEMENT_GUIDE = {
        "test_*.py": "modules/{domain}/{module}/tests/",
        "*_test.py": "modules/{domain}/{module}/tests/",
        "run_*.py": "modules/{domain}/{module}/scripts/",
        "check_*.py": "scripts/verification/ or module scripts/",
        "fix_*.py": "scripts/ or module scripts/",
        "verify_*.py": "scripts/verification/ or module tests/",
        "diagnose_*.py": "scripts/diagnostics/ or module scripts/",
        "inspect_*.py": "scripts/diagnostics/ or module scripts/",
        "approve_*.py": "scripts/verification/ or module scripts/",
        "get_*.py": "scripts/verification/ or module scripts/",
        "close_*.py": "scripts/ or module scripts/",
        "execute_*.py": "scripts/ or module scripts/",
        "batch_*.py": "scripts/ or module scripts/",
        "check_*.sh": "scripts/verification/ or scripts/diagnostics/",
        "fix_*.sh": "scripts/ or module scripts/",
        "verify_*.sh": "scripts/verification/ or module tests/",
        "*_script.py": "modules/{domain}/{module}/scripts/",
        "SESSION_BACKUP_*.md": "logs/",
        "*_temp.*": "modules/{domain}/{module}/temp/ (or delete)",
        "*_debug.*": "modules/{domain}/{module}/debug/ (or delete)"
    }
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        
    def scan_root_directory(self) -> Dict[str, List[str]]:
        """Scan root directory for WSP 85 violations"""
        violations = {
            "prohibited_files": [],
            "prohibited_dirs": [],
            "unknown_files": []
        }
        
        for item in self.project_root.iterdir():
            if item.is_file():
                if item.name not in self.ALLOWED_ROOT_FILES:
                    if self._matches_prohibited_pattern(item.name):
                        violations["prohibited_files"].append(str(item))
                    elif not item.name.startswith('.'):  # Ignore hidden files
                        violations["unknown_files"].append(str(item))
                        
            elif item.is_dir() and item.name in self.PROHIBITED_ROOT_DIRS:
                violations["prohibited_dirs"].append(str(item))
                
        return violations
    
    def _matches_prohibited_pattern(self, filename: str) -> bool:
        """Check if filename matches prohibited patterns"""
        import fnmatch
        return any(fnmatch.fnmatch(filename, pattern) 
                  for pattern in self.PROHIBITED_PATTERNS)
    
    def get_correct_placement(self, filename: str) -> str:
        """Get correct placement suggestion for a file"""
        for pattern, placement in self.PLACEMENT_GUIDE.items():
            import fnmatch
            if fnmatch.fnmatch(filename, pattern):
                return placement
        return "modules/{appropriate_domain}/{appropriate_module}/"
    
    def validate_and_report(self) -> bool:
        """Validate root directory and report violations"""
        violations = self.scan_root_directory()
        has_violations = any(violations.values())
        
        if has_violations:
            print("\n" + "="*60)
            print("[ALERT] WSP 85 ROOT DIRECTORY VIOLATIONS DETECTED")
            print("="*60)
            
            if violations["prohibited_files"]:
                print("\n[FAIL] PROHIBITED FILES IN ROOT:")
                for file_path in violations["prohibited_files"]:
                    filename = Path(file_path).name
                    correct_location = self.get_correct_placement(filename)
                    print(f"  • {filename}")
                    print(f"    -> MOVE TO: {correct_location}")
            
            if violations["prohibited_dirs"]:
                print("\n[FAIL] PROHIBITED DIRECTORIES IN ROOT:")
                for dir_path in violations["prohibited_dirs"]:
                    dirname = Path(dir_path).name
                    print(f"  • {dirname}/ -> Contents should be in module subdirectories")
            
            if violations["unknown_files"]:
                print("\n[U+26A0]️  UNKNOWN FILES IN ROOT (may violate WSP 85):")
                for file_path in violations["unknown_files"]:
                    filename = Path(file_path).name
                    print(f"  • {filename} -> Consider moving to appropriate module")
            
            print(f"\n[U+1F4D6] WSP 85 Reference: Root Directory Anti-Pollution Protocol")
            print(f"[PIN] Only these files allowed in root: {', '.join(self.ALLOWED_ROOT_FILES)}")
            print("="*60)
            
        else:
            print("[OK] WSP 85 COMPLIANCE: Root directory is clean")
            
        return not has_violations
    
    def suggest_fixes(self, violations: Dict[str, List[str]]) -> List[str]:
        """Generate fix commands for violations"""
        fixes = []
        
        for file_path in violations.get("prohibited_files", []):
            filename = Path(file_path).name
            if filename.startswith("test_"):
                # Test files - need to determine module based on content
                fixes.append(f"# Analyze {filename} to determine correct module")
                fixes.append(f"# mv {filename} modules/{{domain}}/{{module}}/tests/")
            elif filename.startswith("run_"):
                fixes.append(f"mv {filename} modules/{{domain}}/{{module}}/scripts/")
        
        for dir_path in violations.get("prohibited_dirs", []):
            dirname = Path(dir_path).name
            if dirname == "tests":
                fixes.append("# Move test files to appropriate module test directories")
                fixes.append("# rmdir tests  # After moving contents")
        
        return fixes


def main():
    """Main validation function"""
    print("[SEARCH] WSP 85 Root Directory Validation")
    print("Checking for Anti-Pollution Protocol violations...")
    
    validator = WSP85Validator()
    is_compliant = validator.validate_and_report()
    
    if not is_compliant:
        print("\n[U+1F6E0]️  FIX VIOLATIONS IMMEDIATELY")
        print("WSP 85 violations must be resolved before continuing development")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
