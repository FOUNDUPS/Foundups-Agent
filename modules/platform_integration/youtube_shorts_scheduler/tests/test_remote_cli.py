"""Remote command regressions: no live browser, model or publishing required."""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from modules.platform_integration.youtube_shorts_scheduler import cli
from modules.platform_integration.youtube_shorts_scheduler.src.schedule_tracker import ScheduleTracker
from modules.platform_integration.youtube_shorts_scheduler.src.scheduler import YouTubeShortsScheduler


@pytest.fixture(autouse=True)
def isolate_optional_side_effects(monkeypatch):
    for name in ('YT_SCHEDULE_INCLUDE_PRIVATE', 'YT_SCHEDULER_DO_SYNC',
                 'YT_SCHEDULER_POST_AUDIT', 'YT_SCHEDULE_INDEX_WEAVE'):
        monkeypatch.delenv(name, raising=False)


def test_preflight_rejects_wrong_browser_without_probe():
    with patch.object(cli, 'urlopen') as probe:
        result = cli.scheduling_preflight('move2japan', 'edge')
    assert result['status'] == 'browser_channel_mismatch'
    probe.assert_not_called()


def test_preflight_does_not_equate_port_with_authenticated_channel():
    response = MagicMock()
    response.__enter__.return_value.read.return_value = b'{"webSocketDebuggerUrl":"ws://127.0.0.1/example"}'
    with patch.object(cli, 'urlopen', return_value=response), patch.object(cli.importlib.util, 'find_spec', return_value=True):
        result = cli.scheduling_preflight('move2japan')
    assert result['browser_transport_ready'] is True
    assert result['authentication'] == 'unverified'
    assert result['scheduling_verified'] is False
    assert result['main_py_required'] is False


def test_preflight_reports_unavailable_browser():
    with patch.object(cli, 'urlopen', side_effect=ConnectionRefusedError), patch.object(cli.importlib.util, 'find_spec', return_value=True):
        result = cli.scheduling_preflight('move2japan')
    assert result['success'] is False
    assert result['status'] == 'browser_unavailable'


def test_preflight_cli_never_invokes_scheduler(capsys):
    with patch.object(cli, 'scheduling_preflight', return_value={'success': True}), patch.object(cli, 'run_scheduling') as run:
        assert cli.main(['--channel', 'move2japan', '--preflight']) == 0
    run.assert_not_called()
    assert json.loads(capsys.readouterr().out)['mode'] == 'preflight'


@pytest.mark.parametrize('limit', ['-1', '-20'])
def test_remote_command_rejects_negative_limit(limit):
    with pytest.raises(SystemExit):
        cli.main(['--channel', 'move2japan', '--max-videos', limit])


def test_cli_default_is_whole_batch_and_forwards_exact_ids():
    ids = ['abcdefghijk', 'lmnopqrstuv']
    with patch.object(cli, 'scheduling_preflight', return_value={'success': True}), patch.object(cli, 'run_scheduling', new=AsyncMock(return_value={'success': True})) as run:
        assert cli.main(['--channel', 'move2japan', '--video-ids', ','.join(ids), '--dry-run']) == 0
    args = run.call_args.args[0]
    assert args.max_videos == 0
    assert args.video_ids == ids


@pytest.mark.parametrize('flags', [[], ['--dry-run'], ['--max-videos', '3']])
def test_unscoped_remote_request_never_falls_through_to_old_backlog(flags, capsys):
    with patch.object(cli, 'scheduling_preflight') as probe, patch.object(cli, 'run_scheduling') as run:
        assert cli.main(['--channel', 'move2japan', *flags]) == 2
    probe.assert_not_called()
    run.assert_not_called()
    assert json.loads(capsys.readouterr().out)['status'] == 'clip_selection_required'


@pytest.mark.parametrize('ids', ['', 'abc', 'abcdefghijk,', 'abcdefghijk;bad'])
def test_invalid_batch_fails_before_transport(ids):
    with patch.object(cli, 'scheduling_preflight') as preflight, pytest.raises(SystemExit):
        cli.main(['--channel', 'move2japan', '--video-ids', ids])
    preflight.assert_not_called()


@pytest.mark.parametrize('count', [3, 8, 13, 61])
def test_entire_selected_batch_is_planned_across_pages_without_count_cap(count, monkeypatch):
    monkeypatch.delenv('YT_SCHEDULE_INCLUDE_PRIVATE', raising=False)
    from modules.platform_integration.youtube_shorts_scheduler.tests.test_schedule_include_private import _make_scheduler
    ids = [f'clip{i:07d}' for i in range(count)]
    scheduler = _make_scheduler([], [])
    pages = [[{'video_id': 'unrelated', 'title': 'older upload'}]] + [
        [{'video_id': vid, 'title': vid} for vid in ids[n:n+20]] for n in range(0, count, 20)
    ]
    scheduler._scrape_videos_for_visibility = Mock(side_effect=pages)
    scheduler.dom.has_next_page = Mock(return_value=True)
    scheduler.dom.click_next_page = Mock()
    with patch('asyncio.sleep', new=AsyncMock()):
        result = asyncio.run(scheduler.run_scheduling_cycle(update_metadata=False, video_ids=ids))
    assert [row['video_id'] for row in result['scheduled']] == ids
    assert result['batch_complete'] is True
    assert result['unresolved_video_ids'] == []
    assert result['preview_scope'] == 'selected_batch'
    assert scheduler.dom.click_next_page.call_count == len(pages)-1


def test_missing_selected_clip_is_reported_incomplete(monkeypatch):
    monkeypatch.delenv('YT_SCHEDULE_INCLUDE_PRIVATE', raising=False)
    from modules.platform_integration.youtube_shorts_scheduler.tests.test_schedule_include_private import _make_scheduler
    scheduler = _make_scheduler([{'video_id': 'present', 'title': 'present'}], [])
    scheduler.dom.has_next_page = Mock(return_value=False)
    with patch('asyncio.sleep', new=AsyncMock()):
        result = asyncio.run(scheduler.run_scheduling_cycle(update_metadata=False, video_ids=['present', 'missing']))
    assert result['batch_complete'] is False
    assert result['unresolved_video_ids'] == ['missing']


@pytest.mark.parametrize('count', [3, 8, 13])
def test_execution_schedules_each_selected_clip_only(count):
    from modules.platform_integration.youtube_shorts_scheduler.tests.test_schedule_include_private import _make_scheduler
    ids = [f'clip{i:07d}' for i in range(count)]
    rows = [{'video_id': vid, 'title': vid} for vid in reversed(ids)]
    rows.append({'video_id': 'unrelated', 'title': 'older upload'})
    scheduler = _make_scheduler(rows, [], dry_run=False)
    scheduler.dom.has_next_page = Mock(return_value=False)
    scheduler.dom.navigate_to_video = Mock()
    scheduler.dom.schedule_video = Mock(return_value=True)
    scheduler.dom.edit_title = Mock()
    scheduler.dom.edit_description = Mock()
    with patch('asyncio.sleep', new=AsyncMock()), patch('modules.platform_integration.youtube_shorts_scheduler.src.scheduler.record_schedule_outcome'):
        result = asyncio.run(scheduler.run_scheduling_cycle(update_metadata=False, video_ids=ids))
    assert result['batch_complete'] is True
    assert [call.args[0] for call in scheduler.dom.navigate_to_video.call_args_list] == ids
    assert scheduler.dom.schedule_video.call_count == count
    scheduler.dom.edit_title.assert_not_called()
    scheduler.dom.edit_description.assert_not_called()


def test_cli_marks_partial_batch_unsuccessful_and_passes_selection():
    scheduler = MagicMock(spec=YouTubeShortsScheduler)
    scheduler.connect_browser.return_value = True
    scheduler.run_scheduling_cycle = AsyncMock(return_value={
        'scheduled': [{'video_id': 'present'}], 'errors': [],
        'batch_complete': False, 'unresolved_video_ids': ['missing'],
    })
    args = SimpleNamespace(channel='move2japan', dry_run=False, max_videos=0,
                           preserve_metadata=True, video_ids=['present', 'missing'])
    with patch('modules.platform_integration.youtube_shorts_scheduler.src.scheduler.YouTubeShortsScheduler', return_value=scheduler):
        result = asyncio.run(cli.run_scheduling(args))
    assert result['success'] is False
    assert result['total_scheduled'] == 1
    assert result['unresolved_video_ids'] == ['missing']
    scheduler.run_scheduling_cycle.assert_awaited_once_with(max_videos=0, update_metadata=False, video_ids=args.video_ids)


def test_stalled_pagination_stops_before_any_video_edit(monkeypatch):
    monkeypatch.delenv('YT_SCHEDULE_INCLUDE_PRIVATE', raising=False)
    from modules.platform_integration.youtube_shorts_scheduler.tests.test_schedule_include_private import _make_scheduler
    scheduler = _make_scheduler([], [])
    scheduler._scrape_videos_for_visibility = Mock(return_value=[{'video_id': 'unrelated'}])
    scheduler.dom.has_next_page = Mock(return_value=True)
    scheduler.dom.click_next_page = Mock()
    scheduler.dom.navigate_to_video = Mock()
    with patch('asyncio.sleep', new=AsyncMock()):
        result = asyncio.run(scheduler.run_scheduling_cycle(update_metadata=False, video_ids=['missing']))
    assert result['batch_complete'] is False
    assert 'stalled' in result['errors'][0]['error']
    scheduler.dom.navigate_to_video.assert_not_called()


def test_missing_dependency_returns_machine_readable_failure(capsys):
    with patch.object(cli, 'scheduling_preflight', side_effect=ImportError('missing fixture dependency')):
        assert cli.main(['--channel', 'move2japan', '--preflight']) == 1
    result = json.loads(capsys.readouterr().out)
    assert result['success'] is False
    assert result['status'] == 'missing_dependency'


@pytest.mark.parametrize('dry_run', [False, True])
def test_cli_uses_current_async_contract_and_reports_actual_count(dry_run):
    scheduler = MagicMock(spec=YouTubeShortsScheduler)
    scheduler.connect_browser.return_value = True
    scheduler.run_scheduling_cycle = AsyncMock(return_value={
        'scheduled': [{'video_id': 'example', 'dry_run': dry_run}], 'errors': [],
    })
    args = SimpleNamespace(channel='move2japan', dry_run=dry_run, max_videos=2, preserve_metadata=True)
    with patch('modules.platform_integration.youtube_shorts_scheduler.src.scheduler.YouTubeShortsScheduler', return_value=scheduler) as factory:
        result = asyncio.run(cli.run_scheduling(args))
    factory.assert_called_once_with(channel_key='move2japan', dry_run=dry_run)
    scheduler.run_scheduling_cycle.assert_awaited_once_with(max_videos=2, update_metadata=False)
    scheduler.disconnect.assert_called_once()
    scheduler.close.assert_not_called()
    assert result['total_scheduled'] == (0 if dry_run else 1)
    assert result['total_planned'] == (1 if dry_run else 0)
    assert result['scheduling_verified'] is False
    assert result['verification_status'] == ('preview_only' if dry_run else 'independent_readback_required')


def test_cycle_error_still_disconnects_without_quitting_browser():
    scheduler = MagicMock(spec=YouTubeShortsScheduler)
    scheduler.connect_browser.return_value = True
    scheduler.run_scheduling_cycle = AsyncMock(side_effect=RuntimeError('cycle failed'))
    args = SimpleNamespace(channel='move2japan', dry_run=False, max_videos=1, preserve_metadata=True)
    with patch('modules.platform_integration.youtube_shorts_scheduler.src.scheduler.YouTubeShortsScheduler', return_value=scheduler):
        with pytest.raises(RuntimeError, match='cycle failed'):
            asyncio.run(cli.run_scheduling(args))
    scheduler.disconnect.assert_called_once()
    scheduler.close.assert_not_called()


def test_preview_reservations_never_modify_disk_or_original_tracker(tmp_path):
    tracker = ScheduleTracker('test_channel', tmp_path)
    tracker.increment('Sep 25, 2026', 'already_scheduled')
    before = tracker.tracker_file.read_bytes()
    preview = tracker.preview_copy()
    preview.increment('Sep 26, 2026', 'preview_only')
    assert tracker.tracker_file.read_bytes() == before
    assert not tracker.is_video_scheduled('preview_only')
    assert preview.is_video_scheduled('preview_only')
    assert preview.tracker_file == tracker.tracker_file


def test_readonly_tracker_does_not_create_storage(tmp_path):
    storage = tmp_path / 'absent'
    tracker = ScheduleTracker('test_channel', storage, persist=False)
    tracker.increment('Sep 25, 2026', 'preview_only')
    assert not storage.exists()


def test_preview_slots_uses_in_memory_state_and_custom_storage(tmp_path):
    scheduler = YouTubeShortsScheduler('move2japan', storage_dir=tmp_path)
    scheduler.tracker.increment('Sep 25, 2026', 'existing')
    before = scheduler.tracker.tracker_file.read_bytes()
    slots = asyncio.run(scheduler.preview_slots(4))
    assert len(slots) == 4
    assert scheduler.tracker.tracker_file.read_bytes() == before
    assert sum(scheduler.tracker.schedule.values()) == 1


def test_dry_cycle_exits_without_revisiting_unchanged_rows_or_healing(tmp_path, monkeypatch):
    monkeypatch.setenv('YT_SCHEDULER_POST_AUDIT', 'true')
    monkeypatch.setenv('YT_SCHEDULER_AUDIT_AUTO_HEAL', 'true')
    monkeypatch.delenv('YT_SCHEDULER_DO_SYNC', raising=False)
    monkeypatch.delenv('YT_SCHEDULE_INCLUDE_PRIVATE', raising=False)
    storage = tmp_path / 'no-preview-state'
    scheduler = YouTubeShortsScheduler('move2japan', storage_dir=storage, dry_run=True)
    scheduler.driver = MagicMock()
    scheduler.dom = MagicMock()
    scheduler.dom.read_visibility_filter_state.return_value = {'detected': 'UNLISTED'}
    scheduler.dom.get_unlisted_videos.return_value = [{'video_id': 'example', 'title': 'A clip'}]
    scheduler.ensure_healthy_connection = lambda: True
    auditor = MagicMock(side_effect=AssertionError('preview must not invoke audit healing'))
    with patch('asyncio.sleep', new=AsyncMock()), patch.dict('sys.modules', {
        'modules.platform_integration.youtube_shorts_scheduler.src.schedule_auditor': SimpleNamespace(ScheduleAuditor=auditor),
    }):
        result = asyncio.run(scheduler.run_scheduling_cycle(max_videos=5))
    assert len(result['scheduled']) == 1
    assert result['preview_scope'] == 'first_visible_batch_per_visibility'
    scheduler.dom.get_unlisted_videos.assert_called_once()
    scheduler.dom.navigate_to_video.assert_not_called()
    scheduler.dom.schedule_video.assert_not_called()
    auditor.assert_not_called()
    assert not storage.exists()


def test_bound_is_shared_across_visibility_passes(monkeypatch):
    monkeypatch.setenv('YT_SCHEDULE_INCLUDE_PRIVATE', '1')
    from modules.platform_integration.youtube_shorts_scheduler.tests.test_schedule_include_private import _make_scheduler
    scheduler = _make_scheduler([{'video_id': 'u1', 'title': 'one'}], [{'video_id': 'p1', 'title': 'two'}])
    with patch('asyncio.sleep', new=AsyncMock()):
        result = asyncio.run(scheduler.run_scheduling_cycle(max_videos=1, update_metadata=False))
    assert len(result['scheduled']) == 1
    assert scheduler.dom.navigate_calls == ['UNLISTED']
