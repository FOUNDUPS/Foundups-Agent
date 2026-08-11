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

Foundups Modular Audit System (FMAS)

# WSP Compliance Headers
- **WSP 4**: FMAS Validation Protocol (Core functionality + Security scanning)
- **WSP 62**: Large File and Refactoring Enforcement Protocol (Size checking)
- **WSP 47**: Module Violation Tracking Protocol (Violation logging)
- **WSP 22**: Traceable Narrative Protocol (Logging standards)
- **WSP 71**: Secrets Management Protocol (Secret detection scanning)

This tool performs an audit of the module structure, test existence, and security vulnerability scanning.
This helps ensure that all modules follow the established standards and security requirements.

Mode 1: Structure check only
- Validates that each module has a src/ directory
- Validates that each module has a tests/ directory
- Checks for the presence of the module interface file
- Checks for the presence of the module.json dependency manifest
- Performs security vulnerability scanning (pip-audit, bandit, secret detection)
- Reports any missing components as findings
- NOW SUPPORTS: Enterprise Domain architecture (WSP 3)
- NOW SUPPORTS: WSP 62 file size compliance checking
- NOW SUPPORTS: WSP 4 security vulnerability scanning

Mode 2: Baseline comparison
- Performs all Mode 1 checks
- Additionally compares the module structure against a baseline
- Reports added, modified, and removed modules and files
- NOW SUPPORTS: Hierarchical domain structure comparison
- NOW SUPPORTS: WSP 62 file size compliance checking
- NOW SUPPORTS: Comprehensive security vulnerability baseline comparison
"""

import argparse
import ast
from datetime import date
import json
import logging
import os
import sys
import hashlib
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

VERSION = "0.8.1"
BASELINE_MISSING = object()
ADVISORY_ARCHIVE_MAX_THRESHOLD = 1000

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)

# Define critical modules that should prompt warnings if modified
CRITICAL_MODULES = {"core", "security", "auth", "config"}

# Security scanning configuration (WSP 4 Section 4.4.1)
SECURITY_SCAN_TOOLS = {
    "pip_audit": {
        "command": ["pip-audit", "--desc", "--format=json"],
        "description": "Python dependency vulnerability scanning",
        "required": True
    },
    "bandit": {
        "command": ["bandit", "-r", ".", "-f", "json"],
        "description": "Python code security analysis",
        "required": True
    },
    "npm_audit": {
        "command": ["npm", "audit", "--json"],
        "description": "Node.js dependency vulnerability scanning",
        "required": False  # Only if package.json exists
    }
}

# Security severity thresholds (WSP 4)
SECURITY_THRESHOLDS = {
    "HIGH": "FAIL",      # Block integration
    "MEDIUM": "WARNING", # Require acknowledgment  
    "LOW": "LOG"         # Track for future resolution
}

# Secret detection patterns (WSP 71)
SECRET_PATTERNS = [
    r'(?i)(password|passwd|pwd)\s*[=:]\s*["\']?[^"\'\s]{8,}',
    r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']?[^"\'\s]{16,}',
    r'(?i)(secret|token)\s*[=:]\s*["\']?[^"\'\s]{16,}',
    r'(?i)(access[_-]?key)\s*[=:]\s*["\']?[^"\'\s]{16,}',
    r'(?i)(private[_-]?key)\s*[=:]\s*["\']?[^"\'\s]{32,}',
    r'-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----',
    r'(?i)mongodb://[^/\s]+:[^@\s]+@',
    r'(?i)postgres://[^/\s]+:[^@\s]+@'
]

# Define recognized Enterprise Domains (WSP 3)
ENTERPRISE_DOMAINS = {
    "ai_intelligence",
    "communication", 
    "platform_integration",
    "infrastructure",
    "data_processing",
    "gamification",
    "foundups",
    "blockchain",
    "development",
    "aggregation"
}

# Define documented architectural exceptions (WSP 3, Section 1)
ARCHITECTURAL_EXCEPTIONS = {
    "wre_core"  # WRE Core Engine - WSP 46 documented exception
}

def is_module_directory(path):
    """
    Check if a directory is an actual module (has src/ and/or tests/ directories).
    
    Args:
        path: Path to check
        
    Returns:
        bool: True if this appears to be a module directory
    """
    if not path.is_dir():
        return False
        
    # A module should have at least src/ directory
    src_dir = path / "src"
    tests_dir = path / "tests"
    
    return src_dir.exists() or tests_dir.exists()

def discover_modules_recursive(modules_root):
    """
    Recursively discover all modules in the Enterprise Domain structure.
    
    Args:
        modules_root: Path to the modules directory
        
    Returns:
        list: List of tuples (module_path, module_name, domain_path)
    """
    if not modules_root.exists() or not modules_root.is_dir():
        return []
    
    modules = []
    
    def scan_directory(current_path, relative_path=""):
        """Recursively scan for modules."""
        for item in current_path.iterdir():
            if not item.is_dir() or item.name.startswith('.') or item.name == '__pycache__':
                continue
                
            item_relative = relative_path + "/" + item.name if relative_path else item.name
            
            # Check if this is a module
            if is_module_directory(item):
                modules.append((item, item.name, item_relative))
                logging.debug(f"Found module: {item_relative}")
            else:
                # Continue scanning deeper
                scan_directory(item, item_relative)
    
    scan_directory(modules_root)
    return modules

def validate_baseline_path(baseline_path):
    """
    Validate that the baseline path exists and contains a modules directory.
    
    Args:
        baseline_path: Path to the baseline directory
        
    Returns:
        bool: True if the baseline path is valid, False otherwise
    """
    if not baseline_path.exists():
        logging.error(f"Baseline path {baseline_path} does not exist")
        return False
        
    if not baseline_path.is_dir():
        logging.error(f"Baseline path {baseline_path} is not a directory")
        return False
        
    modules_dir = baseline_path / "modules"
    if not modules_dir.exists() or not modules_dir.is_dir():
        logging.error(f"Baseline directory {baseline_path} does not contain a modules directory")
        return False
        
    return True


def _git_value(root, *args):
    """Return one bounded Git value without shell interpretation."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def validate_authoritative_baseline(candidate_root, baseline_root):
    """Bind Mode 2 to a clean checkout of the candidate's Git merge base."""
    candidate_common = _git_value(candidate_root, "rev-parse", "--git-common-dir")
    baseline_common = _git_value(baseline_root, "rev-parse", "--git-common-dir")
    candidate_head = _git_value(candidate_root, "rev-parse", "HEAD")
    baseline_head = _git_value(baseline_root, "rev-parse", "HEAD")
    merge_base = _git_value(candidate_root, "merge-base", "HEAD", "origin/main")
    baseline_dirty = _git_value(
        baseline_root, "status", "--porcelain", "--untracked-files=no"
    )
    baseline_untracked = _git_value(
        baseline_root, "ls-files", "--others", "--exclude-standard", "--", "modules"
    )
    if not all((candidate_common, baseline_common, candidate_head, baseline_head, merge_base)):
        return False, "baseline Git authority unavailable"
    if Path(candidate_common).resolve() != Path(baseline_common).resolve():
        return False, "baseline uses a different Git authority root"
    if baseline_dirty is None or baseline_untracked is None:
        return False, "baseline cleanliness proof unavailable"
    if baseline_dirty or baseline_untracked:
        return False, "baseline checkout is not clean"
    if baseline_head != merge_base:
        return False, "baseline HEAD is not the candidate merge base"
    return True, ""


def _git_rename_map(candidate_root):
    """Map candidate paths to exact-base paths using Git rename evidence."""
    merge_base = _git_value(candidate_root, "merge-base", "HEAD", "origin/main")
    if not merge_base:
        return {}
    output = _git_value(
        candidate_root,
        "diff",
        "--name-status",
        "--find-renames=50%",
        merge_base,
        "--",
        "modules",
    )
    if output is None:
        return {}
    renames = {}
    for line in output.splitlines():
        fields = line.split("\t")
        if len(fields) == 3 and fields[0].startswith("R"):
            renames[Path(fields[2]).as_posix()] = Path(fields[1]).as_posix()
    return renames

def discover_source_files(root_path):
    """
    Discover all source files in the modules directory using Enterprise Domain structure.
    
    Args:
        root_path: Path to the project root
        
    Returns:
        tuple: (
            dict: Dictionary of module paths to sets of file paths relative to the module directory,
            set: Set of flat files in the modules directory (not in a module subdirectory)
        )
    """
    modules_dir = root_path / "modules"
    if not modules_dir.exists() or not modules_dir.is_dir():
        logging.error(f"Modules directory {modules_dir} does not exist or is not a directory")
        return {}, set()
        
    module_files = {}
    flat_files = set()
    
    # First, scan for flat files directly in the modules directory
    for file_path in modules_dir.glob('*'):
        if file_path.is_file() and not file_path.name.startswith('.'):
            # Store relative to modules directory
            flat_files.add(file_path.name)
    
    # Discover all modules using recursive search
    modules = discover_modules_recursive(modules_dir)
    
    for module_path, module_name, domain_path in modules:
        # Use domain_path as the key to maintain uniqueness
        module_key = domain_path
        module_files[module_key] = set()
        
        # Find all source files in the module directory (recursively)
        for file_path in module_path.glob('**/*'):
            if file_path.is_file() and not file_path.name.startswith('.') and '__pycache__' not in str(file_path):
                # Store the path relative to the module directory
                relative_path = file_path.relative_to(module_path)
                module_files[module_key].add(str(relative_path))  # Convert Path to string for consistent comparison
    
    return module_files, flat_files

def perform_security_scan(module_path: Path, domain_path: str) -> List[str]:
    """
    Perform security vulnerability scanning for a module (WSP 4 Section 4.4.1).
    
    Args:
        module_path: Path to the module directory
        domain_path: Domain path for reporting
        
    Returns:
        List of security findings
    """
    findings = []
    
    # Check if we're in the module directory for scanning
    original_cwd = os.getcwd()
    
    try:
        os.chdir(module_path)
        
        # Python dependency vulnerability scanning (pip-audit)
        if (module_path / "requirements.txt").exists():
            pip_audit_findings = run_pip_audit()
            findings.extend(_wrap_security_findings(domain_path, pip_audit_findings))
        
        # Python code security analysis (bandit)
        if (module_path / "src").exists():
            bandit_findings = run_bandit()
            findings.extend(_wrap_security_findings(domain_path, bandit_findings))
        
        # Node.js dependency vulnerability scanning (npm audit)
        if (module_path / "package.json").exists():
            npm_audit_findings = run_npm_audit()
            findings.extend(_wrap_security_findings(domain_path, npm_audit_findings))
            
    except Exception as e:
        findings.append(f"SECURITY_SCAN_FAILED: {domain_path} - Security scan failed: {str(e)}")
    finally:
        os.chdir(original_cwd)
    
    return findings

def run_pip_audit() -> List[str]:
    """Run pip-audit for Python dependency vulnerability scanning."""
    findings = []
    
    try:
        result = subprocess.run(
            ["pip-audit", "--desc", "--format=json"],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            # Parse JSON output
            if result.stdout.strip():
                try:
                    audit_data = json.loads(result.stdout)
                    vulnerabilities = audit_data.get("vulnerabilities", [])
                    
                    for vuln in vulnerabilities:
                        package = vuln.get("package", "unknown")
                        severity = vuln.get("severity", "unknown").upper()
                        description = vuln.get("description", "No description")
                        
                        if severity in SECURITY_THRESHOLDS:
                            threshold = SECURITY_THRESHOLDS[severity]
                            findings.append(f"SECURITY_VULNERABILITY_{severity}: {package} - {description[:100]}...")
                            
                            if threshold == "FAIL":
                                findings.append(f"SECURITY_AUDIT_FAIL: High-severity vulnerability in {package} blocks integration")
                                
                except json.JSONDecodeError:
                    findings.append("SECURITY_SCAN_ERROR: Failed to parse pip-audit JSON output")
        else:
            findings.append(f"SECURITY_SCAN_ERROR: pip-audit failed with code {result.returncode}")
            
    except subprocess.TimeoutExpired:
        findings.append("SECURITY_SCAN_ERROR: pip-audit timed out")
    except FileNotFoundError:
        findings.append("SECURITY_SCAN_ERROR: pip-audit tool not found (install with 'pip install pip-audit')")
    except Exception as e:
        findings.append(f"SECURITY_SCAN_ERROR: pip-audit failed: {str(e)}")
    
    return findings

def run_bandit() -> List[str]:
    """Run bandit for Python code security analysis."""
    findings = []
    
    try:
        result = subprocess.run(
            ["bandit", "-r", "src/", "-f", "json"],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        # Bandit returns non-zero when issues are found, so check for JSON output
        if result.stdout.strip():
            try:
                bandit_data = json.loads(result.stdout)
                results = bandit_data.get("results", [])
                
                for issue in results:
                    severity = issue.get("issue_severity", "unknown").upper()
                    test_name = issue.get("test_name", "unknown")
                    filename = issue.get("filename", "unknown")
                    line_number = issue.get("line_number", 0)
                    
                    if severity in SECURITY_THRESHOLDS:
                        threshold = SECURITY_THRESHOLDS[severity]
                        findings.append(f"SECURITY_VULNERABILITY_{severity}: {test_name} in {filename}:{line_number}")
                        
                        if threshold == "FAIL":
                            findings.append(f"SECURITY_AUDIT_FAIL: High-severity security issue in {filename}")
                            
            except json.JSONDecodeError:
                findings.append("SECURITY_SCAN_ERROR: Failed to parse bandit JSON output")
        
    except subprocess.TimeoutExpired:
        findings.append("SECURITY_SCAN_ERROR: bandit timed out")
    except FileNotFoundError:
        findings.append("SECURITY_SCAN_ERROR: bandit tool not found (install with 'pip install bandit')")
    except Exception as e:
        findings.append(f"SECURITY_SCAN_ERROR: bandit failed: {str(e)}")
    
    return findings

def run_npm_audit() -> List[str]:
    """Run npm audit for Node.js dependency vulnerability scanning."""
    findings = []
    
    try:
        result = subprocess.run(
            ["npm", "audit", "--json"],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.stdout.strip():
            try:
                audit_data = json.loads(result.stdout)
                vulnerabilities = audit_data.get("vulnerabilities", {})
                
                for package, vuln_info in vulnerabilities.items():
                    severity = vuln_info.get("severity", "unknown").upper()
                    
                    if severity in SECURITY_THRESHOLDS:
                        threshold = SECURITY_THRESHOLDS[severity]
                        findings.append(f"SECURITY_VULNERABILITY_{severity}: npm package {package}")
                        
                        if threshold == "FAIL":
                            findings.append(f"SECURITY_AUDIT_FAIL: High-severity vulnerability in npm package {package}")
                            
            except json.JSONDecodeError:
                findings.append("SECURITY_SCAN_ERROR: Failed to parse npm audit JSON output")
        
    except subprocess.TimeoutExpired:
        findings.append("SECURITY_SCAN_ERROR: npm audit timed out")
    except FileNotFoundError:
        findings.append("SECURITY_SCAN_ERROR: npm tool not found")
    except Exception as e:
        findings.append(f"SECURITY_SCAN_ERROR: npm audit failed: {str(e)}")
    
    return findings

def scan_for_secrets(modules_dir: Path) -> List[str]:
    """
    Scan for accidentally committed secrets (WSP 71 compliance).
    
    Args:
        modules_dir: Path to modules directory
        
    Returns:
        List of secret detection findings
    """
    findings = []
    
    try:
        # Compile secret patterns
        compiled_patterns = [re.compile(pattern) for pattern in SECRET_PATTERNS]
        
        # Scan all Python, JavaScript, and configuration files
        file_patterns = ["*.py", "*.js", "*.ts", "*.json", "*.yaml", "*.yml", "*.env", "*.conf", "*.config"]
        
        for pattern in file_patterns:
            for file_path in modules_dir.rglob(pattern):
                # Skip certain directories
                if any(skip in str(file_path) for skip in ['.git', '__pycache__', 'node_modules', '.venv']):
                    continue
                    
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                    for line_num, line in enumerate(content.split('\n'), 1):
                        for secret_pattern in compiled_patterns:
                            if secret_pattern.search(line):
                                relative_path = file_path.relative_to(modules_dir)
                                findings.append(f"SECRET_DETECTED: Potential secret in {relative_path}:{line_num}")
                                break  # Only report once per line
                                
                except Exception as e:
                    # Skip files that can't be read
                    continue
                    
    except Exception as e:
        findings.append(f"SECRET_SCAN_ERROR: Secret scanning failed: {str(e)}")
    
    return findings

def audit_all_modules(modules_root):
    """
    Audit all modules to ensure they follow the established structure.
    Now supports Enterprise Domain architecture (WSP 3).
    
    Args:
        modules_root: Path to the root directory containing the modules
        
    Returns:
        tuple: (list of findings, count of modules audited)
    """
    if not modules_root.exists():
        logging.error(f"Modules root {modules_root} does not exist")
        return ["CRITICAL: Modules root directory does not exist"], 0
    
    modules_dir = modules_root if modules_root.name == "modules" else modules_root / "modules"
    
    if not modules_dir.exists():
        logging.error(f"Modules directory {modules_dir} does not exist")
        return ["CRITICAL: Modules directory does not exist"], 0
    
    findings = []
    module_count = 0
    
    # Check for Enterprise Domain compliance
    domain_findings = audit_enterprise_domains(modules_dir)
    findings.extend(domain_findings)
    
    # Discover all modules recursively
    modules = discover_modules_recursive(modules_dir)
    
    for module_path, module_name, domain_path in modules:
        module_count += 1
        
        # Check for src directory
        src_dir = module_path / "src"
        if not src_dir.exists() or not src_dir.is_dir():
            findings.append(f"ERROR: Module '{domain_path}' is missing the src/ directory")
        
        # Check for tests directory
        tests_dir = module_path / "tests"
        if not tests_dir.exists() or not tests_dir.is_dir():
            findings.append(f"ERROR: Module '{domain_path}' is missing the tests/ directory")
        else:
            # Check for tests/README.md (WSP requirement)
            test_readme = tests_dir / "README.md"
            if not test_readme.exists():
                findings.append(f"WARNING: Module '{domain_path}' is missing tests/README.md file")
        
        # Check for interface file (more flexible naming)
        if src_dir.exists():
            interface_files = list(src_dir.glob("*.py"))
            if not interface_files:
                findings.append(f"WARNING: Module '{domain_path}' has no Python files in src/ directory")
        
        # Check for module.json or requirements.txt (dependency manifest)
        module_json = module_path / "module.json"
        requirements_txt = module_path / "requirements.txt"
        if not module_json.exists() and not requirements_txt.exists():
            findings.append(f"WARNING: Module '{domain_path}' is missing dependency manifest (module.json or requirements.txt)")
        
        # WSP 4 Section 4.4.1: Security vulnerability scanning
        security_findings = perform_security_scan(module_path, domain_path)
        findings.extend(security_findings)
    
    # WSP 71: Scan for secrets across all modules
    secret_findings = scan_for_secrets(modules_dir)
    findings.extend(secret_findings)
    
    return findings, module_count

def audit_enterprise_domains(modules_dir):
    """
    Audit Enterprise Domain structure compliance (WSP 3).
    
    Args:
        modules_dir: Path to the modules directory
        
    Returns:
        list: List of domain-related findings
    """
    findings = []
    
    # Check for recognized Enterprise Domains
    found_domains = set()
    unknown_domains = set()
    
    for item in modules_dir.iterdir():
        if not item.is_dir() or item.name.startswith('.') or item.name == '__pycache__':
            continue
            
        # Skip non-domain files
        if item.is_file():
            continue
            
        if item.name in ENTERPRISE_DOMAINS:
            found_domains.add(item.name)
        elif item.name in ARCHITECTURAL_EXCEPTIONS:
            # This is a documented architectural exception - compliant with WSP 3
            logging.debug(f"Found documented architectural exception: {item.name}")
        else:
            # Check if this might be a legacy flat module
            if is_module_directory(item):
                findings.append(f"WARNING: Found potential flat module '{item.name}' - should be moved to appropriate Enterprise Domain")
            else:
                unknown_domains.add(item.name)
    
    # Report unknown domains
    for domain in unknown_domains:
        findings.append(f"WARNING: Unknown Enterprise Domain '{domain}' - not in recognized domains: {', '.join(sorted(ENTERPRISE_DOMAINS))}")
    
    # Report on domain coverage
    if found_domains:
        logging.debug(f"Found Enterprise Domains: {', '.join(sorted(found_domains))}")
    
    return findings

def compute_file_hash(file_path):
    """
    Compute a SHA256 hash of a file's contents.
    
    Args:
        file_path: Path to the file
        
    Returns:
        str: Hexadecimal digest of the file hash, or None if the file cannot be read
    """
    hash_obj = hashlib.sha256()
    
    try:
        with open(file_path, 'rb') as f:
            # Read in chunks to handle large files efficiently
            for chunk in iter(lambda: f.read(4096), b''):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except FileNotFoundError:
        logging.error(f"Error computing hash: File not found: {file_path}")
        return None
    except PermissionError:
        logging.error(f"Error computing hash: Permission denied for file: {file_path}")
        return None
    except Exception as e:
        logging.error(f"Error computing hash for {file_path}: {str(e)}")
        return None

def get_file_size_thresholds():
    """
    Get default WSP 62 file size thresholds.

    Returns:
        dict: File extension to line threshold mapping (warn/critical/hard).
    """
    return {
        '.py': {'warn': 800, 'critical': 1000, 'hard': 1500},
        '.js': {'warn': 400, 'critical': 400, 'hard': 600},
        '.ts': {'warn': 400, 'critical': 400, 'hard': 600},
        '.json': {'warn': 200, 'critical': 200, 'hard': 300},
        '.yaml': {'warn': 200, 'critical': 200, 'hard': 300},
        '.yml': {'warn': 200, 'critical': 200, 'hard': 300},
        '.toml': {'warn': 200, 'critical': 200, 'hard': 300},
        '.sh': {'warn': 300, 'critical': 300, 'hard': 450},
        '.ps1': {'warn': 300, 'critical': 300, 'hard': 450},
        '.md': {'warn': 1000, 'critical': 1000, 'hard': 1500}
    }



def count_file_lines(file_path):
    """
    Count the number of lines in a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        int: Number of lines in the file, or 0 if error
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for line in f)
    except (IOError, OSError) as e:
        logging.debug(f"Unable to count lines in file {file_path}: {e}")
        return 0

def check_exemption_file(module_path):
    """
    Check if a module has WSP 62 exemption configuration.
    
    Args:
        module_path: Path to the module directory
        
    Returns:
        dict: Canonical relative paths mapped to exemption contracts
    """
    exemption_file = module_path / "wsp_62_exemptions.yaml"
    if not exemption_file.exists():
        return {}
    
    try:
        import yaml
    except ImportError as e:
        logging.debug(f"Unable to import YAML parser for {exemption_file}: {e}")
        return {}

    try:
        with open(exemption_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            exemptions = config.get('exemptions', []) or []
            if not isinstance(exemptions, list):
                return {}
            return {
                item['file']: item
                for item in exemptions
                if isinstance(item, dict) and isinstance(item.get('file'), str)
            }
    except (yaml.YAMLError, IOError, KeyError, AttributeError) as e:
        logging.debug(f"Unable to load exemption file {exemption_file}: {e}")
        return {}


def canonical_relative_path(file_path, module_path):
    """Return the WSP 62 exemption key independent of the host path separator."""
    return file_path.relative_to(module_path).as_posix()


def _baseline_line_count(
    file_path, modules_dir, baseline_root, renamed_baseline_path=None
):
    """Return the exact baseline line count when a comparison root exists."""
    if baseline_root is None:
        return None
    if renamed_baseline_path is not None:
        baseline_file = baseline_root / renamed_baseline_path
    else:
        baseline_modules = (
            baseline_root if baseline_root.name == "modules" else baseline_root / "modules"
        )
        baseline_file = baseline_modules / file_path.relative_to(modules_dir)
    if not baseline_file.is_file():
        return BASELINE_MISSING
    return count_file_lines(baseline_file)


def _baseline_file(file_path, modules_dir, baseline_root, renamed_baseline_path=None):
    """Resolve a supported file at the exact comparison root."""
    if baseline_root is None:
        return None
    if renamed_baseline_path is not None:
        candidate = baseline_root / renamed_baseline_path
    else:
        baseline_modules = (
            baseline_root if baseline_root.name == "modules" else baseline_root / "modules"
        )
        candidate = baseline_modules / file_path.relative_to(modules_dir)
    return candidate if candidate.is_file() else BASELINE_MISSING


def _baseline_module_rules(module_path, modules_dir, baseline_root):
    """Load the exemption authority from the exact comparison module."""
    if baseline_root is None:
        return None
    baseline_modules = (
        baseline_root if baseline_root.name == "modules" else baseline_root / "modules"
    )
    baseline_module = baseline_modules / module_path.relative_to(modules_dir)
    if not baseline_module.is_dir():
        return {}
    return check_exemption_file(baseline_module)


def _authorized_ceiling(previous, observed):
    """Return the largest ceiling independently present at the exact base."""
    values = [value for value in (previous, observed) if isinstance(value, int)]
    return max(values, default=0)


def _authorized_policy_transition(relative_key, entry, baseline_entry):
    """Allow only the post-policy migration for canonical append-only logs."""
    return (
        relative_key in {"ModLog.md", "tests/TestModLog.md"}
        and baseline_entry.get("enforcement_mode") is None
        and entry.get("enforcement_mode") == "advisory_archive"
        and entry.get("permanent") == baseline_entry.get("permanent")
    )


def _audit_exemption_authority(
    relative_key, entry, baseline_entry, baseline_count, file_path, baseline_file
):
    """Reject candidate-authored exemption authority and ceiling ratchets."""
    if baseline_entry is None:
        return []
    if baseline_entry is BASELINE_MISSING:
        return [f"WSP 62 ERROR: candidate-authored exemption {relative_key}"]
    fields = ("enforcement_mode", "permanent", "temporary", "expires_on")
    policy_changed = any(
        entry.get(field) != baseline_entry.get(field) for field in fields
    )
    if policy_changed and not _authorized_policy_transition(
        relative_key, entry, baseline_entry
    ):
        return [f"WSP 62 ERROR: exemption policy changed {relative_key}"]
    findings = []
    current_ceiling = entry.get("no_growth_ceiling", {}).get("file_lines")
    prior_ceiling = baseline_entry.get("no_growth_ceiling", {}).get("file_lines")
    if isinstance(current_ceiling, int):
        allowed = _authorized_ceiling(prior_ceiling, baseline_count)
        if current_ceiling > allowed:
            findings.append(f"WSP 62 ERROR: file ceiling ratchet {relative_key}")
    current_override = entry.get("threshold_override")
    prior_override = baseline_entry.get("threshold_override")
    if isinstance(current_override, int):
        allowed = _authorized_ceiling(prior_override, baseline_count)
        if current_override > allowed:
            findings.append(f"WSP 62 ERROR: threshold override ratchet {relative_key}")
    findings.extend(
        _audit_archive_threshold_authority(relative_key, entry, baseline_entry)
    )
    findings.extend(
        _audit_function_ceiling_authority(
            relative_key, entry, baseline_entry, file_path, baseline_file
        )
    )
    return findings


def _wrap_security_findings(domain_path, findings):
    """Bind severity before adding untrusted module-path display context."""
    wrapped = []
    for finding in findings:
        severity = _finding_severity(finding)
        wrapped.append(f"SECURITY_{severity}: {domain_path} - {finding}")
    return wrapped


def _audit_archive_threshold_authority(relative_key, entry, baseline_entry):
    """Reject candidate increases to the canonical archive advisory threshold."""
    if entry.get("enforcement_mode") != "advisory_archive":
        return []
    current = entry.get("advisory_archive_threshold")
    previous = baseline_entry.get("advisory_archive_threshold")
    allowed = previous if isinstance(previous, int) else ADVISORY_ARCHIVE_MAX_THRESHOLD
    if not isinstance(current, int) or current <= 0 or current > allowed:
        return [f"WSP 62 ERROR: archive threshold ratchet {relative_key}"]
    return []


def _audit_function_ceiling_authority(
    relative_key, entry, baseline_entry, file_path, baseline_file
):
    """Bind candidate function ceilings to base policy or observed base size."""
    current = entry.get("no_growth_ceiling", {}).get("functions", {})
    previous = baseline_entry.get("no_growth_ceiling", {}).get("functions", {})
    if not current and not previous:
        return []
    if current == previous and _same_file_bytes(file_path, baseline_file):
        return []
    current_sizes = {}
    if file_path.suffix == ".py":
        try:
            current_sizes = _function_sizes(file_path)
        except (OSError, SyntaxError, UnicodeError) as exc:
            return [f"WSP 62 ERROR: function inspection failed {relative_key}: {exc}"]
    observed = {}
    findings = []
    if baseline_file not in (None, BASELINE_MISSING) and baseline_file.suffix == ".py":
        try:
            observed = _function_sizes(baseline_file)
        except (OSError, SyntaxError, UnicodeError) as exc:
            findings.append(
                f"WSP 62 INHERITED_METADATA: baseline function inspection failed "
                f"{relative_key}: {exc}"
            )
    for name in set(previous) - set(current):
        current_size = current_sizes.get(name)
        previous_size = observed.get(name)
        if current_size is not None and (
            current_size > 50
            or (previous_size is not None and current_size > previous_size)
        ):
            findings.append(f"WSP 62 ERROR: function ceiling removed {relative_key}:{name}")
    for name, ceiling in current.items():
        allowed = _authorized_ceiling(previous.get(name), observed.get(name))
        if not isinstance(ceiling, int) or ceiling > allowed:
            findings.append(f"WSP 62 ERROR: function ceiling ratchet {relative_key}:{name}")
    return findings


def _resolved_exemption_removal(
    file_path, baseline_file, line_count, baseline_count, baseline_entry,
    threshold_data, relative_key,
):
    """Allow policy removal only after independently measured debt resolution."""
    if not isinstance(baseline_count, int) or line_count > baseline_count:
        return False
    warn, _critical, _hard = _threshold_limits(threshold_data)
    if line_count >= warn:
        return False
    function_findings = _audit_standard_function_growth(
        relative_key, file_path, baseline_file
    )
    return not any(_wsp62_severity(item) == "ERROR" for item in function_findings)


def _audit_exempt_file(
    file_path, relative_key, display_path, exemption, baseline_entry,
    line_count, baseline_count, baseline_file,
):
    """Evaluate one exempt file after its baseline policy is resolved."""
    findings = []
    expiry = _expiry_advisory(relative_key, exemption, baseline_entry)
    if expiry:
        findings.append(f"{expiry} [{display_path}]")
    finding = _audit_exemption(relative_key, exemption, line_count, baseline_count)
    if finding:
        findings.append(f"{finding} [{display_path}]")
    authority_findings = _audit_exemption_authority(
        relative_key, exemption, baseline_entry, baseline_count,
        file_path, baseline_file,
    )
    if authority_findings:
        findings.extend(f"{item} [{display_path}]" for item in authority_findings)
        if any(_wsp62_severity(item) == "ERROR" for item in authority_findings):
            return findings
    function_findings = _audit_function_ceilings(
        relative_key, exemption, baseline_entry, file_path, baseline_file
    )
    findings.extend(f"{item} [{display_path}]" for item in function_findings)
    return findings


def _audit_exemption(relative_key, entry, line_count, baseline_count):
    """Evaluate one WSP 62 exemption contract without blanket bypasses."""
    mode = entry.get("enforcement_mode")
    if mode == "advisory_archive":
        valid_paths = {"ModLog.md", "tests/TestModLog.md"}
        if relative_key not in valid_paths:
            return f"WSP 62 ERROR: invalid advisory archive exemption {relative_key}"
        threshold = entry.get("advisory_archive_threshold")
        if not isinstance(threshold, int) or threshold <= 0:
            return f"WSP 62 ERROR: invalid advisory archive threshold {relative_key}"
        if line_count > threshold:
            return f"WSP 62 ADVISORY_ARCHIVE: {relative_key} ({line_count} lines)"
        return ""

    ceiling = entry.get("no_growth_ceiling", {}).get("file_lines")
    if isinstance(ceiling, int) and ceiling > 0:
        if line_count <= ceiling:
            return ""
        if baseline_count is BASELINE_MISSING:
            return f"WSP 62 ERROR: new candidate debt {relative_key} ({line_count} lines)"
        if baseline_count is not None and line_count <= baseline_count:
            return f"WSP 62 INHERITED: {relative_key} ({line_count} lines)"
        if baseline_count is None:
            return f"WSP 62 UNATTRIBUTED: {relative_key} ({line_count} lines)"
        return f"WSP 62 ERROR: candidate growth {relative_key} ({baseline_count}->{line_count})"

    override = entry.get("threshold_override")
    if isinstance(override, int) and override > 0:
        if line_count > override:
            return f"WSP 62 ERROR: override exceeded {relative_key} ({line_count}>{override})"
        return ""
    if entry.get("permanent") is True:
        return ""
    return f"WSP 62 ERROR: invalid exemption contract {relative_key}"


class _QualifiedFunctionVisitor(ast.NodeVisitor):
    """Collect lexical function identities without duplicate-name collapse."""

    def __init__(self):
        self.scope = []
        self.sizes = {}
        self.counts = {}

    def visit_ClassDef(self, node):
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def _visit_function(self, node):
        identity = ".".join((*self.scope, node.name))
        count = self.counts.get(identity, 0) + 1
        self.counts[identity] = count
        key = identity if count == 1 else f"{identity}#{count}"
        self.sizes[key] = node.end_lineno - node.lineno + 1
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    visit_FunctionDef = _visit_function
    visit_AsyncFunctionDef = _visit_function


def _function_sizes(file_path):
    """Return qualified Python function sizes for WSP 62 ceiling checks."""
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    visitor = _QualifiedFunctionVisitor()
    visitor.visit(tree)
    return visitor.sizes


def _audit_function_ceilings(
    relative_key, entry, baseline_entry, file_path, baseline_file
):
    """Evaluate named function ceilings with exact-baseline attribution."""
    ceilings = entry.get("no_growth_ceiling", {}).get("functions", {})
    baseline_ceilings = (
        {}
        if baseline_entry in (None, BASELINE_MISSING)
        else baseline_entry.get("no_growth_ceiling", {}).get("functions", {})
    )
    if file_path.suffix.lower() != ".py":
        return []
    if ceilings == baseline_ceilings and _same_file_bytes(file_path, baseline_file):
        return []
    try:
        current = _function_sizes(file_path)
    except (OSError, SyntaxError, UnicodeError) as exc:
        return [f"WSP 62 ERROR: function inspection failed {relative_key}: {exc}"]
    findings = []
    baseline = {}
    baseline_unknown = False
    if baseline_file not in (None, BASELINE_MISSING):
        try:
            baseline = _function_sizes(baseline_file)
        except (OSError, SyntaxError, UnicodeError) as exc:
            baseline_unknown = True
            findings.append(
                f"WSP 62 INHERITED_METADATA: baseline function inspection failed "
                f"{relative_key}: {exc}"
            )
    for name, ceiling in ceilings.items():
        current_size = current.get(name)
        if not isinstance(ceiling, int):
            findings.append(f"WSP 62 ERROR: invalid function ceiling {relative_key}:{name}")
        elif current_size is None:
            continue
        elif current_size > ceiling:
            previous = baseline.get(name)
            if baseline_file is None:
                label = "UNATTRIBUTED"
            elif previous is not None and current_size <= previous:
                label = "INHERITED"
            else:
                label = "ERROR: candidate function growth"
            findings.append(
                f"WSP 62 {label}: {relative_key}:{name} ({previous}->{current_size})"
            )
    findings.extend(
        _audit_untracked_function_growth(
            relative_key,
            current,
            baseline,
            set() if baseline_unknown else set(ceilings) | set(baseline_ceilings),
            baseline_file,
        )
    )
    return findings


def _audit_untracked_function_growth(
    relative_key, current, baseline, ceilings, baseline_file
):
    """Reject renamed or newly oversized functions outside named ceilings."""
    findings = []
    for name, current_size in current.items():
        if name in ceilings or current_size <= 50:
            continue
        previous = baseline.get(name)
        if baseline_file is None:
            continue
        if previous is None:
            findings.append(
                f"WSP 62 ERROR: new candidate function debt {relative_key}:{name}"
            )
        elif current_size > previous:
            findings.append(
                f"WSP 62 ERROR: candidate function growth {relative_key}:{name} "
                f"({previous}->{current_size})"
            )
    return findings


def _audit_standard_function_growth(relative_key, file_path, baseline_file):
    """Enforce the standard 50-line function boundary on every Python file."""
    if file_path.suffix.lower() != ".py":
        return []
    if _same_file_bytes(file_path, baseline_file):
        return []
    try:
        current = _function_sizes(file_path)
    except (OSError, SyntaxError, UnicodeError) as exc:
        return [f"WSP 62 ERROR: function inspection failed {relative_key}: {exc}"]
    if baseline_file is None:
        return []
    baseline = {}
    if baseline_file is not BASELINE_MISSING:
        try:
            baseline = _function_sizes(baseline_file)
        except (OSError, SyntaxError, UnicodeError) as exc:
            findings = [
                f"WSP 62 INHERITED_METADATA: baseline function inspection failed "
                f"{relative_key}: {exc}"
            ]
            findings.extend(
                _audit_untracked_function_growth(
                    relative_key, current, {}, set(), BASELINE_MISSING
                )
            )
            return findings
    return _audit_untracked_function_growth(
        relative_key, current, baseline, set(), baseline_file
    )


def _same_file_bytes(file_path, baseline_file):
    """Prove a parse defect is byte-identical at the exact base."""
    if baseline_file in (None, BASELINE_MISSING):
        return False
    try:
        return file_path.read_bytes() == baseline_file.read_bytes()
    except OSError:
        return False


def _inherited_expiry_defect(entry, baseline_entry):
    """Return true only when the exact base already contains the same defect."""
    if baseline_entry in (None, BASELINE_MISSING):
        return False
    return (
        baseline_entry.get("temporary") is True
        and entry.get("expires_on") == baseline_entry.get("expires_on")
    )


def _expiry_advisory(relative_key, entry, baseline_entry=None):
    """Report expired temporary debt without attributing it to a candidate."""
    if entry.get("temporary") is not True:
        return ""
    expires_on = entry.get("expires_on")
    if not isinstance(expires_on, str):
        if _inherited_expiry_defect(entry, baseline_entry):
            return f"WSP 62 INHERITED_METADATA: missing exemption expiry {relative_key}"
        return f"WSP 62 ERROR: missing exemption expiry {relative_key}"
    try:
        expired = date.fromisoformat(expires_on) <= date.today()
    except ValueError:
        if _inherited_expiry_defect(entry, baseline_entry):
            return f"WSP 62 INHERITED_METADATA: invalid exemption expiry {relative_key}"
        return f"WSP 62 ERROR: invalid exemption expiry {relative_key}"
    if expired:
        return f"WSP 62 EXEMPTION_EXPIRED: {relative_key} ({expires_on})"
    return ""


def _threshold_limits(threshold_data):
    """Normalize a scalar or tiered WSP 62 threshold."""
    if not isinstance(threshold_data, dict):
        return threshold_data, threshold_data, int(threshold_data * 1.5)
    warn = threshold_data.get("warn", threshold_data.get("critical"))
    critical = threshold_data.get("critical", warn)
    return warn, critical, threshold_data.get("hard", critical)


def _standard_size_finding(display_path, line_count, threshold_data, baseline_count=None):
    """Classify a non-exempt file against standard tiered limits."""
    warn, critical, hard = _threshold_limits(threshold_data)
    if baseline_count is BASELINE_MISSING and line_count >= warn:
        return f"WSP 62 ERROR: new candidate size violation {display_path} ({line_count} lines)"
    if line_count >= hard:
        if baseline_count is not None and line_count <= baseline_count:
            return f"WSP 62 INHERITED: {display_path} ({line_count} lines)"
        if baseline_count is not None:
            return f"WSP 62 ERROR: candidate size growth {display_path} ({baseline_count}->{line_count})"
        return f"WSP 62 CRITICAL: {display_path} ({line_count} lines >= hard limit {hard})"
    if line_count > critical:
        return f"WSP 62 WARNING: {display_path} ({line_count} lines > critical window {critical})"
    if line_count >= warn:
        label = f"within {warn}-{critical} guideline window"
        if warn == critical:
            label = f"approaching limit {warn}"
        return f"WSP 62 APPROACHING: {display_path} ({line_count} lines {label})"
    if line_count >= int(warn * 0.9):
        return f"WSP 62 WATCH: {display_path} ({line_count} lines at 90% of limit {warn})"
    return ""


def _renamed_baseline_entry(baseline_root, renamed_path):
    """Resolve the exemption that governed a Git-detected source path."""
    if baseline_root is None or renamed_path is None:
        return BASELINE_MISSING
    baseline_file = baseline_root / renamed_path
    modules_root = baseline_root / "modules"
    parent = baseline_file.parent
    while parent != modules_root and modules_root in parent.parents:
        rules = check_exemption_file(parent)
        if rules:
            key = baseline_file.relative_to(parent).as_posix()
            return rules.get(key, BASELINE_MISSING)
        parent = parent.parent
    return BASELINE_MISSING


def _candidate_repo_path(file_path, modules_dir):
    """Return the repository-relative candidate path used by Git rename data."""
    return file_path.relative_to(modules_dir.parent).as_posix()


def _audit_unexempt_file(
    file_path, relative_key, display_path, line_count, baseline_file, baseline_count,
    baseline_entry, threshold_data,
):
    """Evaluate an unexempt candidate against exact-base policy and size."""
    if baseline_entry not in (None, BASELINE_MISSING) and not _resolved_exemption_removal(
        file_path,
        baseline_file,
        line_count,
        baseline_count,
        baseline_entry,
        threshold_data,
        relative_key,
    ):
        return [f"WSP 62 ERROR: candidate removed exemption {display_path}"]
    finding = _standard_size_finding(
        display_path, line_count, threshold_data, baseline_count
    )
    findings = [finding] if finding else []
    findings.extend(
        _audit_standard_function_growth(relative_key, file_path, baseline_file)
    )
    return findings


def _audit_sized_file(
    file_path, module_path, domain_path, modules_dir, rules, baseline_rules,
    thresholds, baseline_root, rename_map,
):
    """Return findings for one supported file and its exemption contract."""
    if not file_path.is_file() or file_path.name.startswith('.'):
        return []
    if '__pycache__' in str(file_path) or file_path.suffix.lower() not in thresholds:
        return []
    relative_path = file_path.relative_to(module_path)
    relative_key = canonical_relative_path(file_path, module_path)
    display_path = f"{domain_path}/{relative_path}"
    line_count = count_file_lines(file_path)
    renamed_path = rename_map.get(_candidate_repo_path(file_path, modules_dir))
    baseline_file = _baseline_file(
        file_path, modules_dir, baseline_root, renamed_path
    )
    baseline_count = _baseline_line_count(
        file_path, modules_dir, baseline_root, renamed_path
    )
    exemption = rules.get(relative_key)
    baseline_entry = None
    if baseline_rules is not None:
        baseline_entry = (
            _renamed_baseline_entry(baseline_root, renamed_path)
            if renamed_path is not None
            else baseline_rules.get(relative_key, BASELINE_MISSING)
        )
    if exemption is None:
        return _audit_unexempt_file(
            file_path, relative_key, display_path, line_count, baseline_file, baseline_count,
            baseline_entry, thresholds[file_path.suffix.lower()],
        )
    return _audit_exempt_file(
        file_path, relative_key, display_path, exemption, baseline_entry,
        line_count, baseline_count, baseline_file,
    )


def audit_file_sizes(
    modules_root, enable_wsp_62=False, baseline_root=None, rename_map=None
):
    """Audit module files with optional exact-baseline growth attribution."""
    if not enable_wsp_62:
        return []
    modules_dir = modules_root if modules_root.name == "modules" else modules_root / "modules"
    if not modules_dir.exists():
        return ["WSP 62: Modules directory does not exist"]
    findings = []
    thresholds = get_file_size_thresholds()
    if rename_map is None:
        rename_map = _git_rename_map(modules_dir.parent) if baseline_root else {}
    for module_path, _module_name, domain_path in discover_modules_recursive(modules_dir):
        rules = check_exemption_file(module_path)
        baseline_rules = _baseline_module_rules(
            module_path, modules_dir, baseline_root
        )
        for file_path in module_path.glob('**/*'):
            findings.extend(
                _audit_sized_file(
                    file_path, module_path, domain_path, modules_dir,
                    rules, baseline_rules, thresholds, baseline_root, rename_map,
                )
            )
    return findings


def _mode2_result_errors(audit_results):
    """Normalize the current Mode 2 mapping into explicit error messages."""
    if not isinstance(audit_results, dict):
        return ["WSP 62 ERROR: invalid baseline audit result"]
    if audit_results.get("status") == "success":
        return []
    reason = audit_results.get("reason", "baseline comparison failed")
    return [f"WSP 62 ERROR: {reason}"]


def _wsp62_severity(finding):
    """Read severity from the finding prefix, never from path content."""
    for severity in ("ERROR", "CRITICAL", "WARNING"):
        if finding.startswith(f"WSP 62 {severity}:"):
            return severity
    return "ADVISORY"


def _finding_severity(finding):
    """Classify structural and WSP 62 findings by trusted prefixes."""
    wsp62 = _wsp62_severity(finding)
    if wsp62 != "ADVISORY":
        return wsp62
    if finding.startswith("SECURITY_ERROR:"):
        return "ERROR"
    if finding.startswith("SECURITY_WARNING:"):
        return "WARNING"
    if finding.startswith("SECURITY_ADVISORY:"):
        return "ADVISORY"
    error_prefixes = (
        "ERROR:",
        "SECURITY_AUDIT_FAIL:",
        "SECURITY_SCAN_ERROR:",
        "SECURITY_SCAN_FAILED:",
        "SECRET_SCAN_ERROR:",
    )
    if finding.startswith("SECURITY: "):
        return "ERROR"
    normalized = finding
    if normalized.startswith(error_prefixes):
        return "ERROR"
    if normalized.startswith("WARNING:"):
        return "WARNING"
    return "ADVISORY"

def audit_with_baseline_comparison(target_root, baseline_root):
    """
    Audit modules and compare with a baseline version, reporting changes.
    
    Args:
        target_root: Path to the target directory
        baseline_root: Path to the baseline directory
        
    Returns:
        dict: Summary of changes including new, modified, and deleted modules and files
    """
    # Validate the baseline path
    if not validate_baseline_path(baseline_root):
        return {
            "status": "failed",
            "reason": "Invalid baseline path"
        }
    
    # Initialize summary structure
    summary = {
        "status": "success",
        "modules": {
            "new": [],
            "modified": [],
            "deleted": []
        },
        "files": {
            "new": 0,
            "modified": 0,
            "deleted": 0,
            "found_in_flat": 0
        }
    }
    
    # Discover files in target and baseline
    target_modules, target_flat_files = discover_source_files(target_root)
    baseline_modules, baseline_flat_files = discover_source_files(baseline_root)
    
    logging.info(f"Found {len(target_modules)} modules in target and {len(baseline_modules)} modules in baseline")
    if baseline_flat_files:
        logging.info(f"Found {len(baseline_flat_files)} flat files in baseline modules/ directory")
    
    # Find new and modified modules
    for module_name, target_files in target_modules.items():
        if module_name not in baseline_modules:
            # New module, but check if any files were moved from flat structure
            found_in_flat_files = []
            extra_files = []
            
            # Check each file in the target module
            for file_path in target_files:
                # Check if this is a file that was moved from the flat structure
                if isinstance(file_path, Path):
                    file_name = file_path.name
                else:
                    file_name = Path(file_path).name
                    
                if file_name in baseline_flat_files:
                    found_in_flat_files.append(file_path)
                    # WSP 3.5 detailed FOUND_IN_FLAT file logging
                    logging.warning(f"[{module_name}] FOUND_IN_FLAT: Found only in baseline flat modules/, needs proper placement. (File path: {file_path})")
                else:
                    extra_files.append(file_path)
                    # WSP 3.5 detailed EXTRA file logging for new modules
                    logging.warning(f"[{module_name}] EXTRA: File not found anywhere in baseline. (File path: {file_path})")
            
            # Update counts for new module
            summary["modules"]["new"].append(module_name)
            summary["files"]["new"] += len(extra_files)
            summary["files"]["found_in_flat"] += len(found_in_flat_files)
            
            if found_in_flat_files:
                logging.debug(f"New module {module_name} has {len(found_in_flat_files)} files that were moved from flat structure")
            
            logging.info(f"New module found: {module_name} with {len(target_files)} files")
            
            # Check if this is a critical module
            if module_name in CRITICAL_MODULES:
                logging.warning(f"New critical module found: {module_name}")
        else:
            # Existing module, check for file changes
            baseline_files = baseline_modules[module_name]
            
            # New files (EXTRA) or potentially FOUND_IN_FLAT
            found_in_flat_files = []
            new_files = target_files - baseline_files
            
            # Check if any "new" files actually exist in the baseline's flat files
            for file_path in list(new_files):
                # Check if this is a file that was moved from the flat structure
                if isinstance(file_path, Path):
                    file_name = file_path.name
                else:
                    file_name = Path(file_path).name
                    
                if file_name in baseline_flat_files:
                    found_in_flat_files.append(file_path)
                    new_files.remove(file_path)
                    # WSP 3.5 detailed FOUND_IN_FLAT file logging
                    logging.warning(f"[{module_name}] FOUND_IN_FLAT: Found only in baseline flat modules/, needs proper placement. (File path: {file_path})")
            
            # Update counts for FOUND_IN_FLAT
            if found_in_flat_files:
                if module_name not in summary["modules"]["modified"]:
                    summary["modules"]["modified"].append(module_name)
                summary["files"]["found_in_flat"] += len(found_in_flat_files)
                logging.debug(f"Module {module_name} has {len(found_in_flat_files)} files that were moved from flat structure")
            
            # Report remaining new files as EXTRA
            if new_files:
                if module_name not in summary["modules"]["modified"]:
                    summary["modules"]["modified"].append(module_name)
                summary["files"]["new"] += len(new_files)
                logging.debug(f"Module {module_name} has {len(new_files)} new files")
                
                # WSP 3.5 detailed EXTRA file logging
                for extra_file in new_files:
                    logging.warning(f"[{module_name}] EXTRA: File not found anywhere in baseline. (File path: {extra_file})")
                
            # Deleted files (MISSING)
            deleted_files = baseline_files - target_files
            if deleted_files:
                if module_name not in summary["modules"]["modified"]:
                    summary["modules"]["modified"].append(module_name)
                summary["files"]["deleted"] += len(deleted_files)
                logging.debug(f"Module {module_name} has {len(deleted_files)} deleted files")
                
                # WSP 3.5 detailed MISSING file logging
                for missing_file in deleted_files:
                    logging.warning(f"[{module_name}] MISSING: File missing from target module. (Baseline path: {missing_file})")
                
            # Modified files - compare file contents
            common_files = target_files & baseline_files
            modified_files = []
            
            for common_file in common_files:
                # Handle hierarchical paths - module_name is now domain_path
                target_file_path = target_root / "modules" / Path(module_name) / Path(common_file)
                baseline_file_path = baseline_root / "modules" / Path(module_name) / Path(common_file)
                
                # Compare file contents using hash
                target_hash = compute_file_hash(target_file_path)
                baseline_hash = compute_file_hash(baseline_file_path)
                
                if target_hash is not None and baseline_hash is not None and target_hash != baseline_hash:
                    modified_files.append(common_file)
                    # WSP 3.5 detailed MODIFIED file logging
                    logging.warning(f"[{module_name}] MODIFIED: Content differs from baseline src/. (File path: {common_file})")
            
            if modified_files:
                if module_name not in summary["modules"]["modified"]:
                    summary["modules"]["modified"].append(module_name)
                summary["files"]["modified"] += len(modified_files)
                logging.debug(f"Module {module_name} has {len(modified_files)} modified files")
    
    # Find deleted modules
    for module_name, baseline_files in baseline_modules.items():
        if module_name not in target_modules:
            summary["modules"]["deleted"].append(module_name)
            summary["files"]["deleted"] += len(baseline_files)
            logging.info(f"Deleted module found: {module_name} with {len(baseline_files)} files")
            
            # Check if this was a critical module
            if module_name in CRITICAL_MODULES:
                logging.warning(f"Critical module deleted: {module_name}")
            
            # WSP 3.5 detailed MISSING file logging for all files in the deleted module
            for missing_file in baseline_files:
                logging.warning(f"[{module_name}] MISSING: File missing from target module. (Baseline path: {missing_file})")
    
    # Determine overall status based on findings
    has_changes = (
        len(summary["modules"]["new"]) > 0 or 
        len(summary["modules"]["modified"]) > 0 or 
        len(summary["modules"]["deleted"]) > 0
    )
    
    if has_changes:
        summary["has_changes"] = True
    else:
        summary["has_changes"] = False
        
    return summary

def _log_findings(findings, severity_reader):
    """Emit findings through their trusted severity vocabulary."""
    for finding in findings:
        severity = severity_reader(finding)
        if severity == "ERROR":
            logging.error(f"- {finding}")
        elif severity in {"WARNING", "CRITICAL"}:
            logging.warning(f"- {finding}")
        else:
            logging.info(f"- {finding}")


def _run_mode1(args, project_root):
    """Run structural audit mode without baseline attribution."""
    logging.info("Running FMAS Mode 1: Structure Audit")
    findings, module_count = audit_all_modules(project_root)
    if args.wsp_62_size_check:
        findings.extend(audit_file_sizes(project_root, enable_wsp_62=True))
    if findings:
        logging.info("\nDetailed Findings:")
        _log_findings(findings, _finding_severity)
        print()
    errors = sum(_finding_severity(item) == "ERROR" for item in findings)
    warnings = sum(
        _finding_severity(item) in {"WARNING", "CRITICAL"} for item in findings
    )
    logging.info("Audit Summary:")
    logging.info(f"  Modules audited: {module_count}")
    logging.info(f"  Errors found: {errors}")
    logging.info(f"  Warnings found: {warnings}")
    if errors:
        logging.error("Audit completed with errors.")
        sys.exit(1)
    if warnings:
        logging.warning("Audit completed with warnings.")
    else:
        logging.info("Audit completed with no findings.")


def _validated_mode2_baseline(args, project_root):
    """Resolve and authenticate the exact Git baseline for Mode 2."""
    if not args.baseline:
        logging.error("Baseline path is required for Mode 2")
        sys.exit(1)
        return None
    baseline_root = Path(args.baseline).resolve()
    if not validate_baseline_path(baseline_root):
        sys.exit(2)
        return None
    accepted, reason = validate_authoritative_baseline(project_root, baseline_root)
    if not accepted:
        logging.error(f"Authoritative baseline rejected: {reason}")
        sys.exit(2)
        return None
    return baseline_root


def _run_mode2(args, project_root):
    """Run exact-base comparison and candidate-attributed WSP 62 enforcement."""
    baseline_root = _validated_mode2_baseline(args, project_root)
    if baseline_root is None:
        return
    logging.info(f"Running FMAS Mode 2: Baseline Comparison against {baseline_root}")
    audit_results = audit_with_baseline_comparison(project_root, baseline_root)
    size_findings = []
    if args.wsp_62_size_check:
        size_findings = audit_file_sizes(
            project_root, enable_wsp_62=True, baseline_root=baseline_root
        )
        if size_findings:
            logging.info("\nWSP 62 Size Compliance Findings:")
            _log_findings(size_findings, _wsp62_severity)
    result_errors = _mode2_result_errors(audit_results)
    size_errors = [item for item in size_findings if _wsp62_severity(item) == "ERROR"]
    errors = len(result_errors) + len(size_errors)
    warnings = sum(
        _wsp62_severity(item) in {"WARNING", "CRITICAL"} for item in size_findings
    )
    logging.info("Audit Summary:")
    logging.info(f"  Errors found: {errors}")
    logging.info(f"  Warnings found: {warnings}")
    if result_errors:
        logging.info("\nDetailed Findings:")
        _log_findings(result_errors, _wsp62_severity)
        print()
    if errors:
        logging.error("Audit completed with errors.")
        sys.exit(1)
    logging.info("Audit completed with no findings.")


def main():
    """Parse FMAS CLI arguments and dispatch the selected audit mode."""
    parser = argparse.ArgumentParser(description="Foundups Modular Audit System (FMAS)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug logging")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress most output")
    parser.add_argument("--mode", type=int, choices=[1, 2], default=1)
    parser.add_argument(
        "--baseline", type=str,
        help="Path to baseline directory for Mode 2 comparison",
    )
    parser.add_argument(
        "--wsp-62-size-check", action="store_true",
        help="Enable WSP 62 file size compliance checking",
    )
    args = parser.parse_args()
    level = logging.INFO
    if args.debug:
        level = logging.DEBUG
    elif args.quiet and not args.verbose:
        level = logging.ERROR
    logging.getLogger().setLevel(level)
    project_root = Path.cwd()
    logging.info(f"Project root: {project_root}")
    (_run_mode1 if args.mode == 1 else _run_mode2)(args, project_root)

if __name__ == "__main__":
    main() 

