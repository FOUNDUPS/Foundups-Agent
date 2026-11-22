"""Controlled delayed-queue regressions for the shared Mall player.

Run from the repo root with the existing Python Playwright environment:
    python -B public/member/tests/mall_queue_callbacks_browser.py

Real shell geometry and player code, local routes and a synthetic official-API
provider fixture. This does not exercise real YouTube, network paging, admission,
or a physical iPhone. Every browser/context is closed, including on assertion.
"""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from playwright.sync_api import expect, sync_playwright


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
spec = importlib.util.spec_from_file_location(
    "mall_queue_fixture", HERE / "mall_scoped_video_browser.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)

BOUND_FILES = (
    "public/member/index.html",
    "public/member/js/mall-video-player.js",
    "public/member/js/mall-video-projection.js",
    "public/member/js/mall-tile-field.js",
    "public/member/css/mall-video-player.css",
    "public/member/css/mall-video-projection.css",
    "public/member/css/mall-tile-field.css",
    "public/member/css/member.css",
    "public/member/mall-public-video-catalog.json",
    "public/member/tests/mall_scoped_video_browser.py",
    "public/member/tests/mall_queue_callbacks_browser.py",
)


def source_hashes():
    return {name: hashlib.sha256((REPO / name).read_bytes()).hexdigest()
            for name in BOUND_FILES}


# Expose the fixture's provider API to simulate a native iframe Pause action.
# Application code cannot reach this test-only handle.
PROVIDER = fixture.provider + """
;(() => {
  if (window.top !== window) return;
  const Original = window.YT.Player;
  window.YT.Player = function (...args) {
    const player = new Original(...args);
    window.queueFixtureNativePlayer = player;
    return player;
  };
})();
"""


def settle(page):
    page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
    # Covers the fixture's 25ms load and queued API callbacks after resolution.
    page.wait_for_timeout(120)


def setup(page):
    page.goto("https://hpc.foundups.com/member/", wait_until="domcontentloaded")
    page.wait_for_function("!!window.mallVideoPlayer && document.documentElement.dataset.mallVideoLayout === 'phone' && !!document.querySelector('#mallTileField .mall-tile')")
    clips = deepcopy(fixture.videos[:4])
    page.evaluate("""clips => {
      window.queueProbe = {calls:0, resolved:false, pinches:0};
      window.callbackQueue = clips.slice(0,2);
      window.appendedQueue = clips.slice(2);
      mallVideoPlayer.open('hpc', callbackQueue, 1, {
        scoped:true, floating:true, autoplay:true,
        matchesQuery:(video,query) => video.title.toLowerCase().includes(query.toLowerCase()),
        onPinchReturn:() => { queueProbe.pinches++; return true; },
        onQueueEnd:() => {
          queueProbe.calls++;
          return new Promise(resolve => {
            window.resolveQueuePage = () => {
              callbackQueue.push(...appendedQueue);
              queueProbe.resolved=true;
              resolve(appendedQueue.length);
            };
          });
        }
      });
    }""", clips)
    fixture.expect_playing_id(page, clips[1]["video_id"])
    page.evaluate("window.queueOriginalFrame = document.querySelector('#videoPlayerFullscreen iframe')")
    bounds = page.locator("#videoPlayerFullscreen .video-player-stage").bounding_box()
    assert bounds and bounds["width"] >= 200 and bounds["height"] >= 200, bounds
    return clips


def begin_pending(page, ended=False):
    page.evaluate("fixturePlayback.finishCurrent()" if ended else "mallVideoPlayer.next()")
    page.wait_for_function("queueProbe.calls === 1 && !!window.resolveQueuePage")
    assert page.evaluate("mallVideoPlayer.getCurrentIndex()") == 1
    # Repeated boundary taps cannot launch a competing continuation.
    page.evaluate("mallVideoPlayer.next()")
    assert page.evaluate("queueProbe.calls") == 1


def verify_case(browser, case):
    context = browser.new_context(viewport={"width":390,"height":844},
        is_mobile=True, has_touch=True, service_workers="block", reduced_motion="reduce")
    try:
        context.add_init_script(PROVIDER)
        context.route("**/*", fixture.route_local)
        page = context.new_page()
        page.set_default_timeout(5000)
        page.set_default_navigation_timeout(10000)
        clips = setup(page)
        if case == "query":
            # Use the ordinary visible theater search control. Its existing
            # event path calls the same shared filter controller.
            page.evaluate("mallVideoPlayer.setTheater(true)")
            expect(page.get_by_role("searchbox", name="Search videos", exact=True)).to_be_visible()
        begin_pending(page, ended=case == "ended_continues")
        if case == "native_pause":
            page.evaluate("queueFixtureNativePlayer.pauseVideo()")
            page.wait_for_function("mallVideoPlayer.getPlaybackSnapshot()?.state === 'paused'")
        elif case == "query":
            page.get_by_role("searchbox", name="Search videos", exact=True).fill("Fixture clip 1")
            expect(page.locator("#videoPlayerFullscreen .video-player-queue-item")).to_have_count(1)
        elif case == "hide_restore":
            # Explicitly synthetic background state, never a real OS/device gate.
            page.evaluate("Object.defineProperty(document,'hidden',{value:true,configurable:true});document.dispatchEvent(new Event('visibilitychange'))")
            page.wait_for_function("mallVideoPlayer.getPlaybackSnapshot()?.state === 'paused'")
        elif case == "tuck_restore":
            page.evaluate("mallVideoPlayer.tuck()")
            assert page.evaluate("mallVideoPlayer.isTucked()")
        elif case == "close_reopen":
            page.evaluate("mallVideoPlayer.close()")
            assert page.evaluate("mallVideoPlayer.isOpen()") is False
        elif case == "selection":
            page.evaluate("mallVideoPlayer.selectVideo(0)")
            fixture.expect_playing_id(page, clips[0]["video_id"])

        plays = page.evaluate("fixturePlayback.plays")
        page.evaluate("resolveQueuePage()")
        page.wait_for_function("queueProbe.resolved")
        settle(page)
        if case in {"explicit_continues", "ended_continues"}:
            fixture.expect_playing_id(page, clips[2]["video_id"])
            assert page.evaluate("mallVideoPlayer.getQueueLength()") == 4
            assert page.evaluate("fixturePlayback.plays") == plays + 1
            assert page.evaluate("queueOriginalFrame === document.querySelector('#videoPlayerFullscreen iframe')")
            assert page.evaluate("fixturePlayback.created === 1 && fixturePlayback.destroyed === 0")
        else:
            assert page.evaluate("fixturePlayback.plays") == plays, case
            expected_index = -1 if case == "close_reopen" else 0 if case == "selection" else 1
            assert page.evaluate("mallVideoPlayer.getCurrentIndex()") == expected_index, case
            if case == "hide_restore":
                page.evaluate("delete document.hidden;document.dispatchEvent(new Event('visibilitychange'))")
                settle(page)
                assert page.evaluate("fixturePlayback.plays") == plays
            elif case == "tuck_restore":
                page.evaluate("mallVideoPlayer.untuck()")
                settle(page)
                assert page.evaluate("fixturePlayback.plays") == plays
            elif case == "close_reopen":
                page.evaluate("mallVideoPlayer.open('hpc', callbackQueue,0,{scoped:true,floating:true,autoplay:false})")
                page.wait_for_function("mallVideoPlayer.getPlaybackSnapshot()?.state === 'manual-play'")
                settle(page)
                assert page.evaluate("fixturePlayback.plays") == plays
                assert page.evaluate("mallVideoPlayer.getCurrentIndex()") == 0
        assert page.evaluate("queueProbe.calls") == 1
        return {"case":case,"passed":True,"controlled_provider_only":True}
    finally:
        context.close()


def verify_gesture_boundaries(browser):
    context = browser.new_context(viewport={"width":390,"height":844},
        is_mobile=True, has_touch=True, service_workers="block", reduced_motion="reduce")
    try:
        context.add_init_script(PROVIDER)
        context.route("**/*", fixture.route_local)
        page = context.new_page()
        page.set_default_timeout(5000)
        page.set_default_navigation_timeout(10000)
        setup(page)
        page.evaluate("""() => {
          window.probePinch = selector => {
            const target=document.querySelector(selector);
            if(!target) throw new Error('Missing gesture target: '+selector);
            const touch=(name,distance) => {
              const event=new Event(name,{bubbles:true,cancelable:true});
              Object.defineProperty(event,'touches',{value:name==='touchend'?[]:
                [{clientX:20,clientY:40},{clientX:20+distance,clientY:40}]});
              target.dispatchEvent(event);
              return event.defaultPrevented;
            };
            const flags=[touch('touchstart',220),touch('touchmove',90),touch('touchmove',50)];
            const fallback=new Event('gesturechange',{bubbles:true,cancelable:true});
            Object.defineProperty(fallback,'scale',{value:.2});
            target.dispatchEvent(fallback);
            flags.push(fallback.defaultPrevented);
            touch('touchend',0);
            target.dispatchEvent(new Event('gestureend',{bubbles:true}));
            return flags;
          };
          window.probeWheel=selector => {
            const event=new WheelEvent('wheel',{bubbles:true,cancelable:true,ctrlKey:true,deltaY:120});
            document.querySelector(selector).dispatchEvent(event);
            return event.defaultPrevented;
          };
          const video=document.createElement('video');
          video.id='nativeVideoGestureFixture';
          video.hidden=true; // Event-routing target only; no HTML5 playback claim.
          document.querySelector('.video-player-stage').append(video);
        }""")
        plays = page.evaluate("fixturePlayback.plays")
        for selector in (".video-player-stage", "#videoPlayerFullscreen iframe",
                         "#nativeVideoGestureFixture", "#videoPlayerFullscreen [data-action='back']",
                         "#videoPlayerFullscreen .video-player-source"):
            flags = page.evaluate("selector => probePinch(selector)", selector)
            assert flags == [False,False,False,False], (selector,flags)
            assert page.evaluate("selector => probeWheel(selector)",selector) is False, selector
            assert page.evaluate("queueProbe.pinches") == 0, selector
            assert page.evaluate("mallVideoPlayer.isOpen() && mallVideoPlayer.isFloating()"),selector
            page.wait_for_timeout(100)
        assert page.evaluate("probeWheel('body')") is False
        assert page.evaluate("probeWheel('.video-player-queue-rail')") is False
        flags = page.evaluate("probePinch('.video-player-gesture-grip')")
        assert flags[1:3] == [True,True], flags
        assert page.evaluate("queueProbe.pinches") == 1
        assert page.evaluate("mallVideoPlayer.isOpen() && mallVideoPlayer.isFloating()")
        assert page.evaluate("fixturePlayback.plays") == plays
        page.wait_for_timeout(100)
        page.evaluate("queueProbe.pinches=0")
        assert page.evaluate("probeWheel('.video-player-title')") is True
        assert page.evaluate("queueProbe.pinches") == 1
        assert page.evaluate("mallVideoPlayer.isOpen() && mallVideoPlayer.isFloating()")
        return {"case":"gesture_provider_and_browser_boundaries","passed":True,
                "synthetic_events_only":True,"chrome_callback_once_per_gesture":True}
    finally:
        context.close()


def main():
    if Path.cwd().resolve() != REPO:
        raise SystemExit("Run this runner from the repository root.")
    names = sys.argv[1:] or ["chromium", "webkit"]
    if any(name not in {"chromium", "webkit"} for name in names):
        raise SystemExit("Optional arguments are chromium and/or webkit.")
    before = source_hashes()
    cases = ("explicit_continues", "ended_continues", "native_pause", "query",
             "hide_restore", "tuck_restore", "close_reopen", "selection")
    with sync_playwright() as runtime:
        for name in names:
            browser = getattr(runtime,name).launch(timeout=15000)
            try:
                for case in cases:
                    print(json.dumps({"engine":name, **verify_case(browser,case)}), flush=True)
                print(json.dumps({"engine":name, **verify_gesture_boundaries(browser)}), flush=True)
            finally:
                browser.close()
    assert source_hashes() == before, "Bound runtime source changed during this run."
    print(json.dumps({"source_sha256":before,"real_youtube":"unexecuted",
                      "physical_iphone":"unexecuted","network_page_contract":"unexecuted"}), flush=True)


if __name__ == "__main__":
    main()
