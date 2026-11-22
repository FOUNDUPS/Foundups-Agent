"""Independent controlled phone UI checks; no real provider/device claims."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import time
import traceback
from urllib.parse import urlsplit

sys.dont_write_bytecode = True
parser = argparse.ArgumentParser()
parser.add_argument('--root', type=Path, default=Path.cwd())
parser.add_argument('--out', type=Path)
parser.add_argument('--case', action='append', default=[])
parser.add_argument('--include-defensive', action='store_true',
                    help='Run separately reviewed history literal-rendering checks after its defensive source patch is adopted')
args = parser.parse_args()
ROOT = args.root.resolve()
EVIDENCE = Path(os.environ.get('HPC_EVIDENCE_DIR', str(ROOT.parent / 'hpc-phone-ui-evidence'))).resolve()
OUT = args.out.resolve() if args.out else EVIDENCE / 'mall-phone-ui-qa.json'
OUT.parent.mkdir(parents=True, exist_ok=True)
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / 'public/member/tests'))
import mall_scoped_video_browser as fixture
from playwright.sync_api import expect, sync_playwright

REPORT = {
    'provider': 'Existing controlled YT API fixture; all requests intercepted',
    'physical_iPhone': 'UNEXECUTED',
    'candidate_scope': 'Selective pre-Fractal reversible return and navigation/tap core',
    'excluded_source_cases': [
        {'case': 'retained-lens-forward', 'engines': ['chromium', 'webkit'],
         'status': 'NOT_APPLICABLE', 'reason': 'Guest graph/lens prototype excluded'},
        {'case': 'public-nonvideo-retained-face', 'engines': ['chromium', 'webkit'],
         'status': 'NOT_APPLICABLE', 'reason': 'Guest card-face loan prototype excluded'},
    ],
    'separate_defensive_cases': {'case': 'history-literal-rendering',
        'status': 'SELECTED_REQUIRES_REVIEWED_SOURCE' if args.include_defensive or 'history-literal-rendering' in args.case
                  else 'PENDING_SEPARATE_DEFENSIVE_REVIEW',
        'engines': ['chromium', 'webkit']},
    'viewport': {'width': 414, 'height': 896},
    'playwright': importlib.metadata.version('playwright'),
    'root': str(ROOT), 'cases': [], 'started_epoch': time.time(),
}


def hashes():
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT / 'public').rglob('*')) if p.is_file()
            and '/tests/' not in p.as_posix() and '__pycache__' not in p.parts}


def save():
    OUT.write_text(json.dumps(REPORT, indent=2) + '\n', encoding='utf-8')


def assert_true(condition, detail):
    if not condition:
        raise AssertionError(detail)


def make_page(browser, block=False, block_storage=False, silent_start=False, desktop=False, hold_ready=False):
    context = browser.new_context(viewport={'width': 1440, 'height': 900} if desktop else REPORT['viewport'], is_mobile=not desktop,
                                  has_touch=not desktop, service_workers='block',
                                  reduced_motion='reduce')
    init = fixture.provider + ('\nif(window.fixturePlayback)window.fixturePlayback.block=true;' if block else '')
    if block_storage:
        init += """\n(() => {const original=Storage.prototype.setItem;
          Storage.prototype.setItem=function(...args){
            if(this===window.sessionStorage)throw new DOMException('Controlled storage quota failure','QuotaExceededError');
            return original.apply(this,args);
          };})();"""
    if silent_start:
        init += """\nif(window.YT&&window.fixturePlayback){
          const Original=window.YT.Player;
          window.YT.Player=function(...args){
            const api=new Original(...args), play=api.playVideo;
            api.playVideo=()=>{window.fixturePlayback.playAttempts++};
            window.fixturePlayback.releaseSilentStart=()=>{api.playVideo=play};
            return api;
          };
        }"""
    if hold_ready:init += '\nif(window.fixturePlayback)window.fixturePlayback.holdReady=true;'
    context.add_init_script(init)
    context.route('**/*', fixture.route_local)
    page = context.new_page()
    page.set_default_timeout(3500)
    page.set_default_navigation_timeout(8000)
    return context, page


def boot(page, hpc=False):
    page.goto('https://hpc.foundups.com/member/' if hpc else
              'https://play.foundups.com/member/', wait_until='domcontentloaded')
    expect(page.locator('#mallTileField .mall-tile').first).to_be_visible()
    expect(page.locator('.mall-member-search-dock:visible')).to_have_count(1)


def checkpoint(page, name):
    value = page.evaluate("""() => {
      const visible = e => { const s=getComputedStyle(e),r=e.getBoundingClientRect();
        return !e.hidden&&s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0; };
      const docks=[...document.querySelectorAll('.mall-member-search-dock')].filter(visible);
      const dock=docks[0],input=dock?.querySelector('textarea'),r=input?.getBoundingClientRect();
      const add=dock?.querySelector('.mall-search-add'),ar=add?.getBoundingClientRect();
      return {count:docks.length,same:!window.independentDock||dock===window.independentDock,
        inert:!!dock?.closest('[inert]'),inputRect:r?.toJSON(),
        inputHit:r?document.elementFromPoint(r.left+r.width/2,r.top+r.height/2)===input:false,
        sameFrame:!window.independentFrame||document.querySelector('#videoPlayerFullscreen iframe')===window.independentFrame,
        created:window.fixturePlayback.created,state:window.mallVideoPlayer?.getPlaybackSnapshot?.(),
        addRect:ar?.toJSON(),addPosition:add?getComputedStyle(add).position:null,
        modalDock:!!dock?.closest('.video-player-shared-dock-host'),
        scrollWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth};
    }""")
    REPORT.setdefault('checkpoints', []).append({'engine': REPORT['engine'],
        'case': REPORT.get('active_case'), 'name': name, 'value': value})
    assert_true(value['count'] == 1 and value['same'] and not value['inert'],
                {'checkpoint': name, **value})
    assert_true(value['inputHit'], {'checkpoint': name, 'input_obscured': value})
    assert_true(value['scrollWidth'] <= value['clientWidth'] + 1,
                {'checkpoint': name, 'horizontal_overflow': value})
    assert_true(value['addRect']['width'] >= 44 and value['addRect']['height'] >= 44,
                {'checkpoint': name, 'small_add_target': value})
    assert_true(not value['modalDock'] or value['addPosition'] != 'absolute',
                {'checkpoint': name, 'modal_add_left_absolute': value})
    return value


def public_action_layout(page, name):
    value = page.evaluate("""() => {
      const anchor=document.querySelector('#redDogAnchor'),
        dock=anchor.querySelector(':scope > .mall-member-search-dock'),
        dog=anchor.querySelector(':scope > .red-dog-btn'),add=dock.querySelector('.mall-search-add'),
        input=dock.querySelector('.mall-member-search-bar textarea');
      const d=dog.getBoundingClientRect(),a=add.getBoundingClientRect(),i=input.getBoundingClientRect();
      const hit=(e,r)=>e.contains(document.elementFromPoint(r.left+r.width/2,r.top+r.height/2));
      return {dog:d.toJSON(),add:a.toJSON(),input:i.toJSON(),dogHit:hit(dog,d),addHit:hit(add,a),
        inputHit:hit(input,i),expanded:dock.querySelector('form').hasAttribute('data-expanded'),
        viewportWidth:innerWidth,scrollWidth:document.documentElement.scrollWidth};
    }""")
    assert_true(value['dog']['width'] >= 44 and value['dog']['height'] >= 44 and
                value['add']['width'] >= 44 and value['add']['height'] >= 44,
                {'layout': name, 'small_touch_target': value})
    assert_true(value['dog']['x'] + value['dog']['width'] <= value['add']['x'] + 1,
                {'layout': name, 'dog_not_before_add': value})
    assert_true(value['dogHit'] and value['addHit'] and value['inputHit'],
                {'layout': name, 'controls_obscured': value})
    assert_true(value['scrollWidth'] <= value['viewportWidth'] + 1,
                {'layout': name, 'overflow': value})
    return value


def public_header(page):
    boot(page)
    header = page.locator('.mall-header')
    brand = header.locator('.mall-brand-cluster')
    account = header.locator('.mall-self-anchor')
    expect(brand).to_be_visible()
    expect(page.locator('#mallAvatarTrigger')).to_be_visible()
    expect(page.locator('#redDogListening')).to_have_count(1)
    expect(page.locator('#redDogListening')).not_to_be_visible()
    b, a = brand.bounding_box(), account.bounding_box()
    assert_true(abs(b['y'] + b['height']/2 - a['y'] - a['height']/2) <= 12,
                {'header_not_compact_one_row_at414': {'brand': b, 'account': a}})
    page.screenshot(path=str(OUT.with_name(OUT.stem + '-' + REPORT['engine'] + '-public-header.png')))
    layouts = [public_action_layout(page, 'default-414')]
    search = page.locator('.mall-member-search-dock:visible .mall-member-search-bar textarea')
    search.fill('A viewport-sized Mall query for checking wrapped input and both trailing actions. ' * 3)
    expect(page.locator('.mall-member-search-dock:visible .mall-member-search-bar')).to_have_attribute('data-expanded', '')
    layouts.append(public_action_layout(page, 'expanded-query-414'))
    search.fill('')
    expect(page.locator('#mallProjection')).to_have_count(1)
    expect(page.locator('#mallProjection')).not_to_be_visible()
    dock = page.locator('.mall-member-search-dock:visible')
    dock.locator('.mall-search-plus').tap()
    menu = page.locator('dialog.mall-member-search-options[open]')
    expect(menu).to_be_visible()
    expect(menu.locator('#mallProjection')).to_be_visible()
    for name in ['All', 'A-Z', 'Readiness', 'Category']:
        expect(menu.get_by_role('button', name=name, exact=True)).to_be_visible()
    category = menu.get_by_role('button', name='Category', exact=True)
    category.tap()
    expect(category).to_have_class(__import__('re').compile(r'\bactive\b'))
    page.keyboard.press('Escape')
    expect(menu).not_to_be_visible()
    # No physical accessibility-zoom claim: enlarge text and narrow the CSS viewport.
    page.set_viewport_size({'width': 320, 'height': 896})
    page.evaluate("document.documentElement.style.fontSize='24px'")
    expect(page.locator('#mallAvatarTrigger')).to_be_visible()
    expect(page.locator('.mall-brand-cluster')).to_be_visible()
    assert_true(page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),
                'Narrow large-text public header overflows')
    layouts.append(public_action_layout(page, 'large-text-320'))
    search.fill('A viewport-sized Mall query for checking wrapped input and both trailing actions. ' * 3)
    expect(page.locator('.mall-member-search-dock:visible .mall-member-search-bar')).to_have_attribute('data-expanded', '')
    layouts.append(public_action_layout(page, 'expanded-query-large-text-320'))
    page.screenshot(path=str(OUT.with_name(OUT.stem + '-' + REPORT['engine'] + '-public-narrow-query.png')))
    search.fill('')
    page.evaluate("document.documentElement.style.fontSize=''")
    page.set_viewport_size(REPORT['viewport'])
    page.locator('#mallAvatarTrigger').tap()
    page.wait_for_url('https://play.foundups.com/?signin=required')
    return {'header': header.bounding_box() if page.locator('.mall-header').count() else None,
            'branding_account_initial': {'brand': b, 'account': a},
            'filters_moved_once_and_operable': True, 'account_destination': page.url,
            'idle_listening_hidden': True, 'action_layouts': layouts}


def hpc_branding(page):
    boot(page, True)
    banner = page.locator('.mall-hpc-banner-link')
    expect(banner).to_have_attribute('href', 'https://hasan4speaker.com/')
    image = banner.locator('.mall-hpc-banner-image')
    expect(image).to_be_visible()
    expect(image).to_have_attribute('src', '/member/hpc-banner.webp')
    expect(page.locator('.mall-hpc-mall-return')).to_have_attribute('href', 'https://play.foundups.com/')
    expect(page.locator('.mall-hpc-mall-return')).to_contain_text('Play Mall')
    assert_true(page.locator('.mall-hpc-mall-return a, .mall-hpc-banner-link a').count() == 0,
                'Nested conflicting header links')
    build = page.locator('.mall-hpc-banner > .mall-build-label').bounding_box()
    art = image.bounding_box()
    assert_true(build['y'] + build['height'] <= art['y'] + 1, {'build': build, 'art': art})
    assert_true(abs(art['width']/art['height']-1280/353) < .03, {'art_cropped_ratio': art})
    voice = page.locator('#videoScopeVoice')
    expect(voice).to_have_attribute('href', fixture.catalog['hpc']['voice_resource_url'])
    expect(voice).to_contain_text('Voice Your Opinion')
    expect(voice).to_contain_text('Contact Congress')
    expect(voice.locator('svg')).to_have_attribute('aria-hidden', 'true')
    icon, button = voice.locator('svg').bounding_box(), voice.bounding_box()
    assert_true(24 <= icon['width'] <= 28 and button['height'] >= 44,
                {'voice_icon': icon, 'voice_button': button})
    page.screenshot(path=str(OUT.with_name(OUT.stem + '-' + REPORT['engine'] + '-hpc.png')))
    dog = page.locator('#videoScopePhoneDock .mall-search-dog')
    expect(dog).to_have_attribute('href', 'https://play.foundups.com/')
    expect(dog).to_have_attribute('aria-label', 'Return to Play FoundUps Mall')
    assert_true(dog.evaluate("e=>e.tagName==='A'&&!e.hasAttribute('aria-haspopup')"),
                'Unavailable conversation must expose a direct Mall link')
    expect(page.locator('#videoScopePhoneDock .mall-search-plus')).to_be_visible()
    expect(page.locator('dialog[open]')).to_have_count(0)
    dog.tap()
    page.wait_for_url('https://play.foundups.com/member/')
    expect(page.locator('dialog[open]')).to_have_count(0)
    expect(page.locator('#mallTileField .mall-tile').first).to_be_visible()
    return {'art': art, 'build': build, 'voice_icon': icon,
            'mall_return_navigated': page.url, 'external_banner_href': 'https://hasan4speaker.com/'}



def tile_tap_choices(page, hpc):
    boot(page, hpc)
    selector = '.mall-tile[data-video-id="HPC00000000"]'
    if not hpc:
        # Reuse the current FoundUp video lane for tile-setting checks.
        # Separate reversible-return cases qualify the original FoundUp caller.
        page.locator('#mallTileField [data-foundup-id="move2japan"]').tap(position={'x': 25, 'y': 75})
        expect(page.locator('#videoPlayerFullscreen')).to_have_attribute('aria-label', 'Floating video player')
        identity = page.evaluate('window.mallVideoPlayer.getCurrentVideoId()')
        assert_true(__import__('re').fullmatch(r'[A-Za-z0-9_-]{11}', identity) is not None, identity)
        selector = '.mall-tile[data-video-id="' + identity + '"]'
        page.keyboard.press('Escape')
        expect(page.locator('#videoPlayerFullscreen')).not_to_be_visible()
    tile = page.locator(selector)
    expect(tile).to_be_visible()
    dock = page.locator('.mall-member-search-dock:visible')
    dock.locator('.mall-search-plus').tap()
    menu = page.locator('.mall-member-search-options[open]')
    group = menu.get_by_role('group', name='Video', exact=True)
    expect(group).to_be_visible()
    choice = group.locator('[data-video-option="tileTapDestination"]')
    expect(choice).to_have_value('floating')
    assert_true(choice.locator('option').evaluate_all('(es)=>es.map(e=>e.value)') ==
                ['floating', 'wikitube', 'full-video'], 'Missing deliberate tap choices')
    modes = {'floating': 'Floating video player', 'wikitube': 'WikiTube video player',
             'full-video': 'Full Video in app'}
    results = []
    for destination, mode in modes.items():
        if not menu.is_visible():
            dock.locator('.mall-search-plus').tap()
        choice.select_option(destination)
        expect(group.locator('[data-video-option="frameDestination"]')).to_have_value('wikitube')
        menu.get_by_role('button', name='Close', exact=True).click()
        # Keyboard activation shares the tile action; other choices use a pointer.
        if destination == 'wikitube':
            tile.focus()
            tile.press('Enter')
        else:
            tile.tap(position={'x': 25, 'y': 75})
        player = page.locator('#videoPlayerFullscreen')
        expect(player).to_have_attribute('aria-label', mode)
        page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
        assert_true(page.locator('#videoPlayerFullscreen iframe').count() == 1, 'Duplicate provider frame')
        selected = page.evaluate('window.mallStateRestore.getVideoOptions()')
        assert_true(selected['tileTapDestination'] == destination and selected['frameDestination'] == 'wikitube', selected)
        for key in ['pinchOutDestination', 'pinchInDestination', 'swipeUpDestination']:
            assert_true(key not in selected, 'Unconfirmed initial default was seeded: ' + key)
        result = {'destination': destination, 'mode': mode,
                  'activation': 'keyboard' if destination == 'wikitube' else 'pointer'}
        if destination == 'floating':
            page.wait_for_function('window.mallVideoPlayer.getPlaybackSnapshot()?.positionSeconds>=.35')
            before = page.evaluate('({snapshot:window.mallVideoPlayer.getPlaybackSnapshot(),loads:window.fixturePlayback.loadedIds.length,created:window.fixturePlayback.created})')
            page.evaluate('window.independentFrame=document.querySelector("#videoPlayerFullscreen iframe")')
            dock.locator('.mall-search-plus').tap()
            choice.select_option('full-video')
            menu.get_by_role('button', name='Close', exact=True).click()
            tile.focus()
            tile.press('Enter')
            expect(player).to_have_attribute('aria-label', 'Full Video in app')
            after = page.evaluate('({snapshot:window.mallVideoPlayer.getPlaybackSnapshot(),loads:window.fixturePlayback.loadedIds.length,created:window.fixturePlayback.created,sameFrame:document.querySelector("#videoPlayerFullscreen iframe")===window.independentFrame,nativeFullscreen:!!document.fullscreenElement})')
            assert_true(after['loads'] == before['loads'] and after['created'] == before['created'] and after['sameFrame'], {'before': before, 'after': after})
            assert_true(after['snapshot']['positionSeconds'] >= before['snapshot']['positionSeconds'] - .05, {'timestamp_reset': after})
            assert_true(not after['nativeFullscreen'], 'App presentation invoked native fullscreen')
            result['same_clip_transition'] = {'before': before, 'after': after}
        results.append(result)
        page.keyboard.press('Escape')
        expect(player).not_to_be_visible()
        expect(tile).to_be_visible()
    page.reload(wait_until='domcontentloaded')
    expect(page.locator('#mallTileField .mall-tile').first).to_be_visible()
    page.locator('.mall-member-search-dock:visible .mall-search-plus').tap()
    expect(page.locator('.mall-member-search-options[open] [data-video-option="tileTapDestination"]')).to_have_value('full-video')
    return {'choices': results, 'reload_retained': 'full-video', 'unconfirmed_defaults_seeded': False}



def preview_dog_return(page):
    origin = 'https://foundupscom--play-v26-iphone-jxbn78ue.web.app'
    page.goto(origin + '/member/?foundup=hpc', wait_until='domcontentloaded')
    expect(page.locator('#mallTileField .mall-tile').first).to_be_visible()
    dog = page.locator('#videoScopePhoneDock .mall-search-dog')
    expect(dog).to_have_attribute('href', '/member/')
    expect(dog).to_have_attribute('aria-label', 'Return to Play FoundUps Mall')
    expect(page.locator('#videoScopePhoneDock .mall-search-plus')).to_be_visible()
    dog.tap()
    page.wait_for_url(origin + '/member/')
    expect(page.locator('#mallTileField .mall-tile').first).to_be_visible()
    expect(page.locator('dialog[open]')).to_have_count(0)
    return {'origin_preserved': page.url, 'popup': False, 'network': 'intercepted fixture only'}



def history_literal_rendering(page):
    boot(page)
    payload = '<img data-fixture-injected src=x onerror="window.fixtureXss=99">'
    identity = 'quoted" onfocus="window.fixtureXss=98'
    page.evaluate("""({payload,identity})=>{
      window.fixtureXss=0;
      localStorage.setItem('pfmall_watch_history',JSON.stringify([
        {foundupId:identity,videoId:'abc" onmouseover="window.fixtureXss=97',videoIndex:'0" autofocus onfocus="window.fixtureXss=96',title:payload,thumbnail:'x" onerror="window.fixtureXss=95',playbackPosition:67,timestamp:1},
        {foundupId:'hpc',videoId:'HPC00000000',title:'Safe history',playbackPosition:7,timestamp:1}
      ]));
      // Existing presentation-only admission seam, with entirely synthetic data.
      // This does not authenticate an account or exercise real backend admission.
      window.redDog.setDiscoveryAdmission(true); window.redDog.open();
    }""", {'payload': payload, 'identity': identity})
    history = page.locator('[data-reddog-history]')
    expect(history).to_be_visible()
    expect(history.locator('.reddog-history-card')).to_have_count(2)
    expect(history.locator('.reddog-history-title').first).to_have_text(payload)
    expect(history.locator('.reddog-history-card').first).to_have_attribute('data-history-foundup', identity)
    expect(history.locator('.reddog-history-continue-badge').first).to_have_text('Continue at 1:07')
    expect(history.locator('[data-fixture-injected], [onerror], [onfocus], [onmouseover], [autofocus], script')).to_have_count(0)
    assert_true(page.evaluate('window.fixtureXss===0'), 'History payload became executable markup')
    history.get_by_role('button', name='Clear', exact=True).click()
    expect(history.locator('.reddog-history-count')).to_have_text('0')
    expect(history.locator('.reddog-history-empty')).to_be_visible()
    page.evaluate('window.redDog.close(); window.redDog.setDiscoveryAdmission(false)')
    return {'literal_text_and_attributes': True, 'continue_badge_and_clear': True,
            'admission': 'Synthetic presentation flag only; no real account/backend proof'}


def retained_snapshot(page):
    return page.evaluate("""()=>({playback:window.mallVideoPlayer.getPlaybackSnapshot(),
      id:window.mallVideoPlayer.getCurrentVideoId(),length:window.mallVideoPlayer.getQueueLength(),
      query:window.mallVideoPlayer.getQueueQuery(),created:window.fixturePlayback.created,
      loads:window.fixturePlayback.loadedIds.length,plays:window.fixturePlayback.plays,
      sameFrame:document.querySelector('#videoPlayerFullscreen iframe')===window.returnFixtureFrame,
      mode:window.mallVideoPlayer.getMode?.(),hidden:window.mallVideoPlayer.isMallHidden?.(),
      field:window.mallTileField.getFieldScope(),projection:window.mallTileField.getProjection(),
      scroll:document.querySelector('.mall-tile-field-wrapper').scrollTop,
      scrollLeft:document.querySelector('.mall-tile-field-wrapper').scrollLeft,
      focus:document.activeElement?.dataset?.videoId||document.activeElement?.dataset?.foundupId,
      bodyOverflow:document.body.style.overflow,memberInert:document.querySelector('#memberArea').inert,
      width:innerWidth,touch:matchMedia('(pointer:coarse)').matches})""")


def activate_visible_tile(page, tile, desktop):
    # Coordinate activation avoids an automation-driven scroll changing the
    # caller we are verifying. It still sends real pointer input to the app tile.
    tile.evaluate('e=>e.focus({preventScroll:true})')
    b=tile.bounding_box(); field=page.locator('.mall-tile-field-wrapper').bounding_box()
    y=(max(b['y'],field['y'])+min(b['y']+b['height'],field['y']+field['height']))/2
    x=b['x']+b['width']/2
    assert_true(y>=field['y'] and y<field['y']+field['height'], {'tile':b,'field':field})
    (page.mouse.click if desktop else page.touchscreen.tap)(x,y)


def reopen_retained_from_caller(page, hpc, desktop=False):
    video_id=page.evaluate('window.mallVideoPlayer.getCurrentVideoId()')
    selector='.mall-tile[data-video-id="'+video_id+'"]' if hpc else '#mallTileField [data-foundup-id="move2japan"]'
    tile=page.locator(selector)
    expect(tile).to_be_visible()
    activate_visible_tile(page,tile,desktop)
    return tile


def reversible_mall_return(page, hpc, desktop=False, lane=False):
    page.goto('https://hpc.foundups.com/member/' if hpc else 'https://play.foundups.com/member/',wait_until='domcontentloaded')
    if hpc and desktop:
        # Approved desktop entry opens TV. Deliberately return through its owner
        # before choosing a scrolled grid caller for this transition test.
        page.wait_for_function('window.mallVideoPlayer?.isOpen()')
        assert_true(page.evaluate('window.mallVideoPlayer.isTheater()'), 'Desktop entry did not open TV')
        # Exercise the retained READY theater, not the separate unready-disposal
        # path. Its hidden theater class must no longer hide the actual grid.
        page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
        page.evaluate('window.readyTheaterFrame=document.querySelector("#videoPlayerFullscreen iframe")')
        page.evaluate('window.mallVideoPlayer.returnToMall()')
        page.wait_for_function("window.mallVideoPlayer.isMallHidden()&&window.mallVideoPlayer.getPlaybackSnapshot()?.state==='paused'")
        assert_true(page.evaluate('window.readyTheaterFrame===document.querySelector("#videoPlayerFullscreen iframe")'),
                    'Ready desktop theater return replaced its provider')
    expect(page.locator('#mallTileField .mall-tile').first).to_be_visible()
    page.evaluate("window.mallStateRestore.setVideoOptions({tileTapDestination:'full-video',collapseDestination:'mall'})")
    if lane:
        page.evaluate("window.mallStateRestore.setVideoOptions({tileTapDestination:'floating'})")
        page.locator('#mallTileField [data-foundup-id="move2japan"]').click()
        page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
        # Keep the floating lane's pager alive while materializing its caller.
        for _ in range(10):
            if page.locator('#mallTileField .mall-tile[data-video-id]').count() >= 24:break
            page.get_by_role('button',name='Load more videos',exact=True).evaluate('(e)=>e.click()')
            page.wait_for_timeout(40)
        tile=page.locator('#mallTileField .mall-tile[data-video-id]').nth(20)
        expect(tile).to_be_visible();tile.scroll_into_view_if_needed()
        page.evaluate("window.mallStateRestore.setVideoOptions({tileTapDestination:'full-video'})")
    elif hpc:
        selector='.mall-tile[data-video-id="HPC00000020"]'
        for _ in range(8):
            if page.locator(selector).count(): break
            # Setup only: activate existing pagination without automation scroll
            # racing the field's own progressive materialization in WebKit.
            page.get_by_role('button',name='Load more videos',exact=True).evaluate('(e)=>e.click()')
            page.wait_for_timeout(30)
        tile=page.locator(selector);expect(tile).to_be_visible();tile.scroll_into_view_if_needed()
    else:
        # Use the existing public catalog and its real pagination owner.
        # No guest graph, synthetic hierarchy or extra browse selector is loaded.
        for _ in range(8):
            if page.evaluate('document.querySelector(".mall-tile-field-wrapper").scrollHeight>document.querySelector(".mall-tile-field-wrapper").clientHeight+50'):break
            # The existing observer may replace the tail while an automation
            # click scrolls it into view. Activate the extant control atomically.
            if not page.evaluate("""()=>{const b=[...document.querySelectorAll('.mall-video-grid-tail button')]
              .find(e=>e.textContent.trim()==='Load more cards');if(!b)return false;b.click();return true;}"""):break
            page.wait_for_timeout(40)
        tile=page.locator('#mallTileField [data-foundup-id="move2japan"]')
        expect(tile).to_be_visible()
        page.evaluate('document.querySelector(".mall-tile-field-wrapper").scrollTop=36')
    initial=retained_snapshot(page)
    if hpc or lane:
        assert_true(initial['scroll']>0 or initial['scrollLeft']>0, {'nonzero_caller_scroll_required':initial})
    # This fixture's Root collection can fit the viewport. Zero is its actual
    # caller position; the separate explicit-lane case requires nonzero scroll.
    caller_id=tile.get_attribute('data-video-id') if hpc or lane else 'move2japan'
    activate_visible_tile(page,tile,desktop)
    player=page.locator('#videoPlayerFullscreen')
    expect(player).to_have_attribute('aria-label','Full Video in app')
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    page.wait_for_function('window.mallVideoPlayer.getPlaybackSnapshot()?.positionSeconds>=.35')
    page.evaluate("window.returnFixtureFrame=document.querySelector('#videoPlayerFullscreen iframe')")
    # A queue query has a different owner from the originating field query.
    dock=page.locator('.mall-member-search-dock:visible .mall-member-search-bar textarea')
    expect(page.locator('.mall-member-search-dock:visible')).to_have_count(1)
    dock.fill('Fixture' if hpc else 'retained queue probe')
    dock.press('Enter')
    before=retained_snapshot(page)
    player.locator('[data-action="float"]').click()
    page.wait_for_function('window.mallVideoPlayer.isMallHidden()')
    expect(player).not_to_be_visible()
    after=retained_snapshot(page)
    assert_true(after['mode']=='mall' and after['sameFrame'] and after['created']==before['created'] and after['loads']==before['loads'], {'before':before,'after':after})
    assert_true(after['id']==before['id'] and after['length']==before['length'] and after['query']==before['query'], {'lost_session':after,'before':before})
    assert_true(not after['memberInert'] and after['bodyOverflow']!='hidden', after)
    assert_true(abs(after['scroll']-initial['scroll'])<=2 and abs(after['scrollLeft']-initial['scrollLeft'])<=2 and after['focus']==caller_id, {'caller':initial,'returned':after})
    expect(page.locator('#videoPlayerFullscreen iframe')).to_have_count(1)
    page.set_viewport_size({'width':850,'height':900} if desktop else {'width':896,'height':414})
    page.wait_for_timeout(50)
    rotated=retained_snapshot(page)
    assert_true(rotated['hidden'] and rotated['sameFrame'] and rotated['id']==before['id'], {'hidden_resize_revealed_or_replaced':rotated})
    page.set_viewport_size({'width':1440,'height':900} if desktop else REPORT['viewport'])
    page.wait_for_timeout(50)
    assert_true(page.evaluate('window.mallVideoPlayer.isMallHidden()'),'Restoring viewport revealed the hidden session')
    page.evaluate('window.fixturePlayback.forcePlaying()')
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='paused'")
    hidden_before=retained_snapshot(page)
    page.wait_for_timeout(120)
    hidden_after=retained_snapshot(page)
    assert_true(abs(hidden_after['playback']['positionSeconds']-hidden_before['playback']['positionSeconds'])<.04, {'hidden_time_advanced':hidden_after})
    page.evaluate('window.fixturePlayback.finishCurrent()')
    assert_true(retained_snapshot(page)['id']==before['id'],'Hidden ended event advanced the queue')
    # Native browser history is reversible with the same paused provider.
    page.go_forward(wait_until='domcontentloaded')
    expect(player).to_be_visible()
    forward=retained_snapshot(page)
    assert_true(forward['sameFrame'] and forward['id']==before['id'] and forward['loads']==before['loads'] and forward['query']==before['query'] and forward['length']==before['length'], forward)
    page.go_back(wait_until='domcontentloaded')
    page.wait_for_function('window.mallVideoPlayer.isMallHidden()')
    reopen_retained_from_caller(page,hpc or lane,desktop)
    expect(player).to_have_attribute('aria-label','Full Video in app')
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    resumed=retained_snapshot(page)
    assert_true(resumed['sameFrame'] and resumed['id']==before['id'] and resumed['loads']==before['loads'] and resumed['query']==before['query'] and resumed['length']==before['length'], {'resume':resumed})
    assert_true(resumed['playback']['positionSeconds']>=before['playback']['positionSeconds']-.05, {'resume_reset_time':resumed})
    player.locator('[data-action="back"]').click()
    expect(player).not_to_be_visible()
    expect(player.locator('iframe')).to_have_count(0)
    assert_true(page.evaluate('window.mallVideoPlayer.getQueueLength()===0'),'Final Close retained live resources')
    if hpc and desktop:
        page.set_viewport_size({'width':850,'height':900})
        page.set_viewport_size({'width':1440,'height':900})
        page.wait_for_timeout(80)
        assert_true(page.evaluate('!window.mallVideoPlayer.isOpen()'),'Resize resurrected explicitly closed playback')
        tile.scroll_into_view_if_needed();activate_visible_tile(page,tile,desktop)
        page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
        player.locator('[data-action="back"]').click()
        expect(player.locator('iframe')).to_have_count(0)

    return {'caller':initial,'active':before,'returned':after,'forward':forward,'resumed':resumed,
            'hidden_paused':True,'explicit_close_disposed':True,'desktop':desktop,
            'root_scroll_may_fit':not hpc and not lane,'explicit_lane_origin':lane}



def retained_pending_page(page, close_instead=False):
    held=[]
    pattern='**/member/discovery/*/videos/move2japan/catalog/0001.json'
    page.route(pattern, lambda route: held.append(route))
    boot(page)
    page.evaluate("window.mallStateRestore.setVideoOptions({tileTapDestination:'floating',collapseDestination:'mall'})")
    root=page.locator('#mallTileField [data-foundup-id="move2japan"]')
    root.tap(position={'x':25,'y':75})
    player=page.locator('#videoPlayerFullscreen')
    expect(player).to_have_attribute('aria-label','Floating video player')
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    length=page.evaluate('window.mallVideoPlayer.getQueueLength()')
    assert_true(length==6, {'fixture_initial_page_length':length})
    page.evaluate('window.mallVideoPlayer.goToVideo(window.mallVideoPlayer.getQueueLength()-1)')
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    page.evaluate('window.fixturePlayback.finishCurrent()')
    for _ in range(100):
        if held:break
        page.wait_for_timeout(10)
    assert_true(len(held)==1, {'one_pending_selected_page_required':len(held)})
    request_path=urlsplit(held[0].request.url).path
    source=(fixture.public/request_path.lstrip('/')).resolve()
    assert_true(source.is_relative_to(fixture.public), 'Pending fixture escaped public assets')
    batch=json.loads(source.read_text(encoding='utf-8'))['items']
    assert_true(bool(batch), 'Pending fixture page is empty')
    page.evaluate("window.returnFixtureFrame=document.querySelector('#videoPlayerFullscreen iframe');window.mallVideoPlayer.openFullVideo()")
    expect(player).to_have_attribute('aria-label','Full Video in app')
    before=retained_snapshot(page)
    if close_instead:
        player.locator('[data-action="back"]').click()
        expect(player).not_to_be_visible()
        expect(player.locator('iframe')).to_have_count(0)
    else:
        player.locator('[data-action="float"]').click()
        page.wait_for_function('window.mallVideoPlayer.isMallHidden()')
        expect(root).to_be_visible()
    route=held.pop()
    try:fixture.route_local(route)
    except Exception:
        if not close_instead:raise
        # Explicit Close aborted this request; a late route has no live consumer.
    if close_instead:
        page.wait_for_timeout(80)
        assert_true(page.evaluate('!window.mallVideoPlayer.isOpen()&&window.mallVideoPlayer.getQueueLength()===0'), 'Late page resurrected a closed session')
        expect(player.locator('iframe')).to_have_count(0)
        return {'pending_request':request_path,'explicit_close_disposed':True,'late_page_cannot_reopen_player':True,
                'field_pager':'Existing selected-field owner may complete its bounded page'}
    page.wait_for_function('n=>window.mallVideoPlayer.getQueueLength()===n',arg=length+len(batch))
    hidden=retained_snapshot(page)
    assert_true(hidden['sameFrame'] and hidden['id']==before['id'] and hidden['loads']==before['loads'] and hidden['plays']==before['plays'], {'pending_advanced_hidden_session':hidden,'before':before})
    expect(root).to_be_visible()
    activate_visible_tile(page,root,False)
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    resumed=retained_snapshot(page)
    assert_true(resumed['sameFrame'] and resumed['length']==length+len(batch) and resumed['id']==before['id'], resumed)
    player.locator('[data-action="expand"]').click()
    player.locator('[data-action="next"]').click()
    page.wait_for_function('id=>window.mallVideoPlayer.getCurrentVideoId()===id',arg=batch[0]['video_id'])
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    assert_true(page.evaluate('document.querySelector("#videoPlayerFullscreen iframe")===window.returnFixtureFrame'),'Pending-page continuation recreated the provider')
    player.locator('[data-action="back"]').click()
    expect(player.locator('iframe')).to_have_count(0)
    return {'pending_request':request_path,'before':before,'hidden':hidden,'resumed':resumed,
            'first_new_clip':batch[0]['video_id'],'page_appended_once':True,'same_provider':True}


def selected_lane_close_reopen_paging(page):
    requests=[]
    page.on('request',lambda request:requests.append(request.url)
            if '/videos/move2japan/catalog/0001.json' in request.url else None)
    boot(page)
    page.evaluate("window.mallStateRestore.setVideoOptions({tileTapDestination:'floating'})")
    page.locator('#mallTileField [data-foundup-id="move2japan"]').tap(position={'x':25,'y':75})
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    initial=page.evaluate('window.mallVideoPlayer.getQueueLength()')
    assert_true(initial==6,{'fixture_initial_page':initial})
    player=page.locator('#videoPlayerFullscreen')
    player.locator('[data-action="back"]').click()
    expect(player.locator('iframe')).to_have_count(0)
    assert_true(page.evaluate('!window.mallVideoPlayer.isOpen()&&window.mallVideoPlayer.getQueueLength()===0'),
                'Final Close retained player queue')
    page.locator('#mallTileField .mall-tile[data-video-id]').first.tap(position={'x':25,'y':75})
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    page.evaluate('window.mallVideoPlayer.goToVideo(window.mallVideoPlayer.getQueueLength()-1)')
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    last=page.evaluate('window.mallVideoPlayer.getCurrentVideoId()')
    page.evaluate('window.fixturePlayback.finishCurrent()')
    page.wait_for_function('(old)=>window.mallVideoPlayer.getCurrentVideoId()!==old&&window.mallVideoPlayer.getPlaybackSnapshot()?.state===\'playing\'',arg=last)
    assert_true(len(requests)==1,{'next_page_requests':requests})
    after=page.evaluate('({id:window.mallVideoPlayer.getCurrentVideoId(),length:window.mallVideoPlayer.getQueueLength(),created:window.fixturePlayback.created,destroyed:window.fixturePlayback.destroyed})')
    assert_true(after['length']>initial and after['created']==2 and after['destroyed']==1,after)
    expect(player.locator('iframe')).to_have_count(1)
    player.locator('[data-action="back"]').click()
    expect(player.locator('iframe')).to_have_count(0)
    return {'next_page_requests':requests,'previous_last_clip':last,'continued':after,
            'scope':'Controlled selected-field continuation after final player Close'}


def early_repeated_selection(page, hpc):
    boot(page,hpc)
    page.evaluate("window.fixturePlayback.holdReady=true;window.mallStateRestore.setVideoOptions({tileTapDestination:'floating'})")
    first=page.locator('.mall-tile[data-video-id="HPC00000000"]') if hpc else page.locator('#mallTileField [data-foundup-id="move2japan"]')
    first.tap(position={'x':25,'y':75})
    page.wait_for_function('window.fixturePlayback.created===1')
    video_id=page.evaluate('window.mallVideoPlayer.getCurrentVideoId()')
    tile=page.locator('.mall-tile[data-video-id="'+video_id+'"]')
    tile.focus();tile.press('Enter')
    page.wait_for_timeout(70)
    page.evaluate('window.fixturePlayback.holdReady=false;window.fixturePlayback.deliverReady()')
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    expect(tile).to_have_attribute('aria-current','true')
    if not hpc:
        assert_true(page.locator('.mall-tile-field-wrapper').evaluate("e=>e.classList.contains('member-inline-open')"),'Early replacement lost active presentation')
    # Fixed HPC uses scoped markers, not member-inline-open.
    if not hpc:
        page.evaluate('window.mallVideoPlayer.goToVideo(window.mallVideoPlayer.getQueueLength()-1);window.fixturePlayback.finishCurrent()')
        page.wait_for_function('window.mallVideoPlayer.getQueueLength()>=12')
    created=page.evaluate('window.fixturePlayback.created')
    page.locator('#videoPlayerFullscreen [data-action="back"]').click()
    expect(page.locator('#videoPlayerFullscreen iframe')).to_have_count(0)
    return {'provider_created_before_ready':created,'active_marker':True,'pending_pager_preserved':not hpc}


def retained_history_reentry(page):
    boot(page)
    page.locator('#mallTileField [data-foundup-id="move2japan"]').tap(position={'x':25,'y':75})
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    page.wait_for_function('window.mallVideoPlayer.getPlaybackSnapshot()?.positionSeconds>=.35')
    page.evaluate("window.returnFixtureFrame=document.querySelector('#videoPlayerFullscreen iframe');window.mallVideoPlayer.returnToMall()")
    page.wait_for_function('window.mallVideoPlayer.isMallHidden()')
    identity=page.evaluate('window.mallVideoPlayer.getCurrentVideoId()')
    page.evaluate("""()=>{
      // Synthetic presentation admission; this is not an account/auth test.
      window.redDog.setDiscoveryAdmission(true);
      window.redDog.setFoundUps(window.mallTileField.getLoadedCatalog());window.redDog.open();
    }""")
    card=page.locator('[data-reddog-history] .reddog-history-card').first
    expect(card).to_be_visible();card.click()
    expect(page.locator('#videoPlayerFullscreen')).to_be_visible()
    page.wait_for_function('!window.mallVideoPlayer.isMallHidden()')
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    resumed=retained_snapshot(page)
    assert_true(resumed['sameFrame'] and resumed['id']==identity,resumed)
    page.evaluate('window.mallVideoPlayer.returnToMall()')
    page.wait_for_function('window.mallVideoPlayer.isMallHidden()')
    assert_true(retained_snapshot(page)['focus']=='move2japan','History reuse lost caller callbacks')
    page.evaluate('window.mallVideoPlayer.close();window.redDog.setDiscoveryAdmission(false)')
    return {'resumed':resumed,'original_caller_restored':True,'real_account_auth':'UNEXECUTED'}


def unready_mall_return_stays_closed(page):
    page.goto('https://hpc.foundups.com/member/',wait_until='domcontentloaded')
    page.wait_for_function('window.fixturePlayback.created===1')
    assert_true(page.evaluate("window.mallVideoPlayer.getPlaybackSnapshot()?.state!=='playing'"),'READY was not held')
    page.evaluate('window.mallVideoPlayer.setTheater(false);window.mallVideoPlayer.openFullVideo()')
    player=page.locator('#videoPlayerFullscreen')
    expect(player).to_have_attribute('aria-label','Full Video in app')
    player.locator('[data-action="float"]').click()
    expect(player.locator('iframe')).to_have_count(0)
    assert_true(page.evaluate('!window.mallVideoPlayer.isOpen()&&window.mallVideoPlayer.getQueueLength()===0'),'Unready return retained an unsafe provider')
    event=page.evaluate('window.fixturePlayback.events.at(-1)')
    assert_true(event['state']=='continuity-unavailable' and event['retained'] is False,event)
    page.set_viewport_size({'width':850,'height':900})
    page.set_viewport_size({'width':1440,'height':900})
    page.wait_for_timeout(80)
    assert_true(page.evaluate('!window.mallVideoPlayer.isOpen()&&window.fixturePlayback.created===1'),'Resize restarted cancelled playback')
    page.evaluate('window.fixturePlayback.holdReady=false')
    tile=page.locator('.mall-tile[data-video-id="HPC00000000"]')
    expect(tile).to_be_visible();activate_visible_tile(page,tile,True)
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    player.locator('[data-action="back"]').click()
    expect(player.locator('iframe')).to_have_count(0)
    return {'unready_disposed':True,'resize_stayed_closed':True,'deliberate_reopen':True,'event':event}


def borrowed_queue_keeps_mall_query(page, desktop=False):
    boot(page)
    page.evaluate("window.loanFixtureDock=document.querySelector('.mall-member-search-dock:not([hidden])');window.mallStateRestore.setVideoOptions({tileTapDestination:'full-video'})")
    mall_input=page.locator('.mall-member-search-dock:visible textarea')
    mall_input.fill('move2japan');mall_input.press('Enter')
    tile=page.locator('#mallTileField [data-foundup-id="move2japan"]')
    expect(tile).to_be_visible()
    scope=page.evaluate('window.mallTileField.getFieldScope()')
    assert_true(scope['type']=='query',scope)
    activate_visible_tile(page,tile,desktop)
    expect(page.locator('#videoPlayerFullscreen')).to_have_attribute('aria-label','Full Video in app')
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    expect(page.locator('.mall-member-search-dock:visible')).to_have_count(1)
    queue=page.get_by_role('textbox',name='Search this queue',exact=True)
    queue.fill('queue probe');queue.press('Enter');queue.fill('');queue.press('Enter')
    assert_true(page.evaluate('window.mallTileField.getFieldScope()')==scope,'Clearing loaned queue search cleared the Mall query')
    page.evaluate('window.mallVideoPlayer.returnToMall()')
    page.wait_for_function('window.mallVideoPlayer.isMallHidden()')
    expect(page.locator('.mall-member-search-dock:visible')).to_have_count(1)
    expect(page.get_by_role('textbox',name='Search the Mall',exact=True)).to_have_value('move2japan')
    assert_true(page.evaluate("document.querySelector('.mall-member-search-dock:not([hidden])')===window.loanFixtureDock"),'Return replaced the shared dock')
    assert_true(page.evaluate('window.mallTileField.getFieldScope()')==scope,'Returning changed the Mall query')
    page.evaluate('window.mallVideoPlayer.close()')
    return {'caller_scope':scope,'queue_query_cleared_only':True,'same_dock':True,'desktop':desktop}


def unsupported_provider_return(page):
    boot(page)
    page.evaluate("""()=>window.mallVideoPlayer.open('opaque-fixture',[
      {video_id:'opaque-test',title:'Opaque fixture',embed_url:'https://example.invalid/embed'}
    ],0,{floating:true,autoplay:false})""")
    expect(page.locator('#videoPlayerFullscreen iframe')).to_have_count(1)
    result=page.evaluate('window.mallVideoPlayer.returnToMall()')
    assert_true(result is False,'Opaque provider claimed retained continuity')
    expect(page.locator('#videoPlayerFullscreen iframe')).to_have_count(0)
    assert_true(page.evaluate('!window.mallVideoPlayer.isOpen()&&!window.mallVideoPlayer.isMallHidden()&&window.mallVideoPlayer.getQueueLength()===0'),'Unpausable provider remained retained')
    event=page.evaluate('window.fixturePlayback.events.at(-1)')
    assert_true(event['state']=='continuity-unavailable' and event['retained'] is False,event)
    return {'result':result,'frame_disposed':True,'event':event,'media_delivery':'INTERCEPTED; no real opaque-provider audio claim'}


def blocked_account_storage(page):
    boot(page)
    initial = page.url
    page.locator('#mallAvatarTrigger').tap()
    status = page.locator('#mallAccountReturnStatus[role="alert"]')
    expect(status).to_be_visible()
    expect(status).to_contain_text('safe account return could not be saved')
    assert_true(page.url == initial, {'unexpected_navigation': page.url})
    expect(page.locator('#mallTileField .mall-tile').first).to_be_visible()
    assert_true(page.evaluate('window.mallStateRestore.peekAdmissionIntent()===null'),
                'Failed handoff retained an admission intent')
    assert_true(not page.locator('#accountPlane').evaluate("e=>e.classList.contains('open')"),
                'Blocked account action opened conversation drawer')
    return {'no_navigation': True, 'visible_safe_return_error': status.inner_text(),
            'no_admission_intent': True}


def dock_flow(page, hpc):
    boot(page, hpc)
    page.evaluate("window.independentDock=document.querySelector('.mall-member-search-dock:not([hidden])')")
    if hpc:
        query = page.locator('#videoScopePhoneDock .mall-member-search-bar textarea')
        query.fill('Fixture')
        query.press('Enter')
        page.locator('.mall-tile[data-video-id="HPC00000000"]').tap(position={'x': 25, 'y': 75})
    else:
        page.locator('#mallTileField [data-foundup-id="move2japan"]').tap(position={'x': 30, 'y': 50})
    player = page.locator('#videoPlayerFullscreen')
    expect(player).to_have_attribute('aria-label', 'Floating video player')
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    page.evaluate("window.independentFrame=document.querySelector('#videoPlayerFullscreen iframe')")
    points = [checkpoint(page, 'floating')]
    expect(player.get_by_role('button', name='Play video', exact=True)).not_to_be_visible()
    for cycle in range(2):
        player.get_by_role('button', name='Open WikiTube', exact=True).tap()
        expect(player).to_have_attribute('aria-label', 'WikiTube video player')
        points.append(checkpoint(page, 'expanded-' + str(cycle)))
        queue = page.locator('.mall-member-search-dock:visible .mall-member-search-bar textarea')
        expect(queue).to_have_attribute('aria-label', 'Search this queue')
        queue.fill('nonmatching queue query')
        queue.press('Enter')
        assert_true(page.evaluate("document.querySelector('#videoPlayerFullscreen iframe')===window.independentFrame"),
                    'Queue search replaced provider frame')
        page.locator('.mall-member-search-dock:visible .mall-search-plus').tap()
        expect(page.locator('.mall-member-search-options[open]')).to_be_visible()
        page.keyboard.press('Escape')
        expect(page.locator('.mall-member-search-options[open]')).to_have_count(0)
        expect(player).to_be_visible()
        queue.fill('')
        queue.press('Enter')
        player.locator('[data-action="float"]').tap()
        page.wait_for_function('window.mallVideoPlayer.isMallHidden()')
        expect(player).not_to_be_visible()
        reopen_retained_from_caller(page, hpc)
        expect(player).to_have_attribute('aria-label', 'Floating video player')
        points.append(checkpoint(page, 'restored-' + str(cycle)))
        if hpc:
            expect(page.locator('#videoScopePhoneDock .mall-member-search-bar textarea')).to_have_value('Fixture')
    assert_true(all(p['sameFrame'] and p['created'] == 1 for p in points), points)
    # Exercise the existing options through UI, including Full Video -> WikiTube.
    page.locator('.mall-member-search-dock:visible .mall-search-plus').tap()
    menu = page.locator('.mall-member-search-options[open]')
    menu.locator('[data-video-option="frameDestination"]').select_option('full-video')
    menu.locator('[data-video-option="collapseDestination"]').select_option('wikitube')
    # A native select can consume Escape; focus a dialog control first.
    menu.get_by_role('button', name='Close', exact=True).focus()
    page.keyboard.press('Escape')
    expect(menu).not_to_be_visible()
    player.locator('[data-action="expand"]').tap()
    expect(player).to_have_attribute('aria-label', 'Full Video in app')
    expect(player.locator('.video-player-queue-rail')).not_to_be_visible()
    points.append(checkpoint(page, 'full-video'))
    player.locator('[data-action="float"]').tap()
    expect(player).to_have_attribute('aria-label', 'WikiTube video player')
    points.append(checkpoint(page, 'full-video-to-wikitube'))
    player.locator('[data-action="float"]').tap()
    page.wait_for_function('window.mallVideoPlayer.isMallHidden()')
    expect(player).not_to_be_visible()
    reopen_retained_from_caller(page, hpc)
    expect(player).to_have_attribute('aria-label', 'Floating video player')
    points.append(checkpoint(page, 'full-video-restored'))
    assert_true(all(p['sameFrame'] and p['created'] == 1 for p in points), points)
    page.locator('.mall-member-search-dock:visible .mall-search-plus').tap()
    menu = page.locator('.mall-member-search-options[open]')
    menu.locator('[data-video-option="frameDestination"]').select_option('wikitube')
    menu.get_by_role('button', name='Close', exact=True).focus()
    page.keyboard.press('Escape')
    expect(menu).not_to_be_visible()
    player.locator('[data-action="expand"]').tap()
    if hpc:
        # Only the existing fixed-HPC scope pushes a player history entry.
        page.go_back(wait_until='domcontentloaded')
    else:
        # Public browsing preserves its existing native history. Use its UI Back.
        player.locator('[data-action="back"]').tap()
    expect(player).not_to_be_visible()
    final = checkpoint(page, 'closed')
    if hpc:
        assert_true(page.evaluate('window.mallVideoPlayer.isMallHidden()'),'Browser Back discarded the scoped session')
        expect(player.locator('iframe')).to_have_count(1)
        page.evaluate('window.mallVideoPlayer.close()')
    expect(player.locator('iframe')).to_have_count(0)
    return {'checkpoints': points, 'closed': final,
            'provider_fixture_frame_reused': True, 'history_back': hpc,
            'player_back': not hpc}


def blocked_recovery(page):
    boot(page, True)
    page.locator('.mall-tile[data-video-id="HPC00000000"]').tap(position={'x': 25, 'y': 75})
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='autoplay-blocked'")
    player = page.locator('#videoPlayerFullscreen')
    play = player.get_by_role('button', name='Play video', exact=True)
    expect(play).to_be_visible()
    frame = player.locator('iframe')
    expect(frame).to_have_count(1)
    page.evaluate("window.independentFrame=document.querySelector('#videoPlayerFullscreen iframe');window.fixturePlayback.block=false")
    play.tap()
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    expect(play).not_to_be_visible()
    assert_true(page.evaluate("document.querySelector('#videoPlayerFullscreen iframe')===window.independentFrame"),
                'Manual recovery replaced provider frame')
    return {'positive_blocked_fallback': True, 'successful_fallback_hidden': True,
            'fixture_snapshot': page.evaluate('window.mallVideoPlayer.getPlaybackSnapshot()')}


def silent_start_unknown(page):
    boot(page, True)
    page.locator('.mall-tile[data-video-id="HPC00000000"]').tap(position={'x': 25, 'y': 75})
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='provider-unknown'", timeout=7000)
    player = page.locator('#videoPlayerFullscreen')
    snapshot = page.evaluate('window.mallVideoPlayer.getPlaybackSnapshot()')
    message = player.locator('.video-player-status').inner_text()
    assert_true('blocked' not in message.lower(), {'snapshot': snapshot, 'rendered_message': message})
    play = player.get_by_role('button', name='Play video', exact=True)
    expect(play).to_be_visible()
    page.evaluate("window.independentFrame=document.querySelector('#videoPlayerFullscreen iframe');window.fixturePlayback.releaseSilentStart()")
    play.tap()
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    expect(play).not_to_be_visible()
    assert_true(page.evaluate("document.querySelector('#videoPlayerFullscreen iframe')===window.independentFrame"),
                'Unknown-start manual recovery replaced provider frame')
    return {'silent_start': snapshot, 'rendered_message': message, 'manual_recovery': True,
            'qualification': 'Synthetic API emitted READY then remained silent; no observed browser onAutoplayBlocked event.'}


def run_case(browser, name, fn, block=False, block_storage=False, silent_start=False, desktop=False, hold_ready=False):
    if args.case and name not in args.case:return
    REPORT['active_case'] = name
    context, page = make_page(browser, block, block_storage, silent_start, desktop, hold_ready)
    row = {'engine': REPORT['engine'], 'case': name, 'passed': False}
    page_errors=[]
    page.on('pageerror',lambda error:page_errors.append(str(error)))
    graph_requests=[]
    page.on('request',lambda request:graph_requests.append(request.url) if '/pfmall/tile-graph/' in urlsplit(request.url).path else None)
    try:
        row['evidence'] = fn(page)
        assert_true(not page_errors, {'page_errors':page_errors})
        assert_true(not graph_requests, {'protected_graph_requests':graph_requests})
        row['passed'] = True
    except Exception as exc:
        row['error'] = str(exc)
        row['traceback'] = traceback.format_exc()
        row['url'] = page.url
        try:
            row['diagnostic'] = page.evaluate("""() => ({
              playerClass:document.querySelector('#videoPlayerFullscreen')?.className,
              playerHidden:document.querySelector('#videoPlayerFullscreen')?.hidden,
              state:window.mallVideoPlayer?.getPlaybackSnapshot?.(),
              dialogs:[...document.querySelectorAll('dialog[open]')].map(x=>x.getAttribute('aria-label')),
              accountPlane:document.querySelector('#accountPlane')?.className,
              focused:document.activeElement?.outerHTML?.slice(0,400)})""")
        except Exception:
            pass
        try:
            page.screenshot(path=str(OUT.with_name(OUT.stem + '-' + REPORT['engine'] + '-' + name + '-failure.png')))
        except Exception:
            pass
    finally:
        row['page_errors']=page_errors
        row['protected_graph_requests']=graph_requests
        REPORT['cases'].append(row)
        context.close()
        save()
        print(json.dumps({'engine': row['engine'], 'case': name, 'passed': row['passed'],
                          'error': row.get('error', '')[:240]}), flush=True)


REPORT['source_sha256_before'] = hashes()
save()
try:
    with sync_playwright() as playwright:
        for name in ['chromium', 'webkit']:
            REPORT['engine'] = name
            browser = getattr(playwright, name).launch()
            try:
                run_case(browser, 'public-header-filters-account', public_header)
                run_case(browser, 'account-blocked-storage', blocked_account_storage, block_storage=True)
                run_case(browser, 'hpc-banner-voice-navigation', hpc_branding)
                run_case(browser, 'hpc-preview-dog-return', preview_dog_return)
                if args.include_defensive or 'history-literal-rendering' in args.case:
                    run_case(browser, 'history-literal-rendering', history_literal_rendering)
                run_case(browser, 'pending-page-retained-return', retained_pending_page)
                run_case(browser, 'pending-page-final-close', lambda page: retained_pending_page(page, True))
                run_case(browser, 'selected-lane-close-reopen-paging', selected_lane_close_reopen_paging)
                run_case(browser, 'hpc-reversible-return', lambda page: reversible_mall_return(page, True))
                run_case(browser, 'play-root-reversible-return', lambda page: reversible_mall_return(page, False))
                run_case(browser, 'hpc-desktop-reversible-return', lambda page: reversible_mall_return(page, True, True), desktop=True)
                run_case(browser, 'play-desktop-reversible-return', lambda page: reversible_mall_return(page, False, True), desktop=True)
                run_case(browser, 'play-lane-reversible-return', lambda page: reversible_mall_return(page, False, lane=True))
                run_case(browser, 'play-desktop-lane-reversible-return', lambda page: reversible_mall_return(page, False, True, True), desktop=True)
                run_case(browser, 'hpc-early-repeated-selection', lambda page: early_repeated_selection(page, True))
                run_case(browser, 'play-early-repeated-selection', lambda page: early_repeated_selection(page, False))
                run_case(browser, 'retained-history-reentry', retained_history_reentry)
                run_case(browser, 'unsupported-provider-return', unsupported_provider_return)
                run_case(browser, 'hpc-unready-mall-return-stays-closed', unready_mall_return_stays_closed, desktop=True, hold_ready=True)
                run_case(browser, 'borrowed-queue-preserves-mall-query', borrowed_queue_keeps_mall_query)
                run_case(browser, 'desktop-borrowed-queue-preserves-mall-query', lambda page: borrowed_queue_keeps_mall_query(page,True), desktop=True)
                run_case(browser, 'hpc-tile-tap-choices', lambda page: tile_tap_choices(page, True))
                run_case(browser, 'public-tile-tap-choices', lambda page: tile_tap_choices(page, False))
                run_case(browser, 'hpc-one-dock-player', lambda page: dock_flow(page, True))
                run_case(browser, 'public-one-dock-player', lambda page: dock_flow(page, False))
                run_case(browser, 'conditional-manual-recovery', blocked_recovery, True)
                run_case(browser, 'silent-start-provider-unknown', silent_start_unknown, silent_start=True)
            finally:
                browser.close()
finally:
    REPORT['source_sha256_after'] = hashes()
    REPORT['source_stable'] = REPORT['source_sha256_before'] == REPORT['source_sha256_after']
    REPORT['elapsed_seconds'] = round(time.time() - REPORT['started_epoch'], 3)
    REPORT['status'] = 'PASS' if (len(REPORT['cases']) == (2*len(set(args.case)) if args.case else (54 if args.include_defensive else 52)) and
        all(row['passed'] for row in REPORT['cases']) and REPORT['source_stable']) else 'FAIL'
    save()
sys.exit(0 if REPORT['status'] == 'PASS' else 1)
