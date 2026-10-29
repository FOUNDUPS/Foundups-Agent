"""Local lifecycle helpers for existing livechat owners (no independent state/store).

DAE, coordinator and rotation instances retain all session/task ownership. These
functions settle owned work or fail closed; they cannot roll back browser effects.
"""
import asyncio
import logging
import time

logger = logging.getLogger(__name__)

async def _await_owned_completion(task: asyncio.Task) -> bool:
    """Keep ownership through repeated cancellation; report deferred cancellation."""
    cancelled = False
    caller = asyncio.current_task()
    cancellation_count = caller.cancelling()
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            # Cancellation of the owned task must not cancel its healthy owner.
            current_count = caller.cancelling()
            cancelled |= current_count > cancellation_count
            cancellation_count = current_count
        except Exception:
            break
    if not task.cancelled():
        task.exception()  # Retrieve failures even when the caller is cancelling.
    return cancelled


async def _finish_subprocess(spawn_task, drains, wait_task) -> None:
    """Recover a racing spawn, then reap the child and finish every pipe reader."""
    try:
        process = await spawn_task
    except Exception:
        return  # Spawn failed; the original await owns that exception.
    if not drains:
        drains.append(asyncio.create_task(process.communicate()))
    if process.returncode is None:
        try:
            process.terminate()
        except ProcessLookupError:
            pass
        try:
            await asyncio.wait_for(process.wait(), timeout=2)
        except asyncio.TimeoutError:
            try:
                process.kill()
            except ProcessLookupError:
                pass
    await process.wait()
    if wait_task is not None:
        drains.append(wait_task)
    await asyncio.gather(*drains, return_exceptions=True)


async def await_thread_worker(worker, timeout):
    try:
        # Run in thread to prevent Selenium from blocking event loop
        result = await asyncio.wait_for(
            asyncio.shield(worker),
            timeout=timeout
        )
        logger.info(f"[THREAD] Complete: {result.get('stats', {})}")
        return result

    except asyncio.TimeoutError:
        logger.error(f"[THREAD] Timeout after {timeout}s")
        logger.warning("[THREAD] Waiting for worker completion before releasing ownership")
        return {
            'error': 'timeout',
            'stats': {'comments_processed': 0, 'errors': 1},
            'timeout_seconds': timeout
        }

    except Exception as e:
        logger.error(f"[THREAD] Error: {e}", exc_info=True)
        return {
            'error': str(e),
            'stats': {'comments_processed': 0, 'errors': 1}
        }
    finally:
        if await _await_owned_completion(worker):
            raise asyncio.CancelledError()


def is_live_channel(self, channel_id):
    """Session confirmation survives an absent/expired advisory file signal."""
    if channel_id and channel_id == self.get_confirmed_live_channel():
        return True
    try:
        from modules.platform_integration.stream_resolver.src.live_stream_signal import get_live_channel
        return bool(channel_id and channel_id == get_live_channel())
    except ImportError:
        return False


async def settle_owned_engagements(self, channel_id):
    """Settle owned comment invocations for one channel; retain other work."""
    selected = [(task, runner) for task, (cid, port, runner)
                in tuple(self._active_engagements.items()) if cid == channel_id]
    cancelled = False
    for task, runner in selected:
        if not task.done() and getattr(runner, "supports_settled_cancellation", False):
            task.cancel()
        cancelled = await _await_owned_completion(task) or cancelled
        if not task.cancelled():
            task.result()  # Cleanup failures must block the handoff.
    if cancelled:
        raise asyncio.CancelledError


async def run_owned_engagement(self, runner, *, channel_id, video_id,
                                max_comments, browser_port=9222):
    """Own the real runner through cancellation, including thread completion."""
    deferred = {"deferred": "live_channel", "stats": {"comments_processed": 0}}
    for owned, (cid, port, owner) in tuple(self._active_engagements.items()):
        if cid == channel_id and owned.done() and not owned.cancelled() and owned.exception():
            raise RuntimeError("Prior channel operation has unresolved cleanup") from owned.exception()
    if self._is_live_channel(channel_id):
        return deferred

    async def invoke():
        # A confirmation can arrive between task creation and first execution.
        if self._is_live_channel(channel_id):
            return deferred
        return await runner.run_engagement(
            channel_id=channel_id, video_id=video_id,
            max_comments=max_comments, browser_port=browser_port)

    task = asyncio.create_task(invoke())
    self._active_engagements[task] = (channel_id, browser_port, runner)
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        caller_cancelled = bool(asyncio.current_task().cancelling())
        if caller_cancelled and not task.done() and getattr(runner, "supports_settled_cancellation", False):
            task.cancel()
        caller_cancelled = await _await_owned_completion(task) or caller_cancelled
        if not task.cancelled():
            task.result()
        if caller_cancelled:
            raise
        return deferred  # A targeted handoff leaves this browser loop alive.
    finally:
        # Failure is not proof of cleanup. Retain it so a later handoff cannot
        # mistake an empty map for settlement or overwrite unknown child state.
        if task.done() and (task.cancelled() or task.exception() is None):
            self._active_engagements.pop(task, None)


async def run_confirmed_live_chat(self):
    """Confirm actual session identity, settle its comment work, then poll."""
    if getattr(self, "_live_handoff_running", False):
        raise RuntimeError("A live handoff/session is already owned")
    self._live_handoff_running = True
    try:
        if not self.livechat or not await self.livechat.initialize():
            logger.warning("[LOCK] Live chat unavailable; keeping comment engagement active")
            return
        channel_id = getattr(self.livechat, "channel_id", None)
        chat_id = getattr(self.livechat, "live_chat_id", None)
        if (not getattr(self.livechat, "youtube", None)
                or not isinstance(channel_id, str) or not channel_id.strip()
                or not isinstance(chat_id, str) or not chat_id.strip()):
            logger.warning("[LOCK] No confirmed API chat/channel identity; handoff deferred")
            return

        # Reserve before any await: no fresh comment dispatch may enter this channel.
        self._confirmed_live_channel_id = channel_id
        heartbeat_task = None
        try:
            await self.terminate_comment_engagement(for_live_handoff=True)
            self._live_stream_pending = False
            self._live_chat_active = True
            if self.telemetry:
                heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self.livechat.is_running = True
            await self.livechat.run_polling_loop()
        except KeyboardInterrupt:
            logger.info("[STOP] Monitoring stopped by operator")
        except Exception:
            logger.exception("Live session handoff or polling failed")
        finally:
            await close_live_session(self, heartbeat_task)
    finally:
        self._live_handoff_running = False


async def close_live_session(self, heartbeat_task):
    # Clear even when settlement, polling or heartbeat cleanup fails/cancels.
    self._confirmed_live_channel_id = None
    self._live_chat_active = False
    try:
        if self.livechat:
            self.livechat.stop_listening()
    finally:
        if heartbeat_task:
            heartbeat_task.cancel()
            cancelled = await _await_owned_completion(heartbeat_task)
            if cancelled:
                raise asyncio.CancelledError
    if self.telemetry and self.current_stream_id:
        try:
            self.telemetry.record_stream_end(self.current_stream_id)
            self.current_stream_id = None
        except Exception:
            logger.warning("Failed to record stream end")


async def cancel_browser_tasks(tasks):
    for _b, _t in tasks.items():
        if _t and not _t.done():
            _t.cancel()
    cleanup = asyncio.ensure_future(asyncio.gather(
        *tasks.values(), return_exceptions=True))
    await _await_owned_completion(cleanup)
    for outcome in cleanup.result():
        if isinstance(outcome, Exception):
            raise outcome


async def run_owned_rotation(self, supervisor, browser_name, max_comments, operation):
    if not hasattr(self, "_rotation_supervisors"):
        self._rotation_supervisors = {}
    previous = self._rotation_supervisors.get(browser_name)
    if previous is not None and getattr(previous, "_owned_tasks", {}):
        raise RuntimeError("Prior rotation owner has unresolved child state")
    self._rotation_supervisors[browser_name] = supervisor
    try:
        result = await supervisor.run_rotation(
            operation=operation,
            max_items_per_channel=max_comments if max_comments > 0 else 10,
        )
    finally:
        if (self._rotation_supervisors.get(browser_name) is supervisor
                and not getattr(supervisor, "_owned_tasks", {})):
            self._rotation_supervisors.pop(browser_name, None)
    return result

async def dispatch_comment_engagement(self, runner, channel_id, video_id,
                                      max_comments, mode, groups):
    await self._ensure_multi_channel_coordinator(runner, mode)
    if self.multi_channel_coordinator._is_live_channel(channel_id):
        return {"deferred": "live_channel"}
    browser_port = 9223 if any(ch.get("id") == channel_id for ch in groups.get("edge", [])) else 9222
    self._log_studio_context(channel_id, label="comment_engagement")
    return await self.multi_channel_coordinator._run_owned_engagement(
        runner, channel_id=channel_id, video_id=video_id,
        max_comments=max_comments, browser_port=browser_port)


def comment_accounts(self, accounts):
    """Filter dynamically at iteration time, including pre-audit navigation."""
    for account in accounts:
        if not self._is_live_channel(account[1]):
            yield account



async def retry_verified_channel(self, driver, runner, channel_id,
                                  account_name, max_comments, browser_port):
    self.set_active_channel(channel_id)
    self.log_studio_context(channel_id, f"{account_name} comment_engagement_retry", driver)

    retry_result = await self._run_owned_engagement(runner,
        channel_id=channel_id,
        video_id=None,
        max_comments=max_comments,
        browser_port=browser_port,
    )

    if retry_result and retry_result.get("deferred"):
        return None
    retry_result = retry_result or {}
    retry_stats = retry_result.get('stats', {})
    retry_processed = retry_stats.get('comments_processed', 0)

    self.update_engagement_status(channel_id, {
        "all_processed": bool(retry_stats.get("all_processed", False)),
        "stats": retry_stats,
        "error": retry_result.get('error'),
        "updated_at": time.time(),
    })

    if retry_result.get('error'):
        logger.error(f"[ROTATE] {account_name} retry failed: {retry_result.get('error')}")
    else:
        logger.info(f"[ROTATE] {account_name} retry complete: {retry_processed} comments processed")

    return retry_processed

