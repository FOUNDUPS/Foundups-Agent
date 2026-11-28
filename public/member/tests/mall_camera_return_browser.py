"""Optional Dock-focus return contract; existing shell/fixtures, no real provider.

The tiny AutoPost receiver below models only its admitted return link. Actual
compiled AutoPost, hardware, BFCache and physical PWA checks remain separate.
"""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import sys
import time
import traceback
from urllib.parse import parse_qs, urlsplit

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / 'public/member/tests'))
import mall_scoped_video_browser as fixture
from playwright.sync_api import expect, sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument('--out', type=Path, default=Path(os.environ.get('HPC_EVIDENCE_DIR', str(ROOT.parent / 'hpc-camera-return-evidence'))) / 'camera-return.json')
parser.add_argument('--case', choices=['source-ordering'])
args = parser.parse_args()
args.out.parent.mkdir(parents=True, exist_ok=True)
KEY = 'pfmall_camera_focus_return_v1'
CALLER = 'https://hpc.foundups.com/member/'
CAMERA = 'foundup-japan-ai-autopost-camera-56566376153.us-west1.run.app'
report = {'provider': 'Controlled Mall/API and link-only AutoPost receiver; all network intercepted',
          'physical_iPhone': 'NOT_VERIFIED', 'native_BFCache': 'NOT_VERIFIED', 'cases': []}

def digest():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in
            ['public/member/js/mall-video-projection.js', 'public/member/tests/mall_camera_return_browser.py', 'public/member/tests/mall_scoped_video_browser.py']}

def route_local(route):
    url = urlsplit(route.request.url)
    if url.hostname == CAMERA:
        returned = parse_qs(url.query).get('return_to', [''])[0]
        route.fulfill(status=200, content_type='text/html', body='<a id="caller" href="' + html.escape(returned, quote=True) + '">Return to caller</a>')
    else:
        fixture.route_local(route)

def negative_profile(kind):
    # Every input here is synthetic. Never inspect a device/account/session.
    return """(() => {
      // The focus-frame probe must not seed a second hint from its child frame.
      if(window!==window.top)return;
      const key=KEY, kind=KIND;
      sessionStorage.setItem('unrelated-focus-control','keep');
      let hint={version:1,createdAt:Date.now(),returnTo:CALLER};
      if(kind==='expired')hint.createdAt-=16*60*1000;
      if(kind==='future')hint.createdAt+=60000;
      if(kind==='mismatch')hint.returnTo='https://hpc.foundups.com/member/?foundup=hpc';
      if(kind==='private-url')hint.returnTo='https://hpc.foundups.com/member/?token=private';
      if(kind==='shape')hint.extra='ignored input must be rejected';
      if(kind!=='direct')sessionStorage.setItem(key,kind==='malformed'?'{broken':kind==='oversize'?'x'.repeat(2049):JSON.stringify(hint));
      if(kind==='remove-blocked'){
        const original=Storage.prototype.removeItem;
        Storage.prototype.removeItem=function(k){if(k===key)throw new DOMException('Controlled optional storage denial','SecurityError');return original.call(this,k)};
      }
      if(kind==='read-blocked'){
        const original=Storage.prototype.getItem;
        Storage.prototype.getItem=function(k){if(k===key)throw new DOMException('Controlled optional storage denial','SecurityError');return original.call(this,k)};
      }
      if(kind==='hidden')Object.defineProperty(document,'visibilityState',{configurable:true,get:()=> 'hidden'});
      if(['typing','iframe','overlay','disabled-target','inert-target','hidden-target','outside-target'].includes(kind)){
        const observer=new MutationObserver(()=>{
          const input=document.querySelector('.mall-member-search-dock textarea');
          if(!input||!input.getClientRects().length||input.closest('[hidden]'))return;
          if(kind==='typing')input.focus({preventScroll:true});
          if(kind==='iframe'){const frame=document.createElement('iframe');frame.title='Own fixture focus frame';frame.style.cssText='position:fixed;width:2px;height:2px;top:0;left:0';document.body.append(frame);frame.focus();}
          if(kind==='overlay'){const panel=document.createElement('div');panel.setAttribute('aria-modal','true');panel.setAttribute('role','dialog');panel.style.cssText='position:fixed;inset:10px;z-index:99999;background:black';panel.textContent='Controlled overlay';document.body.append(panel);}
          const camera=input.closest('.mall-member-search-dock').querySelector('.mall-search-camera');
          if(kind==='disabled-target')camera.disabled=true;
          if(kind==='inert-target')camera.setAttribute('inert','');
          if(kind==='hidden-target')camera.hidden=true;
          if(kind==='outside-target')camera.style.transform='translateX(-200vw)';
          observer.disconnect();
        });observer.observe(document,{subtree:true,childList:true,attributes:true,attributeFilter:['hidden','class']});
      }
    })();""".replace('KEY', json.dumps(KEY)).replace('KIND', json.dumps(kind)).replace('CALLER', json.dumps(CALLER))

def check(browser, name, width=414, caller=CALLER, kind=None, write_denied=False, unsupported=False):
    row = {'engine': browser.browser_type.name, 'name': name, 'viewport': {'width': width, 'height': 896 if width == 414 else 874}, 'passed': False}
    context = browser.new_context(viewport=row['viewport'], is_mobile=True, has_touch=True, service_workers='block', reduced_motion='reduce')
    try:
        context.add_init_script(fixture.provider)
        if kind: context.add_init_script(negative_profile(kind))
        if write_denied:
            context.add_init_script("""(() => {const key=KEY,original=Storage.prototype.setItem;
              Storage.prototype.setItem=function(k,v){if(k===key)throw new DOMException('Controlled optional hint failure','QuotaExceededError');return original.call(this,k,v)};
            })();""".replace('KEY', json.dumps(KEY)))
        removed_focus_values = []
        if unsupported:
            # Observe the own-key producer removal before navigation, without
            # evaluating a document whose execution context is being replaced.
            context.expose_binding('__hpcFocusHintRemoved', lambda source, value: removed_focus_values.append(value))
            context.add_init_script("""(() => {
              const key=KEY, remove=Storage.prototype.removeItem, get=Storage.prototype.getItem;
              Storage.prototype.removeItem=function(k){
                const result=remove.call(this,k);
                if(k===key&&window.__observeCameraFocusRemoval)
                  void window.__hpcFocusHintRemoved(get.call(this,k)).catch(()=>{});
                return result;
              };
            })();""".replace('KEY', json.dumps(KEY)))
        context.route('**/*', route_local)
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.set_default_timeout(6000)
        page.goto(caller, wait_until='domcontentloaded')
        dock = page.locator('.mall-member-search-dock:visible')
        expect(dock).to_have_count(1)
        camera = dock.locator('.mall-search-camera')
        page.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
        if kind:
            expect(camera).not_to_be_focused()
            if kind == 'typing': expect(dock.locator('textarea')).to_be_focused()
            assert page.evaluate("sessionStorage.getItem('unrelated-focus-control')") == 'keep'
            if kind not in {'read-blocked','remove-blocked'}:
                assert page.evaluate('key=>sessionStorage.getItem(key)', KEY) is None
            row['recovery'] = 'No focus steal; normal Dock remains present'
        elif unsupported:
            # Boot canonicalizes unknown queries. Change the actual current URL
            # after render to exercise a stale UI handler, not a fictitious route.
            page.evaluate("history.replaceState(history.state,'','/member/?q=unadmitted')")
            assert page.url.endswith('?q=unadmitted')
            page.evaluate("key=>sessionStorage.setItem(key,'stale')", KEY)
            page.evaluate('window.__observeCameraFocusRemoval=true')
            with page.expect_request(lambda request: urlsplit(request.url).hostname == CAMERA) as outbound:
                camera.click()
            assert not parse_qs(urlsplit(outbound.value.url).query).get('return_to')
            expect(page.locator('#caller')).to_be_visible()
            assert not parse_qs(urlsplit(page.url).query).get('return_to')
            assert removed_focus_values == [None], removed_focus_values
            row['unsupported_outbound'] = 'Navigation continues; no unadmitted return URL or stale focus hint'
        else:
            if caller == CALLER:
                dock.locator('textarea').fill('Fixture')
                dock.locator('.mall-search-submit').click()
                page.wait_for_function("mallTileField.getScopedPhoneQuery()==='Fixture'")
                page.wait_for_function("() => {const e=document.querySelector('.mall-tile-field-wrapper');return e&&e.scrollHeight-e.clientHeight>=280}")
                page.locator('.mall-tile-field-wrapper').evaluate('e=>e.scrollTop=280')
                page.wait_for_function("Math.abs(document.querySelector('.mall-tile-field-wrapper').scrollTop-280)<=3")
                assert page.locator('.mall-tile-field-wrapper').evaluate('e=>e.scrollTop') > 100
            camera.click()
            expect(page.locator('#caller')).to_be_visible()
            expect(page.locator('#caller')).to_have_attribute('href', caller)
            page.locator('#caller').click()
            expect(page).to_have_url(caller)
            camera = page.locator('.mall-member-search-dock:visible .mall-search-camera')
            if write_denied: expect(camera).not_to_be_focused()
            else: expect(camera).to_be_focused()
            assert page.evaluate('key=>sessionStorage.getItem(key)', KEY) is None
            if caller == CALLER:
                page.wait_for_function("mallTileField.getScopedPhoneQuery()==='Fixture'&&Math.abs(document.querySelector('.mall-tile-field-wrapper').scrollTop-280)<=3")
                row['scroll'] = page.locator('.mall-tile-field-wrapper').evaluate('e=>e.scrollTop')
            page.reload(wait_until='domcontentloaded')
            expect(page.locator('.mall-member-search-dock:visible')).to_have_count(1)
            page.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
            expect(page.locator('.mall-member-search-dock:visible .mall-search-camera')).not_to_be_focused()
            # A synthetic persisted pageshow proves hint retirement only, not BFCache.
            if not write_denied:
                page.evaluate("key=>{sessionStorage.setItem(key,'stale');dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}))}", KEY)
            assert page.evaluate('key=>sessionStorage.getItem(key)', KEY) is None
            row['one_shot'] = True
        assert not errors, errors
        row['passed'] = True
    except Exception:
        row['error'] = traceback.format_exc()[-2500:]
    finally:
        context.close()
    report['cases'].append(row)
    args.out.write_text(json.dumps(report, indent=2) + '\n')

def check_source_ordering(browser):
    row = {'engine': browser.browser_type.name, 'name': 'source-ordering',
           'evidence': 'Source-extracted callback ordering with controlled storage/frames; not real navigation', 'passed': False}
    context = browser.new_context()
    try:
        context.route('**/*', lambda route: route.fulfill(status=404, body='No network in source-ordering check'))
        page = context.new_page()
        row['orders'] = page.evaluate("""source => {
          const start=source.indexOf('  function cameraDestination() {');
          const end=source.indexOf('  function discoveryPath(',start);
          if(start<0||start!==source.lastIndexOf('  function cameraDestination() {')||end<=start||end-start>8000)
            throw Error('Fixed camera/focus source owner missing or unbounded');
          const create=new Function('window','document','URL','TextEncoder','getComputedStyle','Date',
            source.slice(start,end)+';return {scheduleCameraFocus,rememberCameraFocus};');
          const key='pfmall_camera_focus_return_v1', orders=[];
          for(const name of ['mount-then-departure','replace-pending-return','matching-return']){
            const storage=new Map(),frames=[],body={};let focuses=0,now=100000;
            const camera={disabled:false,closest:()=>null,
              getBoundingClientRect:()=>({width:44,height:44,top:700,bottom:744,left:200,right:244}),
              focus:()=>{focuses++;}};
            const element={isConnected:true,querySelector:()=>camera};
            const document={body,documentElement:{},activeElement:body,visibilityState:'visible',querySelectorAll:()=>[]};
            const window={location:{href:'https://hpc.foundups.com/member/'},innerHeight:896,innerWidth:414,
              sessionStorage:{getItem:k=>storage.get(k)??null,removeItem:k=>storage.delete(k),setItem:(k,v)=>storage.set(k,v)},
              requestAnimationFrame:callback=>frames.push(callback),addEventListener:()=>{}};
            const api=create(window,document,URL,TextEncoder,()=>({visibility:'visible'}),{now:()=>now});
            storage.set('unrelated-focus-control','keep');
            if(name!=='mount-then-departure')api.rememberCameraFocus();
            api.scheduleCameraFocus(element);
            if(name!=='matching-return'){now+=10;api.rememberCameraFocus();}
            const before=storage.get(key);let steps=0;
            while(frames.length){if(++steps>8)throw Error('Unexpected frame loop');frames.shift()();}
            if(name==='matching-return'){
              if(storage.has(key)||focuses!==1)throw Error(name+': expected single consumed focus');
            }else if(storage.get(key)!==before||focuses!==0){
              throw Error(name+': old frames consumed a new departure hint or focused the old document');
            }
            if(storage.get('unrelated-focus-control')!=='keep')throw Error('Unrelated storage changed');
            orders.push({name,new_departure_hint_preserved:name==='matching-return'?null:storage.get(key)===before,focuses});
          }
          return orders;
        }""", (ROOT / 'public/member/js/mall-video-projection.js').read_text(encoding='utf-8'))
        row['passed'] = True
    except Exception:
        row['error'] = traceback.format_exc()[-2500:]
    finally:
        context.close()
    report['cases'].append(row)
    args.out.write_text(json.dumps(report, indent=2) + '\n')


report['source_before'] = digest()
started = time.monotonic()
with sync_playwright() as playwright:
    for engine in [playwright.chromium, playwright.webkit]:
        browser = engine.launch()
        try:
            check_source_ordering(browser)
            if args.case == 'source-ordering': continue
            check(browser, 'hpc-roundtrip-414', 414)
            check(browser, 'hpc-roundtrip-402', 402)
            check(browser, 'play-roundtrip', 414, 'https://play.foundups.com/member/')
            check(browser, 'write-denied-keeps-navigation', write_denied=True)
            check(browser, 'unsupported-outbound-clears-hint', caller=CALLER+'?q=unadmitted', unsupported=True)
            for kind in ['direct','expired','future','mismatch','private-url','shape','malformed','oversize','read-blocked','remove-blocked','typing','iframe','overlay','hidden','disabled-target','inert-target','hidden-target','outside-target']:
                check(browser, kind, kind=kind)
        finally:
            browser.close()
report['source_after'] = digest()
report['source_stable'] = report['source_before'] == report['source_after']
report['passed'] = all(row['passed'] for row in report['cases']) and report['source_stable']
report['seconds'] = round(time.monotonic() - started, 2)
args.out.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'rows':len(report['cases']),'passed':sum(row['passed'] for row in report['cases']),'source_stable':report['source_stable'],'seconds':report['seconds'],
                  'failures':[{'engine':row['engine'],'case':row['name'],'error':row.get('error','')[-900:]} for row in report['cases'] if not row['passed']]}))
sys.exit(0 if report['passed'] else 1)
