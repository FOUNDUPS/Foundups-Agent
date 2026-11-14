import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
const read=p=>readFileSync(new URL('../../../../'+p,import.meta.url),'utf8');
const editor='modules/communication/youtube_shorts/assets/kids_review/';
test('standalone manifest icons and scoped UI cache are coherent',()=>{const m=JSON.parse(read('public/eduit/storytime.webmanifest'));assert.equal(m.display,'standalone');assert.equal(m.start_url,'./review/director.html');for(const i of m.icons)assert.ok(existsSync(new URL('../../../../public/eduit/'+i.src,import.meta.url)));const sw=read('public/eduit/storytime-sw.js');assert.ok(sw.includes("e.request.method!=='GET'"));assert.ok(sw.includes("headers.has('range')"));assert.ok(!sw.includes('little-shrew.mp4'));assert.ok(sw.includes('actual.origin===expected.origin'));assert.ok(sw.includes('expected.pathname.replace'));});
test('flag-only buttons retain accessible language names and pointer capture',()=>{const js=read(editor+'director.js');assert.ok(js.includes("button.setAttribute('aria-label',l.label)"));assert.ok(js.includes("flag.alt=''"));assert.ok(!js.includes("l.flag+' '+l.label"));assert.ok(js.includes('setPointerCapture'));assert.ok(js.includes('onlostpointercapture'));for(const id of ['gb','jp','pt','es'])assert.ok(read(editor+'flags/'+id+'.svg').includes('<svg'));});
