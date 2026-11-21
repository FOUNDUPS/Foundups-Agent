"""Bounded public TV/network regression using the existing local fixtures.

Run from the repository root. Routes, accounts and provider events are fixtures;
no real YouTube, Google session, live TLS or physical iPhone claim is made.
"""
from pathlib import Path
from urllib.parse import urlsplit
import hashlib
import json
import sys
import time
import traceback
import subprocess
from playwright.sync_api import expect, sync_playwright
import mall_scoped_video_browser as base

ROOT = Path.cwd()
PUBLIC = ROOT / 'public'
OUT = ROOT.parent / 'mall_v26_public_tv_qa.json'
REPORT = {'provider': 'existing controlled YT API fixture', 'physical_iPhone': 'UNEXECUTED',
          'landscape_acceptance':'Explicit root update: 390px-high phone landscape may reserve a left grid and right player; all visible tiles/header/CTAs must avoid player, retain >=200 stage. Portrait remains player above grid. Initial collision receipts retained.',
          'cases': [], 'started_epoch': time.time(), 'source_sha256_before': {}}

def hashes():
    paths = [ROOT / p for p in ('public/member/index.html', 'public/member/member-sw.js',
        'public/member/js/mall-discovery-pager.js', 'public/member/js/mall-tile-field.js',
        'public/member/css/mall-tile-field.css', 'public/member/js/mall-video-player.js',
        'public/member/css/mall-video-player.css', 'public/member/js/mall-video-projection.js',
        'public/member/js/mall-state-restore.js', 'public/member/tests/mall_public_tv_browser.py')]
    paths += sorted((PUBLIC / 'member/discovery').rglob('*.json'))
    return {str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}

def check(name, condition, detail=None):
    REPORT['cases'].append({'name': name, 'passed': bool(condition), 'detail': detail})
    if not condition:
        raise AssertionError({'name': name, 'detail': detail})

def local_json(path):
    candidate = (PUBLIC / path.lstrip('/')).resolve()
    assert candidate.is_relative_to(PUBLIC.resolve())
    return json.loads(candidate.read_text(encoding='utf-8'))

class Ledger:
    def __init__(self):
        self.rows = []
        self.fail_once = set()
        self.hold_once = set()
        self.held = []
        self.failed = []

    def route(self, route):
        path = urlsplit(route.request.url).path
        if path.startswith('/member/discovery/') and path.endswith('.json'):
            filename = (PUBLIC / path.lstrip('/')).resolve()
            if filename.is_file() and filename.is_relative_to(PUBLIC.resolve()):
                body = filename.read_bytes()
                data = json.loads(body)
                row = {'path': path, 'bytes':len(body), 'status':200,'kind':data.get('kind'),
                       'record_id':data.get('record_id'), 'page':data.get('page'),
                       'count':len(data.get('items',[])),
                       'video_arrays':any('videos' in x for x in data.get('items',[]))}
                self.rows.append(row)
                if path in self.fail_once:
                    self.fail_once.remove(path)
                    error='{"error":"controlled_page_failure"}'
                    row.update(status=503,bytes=len(error),source_count=row['count'],count=0)
                    route.fulfill(status=503,content_type='application/json',body=error)
                elif path in self.hold_once:
                    self.hold_once.remove(path)
                    row.update(status='held',source_count=row['count'],count=0,source_bytes=len(body),bytes=0)
                    self.held.append((route, body, path,row))
                else:
                    route.fulfill(status=200,content_type='application/json',body=body)
                return
        if path in ('/member/mall-video-catalog.json','/member/mall-public-video-catalog.json'):
            self.rows.append({'path':path,'kind':'legacy_raw'})
        base.route_local(route)

    def release(self):
        held, self.held = self.held, []
        for route,body,path,row in held:
            try:
                route.fulfill(status=200,content_type='application/json',body=body)
                row.update(status='released',bytes=len(body),count=row['source_count'])
            except Exception as exc:
                self.failed.append({'path':path,'release_error':str(exc)[:180]})

def context_for(browser, width=390, height=844, disable_io=False):
    context = browser.new_context(viewport={'width':width,'height':height},
        is_mobile=width<900,has_touch=width<900,service_workers='block',reduced_motion='reduce')
    context.add_init_script(base.provider)
    context.add_init_script("""(() => {const original=window.fetch;window.fixtureDiscoveryAbort=[];window.fetch=function(input,options){const url=typeof input==='string'?input:input.url;if(url.includes('/member/discovery/')&&options?.signal)options.signal.addEventListener('abort',()=>window.fixtureDiscoveryAbort.push(new URL(url,location.origin).pathname),{once:true});return original.apply(this,arguments)}})()""")
    if disable_io:
        context.add_init_script('window.IntersectionObserver=undefined')
    ledger = Ledger()
    context.route('**/*',ledger.route)
    page = context.new_page()
    page.set_default_timeout(6000)
    page.on('requestfailed',lambda request:ledger.failed.append({'path':urlsplit(request.url).path,'failure':request.failure}))
    return context,page,ledger

def boot(page):
    page.goto('https://play.foundups.com/member/',wait_until='domcontentloaded')
    expect(page.locator('#mallTileField .mall-tile').first).to_be_visible()

def expect_ids(page, ids):
    page.wait_for_function('ids=>{const els=[...document.querySelectorAll("#mallTileField .mall-tile")];return els.length===ids.length&&els.every((el,i)=>el.dataset.videoId===ids[i])}',arg=ids)
    expect(page.locator('#mallTileField .mall-tile')).to_have_count(len(ids))
    actual=page.locator('#mallTileField .mall-tile').evaluate_all('els=>els.map(x=>x.dataset.videoId)')
    check('selected grid contains expected video IDs only',actual==ids,actual)

def geometry(page):
    return page.evaluate("""() => {
      const p=document.querySelector('#videoPlayerFullscreen'),s=p.querySelector('.video-player-stage'),f=s.querySelector('iframe'),t=document.querySelector('#mallTileField .mall-tile'),w=document.querySelector('#mallTileField').parentElement;
      const r=f.getBoundingClientRect(),b=p.getBoundingClientRect(),g=t.getBoundingClientRect(),wr=w.getBoundingClientRect();
      const area=Math.max(0,Math.min(r.right,innerWidth)-Math.max(r.left,0))*Math.max(0,Math.min(r.bottom,innerHeight)-Math.max(r.top,0));
      const overlapping=[...p.querySelectorAll('.video-player-top-bar button,.video-player-top-bar a,.video-player-manual-play')].filter(x=>!x.hidden&&x.getClientRects().length).filter(x=>{const q=x.getBoundingClientRect();return Math.min(q.right,r.right)>Math.max(q.left,r.left)&&Math.min(q.bottom,r.bottom)>Math.max(q.top,r.top)}).length;
      const visibleTiles=[...document.querySelectorAll('#mallTileField .mall-tile')].map(el=>{const q=el.getBoundingClientRect(),v={left:Math.max(q.left,wr.left,0),right:Math.min(q.right,wr.right,innerWidth),top:Math.max(q.top,wr.top,0),bottom:Math.min(q.bottom,wr.bottom,innerHeight)};return {id:el.dataset.videoId,rect:q.toJSON(),visible:v,playerIntersection:Math.max(0,Math.min(v.right,b.right)-Math.max(v.left,b.left))*Math.max(0,Math.min(v.bottom,b.bottom)-Math.max(v.top,b.top)),iframeIntersection:Math.max(0,Math.min(v.right,r.right)-Math.max(v.left,r.left))*Math.max(0,Math.min(v.bottom,r.bottom)-Math.max(v.top,r.top))}});
      const headerOverlap=[...document.querySelectorAll('.mall-header button,.mall-header a,.mall-header input')].filter(el=>!el.hidden&&el.getClientRects().length).map(el=>{const q=el.getBoundingClientRect();return {name:el.getAttribute('aria-label')||el.textContent.trim(),area:Math.max(0,Math.min(q.right,b.right)-Math.max(q.left,b.left))*Math.max(0,Math.min(q.bottom,b.bottom)-Math.max(q.top,b.top))}}).filter(x=>x.area>0);
      return {iframe:{width:r.width,height:r.height,visible:area/(r.width*r.height)},player:b.toJSON(),tile:g.toJSON(),wrapper:wr.toJSON(),wrapperScrollTop:w.scrollTop,wrapperHeight:w.clientHeight,visibleTiles,headerOverlap,overlappingControls:overlapping,theater:window.mallVideoPlayer.isTheater(),floating:window.mallVideoPlayer.isFloating()};
    }""")

def diagnostic_geometry(page):
    """Collect layout details only after the original acceptance snapshot fails."""
    return page.evaluate("""() => {
      const beforeLayoutRead={at:performance.now(),innerWidth,innerHeight,compactLandscape:matchMedia('(orientation: landscape) and (max-height: 500px)').matches};
      const p=document.querySelector('#videoPlayerFullscreen'),s=p.querySelector('.video-player-stage'),f=s.querySelector('iframe'),t=document.querySelector('#mallTileField .mall-tile'),w=document.querySelector('#mallTileField').parentElement;
      const r=f.getBoundingClientRect(),b=p.getBoundingClientRect(),g=t.getBoundingClientRect(),wr=w.getBoundingClientRect();
      const area=Math.max(0,Math.min(r.right,innerWidth)-Math.max(r.left,0))*Math.max(0,Math.min(r.bottom,innerHeight)-Math.max(r.top,0));
      const overlapping=[...p.querySelectorAll('.video-player-top-bar button,.video-player-top-bar a,.video-player-manual-play')].filter(x=>!x.hidden&&x.getClientRects().length).filter(x=>{const q=x.getBoundingClientRect();return Math.min(q.right,r.right)>Math.max(q.left,r.left)&&Math.min(q.bottom,r.bottom)>Math.max(q.top,r.top)}).length;
      const visibleTiles=[...document.querySelectorAll('#mallTileField .mall-tile')].map(el=>{const q=el.getBoundingClientRect(),v={left:Math.max(q.left,wr.left,0),right:Math.min(q.right,wr.right,innerWidth),top:Math.max(q.top,wr.top,0),bottom:Math.min(q.bottom,wr.bottom,innerHeight)};return {id:el.dataset.videoId,rect:q.toJSON(),visible:v,playerIntersection:Math.max(0,Math.min(v.right,b.right)-Math.max(v.left,b.left))*Math.max(0,Math.min(v.bottom,b.bottom)-Math.max(v.top,b.top)),iframeIntersection:Math.max(0,Math.min(v.right,r.right)-Math.max(v.left,r.left))*Math.max(0,Math.min(v.bottom,r.bottom)-Math.max(v.top,r.top))}});
      const headerOverlap=[...document.querySelectorAll('.mall-header button,.mall-header a,.mall-header input')].filter(el=>!el.hidden&&el.getClientRects().length).map(el=>{const q=el.getBoundingClientRect();return {name:el.getAttribute('aria-label')||el.textContent.trim(),area:Math.max(0,Math.min(q.right,b.right)-Math.max(q.left,b.left))*Math.max(0,Math.min(q.bottom,b.bottom)-Math.max(q.top,b.top))}}).filter(x=>x.area>0);
      const root=document.documentElement,header=document.querySelector('.mall-header'),viewport=window.visualViewport;
      const layout={beforeLayoutRead,at:performance.now(),innerWidth,innerHeight,clientWidth:root.clientWidth,clientHeight:root.clientHeight,visibility:document.visibilityState,compactLandscape:matchMedia('(orientation: landscape) and (max-height: 500px)').matches,clearance:root.style.getPropertyValue('--floating-player-clearance'),gridPadding:getComputedStyle(document.querySelector('#mallTileField')).paddingTop,header:header?.getBoundingClientRect().toJSON(),floatingTop:p.style.getPropertyValue('--floating-top'),viewport:viewport?{width:viewport.width,height:viewport.height,scale:viewport.scale,offsetTop:viewport.offsetTop}:null};
      return {iframe:{width:r.width,height:r.height,visible:area/(r.width*r.height)},player:b.toJSON(),tile:g.toJSON(),wrapper:wr.toJSON(),wrapperScrollTop:w.scrollTop,wrapperHeight:w.clientHeight,visibleTiles,headerOverlap,overlappingControls:overlapping,theater:window.mallVideoPlayer.isTheater(),floating:window.mallVideoPlayer.isFloating(),layout};
    }""")

def verify_boot_and_selection(engine):
    browser=engine.launch()
    context,page,ledger=context_for(browser)
    try:
        boot(page)
        page.wait_for_timeout(180)
        meta=[x for x in ledger.rows if x.get('kind')=='catalog']
        check(engine.name+' native IO boot metadata is bounded to six',sum(x['count'] for x in meta)<=6,meta)
        check(engine.name+' public boot avoids raw video catalogs',not any(x['kind']=='legacy_raw' for x in ledger.rows),ledger.rows)
        check(engine.name+' boot metadata has no video arrays',all(not x['video_arrays'] for x in meta),meta)
        first=local_json('/member/discovery/catalog.json')
        record=next(x for x in first['items'] if x['foundup_id']=='move2japan')
        videos=local_json(record['video_pages']['catalog'])
        expected=[x['video_id'] for x in videos['items']]
        page.locator('#mallTileField [data-foundup-id="move2japan"]').tap(position={'x':30,'y':50})
        expect_ids(page,expected)
        base.expect_playing_id(page,expected[0])
        check(engine.name+' one tap opens one floating player',page.evaluate('window.fixturePlayback.created===1&&window.mallVideoPlayer.isFloating()&&!window.mallVideoPlayer.isWikiTube()'))
        check(engine.name+' selected label states Catalog order','Catalog order' in page.locator('.mall-selected-label').inner_text())
        selected=[x for x in ledger.rows if x.get('kind')=='videos']
        check(engine.name+' selection fetches only six videos for selected lane',len(selected)==1 and selected[0]['record_id']=='move2japan' and selected[0]['count']==6,selected)
        page.evaluate('window.tvFrame=document.querySelector("#videoPlayerFullscreen iframe")')
        # Plain control: preserve the original success-path geometry read order.
        # Detailed layout diagnostics run only after a frozen 90ms failure.
        rotations=5 if engine.name=='webkit' else 1
        for width,height in [(390,844)]+[(844,390),(390,844)]*rotations:
            page.set_viewport_size({'width':width,'height':height})
            page.wait_for_timeout(90)
            g=geometry(page)
            clear=((g['tile']['y']>=g['player']['bottom']-1) if height>width else all(x['playerIntersection']==0 for x in g['visibleTiles'])) and not g['headerOverlap']
            accepted=g['floating'] and min(g['iframe']['width'],g['iframe']['height'])>=200 and g['iframe']['visible']>.5 and clear and g['overlappingControls']==0 and g['player']['top']>=-1 and g['player']['bottom']<=height+1
            if not accepted:
                # Preserve the original 90ms failure. Later observations diagnose
                # delivery timing; neither waiting nor manual sync can turn it into a pass.
                diagnostic={'engine':engine.name,'target':[width,height],'at_failure':g,
                            'after_failure_diagnostics':diagnostic_geometry(page),'later':[]}
                for delay in (200,800):
                    page.wait_for_timeout(delay)
                    diagnostic['later'].append(diagnostic_geometry(page))
                page.evaluate('window.mallVideoPlayer.syncFloatingGeometry()')
                diagnostic['after_explicit_sync']=diagnostic_geometry(page)
                REPORT.setdefault('layout_failure_diagnostics',[]).append(diagnostic)
            check(engine.name+f' {width}x{height} approved responsive player clearance',accepted,g)
        check(engine.name+' orientation keeps one iframe',page.evaluate('window.tvFrame===document.querySelector("#videoPlayerFullscreen iframe")&&window.fixturePlayback.created===1'))
        before=page.locator('#videoPlayerFullscreen').bounding_box()
        page.locator('#mallTileField').evaluate('el=>el.parentElement.scrollTop=el.parentElement.scrollHeight')
        after=page.locator('#videoPlayerFullscreen').bounding_box()
        check(engine.name+' grid scroll leaves player stationary',abs(before['y']-after['y'])<=1,{'before':before,'after':after})
        page.get_by_role('button',name='Back to Mall',exact=True).click()
        expect(page.locator('.mall-selected-controls')).to_be_hidden()
        expect(page.locator('#mallTileField [data-foundup-id="move2japan"]')).to_be_focused()
        check(engine.name+' Back to Mall closes player',page.evaluate('!window.mallVideoPlayer.isOpen()'))
        REPORT.setdefault('request_ledgers',[]).append({'engine':engine.name,'case':'native boot and normal tap','rows':ledger.rows})
    finally:
        ledger.release()
        context.close()
        browser.close()

def metadata_record(identifier):
    path='/member/discovery/catalog.json'
    seen=set()
    while path:
        assert path not in seen
        seen.add(path)
        data=local_json(path)
        for record in data['items']:
            if record['foundup_id']==identifier: return record
        path=data['next']
    raise AssertionError('Missing metadata record '+identifier)

def load_all_cards(page):
    field=page.locator('#mallTileField')
    for _ in range(4):
        count=field.locator('.mall-tile').count()
        if count==17: return
        assert count<17,count
        page.get_by_role('button',name='Load more cards',exact=True).click()
        page.wait_for_function('n=>document.querySelectorAll("#mallTileField .mall-tile").length>n',arg=count)
    expect(field.locator('.mall-tile')).to_have_count(17)

def dispatch_tile_pinch(locator, start, end):
    # The general gesture engine computes its final distance from touchend;
    # the existing player helper reacts on touchmove and has one changedTouch.
    # Supply both lifted fingers for a valid simultaneous two-finger ending.
    locator.evaluate("""(el,[start,end])=>{for(const [type,distance]of[['touchstart',start],['touchmove',end]]){const event=new Event(type,{bubbles:true,cancelable:true});Object.defineProperty(event,'touches',{value:[{clientX:60,clientY:80},{clientX:60+distance,clientY:80}]});el.dispatchEvent(event)}const event=new Event('touchend',{bubbles:true,cancelable:true});Object.defineProperty(event,'touches',{value:[]});Object.defineProperty(event,'changedTouches',{value:[{clientX:60,clientY:80},{clientX:60+end,clientY:80}]});el.dispatchEvent(event)}""",[start,end])

def verify_paging_return_and_gestures(engine):
    browser=engine.launch()
    context,page,ledger=context_for(browser,disable_io=True)
    try:
        boot(page)
        expect(page.locator('#mallTileField .mall-tile')).to_have_count(6)
        load_all_cards(page)
        record=metadata_record('move2japan')
        p0=local_json(record['video_pages']['catalog']);p1=local_json(p0['next']);p2=local_json(p1['next'])
        ids0=[x['video_id'] for x in p0['items']]
        ids1=[x['video_id'] for x in p1['items']]
        ids2=[x['video_id'] for x in p2['items']]
        move=page.locator('#mallTileField [data-foundup-id="move2japan"]')
        move.tap(position={'x':30,'y':50});expect_ids(page,ids0)
        base.expect_playing_id(page,ids0[0])
        page.evaluate('window.pagingFrame=document.querySelector("#videoPlayerFullscreen iframe")')
        # Ending the last loaded video must request the next bounded page.
        page.evaluate('window.mallVideoPlayer.selectVideo(5,{autoplay:true})')
        base.expect_playing_id(page,ids0[5]);page.evaluate('window.fixturePlayback.finishCurrent()')
        base.expect_playing_id(page,ids1[0])
        expect_ids(page,ids0+ids1)
        check(engine.name+' end-of-page appends exactly six unique selected videos',len(set(ids0+ids1))==12)
        check(engine.name+' queue refresh retains twelve loaded videos',page.evaluate('window.mallVideoPlayer.getQueueLength()===12'))
        check(engine.name+' queue crosses six-to-twelve on same iframe',page.evaluate('window.pagingFrame===document.querySelector("#videoPlayerFullscreen iframe")'))
        ledger.fail_once.add(p1['next'])
        page.get_by_role('button',name='Load more videos',exact=True).click()
        expect(page.get_by_text('Could not load the next videos. Use Load more videos to retry.',exact=True)).to_be_visible()
        expect_ids(page,ids0+ids1)
        check(engine.name+' failed More preserves live selected player',page.evaluate('window.mallVideoPlayer.isOpen()&&window.pagingFrame===document.querySelector("#videoPlayerFullscreen iframe")'))
        page.get_by_role('button',name='Load more videos',exact=True).click()
        expect_ids(page,ids0+ids1+ids2)
        check(engine.name+' manual More retry appends six without duplicates',len(set(ids0+ids1+ids2))==18)
        paths=[x['path'] for x in ledger.rows if x.get('kind')=='videos']
        check(engine.name+' failed cursor retries same page and never another lane',paths==[record['video_pages']['catalog'],p0['next'],p1['next'],p1['next']],paths)
        # Selected logo is a Mall return; outside selection it remains Portal.
        page.locator('.mall-header .mall-brand-minimal').click()
        expect(page.locator('.mall-selected-controls')).to_be_hidden()
        expect(page.locator('#mallTileField [data-foundup-id="move2japan"]')).to_be_focused()
        check(engine.name+' selected logo returns without navigation',page.url=='https://play.foundups.com/member/' and page.evaluate('!window.mallVideoPlayer.isOpen()'))
        expect(page.locator('.mall-header .mall-brand-minimal')).to_have_attribute('href','https://foundups.com/')
        # Pinch is a synthetic gesture fixture, not physical Safari proof.
        dispatch_tile_pinch(page.locator('#mallTileField [data-foundup-id="move2japan"]'),40,105)
        expect_ids(page,ids0);base.expect_playing_id(page,ids0[0])
        base.dispatch_pinch(page.locator('#videoPlayerFullscreen .video-player-stage'),120,48)
        check(engine.name+' player surface pinch is reserved for provider/browser',page.evaluate('window.mallTileField.isExpanded()&&window.mallVideoPlayer.isOpen()'))
        base.dispatch_pinch(page.locator('#videoPlayerFullscreen .video-player-top-bar'),120,48)
        expect(page.locator('.mall-selected-controls')).to_be_hidden()
        expect(page.locator('#mallTileField [data-foundup-id="move2japan"]')).to_be_focused()
        check(engine.name+' application pinch returns to Mall',page.evaluate('!window.mallTileField.isExpanded()&&!window.mallVideoPlayer.isOpen()'))
        # A real nonzero browse position and a source-group filter are restored.
        load_all_cards(page)
        page.locator('#mallTileField').evaluate('el=>el.parentElement.scrollTo({top:300,behavior:"instant"})')
        eduit=page.locator('#mallTileField [data-foundup-id="eduit"]')
        eduit.scroll_into_view_if_needed()
        saved=page.locator('#mallTileField').evaluate('el=>el.parentElement.scrollTop')
        check(engine.name+' return-position precondition is nonzero',saved>0,saved)
        eduit.tap(position={'x':30,'y':50})
        page.wait_for_function('window.mallTileField.isExpanded()&&window.mallVideoPlayer.isOpen()')
        page.get_by_role('button',name='Back to Mall',exact=True).click()
        page.wait_for_function('top=>Math.abs(document.querySelector("#mallTileField").parentElement.scrollTop-top)<=2',arg=saved)
        expect(page.locator('#mallTileField [data-foundup-id="eduit"]')).to_be_focused()
        check(engine.name+' Back restores nonzero browse position and selected card',True,{'scrollTop':saved,'id':'eduit'})
        page.evaluate('window.mallTileField.filterBySourceGroup("videos")')
        scope=page.evaluate('window.mallTileField.getFieldScope()')
        page.locator('#mallTileField [data-foundup-id="move2japan"]').tap(position={'x':30,'y':50})
        page.wait_for_function('window.mallTileField.isExpanded()&&window.mallVideoPlayer.isOpen()')
        page.get_by_role('button',name='Back to Mall',exact=True).click()
        check(engine.name+' Back preserves Mall source-group filter',page.evaluate('window.mallTileField.getFieldScope()')==scope,scope)
        check(engine.name+' only Catalog order is claimed','popular' not in page.locator('.mall-selected-controls').inner_text().lower())
    finally:
        REPORT.setdefault('request_ledgers',[]).append({'engine':engine.name,'case':'manual paging, cursor retry, queue and return','rows':ledger.rows,'failed':ledger.failed})
        ledger.release();context.close();browser.close()

def verify_pending_selection_failures(engine):
    browser=engine.launch()
    context,page,ledger=context_for(browser,disable_io=True)
    try:
        boot(page)
        move=metadata_record('move2japan');undaodu=metadata_record('undaodu')
        target=move['video_pages']['catalog']
        ids0=[x['video_id'] for x in local_json(target)['items']]
        ledger.fail_once.add(target)
        page.locator('#mallTileField [data-foundup-id="move2japan"]').tap(position={'x':30,'y':50})
        expect(page.get_by_text('Could not load videos. Select the card to retry.',exact=True)).to_be_visible()
        check(engine.name+' failed first page does not create playback',page.evaluate('!window.mallVideoPlayer?.isOpen?.()'))
        page.locator('#mallTileField [data-foundup-id="move2japan"]').tap(position={'x':30,'y':50})
        expect_ids(page,ids0);base.expect_playing_id(page,ids0[0])
        page.get_by_role('button',name='Back to Mall',exact=True).click()
        check(engine.name+' first page retry succeeds using same verified cursor',len([x for x in ledger.rows if x['path']==target])==2)
        # Explicit lookup may fetch small metadata pages, but a zero-video card
        # must cancel a previously loading video selection and return false.
        ledger.hold_once.add(target)
        page.locator('#mallTileField [data-foundup-id="move2japan"]').tap(position={'x':30,'y':50})
        page.wait_for_function('document.querySelector(".mall-selected-label").textContent.startsWith("Loading")')
        check(engine.name+' zero-video metadata lookup precondition is unloaded',page.evaluate('!window.mallTileField.getLoadedCatalog().some(x=>x.foundup_id==="voteballots")'))
        result=page.evaluate('async()=>await window.mallTileField.openEntityById("voteballots")')
        check(engine.name+' unloaded zero-video lookup honestly returns false',result is False,result)
        expect(page.locator('.mall-selected-controls')).to_be_hidden()
        check(engine.name+' explicit metadata lookup materializes Vote without videos',page.evaluate('window.mallTileField.getLoadedCatalog().some(x=>x.foundup_id==="voteballots")&&!window.mallTileField.isExpanded()&&!window.mallVideoPlayer.isOpen()'))
        ledger.release();page.wait_for_timeout(80)
        check(engine.name+' late aborted page cannot reopen zero-video selection',page.evaluate('!window.mallTileField.isExpanded()&&!window.mallVideoPlayer.isOpen()'))
        # Another normal tap owns the selection before the old response arrives.
        ledger.hold_once.add(target)
        page.locator('#mallTileField [data-foundup-id="move2japan"]').tap(position={'x':30,'y':50})
        page.wait_for_function('document.querySelector(".mall-selected-label").textContent.startsWith("Loading")')
        page.locator('#mallTileField [data-foundup-id="undaodu"]').tap(position={'x':30,'y':50})
        expected=[x['video_id'] for x in local_json(undaodu['video_pages']['catalog'])['items']]
        expect_ids(page,expected);base.expect_playing_id(page,expected[0])
        page.evaluate('window.staleFrame=document.querySelector("#videoPlayerFullscreen iframe")')
        ledger.release();page.wait_for_timeout(80)
        expect_ids(page,expected)
        check(engine.name+' stale initial selection cannot replace newer lane',page.evaluate('window.mallVideoPlayer.getFoundUpId()==="undaodu"&&window.staleFrame===document.querySelector("#videoPlayerFullscreen iframe")'))
        check(engine.name+' actual fetch signals were aborted for superseded scope',target in page.evaluate('window.fixtureDiscoveryAbort'))
        page.locator('#videoPlayerFullscreen').get_by_role('button',name='Close player',exact=True).click()
        expect(page.locator('[data-selected-watch]')).to_be_visible()
        page.get_by_role('button',name='Watch',exact=True).click()
        base.expect_playing_id(page,expected[0])
        check(engine.name+' Watch is an accessible resume alternative',page.evaluate('window.mallVideoPlayer.isOpen()'))
    finally:
        REPORT.setdefault('request_ledgers',[]).append({'engine':engine.name,'case':'first-page retry, zero-video cancel, stale response','rows':ledger.rows,'failed':ledger.failed})
        ledger.release();context.close();browser.close()

def verify_desktop_selected_theater(engine):
    browser=engine.launch()
    context,page,ledger=context_for(browser,1366,900,disable_io=True)
    try:
        boot(page)
        record=metadata_record('move2japan')
        expected=[x['video_id'] for x in local_json(record['video_pages']['catalog'])['items']]
        page.locator('#mallTileField [data-foundup-id="move2japan"]').click(position={'x':30,'y':50})
        base.expect_playing_id(page,expected[0])
        check(engine.name+' desktop keeps existing theater',page.evaluate('window.mallVideoPlayer.isTheater()&&!window.mallVideoPlayer.isFloating()'))
        frame=page.locator('#videoPlayerFullscreen iframe').bounding_box()
        check(engine.name+' desktop theater keeps minimum player dimensions',min(frame['width'],frame['height'])>=200,frame)
        page.get_by_role('button',name='Back to Mall',exact=True).click()
        check(engine.name+' desktop Back restores Mall discovery',page.evaluate('!window.mallTileField.isExpanded()&&!window.mallVideoPlayer.isOpen()'))
    finally:
        REPORT.setdefault('request_ledgers',[]).append({'engine':engine.name,'case':'desktop theater','rows':ledger.rows})
        ledger.release();context.close();browser.close()

def main():
    REPORT['source_sha256_before']=hashes()
    try:
        with sync_playwright() as p:
            for engine in (p.chromium,p.webkit):
                verify_boot_and_selection(engine)
                verify_paging_return_and_gestures(engine)
                verify_pending_selection_failures(engine)
                verify_desktop_selected_theater(engine)
        REPORT['exit_code']=0
    except Exception:
        REPORT['exit_code']=1
        REPORT['failure']=traceback.format_exc()
    finally:
        REPORT['source_sha256_after']=hashes()
        REPORT['source_stable']=REPORT['source_sha256_before']==REPORT['source_sha256_after']
        REPORT['elapsed_seconds']=round(time.time()-REPORT['started_epoch'],3)
        OUT.write_text(json.dumps(REPORT,indent=2,sort_keys=True),encoding='utf-8')
        print(json.dumps({'receipt':str(OUT),'exit_code':REPORT['exit_code'],'source_stable':REPORT['source_stable'],'elapsed_seconds':REPORT['elapsed_seconds'],'failure':REPORT.get('failure')},indent=2))
    raise SystemExit(REPORT['exit_code'])

if __name__=='__main__':
    if '--worker' in sys.argv:
        main()
    else:
        # Same bounded supervisor pattern as the existing QA wrapper. The only
        # termination target is this invocation's own child process tree.
        process=subprocess.Popen([sys.executable,'-B','-u',__file__,'--worker'],
            cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            stdout,stderr=process.communicate(timeout=155)
        except subprocess.TimeoutExpired:
            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,timeout=10)
            stdout,stderr=process.communicate(timeout=10)
            OUT.write_text(json.dumps({'exit_code':124,'deadline_seconds':155,
                'cleanup':'owned child tree terminated','physical_iPhone':'UNEXECUTED'},indent=2),encoding='utf-8')
            print(str(OUT))
            raise SystemExit(124)
        print(stdout,end='')
        if stderr: print(stderr,file=sys.stderr,end='')
        raise SystemExit(process.returncode)
