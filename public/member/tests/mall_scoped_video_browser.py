"""Offline browser regression for the shared Mall's scoped video field.

From the repo root, with Python Playwright and Chromium installed:
    python -B public/member/tests/mall_scoped_video_browser.py

The shell and CSS are real. All network routes and provider events are
fixtures. Real YouTube and physical iOS playback are separate gates.
"""
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlsplit
import json
import mimetypes
import re
from playwright.sync_api import expect, sync_playwright

public = Path("public").resolve()
catalog = json.loads((public / "member/mall-public-video-catalog.json").read_text(encoding="utf-8"))
lane = catalog["hpc"]["lane"]
prototype = deepcopy(lane["videos"][0])
fixture_total = 31
videos = []
for i in range(fixture_total):
    video = deepcopy(prototype)
    identifier = f"HPC{i:08d}"
    suffix = " theater topic" if i in (2, 20) else " theater selection" if i == 24 else ""
    video.update(video_id=identifier, id=identifier, title=f"Fixture clip {i}{suffix}",
                 embed_url=f"https://www.youtube.com/embed/{identifier}",
                 source_url=f"https://www.youtube.com/shorts/{identifier}",
                 thumbnail_url="/logo-dog.png", poster_url="/logo-dog.png")
    videos.append(video)
lane.update(videos=videos, video_count=len(videos))

provider = """(() => {
  if (window.top !== window) return;
  const trace = window.fixturePlayback = {
    created: 0, destroyed: 0, pause: 0, plays: 0, events: [],
    error: null, errorsByVideo: {}, loadedIds: [], block: false, hang: false, mutes: 0
  };
  window.addEventListener('mallVideoPlayback', e => trace.events.push(e.detail));
  window.YT = {
    PlayerState: {UNSTARTED:-1,ENDED:0,PLAYING:1,PAUSED:2,BUFFERING:3,CUED:5},
    Player: function(target, options = {}) {
      let frame = typeof target === 'string' ? document.getElementById(target) : target;
      trace.created++;
      if (frame.tagName !== 'IFRAME') {
        const iframe = document.createElement('iframe');
        const args = options.playerVars || {};
        iframe.src = 'https://www.youtube.com/embed/' + (options.videoId || 'HPC00000000') + '?' + new URLSearchParams(args);
        frame.replaceWith(iframe);
        frame = iframe;
      }
      let currentVid = options.videoId || (new URL(frame.src).pathname.split('/').pop() || 'HPC00000000');
      const checkError = (vid) => (trace.errorsByVideo && vid in trace.errorsByVideo) ? trace.errorsByVideo[vid] : trace.error;
      const events = options.events || {}, api = this, emit = (fn, data) => events[fn]?.({target:api, data});
      let state = -1, dead = false, startedAt = null, elapsed = 0, muted = false;
      this.getIframe = () => frame;
      this.getPlayerState = () => state;
      this.getDuration = () => 180;
      this.getCurrentTime = () => elapsed + (startedAt === null ? 0 : (performance.now() - startedAt)/1000);
      this.seekTo = time => { elapsed = time; };
      this.playVideo = () => {
        if (trace.block) { emit('onAutoplayBlocked'); return; }
        trace.plays++;
        if (startedAt === null) startedAt = performance.now();
        state = 1;
        emit('onStateChange', state);
      };
      this.loadVideoById = vid => {
        currentVid = vid;
        trace.loadedIds.push(vid);
        frame.dataset.loadedVideoId = vid;
        elapsed = 0;
        startedAt = null;
        state = -1;
        setTimeout(() => {
          if (dead || trace.hang) return;
          const err = checkError(vid);
          if (err !== null && err !== undefined) emit('onError', err);
          else this.playVideo();
        }, 25);
      };
      this.cueVideoById = vid => {
        currentVid = vid;
        trace.loadedIds.push(vid);
        frame.dataset.loadedVideoId = vid;
        elapsed = 0;
        startedAt = null;
        state = 5;
        setTimeout(() => {
          if (dead || trace.hang) return;
          const err = checkError(vid);
          if (err !== null && err !== undefined) emit('onError', err);
          else emit('onStateChange', 5);
        }, 25);
      };
      this.pauseVideo = () => {
        trace.pause++;
        elapsed = this.getCurrentTime();
        startedAt = null;
        state = 2;
        emit('onStateChange', state);
      };
      this.destroy = () => { dead = true; trace.destroyed++; frame.remove(); };
      this.mute = () => { muted = true; trace.mutes++; };
      this.unMute = () => { muted = false; };
      this.isMuted = () => muted;
      trace.finishCurrent = () => {
        elapsed = this.getCurrentTime();
        startedAt = null;
        state = 0;
        emit('onStateChange', state);
      };
      setTimeout(() => {
        if (dead || trace.hang) return;
        const err = checkError(currentVid);
        if (err !== null && err !== undefined) emit('onError', err);
        else {
          emit('onReady');
          const requested = new URL(frame.src).searchParams.get('autoplay') === '1' || options.playerVars?.autoplay === 1;
          if (requested && state !== 1) this.playVideo();
        }
      }, 50);
    }
  };
})();"""

def route_local(route):
    u = urlsplit(route.request.url)
    if u.hostname in {"hpc.foundups.com", "foundups.com", "play.foundups.com"}:
        if u.path == "/member/mall-public-video-catalog.json":
            route.fulfill(status=200, json=catalog)
            return
        relative = u.path.lstrip("/")
        if relative.startswith("f/") and "." not in relative:
            relative = "f/index.html"
        if not relative or relative.endswith("/"):
            relative += "index.html"
        filename = (public / relative).resolve()
        if filename.is_relative_to(public) and filename.is_file():
            mime = mimetypes.guess_type(filename.name)[0] or "application/octet-stream"
            if filename.suffix in {".js", ".mjs"}:
                mime = "text/javascript"
            route.fulfill(status=200, content_type=mime, body=filename.read_bytes(), headers={"Referrer-Policy":"strict-origin-when-cross-origin"})
            return
        route.fulfill(status=404, content_type="text/plain", body="Missing fixture asset")
    elif u.hostname in {"www.youtube.com", "www.youtube-nocookie.com"} and u.path.startswith("/embed/"):
        route.fulfill(status=200, content_type="text/html", body="<button>Provider fixture</button>")
    elif u.hostname == "vote.mtrout.com" and u.path == "/contact":
        route.fulfill(status=200, content_type="text/html", body="<h1>Contact Congress fixture</h1>")
    else:
        route.abort()

def info(page):
    return page.evaluate("""() => ({
      scroll:document.querySelector('.mall-tile-field-wrapper').scrollTop,
      width:document.querySelector('.mall-tile-field-wrapper').clientWidth,
      contentWidth:document.querySelector('.mall-tile-field-wrapper').scrollWidth,
      tiles:[...document.querySelectorAll('.mall-tile')].map(t=>({id:t.dataset.videoId,x:t.offsetLeft,y:t.offsetTop,w:t.offsetWidth,h:t.offsetHeight})),
      player:window.mallVideoPlayer?.getPlaybackSnapshot?.(),
      stage:(()=>{const r=document.querySelector('.video-player-stage')?.getBoundingClientRect();return r&&{w:r.width,h:r.height}})()
    })""")

def video(page, index):
    return page.locator(f'.mall-tile[data-video-id="{videos[index]["video_id"]}"]')

def expect_position(page, offset):
    page.wait_for_function("(expected) => Math.abs(document.querySelector('.mall-tile-field-wrapper').scrollTop - expected) <= 2", arg=offset, timeout=4000)

def main():
    observed = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width":390,"height":844}, is_mobile=True, has_touch=True, service_workers="block", reduced_motion="reduce")
        context.add_init_script(provider)
        context.route("**/*", route_local)
        page = context.new_page()
        page.set_default_timeout(8000)
        page.goto("https://hpc.foundups.com/member/", wait_until="domcontentloaded")
        expect(page.locator("#videoScopeTitle")).to_have_text("Hasan Piker Coalition")
        expect(page.locator("#videoScopeHeader #videoScopeTopic")).to_have_text("#SchumerOUT")
        build = page.locator("#videoScopeHeader .mall-build-label")
        expect(build).to_have_text("Build v22")
        expect(build).to_be_visible()
        expect(page.locator("#videoScopeHeader #videoScopeVoice")).to_have_attribute("href", "https://vote.mtrout.com/contact")
        expect(page.locator("#videoScopeInfo")).to_be_hidden()
        expect(page).to_have_title("Hasan Piker Coalition")
        expect(page.locator('meta[name="apple-mobile-web-app-title"]')).to_have_attribute("content", "Hasan Piker Coalition")
        expect(page.locator('link[rel="apple-touch-icon"]')).to_have_attribute("href", "/member/hpc-icon-180.png")
        session = context.new_cdp_session(page)
        manifest = session.send("Page.getAppManifest")
        assert manifest["url"].endswith("/member/hpc.webmanifest") and not manifest["errors"], manifest
        data = json.loads(manifest["data"])
        assert (data["name"], data["short_name"], data["display"]) == ("Hasan Piker Coalition", "HPC", "standalone")
        assert data["id"] == data["start_url"] == "/member/?foundup=hpc"
        mall_link = page.get_by_role("link", name="Return to Play FoundUps Mall")
        expect(mall_link).to_have_attribute("href", "https://play.foundups.com/")
        expect(mall_link.locator("img")).to_have_attribute("src", "/member/hpc-icon-192.png")
        logo = mall_link.bounding_box()
        title = page.locator("#videoScopeTitle").bounding_box()
        assert logo["x"] < title["x"] and title["y"] < logo["y"] + logo["height"]
        expect(page.locator(".mall-tile-play-indicator")).to_have_count(0)
        layout = info(page)
        assert 6 <= len(layout["tiles"]) < fixture_total
        first = layout["tiles"][:6]
        assert len({t["x"] for t in first}) == 3 and len({t["y"] for t in first}) == 2, first
        assert max(t["w"] for t in first) - min(t["w"] for t in first) <= 1
        assert abs(layout["width"] - layout["contentWidth"]) <= 1
        observed["initial_tiles"] = len(layout["tiles"])

        first_header = page.locator("#videoScopeHeader").bounding_box()
        dock = page.locator("#videoScopePhoneDock")
        expect(dock).to_be_visible()
        first_nav = dock.bounding_box()
        assert first_nav["y"] + first_nav["height"] <= 844
        wrapper = page.locator(".mall-tile-field-wrapper")
        for _ in range(10):
            wrapper.evaluate("(el) => el.scrollTop = el.scrollHeight")
            if page.locator(".mall-tile").count() == fixture_total:
                break
            page.wait_for_timeout(200)
        expect(page.locator(".mall-tile")).to_have_count(fixture_total)
        assert len({t["id"] for t in info(page)["tiles"]}) == fixture_total
        assert abs(first_header["y"] - page.locator("#videoScopeHeader").bounding_box()["y"]) <= 1
        assert abs(first_nav["y"] - dock.bounding_box()["y"]) <= 1
        observed["unique_scrolled_tiles"] = fixture_total

        wrapper.evaluate("(el) => el.scrollTop = 0")
        selected = video(page, 2)
        original_row = selected.evaluate("tile => tile.offsetTop")
        selected.tap(position={"x":25,"y":90})
        player = page.locator("#videoPlayerFullscreen")
        expect(player).to_have_attribute("aria-label","Floating video player")
        expect(selected).to_be_visible()
        expect(selected).to_have_attribute("aria-current", "true")
        expect(page.locator(".mall-inline-player-slot")).to_have_count(0)
        floating_top_y = player.bounding_box()["y"]
        assert floating_top_y < 120
        expect(player.locator("iframe")).to_have_count(1)
        page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot().state === 'playing'")
        state = info(page)
        assert state["stage"]["w"] >= 200 and state["stage"]["h"] >= 200, state["stage"]
        assert state["player"]["videoId"] == videos[2]["video_id"]
        page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot().positionSeconds > 0.15")
        page.evaluate("window.originalFixtureIframe = document.querySelector('#videoPlayerFullscreen iframe')")
        frame_clear = page.evaluate("""() => {
          const f=document.querySelector('#videoPlayerFullscreen iframe'), r=f.getBoundingClientRect();
          return [0.15,0.5,0.85].every(x => [0.15,0.5,0.85].every(y => document.elementFromPoint(r.left + x*r.width,r.top+y*r.height) === f));
        }""")
        assert frame_clear, "Floating player controls are covered"
        observed["floating"] = {**state["stage"], "nine_unobstructed_points": frame_clear}
        player.get_by_role("button", name="Open WikiTube", exact=True).tap()
        expect(player).to_have_attribute("aria-label", "WikiTube video player")
        assert page.evaluate("window.originalFixtureIframe === document.querySelector('#videoPlayerFullscreen iframe')")
        assert page.evaluate("window.fixturePlayback.created") == 1
        immersive_query = player.get_by_role("textbox", name="Search this queue")
        immersive_query.fill("theater topic")
        immersive_query.press("Enter")
        expect_playing(page, 2)
        expect(player.locator(".video-player-queue-item")).to_have_count(2)
        assert page.evaluate("window.originalFixtureIframe === document.querySelector('#videoPlayerFullscreen iframe')")
        player.get_by_role("button", name="Search options").tap()
        expect(player.get_by_role("dialog", name="Search options")).to_be_visible()
        expect(player.get_by_role("link", name="AutoPost camera and photos")).to_have_count(0)
        page.keyboard.press("Escape")
        expect(player.get_by_role("dialog", name="Search options")).to_be_hidden()
        expect(player).to_be_visible()
        assert page.evaluate("history.state.pfmallScopedPlayer") == "hpc"
        page.evaluate("history.back()")
        page.wait_for_function("!history.state?.pfmallScopedPlayer")
        expect(player).to_be_hidden()
        expect(selected).to_be_visible()
        assert abs(selected.evaluate("tile => tile.offsetTop") - original_row) <= 1
        expect(selected).to_be_focused()
        expect_position(page, 0)
        expect(player.locator("iframe")).to_have_count(0)
        observed["top_anchored_floating_and_same_iframe_wikitube"] = True

        middle = video(page, 1)
        middle.tap(position={"x":25,"y":90})
        page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot().state === 'playing'")
        expect(middle).to_be_visible()
        expect(middle).to_have_attribute("aria-current", "true")
        floating_box_before = player.bounding_box()
        assert floating_box_before["y"] < 120
        # Scroll so tile 0 is below the floating player card, then tap tile 0 to switch
        video(page, 6).tap(position={"x":25,"y":90})
        expect_playing(page, 6)
        expect(middle).not_to_have_attribute("aria-current", "true")
        expect(video(page, 6)).to_have_attribute("aria-current", "true")
        expect(player.locator("iframe")).to_have_count(1)
        trace = page.evaluate("window.fixturePlayback")
        assert trace["created"] == 2 and trace["destroyed"] == 1 and videos[6]["video_id"] in trace["loadedIds"], trace
        pos_before_scroll = page.evaluate("window.mallVideoPlayer.getPlaybackSnapshot().positionSeconds")
        wrapper.evaluate("(el) => el.scrollTop = el.scrollHeight")
        page.wait_for_function("prev => window.mallVideoPlayer.getPlaybackSnapshot().positionSeconds > prev + 0.08", arg=pos_before_scroll)
        assert abs(player.bounding_box()["y"] - floating_box_before["y"]) <= 1
        expect(player.locator("iframe")).to_have_count(1)
        page.keyboard.press("Escape")
        page.wait_for_function("!history.state?.pfmallScopedPlayer")
        observed["one_provider_reused_on_switch_and_stationary_scroll"] = True

        wrapper.evaluate("(el) => el.scrollTop = Math.min(860, el.scrollHeight)")
        saved_offset = info(page)["scroll"]
        saved_anchor = page.evaluate("mallTileField.getVideoGridState().anchorVideoId")
        assert saved_offset > 0
        with page.expect_navigation(wait_until="domcontentloaded"):
            page.locator("#videoScopeVoice").tap()
        expect(page.get_by_role("heading", name="Contact Congress fixture")).to_be_visible()
        page.go_back(wait_until="domcontentloaded")
        expect(page.locator("#videoScopeTitle")).to_have_text("Hasan Piker Coalition")
        expect_position(page, saved_offset)
        assert page.evaluate("mallTileField.getVideoGridState().anchorVideoId") == saved_anchor
        observed["voice_return_position"] = {"offset":saved_offset,"anchor":saved_anchor}

        page.set_viewport_size({"width": 844, "height":390})
        page.wait_for_timeout(300)
        assert page.evaluate("mallTileField.getVideoGridState().anchorVideoId") == saved_anchor
        oriented = info(page)
        assert abs(oriented["width"] - oriented["contentWidth"]) <= 1
        assert page.locator("#videoScopeHeader").bounding_box()["y"] >= 0
        assert page.locator("#videoScopeVoice").bounding_box()["y"] < 390
        video(page, 4).tap(position={"x":25,"y":90})
        expect_playing(page, 4)
        expect(video(page, 4)).to_have_attribute("aria-current", "true")
        landscape_stage = player.locator(".video-player-stage").bounding_box()
        assert landscape_stage["width"] >= 200 and 200 <= landscape_stage["height"] <= 260
        player.get_by_role("button", name="Close player").tap()
        page.wait_for_function("!history.state?.pfmallScopedPlayer")
        expect(video(page, 4)).to_be_visible()
        observed["landscape_playback_without_horizontal_overflow"] = True

        page.set_viewport_size({"width":320, "height":640})
        voice = page.locator("#videoScopeVoice").bounding_box()
        assert voice["x"] + voice["width"] <= 320
        assert build.bounding_box()["x"] + build.bounding_box()["width"] <= voice["x"]
        more = dock.get_by_role("button", name="More options")
        search = dock.get_by_role("textbox", name="Search videos")
        red_dog = dock.get_by_role("link", name="Red Dog")
        assert more.bounding_box()["x"] < search.bounding_box()["x"] < red_dog.bounding_box()["x"]
        page.evaluate("window.SpeechRecognition = window.webkitSpeechRecognition = undefined")
        dock.get_by_role("button", name="Dictate search").tap()
        expect(search).to_be_focused()
        expect(dock.get_by_role("status")).to_have_text("Use the microphone on your keyboard to dictate.")
        page.evaluate("""() => { window.SpeechRecognition = class {
          static available(options) { return options.processLocally ? 'available' : 'unavailable'; }
          get processLocally() { return this.local; }
          set processLocally(value) { this.local = value; }
          start() {
            if (this.local) this.onresult({results:[[{transcript:'theater topic'}]]});
            this.onend();
          }
          abort() {}
        }; }""")
        dock.get_by_role("button", name="Dictate search").tap()
        expect(search).to_have_value("theater topic")
        assert page.locator(".mall-tile").count() > 2, "Dictation must not submit"
        search.press("Enter")
        expect(page.locator(".mall-tile")).to_have_count(2)
        expect(video(page, 20)).to_be_visible()
        assert page.evaluate("document.querySelector('.mall-tile[data-index=\"20\"]').dataset.videoId") == videos[20]["video_id"]
        with page.expect_navigation(wait_until="domcontentloaded"):
            red_dog.tap()
        assert page.url.endswith("/f/hpc#red-dog")
        page.wait_for_function("window.entryRedDog?.isOpen() && window.entryRedDog.getContext().foundupId === 'hpc'")
        page.go_back(wait_until="domcontentloaded")
        expect(search).to_have_value("theater topic")
        expect(page.locator(".mall-tile")).to_have_count(2)
        search.fill("no matching clip")
        search.press("Enter")
        expect(page.locator(".mall-video-grid-empty")).to_have_text("No videos match your search.")
        more.tap()
        menu = page.get_by_role("dialog", name="More options")
        expect(menu.get_by_text("Build v22", exact=True)).to_be_visible()
        assert menu.bounding_box()["x"] <= more.bounding_box()["x"] + 1
        assert menu.bounding_box()["y"] + menu.bounding_box()["height"] < dock.bounding_box()["y"]
        expect(menu.get_by_role("combobox", name="Browser AI")).to_be_disabled()
        page.touchscreen.tap(20, 120)
        expect(menu).to_be_hidden()
        more.tap()
        menu.get_by_role("button", name="About this FoundUp").tap()
        disclosure = page.get_by_role("dialog", name="About this FoundUp")
        expect(disclosure).to_contain_text("independent satirical FoundUp")
        disclosure.get_by_role("button", name="Close").tap()
        more.tap()
        menu.get_by_role("button", name="Home").tap()
        expect(search).to_have_value("")
        expect(video(page, 0)).to_be_visible()
        observed["install_manifest_phone_search_dictation_and_dock"] = True
        browser.close()
    print(json.dumps(observed, sort_keys=True))


def verify_diagnostics():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width":430,"height":844}, is_mobile=True, has_touch=True, service_workers="block")
        context.add_init_script(provider)
        context.route("**/*", route_local)
        page = context.new_page()
        page.set_default_timeout(7000)
        page.goto("https://hpc.foundups.com/member/", wait_until="domcontentloaded")
        expect(page.locator("#videoScopeTitle")).to_have_text("Hasan Piker Coalition")
        player = page.locator("#videoPlayerFullscreen")
        observed = {}
        diagnostics = [(2,"configuration"), (5,"playback-error"), (100,"unavailable"), (101,"embedding-disabled"),
                       (150,"embedding-disabled"), (153,"client-identification"), (999,"provider-unknown")]
        for code,state in diagnostics:
            page.evaluate("(error) => window.fixturePlayback.error = error", code)
            video(page, 0).tap(position={"x":25,"y":90})
            page.wait_for_function("(expected) => window.mallVideoPlayer.getPlaybackSnapshot()?.state === expected", arg=state)
            snapshot = page.evaluate("window.mallVideoPlayer.getPlaybackSnapshot()")
            assert snapshot["code"] == code
            if code in (101, 150):
                expect(page.get_by_text("YouTube refused to play this embedded video.", exact=False)).to_be_visible()
            expect(player.locator(".video-player-status")).to_be_visible()
            expect(player.locator(".video-player-source")).to_have_attribute("href", videos[0]["source_url"])
            expect(player.locator("iframe")).to_have_count(1)
            assert page.url == "https://hpc.foundups.com/member/"
            page.keyboard.press("Escape")
            expect(player.locator("iframe")).to_have_count(0)
            observed[str(code)] = state

        page.evaluate("window.fixturePlayback.error = null; window.fixturePlayback.block = true")
        video(page, 0).tap(position={"x":25,"y":90})
        page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state === 'autoplay-blocked'")
        expect(player.locator("iframe")).to_have_count(1)
        page.keyboard.press("Escape")
        observed["autoplay_blocked"] = True

        page.evaluate("window.fixturePlayback.block = false; window.fixturePlayback.hang = true")
        video(page, 0).tap(position={"x":25,"y":90})
        page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state === 'timeout'", timeout=15000)
        expect(player.locator("iframe")).to_have_count(1)
        page.keyboard.press("Escape")
        observed["timeout_retains_provider_manual_controls"] = True

        page.evaluate("window.fixturePlayback.hang = false")
        video(page, 0).tap(position={"x":25,"y":90})
        page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state === 'playing'")
        page.evaluate("Object.defineProperty(document, 'hidden', {value:true, configurable:true}); document.dispatchEvent(new Event('visibilitychange'));")
        page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state === 'paused'")
        expect(player.locator("iframe")).to_have_count(1)
        page.evaluate("delete document.hidden")
        page.keyboard.press("Escape")
        observed["background_pause"] = True

        page.set_viewport_size({"width":320, "height":844})
        video(page, 0).tap(position={"x":25,"y":90})
        page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state === 'manual-play'")
        assert info(page)["stage"]["w"] >= 200 and info(page)["stage"]["h"] >= 200
        player.get_by_role("button", name="Play video", exact=True).tap()
        page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.positionSeconds > 0.1")
        expect(player.get_by_role("button", name="Close player", exact=True)).to_be_focused()
        page.keyboard.press("Escape")
        expect(player.locator("iframe")).to_have_count(0)
        observed["small_thumbnail_requires_manual_play"] = True
        browser.close()
        print(json.dumps(observed, sort_keys=True))

def expect_playing(page, index):
    expect_playing_id(page, videos[index]["video_id"])


def expect_playing_id(page, video_id):
    page.wait_for_function("""id => {
        const snapshot = window.mallVideoPlayer.getPlaybackSnapshot();
        return snapshot?.videoId === id && snapshot.state === 'playing' && snapshot.positionSeconds > 0.1;
    }""", arg=video_id)


def verify_member_poster_grid(page):
    ordinary = json.loads((public / "member/mall-video-catalog.json").read_text(encoding="utf-8"))
    clips = next(item["videos"] for item in ordinary if item["foundup_id"] == "move2japan")
    page.goto("https://foundups.com/member/", wait_until="domcontentloaded")
    field = page.locator("#mallTileField")
    expect(field).to_have_attribute("data-layout", "grid")
    tiles = field.locator(".mall-tile")
    expect(tiles).to_have_count(len(ordinary))
    columns = tiles.evaluate_all("tiles => new Set(tiles.map(tile => tile.offsetLeft)).size")
    assert columns == 8
    row_gap = tiles.evaluate_all("(tiles, columns) => tiles[columns].offsetTop - tiles[0].offsetTop - tiles[0].offsetHeight", columns)
    assert 0 <= row_gap <= 8

    lane_tile = field.locator('.mall-tile[data-foundup-id="move2japan"]')
    assert lane_tile.evaluate("tile => getComputedStyle(tile).backgroundSize") == "contain"
    assert lane_tile.evaluate("tile => getComputedStyle(tile).backgroundPosition") == "50% 50%"
    lane_tile.hover()
    expect(field.locator("iframe, video")).to_have_count(0)
    expect(lane_tile.locator(".mall-tile-audio")).to_have_count(0)
    expect(lane_tile.get_by_role("button", name="Open fullscreen")).to_be_visible()
    mall_search = page.get_by_role("textbox", name="Search the Mall")
    expect(mall_search).to_be_visible()
    mall_search.fill("AutoPost")
    mall_search.press("Enter")
    expect(tiles).to_have_count(1)
    mall_search.fill("")
    expect(tiles).to_have_count(len(ordinary))

    lane_tile.click()
    inline = page.get_by_role("region", name="Floating video player")
    expect(inline).to_be_visible()
    expect(lane_tile).to_be_visible()
    expect(lane_tile).to_have_attribute("aria-current", "true")
    expect_playing_id(page, clips[0]["video_id"])
    inline_frame = inline.locator("iframe")
    inline_box = inline_frame.bounding_box()
    assert inline_box and min(inline_box["width"], inline_box["height"]) >= 200
    inline_frame.evaluate("el => { window.originalPlayerFrame = el; }")
    inline.get_by_role("button", name="Open WikiTube").click()
    player = page.get_by_role("dialog", name="WikiTube video player")
    expect(player).to_have_attribute("aria-modal", "true")
    expect(player.get_by_role("button", name="Enter FoundUp")).to_be_visible()
    expect_playing_id(page, clips[0]["video_id"])
    frame = player.locator("iframe")
    expect(frame).to_have_count(1)
    assert frame.evaluate("el => el === window.originalPlayerFrame")
    assert "controls=1" in frame.get_attribute("src")
    box = frame.bounding_box()
    assert box and min(box["width"], box["height"]) >= 200
    query = player.get_by_role("textbox", name="Search this queue")
    query_box = query.bounding_box()
    rail_box = player.locator(".video-player-queue-rail").bounding_box()
    assert query_box and rail_box and box["y"] + box["height"] <= query_box["y"] < rail_box["y"]
    assert query_box["x"] < box["width"] / 4
    query.fill("vulnpocalypse")
    query.press("Enter")
    expect_playing_id(page, clips[0]["video_id"])
    assert frame.evaluate("el => el === window.originalPlayerFrame")
    matches = player.locator(".video-player-queue-item")
    expect(matches.first).to_be_visible()
    assert matches.count() < len(clips)
    query.fill("no-such-queue-match-298")
    expect(player.get_by_text("No videos match your search.")).to_be_visible()
    query.fill("")
    expect(matches).to_have_count(len(clips))
    page.evaluate("window.SpeechRecognition = window.webkitSpeechRecognition = undefined")
    player.get_by_role("button", name="Dictate search").click()
    expect(player.get_by_text("Use the microphone on your keyboard to dictate.")).to_be_visible()
    player.get_by_role("button", name="Search options").click()
    options = player.get_by_role("dialog", name="Search options")
    expect(options.get_by_role("combobox", name="Browser AI")).to_be_disabled()
    expect(options.get_by_text("Build v22", exact=True)).to_be_visible()
    page.keyboard.press("Escape")
    expect(options).not_to_be_visible()
    expect(player).to_be_visible()
    player.get_by_role("button", name="Search options").click()
    with page.expect_popup() as opened:
        options.get_by_role("link", name="AutoPost camera and photos").click()
    capture = opened.value
    capture.wait_for_url("https://foundup-japan-ai-autopost-camera-56566376153.us-west1.run.app/")
    expect(capture.get_by_role("heading", name="AutoPost fixture")).to_be_visible()
    capture.close()
    expect(options).not_to_be_visible()
    assert frame.evaluate("el => el === window.originalPlayerFrame")
    if page.evaluate("mallVideoPlayer.getPlaybackSnapshot()?.state === 'paused'"):
        player.get_by_role("button", name="Play video", exact=True).click()
        expect_playing_id(page, clips[0]["video_id"])
    page.set_viewport_size({"width": 1010, "height": 768})
    assert frame.evaluate("el => el === window.originalPlayerFrame")
    page.set_viewport_size({"width": 1440, "height": 900})
    page.evaluate("fixturePlayback.finishCurrent()")
    expect_playing_id(page, clips[1]["video_id"])
    queued = player.locator(".video-player-queue-item").nth(2)
    thumbnail = queued.locator("img").bounding_box()
    assert thumbnail and thumbnail["width"] >= 120 and thumbnail["height"] >= 70
    queued.click()
    expect_playing_id(page, clips[2]["video_id"])
    expect(page.locator("iframe")).to_have_count(1)
    page.keyboard.press("Escape")
    expect(player).not_to_be_visible()
    expect(lane_tile).to_be_focused()
    expect(page.locator("iframe")).to_have_count(0)

    app = field.locator('.mall-tile[data-foundup-id="autopost"]')
    app.press("Enter")
    expect(page.locator("#foundupViewPlane")).to_have_class("foundup-view-plane open")
    expect(page.locator("#foundupViewBody")).to_contain_text("AutoPost")
    page.locator("#foundupViewClose").click()
    expect(app).to_be_focused()

    browse_offset = page.locator(".mall-tile-field-wrapper").evaluate("el => el.scrollTop")
    lane_tile.dispatch_event("wheel", {"ctrlKey": True, "deltaY": -100})
    clip_tile = field.locator('.mall-tile[data-foundup-id="move2japan_video_48"]')
    expect(clip_tile).to_be_attached()
    # Finish focus scrolling to the tile's snap point before activating it.
    clip_tile.evaluate("tile => { tile.focus(); tile.scrollIntoView({block: 'start'}); }")
    page.wait_for_function("""tile => {
        const wrapper = tile.closest('.mall-tile-field-wrapper');
        return Math.abs(tile.getBoundingClientRect().top - wrapper.getBoundingClientRect().top) <= 3;
    }""", arg=clip_tile.element_handle(), timeout=4000)
    offset = page.locator(".mall-tile-field-wrapper").evaluate("el => el.scrollTop")
    assert offset > 0
    page.keyboard.press("Enter")
    expect_playing_id(page, clips[48]["video_id"])
    page.keyboard.press("Escape")
    expect(player).not_to_be_visible()
    expect(clip_tile).to_be_focused()
    expect_position(page, offset)
    assert page.evaluate("mallTileField.isExpanded()")

    page.keyboard.press("Enter")
    expect_playing_id(page, clips[48]["video_id"])
    inline.locator("iframe").evaluate("el => { window.originalPlayerFrame = el; }")
    page.set_viewport_size({"width": 680, "height": 600})
    assert inline.locator("iframe").evaluate("el => el === window.originalPlayerFrame")
    page.keyboard.press("Escape")
    expect(clip_tile).to_be_focused()
    page.wait_for_function("""tile => {
        const tileBounds = tile.getBoundingClientRect();
        const fieldBounds = tile.closest('.mall-tile-field-wrapper').getBoundingClientRect();
        return tileBounds.bottom > fieldBounds.top && tileBounds.top < fieldBounds.bottom;
    }""", arg=clip_tile.element_handle(), timeout=4000)
    assert page.evaluate("mallTileField.isExpanded()")
    page.set_viewport_size({"width": 1440, "height": 900})
    clip_tile.dispatch_event("wheel", {"ctrlKey": True, "deltaY": 100})
    expect(lane_tile).to_be_visible()
    expect_position(page, browse_offset)

    page.evaluate("mallTileField.setDensity('15x4')")
    lane_tile.get_by_role("button", name="Open fullscreen").press("Enter")
    page.wait_for_function("mallVideoPlayer.getPlaybackSnapshot()?.state === 'manual-play'")
    query.fill("vulnpocalypse")
    query.press("Enter")
    expect_playing_id(page, clips[1]["video_id"])
    query.fill("")
    page.evaluate("fixturePlayback.finishCurrent()")
    expect_playing_id(page, clips[2]["video_id"])
    player.get_by_role("button", name="Back").click()

    page.evaluate("mallTileField.setLayoutMode('rows'); mallStateRestore.save()")
    page.reload(wait_until="domcontentloaded")
    expect(field).to_have_attribute("data-layout", "rows")
    lane_tile.click()
    expect_playing_id(page, clips[0]["video_id"])
    row_box = inline.locator("iframe").bounding_box()
    assert row_box and min(row_box["width"], row_box["height"]) >= 200
    inline.get_by_role("button", name="Open WikiTube").click()
    player.get_by_role("button", name="Open Red Dog").click()
    expect(player).not_to_be_visible()
    expect(page.locator("#accountPlane")).to_have_class(re.compile(r"\bopen\b"))
    page.evaluate("redDog.close()")
    lane_tile.get_by_role("button", name="Open fullscreen").press("Enter")
    player.get_by_role("button", name="Enter FoundUp").click()
    page.wait_for_url("https://foundups.com/f/move2japan")
    print(json.dumps({"member_desktop_columns": columns, "mixed_cards": len(ordinary),
                      "watch_viewport": box, "queue_advance_after_manual_play": True, "hover_frames": 0,
                      "quick_view_and_saved_rows": True, "expanded_clip_return": offset}))


def verify_member_phone(page, context, supports_cdp):
    page.goto("https://foundups.com/member/", wait_until="domcontentloaded")
    field = page.locator("#mallTileField")
    tile = field.locator('.mall-tile[data-foundup-id="move2japan"]')
    expect(tile).to_be_visible()
    clips = page.evaluate("mallTileField.getCatalog().find(item => item.foundup_id === 'move2japan').videos")
    field_scroll = page.locator(".mall-tile-field-wrapper")
    tile.scroll_into_view_if_needed()
    start_scroll = field_scroll.evaluate("el => el.scrollTop")
    tile.tap(position={"x":60,"y":40})
    inline = page.get_by_role("region", name="Floating video player")
    expect(inline).to_be_visible()
    expect(tile).to_have_attribute("aria-current", "true")
    stage = inline.locator("iframe")
    expect(stage).to_be_visible()
    assert min(stage.bounding_box()["width"], stage.bounding_box()["height"]) >= 200
    if page.evaluate("mallVideoPlayer.getPlaybackSnapshot()?.state === 'manual-play'"):
        inline.get_by_role("button", name="Play video", exact=True).tap()
    expect_playing_id(page, clips[0]["video_id"])
    stage.evaluate("frame => { window.phoneFrame = frame; window.phoneFrameContext = frame.contentWindow; }")

    inline.get_by_role("button", name="Open WikiTube").tap()
    player = page.get_by_role("dialog", name="WikiTube video player")
    query = player.get_by_role("textbox", name="Search this queue")
    rail = player.locator(".video-player-queue-track")
    frame = player.locator("iframe")
    same_context = "frame => frame === window.phoneFrame && frame.contentWindow === window.phoneFrameContext"
    expect(query).to_be_visible()
    assert frame.evaluate(same_context)
    box = frame.bounding_box()
    assert box["y"] + box["height"] <= query.bounding_box()["y"] < rail.bounding_box()["y"]
    thumbnail = rail.locator("img").first.bounding_box()
    assert thumbnail["width"] >= 120 and thumbnail["height"] >= 70
    assert rail.evaluate("el => el.scrollWidth > el.clientWidth")

    if supports_cdp:
        session = context.new_cdp_session(page)
        rect = rail.bounding_box()
        y = round(rect["y"] + rect["height"] / 2)
        start = round(rect["x"] + rect["width"] * .8)
        end = round(rect["x"] + rect["width"] * .2)
        session.send("Input.dispatchTouchEvent", {"type":"touchStart", "touchPoints":[{"x":start,"y":y}]})
        for step in range(1, 7):
            x = round(start + (end - start) * step / 6)
            session.send("Input.dispatchTouchEvent", {"type":"touchMove", "touchPoints":[{"x":x,"y":y}]})
        session.send("Input.dispatchTouchEvent", {"type":"touchEnd", "touchPoints":[]})
        page.wait_for_function("document.querySelector('.video-player-queue-track').scrollLeft > 0")
        assert frame.evaluate(same_context)
        expect_playing_id(page, clips[0]["video_id"])

    query.fill("vulnpocalypse")
    query.press("ArrowLeft")
    query.press("Enter")
    expect_playing_id(page, clips[0]["video_id"])
    assert frame.evaluate(same_context)
    expect(rail.get_by_role("button").first).to_be_visible()
    query.fill("")
    query.press("Escape")
    expect(player).to_be_visible()
    expect(player.get_by_role("button", name="Back")).to_be_focused()

    options = player.get_by_role("button", name="Search options")
    options.evaluate("""button => {
        for (const [type, y] of [['touchstart', 400], ['touchend', 320]]) {
          const event = new Event(type, {bubbles: true});
          Object.defineProperty(event, type === 'touchend' ? 'changedTouches' : 'touches',
            {value: [{clientX: 30, clientY: y}]});
          button.dispatchEvent(event);
        }
    }""")
    expect(player.get_by_role("dialog", name="Search options")).to_be_visible()
    page.keyboard.press("Escape")
    expect(player.get_by_role("dialog", name="Search options")).to_be_hidden()

    transcript = "Please show me the Move2Japan videos about the Vulnpocalypse in this queue."
    page.evaluate("value => { window.fixtureTranscript = value; }", transcript)
    page.evaluate("""() => {
      window.fixtureSpeech = {starts: 0, stops: 0, aborts: 0};
      window.SpeechRecognition = class {
        static available(options) { return options.processLocally ? 'available' : 'unavailable'; }
        set processLocally(value) { this.local = value; }
        start() { if (this.local) { fixtureSpeech.starts++; this.onstart(); } }
        stop() {
          fixtureSpeech.stops++;
          this.onresult({results: [[{transcript: fixtureTranscript}]]});
          this.onend();
        }
        abort() { fixtureSpeech.aborts++; }
      };
    }""")
    dog = player.get_by_role("button", name="Open Red Dog")
    dog_position = dog.bounding_box()
    idle_height = query.bounding_box()["height"]
    dog.dispatch_event("pointerdown", {"isPrimary":True,"button":0})
    stop = player.get_by_role("button", name="Stop dictation")
    expect(stop).to_be_visible()
    expect(stop.locator(".mall-dictation-stop")).to_be_visible()
    assert abs(stop.bounding_box()["x"] - dog_position["x"]) <= 1
    assert abs(stop.bounding_box()["y"] - dog_position["y"]) <= 1
    assert dog.evaluate("el => { const r = el.getBoundingClientRect(); return el.contains(document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2)); }")
    dog.dispatch_event("pointerup", {"isPrimary":True,"button":0})
    expect(query).to_have_value(transcript)
    assert query.bounding_box()["height"] > idle_height
    assert page.evaluate("fixtureSpeech.starts === 1 && fixtureSpeech.stops === 1")
    assert frame.evaluate(same_context)
    mic = player.get_by_role("button", name="Dictate search")
    mic.tap()
    expect(mic).to_have_attribute("aria-pressed", "true")
    expect(dog).to_be_hidden()
    assert stop.bounding_box()["x"] > mic.bounding_box()["x"]
    stop.tap()
    page.wait_for_function("fixtureSpeech.starts === 2 && fixtureSpeech.stops === 2")
    expect(dog).to_be_visible()
    expect(query).to_have_value(transcript)
    expect_playing_id(page, clips[0]["video_id"])
    query.press("End")
    query.press("Backspace")
    expect(query).to_have_value(transcript[:-1])
    dog.dispatch_event("pointerdown", {"isPrimary":True,"button":0})
    expect(stop).to_be_visible()
    dog.dispatch_event("pointercancel", {"isPrimary":True,"button":0})
    expect(stop).to_be_hidden()
    assert page.evaluate("fixtureSpeech.aborts === 1")
    assert frame.evaluate(same_context)

    for width, height in [(320, 640), (430, 932), (844, 390)]:
        page.set_viewport_size({"width":width, "height":height})
        expect(query).to_be_in_viewport()
        expect(rail).to_be_in_viewport()
        assert frame.evaluate(same_context)
        frame_box = frame.bounding_box()
        assert min(frame_box["width"], frame_box["height"]) >= 200
        assert query.bounding_box()["y"] < rail.bounding_box()["y"]
    page.set_viewport_size({"width":390, "height":844})
    expect(query).to_be_in_viewport()
    expect(rail).to_be_in_viewport()
    query.fill("")
    assert query.bounding_box()["height"] == idle_height
    player.get_by_role("button", name="Back").tap()
    expect(player).to_be_hidden()
    expect(tile).to_be_focused()
    expect_position(page, start_scroll)
    assert page.locator("iframe").count() == 0

    anchor = page.locator('#redDogAnchor')
    page.evaluate("redDog.openModes()")
    anchor.locator('[data-reddog-mode="listen"]').tap()
    anchor.get_by_role("button", name="Stop dictation").tap()
    expect(anchor.get_by_role("textbox", name="Search the Mall")).to_have_value(transcript)
    assert page.evaluate("fixtureSpeech.starts === 4 && fixtureSpeech.stops === 3")
    expect(anchor.get_by_role("button", name="Open Red Dog")).to_be_visible()

    # Phone patch-load (mounts only visible screenful patches out of 594 clips) & touch press-hold OSP flip
    page.evaluate("mallTileField.searchCatalog(''); mallTileField.expandFoundUp(0)")
    patched_count = field.locator(".mall-tile").count()
    assert 9 <= patched_count < len(clips), f"Expected phone patch-load < {len(clips)}, got {patched_count}"
    expect(field.get_by_role("button", name="Load more videos")).to_be_attached()
    page.evaluate("mallTileField.collapseFoundUp()")
    first_tile = field.locator('.mall-tile[data-foundup-id="move2japan"]')
    first_tile.scroll_into_view_if_needed()
    first_tile.evaluate("""el => {
      const ev = new Event('touchstart', { bubbles: true, cancelable: true });
      Object.defineProperty(ev, 'touches', { value: [{ clientX: 60, clientY: 60 }] });
      el.dispatchEvent(ev);
    }""")
    page.wait_for_timeout(520)
    first_tile.evaluate("""el => {
      const ev = new Event('touchend', { bubbles: true, cancelable: true });
      Object.defineProperty(ev, 'touches', { value: [] });
      el.dispatchEvent(ev);
    }""")
    expect(first_tile).to_have_class(re.compile(r"\bis-flipped\b"))
    expect(first_tile.locator(".mall-tile-osp-back")).to_contain_text("Outcome")
    expect(first_tile.locator(".mall-tile-osp-back")).to_contain_text("Solution")
    expect(first_tile.locator(".mall-tile-osp-back")).to_contain_text("Pain")
    first_tile.locator(".mall-tile-osp-close").tap()
    expect(first_tile).not_to_have_class(re.compile(r"\bis-flipped\b"))

    print(json.dumps({"member_phone_inline_and_immersive": True,
                      "horizontal_touch_scroll": supports_cdp,
                      "foreground_dictation_hold_and_stop": True,
                      "red_dog_mode_sheet_stop": True,
                      "multiline_editing_and_stop_in_red_dog_slot": True,
                      "queue_search_portrait_and_landscape": True}))


def verify_member_entry(browser_type):
    browser = browser_type.launch()
    context = browser.new_context(viewport={"width": 1440, "height": 900}, service_workers="block",
                                  reduced_motion="reduce")
    context.add_init_script(provider)
    account = None
    requested = []

    def route_member(route):
        url = urlsplit(route.request.url)
        requested.append(url.path)
        if url.hostname and url.hostname.endswith(".clerk.accounts.dev") and url.path.endswith("/clerk.browser.js"):
            account_data = json.dumps(account)
            body = f"""window.fixtureMemberAccount = {account_data};
                window.Clerk = {{user: window.fixtureMemberAccount && {{id:'fixture-member'}}, load: async () => {{}}}};"""
        elif url.hostname == "www.gstatic.com" and url.path.endswith("/firebase-app.js"):
            body = "export const initializeApp = () => ({});"
        elif url.hostname == "www.gstatic.com" and url.path.endswith("/firebase-firestore.js"):
            body = """export const getFirestore = () => ({}), doc = () => ({});
                export const getDoc = async () => ({exists: () => true, data: () => window.fixtureMemberAccount});"""
        elif url.path == "/js/firebase-runtime-config.js":
            body = "export const loadFirebaseRuntimeConfig = async () => ({});"
        elif url.hostname == "foundup-japan-ai-autopost-camera-56566376153.us-west1.run.app" and url.path == "/":
            route.fulfill(status=200, content_type="text/html", body="<h1>AutoPost fixture</h1>")
            return
        elif url.hostname in {"foundups.com", "play.foundups.com"} and url.path == "/" and url.query == "signin=required":
            route.fulfill(status=200, content_type="text/html", body="<h1>Member sign-in destination</h1>")
            return
        else:
            return route_local(route)
        route.fulfill(status=200, content_type="text/javascript", body=body,
                      headers={"Access-Control-Allow-Origin": "*"})

    context.route("**/*", route_member)
    page = context.new_page()
    page.set_default_timeout(10000)

    # 1. play.foundups.com is the open discovery landing for ALL FoundUps (zero Clerk/Firestore gate)
    ordinary_catalog = json.loads((public / "member/mall-video-catalog.json").read_text(encoding="utf-8"))
    page.goto("https://play.foundups.com/", wait_until="domcontentloaded")
    page.wait_for_url("https://play.foundups.com/member/")
    expect(page.get_by_role("textbox", name="Search the Mall")).to_be_visible()
    expect(page.locator("#mallTileField .mall-tile")).to_have_count(len(ordinary_catalog))
    assert not any("clerk" in path or "firebase" in path for path in requested), requested
    expect(page.locator("#mallUserHandle")).to_have_text("Member Portal ↗")
    expect(page.locator(".mall-brand-minimal img")).to_have_attribute("src", "/logo-foundups.svg")
    expect(page.locator("a.mall-brand-ln")).to_have_attribute("href", "https://www.linkedin.com/company/foundups/")
    expect(page.locator('#mallTileField .mall-tile[data-foundup-id^="linkedin_"]')).to_have_count(0)
    expect(page.locator('#mallTileField .mall-tile[data-foundup-id="voteballots"]')).to_have_count(1)

    # Desktop mouse hover-and-hold flips tile to reveal Outcome, Solution, Pain
    gotjunk_tile = page.locator('#mallTileField .mall-tile[data-foundup-id="gotjunk_001"]')
    gotjunk_tile.dispatch_event("pointerenter", {"pointerType": "mouse"})
    page.wait_for_timeout(720)
    expect(gotjunk_tile).to_have_class(re.compile(r"\bis-flipped\b"))
    expect(gotjunk_tile.locator(".mall-tile-osp-back")).to_contain_text("Outcome")
    expect(gotjunk_tile.locator(".mall-tile-osp-back")).to_contain_text("Solution")
    expect(gotjunk_tile.locator(".mall-tile-osp-back")).to_contain_text("Pain")
    gotjunk_tile.dispatch_event("pointerleave", {"pointerType": "mouse"})
    expect(gotjunk_tile).not_to_have_class(re.compile(r"\bis-flipped\b"))

    # Non-video FoundUp quick-view on play.foundups.com routes Enter FoundUp through foundups.com Member Portal
    page.locator('#mallTileField .mall-tile[data-foundup-id="gotjunk_001"]').click()
    expect(page.locator("#foundupViewPlane")).to_have_class("foundup-view-plane open")
    portal_cta = page.locator("#foundupViewPlane .fv-primary-cta")
    expect(portal_cta).to_contain_text("Enter FoundUp · Member Portal")
    expect(portal_cta).to_have_attribute("href", "https://foundups.com/member/?enter=gotjunk_001")
    portal_cta.click()
    page.wait_for_url("https://foundups.com/?signin=required")
    assert json.loads(page.evaluate("sessionStorage.getItem('pfmall_product_return_v1')"))["filters"] == {"enter": "gotjunk_001"}

    # Uninvited account on foundups.com stops at #inviteGate without consuming FoundUp entry return
    account = {"username": "fixture"}
    page.goto("https://foundups.com/member/", wait_until="domcontentloaded")
    expect(page.locator("#inviteGate")).to_be_visible()
    assert page.evaluate("sessionStorage.getItem('pfmall_product_return_v1')")

    # Admitted member on foundups.com completes FoundUp entry handoff to /member/foundup.html?id=gotjunk_001
    account = {"username": "fixture", "inviteValidated": True}
    page.goto("https://foundups.com/member/", wait_until="domcontentloaded")
    page.wait_for_url("https://foundups.com/member/foundup.html?id=gotjunk_001")
    expect(page.locator(".entry-hero-name")).to_have_text("GotJunk")
    assert page.evaluate("sessionStorage.getItem('pfmall_product_return_v1')") is None

    # Video player Enter FoundUp on play.foundups.com also passes through foundups.com Member Portal
    account = None
    page.goto("https://play.foundups.com/member/", wait_until="domcontentloaded")
    page.locator('#mallTileField .mall-tile[data-foundup-id="move2japan"]').click()
    floating = page.get_by_role("region", name="Floating video player")
    expect(floating).to_be_visible()
    floating.get_by_role("button", name="Enter FoundUp").click()
    page.wait_for_url("https://foundups.com/?signin=required")
    assert json.loads(page.evaluate("sessionStorage.getItem('pfmall_product_return_v1')"))["filters"] == {"enter": "move2japan"}
    page.evaluate("sessionStorage.removeItem('pfmall_product_return_v1')")

    # Direct play.foundups.com/member/foundup.html?id=... also redirects through foundups.com Member Portal
    page.goto("https://play.foundups.com/member/foundup.html?id=autopost", wait_until="domcontentloaded")
    page.wait_for_url("https://foundups.com/?signin=required")
    page.evaluate("sessionStorage.removeItem('pfmall_product_return_v1')")

    # 2. Scoped ?foundup=hpc on foundups.com retains its member admission + sign-in return contract
    requested.clear()
    scoped = "https://foundups.com/member/?foundup=hpc"
    page.goto(scoped, wait_until="domcontentloaded")
    page.wait_for_url("https://foundups.com/?signin=required")
    assert page.evaluate("sessionStorage.getItem('pfmall_product_return_v1')")
    assert not any(path.endswith("catalog.json") for path in requested)

    account = {"username": "fixture"}
    page.goto("https://foundups.com/member/", wait_until="domcontentloaded")
    expect(page.locator("#inviteGate")).to_be_visible()
    assert page.evaluate("sessionStorage.getItem('pfmall_product_return_v1')")
    assert not any(path.endswith("catalog.json") for path in requested)

    account = {"username": "fixture", "inviteValidated": True}
    requested.clear()
    page.goto("https://foundups.com/member/", wait_until="domcontentloaded")
    page.wait_for_url(scoped)
    expect(page.get_by_role("region", name="Video theater")).to_be_visible()
    expect_playing(page, 0)
    assert page.evaluate("sessionStorage.getItem('pfmall_product_return_v1')") is None
    assert requested.count("/member/mall-public-video-catalog.json") == 1
    assert "/member/mall-video-catalog.json" not in requested
    page.goto("https://foundups.com/f/hpc", wait_until="domcontentloaded")
    expect(page.get_by_role("link", name="Browse Shorts")).to_have_attribute(
        "href", "https://hpc.foundups.com/"
    )
    verify_member_poster_grid(page)
    touch = browser.new_context(viewport={"width": 1100, "height": 800}, has_touch=True,
                                is_mobile=True, service_workers="block")
    touch.route("**/*", route_member)
    touch_page = touch.new_page()
    touch_page.goto("https://foundups.com/member/", wait_until="domcontentloaded")
    expect(touch_page.locator("#mallTileField")).to_have_attribute("data-layout", "rows")
    phone = browser.new_context(viewport={"width":390, "height":844}, has_touch=True,
                                is_mobile=True, service_workers="block", reduced_motion="reduce")
    phone.add_init_script(provider)
    phone.route("**/*", route_member)
    verify_member_phone(phone.new_page(), phone, browser_type.name == "chromium")
    browser.close()
    print(json.dumps({"member_sign_in_return": True, "uninvited_blocked": True,
                      "admitted_desktop_theater": True, "public_discovery_destination": True,
                      "member_wide_touch_rows": True}))


def verify_desktop(browser_type):
    browser = browser_type.launch()
    context = browser.new_context(viewport={"width":1440,"height":900}, service_workers="block")
    context.add_init_script(provider)
    context.route("**/*", route_local)
    page = context.new_page()
    page.set_default_timeout(8000)
    page.goto("https://hpc.foundups.com/member/", wait_until="domcontentloaded")
    expect(page.locator("#videoScopeHeader .mall-build-label")).to_be_visible()
    player = page.get_by_role("region", name="Video theater")
    search = player.get_by_role("searchbox", name="Search videos")
    search_form = player.get_by_role("search")
    submit = search_form.get_by_role("button", name="Play search result")
    stage = player.locator(".video-player-stage")
    rail = player.locator(".video-player-queue-rail")
    cards = rail.get_by_role("button")
    expect_playing(page, 0)
    expect(cards).to_have_count(fixture_total)
    expect(page.locator(".mall-tile").first).to_be_hidden()
    stage_box, search_box, rail_box = stage.bounding_box(), search_form.bounding_box(), rail.bounding_box()
    assert stage_box["width"] >= 200 and stage_box["height"] >= 200
    assert abs(search_box["width"] - 584) <= 1 and abs(search_box["height"] - 52) <= 1
    assert abs(search_box["x"] + search_box["width"]/2 - stage_box["x"] - stage_box["width"]/2) <= 1
    assert stage_box["y"] + stage_box["height"] <= search_box["y"]
    assert search_box["y"] + search_box["height"] <= rail_box["y"]
    assert rail_box["y"] + rail_box["height"] <= 900
    assert page.evaluate("!history.state?.pfmallScopedPlayer && document.activeElement === document.body")
    assert page.evaluate("window.fixturePlayback.mutes") == 1

    page.evaluate("""window.originalFrame = document.querySelector('.video-player-stage iframe');
        window.originalContext = window.originalFrame.contentWindow""")
    search.fill("theater topic")
    expect(cards).to_have_count(2)
    assert page.evaluate("window.originalFrame === document.querySelector('.video-player-stage iframe')")
    expect_playing(page, 0)
    search.press("Enter")
    expect_playing(page, 2)
    page.evaluate("window.fixturePlayback.finishCurrent()")
    expect_playing(page, 20)
    submit.click()
    expect_playing(page, 2)
    cards.nth(1).press("Enter")
    expect_playing(page, 20)

    search.fill("no matching clip")
    search.press("Enter")
    expect(rail.get_by_role("status")).to_have_text("No videos match your search.")
    expect(cards).to_have_count(0)
    expect_playing(page, 20)
    search.fill("theater selection")
    submit.click()
    expect_playing(page, 24)
    expect(cards).to_have_attribute("aria-current", "true")
    expect(player.locator("iframe")).to_have_count(1)
    assert page.evaluate("window.fixturePlayback.created - window.fixturePlayback.destroyed") == 1

    page.evaluate("""window.selectedFrame = document.querySelector('.video-player-stage iframe');
        window.selectedContext = window.selectedFrame.contentWindow""")
    start_time = page.evaluate("window.mallVideoPlayer.getPlaybackSnapshot().positionSeconds")
    page.set_viewport_size({"width":899,"height":844})
    inline = page.get_by_role("region", name="Floating video player")
    expect(inline).to_be_visible()
    expect(video(page, 24)).to_have_attribute("aria-current", "true")
    expect(video(page, 24)).to_be_visible()
    assert page.evaluate("window.selectedContext === document.querySelector('.video-player-stage iframe').contentWindow")
    page.wait_for_function("start => window.mallVideoPlayer.getPlaybackSnapshot().positionSeconds > start + 0.1", arg=start_time)
    page.set_viewport_size({"width":900,"height":844})
    expect(search).to_have_value("theater selection")
    expect(cards).to_have_count(1)
    expect(cards).to_have_attribute("aria-current", "true")
    assert page.evaluate("window.selectedFrame === document.querySelector('.video-player-stage iframe') && window.selectedContext === window.selectedFrame.contentWindow")
    expect_playing(page, 24)

    # A fresh load after the civic resource recovers the same tab-local query and video.
    with page.expect_navigation(wait_until="domcontentloaded"):
        page.locator("#videoScopeVoice").click()
    expect(page.get_by_role("heading", name="Contact Congress fixture")).to_be_visible()
    page.go_back(wait_until="domcontentloaded")
    expect(search).to_have_value("theater selection")
    expect_playing(page, 24)

    page.set_viewport_size({"width":390,"height":844})
    expect(inline).to_be_visible()
    inline.locator(".video-player-top-bar").evaluate("""bar => {
      for (const [type, distance] of [['touchstart', 40], ['touchmove', 90]]) {
        const event = new Event(type, { bubbles: true, cancelable: true });
        Object.defineProperty(event, 'touches', { value: [{clientX: 0, clientY: 0}, {clientX: distance, clientY: 0}] });
        bar.dispatchEvent(event);
      }
    }""")
    expect(page.get_by_role("dialog", name="WikiTube video player")).to_be_visible()
    page.evaluate("history.back()")
    expect(page.locator("#videoPlayerFullscreen")).to_be_hidden()
    expect(video(page, 24)).to_be_focused()
    expect(video(page, 24)).to_be_in_viewport()
    assert page.evaluate("document.querySelector('.mall-tile-field-wrapper').scrollTop") > 0
    assert page.url == "https://hpc.foundups.com/member/"

    phone_search = page.locator("#videoScopePhoneDock").get_by_role("textbox", name="Search videos")
    phone_search.fill("fixture clip 25")
    phone_search.press("Enter")
    expect(page.locator(".mall-tile")).to_have_count(1)
    video(page, 25).click(position={"x":25,"y":90})
    expect_playing(page, 25)
    page.evaluate("window.phoneContext = document.querySelector('.video-player-stage iframe').contentWindow")
    page.set_viewport_size({"width":1440,"height":900})
    expect(search).to_have_value("theater selection")
    expect(cards).to_have_count(1)
    assert page.evaluate("window.phoneContext === document.querySelector('.video-player-stage iframe').contentWindow")
    expect_playing(page, 25)
    page.set_viewport_size({"width":899,"height":844})
    expect(phone_search).to_have_value("fixture clip 25")
    expect(video(page, 25)).to_have_attribute("aria-current", "true")
    assert page.evaluate("window.phoneContext === document.querySelector('.video-player-stage iframe').contentWindow")
    inline.get_by_role("button", name="Open WikiTube", exact=True).click()
    expect(page.get_by_role("dialog", name="WikiTube video player")).to_be_visible()
    page.set_viewport_size({"width":900,"height":844})
    expect(page.locator(".mall-tile")).to_have_count(1)
    assert page.evaluate("document.querySelector('.mall-tile').closest('[inert]') !== null")
    assert page.evaluate("window.phoneContext === document.querySelector('.video-player-stage iframe').contentWindow")
    page.get_by_role("dialog", name="WikiTube video player").get_by_role("button", name="Back", exact=True).click()
    expect(search).to_be_visible()
    expect_playing(page, 25)
    search.fill("theater topic")
    search.press("Enter")
    expect_playing(page, 2)
    page.evaluate("window.outOfFilterContext = document.querySelector('.video-player-stage iframe').contentWindow")
    page.set_viewport_size({"width":899,"height":844})
    expect(phone_search).to_have_value("fixture clip 25")
    expect(video(page, 2)).to_have_attribute("aria-current", "true")
    expect(page.locator(".mall-tile")).to_have_count(2)
    assert page.evaluate("window.outOfFilterContext === document.querySelector('.video-player-stage iframe').contentWindow")
    inline.get_by_role("button", name="Close player").click()
    expect(page.locator(".mall-tile")).to_have_count(1)
    expect(video(page, 25)).to_be_visible()
    context.close()

    blocked = browser.new_context(viewport={"width":1280,"height":720}, service_workers="block")
    blocked.add_init_script(provider.replace("block: false", "block: true", 1))
    blocked.route("**/*", route_local)
    page = blocked.new_page()
    page.goto("https://hpc.foundups.com/member/", wait_until="domcontentloaded")
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state === 'autoplay-blocked'")
    page.evaluate("window.fixturePlayback.block = false")
    page.get_by_role("button", name="Play video", exact=True).click()
    expect_playing(page, 0)
    blocked.close()

    touch = browser.new_context(viewport={"width":1024,"height":768}, is_mobile=True, has_touch=True, service_workers="block")
    touch.add_init_script(provider)
    touch.route("**/*", route_local)
    page = touch.new_page()
    page.goto("https://hpc.foundups.com/member/", wait_until="domcontentloaded")
    expect(video(page, 0)).to_be_visible()
    assert len({t["x"] for t in info(page)["tiles"][:3]}) == 3
    expect(page.get_by_role("region", name="Video theater")).to_have_count(0)
    browser.close()
    print(json.dumps({"desktop_theater": True, "startup_mute_and_block_recovery": True,
                      "filtered_queue_advance": True, "search_submit_playback": True,
                      "breakpoint_kept_provider_context": True,
                      "coarse_pointer_stays_grid": True}, sort_keys=True))


def dispatch_pinch(locator, start_dist, end_dist):
    locator.evaluate("""(el, [d0, d1]) => {
      for (const [type, dist] of [['touchstart', d0], ['touchmove', d1]]) {
        const ev = new Event(type, { bubbles: true, cancelable: true });
        Object.defineProperty(ev, 'touches', {
          value: [{ clientX: 60, clientY: 80 }, { clientX: 60 + dist, clientY: 80 }]
        });
        el.dispatchEvent(ev);
      }
      const end = new Event('touchend', { bubbles: true, cancelable: true });
      Object.defineProperty(end, 'touches', { value: [] });
      Object.defineProperty(end, 'changedTouches', { value: [{ clientX: 60 + d1, clientY: 80 }] });
      el.dispatchEvent(end);
    }""", [start_dist, end_dist])


def dispatch_swipe(locator, dx, dy=4):
    locator.evaluate("""(el, [dx, dy]) => {
      const start = new Event('touchstart', { bubbles: true, cancelable: true });
      Object.defineProperty(start, 'touches', { value: [{ clientX: 120, clientY: 60 }] });
      el.dispatchEvent(start);
      const move = new Event('touchmove', { bubbles: true, cancelable: true });
      Object.defineProperty(move, 'touches', { value: [{ clientX: 120 + dx, clientY: 60 + dy }] });
      el.dispatchEvent(move);
      const end = new Event('touchend', { bubbles: true, cancelable: true });
      Object.defineProperty(end, 'touches', { value: [] });
      Object.defineProperty(end, 'changedTouches', { value: [{ clientX: 120 + dx, clientY: 60 + dy }] });
      el.dispatchEvent(end);
    }""", [dx, dy])


def verify_floating_and_wikitube_gestures(browser_type):
    browser = browser_type.launch()
    context = browser.new_context(
        viewport={"width": 375, "height": 812},
        is_mobile=True,
        has_touch=True,
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
        service_workers="block",
        reduced_motion="reduce"
    )
    context.add_init_script(provider)
    context.route("**/*", route_local)
    page = context.new_page()
    page.set_default_timeout(10000)
    page.goto("https://hpc.foundups.com/member/", wait_until="domcontentloaded")
    page.evaluate("window.__pfmallWikiTubeSkipDelayMs = 40")

    # 1. 375px iPhone one-tap playback & top-anchored floating position
    tile0_box = video(page, 0).bounding_box()
    assert tile0_box["width"] >= 120 and tile0_box["height"] >= 70, tile0_box
    video(page, 0).tap(position={"x": 30, "y": 80})
    expect_playing(page, 0)
    player = page.locator("#videoPlayerFullscreen")
    expect(player).to_have_attribute("aria-label", "Floating video player")
    top_anchor_y = player.bounding_box()["y"]
    assert top_anchor_y < 100, top_anchor_y

    # 2. Grid scrolls freely beneath floating player; lower clicked tile opens at SAME top anchor
    wrapper = page.locator(".mall-tile-field-wrapper")
    wrapper.evaluate("el => el.scrollTop = 520")
    page.wait_for_function("document.querySelector('.mall-tile-field-wrapper').scrollTop >= 400")
    assert abs(player.bounding_box()["y"] - top_anchor_y) <= 1
    lower_tile = video(page, 11)
    lower_tile.scroll_into_view_if_needed()
    lower_tile_y = lower_tile.bounding_box()["y"]
    assert lower_tile_y > 150
    page.evaluate("window.floatingFrameRef = document.querySelector('#videoPlayerFullscreen iframe')")
    lower_tile.tap(position={"x": 30, "y": 80})
    expect_playing(page, 11)
    assert abs(player.bounding_box()["y"] - top_anchor_y) <= 1
    assert page.evaluate("window.floatingFrameRef === document.querySelector('#videoPlayerFullscreen iframe')")
    assert page.evaluate("window.fixturePlayback.created") == 1

    # 3. Swipe-right tuck + audio/time continuity + edge-handle swipe-left & button restore
    pos_before_tuck = page.evaluate("window.mallVideoPlayer.getPlaybackSnapshot().positionSeconds")
    dispatch_swipe(player.locator(".video-player-top-bar"), 95, 4)
    assert page.evaluate("window.mallVideoPlayer.isTucked() === true")
    handle = page.locator(".video-player-tuck-handle")
    expect(handle).to_be_visible()
    handle_box = handle.bounding_box()
    assert handle_box["x"] + handle_box["width"] >= 370, handle_box
    assert page.evaluate("document.documentElement.style.getPropertyValue('--floating-player-clearance')") == "0px"
    page.wait_for_function("prev => window.mallVideoPlayer.getPlaybackSnapshot().positionSeconds > prev + 0.1", arg=pos_before_tuck)
    wrapper.evaluate("el => el.scrollTop = 200")
    assert page.evaluate("window.mallVideoPlayer.isTucked() === true && window.mallVideoPlayer.getPlaybackSnapshot().state === 'playing'")
    # Swipe-left on edge handle restores player
    dispatch_swipe(handle, -45, 2)
    assert page.evaluate("window.mallVideoPlayer.isTucked() === false")
    expect(handle).to_be_hidden()
    assert page.evaluate("window.floatingFrameRef === document.querySelector('#videoPlayerFullscreen iframe')")
    # Accessible Tuck button + tap on Restore handle
    player.get_by_role("button", name="Tuck player", exact=True).tap()
    assert page.evaluate("window.mallVideoPlayer.isTucked() === true")
    expect(handle).to_be_visible()
    handle.tap()
    assert page.evaluate("window.mallVideoPlayer.isTucked() === false")
    expect_playing(page, 11)

    # 4. Gesture disambiguation: tiny 2-finger jitter (<26px delta) must NOT trigger pinch
    dispatch_pinch(player.locator(".video-player-top-bar"), 45, 53)
    assert page.evaluate("window.mallVideoPlayer.isFloating() === true && window.mallVideoPlayer.isOpen() === true")
    page.wait_for_timeout(100)

    # 5. Autoplay-blocked truth + Pinch-out into WikiTube immediately attempts playback
    player.get_by_role("button", name="Close player", exact=True).tap()
    expect(player).to_be_hidden()
    page.evaluate("window.fixturePlayback.block = true")
    video(page, 1).tap(position={"x": 30, "y": 80})
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state === 'autoplay-blocked'")
    expect(player.get_by_role("button", name="Play video", exact=True)).to_be_visible()
    page.evaluate("window.fixturePlayback.block = false")
    dispatch_pinch(player.locator(".video-player-top-bar"), 40, 105)
    expect(player).to_have_attribute("aria-label", "WikiTube video player")
    expect_playing(page, 1)
    assert page.evaluate("window.mallVideoPlayer.getCurrentIndex()") == 1
    assert page.evaluate("window.mallVideoPlayer.getQueueLength()") == fixture_total

    # Horizontal swipe on WikiTube queue rail must NOT dismiss or exit WikiTube
    dispatch_swipe(player.locator(".video-player-queue-track"), -120, 3)
    assert page.evaluate("window.mallVideoPlayer.isWikiTube() === true")

    # Accessible Floating player button minimizes WikiTube back to floating
    player.get_by_role("button", name="Floating player", exact=True).tap()
    expect(player).to_have_attribute("aria-label", "Floating video player")
    expect_playing(page, 1)

    # Pinch-out back to WikiTube, then Pinch-in on WikiTube returns directly to grid
    dispatch_pinch(player.locator(".video-player-top-bar"), 40, 105)
    expect(player).to_have_attribute("aria-label", "WikiTube video player")
    page.wait_for_timeout(100)
    dispatch_pinch(player.locator(".video-player-top-bar"), 120, 48)
    expect(player).to_be_hidden()
    assert page.evaluate("window.mallVideoPlayer.isOpen() === false")
    expect(player.locator("iframe")).to_have_count(0)

    # Pinch-in on Floating player closes to grid
    wrapper.evaluate("el => el.scrollTop = 0")
    video(page, 2).tap(position={"x": 30, "y": 80})
    expect_playing(page, 2)
    page.wait_for_timeout(100)
    dispatch_pinch(player.locator(".video-player-top-bar"), 120, 48)
    expect(player).to_be_hidden()

    # 6. WikiTube sequential auto-advance + bounded error skip & halt recovery (zero infinite loops)
    video(page, 0).tap(position={"x": 30, "y": 80})
    expect_playing(page, 0)
    player.get_by_role("button", name="Open WikiTube", exact=True).tap()
    expect(player).to_have_attribute("aria-label", "WikiTube video player")
    page.evaluate("window.wikitubeFrameRef = document.querySelector('#videoPlayerFullscreen iframe')")
    page.evaluate("window.fixturePlayback.finishCurrent()")
    expect_playing(page, 1)
    assert page.evaluate("window.wikitubeFrameRef === document.querySelector('#videoPlayerFullscreen iframe')")

    #Unavailable (100) at index 2 and Restricted (150) at index 3 skip cleanly to playable index 4
    page.evaluate("""() => {
      window.fixturePlayback.errorsByVideo = { HPC00000002: 100, HPC00000003: 150 };
    }""")
    page.evaluate("window.fixturePlayback.finishCurrent()")
    expect_playing(page, 4)
    failed = page.evaluate("window.mallVideoPlayer.getPlaybackSnapshot().failedIndices")
    assert 2 in failed and 3 in failed, failed

    # All remaining videos failing halts cleanly after MAX_CONSECUTIVE_AUTO_SKIPS (5)
    page.evaluate("window.fixturePlayback.errorsByVideo = {}; window.fixturePlayback.error = 150;")
    page.evaluate("window.fixturePlayback.finishCurrent()")
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.queueHalted === true")
    halted_snap = page.evaluate("window.mallVideoPlayer.getPlaybackSnapshot()")
    assert halted_snap["state"] == "embedding-disabled" and halted_snap["queueIndex"] == 10, halted_snap
    expect(player.locator(".video-player-status")).to_contain_text("Queue stopped")

    # Autoplay-blocked in WikiTube halts immediately and surfaces Play video (never auto-skips)
    page.evaluate("window.fixturePlayback.error = null; window.fixturePlayback.block = true;")
    player.locator('.video-player-queue-item[data-index="12"]').tap()
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state === 'autoplay-blocked'")
    blocked_snap = page.evaluate("window.mallVideoPlayer.getPlaybackSnapshot()")
    assert blocked_snap["queueIndex"] == 12 and blocked_snap["queueHalted"] is True, blocked_snap
    expect(player.get_by_role("button", name="Play video", exact=True)).to_be_visible()
    page.evaluate("window.fixturePlayback.block = false")
    player.get_by_role("button", name="Play video", exact=True).tap()
    expect_playing(page, 12)

    # Orientation rotation (portrait 375x812 -> landscape 844x390 -> portrait) keeps playback & stage >= 200px
    page.set_viewport_size({"width": 844, "height": 390})
    assert min(player.locator(".video-player-stage").bounding_box()["width"],
               player.locator(".video-player-stage").bounding_box()["height"]) >= 200
    expect_playing(page, 12)
    page.set_viewport_size({"width": 375, "height": 812})
    player.get_by_role("button", name="Back", exact=True).tap()
    expect(player).to_be_hidden()
    browser.close()
    print(json.dumps({
        "engine": browser_type.name,
        "one_tap_375px_autoplay": True,
        "top_anchored_floating_scroll": True,
        "swipe_tuck_and_edge_restore": True,
        "pinch_transitions_and_jitter_guard": True,
        "wikitube_sequential_and_bounded_recovery": True
    }, sort_keys=True))


if __name__ == "__main__":
    main()
    verify_diagnostics()
    with sync_playwright() as p:
        verify_desktop(p.chromium)
        verify_member_entry(p.chromium)
        verify_floating_and_wikitube_gestures(p.chromium)
        verify_floating_and_wikitube_gestures(p.webkit)
        verify_desktop(p.webkit)
