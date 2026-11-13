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
    created: 0, destroyed: 0, pause: 0, plays: 0, events: [], error: null, block: false, hang: false, mutes: 0
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
        if (trace.error !== null) emit('onError', trace.error);
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
        expect(mall_link).to_have_attribute("href", "https://foundups.com/member/")
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
        expect(player).to_have_attribute("aria-label","Inline video player")
        expect(selected).to_be_hidden()
        slot = page.locator(".mall-inline-player-slot")
        expect(slot).to_have_count(1)
        assert abs(slot.evaluate("slot => slot.offsetTop") - original_row) <= 1
        assert video(page, 0).evaluate("tile => tile.offsetTop") > original_row
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
        assert frame_clear, "Inline player controls are covered"
        observed["inline"] = {**state["stage"], "nine_unobstructed_points": frame_clear}
        player.get_by_role("button", name="Expand video", exact=True).tap()
        expect(player).to_have_attribute("aria-label", "Fullscreen video player")
        assert page.evaluate("window.originalFixtureIframe === document.querySelector('#videoPlayerFullscreen iframe')")
        assert page.evaluate("window.fixturePlayback.created") == 1
        assert page.evaluate("history.state.pfmallScopedPlayer") == "hpc"
        page.evaluate("history.back()")
        page.wait_for_function("!history.state?.pfmallScopedPlayer")
        expect(player).to_be_hidden()
        expect(selected).to_be_visible()
        assert abs(selected.evaluate("tile => tile.offsetTop") - original_row) <= 1
        expect(selected).to_be_focused()
        expect_position(page, 0)
        expect(player.locator("iframe")).to_have_count(0)
        observed["tile_row_replacement_and_same_iframe_expand"] = True

        middle = video(page, 1)
        row = middle.evaluate("tile => tile.offsetTop")
        middle.tap(position={"x":25,"y":90})
        page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot().state === 'playing'")
        expect(middle).to_be_hidden()
        assert abs(slot.evaluate("slot => slot.offsetTop") - row) <= 1
        video(page, 0).tap(position={"x":25,"y":90})
        page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot().state === 'playing'")
        expect(middle).to_be_visible()
        expect(video(page, 0)).to_be_hidden()
        expect(player.locator("iframe")).to_have_count(1)
        trace = page.evaluate("window.fixturePlayback")
        assert trace["created"] == 3 and trace["destroyed"] == 2, trace
        wrapper.evaluate("(el) => el.scrollTop = el.scrollHeight")
        page.wait_for_function("window.fixturePlayback.pause > 0")
        expect(player.locator("iframe")).to_have_count(1)
        page.keyboard.press("Escape")
        page.wait_for_function("!history.state?.pfmallScopedPlayer")
        observed["one_provider_after_switch_and_scroll_pause"] = True

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
        expect(video(page, 4)).to_be_hidden()
        landscape_stage = player.locator(".video-player-stage").bounding_box()
        assert 200 <= landscape_stage["height"] <= 235
        player.get_by_role("button", name="Close player").tap()
        page.wait_for_function("!history.state?.pfmallScopedPlayer")
        expect(video(page, 4)).to_be_visible()
        observed["landscape_playback_without_horizontal_overflow"] = True

        page.set_viewport_size({"width":320, "height":640})
        voice = page.locator("#videoScopeVoice").bounding_box()
        assert voice["x"] + voice["width"] <= 320
        more = dock.get_by_role("button", name="More options")
        search = dock.get_by_role("searchbox")
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
        expect(menu.get_by_text("No on-device models are connected.")).to_be_visible()
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
    mall_search = page.get_by_role("searchbox", name="Search the Mall")
    expect(mall_search).to_be_visible()
    mall_search.fill("AutoPost")
    mall_search.press("Enter")
    expect(tiles).to_have_count(1)
    mall_search.fill("")
    expect(tiles).to_have_count(len(ordinary))

    lane_tile.click()
    inline = page.get_by_role("region", name="Inline video player")
    expect(inline).to_be_visible()
    expect(lane_tile).to_be_hidden()
    expect_playing_id(page, clips[0]["video_id"])
    inline_frame = inline.locator("iframe")
    inline_box = inline_frame.bounding_box()
    assert inline_box and min(inline_box["width"], inline_box["height"]) >= 200
    inline_frame.evaluate("el => { window.originalPlayerFrame = el; }")
    inline.get_by_role("button", name="Expand video").click()
    player = page.get_by_role("dialog", name="Fullscreen video player")
    expect(player).to_have_attribute("aria-modal", "true")
    expect(player.get_by_role("button", name="Enter FoundUp")).to_be_visible()
    expect_playing_id(page, clips[0]["video_id"])
    frame = player.locator("iframe")
    expect(frame).to_have_count(1)
    assert frame.evaluate("el => el === window.originalPlayerFrame")
    assert "controls=1" in frame.get_attribute("src")
    box = frame.bounding_box()
    assert box and min(box["width"], box["height"]) >= 200
    query = player.get_by_role("searchbox", name="Search this queue")
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
    expect(options.get_by_role("link", name="AutoPost camera and photos")).to_have_attribute("href", "/f/autopost")
    expect(options.get_by_text("Device models are unavailable in this Mall.")).to_be_visible()
    page.keyboard.press("Escape")
    expect(options).not_to_be_visible()
    expect(player).to_be_visible()
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
    inline.get_by_role("button", name="Expand video").click()
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
    page.goto("https://play.foundups.com/", wait_until="domcontentloaded")
    page.wait_for_url("https://play.foundups.com/?signin=required")
    assert "/member/" in requested
    assert not any(path.endswith("catalog.json") for path in requested)
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
    page.goto("https://play.foundups.com/", wait_until="domcontentloaded")
    page.wait_for_url("https://play.foundups.com/member/")
    expect(page.get_by_role("searchbox", name="Search the Mall")).to_be_visible()
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
    inline = page.get_by_role("region", name="Inline video player")
    expect(inline).to_be_visible()
    expect(video(page, 24)).to_have_attribute("aria-current", "true")
    expect(video(page, 24)).to_be_hidden()
    assert page.evaluate("document.querySelector('.mall-inline-player-slot').nextElementSibling.dataset.index") == "24"
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
    expect(page.get_by_role("dialog", name="Fullscreen video player")).to_be_visible()
    page.evaluate("history.back()")
    expect(page.locator("#videoPlayerFullscreen")).to_be_hidden()
    expect(video(page, 24)).to_be_focused()
    expect(video(page, 24)).to_be_in_viewport()
    assert page.evaluate("document.querySelector('.mall-tile-field-wrapper').scrollTop") > 0
    assert page.url == "https://hpc.foundups.com/member/"

    phone_search = page.locator("#videoScopePhoneDock").get_by_role("searchbox")
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
    inline.get_by_role("button", name="Expand video", exact=True).click()
    expect(page.get_by_role("dialog", name="Fullscreen video player")).to_be_visible()
    page.set_viewport_size({"width":900,"height":844})
    expect(page.locator(".mall-tile")).to_have_count(1)
    assert page.evaluate("document.querySelector('.mall-tile').inert")
    assert page.evaluate("window.phoneContext === document.querySelector('.video-player-stage iframe').contentWindow")
    page.get_by_role("dialog", name="Fullscreen video player").get_by_role("button", name="Back", exact=True).click()
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


if __name__ == "__main__":
    main()
    verify_diagnostics()
    with sync_playwright() as p:
        verify_desktop(p.chromium)
        verify_member_entry(p.chromium)
