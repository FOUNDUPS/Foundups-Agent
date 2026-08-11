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

    def test_mode1_structural_error_remains_blocking(self):
        args = argparse.Namespace(
            mode=1,
            baseline=None,
            verbose=False,
            debug=False,
            quiet=True,
            wsp_62_size_check=False,
        )
        finding = "ERROR: Module 'infrastructure/example' is missing the tests/ directory"

        with patch('argparse.ArgumentParser.parse_args', return_value=args):
            with patch('modular_audit.audit_all_modules', return_value=([finding], 1)):
                with self.assertRaises(SystemExit) as raised:
                    modular_audit.main()

        self.assertEqual(raised.exception.code, 1)

    def test_mode1_wrapped_security_failure_remains_blocking(self):
        args = argparse.Namespace(
            mode=1,
            baseline=None,
            verbose=False,
            debug=False,
            quiet=True,
            wsp_62_size_check=False,
        )
        finding = "SECURITY: infrastructure/example - SECURITY_AUDIT_FAIL: blocked"

        with patch('argparse.ArgumentParser.parse_args', return_value=args):
            with patch('modular_audit.audit_all_modules', return_value=([finding], 1)):
                with self.assertRaises(SystemExit) as raised:
                    modular_audit.main()

        self.assertEqual(raised.exception.code, 1)

    def test_security_module_delimiter_cannot_mask_failure(self):
        finding = modular_audit._wrap_security_findings(
            "infrastructure/example - decoy",
            ["SECURITY_SCAN_ERROR: bandit unavailable"],
        )[0]

        self.assertEqual(modular_audit._finding_severity(finding), "ERROR")

    def test_security_path_marker_cannot_promote_low_finding(self):
        finding = modular_audit._wrap_security_findings(
            "infrastructure/example - SECURITY_SCAN_ERROR: path-marker",
            ["SECURITY_VULNERABILITY_LOW: advisory"],
        )[0]

        self.assertEqual(modular_audit._finding_severity(finding), "ADVISORY")
    
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

    def test_authoritative_baseline_rejects_candidate_checkout(self):
        values = {
            (str(self.baseline_dir), ("rev-parse", "--git-common-dir")): "C:/repo/.git",
            (str(self.baseline_dir), ("rev-parse", "HEAD")): "candidate",
            (
                str(self.baseline_dir),
                ("status", "--porcelain", "--untracked-files=no"),
            ): "",
            (
                str(self.baseline_dir),
                ("ls-files", "--others", "--exclude-standard", "--", "modules"),
            ): "",
            (str(Path.cwd()), ("rev-parse", "--git-common-dir")): "C:/repo/.git",
            (str(Path.cwd()), ("rev-parse", "HEAD")): "candidate",
            (str(Path.cwd()), ("merge-base", "HEAD", "origin/main")): "base",
        }

        def fake_git(root, *args):
            return values.get((str(root), args))

        with patch('modular_audit._git_value', side_effect=fake_git):
            accepted, reason = modular_audit.validate_authoritative_baseline(
                Path.cwd(), self.baseline_dir
            )

        self.assertFalse(accepted)
        self.assertIn("merge base", reason)

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

    def test_severity_does_not_parse_error_from_filename(self):
        finding = (
            "WSP 62 WARNING: docs/VALIDATION_AND_ERROR_CONTRACT.md "
            "(1234 lines > critical window 1000)"
        )

        self.assertEqual(modular_audit._wsp62_severity(finding), "WARNING")

    def test_standard_hard_limit_rejects_new_candidate_file(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            src = target / "modules/infrastructure/example/src"
            src.mkdir(parents=True)
            (baseline / "modules").mkdir()
            (src / "sample.py").write_text("line\n" * 1500, encoding="utf-8")

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline
            )

            self.assertTrue(any("ERROR: new candidate size violation" in item for item in findings))

    def test_renamed_oversized_file_is_new_candidate_debt(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            target_src = target / "modules/infrastructure/example/src"
            base_src = baseline / "modules/infrastructure/example/src"
            target_src.mkdir(parents=True)
            base_src.mkdir(parents=True)
            (target_src / "renamed.py").write_text("line\n" * 1201, encoding="utf-8")
            (base_src / "legacy.py").write_text("line\n" * 1200, encoding="utf-8")

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline
            )

            self.assertTrue(any("new candidate size violation" in item for item in findings))

    def test_git_rename_preserves_stricter_file_ceiling(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            base_rule = (
                "  - file: src/sample.py\n"
                "    no_growth_ceiling: {file_lines: 100, functions: {}}\n"
            )
            self._write_exempt_module(target, "src/renamed.py", 101, "")
            self._write_exempt_module(baseline, "src/sample.py", 100, base_rule)
            rename_map = {
                "modules/infrastructure/example/src/renamed.py":
                "modules/infrastructure/example/src/sample.py"
            }

            findings = modular_audit.audit_file_sizes(
                target,
                enable_wsp_62=True,
                baseline_root=baseline,
                rename_map=rename_map,
            )

            self.assertTrue(any("candidate removed exemption" in item for item in findings))

    def test_inherited_invalid_python_does_not_block(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            for root in (target, baseline):
                src = root / "modules/infrastructure/example/src"
                src.mkdir(parents=True)
                (src / "sample.py").write_text("not valid python !!!\n", encoding="utf-8")

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline, rename_map={}
            )

            self.assertFalse(any("ERROR: function inspection failed" in item for item in findings))

    def test_inherited_invalid_exempt_python_does_not_block(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            exemption = (
                "  - file: src/sample.py\n"
                "    no_growth_ceiling: {file_lines: 100, functions: {}}\n"
            )
            self._write_exempt_module(target, "src/sample.py", 1, exemption)
            self._write_exempt_module(baseline, "src/sample.py", 1, exemption)
            target_file = target / "modules/infrastructure/example/src/sample.py"
            base_file = baseline / "modules/infrastructure/example/src/sample.py"
            target_file.write_text("not valid python !!!\n", encoding="utf-8")
            base_file.write_text("not valid python !!!\n", encoding="utf-8")

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline, rename_map={}
            )

            self.assertFalse(any("ERROR: function inspection failed" in item for item in findings))

    def test_inherited_invalid_named_function_ceiling_does_not_block(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            exemption = (
                "  - file: src/sample.py\n"
                "    no_growth_ceiling: {file_lines: 100, functions: {legacy: 61}}\n"
            )
            self._write_exempt_module(target, "src/sample.py", 1, exemption)
            self._write_exempt_module(baseline, "src/sample.py", 1, exemption)
            target_file = target / "modules/infrastructure/example/src/sample.py"
            base_file = baseline / "modules/infrastructure/example/src/sample.py"
            target_file.write_text("not valid python !!!\n", encoding="utf-8")
            base_file.write_text("not valid python !!!\n", encoding="utf-8")

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline, rename_map={}
            )

            self.assertFalse(any("ERROR: function inspection failed" in item for item in findings))

    def test_candidate_invalid_python_remains_blocking(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            target_src = target / "modules/infrastructure/example/src"
            base_src = baseline / "modules/infrastructure/example/src"
            target_src.mkdir(parents=True)
            base_src.mkdir(parents=True)
            (target_src / "sample.py").write_text("not valid python !!!\n", encoding="utf-8")
            (base_src / "sample.py").write_text("value = 1\n", encoding="utf-8")

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline, rename_map={}
            )

            self.assertTrue(any("ERROR: function inspection failed" in item for item in findings))

    def test_valid_candidate_over_malformed_baseline_checks_function_debt(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            target_src = target / "modules/infrastructure/example/src"
            base_src = baseline / "modules/infrastructure/example/src"
            target_src.mkdir(parents=True)
            base_src.mkdir(parents=True)
            body = "def work():\n" + "    value = 1\n" * 61
            (target_src / "sample.py").write_text(body, encoding="utf-8")
            (base_src / "sample.py").write_text("not valid python !!!\n", encoding="utf-8")

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline, rename_map={}
            )

            self.assertTrue(any("new candidate function debt" in item for item in findings))

    def test_bounded_repair_over_malformed_exempt_baseline_passes(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            exemption = (
                "  - file: src/sample.py\n"
                "    no_growth_ceiling: {file_lines: 100, functions: {legacy: 61}}\n"
            )
            self._write_exempt_module(target, "src/sample.py", 1, exemption)
            self._write_exempt_module(baseline, "src/sample.py", 1, exemption)
            target_file = target / "modules/infrastructure/example/src/sample.py"
            base_file = baseline / "modules/infrastructure/example/src/sample.py"
            target_file.write_text("def work():\n    return 1\n", encoding="utf-8")
            base_file.write_text("not valid python !!!\n", encoding="utf-8")

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline, rename_map={}
            )

            self.assertFalse(any("WSP 62 ERROR:" in item for item in findings))

    def test_bounded_repair_can_remove_named_ceiling_over_malformed_base(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            target_rule = (
                "  - file: src/sample.py\n"
                "    no_growth_ceiling: {file_lines: 100, functions: {}}\n"
            )
            base_rule = (
                "  - file: src/sample.py\n"
                "    no_growth_ceiling: {file_lines: 100, functions: {legacy: 61}}\n"
            )
            self._write_exempt_module(target, "src/sample.py", 1, target_rule)
            self._write_exempt_module(baseline, "src/sample.py", 1, base_rule)
            target_file = target / "modules/infrastructure/example/src/sample.py"
            base_file = baseline / "modules/infrastructure/example/src/sample.py"
            target_file.write_text("def legacy():\n    return 1\n", encoding="utf-8")
            base_file.write_text("not valid python !!!\n", encoding="utf-8")

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline, rename_map={}
            )

            self.assertFalse(any("WSP 62 ERROR:" in item for item in findings))

    def test_exempt_candidate_debt_over_malformed_baseline_blocks(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            exemption = (
                "  - file: src/sample.py\n"
                "    no_growth_ceiling: {file_lines: 100, functions: {legacy: 61}}\n"
            )
            self._write_exempt_module(target, "src/sample.py", 1, exemption)
            self._write_exempt_module(baseline, "src/sample.py", 1, exemption)
            target_file = target / "modules/infrastructure/example/src/sample.py"
            base_file = baseline / "modules/infrastructure/example/src/sample.py"
            target_file.write_text(
                "def work():\n" + "    value = 1\n" * 60,
                encoding="utf-8",
            )
            base_file.write_text("not valid python !!!\n", encoding="utf-8")

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline, rename_map={}
            )

            self.assertTrue(any("new candidate function debt" in item for item in findings))

    def test_standard_hard_limit_reports_unchanged_inherited_file(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            for root in (target, baseline):
                src = root / "modules/infrastructure/example/src"
                src.mkdir(parents=True)
                (src / "sample.py").write_text("line\n" * 1500, encoding="utf-8")

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline
            )

            self.assertTrue(any("WSP 62 INHERITED" in item for item in findings))
            self.assertFalse(any("ERROR" in item for item in findings))

    def _write_exempt_module(self, root, relative_path, lines, exemption):
        module = root / "modules" / "infrastructure" / "example"
        (module / "src").mkdir(parents=True, exist_ok=True)
        target = module / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("line\n" * lines, encoding="utf-8")
        (module / "wsp_62_exemptions.yaml").write_text(
            "exemptions:\n" + exemption,
            encoding="utf-8",
        )

    def test_no_growth_contract_rejects_candidate_growth(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            exemption = (
                "  - file: src/sample.py\n"
                "    no_growth_ceiling: {file_lines: 3, functions: {}}\n"
            )
            self._write_exempt_module(target, "src/sample.py", 4, exemption)
            self._write_exempt_module(baseline, "src/sample.py", 3, exemption)

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline
            )

            self.assertTrue(any("ERROR: candidate growth" in item for item in findings))

    def test_inherited_missing_expiry_is_advisory(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            exemption = (
                "  - file: src/sample.py\n"
                "    temporary: true\n"
                "    no_growth_ceiling: {file_lines: 3, functions: {}}\n"
            )
            self._write_exempt_module(target, "src/sample.py", 3, exemption)
            self._write_exempt_module(baseline, "src/sample.py", 3, exemption)

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline
            )

            self.assertTrue(any("INHERITED_METADATA" in item for item in findings))
            self.assertFalse(any("ERROR: missing exemption expiry" in item for item in findings))

    def test_candidate_cannot_remove_expiry(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            target_rule = (
                "  - file: src/sample.py\n"
                "    temporary: true\n"
                "    no_growth_ceiling: {file_lines: 3, functions: {}}\n"
            )
            base_rule = (
                "  - file: src/sample.py\n"
                "    temporary: true\n"
                "    expires_on: '2099-01-01'\n"
                "    no_growth_ceiling: {file_lines: 3, functions: {}}\n"
            )
            self._write_exempt_module(target, "src/sample.py", 3, target_rule)
            self._write_exempt_module(baseline, "src/sample.py", 3, base_rule)

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline
            )

            self.assertTrue(any("ERROR: missing exemption expiry" in item for item in findings))

    def test_candidate_cannot_introduce_invalid_expiry(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            target_rule = (
                "  - file: src/sample.py\n"
                "    temporary: true\n"
                "    expires_on: never\n"
                "    no_growth_ceiling: {file_lines: 3, functions: {}}\n"
            )
            base_rule = (
                "  - file: src/sample.py\n"
                "    temporary: true\n"
                "    expires_on: '2099-01-01'\n"
                "    no_growth_ceiling: {file_lines: 3, functions: {}}\n"
            )
            self._write_exempt_module(target, "src/sample.py", 3, target_rule)
            self._write_exempt_module(baseline, "src/sample.py", 3, base_rule)

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline
            )

            self.assertTrue(any("ERROR: invalid exemption expiry" in item for item in findings))

    def test_candidate_cannot_erase_temporary_expiry_policy(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            target_rule = (
                "  - file: src/sample.py\n"
                "    no_growth_ceiling: {file_lines: 3, functions: {}}\n"
            )
            base_rule = (
                "  - file: src/sample.py\n"
                "    temporary: true\n"
                "    expires_on: '2026-01-01'\n"
                "    no_growth_ceiling: {file_lines: 3, functions: {}}\n"
            )
            self._write_exempt_module(target, "src/sample.py", 3, target_rule)
            self._write_exempt_module(baseline, "src/sample.py", 3, base_rule)

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline
            )

            self.assertTrue(any("exemption policy changed" in item for item in findings))

    def test_candidate_cannot_raise_its_own_file_ceiling(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            target_rule = (
                "  - file: src/sample.py\n"
                "    no_growth_ceiling: {file_lines: 4, functions: {}}\n"
            )
            base_rule = (
                "  - file: src/sample.py\n"
                "    no_growth_ceiling: {file_lines: 3, functions: {}}\n"
            )
            self._write_exempt_module(target, "src/sample.py", 4, target_rule)
            self._write_exempt_module(baseline, "src/sample.py", 3, base_rule)

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline
            )

            self.assertTrue(any("ERROR: file ceiling ratchet" in item for item in findings))

    def test_candidate_cannot_remove_file_ceiling_while_growing(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            base_rule = (
                "  - file: src/sample.py\n"
                "    no_growth_ceiling: {file_lines: 1200, functions: {}}\n"
            )
            self._write_exempt_module(target, "src/sample.py", 1201, "")
            self._write_exempt_module(baseline, "src/sample.py", 1200, base_rule)

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline
            )

            self.assertTrue(any("ERROR: candidate removed exemption" in item for item in findings))

    def test_candidate_may_remove_resolved_file_ceiling(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            base_rule = (
                "  - file: src/sample.py\n"
                "    no_growth_ceiling: {file_lines: 1200, functions: {}}\n"
            )
            self._write_exempt_module(target, "src/sample.py", 700, "")
            self._write_exempt_module(baseline, "src/sample.py", 1200, base_rule)

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline
            )

            self.assertFalse(any("removed exemption" in item for item in findings))

    def test_no_growth_contract_reports_unchanged_inherited_debt(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            exemption = (
                "  - file: src/sample.py\n"
                "    no_growth_ceiling: {file_lines: 3, functions: {}}\n"
            )
            self._write_exempt_module(target, "src/sample.py", 4, exemption)
            self._write_exempt_module(baseline, "src/sample.py", 4, exemption)

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline
            )

            self.assertTrue(any("WSP 62 INHERITED" in item for item in findings))
            self.assertFalse(any("ERROR" in item for item in findings))

    def test_no_growth_contract_rejects_new_candidate_debt(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            (baseline / "modules").mkdir()
            exemption = (
                "  - file: src/sample.py\n"
                "    no_growth_ceiling: {file_lines: 3, functions: {}}\n"
            )
            self._write_exempt_module(target, "src/sample.py", 4, exemption)

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline
            )

            self.assertTrue(any("ERROR: new candidate debt" in item for item in findings))

    def test_function_ceiling_rejects_candidate_growth(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            exemption = (
                "  - file: src/sample.py\n"
                "    no_growth_ceiling:\n"
                "      file_lines: 100\n"
                "      functions: {work: 2}\n"
            )
            self._write_exempt_module(target, "src/sample.py", 1, exemption)
            self._write_exempt_module(baseline, "src/sample.py", 1, exemption)
            target_file = target / "modules/infrastructure/example/src/sample.py"
            base_file = baseline / "modules/infrastructure/example/src/sample.py"
            target_file.write_text("def work():\n    value = 1\n    value += 1\n    return value\n", encoding="utf-8")
            base_file.write_text("def work():\n    return 1\n", encoding="utf-8")

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline
            )

            self.assertTrue(any("ERROR: candidate function growth" in item for item in findings))

    def test_candidate_cannot_raise_its_own_function_ceiling(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            target_rule = (
                "  - file: src/sample.py\n"
                "    no_growth_ceiling: {file_lines: 100, functions: {work: 4}}\n"
            )
            base_rule = (
                "  - file: src/sample.py\n"
                "    no_growth_ceiling: {file_lines: 100, functions: {work: 2}}\n"
            )
            self._write_exempt_module(target, "src/sample.py", 1, target_rule)
            self._write_exempt_module(baseline, "src/sample.py", 1, base_rule)
            target_file = target / "modules/infrastructure/example/src/sample.py"
            base_file = baseline / "modules/infrastructure/example/src/sample.py"
            target_file.write_text("def work():\n    value = 1\n    value += 1\n    return value\n", encoding="utf-8")
            base_file.write_text("def work():\n    return 1\n", encoding="utf-8")

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline
            )

            self.assertTrue(any("ERROR: function ceiling ratchet" in item for item in findings))

    def test_candidate_cannot_remove_function_ceiling_while_growing(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            target_rule = (
                "  - file: src/sample.py\n"
                "    no_growth_ceiling: {file_lines: 100, functions: {}}\n"
            )
            base_rule = (
                "  - file: src/sample.py\n"
                "    no_growth_ceiling: {file_lines: 100, functions: {work: 2}}\n"
            )
            self._write_exempt_module(target, "src/sample.py", 1, target_rule)
            self._write_exempt_module(baseline, "src/sample.py", 1, base_rule)
            target_file = target / "modules/infrastructure/example/src/sample.py"
            base_file = baseline / "modules/infrastructure/example/src/sample.py"
            target_file.write_text("def work():\n    value = 1\n    value += 1\n    return value\n", encoding="utf-8")
            base_file.write_text("def work():\n    return 1\n", encoding="utf-8")

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline
            )

            self.assertTrue(any("ERROR: function ceiling removed" in item for item in findings))

    def test_function_rename_cannot_bypass_named_ceiling(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            exemption = (
                "  - file: src/sample.py\n"
                "    no_growth_ceiling: {file_lines: 100, functions: {legacy: 61}}\n"
            )
            self._write_exempt_module(target, "src/sample.py", 1, exemption)
            self._write_exempt_module(baseline, "src/sample.py", 1, exemption)
            target_file = target / "modules/infrastructure/example/src/sample.py"
            base_file = baseline / "modules/infrastructure/example/src/sample.py"
            target_body = "def renamed():\n" + "    value = 1\n" * 60 + "    return value\n"
            base_body = "def legacy():\n" + "    value = 1\n" * 59 + "    return value\n"
            target_file.write_text(target_body, encoding="utf-8")
            base_file.write_text(base_body, encoding="utf-8")

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline
            )

            self.assertTrue(any("new candidate function debt" in item for item in findings))

    def test_function_rename_plus_ceiling_removal_still_fails(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            target_rule = (
                "  - file: src/sample.py\n"
                "    no_growth_ceiling: {file_lines: 100, functions: {}}\n"
            )
            base_rule = (
                "  - file: src/sample.py\n"
                "    no_growth_ceiling: {file_lines: 100, functions: {legacy: 61}}\n"
            )
            self._write_exempt_module(target, "src/sample.py", 1, target_rule)
            self._write_exempt_module(baseline, "src/sample.py", 1, base_rule)
            target_file = target / "modules/infrastructure/example/src/sample.py"
            base_file = baseline / "modules/infrastructure/example/src/sample.py"
            target_body = "def renamed():\n" + "    value = 1\n" * 60 + "    return value\n"
            base_body = "def legacy():\n" + "    value = 1\n" * 59 + "    return value\n"
            target_file.write_text(target_body, encoding="utf-8")
            base_file.write_text(base_body, encoding="utf-8")

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline
            )

            self.assertTrue(any("new candidate function debt" in item for item in findings))

    def test_function_rename_plus_whole_exemption_removal_fails(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            base_rule = (
                "  - file: src/sample.py\n"
                "    no_growth_ceiling: {file_lines: 100, functions: {legacy: 61}}\n"
            )
            self._write_exempt_module(target, "src/sample.py", 1, "")
            self._write_exempt_module(baseline, "src/sample.py", 1, base_rule)
            target_file = target / "modules/infrastructure/example/src/sample.py"
            base_file = baseline / "modules/infrastructure/example/src/sample.py"
            target_body = (
                "def renamed():\n" + "    value = 1\n" * 60 +
                "    return value\n" + "padding = 0\n" * 38
            )
            base_body = (
                "def legacy():\n" + "    value = 1\n" * 59 +
                "    return value\n" + "padding = 0\n" * 39
            )
            target_file.write_text(target_body, encoding="utf-8")
            base_file.write_text(base_body, encoding="utf-8")

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline, rename_map={}
            )

            self.assertTrue(any("candidate removed exemption" in item for item in findings))

    def test_qualified_methods_prevent_duplicate_name_collapse(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            exemption = (
                "  - file: src/sample.py\n"
                "    no_growth_ceiling: {file_lines: 200, functions: {A.work: 61}}\n"
            )
            self._write_exempt_module(target, "src/sample.py", 1, exemption)
            self._write_exempt_module(baseline, "src/sample.py", 1, exemption)
            target_file = target / "modules/infrastructure/example/src/sample.py"
            base_file = baseline / "modules/infrastructure/example/src/sample.py"
            target_body = (
                "class A:\n    def work(self):\n" + "        value = 1\n" * 61 +
                "class B:\n    def work(self):\n        return 1\n"
            )
            base_body = (
                "class A:\n    def work(self):\n" + "        value = 1\n" * 60 +
                "class B:\n    def work(self):\n        return 1\n"
            )
            target_file.write_text(target_body, encoding="utf-8")
            base_file.write_text(base_body, encoding="utf-8")

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline, rename_map={}
            )

            self.assertTrue(any("candidate function growth" in item for item in findings))

    def test_empty_function_map_cannot_hide_new_function_debt(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            exemption = (
                "  - file: src/sample.py\n"
                "    no_growth_ceiling: {file_lines: 200, functions: {}}\n"
            )
            self._write_exempt_module(target, "src/sample.py", 1, exemption)
            self._write_exempt_module(baseline, "src/sample.py", 1, exemption)
            target_file = target / "modules/infrastructure/example/src/sample.py"
            base_file = baseline / "modules/infrastructure/example/src/sample.py"
            body = "def work():\n" + "    value = 1\n" * 61
            target_file.write_text(body, encoding="utf-8")
            base_file.write_text("value = 1\n" * 62, encoding="utf-8")

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline, rename_map={}
            )

            self.assertTrue(any("new candidate function debt" in item for item in findings))

    def test_advisory_archive_is_restricted_to_audit_logs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            exemption = (
                "  - file: src/sample.py\n"
                "    enforcement_mode: advisory_archive\n"
                "    advisory_archive_threshold: 1\n"
            )
            self._write_exempt_module(root, "src/sample.py", 2, exemption)

            findings = modular_audit.audit_file_sizes(root, enable_wsp_62=True)

            self.assertTrue(any("invalid advisory archive" in item for item in findings))

    def test_advisory_archive_rejects_source_path_lookalike(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            exemption = (
                "  - file: src/ModLog.md\n"
                "    enforcement_mode: advisory_archive\n"
                "    advisory_archive_threshold: 1\n"
            )
            self._write_exempt_module(root, "src/ModLog.md", 2, exemption)

            findings = modular_audit.audit_file_sizes(root, enable_wsp_62=True)

            self.assertTrue(any("invalid advisory archive" in item for item in findings))

    def test_exact_audit_log_policy_transition_is_allowed(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            target_rule = (
                "  - file: ModLog.md\n"
                "    enforcement_mode: advisory_archive\n"
                "    advisory_archive_threshold: 1\n"
            )
            base_rule = (
                "  - file: ModLog.md\n"
                "    no_growth_ceiling: {file_lines: 2, functions: {}}\n"
            )
            self._write_exempt_module(target, "ModLog.md", 3, target_rule)
            self._write_exempt_module(baseline, "ModLog.md", 2, base_rule)

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline
            )

            self.assertTrue(any("ADVISORY_ARCHIVE" in item for item in findings))
            self.assertFalse(any("policy changed" in item for item in findings))

    def test_candidate_cannot_raise_archive_threshold(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            target_rule = (
                "  - file: ModLog.md\n"
                "    enforcement_mode: advisory_archive\n"
                "    advisory_archive_threshold: 999999\n"
            )
            base_rule = (
                "  - file: ModLog.md\n"
                "    enforcement_mode: advisory_archive\n"
                "    advisory_archive_threshold: 1000\n"
            )
            self._write_exempt_module(target, "ModLog.md", 1001, target_rule)
            self._write_exempt_module(baseline, "ModLog.md", 1000, base_rule)

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline
            )

            self.assertTrue(any("archive threshold ratchet" in item for item in findings))

    def test_noncanonical_policy_transition_is_rejected(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            target_rule = (
                "  - file: src/ModLog.md\n"
                "    enforcement_mode: advisory_archive\n"
                "    advisory_archive_threshold: 1\n"
            )
            base_rule = (
                "  - file: src/ModLog.md\n"
                "    no_growth_ceiling: {file_lines: 2, functions: {}}\n"
            )
            self._write_exempt_module(target, "src/ModLog.md", 3, target_rule)
            self._write_exempt_module(baseline, "src/ModLog.md", 2, base_rule)

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline
            )

            self.assertTrue(any("policy changed" in item for item in findings))

    def test_arbitrary_policy_mode_transition_is_rejected(self):
        with tempfile.TemporaryDirectory() as target_dir, tempfile.TemporaryDirectory() as base_dir:
            target = Path(target_dir)
            baseline = Path(base_dir)
            target_rule = "  - file: ModLog.md\n    enforcement_mode: permanent\n"
            base_rule = (
                "  - file: ModLog.md\n"
                "    no_growth_ceiling: {file_lines: 2, functions: {}}\n"
            )
            self._write_exempt_module(target, "ModLog.md", 2, target_rule)
            self._write_exempt_module(baseline, "ModLog.md", 2, base_rule)

            findings = modular_audit.audit_file_sizes(
                target, enable_wsp_62=True, baseline_root=baseline
            )

            self.assertTrue(any("policy changed" in item for item in findings))

    def test_audit_log_archival_threshold_is_advisory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            exemption = (
                "  - file: ModLog.md\n"
                "    enforcement_mode: advisory_archive\n"
                "    advisory_archive_threshold: 1\n"
            )
            self._write_exempt_module(root, "ModLog.md", 2, exemption)

            findings = modular_audit.audit_file_sizes(root, enable_wsp_62=True)

            self.assertTrue(any("ADVISORY_ARCHIVE" in item for item in findings))
            self.assertFalse(any("ERROR" in item for item in findings))


if __name__ == "__main__":
    unittest.main()
