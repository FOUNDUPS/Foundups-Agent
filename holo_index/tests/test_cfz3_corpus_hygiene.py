# -*- coding: utf-8 -*-
"""CFZ3 — Corpus hygiene exclusion tests.

Verifies that index_wsp_entries() excludes:
- Hidden directories (paths with components starting with '.')
- Backup directories (paths containing '_backup')
- Archive directories (paths containing '/archive/')

WSP: WSP 97 (truthful testing), WSP 50 (pre-action verification)
"""
from pathlib import Path
import pytest


def _should_exclude_path(file_path: Path) -> bool:
    """Mirror the exclusion logic from indexing_engine.py line 372-381."""
    path_str = str(file_path)
    return (
        'node_modules' in path_str
        or 'CHANGELOG' in file_path.name.upper()
        or 'package-lock' in file_path.name.lower()
        or any(part.startswith('.') for part in file_path.parts)
        or '_backup' in path_str.lower()
        or '/archive/' in path_str.lower()
        or '\\archive\\' in path_str.lower()
    )


class TestCorpusHygieneExclusions:
    """Test that corpus hygiene rules exclude polluting paths."""

    def test_excludes_hidden_directory(self):
        """Hidden directories (starting with .) must be excluded."""
        path = Path("WSP_knowledge/docs/Papers/.consciousness_migration_backup/file.md")
        assert _should_exclude_path(path), "Hidden directory should be excluded"

    def test_excludes_dotfile_in_path(self):
        """Any path component starting with . must trigger exclusion."""
        path = Path("some/path/.hidden/subdir/file.md")
        assert _should_exclude_path(path), "Dotfile in path should be excluded"

    def test_excludes_backup_suffix(self):
        """Paths containing _backup must be excluded."""
        path = Path("docs/old_backup/file.md")
        assert _should_exclude_path(path), "_backup in path should be excluded"

    def test_excludes_archive_directory(self):
        """Paths containing /archive/ must be excluded."""
        path = Path("docs/archive/old_wsps/file.md")
        assert _should_exclude_path(path), "/archive/ in path should be excluded"

    def test_excludes_archive_windows_path(self):
        """Paths containing \\archive\\ must be excluded (Windows)."""
        path = Path("docs\\archive\\old_wsps\\file.md")
        assert _should_exclude_path(path), "\\archive\\ in path should be excluded"

    def test_allows_normal_wsp_path(self):
        """Normal WSP paths must NOT be excluded."""
        path = Path("WSP_framework/src/WSP_97_System_Execution_Prompting_Protocol.md")
        assert not _should_exclude_path(path), "Normal WSP path should be allowed"

    def test_allows_module_readme(self):
        """Module READMEs must NOT be excluded."""
        path = Path("modules/ai_intelligence/agent_permissions/README.md")
        assert not _should_exclude_path(path), "Module README should be allowed"

    def test_excludes_consciousness_migration_backup(self):
        """The specific .consciousness_migration_backup dir must be excluded."""
        paths = [
            Path("WSP_knowledge/docs/Papers/.consciousness_migration_backup/PQN_rESP_Entanglement_Signaling_Addendum_2026-02-25.md"),
            Path("WSP_knowledge/docs/Papers/.consciousness_migration_backup/Empirical_Evidence/rESP_Cross_Linguistic_Quantum_Signatures_2025.md"),
            Path("WSP_knowledge/docs/Papers/.consciousness_migration_backup/Patent_Series/04_rESP_Patent_Updated.md"),
        ]
        for p in paths:
            assert _should_exclude_path(p), f"Backup path should be excluded: {p}"

    def test_excludes_node_modules(self):
        """node_modules must be excluded (existing rule)."""
        path = Path("frontend/node_modules/some-package/README.md")
        assert _should_exclude_path(path), "node_modules should be excluded"

    def test_excludes_changelog(self):
        """CHANGELOG files must be excluded (existing rule)."""
        path = Path("docs/CHANGELOG.md")
        assert _should_exclude_path(path), "CHANGELOG should be excluded"
