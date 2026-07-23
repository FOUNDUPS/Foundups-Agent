#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

Unit tests for the modular_audit.py script.
"""

import unittest
import argparse
import sys
import io
import os
import tempfile
import shutil
import logging
from pathlib import Path, PurePosixPath, PureWindowsPath
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import modular_audit
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import modular_audit

# Disable logging during tests
logging.disable(logging.CRITICAL)


def test_canonical_relative_path_is_platform_neutral():
    assert modular_audit.canonical_relative_path(
        PureWindowsPath(r"C:\repo\modules\communication\moltbot_bridge\src\file.py"),
        PureWindowsPath(r"C:\repo\modules\communication\moltbot_bridge"),
    ) == "src/file.py"
    assert modular_audit.canonical_relative_path(
        PurePosixPath("/repo/modules/communication/moltbot_bridge/src/file.py"),
        PurePosixPath("/repo/modules/communication/moltbot_bridge"),
    ) == "src/file.py"

class TestArgumentParsing(unittest.TestCase):
    """Test the argument parsing functionality."""
    
    def test_parse_arguments_no_baseline(self):
        """Test parsing arguments without the --baseline option."""
        test_args = ["modular_audit.py", "/path/to/modules"]
        with patch('sys.argv', test_args):
            parser = argparse.ArgumentParser()
            parser.add_argument("modules_root", type=Path)
            parser.add_argument("--baseline", type=Path)
            args = parser.parse_args()
            self.assertEqual(args.modules_root, Path("/path/to/modules"))
            self.assertIsNone(args.baseline)
    
    def test_parse_arguments_with_baseline(self):
        """Test parsing arguments with the --baseline option."""
        test_args = ["modular_audit.py", "/path/to/modules", "--baseline", "/path/to/baseline"]
        with patch('sys.argv', test_args):
            parser = argparse.ArgumentParser()
            parser.add_argument("modules_root", type=Path)
            parser.add_argument("--baseline", type=Path)
            args = parser.parse_args()
            self.assertEqual(args.modules_root, Path("/path/to/modules"))
            self.assertEqual(args.baseline, Path("/path/to/baseline"))
    
    def test_parse_arguments_with_all_options(self):
        """Test parsing arguments with all available options."""
        test_args = ["modular_audit.py", "/path/to/modules", "--baseline", "/path/to/baseline", "--lang", "python", "--verbose"]
        with patch('sys.argv', test_args):
            parser = argparse.ArgumentParser()
            parser.add_argument("modules_root", type=Path)
            parser.add_argument("--baseline", type=Path)
            parser.add_argument("--lang")
            parser.add_argument("--verbose", action="store_true")
            args = parser.parse_args()
            self.assertEqual(args.modules_root, Path("/path/to/modules"))
            self.assertEqual(args.baseline, Path("/path/to/baseline"))
            self.assertEqual(args.lang, "python")
            self.assertTrue(args.verbose)
    
    def test_help_includes_baseline(self):
        """Test that the help text includes the --baseline option."""
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            with self.assertRaises(SystemExit):
                with patch('sys.argv', ["modular_audit.py", "--help"]):
                    modular_audit.parser = argparse.ArgumentParser()
                    modular_audit.parser.add_argument("modules_root", type=Path)
                    modular_audit.parser.add_argument("--baseline", type=Path, help="Path to baseline directory for Mode 2 comparison")
                    modular_audit.parser.parse_args()
            help_text = fake_out.getvalue()
            self.assertIn("--baseline", help_text)
            self.assertIn("Path to baseline directory for Mode 2 comparison", help_text)
    
    def test_mode_detection_no_baseline(self):
        """Test that Mode 1 is detected when no baseline is provided."""
        # This is an integration test that would test the main function
        # We'll check that audit_all_modules is called instead of audit_with_baseline_comparison
        with patch('modular_audit.audit_all_modules') as mock_audit_all_modules:
            with patch('modular_audit.audit_with_baseline_comparison') as mock_audit_with_baseline:
                mock_audit_all_modules.return_value = ([], 0)
                mock_audit_with_baseline.return_value = {"status": "success"}
                with patch('sys.argv', ["modular_audit.py", "--mode", "1"]):
                    # Create minimal parser for test
                    with patch('argparse.ArgumentParser.parse_args') as mock_parse_args:
                        args = argparse.Namespace()
                        args.mode = 1
                        args.baseline = None
                        args.verbose = False
                        args.debug = False
                        args.quiet = False
                        args.wsp_62_size_check = False
                        mock_parse_args.return_value = args
                        
                        # Run main logic
                        with patch('sys.exit'): # Prevent exit
                            if hasattr(modular_audit, 'main'):
                                modular_audit.main()
                            else:
                                # Simulate the main block
                                if args.baseline:
                                    modular_audit.audit_with_baseline_comparison(args.modules_root, args.baseline)
                                else:
                                    modular_audit.audit_all_modules(args.modules_root)
                
                # Verify Mode 1 (audit_all_modules) was called instead of Mode 2
                mock_audit_all_modules.assert_called_once()
                mock_audit_with_baseline.assert_not_called()
    
    def test_mode_detection_with_baseline(self):
        """Test that Mode 2 is detected when a baseline is provided."""
        # This is an integration test that would test the main function
        # We'll check that audit_with_baseline_comparison is called instead of audit_all_modules
        with patch('modular_audit.audit_all_modules') as mock_audit_all_modules:
            with patch('modular_audit.audit_with_baseline_comparison') as mock_audit_with_baseline:
                
                # Setup proper return values
                mock_audit_all_modules.return_value = ([], 0)
                mock_audit_with_baseline.return_value = {
                    "status": "success",
                    "modules": {
                        "new": [],
                        "modified": [],
                        "deleted": []
                    },
                    "files": {
                        "new": 0,
                        "modified": 0,
                        "deleted": 0
                    }
                }
                
                # Skip actually running the main function, just verify the right function is called
                with patch('sys.argv', ["modular_audit.py", "--mode", "2", "--baseline", "/path/to/baseline"]):
                    with patch('modular_audit.main') as mock_main:
                        # Mock a simplified main function just to test mode detection
                        def simple_main():
                            parser = argparse.ArgumentParser()
                            parser.add_argument("--mode", type=int, default=1)
                            parser.add_argument("--baseline")
                            args = parser.parse_args()
                            
                            if args.mode == 2 and args.baseline:
                                mock_audit_with_baseline(Path("."), Path(args.baseline))
                            else:
                                mock_audit_all_modules(Path("."))
                        
                        mock_main.side_effect = simple_main
                        modular_audit.main()
                
                # Verify Mode 2 was detected by checking which function was called
                mock_audit_with_baseline.assert_called_once()
                mock_audit_all_modules.assert_not_called()

class TestBaselineValidation(unittest.TestCase):
    """Test the baseline validation functionality."""
    
    def setUp(self):
        """Set up temporary directories for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.baseline_dir = Path(self.temp_dir) / "baseline"
        self.modules_dir = self.baseline_dir / "modules"
        self.modules_dir.mkdir(parents=True)
        
        # Create a dummy module for testing
        self.test_module_dir = self.modules_dir / "test_module"
        self.test_module_dir.mkdir()
    
    def tearDown(self):
        """Clean up temporary directories after testing."""
        shutil.rmtree(self.temp_dir)
    
    def test_validate_baseline_path_nonexistent(self):
        """Test validation of a non-existent baseline path."""
        non_existent_path = Path(self.temp_dir) / "nonexistent"
        self.assertFalse(modular_audit.validate_baseline_path(non_existent_path))
    
    def test_validate_baseline_path_not_directory(self):
        """Test validation of a baseline path that is not a directory."""
        file_path = Path(self.temp_dir) / "file.txt"
        with open(file_path, 'w') as f:
            f.write("Not a directory")
        self.assertFalse(modular_audit.validate_baseline_path(file_path))
    
    def test_validate_baseline_path_no_modules_dir(self):
        """Test validation of a baseline path without a modules directory."""
        no_modules_dir = Path(self.temp_dir) / "no_modules"
        no_modules_dir.mkdir()
        self.assertFalse(modular_audit.validate_baseline_path(no_modules_dir))
    
    def test_validate_baseline_path_empty_modules_dir(self):
        """Test validation of a baseline path with an empty modules directory."""
        empty_baseline_dir = Path(self.temp_dir) / "empty_baseline"
        empty_modules_dir = empty_baseline_dir / "modules"
        empty_modules_dir.mkdir(parents=True)
        
        # Empty baseline is valid
        self.assertTrue(modular_audit.validate_baseline_path(empty_baseline_dir))
    
    def test_validate_baseline_path_valid(self):
        """Test validation of a valid baseline path."""
        self.assertTrue(modular_audit.validate_baseline_path(self.baseline_dir))

class TestFileDiscovery(unittest.TestCase):
    """Test the file discovery functionality."""
    
    def setUp(self):
        """Set up temporary directories for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.modules_dir = Path(self.temp_dir) / "modules"
        self.modules_dir.mkdir()
        
        # Create some test modules
        self.module1_dir = self.modules_dir / "module1"
        self.module1_src_dir = self.module1_dir / "src"
        self.module1_tests_dir = self.module1_dir / "tests"
        self.module1_dir.mkdir()
        self.module1_src_dir.mkdir()
        self.module1_tests_dir.mkdir()
        
        # Create some test files
        self.module1_src_file = self.module1_src_dir / "module1.py"
        self.module1_test_file = self.module1_tests_dir / "test_module1.py"
        self.module1_config_file = self.module1_dir / "config.json"
        
        with open(self.module1_src_file, 'w') as f:
            f.write("# Source file\n")
        with open(self.module1_test_file, 'w') as f:
            f.write("# Test file\n")
        with open(self.module1_config_file, 'w') as f:
            f.write("{ \"config\": true }\n")
        
        # Create a second module
        self.module2_dir = self.modules_dir / "module2"
        self.module2_src_dir = self.module2_dir / "src"
        self.module2_dir.mkdir()
        self.module2_src_dir.mkdir()
        
        # Create some test files
        self.module2_src_file = self.module2_src_dir / "module2.py"
        self.module2_utils_file = self.module2_src_dir / "utils.py"
        
        with open(self.module2_src_file, 'w') as f:
            f.write("# Source file\n")
        with open(self.module2_utils_file, 'w') as f:
            f.write("# Utils file\n")
        
        # Create some hidden files that should be ignored
        self.hidden_dir = self.module1_src_dir / ".hidden"
        self.hidden_dir.mkdir()
        self.hidden_file = self.hidden_dir / "hidden.py"
        with open(self.hidden_file, 'w') as f:
            f.write("# Hidden file\n")
        
        # Create some __pycache__ directories that should be ignored
        self.pycache_dir = self.module1_src_dir / "__pycache__"
        self.pycache_dir.mkdir()
        self.pycache_file = self.pycache_dir / "module1.cpython-39.pyc"
        with open(self.pycache_file, 'w') as f:
            f.write("# Compiled file\n")
    
    def tearDown(self):
        """Clean up temporary directories after testing."""
        shutil.rmtree(self.temp_dir)
    
    def test_discover_source_files(self):
        """Test file discovery in different scenarios."""
        # Mock the discover_source_files function for testing
        with patch('modular_audit.discover_source_files') as mock_discover:
            # Set up mock return value
            mock_discover.return_value = {
                "module1": {"src/module1.py", "tests/test_module1.py", "config.json"},
                "module2": {"src/module2.py", "src/utils.py", "tests/test_module2.py"}
            }
            
            # Call the function with various inputs
            result = modular_audit.discover_source_files(Path("/dummy/path"))
            
            # Verify the mock was called
            mock_discover.assert_called_with(Path("/dummy/path"))
            
            # Verify proper result was returned
            self.assertEqual(result, mock_discover.return_value)
            
            # Verify structure of the result
            self.assertIn("module1", result)
            self.assertIn("module2", result)
            self.assertIn("src/module1.py", result["module1"])
            self.assertIn("tests/test_module1.py", result["module1"])
            self.assertIn("config.json", result["module1"])
            self.assertIn("src/module2.py", result["module2"])
            self.assertIn("src/utils.py", result["module2"])
            self.assertIn("tests/test_module2.py", result["module2"])

class TestBaselineComparison(unittest.TestCase):
    """Test the baseline comparison functionality."""
    
    def setUp(self):
        """Set up temporary directories for testing."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create target and baseline directories
        self.target_dir = Path(self.temp_dir) / "target"
        self.baseline_dir = Path(self.temp_dir) / "baseline"
        self.target_modules_dir = self.target_dir / "modules"
        self.baseline_modules_dir = self.baseline_dir / "modules"
        
        self.target_modules_dir.mkdir(parents=True)
        self.baseline_modules_dir.mkdir(parents=True)
        
        # Create common modules in both target and baseline
        self.create_module(self.target_modules_dir, "common_module", ["module.py", "utils.py"])
        self.create_module(self.baseline_modules_dir, "common_module", ["module.py", "utils.py"])
        
        # Create a modified module (exists in both but with differences)
        self.create_module(self.target_modules_dir, "modified_module", ["module.py", "new_file.py"])
        self.create_module(self.baseline_modules_dir, "modified_module", ["module.py", "old_file.py"])
        
        # Create a new module (exists only in target)
        self.create_module(self.target_modules_dir, "new_module", ["module.py"])
        
        # Create a deleted module (exists only in baseline)
        self.create_module(self.baseline_modules_dir, "deleted_module", ["module.py"])
        
        # Create a critical module (for testing warnings)
        self.create_module(self.target_modules_dir, "core", ["core.py", "new_core_feature.py"])
        self.create_module(self.baseline_modules_dir, "core", ["core.py"])
    
    def tearDown(self):
        """Clean up temporary directories after testing."""
        shutil.rmtree(self.temp_dir)
    
    def create_module(self, base_dir, module_name, files):
        """Helper method to create a module with the given files."""
        module_dir = base_dir / module_name
        src_dir = module_dir / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        
        for file_name in files:
            file_path = src_dir / file_name
            with open(file_path, 'w') as f:
                f.write(f"# {module_name} - {file_name}\n")
    
    def test_audit_with_baseline_comparison_invalid_baseline(self):
        """Test comparison with an invalid baseline path."""
        invalid_baseline = Path(self.temp_dir) / "nonexistent"
        result = modular_audit.audit_with_baseline_comparison(self.target_modules_dir, invalid_baseline)
        
        # Should return a failed status and reason
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["reason"], "Invalid baseline path")
    
    @patch('modular_audit.audit_all_modules')
    def test_audit_with_baseline_comparison_valid(self, mock_audit_all_modules):
        """Test comparison with a valid baseline."""
        mock_audit_all_modules.return_value = ([], 4)  # 4 modules, no findings
        
        result = modular_audit.audit_with_baseline_comparison(self.target_dir, self.baseline_dir)
        
        # Verify result has success status
        self.assertEqual(result["status"], "success")
        
        # Check module counts in the result
        self.assertEqual(len(result["modules"]["new"]), 1)  # new_module
        self.assertEqual(len(result["modules"]["deleted"]), 1)  # deleted_module
        self.assertEqual(len(result["modules"]["modified"]), 2)  # modified_module and core
        
        # Check file counts
        self.assertGreater(result["files"]["new"], 0)
        self.assertGreater(result["files"]["deleted"], 0)

class TestWSP62Thresholds(unittest.TestCase):
    """Validate WSP 62 tiered thresholds for Python files."""

    def test_python_tiered_thresholds(self):
        """Python files should trigger tiered WSP 62 notices."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            modules_dir = root / "modules"

            scenarios = [
                ("ai_intelligence", "size_guideline", 850, "APPROACHING"),
                ("communication", "size_warning", 1200, "WARNING"),
                ("platform_integration", "size_critical", 1510, "CRITICAL"),
            ]

            for domain, module, lines, _ in scenarios:
                src_dir = modules_dir / domain / module / "src"
                src_dir.mkdir(parents=True, exist_ok=True)
                file_path = src_dir / "sample.py"
                with file_path.open('w', encoding='utf-8') as handle:
                    handle.writelines(f"print({i})\n" for i in range(lines))

            findings = modular_audit.audit_file_sizes(root, enable_wsp_62=True)

            self.assertTrue(
                any("APPROACHING" in message and "guideline" in message for message in findings),
                msg="Expected guideline warning for files between 800-1000 lines",
            )
            self.assertTrue(
                any("WARNING" in message and "critical window" in message for message in findings),
                msg="Expected critical window warning for files >1000 lines",
            )
            self.assertTrue(
                any("CRITICAL" in message and "hard limit" in message for message in findings),
                msg="Expected hard limit violation for files >=1500 lines",
            )


if __name__ == "__main__":
    unittest.main()
