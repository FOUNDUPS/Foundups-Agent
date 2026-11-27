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
parser.add_argument('--phone-size', choices=['414x896', '402x874'], default='414x896',
                    help='Explicit CSS mobile/touch fixture; not physical Safari viewport qualification')
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
    'provider': 'Controlled YT API fixture; VOTE uses real source-bound local MP4 bytes. All requests intercepted.',
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
    'viewport': dict(zip(('width', 'height'), map(int, args.phone_size.split('x')))),
    'device_qualification': 'Explicit CSS mobile/touch fixture; physical Safari, safe area and keyboard UNEXECUTED',
    'playwright': importlib.metadata.version('playwright'),
    'root': str(ROOT), 'cases': [], 'started_epoch': time.time(),
}


def hashes():
    files = [p for p in sorted((ROOT / 'public').rglob('*')) if p.is_file()
             and '/tests/' not in p.as_posix() and '__pycache__' not in p.parts]
    vote = ROOT / 'modules/foundups/voteballots/web'
    files += [vote / 'congressional-cards.json'] + sorted((vote / 'comics').glob('*-card-*'))
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def save():
    OUT.write_text(json.dumps(REPORT, indent=2) + '\n', encoding='utf-8')


def assert_true(condition, detail):
    if not condition:
        raise AssertionError(detail)


def make_page(browser, block=False, block_storage=False, silent_start=False, desktop=False, hold_ready=False):
    context, transport = fixture.offline_fixture_context(browser,viewport={'width': 1440, 'height': 900} if desktop else REPORT['viewport'], is_mobile=not desktop,
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
    return context, page, transport


def boot(page, hpc=False):
    page.goto('https://hpc.foundups.com/member/' if hpc else
              'https://play.foundups.com/member/', wait_until='domcontentloaded')
    expect(page.locator('#mallTileField .mall-tile').first).to_be_visible()
    expect(page.locator('.mall-member-search-dock:visible')).to_have_count(1)


def open_video_menu(page, settings=False):
    if page.evaluate('window.mallVideoPlayer?.isFloating?.()&&!window.mallVideoPlayer?.isTucked?.()'):
        page.locator('#videoPlayerFullscreen .video-player-gesture-grip').click()
    elif page.locator('.mall-member-search-dock:visible .mall-search-plus').count():
        page.locator('.mall-member-search-dock:visible .mall-search-plus').click()
    else:
        page.locator('#videoPlayerFullscreen .video-player-gesture-grip').click()
    menu = page.locator('.mall-member-search-options[open]')
    expect(menu).to_be_visible()
    details = menu.locator('[data-video-settings]' if settings else '[data-video-commands]')
    if details.get_attribute('open') is None:
        details.locator(':scope > summary').click()
    expect(details).to_have_attribute('open', '')
    return menu


def close_video_menu(page, menu):
    dialog = menu.element_handle()
    dialog.evaluate("d=>{delete d.dataset.fixtureClosed;d.addEventListener('close',()=>{d.dataset.fixtureClosed='yes'},{once:true})}")
    menu.get_by_role('button', name='Close', exact=True).click()
    page.wait_for_function("d=>d.dataset.fixtureClosed==='yes'", arg=dialog)
    dialog.dispose()
    expect(menu).not_to_be_visible()


def set_video_choices(page, **values):
    menu = open_video_menu(page, settings=True)
    for key, value in values.items():
        control = menu.locator('[data-video-option="' + key + '"]')
        if isinstance(value, bool):
            control.set_checked(value)
        else:
            control.select_option(value)
    close_video_menu(page, menu)


def video_action(page, action):
    # The existing desktop theater retains its own Back control; it has no
    # floating phone dock. Do not change input capabilities to manufacture a tap.
    if action == 'close' and page.evaluate('window.mallVideoPlayer.isTheater()'):
        page.locator('#videoPlayerFullscreen [data-action="back"]').click()
        return
    menu = open_video_menu(page)
    dialog = menu.element_handle()
    dialog.evaluate("d=>{delete d.dataset.fixtureActionClosed;d.addEventListener('close',()=>{d.dataset.fixtureActionClosed='yes'},{once:true})}")
    menu.locator('[data-player-action="' + action + '"]').click()
    page.wait_for_function("d=>d.dataset.fixtureActionClosed==='yes'", arg=dialog)
    dialog.dispose()


def app_touch(page, target, dx=0, dy=0, pinch=None, start_fraction=.5):
    """Hit-tested app edge; Chromium native touch injection, WebKit DOM events.

    No input is sent into the provider iframe. Neither engine proves physical
    iPhone/Safari gesture behavior.
    """
    expect(target).to_be_visible()
    box = target.bounding_box()
    assert_true(box and box['width'] > 0 and box['height'] >= 44, box)
    viewport = page.viewport_size
    x, y = box['x'] + box['width'] * start_fraction, box['y'] + box['height'] / 2
    assert_true(target.evaluate('(e,p)=>e===document.elementFromPoint(p.x,p.y)||e.contains(document.elementFromPoint(p.x,p.y))', {'x': x, 'y': y}),
                {'app_surface_not_hit_testable': box})
    if pinch is None:
        start = [{'x': x, 'y': y}]
        end = [{'x': x + dx, 'y': y + dy}]
    else:
        half = min(box['height'] / 2 - 8, y - 8, viewport['height'] - y - 8)
        assert_true(half >= 70, {'insufficient_pinch_surface': box})
        a, b = (half / 2, half) if pinch == 'out' else (half, half / 2)
        start = [{'x': x, 'y': y - a}, {'x': x, 'y': y + a}]
        end = [{'x': x, 'y': y - b}, {'x': x, 'y': y + b}]
    for point in start + end:
        assert_true(0 <= point['x'] < viewport['width'] and 0 <= point['y'] < viewport['height'],
                    {'gesture_point_outside_viewport': point, 'box': box})
    engine = page.context.browser.browser_type.name
    if engine == 'chromium':
        session = page.context.new_cdp_session(page)
        try:
            session.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': start})
            for step in range(1, 7):
                points = [{'x': a['x'] + (b['x'] - a['x']) * step / 6,
                           'y': a['y'] + (b['y'] - a['y']) * step / 6} for a, b in zip(start, end)]
                session.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': points})
            session.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
        finally:
            session.detach()
        mode = 'Chromium CDP touch on visible app edge'
    else:
        target.evaluate("""(e,p)=>{
          const touches=points=>points.map(t=>({clientX:t.x,clientY:t.y}));
          for(const [name,active,changed] of [['touchstart',p.start,p.start],['touchmove',p.end,p.end],['touchend',[],p.end]]){
            const event=new Event(name,{bubbles:true,cancelable:true});
            Object.defineProperties(event,{touches:{value:touches(active)},changedTouches:{value:touches(changed)}});
            e.dispatchEvent(event);
          }
        }""", {'start': start, 'end': end})
        mode = 'WebKit synthetic touch events on hit-tested visible app edge'
    # Settle the pinch fence and the longer synthetic-click suppression. This
    # also exposes an accidental second navigation from pointer/touch delivery.
    page.wait_for_timeout(460)
    return {'surface': box, 'start': start, 'end': end, 'delivery': mode}


def checkpoint(page, name):
    value = page.evaluate("""() => {
      const visible = e => { const s=getComputedStyle(e),r=e.getBoundingClientRect();
        return !e.hidden&&s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0; };
      const docks=[...document.querySelectorAll('.mall-member-search-dock')].filter(visible);
      const dock=docks[0],input=dock?.querySelector('textarea'),r=input?.getBoundingClientRect();
      const scopedActions=document.documentElement.dataset.mallVideoScope==='hpc';
      const guest=!!window.mallVideoProjection?.isOpenMallHost(location)&&!window.mallVideoProjection.isAdmissionRequest(location);
      const contribution=dock?.querySelector('.mall-search-add');
      const add=dock?.querySelector(scopedActions||guest?'.mall-search-plus':'.mall-search-add'),ar=add?.getBoundingClientRect();
      return {count:docks.length,same:!window.independentDock||dock===window.independentDock,
        inert:!!dock?.closest('[inert]'),inputRect:r?.toJSON(),
        inputHit:r?document.elementFromPoint(r.left+r.width/2,r.top+r.height/2)===input:false,
        sameFrame:!window.independentFrame||document.querySelector('#videoPlayerFullscreen iframe')===window.independentFrame,
        created:window.fixturePlayback.created,state:window.mallVideoPlayer?.getPlaybackSnapshot?.(),
        addRect:ar?.toJSON(),addPosition:add?getComputedStyle(add).position:null,
        guest,contributionHidden:!!contribution?.hidden,contributionDisabled:!!contribution?.disabled,
        addKind:scopedActions||guest?'actions':'contribution',
        addHit:ar?add.contains(document.elementFromPoint(ar.left+ar.width/2,ar.top+ar.height/2)):false,
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
    assert_true(value['addHit'], {'checkpoint': name, 'action_obscured': value})
    if value['guest']:
        assert_true(value['contributionHidden'] and value['contributionDisabled'],
                    {'checkpoint': name, 'guest_contribution_exposed': value})
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
      const guest=!!window.mallVideoProjection?.isOpenMallHost(location)&&!window.mallVideoProjection.isAdmissionRequest(location);
      const hit=(e,r)=>e.contains(document.elementFromPoint(r.left+r.width/2,r.top+r.height/2));
      return {dog:d.toJSON(),add:a.toJSON(),input:i.toJSON(),dogHit:hit(dog,d),addHit:hit(add,a),
        guest,addHidden:add.hidden,addDisabled:add.disabled,
        controls:[...dock.querySelectorAll('button:not([hidden]),a:not([hidden])')].filter(e=>e.getClientRects().length).map(e=>{
          const r=e.getBoundingClientRect();return {name:e.getAttribute('aria-label')||e.textContent.trim(),rect:r.toJSON(),hit:hit(e,r)};}),
        inputHit:hit(input,i),expanded:dock.querySelector('form').hasAttribute('data-expanded'),
        viewportWidth:innerWidth,scrollWidth:document.documentElement.scrollWidth};
    }""")
    assert_true(value['dog']['width'] >= 44 and value['dog']['height'] >= 44,
                {'layout': name, 'small_touch_target': value})
    if value['guest']:
        assert_true(value['addHidden'] and value['addDisabled'] and value['add']['width'] == 0 and value['add']['height'] == 0,
                    {'layout': name, 'guest_contribution_exposed_or_reserved': value})
        requests=[]
        listener=lambda request:requests.append(request.url)
        page.on('request',listener)
        before=page.evaluate('JSON.stringify(window.mallStateRestore.peekAdmissionIntent())')
        original_url=page.url
        page.locator('.mall-search-add').evaluate("e=>e.dispatchEvent(new MouseEvent('click',{bubbles:true}))")
        page.wait_for_timeout(30)
        page.remove_listener('request',listener)
        assert_true(not requests and page.url==original_url and page.evaluate('JSON.stringify(window.mallStateRestore.peekAdmissionIntent())')==before and page.locator('#mallContributionReview').count()==0,
                    {'layout':name,'guest_synthetic_add_effect':requests})
    else:
        assert_true(value['add']['width'] >= 44 and value['add']['height'] >= 44 and value['addHit'],
                    {'layout': name, 'contribution_target': value})
        assert_true(value['dog']['x'] + value['dog']['width'] <= value['add']['x'] + 1,
                    {'layout': name, 'dog_not_before_add': value})
    assert_true(all(c['rect']['width']>=44 and c['rect']['height']>=44 and c['hit'] for c in value['controls']),
                {'layout':name,'remaining_control_target':value})
    assert_true(value['dogHit'] and value['inputHit'],
                {'layout': name, 'controls_obscured': value})
    assert_true(value['scrollWidth'] <= value['viewportWidth'] + 1,
                {'layout': name, 'overflow': value})
    return value


def public_detail_scroll_return(page):
    """Close a real, partly visible full17 card without focus scrolling it."""
    tile=page.locator('.mall-tile[data-foundup-id="kids_episodes"]')
    button=tile.locator('.mall-card-front .mall-card-expand-detail')
    expect(button).to_be_visible()
    # Setup only: leave the real card partly below the dock, with its button
    # exposed. No scroll or focus repair runs after opening or closing.
    button.evaluate("""e=>{const w=e.closest('.mall-tile-field-wrapper'),d=document.querySelector('#redDogAnchor');
      const bottom=Math.min(w.getBoundingClientRect().bottom,d.getBoundingClientRect().top);
      w.scrollTo({top:w.scrollTop+e.getBoundingClientRect().top-(bottom-55),behavior:'instant'});} """)
    def snapshot():
        return page.evaluate("""()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>{
          const w=document.querySelector('.mall-tile-field-wrapper');resolve({top:w.scrollTop,rect:w.getBoundingClientRect().toJSON(),focusId:document.activeElement?.dataset?.foundupId||null});
        })))""")
    before=snapshot()
    assert_true(before['top']>1, {'plane_return_missing_positive_scroll_setup':before})
    button.click()
    plane=page.locator('#foundupViewPlane')
    expect(plane).to_have_class(__import__('re').compile(r'\bopen\b'))
    opened=snapshot()
    page.locator('#foundupViewClose').click()
    expect(plane).not_to_have_class(__import__('re').compile(r'\bopen\b'))
    after=snapshot()
    result={'id':'kids_episodes','before':before,'open':opened,'after_two_animation_frames':after,
            'close_delta':after['top']-opened['top'],'no_forced_scroll_after_setup':True}
    assert_true(abs(opened['top']-before['top'])<=2 and abs(result['close_delta'])<=2 and
                after['focusId']=='kids_episodes' and after['rect']==before['rect'],
                {'full17_plane_close_scroll_or_focus_regression':result})
    return result


def public_poster_and_overlay(page):
    """Actual shared CSS, poster/one avatar state, and no reserved dock block."""
    total=len(json.loads((ROOT/'public/member/mall-video-catalog.json').read_text(encoding='utf-8')))
    fixture.materialize_public_cards(page,total)
    tile=page.locator('.mall-tile[data-foundup-id="science_swarm"]')
    expect(tile).to_have_count(1)
    poster=tile.evaluate("e=>{const s=getComputedStyle(e);return {size:s.backgroundSize,position:s.backgroundPosition,repeat:s.backgroundRepeat,type:e.dataset.tileType}}")
    assert_true(poster['size']=='cover' and poster['position']=='50% 50%' and poster['repeat']=='no-repeat',
                {'themed_poster_css_reset':poster})
    avatar=tile.evaluate("""e=>{const original=e.dataset.tileType;e.dataset.tileType='avatar';
      const s=getComputedStyle(e),result={size:s.backgroundSize,position:s.backgroundPosition,repeat:s.backgroundRepeat};
      e.dataset.tileType=original;return result;}""")
    assert_true(avatar=={'size':'contain','position':'50% 50%','repeat':'no-repeat'}, {'avatar_css_state':avatar})
    measured=[]
    for height in (REPORT['viewport']['height'],500):
        page.set_viewport_size({'width':REPORT['viewport']['width'],'height':height})
        wrapper=page.locator('.mall-tile-field-wrapper')
        wrapper.evaluate('e=>e.scrollTo({top:e.scrollHeight,behavior:"instant"})')
        page.wait_for_function("""()=>{const t=document.querySelector('#mallTileField .mall-tile:last-of-type'),d=document.querySelector('#redDogAnchor');
          return t&&d&&t.getBoundingClientRect().bottom<=d.getBoundingClientRect().top+1;}""")
        value=page.evaluate("""()=>{
          const shell=document.querySelector('.mall-shell'),field=document.querySelector('.mall-tile-field-wrapper'),
            grid=document.querySelector('#mallTileField'),dock=document.querySelector('#redDogAnchor'),last=grid.querySelector('.mall-tile:last-of-type');
          const rect=e=>e.getBoundingClientRect().toJSON(),s=getComputedStyle(shell),f=getComputedStyle(field);
          return {viewport:[innerWidth,innerHeight],shell:rect(shell),shellPaddingBottom:parseFloat(s.paddingBottom),shellRows:s.gridTemplateRows,
            field:rect(field),fieldPaddingBottom:f.paddingBottom,grid:rect(grid),gridPaddingBottom:parseFloat(getComputedStyle(grid).paddingBottom),
            dock:rect(dock),dockPosition:getComputedStyle(dock).position,last:rect(last),scrollTop:field.scrollTop,scrollMaximum:field.scrollHeight-field.clientHeight,
            safeBottom:parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--safe-bottom'))||0};
        }""")
        assert_true(value['shellPaddingBottom']<=max(16,value['safeBottom'])+1 and value['field']['bottom']>value['dock']['top']+1,
                    {'reserved_dock_layout_block':value})
        assert_true(value['dockPosition']=='fixed' and value['gridPaddingBottom']>=value['dock']['height']+12 and
                    value['last']['bottom']<=value['dock']['top']+1 and value['scrollTop']>1,
                    {'dock_overlay_tail_or_positive_scroll':value})
        measured.append(value)
    page.set_viewport_size(REPORT['viewport'])
    detail_return=public_detail_scroll_return(page)
    return {'poster':poster,'avatar_css_state':avatar,'overlay_and_scroll_tail':measured,
            'full17_detail_return':detail_return,'physical_keyboard_safe_area':'UNEXECUTED'}


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
                {'header_not_compact_one_row': {'viewport':REPORT['viewport'],'brand': b, 'account': a}})
    poster_overlay=public_poster_and_overlay(page)
    page.screenshot(path=str(OUT.with_name(OUT.stem + '-' + REPORT['engine'] + '-public-header.png')))
    layouts = [public_action_layout(page, 'default-'+args.phone_size)]
    search = page.locator('.mall-member-search-dock:visible .mall-member-search-bar textarea')
    search.fill('A viewport-sized Mall query for checking wrapped input and both trailing actions. ' * 3)
    expect(page.locator('.mall-member-search-dock:visible .mall-member-search-bar')).to_have_attribute('data-expanded', '')
    layouts.append(public_action_layout(page, 'expanded-query-'+args.phone_size))
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
    return {'poster_overlay':poster_overlay,'header': header.bounding_box() if page.locator('.mall-header').count() else None,
            'branding_account_initial': {'brand': b, 'account': a},
            'filters_moved_once_and_operable': True, 'account_destination': page.url,
            'idle_listening_hidden': True, 'action_layouts': layouts}


def hpc_branding(page):
    boot(page, True)
    banner = page.locator('.mall-hpc-banner-link')
    expect(banner).to_have_attribute('href', '/member/')
    expect(banner).to_have_attribute('aria-label', 'Home: HPC video tiles')
    expect(page.locator('#videoScopeDisclosure a[href="https://hasan4speaker.com/"]')).to_have_count(1)
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
    expect(dog).to_have_attribute('aria-label', 'Open Red Dog conversation')
    assert_true(dog.evaluate("e=>e.tagName==='BUTTON'&&!e.hasAttribute('href')"),
                'Conversation availability must not become a Mall redirect')
    expect(page.locator('#videoScopePhoneDock .mall-search-plus')).to_be_visible()
    expect(page.locator('dialog[open]')).to_have_count(0)
    dog.tap()
    expect(page.get_by_role('dialog', name='Red Dog conversation', exact=True)).to_be_visible()
    page.get_by_role('button', name='Back to browsing', exact=True).click()
    banner.tap()
    assert_true(page.url == 'https://hpc.foundups.com/member/', 'HPC Home left the scope')
    assert_true(page.evaluate("mallStateRestore.getScopedPresentation()==='grid'"), 'Home intent was not saved')
    page.locator('.mall-hpc-mall-return').tap()
    page.wait_for_url('https://play.foundups.com/member/')
    expect(page.locator('dialog[open]')).to_have_count(0)
    expect(page.locator('#mallTileField .mall-tile').first).to_be_visible()
    return {'art': art, 'build': build, 'voice_icon': icon,
            'mall_return_navigated': page.url, 'campaign_link_preserved_in_disclosure': True}



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
    assert_true(group.locator('[data-video-settings]').get_attribute('open') is None,
                'Normal plus entry exposed the settings detail group by default')
    assert_true(group.locator('[data-video-commands]').get_attribute('open') is None,
                'Normal plus entry exposed playback commands by default')
    group.locator('[data-video-settings] > summary').click()
    choice = group.locator('[data-video-option="tileTapDestination"]')
    expect(choice).to_have_value('floating')
    assert_true(choice.locator('option').evaluate_all('(es)=>es.map(e=>e.value)') ==
                ['floating', 'wikitube', 'full-video'], 'Missing deliberate tap choices')
    modes = {'floating': 'Floating video player', 'wikitube': 'WikiTube video player',
             'full-video': 'Full Video in app'}
    def close_choices():
        # Native dialog.close() queues its close/focus-restoration event. Await
        # that event before assigning keyboard focus to a tile, so this test
        # cannot send Enter to the restored plus button instead of the tile.
        closing_dialog = menu.element_handle()
        closing_dialog.evaluate("d=>{delete d.dataset.fixtureClosed;d.addEventListener('close',()=>{d.dataset.fixtureClosed='yes'},{once:true})}")
        menu.get_by_role('button', name='Close', exact=True).click()
        page.wait_for_function("d=>d.dataset.fixtureClosed==='yes'", arg=closing_dialog)
        closing_dialog.dispose()
        expect(menu).not_to_be_visible()
    results = []
    for destination, mode in modes.items():
        if not menu.is_visible():
            dock.locator('.mall-search-plus').tap()
        if group.locator('[data-video-settings]').get_attribute('open') is None:
            group.locator('[data-video-settings] > summary').click()
        choice.select_option(destination)
        expect(group.locator('[data-video-option="pinchOutDestination"]')).to_have_value('wikitube')
        assert_true(page.evaluate('window.mallStateRestore.getVideoOptions().tileTapDestination') == destination,
                    'Tile setting did not persist before activation')
        close_choices()
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
        assert_true(selected['pinchOutDestination'] == 'wikitube', selected)
        for key in ['pinchInDestination', 'swipeUpDestination']:
            assert_true(key not in selected, 'Unconfirmed initial default was seeded: ' + key)
        result = {'destination': destination, 'mode': mode,
                  'activation': 'keyboard' if destination == 'wikitube' else 'pointer'}
        if destination == 'floating':
            page.wait_for_function('window.mallVideoPlayer.getPlaybackSnapshot()?.positionSeconds>=.35')
            before = page.evaluate('({snapshot:window.mallVideoPlayer.getPlaybackSnapshot(),loads:window.fixturePlayback.loadedIds.length,created:window.fixturePlayback.created})')
            page.evaluate('window.independentFrame=document.querySelector("#videoPlayerFullscreen iframe")')
            dock.locator('.mall-search-plus').tap()
            if group.locator('[data-video-settings]').get_attribute('open') is None:
                group.locator('[data-video-settings] > summary').click()
            choice.select_option('full-video')
            close_choices()
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
    if page.locator('.mall-member-search-options[open] [data-video-settings]').get_attribute('open') is None:
        page.locator('.mall-member-search-options[open] [data-video-settings] > summary').click()
    expect(page.locator('.mall-member-search-options[open] [data-video-option="tileTapDestination"]')).to_have_value('full-video')
    return {'choices': results, 'reload_retained': 'full-video', 'unconfirmed_defaults_seeded': False}



def preview_dog_return(page):
    origin = 'https://foundupscom--play-v26-iphone-jxbn78ue.web.app'
    page.goto(origin + '/member/?foundup=hpc', wait_until='domcontentloaded')
    expect(page.locator('#mallTileField .mall-tile').first).to_be_visible()
    dog = page.locator('#videoScopePhoneDock .mall-search-dog')
    expect(dog).not_to_have_attribute('href', '/member/')
    expect(dog).to_have_attribute('aria-label', 'Open Red Dog conversation')
    expect(page.locator('#videoScopePhoneDock .mall-search-plus')).to_be_visible()
    dog.tap()
    expect(page.get_by_role('dialog', name='Red Dog conversation', exact=True)).to_be_visible()
    page.get_by_role('button', name='Back to browsing', exact=True).click()
    assert_true(page.url == origin + '/member/?foundup=hpc', 'Dog left the current preview')
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
        {foundupId:'hpc',videoId:'HPC00000000',title:'Safe history',thumbnail:'/logo-dog.png',playbackPosition:7,timestamp:1},
        {foundupId:'hpc',videoId:'HPC00000001',title:'Safe HTTPS image',thumbnail:'https://i.ytimg.com/vi/HPC00000001/hqdefault.jpg',timestamp:1},
        ...['javascript:void(0)','data:image/svg+xml,<svg/>','https://user:pass@example.invalid/image',
            'http://example.invalid/image','file:///fixture.png','blob:https://play.foundups.com/fixture']
          .map((thumbnail,i)=>({foundupId:'hpc',videoId:'unsafe'+i,title:'Rejected thumbnail '+i,thumbnail,timestamp:1}))
      ]));
      // Existing presentation-only admission seam, with entirely synthetic data.
      // This does not authenticate an account or exercise real backend admission.
      window.redDog.setDiscoveryAdmission(true); window.redDog.open();
    }""", {'payload': payload, 'identity': identity})
    history = page.locator('[data-reddog-history]')
    expect(history).to_be_visible()
    expect(history.locator('.reddog-history-card')).to_have_count(9)
    expect(history.locator('.reddog-history-title').first).to_have_text(payload)
    expect(history.locator('.reddog-history-card').first).to_have_attribute('data-history-foundup', identity)
    expect(history.locator('.reddog-history-continue-badge').first).to_have_text('Continue at 1:07')
    expect(history.locator('[data-fixture-injected], [onerror], [onfocus], [onmouseover], [autofocus], script')).to_have_count(0)
    assert_true(page.evaluate('window.fixtureXss===0'), 'History payload became executable markup')
    cards=history.locator('.reddog-history-card')
    expect(cards.nth(1).locator('img')).to_have_attribute('src','https://play.foundups.com/logo-dog.png')
    expect(cards.nth(2).locator('img')).to_have_attribute('src','https://i.ytimg.com/vi/HPC00000001/hqdefault.jpg')
    for index in range(3,9):
        expect(cards.nth(index).locator('img')).to_have_count(0)
        expect(cards.nth(index).locator('.reddog-history-thumb-empty')).to_have_count(1)
    history.get_by_role('button', name='Clear', exact=True).click()
    expect(history.locator('.reddog-history-count')).to_have_text('0')
    expect(history.locator('.reddog-history-empty')).to_be_visible()
    page.evaluate('window.redDog.close(); window.redDog.setDiscoveryAdmission(false)')
    return {'literal_text_and_attributes': True, 'continue_badge_and_clear': True,
            'unsafe_thumbnail_schemes_and_userinfo_rejected':6,'https_and_relative_thumbnails_preserved':True,
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
    video_action(page, 'collapse')
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
    video_action(page, 'close')
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
        video_action(page, 'close')
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
        video_action(page, 'close')
        expect(player).not_to_be_visible()
        expect(player.locator('iframe')).to_have_count(0)
    else:
        video_action(page, 'collapse')
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
    video_action(page, 'expand')
    video_action(page, 'next')
    page.wait_for_function('id=>window.mallVideoPlayer.getCurrentVideoId()===id',arg=batch[0]['video_id'])
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    assert_true(page.evaluate('document.querySelector("#videoPlayerFullscreen iframe")===window.returnFixtureFrame'),'Pending-page continuation recreated the provider')
    video_action(page, 'close')
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
    video_action(page, 'close')
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
    video_action(page, 'close')
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
    video_action(page, 'close')
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
    video_action(page, 'collapse')
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
    video_action(page, 'close')
    expect(player.locator('iframe')).to_have_count(0)
    return {'unready_disposed':True,'resize_stayed_closed':True,'deliberate_reopen':True,'event':event}


def borrowed_queue_keeps_mall_query(page, desktop=False):
    boot(page)
    page.evaluate("window.loanFixtureDock=document.querySelector('.mall-member-search-dock:not([hidden])');window.mallStateRestore.setVideoOptions({tileTapDestination:'full-video'})")
    mall_input=page.locator('.mall-member-search-dock:visible textarea')
    mall_input.fill('move2japan');mall_input.press('Enter')
    # This case tests borrowing a completed Mall query, not a pointer race
    # while explicit search hydrates the remaining bounded metadata pages.
    # The matching tile is already present at boot, so visibility alone cannot
    # establish that the last search-owned DOM replacement has completed.
    expected_total=json.loads((fixture.public/'member/discovery/catalog.json').read_text(encoding='utf-8'))['total']
    page.wait_for_function("""total => {
      const field=window.mallTileField, scope=field.getFieldScope();
      return scope?.type==='query' && scope.query==='move2japan' &&
        field.getLoadedCatalog().length===total;
    }""",arg=expected_total)
    readiness=page.evaluate("""() => ({scope:window.mallTileField.getFieldScope(),
      loaded:window.mallTileField.getLoadedCatalog().length})""")
    assert_true(readiness['scope']=={'type':'query','query':'move2japan'} and
                readiness['loaded']==expected_total,{'search_readiness':readiness,'expected_total':expected_total})
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
        video_action(page, 'expand')
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
        video_action(page, 'collapse')
        page.wait_for_function('window.mallVideoPlayer.isMallHidden()')
        expect(player).not_to_be_visible()
        reopen_retained_from_caller(page, hpc)
        expect(player).to_have_attribute('aria-label', 'Floating video player')
        points.append(checkpoint(page, 'restored-' + str(cycle)))
        if hpc:
            expect(page.locator('#videoScopePhoneDock .mall-member-search-bar textarea')).to_have_value('Fixture')
    assert_true(all(p['sameFrame'] and p['created'] == 1 for p in points), points)
    # Exercise the existing options through UI, including Full Video -> WikiTube.
    menu = open_video_menu(page, settings=True)
    menu.locator('[data-video-option="pinchOutDestination"]').select_option('full-video')
    menu.locator('[data-video-option="collapseDestination"]').select_option('wikitube')
    # A native select can consume Escape; focus a dialog control first.
    menu.get_by_role('button', name='Close', exact=True).focus()
    page.keyboard.press('Escape')
    expect(menu).not_to_be_visible()
    video_action(page, 'expand')
    expect(player).to_have_attribute('aria-label', 'Full Video in app')
    expect(player.locator('.video-player-queue-rail')).not_to_be_visible()
    points.append(checkpoint(page, 'full-video'))
    video_action(page, 'collapse')
    expect(player).to_have_attribute('aria-label', 'WikiTube video player')
    points.append(checkpoint(page, 'full-video-to-wikitube'))
    video_action(page, 'collapse')
    page.wait_for_function('window.mallVideoPlayer.isMallHidden()')
    expect(player).not_to_be_visible()
    reopen_retained_from_caller(page, hpc)
    expect(player).to_have_attribute('aria-label', 'Floating video player')
    points.append(checkpoint(page, 'full-video-restored'))
    assert_true(all(p['sameFrame'] and p['created'] == 1 for p in points), points)
    menu = open_video_menu(page, settings=True)
    menu.locator('[data-video-option="pinchOutDestination"]').select_option('wikitube')
    menu.get_by_role('button', name='Close', exact=True).focus()
    page.keyboard.press('Escape')
    expect(menu).not_to_be_visible()
    video_action(page, 'expand')
    if hpc:
        # Only the existing fixed-HPC scope pushes a player history entry.
        page.go_back(wait_until='domcontentloaded')
    else:
        # Public browsing preserves its existing native history. Use its UI Back.
        video_action(page, 'close')
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
    expect(play).not_to_be_visible()
    frame = player.locator('iframe')
    expect(frame).to_have_count(1)
    page.evaluate("window.independentFrame=document.querySelector('#videoPlayerFullscreen iframe');window.fixturePlayback.block=false")
    video_action(page, 'play')
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
    expect(play).not_to_be_visible()
    page.evaluate("window.independentFrame=document.querySelector('#videoPlayerFullscreen iframe');window.fixturePlayback.releaseSilentStart()")
    video_action(page, 'play')
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    expect(play).not_to_be_visible()
    assert_true(page.evaluate("document.querySelector('#videoPlayerFullscreen iframe')===window.independentFrame"),
                'Unknown-start manual recovery replaced provider frame')
    return {'silent_start': snapshot, 'rendered_message': message, 'manual_recovery': True,
            'qualification': 'Synthetic API emitted READY then remained silent; no observed browser onAutoplayBlocked event.'}


def floating_frame_controls(page):
    boot(page, True)
    page.locator('.mall-tile[data-video-id="HPC00000000"]').tap(position={'x': 25, 'y': 75})
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    player = page.locator('#videoPlayerFullscreen')
    grip = player.locator('.video-player-gesture-grip')
    expect(grip).to_be_visible()
    expect(player.locator('.video-player-top-bar')).not_to_be_visible()
    expect(player.locator('.video-player-manual-play')).not_to_be_visible()
    page.evaluate("window.independentFrame=document.querySelector('#videoPlayerFullscreen iframe')")
    for width, height in [(390, 844), (414, 896), (320, 690)]:
        page.set_viewport_size({'width': width, 'height': height})
        rect = player.locator('iframe').bounding_box()
        assert_true(rect['width'] >= 200 and rect['height'] >= 200, rect)
        assert_true(rect['x'] >= 0 and rect['x'] + rect['width'] <= width + 1, rect)
    before = player.bounding_box()
    rect = grip.bounding_box()
    x, y = rect['x'] + rect['width'] / 2, rect['y'] + rect['height'] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x - 12, y + 65, steps=8)
    page.mouse.up()
    after = player.bounding_box()
    assert_true(after['y'] > before['y'] + 30, {'before': before, 'after': after})
    assert_true(page.evaluate("document.querySelector('#videoPlayerFullscreen iframe')===window.independentFrame"), 'Drag reloaded iframe')
    rect = grip.bounding_box()
    x, y = rect['x'] + rect['width'] / 2, rect['y'] + rect['height'] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + 85, y, steps=3)
    page.mouse.up()
    page.wait_for_function('window.mallVideoPlayer.isTucked()')
    rail = page.locator('.video-player-tuck-handle')
    expect(rail).to_be_visible()
    assert_true(page.evaluate('document.querySelector("#videoPlayerFullscreen").inert'), 'Tucked controls remain focusable')
    box = rail.bounding_box()
    assert_true(abs(box['height'] - after['height']) <= 1, {'rail': box, 'player': after})
    assert_true(page.evaluate("window.mallVideoPlayer.getPlaybackSnapshot()?.state!=='playing'"), 'Hidden playback continued')
    rail.tap(position={'x': 18, 'y': box['height'] - 15})
    page.wait_for_function('!window.mallVideoPlayer.isTucked()')
    assert_true(page.evaluate('!document.querySelector("#videoPlayerFullscreen").inert'), 'Restored player remains inert')
    video_action(page, 'play')
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.positionSeconds>.3")
    page.evaluate("window.mallStateRestore.setVideoOptions({pinchOutDestination:'full-video',pinchInDestination:'wikitube',swipeUpDestination:'mall'})")
    # App-owned grip, not the inaccessible provider document, receives this gesture.
    grip.evaluate("e=>{const g=new Event('gesturechange',{bubbles:true,cancelable:true});Object.defineProperty(g,'scale',{value:1.4});e.dispatchEvent(g)}")
    expect(player).to_have_attribute('aria-label', 'Full Video in app')
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    page.evaluate("window.__pfmallWikiTubeSkipDelayMs=40;window.fixturePlayback.errorsByVideo={HPC00000001:100};window.fixturePlayback.finishCurrent()")
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'&&window.mallVideoPlayer.getCurrentVideoId()==='HPC00000002'")
    assert_true(page.evaluate("window.mallVideoPlayer.getPlaybackSnapshot().failedIndices.includes(1)"), 'Full Video did not retain failed-clip diagnosis')
    expect(grip).to_be_visible()
    app_touch(page, grip, pinch='in')
    expect(player).to_have_attribute('aria-label', 'WikiTube video player')
    app_touch(page, grip, dy=-90)
    page.wait_for_function('window.mallVideoPlayer.isMallHidden()')
    assert_true(page.evaluate("document.querySelector('#videoPlayerFullscreen iframe')===window.independentFrame"), 'Gesture return recreated iframe')
    assert_true(page.evaluate('window.fixturePlayback.created===1'), 'More than one player created')
    return {'responsive_provider_minimum': True, 'drag': {'before': before, 'after': after},
            'restore_rail': box, 'hidden_paused': True, 'independent_gesture_destinations': True,
            'same_iframe': True, 'cross_origin_touches': 'NOT_CAPTURED', 'physical_iPhone': 'UNEXECUTED'}


def clean_video_gestures(page):
    boot(page, True)
    page.locator('.mall-tile[data-video-id="HPC00000000"]').tap(position={'x': 25, 'y': 75})
    page.wait_for_function("window.mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    player = page.locator('#videoPlayerFullscreen')
    grip = player.locator('.video-player-gesture-grip')
    # Materialize the existing paged fixture through its canonical control;
    # filtered navigation must include records beyond the first loaded page.
    for _ in range(12):
        if page.evaluate('window.mallVideoPlayer.getQueueLength()>=24'):
            break
        more = page.get_by_role('button', name='Load more videos', exact=True)
        if not more.count():
            break
        more.evaluate('e=>e.click()')
        page.wait_for_timeout(40)
    assert_true(page.evaluate('window.mallVideoPlayer.getQueueLength()>=24'), 'Fixture did not exercise more than one catalog page')
    page.evaluate("""() => {
      const frame=document.querySelector('#videoPlayerFullscreen iframe');
      window.cleanFrame=frame;window.cleanWindow=frame.contentWindow;
      const wrapper=document.querySelector('.mall-tile-field-wrapper');
      window.cleanCaller={id:mallVideoPlayer.getCurrentVideoId(),scroll:wrapper.scrollTop,left:wrapper.scrollLeft};
      window.cleanEvents={save:0,share:0,dismiss:0};window.cleanShares=[];
      for(const [event,key] of [['videoPlayerSave','save'],['videoPlayerShare','share'],['videoPlayerDismiss','dismiss']])
        addEventListener(event,()=>window.cleanEvents[key]++);
      Object.defineProperty(navigator,'share',{configurable:true,value:async data=>{window.cleanShares.push(data)}});
    }""")
    set_video_choices(page, autoplayNext=False, pinchOutDestination='full-video',
                      pinchInDestination='wikitube', fullVideoSwipeRight='next', tuckedSwipeRight='next-reveal')
    transitions = [app_touch(page, grip, pinch='out')]
    expect(player).to_have_attribute('aria-label', 'Full Video in app')
    expect(player.locator('.video-player-top-bar')).not_to_be_visible()
    expect(player.locator('.video-player-manual-play')).not_to_be_visible()
    assert_true(page.evaluate('document.activeElement===document.querySelector(".video-player-gesture-grip")'), 'Expanded keyboard focus did not reach the visible app grip')
    assert_true(not page.evaluate('!!document.fullscreenElement'), 'App Full Video entered native provider fullscreen')
    frame = player.locator('iframe').bounding_box()
    edge = grip.bounding_box()
    assert_true(frame['width'] >= 200 and frame['height'] >= 200 and edge['x'] + edge['width'] <= frame['x'] + 1,
                {'provider_or_edge_geometry': {'frame': frame, 'edge': edge}})
    assert_true(abs(frame['height'] - edge['height']) <= 1, 'Grip is not the provider-height side edge')
    before = page.evaluate('({id:mallVideoPlayer.getCurrentVideoId(),loads:fixturePlayback.loadedIds.length,plays:fixturePlayback.plays})')
    transitions.append(app_touch(page, grip, dx=110))
    page.wait_for_function("mallVideoPlayer.getCurrentVideoId()==='HPC00000001'&&mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    page.wait_for_function('mallVideoPlayer.getPlaybackSnapshot()?.positionSeconds>.3')
    after = page.evaluate('({id:mallVideoPlayer.getCurrentVideoId(),loads:fixturePlayback.loadedIds.length,plays:fixturePlayback.plays,events:cleanEvents})')
    assert_true(after['loads'] == before['loads'] + 1 and after['plays'] == before['plays'] + 1,
                {'one_swipe_advanced_more_than_once': {'before': before, 'after': after}})
    assert_true(after['events'] == {'save': 0, 'share': 0, 'dismiss': 0}, after)
    assert_true(page.evaluate('mallStateRestore.getVideoOptions().autoplayNext===false'), 'Explicit swipe silently enabled natural autoplay')

    # The canonical queue filter leaves the current clip playing while typing.
    query = page.locator('.mall-member-search-dock:visible textarea')
    # Existing fixture IDs2 and20 alone carry the unique topic marker. Common
    # words in "Fixture clip2" would match the canonical token-search grammar.
    query.fill('topic')
    expect(page.locator('.video-player-queue-item')).to_have_count(2)
    matches = page.locator('.video-player-queue-item').evaluate_all('es=>es.map(e=>Number(e.dataset.index))')
    assert_true(matches == [2, 20], {'filtered_fixture': matches})
    assert_true(page.evaluate('mallVideoPlayer.getCurrentVideoId()') == 'HPC00000001', 'Typing interrupted the active clip')
    video_action(page, 'next')
    page.wait_for_function('i=>mallVideoPlayer.getCurrentIndex()===i', arg=matches[0])
    video_action(page, 'previous')
    assert_true(page.evaluate('mallVideoPlayer.getCurrentIndex()') == matches[0], 'Previous escaped the beginning of the filtered queue')
    # Setup an out-of-filter active clip through the existing shared API,
    # preserving the entered query; previous must choose the last match.
    page.evaluate('mallVideoPlayer.selectVideo(1)')
    page.wait_for_function("mallVideoPlayer.getCurrentVideoId()==='HPC00000001'&&mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    video_action(page, 'previous')
    page.wait_for_function('i=>mallVideoPlayer.getCurrentIndex()===i', arg=matches[-1])
    boundary = page.evaluate('({id:mallVideoPlayer.getCurrentVideoId(),loads:fixturePlayback.loadedIds.length})')
    video_action(page, 'next')
    assert_true(page.evaluate('({id:mallVideoPlayer.getCurrentVideoId(),loads:fixturePlayback.loadedIds.length})') == boundary,
                'End of filtered queue wrapped or loaded an unrelated clip')
    query.fill('')
    set_video_choices(page, fullVideoSwipeRight='previous')
    index = page.evaluate('mallVideoPlayer.getCurrentIndex()')
    transitions.append(app_touch(page, grip, dx=110))
    assert_true(page.evaluate('mallVideoPlayer.getCurrentIndex()') == index - 1, 'Configured reverse swipe did not select exactly one previous clip')
    set_video_choices(page, fullVideoSwipeRight='none')
    index = page.evaluate('mallVideoPlayer.getCurrentIndex()')
    transitions.append(app_touch(page, grip, dx=110))
    assert_true(page.evaluate('mallVideoPlayer.getCurrentIndex()') == index, 'No-action swipe changed video')
    set_video_choices(page, fullVideoSwipeRight='next')

    # WikiTube retains save-left/dismiss-right, rather than Full Video next.
    transitions.append(app_touch(page, grip, pinch='in'))
    expect(player).to_have_attribute('aria-label', 'WikiTube video player')
    index = page.evaluate('mallVideoPlayer.getCurrentIndex()')
    saved_before = page.evaluate('mallVideoPlayer.isCurrentSaved()')
    right_edge = player.locator('.video-player-gesture-side[data-side="right"]')
    transitions.append(app_touch(page, right_edge, dx=-90))
    assert_true(page.evaluate('mallVideoPlayer.isCurrentSaved()') is not saved_before, 'WikiTube left swipe stopped saving')
    transitions.append(app_touch(page, grip, dx=110))
    assert_true(page.evaluate('mallVideoPlayer.getCurrentIndex()') == index, 'WikiTube right swipe acquired Full Video next semantics')
    assert_true(page.evaluate('cleanEvents.dismiss') == 1, 'WikiTube dismiss hook changed')
    video_action(page, 'save')
    assert_true(page.evaluate('mallVideoPlayer.isCurrentSaved()') == saved_before, 'Accessible Save command did not revise selection')
    video_action(page, 'share')
    assert_true(page.evaluate('cleanEvents.share===1&&cleanShares.length===1'), 'Accessible Share did not use the existing shared owner')

    # Escape first dismisses the focused search; its return target is visible.
    query.focus(); page.keyboard.press('Escape')
    expect(player).to_be_visible()
    assert_true(page.evaluate('document.activeElement===document.querySelector(".video-player-gesture-grip")'), 'Search Escape focused hidden chrome')
    video_action(page, 'return')
    page.wait_for_function('mallVideoPlayer.isMallHidden()')
    returned = page.evaluate("""() => {
      const wrapper=document.querySelector('.mall-tile-field-wrapper'),active=document.activeElement;
      return {caller:cleanCaller,retainedId:mallVideoPlayer.getCurrentVideoId(),focus:active?.dataset?.videoId,
        scroll:wrapper.scrollTop,left:wrapper.scrollLeft};
    }""")
    assert_true(returned['focus'] == returned['caller']['id'] and
                abs(returned['scroll'] - returned['caller']['scroll']) <= 2 and
                abs(returned['left'] - returned['caller']['left']) <= 2,
                {'return_before_any_test_focus_or_scroll': returned})
    caller = page.locator('.mall-tile[data-video-id="' + returned['caller']['id'] + '"]')
    # This is a deliberate new selection of the original visible caller. The
    # retained clip can differ after queue navigation; do not call it lost state.
    activate_visible_tile(page, caller, False)
    page.wait_for_function('id=>mallVideoPlayer.getCurrentVideoId()===id&&mallVideoPlayer.getPlaybackSnapshot()?.state==="playing"',
                           arg=returned['caller']['id'])
    expect(player).to_have_attribute('aria-label', 'Floating video player')
    transitions.append(app_touch(page, grip, dx=85))
    page.wait_for_function('mallVideoPlayer.isTucked()')
    page.wait_for_function("mallVideoPlayer.getPlaybackSnapshot()?.state==='paused'")
    rail = page.locator('.video-player-tuck-handle')
    before = page.evaluate('({index:mallVideoPlayer.getCurrentIndex(),loads:fixturePlayback.loadedIds.length})')
    #42px edge: this complete right swipe starts AND ends inside the viewport.
    rail_box = rail.bounding_box()
    dx = min(26, page.viewport_size['width'] - (rail_box['x'] + rail_box['width'] * .25) - 2)
    assert_true(dx >= rail_box['width'] * .5, {'insufficient_real_tuck_swipe': {'rail': rail_box, 'dx': dx}})
    transitions.append(app_touch(page, rail, dx=dx, start_fraction=.25))
    page.wait_for_function('!mallVideoPlayer.isTucked()&&mallVideoPlayer.getCurrentIndex()==='+str(before['index'] + 1))
    page.wait_for_function("mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'&&mallVideoPlayer.getPlaybackSnapshot()?.positionSeconds>.3")
    assert_true(page.evaluate('fixturePlayback.loadedIds.length') == before['loads'] + 1, 'Tucked right swipe advanced more than once')
    set_video_choices(page, tuckedSwipeRight='restore')
    transitions.append(app_touch(page, grip, dx=85))
    page.wait_for_function('mallVideoPlayer.isTucked()')
    held = page.evaluate('({id:mallVideoPlayer.getCurrentVideoId(),loads:fixturePlayback.loadedIds.length})')
    transitions.append(app_touch(page, rail, dx=26, start_fraction=.25))
    page.wait_for_function('!mallVideoPlayer.isTucked()')
    assert_true(page.evaluate('({id:mallVideoPlayer.getCurrentVideoId(),loads:fixturePlayback.loadedIds.length})') == held,
                'Restore-current tuck gesture selected another video')
    assert_true(page.evaluate("mallVideoPlayer.getPlaybackSnapshot()?.state==='paused'"), 'Restore-current gesture resumed hidden playback without Play')
    set_video_choices(page, tuckedSwipeRight='none')
    transitions.append(app_touch(page, grip, dx=85))
    page.wait_for_function('mallVideoPlayer.isTucked()')
    transitions.append(app_touch(page, rail, dx=26, start_fraction=.25))
    assert_true(page.evaluate('mallVideoPlayer.isTucked()'), 'No-action tucked gesture revealed the player')
    assert_true(page.evaluate('({id:mallVideoPlayer.getCurrentVideoId(),loads:fixturePlayback.loadedIds.length})') == held,
                'No-action tucked gesture selected another video')
    # The persistent dock provides explicit recovery even while the player/grip
    # is inert and a no-action tuck gesture is selected.
    video_action(page, 'play')
    page.wait_for_function("!mallVideoPlayer.isTucked()&&mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'&&mallVideoPlayer.getPlaybackSnapshot()?.positionSeconds>.3")
    assert_true(page.evaluate('document.querySelector("#videoPlayerFullscreen iframe")===cleanFrame&&cleanFrame.contentWindow===cleanWindow&&fixturePlayback.created===1'), 'Navigation or gestures replaced the ready provider')
    expect(player.locator('iframe')).to_have_count(1)
    return {'transitions': transitions, 'explicit_swipe_autoplay_with_natural_autoplay_off': True,
            'return_before_test_activation': returned,
            'filtered_first_last_end_reverse': True, 'wiki_save_dismiss_retained': True,
            'tucked_next_and_reveal': True, 'one_provider': True,
            'menu_play_from_tucked': True,
            'share': 'MOCK_NATIVE_SHARE_API; no OS share or clipboard operation',
            'cross_origin_provider_gestures': 'NOT_CAPTURED', 'physical_iPhone': 'UNEXECUTED'}


def hpc_home_shared_desktop_dock(page):
    page.goto('https://hpc.foundups.com/member/', wait_until='domcontentloaded')
    page.wait_for_function("mallVideoPlayer.isTheater()&&mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    player = page.locator('#videoPlayerFullscreen')
    dock = page.locator('#videoScopePhoneDock')
    expect(dock).to_be_visible()
    page.evaluate("window.homeDock=document.querySelector('#videoScopePhoneDock');window.homeFrame=document.querySelector('#videoPlayerFullscreen iframe')")
    expect(player.get_by_role('search')).to_have_count(1)
    expect(dock.get_by_role('button', name='Available actions', exact=True)).to_be_visible()
    expect(dock.locator('.mall-search-add')).not_to_be_visible()
    expect(page.locator('.mall-grid-add-video')).not_to_be_visible()
    queue_box = player.locator('.video-player-queue-rail').bounding_box()
    dock_box = dock.locator('form[role="search"]').bounding_box()
    assert_true(queue_box['y'] + queue_box['height'] <= dock_box['y'] + 1,
                {'dock_not_below_app_queue': {'queue': queue_box, 'dock': dock_box}})
    assert_true(dock_box['width'] <= 585 and dock_box['height'] >= 44, dock_box)
    dock.locator('.mall-search-plus').click()
    menu = page.locator('.mall-member-search-options[open]')
    expect(menu).to_be_visible()
    expect(page.locator('#mallContributionReview[open]')).to_have_count(0)
    expect(menu.locator('[data-video-settings]')).to_be_visible()
    close_video_menu(page, menu)
    query = dock.get_by_role('textbox', name='Search this queue', exact=True)
    query.fill('theater topic')
    expect(player.locator('.video-player-queue-item')).to_have_count(2)
    assert_true(page.evaluate('mallVideoPlayer.getCurrentIndex()') == 0, 'Typing interrupted the current clip')
    query.press('Enter')
    page.wait_for_function("mallVideoPlayer.getCurrentIndex()===2&&mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    assert_true(page.evaluate('homeFrame===document.querySelector("#videoPlayerFullscreen iframe")'), 'Dock search replaced the iframe')
    page.reload(wait_until='domcontentloaded')
    page.wait_for_function("mallVideoPlayer.isTheater()&&mallVideoPlayer.getCurrentIndex()===2&&mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    expect(query).to_have_value('theater topic')
    page.evaluate("window.homeDock=document.querySelector('#videoScopePhoneDock');window.homeFrame=document.querySelector('#videoPlayerFullscreen iframe')")
    page.screenshot(path=str(OUT.with_name(OUT.stem+'-'+REPORT['engine']+'-hpc-desktop-dock.png')))

    page.get_by_role('link', name='Home: HPC video tiles', exact=True).click()
    page.wait_for_function("document.documentElement.dataset.mallVideoLayout==='grid'&&mallVideoPlayer.isMallHidden()")
    expect(page.locator('#mallTileField .mall-tile').first).to_be_visible()
    expect(dock).to_be_visible()
    assert_true(page.evaluate('homeDock===document.querySelector("#videoScopePhoneDock")&&homeFrame===document.querySelector("#videoPlayerFullscreen iframe")'), 'Home copied a shared owner')
    assert_true(page.evaluate("mallVideoPlayer.getPlaybackSnapshot()?.state==='paused'"), 'Home left hidden audio playing')
    expect(page.get_by_role('textbox', name='Search HPC Mall', exact=True)).to_have_value('')
    page.screenshot(path=str(OUT.with_name(OUT.stem+'-'+REPORT['engine']+'-hpc-desktop-grid.png')))
    page.get_by_role('button', name='Add Video to HPC', exact=True).click()
    contribution = page.locator('#mallContributionReview')
    expect(contribution).to_be_visible()
    expect(contribution).to_contain_text('no contribution has been submitted')
    expect(contribution.get_by_role('button', name='Contribution return not connected', exact=True)).to_be_disabled()
    # Do not sign in or submit. Closing this local review has no external effect.
    page.keyboard.press('Escape')
    expect(contribution).not_to_be_visible()
    page.reload(wait_until='domcontentloaded')
    page.wait_for_function("document.documentElement.dataset.mallVideoLayout==='grid'")
    assert_true(page.evaluate('!mallVideoPlayer.isOpen()'), 'Reload re-opened automatic TV after Home')
    for size in [{'width':899,'height':844}, {'width':1440,'height':900}]:
        page.set_viewport_size(size)
        expect(page.locator('#mallTileField .mall-tile').first).to_be_visible()
        assert_true(page.evaluate('!mallVideoPlayer.isOpen()'), 'Resize re-opened automatic TV')
    tile = page.locator('#mallTileField .mall-tile[data-video-id]').first
    tile.focus(); page.keyboard.press('Enter')
    page.wait_for_function("mallVideoPlayer.isFloating()&&mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    video_action(page, 'expand')
    expect(player).to_have_attribute('aria-label', 'WikiTube video player')
    expect(dock).to_be_visible()
    expect(player.get_by_role('search')).to_have_count(1)
    video_action(page, 'return')
    page.wait_for_function('mallVideoPlayer.isMallHidden()')
    expect(tile).to_be_visible()
    return {'fresh_windows_tv': True, 'same_dock_below_app_queue': True,
            'home_same_url': page.url, 'reload_resize_stays_grid': True,
            'actions_plus_distinct_from_gated_grid_add': True,
            'provider_recommendations_modified': False, 'physical_iPhone': 'UNEXECUTED'}


def tucked_next_stays_hidden(page):
    boot(page, True)
    assert_true(page.evaluate("mallStateRestore.getVideoOptions().tuckedSwipeRight==='next-hidden'"), 'Wrong fresh default')
    page.locator('#mallTileField .mall-tile[data-video-id]').first.tap(position={'x':25,'y':75})
    page.wait_for_function("mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    grip = page.locator('.video-player-gesture-grip')
    app_touch(page, grip, dx=85)
    page.wait_for_function('mallVideoPlayer.isTucked()')
    rail = page.locator('.video-player-tuck-handle')
    before = page.evaluate('({created:fixturePlayback.created,plays:fixturePlayback.plays,loads:fixturePlayback.loadedIds.length,cues:fixturePlayback.cuedIds.length})')
    for index in [1, 2]:
        app_touch(page, rail, dx=26, start_fraction=.25)
        page.wait_for_function('i=>mallVideoPlayer.isTucked()&&mallVideoPlayer.getCurrentIndex()===i', arg=index)
        expect(page.locator('#videoPlayerFullscreen iframe')).to_have_count(0)
        after = page.evaluate('({created:fixturePlayback.created,plays:fixturePlayback.plays,loads:fixturePlayback.loadedIds.length,cues:fixturePlayback.cuedIds.length})')
        assert_true(after == before, {'hidden_provider_work': after, 'before': before})
        snapshot = page.evaluate('mallVideoPlayer.getPlaybackSnapshot()')
        assert_true(snapshot['state'] == 'selected-hidden' and snapshot['positionSeconds'] is None and
                    snapshot['videoId'] == 'HPC'+str(index).zfill(8), snapshot)
    page.screenshot(path=str(OUT.with_name(OUT.stem+'-'+REPORT['engine']+'-tucked-next.png')))
    # Let the compatibility-click fence expire before a new intentional tap.
    page.wait_for_timeout(450)
    # A real touch sequence need not emit a compatibility click (observed on
    # the HTTPS preview). Isolate that boundary rather than letting click hide
    # a missing touchend tap path in this controlled provider fixture.
    rail.evaluate("e=>e.addEventListener('click',event=>{event.preventDefault();event.stopImmediatePropagation()},true)")
    rail.tap()
    page.wait_for_function("!mallVideoPlayer.isTucked()&&mallVideoPlayer.getPlaybackSnapshot()?.state==='manual-play'")
    assert_true(page.evaluate('mallVideoPlayer.getCurrentIndex()') == 2, 'Tap changed the selected video')
    assert_true(page.evaluate('fixturePlayback.plays') == before['plays'], 'Restoration auto-started a hidden selection')
    video_action(page, 'play')
    page.wait_for_function("mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'&&mallVideoPlayer.getPlaybackSnapshot()?.positionSeconds>.15")
    expect(page.locator('#videoPlayerFullscreen iframe')).to_have_count(1)
    return {'two_hit_tested_right_swipes_stay_hidden': True, 'no_hidden_provider_work': True,
            'tap_without_compatibility_click_reveals_paused': True, 'visible_play_advances_time': True,
            'physical_iPhone': 'UNEXECUTED'}


def theater_clean_control_regression(page):
    boot(page, False)
    page.locator('#mallTileField [data-foundup-id="move2japan"]').click()
    page.wait_for_function("mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    player = page.locator('#videoPlayerFullscreen')
    page.evaluate("""() => {
      window.theaterFrame=document.querySelector('#videoPlayerFullscreen iframe');
      window.theaterErrors=[];addEventListener('error',event=>theaterErrors.push(event.message));
      mallVideoPlayer.setTheater(true);
    }""")
    assert_true(page.evaluate('mallVideoPlayer.isTheater()'), 'Theater mode did not remain distinct')
    expect(player.locator('.video-player-top-bar')).to_be_visible()
    expect(player.locator('.video-player-gesture-grip')).not_to_be_visible()
    page.evaluate('fixturePlayback.block=true;mallVideoPlayer.requestPlay()')
    page.wait_for_function("mallVideoPlayer.getPlaybackSnapshot()?.state==='autoplay-blocked'")
    recovery = player.get_by_role('button', name='Play video', exact=True)
    expect(recovery).to_be_visible()
    page.evaluate('fixturePlayback.block=false')
    recovery.focus()
    page.keyboard.press('Enter')
    page.wait_for_function("mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    expect(recovery).not_to_be_visible()
    assert_true(page.evaluate('document.activeElement===theaterFrame'), 'Theater keyboard recovery did not focus its mounted provider')
    assert_true(page.evaluate('theaterErrors.length===0'), 'Theater recovery threw a runtime error')
    assert_true(page.evaluate('theaterFrame===document.querySelector("#videoPlayerFullscreen iframe")'), 'Theater recovery recreated the player')
    expect(player.locator('iframe')).to_have_count(1)
    return {'ordinary_mall_theater_chrome_retained': True, 'keyboard_recovery': True,
            'one_provider': True, 'real_provider': 'UNEXECUTED'}


def dog_and_camera_actions(page):
    boot(page, True)
    dock = page.locator('#videoScopePhoneDock')
    url = page.url
    dog_box = dock.locator('.mall-search-dog').bounding_box()
    camera_box = dock.locator('.mall-search-camera').bounding_box()
    plus_box = dock.locator('.mall-search-plus').bounding_box()
    expect(dock.locator('.mall-search-add')).not_to_be_visible()
    assert_true(dog_box['x'] > camera_box['x'] > plus_box['x'], 'Dog must be the rightmost primary dock action')
    dock.locator('.mall-search-dog').tap()
    dialog = page.get_by_role('dialog', name='Red Dog conversation', exact=True)
    expect(dialog).to_be_visible()
    expect(dialog.get_by_text('Conversation is not connected on this build. No microphone is recording.')).to_be_visible()
    dialog.get_by_role('button', name='Back to browsing', exact=True).click()
    assert_true(page.url == url, 'Dog navigated away')
    expect(dock.locator('.mall-search-dog')).to_be_focused()
    dock.locator('.mall-search-plus').tap()
    menu = page.locator('#videoScopeOptions[open]')
    expect(menu.locator('[data-action="browse-ai"]')).to_be_visible()
    assert_true(menu.locator(':scope > button').first.get_attribute('data-action') == 'browse-ai', 'AI was not first')
    menu.get_by_role('button', name='Close', exact=True).click()
    page.context.route('https://foundup-japan-ai-autopost-camera-56566376153.us-west1.run.app/**',
                       lambda route: route.fulfill(content_type='text/html', body='<title>Controlled AutoPost destination</title>'))
    dock.get_by_role('button', name='Open AutoPost camera', exact=True).tap()
    page.wait_for_url('https://foundup-japan-ai-autopost-camera-56566376153.us-west1.run.app/**')
    from urllib.parse import parse_qs
    assert_true(parse_qs(urlsplit(page.url).query) == {'return_to': [url]}, page.url)
    return {'dog_stays_in_context': True, 'unavailable_is_truthful': True, 'camera_same_tab': True,
            'camera_destination': page.url, 'actual_camera': 'UNEXECUTED'}


def observe_member_media(page):
    page.wait_for_function("mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    snapshot = page.evaluate('mallVideoPlayer.getPlaybackSnapshot()')
    if snapshot['provider'] == 'html5':
        page.wait_for_function("document.querySelector('#videoPlayerFullscreen video')?.currentTime>.15")
        native = page.locator('#videoPlayerFullscreen video').evaluate('e=>({duration:e.duration,width:e.videoWidth,height:e.videoHeight,time:e.currentTime,loop:e.loop,muted:e.muted,paused:e.paused})')
        assert_true(native['width'] == 480 and native['height'] == 562 and abs(native['duration']-4) < .1 and
                    native['loop'] and native['muted'] and not native['paused'], native)
        return {'kind':'native-video','decoded_playback':native}
    assert_true(snapshot['provider'] == 'image-animation' and snapshot['nativeErrorCode'] == 4 and
                snapshot['fallback'] == 'approved-animated-webp' and snapshot['positionSeconds'] is None, snapshot)
    image = page.locator('#videoPlayerFullscreen .video-player-member-animation img')
    page.wait_for_function("document.querySelector('.video-player-member-animation img')?.naturalWidth>0")
    assert_true(image.get_attribute('src').endswith('-loop.webp'), 'Fallback did not use the approved motion asset')
    first = image.screenshot()
    changed = False
    for _ in range(12):
        page.wait_for_timeout(100)
        if image.screenshot() != first:
            changed = True
            break
    assert_true(changed, 'Image fallback did not demonstrate changing frames')
    page.get_by_role('button', name='Pause card animation', exact=True).click()
    expect(image).to_have_attribute('src', __import__('re').compile(r'-still\.webp$'))
    page.wait_for_function("mallVideoPlayer.getPlaybackSnapshot()?.state==='paused'")
    paused = image.screenshot(); page.wait_for_timeout(250)
    assert_true(image.screenshot() == paused, 'Paused fallback still changed frames')
    video_action(page, 'play')
    page.wait_for_function("mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    return {'kind':'image-animation','native_error':4,'frames_changed':True,'pause_still_verified':True,
            'native_video_playback':'NOT_SUPPORTED_IN_THIS_ENVIRONMENT','media_time':None}


def vote_native_cards(page, desktop=False):
    page.emulate_media(reduced_motion='no-preference')
    if not desktop:
        page.set_viewport_size({'width': 390, 'height': 844})
    page.goto('https://play.foundups.com/member/?foundup=voteballots', wait_until='domcontentloaded')
    tiles = page.locator('#mallTileField .mall-member-card')
    expect(tiles).to_have_count(2)
    expect(page.locator('#videoScopeTitle')).to_have_text('VOTE')
    expect(page.get_by_role('textbox', name='Search VOTE cards', exact=True)).to_be_visible()
    expect(page.locator('#videoScopePhoneDock .mall-search-add')).not_to_be_visible()
    expect(page.locator('#videoScopePhoneDock .mall-search-plus')).to_have_attribute('aria-label', 'Available actions')
    assert_true(page.evaluate('!mallVideoPlayer.isOpen()'), 'VOTE forced desktop theater')
    widths = [1440, 1000] if desktop else [390, 320]
    measured = []
    for width in widths:
        page.set_viewport_size({'width': width, 'height': 900 if desktop else 844})
        for tile, expected in [(tiles.nth(0), 'Chuck Schumer'), (tiles.nth(1), 'Hakeem Jeffries')]:
            expect(tile.locator('h3')).to_have_text(expected)
            expect(tile.locator('.mall-member-card-scores')).to_contain_text('UDP Pending')
            expect(tile.locator('.mall-member-card-scores')).to_contain_text('CU Pending')
            geometry = tile.evaluate('''e=>{
              const b=e.getBoundingClientRect(),h=e.querySelector('header').getBoundingClientRect(),
                a=e.querySelector('.mall-tile-expand').getBoundingClientRect(),f=e.querySelector('footer').getBoundingClientRect();
              return {width:b.width,height:b.height,targetWidth:a.width,targetHeight:a.height,
                clearHeading:a.top>=h.bottom,clearFooter:a.bottom<=f.top,overflow:e.scrollWidth>e.clientWidth+1};
            }''')
            assert_true(geometry['targetWidth'] >= 44 and geometry['targetHeight'] >= 44 and
                        geometry['clearHeading'] and geometry['clearFooter'] and not geometry['overflow'], geometry)
            measured.append({'viewport': width, 'member': expected, **geometry})
    page.set_viewport_size({'width': 1440 if desktop else 390, 'height': 900 if desktop else 844})
    page.screenshot(path=str(OUT.with_name(OUT.stem+'-'+REPORT['engine']+'-vote-'+('desktop' if desktop else 'phone')+'.png')))
    tiles.first.focus(); page.keyboard.press('Enter')
    page.wait_for_function("mallVideoPlayer.isFloating()&&mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    player = page.locator('#videoPlayerFullscreen')
    native = observe_member_media(page)
    page.evaluate("window.retiredVoteMedia=document.querySelector('#videoPlayerFullscreen video, #videoPlayerFullscreen .video-player-member-animation')")
    stage = player.locator('.video-player-stage').bounding_box()
    card = player.locator('.video-player-member-card').bounding_box()
    assert_true(card['width'] <= stage['width']+1 and card['height'] <= stage['height']+1, {'stage':stage,'card':card})
    expect(player.locator('h2')).to_have_text('Chuck Schumer')
    expect(player.locator('iframe')).to_have_count(0)
    video_action(page, 'next')
    page.wait_for_function("mallVideoPlayer.getCurrentIndex()===1&&mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    assert_true(page.evaluate("!retiredVoteMedia.isConnected&&(retiredVoteMedia.tagName==='VIDEO'?retiredVoteMedia.paused&&!retiredVoteMedia.hasAttribute('src'):!retiredVoteMedia.querySelector('img'))"), 'Retired media remains active')
    expect(player.locator('video, .video-player-member-animation')).to_have_count(1)
    expect(player.locator('h2')).to_have_text('Hakeem Jeffries')
    video_action(page, 'expand')
    expect(player).to_have_attribute('aria-label', 'WikiTube video player')
    expect(page.locator('#videoScopePhoneDock')).to_be_visible()
    page.keyboard.press('Escape')
    page.wait_for_function('mallVideoPlayer.isMallHidden()||!mallVideoPlayer.isOpen()')
    expect(tiles.nth(1)).to_be_visible()
    query = page.get_by_role('textbox', name='Search VOTE cards', exact=True)
    query.fill('Jeffries')
    query.press('Enter')
    expect(tiles).to_have_count(1)
    expect(tiles.first.locator('h3')).to_have_text('Hakeem Jeffries')
    query.fill(''); expect(tiles).to_have_count(2)
    # Compare with the same shared floating stage, not a separately sized player.
    page.goto('https://hpc.foundups.com/member/', wait_until='domcontentloaded')
    expect(page.locator('#mallTileField .mall-tile').first).to_be_attached()
    if desktop:
        page.get_by_role('link', name='Home: HPC video tiles', exact=True).click()
        page.wait_for_function("document.documentElement.dataset.mallVideoLayout==='grid'")
    page.locator('#mallTileField .mall-tile[data-video-id]').first.focus(); page.keyboard.press('Enter')
    page.wait_for_function("mallVideoPlayer.isFloating()&&mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    reference = page.locator('#videoPlayerFullscreen .video-player-stage').bounding_box()
    assert_true(abs(reference['width']-stage['width']) < 1 and abs(reference['height']-stage['height']) < 1,
                {'vote_stage':stage,'hpc_stage':reference})
    return {'observed_media':native,'two_cards':True,'targets':measured,'same_shared_stage':True,
            'single_native_source_and_cleanup':True,'search_and_escape_return':True,'physical_iPhone':'UNEXECUTED'}


def vote_reduced_motion(page):
    page.goto('https://play.foundups.com/member/?foundup=voteballots', wait_until='domcontentloaded')
    tile = page.locator('#mallTileField .mall-member-card').first
    expect(tile).to_be_visible()
    page.wait_for_function("document.querySelector('.mall-member-card img')?.currentSrc.endsWith('-still.webp')")
    tile.focus(); page.keyboard.press('Enter')
    page.wait_for_function("mallVideoPlayer.getPlaybackSnapshot()?.state==='manual-play'")
    media = page.locator('#videoPlayerFullscreen video')
    initial = media.evaluate('e=>({paused:e.paused,time:e.currentTime,autoplay:e.autoplay,poster:e.poster})')
    assert_true(initial['paused'] and initial['time'] == 0 and not initial['autoplay'] and initial['poster'].endswith('-still.webp'), initial)
    video_action(page, 'play')
    manual = observe_member_media(page)
    page.emulate_media(reduced_motion='no-preference')
    video_action(page, 'next')
    page.wait_for_function("mallVideoPlayer.getCurrentIndex()===1&&mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    page.emulate_media(reduced_motion='reduce')
    page.wait_for_function("""()=>{
      const v=document.querySelector('#videoPlayerFullscreen video'),i=document.querySelector('.video-player-member-animation img');
      return v?v.paused&&v.currentTime===0&&!v.autoplay:i?.getAttribute('src').endsWith('-still.webp')&&mallVideoPlayer.getPlaybackSnapshot()?.state==='paused';
    }""")
    validity = page.evaluate('''()=>{
      const good={source_url:'/member/vote/comics/schumer-card-loop.mp4',member_card:{name:'Chuck Schumer',chamber:'U.S. Senate',
        constituency:'New York',hashtag:'#SchumerOUT',still_url:'/member/vote/comics/schumer-card-still.webp',
        animation_url:'/member/vote/comics/schumer-card-loop.webp',udp_score:null,cu_score:null}};
      return [mallVideoPlayer.isMemberCardVideo(good), ...[
        {source_url:'https://external.example/card.mp4'}, {embed_url:'https://www.youtube.com/embed/iJuguXpbRR4'},
        {source_url:'/member/vote/comics/../schumer-card-loop.mp4'},
        {member_card:{...good.member_card,udp_score:90}}, {member_card:{...good.member_card,still_url:'/other.webp'}}
      ].map(change=>mallVideoPlayer.isMemberCardVideo({...good,...change}))];
    }''')
    assert_true(validity == [True,False,False,False,False,False], validity)
    page.emulate_media(reduced_motion='no-preference')
    video_action(page, 'previous')
    page.wait_for_function("mallVideoPlayer.getCurrentIndex()===0&&mallVideoPlayer.getPlaybackSnapshot()?.state==='playing'")
    app_touch(page, page.locator('.video-player-gesture-grip'), dx=85)
    page.wait_for_function('mallVideoPlayer.isTucked()')
    app_touch(page, page.locator('.video-player-tuck-handle'), dx=26, start_fraction=.25)
    page.wait_for_function("mallVideoPlayer.isTucked()&&mallVideoPlayer.getCurrentIndex()===1&&mallVideoPlayer.getPlaybackSnapshot()?.state==='selected-hidden'")
    expect(page.locator('#videoPlayerFullscreen video, #videoPlayerFullscreen .video-player-member-animation')).to_have_count(0)
    return {'initial_still_and_paused':initial,'manual_play':manual,'live_motion_change_stops':True,
            'typed_media_boundary':validity,'hidden_next_has_no_active_media':True,'physical_iPhone':'UNEXECUTED'}


def run_case(browser, name, fn, block=False, block_storage=False, silent_start=False, desktop=False, hold_ready=False):
    if args.case and name not in args.case:return
    REPORT['active_case'] = name
    context, page, transport = make_page(browser, block, block_storage, silent_start, desktop, hold_ready)
    row = {'engine': REPORT['engine'], 'case': name, 'passed': False, 'transport':transport}
    page_errors=[]
    page.on('pageerror',lambda error:page_errors.append(str(error)))
    graph_requests=[]
    page.on('request',lambda request:graph_requests.append(request.url) if '/pfmall/tile-graph/' in urlsplit(request.url).path else None)
    try:
        row['evidence'] = fn(page)
        assert_true(not page_errors, {'page_errors':page_errors})
        assert_true(not graph_requests, {'protected_graph_requests':graph_requests})
        assert_true(transport['websockets_blocked']==0, {'unexpected_websockets':transport})
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
              focused:document.activeElement?.outerHTML?.slice(0,400),
              native:[...document.querySelectorAll('#videoPlayerFullscreen video')].map(e=>({
                src:e.getAttribute('src'),error:e.error?{code:e.error.code,message:e.error.message}:null,
                ready:e.readyState,network:e.networkState,paused:e.paused,time:e.currentTime}))})""")
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
                run_case(browser, 'floating-frame-controls', floating_frame_controls)
                run_case(browser, 'clean-video-gestures', clean_video_gestures)
                run_case(browser, 'tucked-next-stays-hidden', tucked_next_stays_hidden)
                run_case(browser, 'hpc-home-shared-desktop-dock', hpc_home_shared_desktop_dock, desktop=True)
                run_case(browser, 'theater-clean-control-regression', theater_clean_control_regression, desktop=True)
                run_case(browser, 'dog-and-camera-actions', dog_and_camera_actions)
                run_case(browser, 'vote-native-cards', vote_native_cards)
                run_case(browser, 'vote-native-desktop', lambda page: vote_native_cards(page, True), desktop=True)
                run_case(browser, 'vote-reduced-motion', vote_reduced_motion)
                run_case(browser, 'conditional-manual-recovery', blocked_recovery, True)
                run_case(browser, 'silent-start-provider-unknown', silent_start_unknown, silent_start=True)
            finally:
                browser.close()
finally:
    REPORT['source_sha256_after'] = hashes()
    REPORT['source_stable'] = REPORT['source_sha256_before'] == REPORT['source_sha256_after']
    REPORT['elapsed_seconds'] = round(time.time() - REPORT['started_epoch'], 3)
    REPORT['status'] = 'PASS' if (len(REPORT['cases']) == (2*len(set(args.case)) if args.case else (72 if args.include_defensive else 70)) and
        all(row['passed'] for row in REPORT['cases']) and REPORT['source_stable']) else 'FAIL'
    save()
sys.exit(0 if REPORT['status'] == 'PASS' else 1)
