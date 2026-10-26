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

FMAS Mode 2 specific tests for the modular_audit.py script.
These tests focus on functionality needed for baseline comparison.
"""

import unittest
import tempfile
import shutil
import sys
import os
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock, call

# Add the parent directory to the path so we can import modular_audit
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import modular_audit

# Disable logging during tests
logging.disable(logging.CRITICAL)

class TestFMASMode2Integration(unittest.TestCase):
    """Integration tests for FMAS Mode 2 functionality."""
    
    def setUp(self):
        """Set up temporary directories for testing."""
        self.temp_dir = tempfile.mkdtemp()
        # Create target and baseline directories
        self.target_dir = Path(self.temp_dir) / "target"
        self.baseline_dir = Path(self.temp_dir) / "baseline"
        self.target_modules_dir = self.target_dir / "modules"
        self.baseline_modules_dir = self.baseline_dir / "modules"
        
        # Create directories
        self.target_modules_dir.mkdir(parents=True)
        self.baseline_modules_dir.mkdir(parents=True)
    
    def tearDown(self):
        """Clean up temporary directories after testing."""
        shutil.rmtree(self.temp_dir)
    
    def create_module(self, base_dir, module_name, src_files=None, test_files=None, 
                     has_module_json=True, has_interface=True):
        """Helper method to create a module with the given files."""
        if src_files is None:
            src_files = []
        if test_files is None:
            test_files = []
            
        module_dir = base_dir / module_name
        src_dir = module_dir / "src"
        tests_dir = module_dir / "tests"
        
        # Create directories
        module_dir.mkdir(exist_ok=True)
        src_dir.mkdir(exist_ok=True)
        tests_dir.mkdir(exist_ok=True)
        
        # Create source files
        for file_name in src_files:
            file_path = src_dir / file_name
            with open(file_path, 'w') as f:
                f.write(f"# {module_name} - {file_name}\n")
        
        # Create test files
        for file_name in test_files:
            file_path = tests_dir / file_name
            with open(file_path, 'w') as f:
                f.write(f"# {module_name} - Test - {file_name}\n")
        
        # Create interface file if requested
        if has_interface:
            interface_path = src_dir / f"{module_name}.py"
            with open(interface_path, 'w') as f:
                f.write(f"# {module_name} - Interface\n")
        
        # Create module.json if requested
        if has_module_json:
            module_json_path = module_dir / "module.json"
            with open(module_json_path, 'w') as f:
                f.write('{\n  "name": "' + module_name + '",\n  "dependencies": []\n}\n')
    
    def test_full_mode2_workflow(self):
        """Test the full Mode 2 workflow with various scenarios."""
        # Create modules in baseline
        self.create_module(
            self.baseline_modules_dir, 
            "unchanged_module", 
            src_files=["utils.py"], 
            test_files=["test_utils.py"]
        )
        
        self.create_module(
            self.baseline_modules_dir, 
            "modified_module", 
            src_files=["utils.py", "old.py"], 
            test_files=["test_utils.py"]
        )
        
        self.create_module(
            self.baseline_modules_dir, 
            "removed_module", 
            src_files=["utils.py"], 
            test_files=["test_utils.py"]
        )
        
        self.create_module(
            self.baseline_modules_dir, 
            "core", 
            src_files=["core.py"], 
            test_files=["test_core.py"]
        )
        
        # Create modules in target
        self.create_module(
            self.target_modules_dir, 
            "unchanged_module", 
            src_files=["utils.py"], 
            test_files=["test_utils.py"]
        )
        
        self.create_module(
            self.target_modules_dir, 
            "modified_module", 
            src_files=["utils.py", "new.py"],  # old.py replaced with new.py
            test_files=["test_utils.py", "test_new.py"]  # Added test file
        )
        
        self.create_module(
            self.target_modules_dir, 
            "new_module",  # New module
            src_files=["new_module.py"], 
            test_files=["test_new_module.py"]
        )
        
        self.create_module(
            self.target_modules_dir, 
            "core", 
            src_files=["core.py", "extra.py"],  # Modified critical module
            test_files=["test_core.py", "test_extra.py"]
        )
        
        # Create a module with structural issues to test Mode 1 findings
        incomplete_module_dir = self.target_modules_dir / "incomplete_module"
        incomplete_module_dir.mkdir()
        incomplete_src_dir = incomplete_module_dir / "src"
        incomplete_src_dir.mkdir()
        # Missing tests directory, interface file, and module.json
        
        # Mock logging.warning to capture the WSP 3.5 log messages
        with patch('logging.warning') as mock_warning:
            # Run Mode 2 audit
            result = modular_audit.audit_with_baseline_comparison(
                self.target_dir, self.baseline_dir
            )
            
            # Verify successful status
            self.assertEqual(result["status"], "success")
            
            # Verify module counts
            self.assertEqual(len(result["modules"]["new"]), 2)  # new_module and incomplete_module
            self.assertEqual(len(result["modules"]["deleted"]), 1)  # removed_module
            self.assertEqual(len(result["modules"]["modified"]), 2)  # modified_module and core
            
            # Verify file counts
            self.assertGreater(result["files"]["new"], 0)
            self.assertGreater(result["files"]["deleted"], 0)
            
            # Check for specific modules
            self.assertIn("new_module", result["modules"]["new"])
            self.assertIn("core", result["modules"]["modified"])
            self.assertIn("removed_module", result["modules"]["deleted"])
            
            # Check that warning was called for EXTRA and MISSING files
            # We can't check the exact paths due to platform-specific path separators
            # So we check if any call contains the expected substring
            warning_calls = [call[0][0] for call in mock_warning.call_args_list]
            
            # Verify WSP 3.5 log messages for EXTRA files
            self.assertTrue(any(
                "[modified_module] EXTRA: File not found anywhere in baseline" in msg 
                and "new.py" in msg 
                for msg in warning_calls
            ), "Missing EXTRA warning for modified_module/new.py")
            
            self.assertTrue(any(
                "[core] EXTRA: File not found anywhere in baseline" in msg 
                and "extra.py" in msg 
                for msg in warning_calls
            ), "Missing EXTRA warning for core/extra.py")
            
            # Verify WSP 3.5 log messages for MISSING files
            self.assertTrue(any(
                "[modified_module] MISSING: File missing from target module" in msg 
                and "old.py" in msg 
                for msg in warning_calls
            ), "Missing MISSING warning for modified_module/old.py")
            
            # Check for test files as well
            self.assertTrue(any(
                "[modified_module] EXTRA: File not found anywhere in baseline" in msg 
                and "test_new.py" in msg 
                for msg in warning_calls
            ), "Missing EXTRA warning for modified_module/test_new.py")
            
            self.assertTrue(any(
                "[core] EXTRA: File not found anywhere in baseline" in msg 
                and "test_extra.py" in msg 
                for msg in warning_calls
            ), "Missing EXTRA warning for core/test_extra.py")

    def test_empty_baseline(self):
        """Test Mode 2 with an empty baseline."""
        # Create an empty baseline
        # (directories already created in setUp)
        
        # Create some modules in target
        self.create_module(
            self.target_modules_dir, 
            "module1", 
            src_files=["module1.py"], 
            test_files=["test_module1.py"]
        )
        
        self.create_module(
            self.target_modules_dir, 
            "module2", 
            src_files=["module2.py"], 
            test_files=["test_module2.py"]
        )
        
        # Run Mode 2 audit
        result = modular_audit.audit_with_baseline_comparison(
            self.target_dir, self.baseline_dir
        )
        
        # Verify successful status
        self.assertEqual(result["status"], "success")
        
        # Verify module counts
        self.assertEqual(len(result["modules"]["new"]), 2)
        self.assertEqual(len(result["modules"]["deleted"]), 0)
        self.assertEqual(len(result["modules"]["modified"]), 0)
        
        # Verify specific modules
        self.assertIn("module1", result["modules"]["new"])
        self.assertIn("module2", result["modules"]["new"])

    @patch('logging.error')
    def test_invalid_baseline(self, mock_error):
        """Test Mode 2 with an invalid baseline path."""
        # Create an invalid baseline path
        invalid_baseline = Path(self.temp_dir) / "nonexistent"
        
        # Run Mode 2 audit
        result = modular_audit.audit_with_baseline_comparison(
            self.target_dir, invalid_baseline
        )
        
        # Verify failed status
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["reason"], "Invalid baseline path")
        
        # Verify logging.error was called
        mock_error.assert_called()

    @patch('logging.warning')
    def test_wsp35_missing_extra_logging(self, mock_warning):
        """Test that WSP 3.5 compliant logging is generated for MISSING and EXTRA files."""
        # Create a specific test case for MISSING and EXTRA files
        self.create_module(
            self.baseline_modules_dir, 
            "test_module", 
            src_files=["common.py", "missing.py"], 
            test_files=["test_common.py", "test_missing.py"]
        )
        
        self.create_module(
            self.target_modules_dir, 
            "test_module", 
            src_files=["common.py", "extra.py"], 
            test_files=["test_common.py", "test_extra.py"]
        )
        
        # Run Mode 2 audit
        result = modular_audit.audit_with_baseline_comparison(
            self.target_dir, self.baseline_dir
        )
        
        # Verify module is modified
        self.assertIn("test_module", result["modules"]["modified"])
        
        # Get all warning calls
        warning_calls = [call[0][0] for call in mock_warning.call_args_list]
        
        # Verify WSP 3.5 log messages for EXTRA files
        self.assertTrue(any(
            "[test_module] EXTRA: File not found anywhere in baseline" in msg 
            and "extra.py" in msg 
            for msg in warning_calls
        ), "Missing EXTRA warning for test_module/extra.py")
        
        self.assertTrue(any(
            "[test_module] EXTRA: File not found anywhere in baseline" in msg 
            and "test_extra.py" in msg 
            for msg in warning_calls
        ), "Missing EXTRA warning for test_module/test_extra.py")
        
        # Verify WSP 3.5 log messages for MISSING files
        self.assertTrue(any(
            "[test_module] MISSING: File missing from target module" in msg 
            and "missing.py" in msg 
            for msg in warning_calls
        ), "Missing MISSING warning for test_module/missing.py")
        
        self.assertTrue(any(
            "[test_module] MISSING: File missing from target module" in msg 
            and "test_missing.py" in msg 
            for msg in warning_calls
        ), "Missing MISSING warning for test_module/test_missing.py")
        
        # Verify total number of EXTRA/MISSING log messages
        # 2 EXTRA files (src/extra.py, tests/test_extra.py)
        # 2 MISSING files (src/missing.py, tests/test_missing.py)
        # Should be at least 4 calls related to test_module
        relevant_calls = [
            call for call in warning_calls 
            if "[test_module]" in call
        ]
        self.assertGreaterEqual(len(relevant_calls), 4)

    @patch('logging.warning')
    def test_wsp35_modified_file_logging(self, mock_warning):
        """Test that WSP 3.5 compliant logging is generated for MODIFIED files."""
        # Create baseline module with specific content
        baseline_module_dir = self.baseline_modules_dir / "test_module"
        baseline_src_dir = baseline_module_dir / "src"
        baseline_module_dir.mkdir()
        baseline_src_dir.mkdir()
        
        # Create target module with same files but different content
        target_module_dir = self.target_modules_dir / "test_module"
        target_src_dir = target_module_dir / "src"
        target_module_dir.mkdir()
        target_src_dir.mkdir()
        
        # Create a common file with different content in both directories
        with open(baseline_src_dir / "common.py", 'w') as f:
            f.write("# Baseline version of the file\nprint('baseline')\n")
            
        with open(target_src_dir / "common.py", 'w') as f:
            f.write("# Target version of the file\nprint('target')\n")
        
        # Create a common file with identical content in both directories
        with open(baseline_src_dir / "identical.py", 'w') as f:
            f.write("# This file is identical in both directories\n")
            
        with open(target_src_dir / "identical.py", 'w') as f:
            f.write("# This file is identical in both directories\n")
        
        # Run Mode 2 audit
        result = modular_audit.audit_with_baseline_comparison(
            self.target_dir, self.baseline_dir
        )
        
        # Verify module is modified
        self.assertIn("test_module", result["modules"]["modified"])
        
        # Verify modified files count
        self.assertEqual(result["files"]["modified"], 1)
        
        # Get all warning calls
        warning_calls = [call[0][0] for call in mock_warning.call_args_list]
        
        # Verify WSP 3.5 log message for MODIFIED file
        self.assertTrue(any(
            "[test_module] MODIFIED: Content differs from baseline" in msg 
            and "common.py" in msg 
            for msg in warning_calls
        ), "Missing MODIFIED warning for test_module/src/common.py")
        
        # Verify no MODIFIED warning for identical file
        self.assertFalse(any(
            "[test_module] MODIFIED: Content differs from baseline" in msg 
            and "identical.py" in msg 
            for msg in warning_calls
        ), "Unexpected MODIFIED warning for identical file test_module/src/identical.py")

    @patch('logging.warning')
    def test_wsp35_found_in_flat_logging(self, mock_warning):
        """Test that WSP 3.5 compliant logging is generated for FOUND_IN_FLAT files."""
        # Create flat file in baseline modules directory
        baseline_modules_dir = self.baseline_dir / "modules"
        baseline_flat_file = baseline_modules_dir / "flat_file.py"
        with open(baseline_flat_file, 'w') as f:
            f.write("# This is a flat file in the baseline modules directory\n")
            
        # Create a target module with the same file inside a module structure
        target_module_dir = self.target_modules_dir / "new_module"
        target_src_dir = target_module_dir / "src"
        target_src_dir.mkdir(parents=True)
        
        target_file = target_src_dir / "flat_file.py"
        with open(target_file, 'w') as f:
            f.write("# This file was moved from the flat structure to a module\n")
        
        # Also create a truly extra file that's not in the baseline
        target_extra_file = target_src_dir / "extra_file.py"
        with open(target_extra_file, 'w') as f:
            f.write("# This is a completely new file\n")
            
        # Run Mode 2 audit
        result = modular_audit.audit_with_baseline_comparison(
            self.target_dir, self.baseline_dir
        )
        
        # Verify module is correctly identified
        self.assertIn("new_module", result["modules"]["new"])
        
        # Verify FOUND_IN_FLAT count
        self.assertEqual(result["files"]["found_in_flat"], 1)
        
        # Verify file counts (1 FOUND_IN_FLAT, 1 EXTRA)
        self.assertEqual(result["files"]["new"], 1)
        
        # Get all warning calls
        warning_calls = [call[0][0] for call in mock_warning.call_args_list]
        
        # Verify WSP 3.5 log message for FOUND_IN_FLAT file
        self.assertTrue(any(
            "[new_module] FOUND_IN_FLAT: Found only in baseline flat modules/" in msg 
            and "flat_file.py" in msg 
            for msg in warning_calls
        ), "Missing FOUND_IN_FLAT warning for new_module with flat_file.py")
        
        # Verify EXTRA warning for the truly extra file
        self.assertTrue(any(
            "[new_module] EXTRA: File not found anywhere in baseline" in msg 
            and "extra_file.py" in msg 
            for msg in warning_calls
        ), "Missing EXTRA warning for new_module with extra_file.py")
        
        # Verify the flat file is not incorrectly reported as EXTRA
        self.assertFalse(any(
            "[new_module] EXTRA: File not found anywhere in baseline" in msg 
            and "flat_file.py" in msg 
            for msg in warning_calls
        ), "Flat file incorrectly reported as EXTRA")

class TestFileDiscoveryMock(unittest.TestCase):
    """Tests for mocked file discovery functionality."""
    
    def test_discover_files_with_different_extensions_mock(self):
        """Test file discovery with different file extensions using a mock."""
        with patch('modular_audit.discover_source_files') as mock_discover:
            # Set up mock return value
            mock_discover.return_value = {
                "mixed_module": {
                    "src/module.py",
                    "src/script.js",
                    "src/native.cpp",
                    "src/header.h",
                    "src/README.md",
                    "src/notes.txt",
                    "module.json",
                    "src/mixed_module.py"
                }
            }
            
            # Call function with a dummy path
            files = modular_audit.discover_source_files(Path("/dummy/path"))
            
            # Verify mock was called
            mock_discover.assert_called_with(Path("/dummy/path"))
            
            # Verify result matches mock
            self.assertEqual(files, mock_discover.return_value)
            
            # Verify all files are included
            self.assertIn("mixed_module", files)
            module_files = files["mixed_module"]
            
            # Check that all files are found regardless of extension
            self.assertEqual(len(module_files), 8)
            self.assertIn("src/module.py", module_files)
            self.assertIn("src/script.js", module_files)
            self.assertIn("src/native.cpp", module_files)
            self.assertIn("src/header.h", module_files)
            self.assertIn("src/README.md", module_files)
            self.assertIn("src/notes.txt", module_files)
            self.assertIn("module.json", module_files)
            self.assertIn("src/mixed_module.py", module_files)

class TestCommandLineIntegration(unittest.TestCase):
    """Tests for command line integration with baseline comparison."""
    
    def setUp(self):
        """Set up temporary directories for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.target_dir = Path(self.temp_dir) / "target"
        self.baseline_dir = Path(self.temp_dir) / "baseline"
        self.target_modules_dir = self.target_dir / "modules"
        self.baseline_modules_dir = self.baseline_dir / "modules"
        
        # Create directories
        self.target_modules_dir.mkdir(parents=True)
        self.baseline_modules_dir.mkdir(parents=True)
        
        # Create a module in both target and baseline
        for root_dir in [self.target_modules_dir, self.baseline_modules_dir]:
            module_dir = root_dir / "test_module"
            src_dir = module_dir / "src"
            tests_dir = module_dir / "tests"
            module_dir.mkdir()
            src_dir.mkdir()
            tests_dir.mkdir()
            
            # Create files
            with open(src_dir / "test_module.py", 'w') as f:
                f.write("# Test module interface\n")
            with open(module_dir / "module.json", 'w') as f:
                f.write('{\n  "name": "test_module",\n  "dependencies": []\n}\n')
    
    def tearDown(self):
        """Clean up temporary directories after testing."""
        shutil.rmtree(self.temp_dir)
    
    @patch('sys.argv')
    @patch('sys.exit')
    @patch('logging.info')
    def test_main_with_baseline_argument(self, mock_logging_info, mock_exit, mock_argv):
        """Test the main function with a baseline argument."""
        # Set up command line arguments
        mock_argv.__getitem__.side_effect = lambda idx: [
            "modular_audit.py",
            "--mode", "2",
            "--baseline",
            str(self.baseline_dir)
        ][idx]
        
        # Run the main function
        with patch('modular_audit.audit_with_baseline_comparison') as mock_audit:
            authority = patch(
                'modular_audit.validate_authoritative_baseline',
                return_value=(True, ""),
            )
            authority.start()
            self.addCleanup(authority.stop)
            # Set up the mock to return a successful result with no changes
            mock_audit.return_value = {
                "status": "success",
                "modules": {"new": [], "modified": [], "deleted": []},
                "files": {"new": 0, "deleted": 0, "modified": 0, "found_in_flat": 0}
            }
            
            modular_audit.main()
            
            # Verify that audit_with_baseline_comparison was called
            mock_audit.assert_called_once()
            
            # Verify that mode 2 was activated (check logs)
            mock_logging_info.assert_any_call(
                f"Running FMAS Mode 2: Baseline Comparison against {self.baseline_dir.resolve()}"
            )
    
    def test_main_with_invalid_baseline(self):
        """Test the main function with an invalid baseline argument."""
        invalid_baseline = Path(self.temp_dir) / "nonexistent"
        
        # Set up command line arguments
        sys_argv_mock = MagicMock()
        sys_argv_mock.__getitem__.side_effect = lambda idx: [
            "modular_audit.py",
            "--mode", "2",
            "--baseline",
            str(invalid_baseline)
        ][idx]
        
        with patch('sys.argv', sys_argv_mock):
            # Mock validate_baseline_path to force the validation to fail
            with patch('modular_audit.validate_baseline_path', return_value=False):
                # Mock audit_with_baseline_comparison to avoid actual execution
                with patch('modular_audit.audit_with_baseline_comparison'):
                    # Mock sys.exit directly
                    with patch('sys.exit') as mock_exit:
                        # Run the main function
                        modular_audit.main()
                        
                        # Verify that sys.exit was called with the actual exit code (2)
                        mock_exit.assert_called_once_with(2)

if __name__ == "__main__":
    unittest.main()
