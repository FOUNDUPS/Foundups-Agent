# -*- coding: utf-8 -*-
"""Tests for full-body chunking in knowledge indexer.

Acceptance test for HOLOINDEX_KNOWLEDGE_FULL_BODY_CHUNKING_PHASE1:
Deep sections (like rESP §4.4) must be retrievable after indexing.

This test creates a mock paper with deep content and verifies that
the indexer produces chunk records containing that content.
"""

import pytest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

from holo_index.core.indexing_engine import (
    index_knowledge_entries,
    _chunk_markdown_by_headings,
)


class TestChunkMarkdownByHeadings:
    """Unit tests for the heading-based chunker."""

    def test_splits_on_headings(self):
        text = """# Title
Intro content here.

## Section 1
First section content.

### Section 1.1
Subsection content.

## Section 2
Second section content.
"""
        chunks = _chunk_markdown_by_headings(text)
        sections = [c['section'] for c in chunks]
        assert 'Section 1' in sections
        assert 'Section 1.1' in sections
        assert 'Section 2' in sections

    def test_large_section_gets_sub_split(self):
        large_content = "word " * 500
        text = f"""# Title

## Big Section
{large_content}
"""
        chunks = _chunk_markdown_by_headings(text, max_chunk_chars=200)
        big_chunks = [c for c in chunks if 'Big Section' in c['section']]
        assert len(big_chunks) > 1
        assert any('part' in c['section'] for c in big_chunks)

    def test_handles_code_fences(self):
        text = """# Title

## Code Example
Here is code:
```python
def foo():
    return "bar"
```
End of section.
"""
        chunks = _chunk_markdown_by_headings(text)
        code_chunk = next(c for c in chunks if c['section'] == 'Code Example')
        assert 'def foo' in code_chunk['content']

    def test_section_44_pattern(self):
        """Regression test: content at line 400+ must be in a chunk."""
        lines = ['# Test Paper\n', 'Author info\n', '\n']
        for i in range(1, 4):
            lines.append(f'## Section {i}\n')
            lines.append(f'Content for section {i}.\n' * 5)
        lines.append('### 4.4 Null-Model Comparison Status\n')
        lines.append('This section discusses N0-N2 head-to-head comparison.\n')
        lines.append('We use phase-randomized surrogates for validation.\n')

        text = ''.join(lines)
        chunks = _chunk_markdown_by_headings(text)

        section_44 = next(
            (c for c in chunks if '4.4' in c['section'] or 'Null-Model' in c['section']),
            None
        )
        assert section_44 is not None, "Section 4.4 chunk not found"
        assert 'phase-randomized surrogates' in section_44['content']


class TestIndexKnowledgeEntriesChunking:
    """Integration tests for knowledge indexer with chunking."""

    @pytest.fixture
    def mock_holo(self, tmp_path: Path):
        """Create a mock HoloIndex with fake collection."""
        holo = MagicMock()
        holo.project_root = tmp_path

        papers_dir = tmp_path / "WSP_knowledge" / "docs" / "Papers"
        papers_dir.mkdir(parents=True)

        collection = MagicMock()
        collection.add = MagicMock()
        holo._reset_collection = MagicMock(return_value=collection)
        holo._get_embedding = MagicMock(return_value=[0.1] * 384)
        holo._log_agent_action = MagicMock()
        holo.knowledge_collection = collection

        return holo, papers_dir, collection

    def test_produces_summary_and_chunk_records(self, mock_holo):
        """Verify indexer creates both paper_summary and paper_chunk records."""
        holo, papers_dir, collection = mock_holo

        paper = papers_dir / "test_paper.md"
        paper.write_text("""# Test Paper
Author: Test

## Abstract
This is the abstract.

## Methods
This is the methods section.
""", encoding='utf-8')

        result = index_knowledge_entries(holo)

        assert result.indexed_count > 1
        assert collection.add.called

        all_ids = []
        all_metas = []
        for call in collection.add.call_args_list:
            _, kwargs = call
            all_ids.extend(kwargs.get('ids', []))
            all_metas.extend(kwargs.get('metadatas', []))

        summary_records = [m for m in all_metas if m.get('record_kind') == 'paper_summary']
        chunk_records = [m for m in all_metas if m.get('record_kind') == 'paper_chunk']

        assert len(summary_records) == 1
        assert len(chunk_records) >= 2

    def test_deep_section_is_indexed(self, mock_holo):
        """§4.4 acceptance: deep content must appear in a chunk document."""
        holo, papers_dir, collection = mock_holo

        lines = ['# rESP Test Paper\n', 'Author: Test\n', '\n']
        for i in range(1, 5):
            lines.append(f'## Section {i}\n')
            lines.append(f'Filler content for section {i}. ' * 20 + '\n')

        lines.append('### 4.4 Null-Model Comparison Status\n')
        lines.append('N0-N2 head-to-head comparison using phase-randomized surrogates.\n')
        lines.append('Candidate detector signals require decoder/tokenizer priors.\n')

        paper = papers_dir / "rESP_Quantum_Self_Reference.md"
        paper.write_text(''.join(lines), encoding='utf-8')

        result = index_knowledge_entries(holo)

        all_docs = []
        all_metas = []
        for call in collection.add.call_args_list:
            _, kwargs = call
            all_docs.extend(kwargs.get('documents', []))
            all_metas.extend(kwargs.get('metadatas', []))

        section_44_found = any(
            'phase-randomized surrogates' in doc or 'Null-Model Comparison' in doc
            for doc in all_docs
        )
        assert section_44_found, "Section 4.4 content not found in indexed chunks"

        section_44_meta = next(
            (m for m in all_metas if '4.4' in m.get('section', '') or 'Null-Model' in m.get('section', '')),
            None
        )
        assert section_44_meta is not None
        assert section_44_meta['record_kind'] == 'paper_chunk'
        assert 'rESP' in section_44_meta['title']

    def test_chunk_ids_are_deterministic(self, mock_holo):
        """Stable IDs: paper_{idx} for summary, paper_{idx}_chunk_{m} for chunks."""
        holo, papers_dir, collection = mock_holo

        paper = papers_dir / "stable_id_test.md"
        paper.write_text("""# Stable ID Test
## Section A
Content A.
## Section B
Content B.
""", encoding='utf-8')

        index_knowledge_entries(holo)

        all_ids = []
        for call in collection.add.call_args_list:
            _, kwargs = call
            all_ids.extend(kwargs.get('ids', []))

        assert 'paper_1' in all_ids
        chunk_ids = [i for i in all_ids if '_chunk_' in i]
        assert len(chunk_ids) >= 2
        assert all(i.startswith('paper_1_chunk_') for i in chunk_ids)

    def test_metadata_has_required_fields(self, mock_holo):
        """All chunk records must have section, section_title, record_kind."""
        holo, papers_dir, collection = mock_holo

        paper = papers_dir / "meta_test.md"
        paper.write_text("""# Metadata Test
## My Section
Section content here.
""", encoding='utf-8')

        index_knowledge_entries(holo)

        all_metas = []
        for call in collection.add.call_args_list:
            _, kwargs = call
            all_metas.extend(kwargs.get('metadatas', []))

        for meta in all_metas:
            assert 'record_kind' in meta
            assert meta['record_kind'] in ('paper_summary', 'paper_chunk')
            if meta['record_kind'] == 'paper_chunk':
                assert 'section' in meta
                assert 'section_title' in meta
                assert meta['section'] == meta['section_title']
