import json
from pathlib import Path

import pytest

from holo_index.exporters.graphrag_exporter import GraphRAGExporter


class DummyHoloIndex:
    """Minimal stand-in that mimics the search signature."""

    def __init__(self, files, project_root):
        self.files = files
        self.project_root = project_root

    def search(self, query, limit=10, doc_type_filter="all"):
        hits = []
        for path, metadata in self.files.items():
            if query.lower() in metadata.get("query_match", "").lower():
                hits.append(
                    {
                        "need": metadata.get("title"),
                        "path": str(path),
                        "type": metadata.get("type", "code"),
                    }
                )
        return {"code": hits, "wsps": []}


@pytest.fixture()
def sample_files(tmp_path):
    file_a = tmp_path / "module_a.md"
    file_a.write_text("# Module A\nSome documentation.", encoding="utf-8")
    file_b = tmp_path / "module_b.py"
    file_b.write_text("def foo():\n    return 42\n", encoding="utf-8")
    return {
        file_a: {"title": "Module A Doc", "query_match": "module architecture", "type": "documentation"},
        file_b: {"title": "Module B Code", "query_match": "semantic search", "type": "code"},
    }


def test_exporter_writes_documents(tmp_path, sample_files):
    holo = DummyHoloIndex(sample_files, tmp_path)
    exporter = GraphRAGExporter(holo)

    output_dir = tmp_path / "bundle"
    exporter.export(output_dir, limit=5)

    input_dir = output_dir / "input"
    assert input_dir.exists()

    docs = sorted(input_dir.glob("doc_*.txt"))
    assert len(docs) == 2  # both documents exported

    metadata = json.loads((output_dir / "metadata.json").read_text(encoding="utf-8"))
    assert len(metadata) == 2
    titles = {item["title"] for item in metadata}
    assert "Module A Doc" in titles
    assert "Module B Code" in titles


def test_exporter_skips_unsupported_suffix(tmp_path, sample_files):
    # add unsupported file type
    unsupported = tmp_path / "diagram.png"
    unsupported.write_bytes(b"\x89PNG\r\n")
    sample_files[unsupported] = {"title": "PNG", "query_match": "module architecture", "type": "asset"}

    holo = DummyHoloIndex(sample_files, tmp_path)
    exporter = GraphRAGExporter(holo)
    output_dir = tmp_path / "bundle2"
    exporter.export(output_dir, limit=5)

    docs = sorted((output_dir / "input").glob("doc_*.txt"))
    assert len(docs) == 2  # PNG skipped


class RelativePathHoloIndex:
    """Return repository-relative hits independently of the process CWD."""

    def __init__(self, project_root: Path, hit_path: str):
        self.project_root = project_root
        self.hit_path = hit_path

    def search(self, _query, limit=10):
        return {
            "code": [
                {"need": "Relative", "path": self.hit_path, "type": "code"}
            ],
            "wsps": [],
        }


def test_exporter_resolves_relative_hit_from_authority_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = tmp_path / "authority"
    source = repo_root / "modules" / "example" / "README.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Relative source\n", encoding="utf-8")
    foreign_cwd = tmp_path / "foreign-cwd"
    foreign_cwd.mkdir()
    monkeypatch.chdir(foreign_cwd)

    exporter = GraphRAGExporter(
        RelativePathHoloIndex(repo_root, "modules/example/README.md")
    )

    documents = exporter.collect_documents(queries=["relative"])

    assert len(documents) == 1
    assert documents[0]["path"] == source.resolve().as_posix()
    assert documents[0]["content"] == "# Relative source\n"


def test_exporter_rejects_relative_hit_outside_authority_root(tmp_path: Path) -> None:
    repo_root = tmp_path / "authority"
    repo_root.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("must not export\n", encoding="utf-8")
    exporter = GraphRAGExporter(RelativePathHoloIndex(repo_root, "../outside.md"))

    assert exporter.collect_documents(queries=["relative"]) == []


def test_exporter_rejects_relative_hit_without_authority_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    relative = "modules/example/README.md"
    cwd_source = tmp_path / relative
    cwd_source.parent.mkdir(parents=True)
    cwd_source.write_text("must not inherit CWD authority\n", encoding="utf-8")
    holo = RelativePathHoloIndex(tmp_path / "unused", relative)
    del holo.project_root
    monkeypatch.chdir(tmp_path)

    assert GraphRAGExporter(holo).collect_documents(queries=["relative"]) == []


def test_exporter_rejects_absolute_hit_outside_authority_root(tmp_path: Path) -> None:
    repo_root = tmp_path / "authority"
    repo_root.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("must not export\n", encoding="utf-8")
    exporter = GraphRAGExporter(RelativePathHoloIndex(repo_root, str(outside)))

    assert exporter.collect_documents(queries=["absolute"]) == []
