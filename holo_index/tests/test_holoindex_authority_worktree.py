"""Fail-closed authority-worktree selection tests."""

from __future__ import annotations

from pathlib import Path

from holo_index.authority_worktree import (
    AUTHORITY_REPO_ROOT_ENV,
    AUTHORITY_ROOT_DIRTY,
    AUTHORITY_ROOT_HEAD_MISMATCH,
    AUTHORITY_ROOT_INVALID,
    AUTHORITY_ROOT_UNRELATED,
    authority_selection_matches_target,
    resolve_holoindex_authority_root,
    resolve_holoindex_runtime_root,
)
from holo_index.repository_state import RepositoryState, repository_root_digest


SHA = "a" * 40


def _state(head: str = SHA, *, clean: bool = True) -> RepositoryState:
    return RepositoryState(
        head_sha=head,
        clean=clean,
        state_digest="sha256:" + "b" * 64,
        error="" if clean else "HOLOINDEX_REPOSITORY_DIRTY",
    )


def _roots(tmp_path: Path) -> tuple[Path, Path]:
    workspace = tmp_path / "Foundups-Agent"
    authority = tmp_path / "Foundups-Agent-holo-authority"
    workspace.mkdir()
    authority.mkdir()
    (workspace / ".git").mkdir()
    (authority / ".git").write_text("gitdir: ../.git/worktrees/holo", encoding="utf-8")
    return workspace, authority


def _state_reader(workspace: Path, authority: Path, authority_state: RepositoryState):
    def read(path: Path) -> RepositoryState:
        return authority_state if path == authority else _state()

    return read


def test_configured_clean_same_head_authority_is_selected(tmp_path: Path) -> None:
    workspace, authority = _roots(tmp_path)
    common = tmp_path / "common.git"
    result = resolve_holoindex_authority_root(
        workspace,
        environment={AUTHORITY_REPO_ROOT_ENV: str(authority)},
        state_reader=_state_reader(workspace, authority, _state()),
        common_dir_reader=lambda _path: common,
    )

    assert result.accepted is True
    assert result.selected_root == authority
    assert result.authority_root_digest == repository_root_digest(authority)
    assert result.source == "configured"
    assert result.rejection_reasons == ()


def test_dirty_workspace_can_use_clean_same_head_authority(tmp_path: Path) -> None:
    workspace, authority = _roots(tmp_path)
    common = tmp_path / "common.git"

    def state_reader(path: Path) -> RepositoryState:
        return _state() if path == authority else _state(clean=False)

    result = resolve_holoindex_authority_root(
        workspace,
        environment={AUTHORITY_REPO_ROOT_ENV: str(authority)},
        state_reader=state_reader,
        common_dir_reader=lambda _path: common,
    )

    assert result.accepted is True
    assert result.workspace_overlay_present is True
    assert result.authority_head_sha == result.workspace_head_sha == SHA


def test_existing_deterministic_sibling_is_selected(tmp_path: Path) -> None:
    workspace, authority = _roots(tmp_path)
    result = resolve_holoindex_authority_root(
        workspace,
        environment={},
        state_reader=_state_reader(workspace, authority, _state()),
        common_dir_reader=lambda _path: tmp_path / "common.git",
    )

    assert result.accepted is True
    assert result.selected_root == authority
    assert result.source == "deterministic_sibling"


def test_configured_invalid_path_fails_without_workspace_fallback(
    tmp_path: Path,
) -> None:
    workspace, _authority = _roots(tmp_path)
    result = resolve_holoindex_authority_root(
        workspace,
        environment={AUTHORITY_REPO_ROOT_ENV: "relative/repo"},
        state_reader=lambda _path: _state(),
    )

    assert result.accepted is False
    assert result.error == AUTHORITY_ROOT_INVALID


def test_unrelated_authority_is_rejected(tmp_path: Path) -> None:
    workspace, authority = _roots(tmp_path)
    result = resolve_holoindex_authority_root(
        workspace,
        environment={AUTHORITY_REPO_ROOT_ENV: str(authority)},
        state_reader=_state_reader(workspace, authority, _state()),
        common_dir_reader=lambda path: tmp_path / path.name,
    )

    assert result.accepted is False
    assert result.error == AUTHORITY_ROOT_UNRELATED


def test_dirty_authority_is_rejected(tmp_path: Path) -> None:
    workspace, authority = _roots(tmp_path)
    result = resolve_holoindex_authority_root(
        workspace,
        environment={AUTHORITY_REPO_ROOT_ENV: str(authority)},
        state_reader=_state_reader(workspace, authority, _state(clean=False)),
        common_dir_reader=lambda _path: tmp_path / "common.git",
    )

    assert result.accepted is False
    assert result.error == AUTHORITY_ROOT_DIRTY


def test_different_head_authority_is_rejected(tmp_path: Path) -> None:
    workspace, authority = _roots(tmp_path)
    stale_head = "c" * 40
    result = resolve_holoindex_authority_root(
        workspace,
        environment={AUTHORITY_REPO_ROOT_ENV: str(authority)},
        state_reader=_state_reader(workspace, authority, _state(stale_head)),
        common_dir_reader=lambda _path: tmp_path / "common.git",
    )

    assert result.accepted is False
    assert result.error == AUTHORITY_ROOT_HEAD_MISMATCH
    assert result.selected_root == workspace
    assert result.workspace_head_sha == SHA
    assert result.authority_head_sha == stale_head
    assert result.authority_root_digest == repository_root_digest(authority)
    assert result.workspace_overlay_present is False
    assert authority_selection_matches_target(
        result,
        target_head_sha=SHA,
        authority_root_digest=repository_root_digest(authority),
        allow_stale=True,
        expected_stale_head_sha=stale_head,
    ) is True
    assert authority_selection_matches_target(
        result,
        target_head_sha=SHA,
        authority_root_digest=repository_root_digest(authority),
    ) is False


def test_missing_sibling_preserves_clean_workspace_behavior(tmp_path: Path) -> None:
    workspace = tmp_path / "repo"
    workspace.mkdir()
    (workspace / ".git").mkdir()
    result = resolve_holoindex_authority_root(
        workspace,
        environment={},
        state_reader=lambda _path: _state(),
    )

    assert result.accepted is True
    assert result.selected_root == workspace
    assert result.source == "workspace"
    assert result.workspace_overlay_present is False


def test_dirty_workspace_without_authority_fails_closed(tmp_path: Path) -> None:
    workspace = tmp_path / "repo"
    workspace.mkdir()
    (workspace / ".git").mkdir()
    result = resolve_holoindex_authority_root(
        workspace,
        environment={},
        state_reader=lambda _path: _state(clean=False),
    )

    assert result.accepted is False
    assert result.error == AUTHORITY_ROOT_DIRTY
    assert result.workspace_overlay_present is True


def test_linked_worktree_uses_same_repository_primary_runtime_root(
    tmp_path: Path,
) -> None:
    primary = tmp_path / "Foundups-Agent"
    workspace = tmp_path / "worktrees" / "slice"
    primary.mkdir()
    workspace.mkdir(parents=True)
    common = primary / ".git"
    common.mkdir()
    (workspace / ".git").write_text("gitdir: linked", encoding="utf-8")

    result = resolve_holoindex_runtime_root(
        workspace,
        common_dir_reader=lambda path: (
            common if path in (workspace, primary) else None
        ),
    )

    assert result == primary


def test_runtime_root_falls_back_when_primary_is_not_same_repository(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "worktree"
    unrelated = tmp_path / "unrelated"
    workspace.mkdir()
    unrelated.mkdir()
    (unrelated / ".git").mkdir()
    workspace_common = unrelated / "common.git"

    result = resolve_holoindex_runtime_root(
        workspace,
        common_dir_reader=lambda path: (
            workspace_common if path == workspace else tmp_path / "other.git"
        ),
    )

    assert result == workspace


def test_query_selector_contains_no_mutation_commands() -> None:
    source = (
        Path(__file__).resolve().parents[1] / "authority_worktree.py"
    ).read_text(encoding="utf-8")

    assert '"rev-parse"' in source
    for forbidden in (
        '"checkout"',
        '"switch"',
        '"worktree", "add"',
        '"reset"',
        '"clean"',
        '"index"',
    ):
        assert forbidden not in source
