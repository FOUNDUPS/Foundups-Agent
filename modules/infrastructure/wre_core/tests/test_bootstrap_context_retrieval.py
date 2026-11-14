"""
Test suite for RedDog Bootstrap Context Retrieval Phase 1.

Slice: REDDOG_BOOTSTRAP_CONTEXT_RETRIEVAL_PHASE1
Verifies boot retrieval layer is properly wired.
"""

import re
from pathlib import Path

import pytest

# Repository root
REPO_ROOT = Path(__file__).resolve().parents[4]

# Bootstrap files directory
BOOTSTRAP_DIR = REPO_ROOT / "WSP_knowledge" / "red_dog_external_state"

# WSP_00 locations
WSP_00_FRAMEWORK = REPO_ROOT / "WSP_framework" / "src" / "WSP_00_Zen_State_Attainment_Protocol.md"
WSP_00_KNOWLEDGE = REPO_ROOT / "WSP_knowledge" / "src" / "WSP_00_Zen_State_Attainment_Protocol.md"

# Expected sibling files in BOOTSTRAP.md read-order
SIBLING_FILES = [
    "MEMORY_BOUNDARY.md",
    "CURRENT_CONTEXT.md",
    "WORK_TO_WORK_LINEAGE.md",
    "ACTIVE_RESEARCH_THREADS.md",
]

# Secret patterns that must NOT appear in bootstrap files
SECRET_PATTERNS = [
    r"AIza[A-Za-z0-9_-]{35}",  # Google API key
    r"sk-[A-Za-z0-9]{48}",  # OpenAI API key
    r"hf_[A-Za-z0-9]{34}",  # HuggingFace token
    r"ghp_[A-Za-z0-9]{36}",  # GitHub PAT (classic)
    r"gho_[A-Za-z0-9]{36}",  # GitHub OAuth token
    r"github_pat_[A-Za-z0-9_]{82}",  # GitHub PAT (fine-grained)
    r"Bearer\s+[A-Za-z0-9_-]{20,}",  # Bearer tokens
    r"oauth_token\s*=\s*['\"][^'\"]+['\"]",  # OAuth token assignment
    r"refresh_token\s*=\s*['\"][^'\"]+['\"]",  # Refresh token assignment
    r"eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*",  # JWT pattern
]


class TestBootstrapFileExists:
    """Verify BOOTSTRAP.md exists."""

    def test_bootstrap_md_exists(self):
        """BOOTSTRAP.md must exist in red_dog_external_state directory."""
        bootstrap_path = BOOTSTRAP_DIR / "BOOTSTRAP.md"
        assert bootstrap_path.exists(), f"BOOTSTRAP.md not found at {bootstrap_path}"


class TestBootstrapNamesAllSiblings:
    """Verify BOOTSTRAP.md names all 4 sibling files."""

    def test_bootstrap_names_memory_boundary(self):
        """BOOTSTRAP.md must reference MEMORY_BOUNDARY.md."""
        content = (BOOTSTRAP_DIR / "BOOTSTRAP.md").read_text(encoding="utf-8")
        assert "MEMORY_BOUNDARY.md" in content

    def test_bootstrap_names_current_context(self):
        """BOOTSTRAP.md must reference CURRENT_CONTEXT.md."""
        content = (BOOTSTRAP_DIR / "BOOTSTRAP.md").read_text(encoding="utf-8")
        assert "CURRENT_CONTEXT.md" in content

    def test_bootstrap_names_work_to_work_lineage(self):
        """BOOTSTRAP.md must reference WORK_TO_WORK_LINEAGE.md."""
        content = (BOOTSTRAP_DIR / "BOOTSTRAP.md").read_text(encoding="utf-8")
        assert "WORK_TO_WORK_LINEAGE.md" in content

    def test_bootstrap_names_active_research_threads(self):
        """BOOTSTRAP.md must reference ACTIVE_RESEARCH_THREADS.md."""
        content = (BOOTSTRAP_DIR / "BOOTSTRAP.md").read_text(encoding="utf-8")
        assert "ACTIVE_RESEARCH_THREADS.md" in content


class TestAllSiblingFilesExist:
    """Verify all 4 sibling files exist."""

    @pytest.mark.parametrize("filename", SIBLING_FILES)
    def test_sibling_file_exists(self, filename):
        """Each sibling file named in BOOTSTRAP.md must exist."""
        filepath = BOOTSTRAP_DIR / filename
        assert filepath.exists(), f"{filename} not found at {filepath}"


class TestWSP00ReferencesBootstrap:
    """Verify both WSP_00 mirrors reference BOOTSTRAP.md."""

    def test_wsp00_framework_references_bootstrap(self):
        """WSP_framework/src/WSP_00*.md must reference BOOTSTRAP.md."""
        content = WSP_00_FRAMEWORK.read_text(encoding="utf-8")
        assert "BOOTSTRAP.md" in content, "WSP_00 in WSP_framework does not reference BOOTSTRAP.md"

    def test_wsp00_knowledge_references_bootstrap(self):
        """WSP_knowledge/src/WSP_00*.md must reference BOOTSTRAP.md."""
        content = WSP_00_KNOWLEDGE.read_text(encoding="utf-8")
        assert "BOOTSTRAP.md" in content, "WSP_00 in WSP_knowledge does not reference BOOTSTRAP.md"


class TestWSP00MirrorEquality:
    """Verify WSP_framework and WSP_knowledge mirrors are byte-identical for amendment block."""

    def test_wsp00_mirrors_byte_identical(self):
        """Both WSP_00 files must be byte-identical."""
        framework_content = WSP_00_FRAMEWORK.read_bytes()
        knowledge_content = WSP_00_KNOWLEDGE.read_bytes()
        assert framework_content == knowledge_content, "WSP_00 mirrors are not byte-identical"


class TestNoSecretPatterns:
    """Verify no secret patterns in any of the 5 bootstrap files."""

    @pytest.fixture
    def all_bootstrap_files(self):
        """Return list of all bootstrap files to check."""
        return [BOOTSTRAP_DIR / "BOOTSTRAP.md"] + [BOOTSTRAP_DIR / f for f in SIBLING_FILES]

    @pytest.mark.parametrize("pattern", SECRET_PATTERNS)
    def test_no_secret_pattern_in_bootstrap(self, pattern, all_bootstrap_files):
        """No secret pattern should match in any bootstrap file."""
        compiled = re.compile(pattern)
        for filepath in all_bootstrap_files:
            if filepath.exists():
                content = filepath.read_text(encoding="utf-8")
                match = compiled.search(content)
                assert match is None, f"Secret pattern '{pattern}' found in {filepath.name}"


class TestREADMELinksBootstrap:
    """Verify README.md links to BOOTSTRAP.md."""

    def test_readme_links_bootstrap(self):
        """README.md must contain a link to BOOTSTRAP.md."""
        readme_path = BOOTSTRAP_DIR / "README.md"
        content = readme_path.read_text(encoding="utf-8")
        assert "BOOTSTRAP.md" in content, "README.md does not link to BOOTSTRAP.md"
