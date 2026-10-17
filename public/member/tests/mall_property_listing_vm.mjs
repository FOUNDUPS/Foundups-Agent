/**
 * Execute the real shared Mall tile/plane scripts with a bounded DOM fixture.
 * Run: node public/member/tests/mall_property_listing_vm.mjs
 * No browser, packages, network, auth, paid entitlements or layout claims.
 * Existing dispatcher VM fixtures do not implement DOM rendering; this fixture
 * covers that distinct interaction seam and is called by the nonvideo suite.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { runInNewContext } from 'node:vm';

const memberRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const htmlEscape = value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
const decode = value => String(value).replaceAll('&quot;', '"').replaceAll('&#39;', "'").replaceAll('&lt;', '<').replaceAll('&gt;', '>').replaceAll('&amp;', '&');
let doc;
let focusDetachments = 0;

class FixtureElement {
  constructor(tag = 'div', id = '') {
    this.tagName = tag.toUpperCase();
    this.id = id;
    this.dataset = {};
    this.attributes = {};
    this.style = {};
    this.children = [];
    this.events = new Map();
    this.classes = new Set();
    this.classList = {
      add: (...names) => names.forEach(name => this.classes.add(name)),
      remove: (...names) => names.forEach(name => this.classes.delete(name)),
      contains: name => this.classes.has(name),
      toggle: (name, force = !this.classes.has(name)) => force ? this.classes.add(name) : this.classes.delete(name)
    };
    this.scrollLeft = this.scrollTop = 0;
    this.scrollHeight = this.clientHeight = 600;
  }
  set className(value) { this.classes = new Set(value.split(/\s+/)); }
  set textContent(value) { this._html = htmlEscape(value); }
  get innerHTML() { return this._html || ''; }
  set innerHTML(value) {
    this._html = value;
    // Browsers return focus to the document when innerHTML removes its target.
    if (doc && this.children.some(child => child.contains(doc.activeElement))) {
      doc.activeElement = doc.body;
      focusDetachments++;
    }
    for (const child of this.children) child.parentElement = child.parentNode = null;
    this.children = [];
    // Parse only the boundary elements needed for dispatch/focus observations.
    for (const match of value.matchAll(/<(article|button|a)\b([^>]*)>([\s\S]*?)<\/\1>/g)) {
      const el = new FixtureElement(match[1]);
      for (const attr of match[2].matchAll(/([\w-]+)="([^"]*)"/g)) el.setAttribute(attr[1], decode(attr[2]));
      el.innerHTML = match[3];
      this.appendChild(el);
    }
  }
  setAttribute(name, value) {
    this.attributes[name] = String(value);
    if (name === 'class') this.className = value;
    if (name.startsWith('data-')) this.dataset[name.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = String(value);
  }
  removeAttribute(name) { delete this.attributes[name]; }
  hasAttribute(name) { return Object.hasOwn(this.attributes, name); }
  appendChild(child) { this.children.push(child); child.parentElement = child.parentNode = this; return child; }
  addEventListener(name, fn) { this.events.set(name, [...(this.events.get(name) || []), fn]); }
  removeEventListener(name, fn) { this.events.set(name, (this.events.get(name) || []).filter(item => item !== fn)); }
  fire(name, values = {}) {
    const event = { target: this, preventDefault() { this.prevented = true; }, stopPropagation() {}, ...values };
    for (const fn of this.events.get(name) || []) fn(event);
    return event;
  }
  focus() { doc.activeElement = this; }
  contains(node) { return this === node || this.children.some(child => child.contains(node)); }
  matches(selector) {
    if (selector === 'button') return this.tagName === 'BUTTON';
    if (selector === 'a[href]') return this.tagName === 'A' && this.hasAttribute('href');
    const match = selector.match(/^\.([\w-]+)(?:\[([\w-]+)(?:="([^"]*)")?\])?$/);
    return !!match && this.classes.has(match[1]) && (!match[2] || this.hasAttribute(match[2]) && (match[3] === undefined || this.attributes[match[2]] === match[3]));
  }
  querySelectorAll(selector) {
    const result = [];
    for (const child of this.children) {
      if (selector.split(',').some(part => child.matches(part.trim()))) result.push(child);
      result.push(...child.querySelectorAll(selector));
    }
    return result;
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
}

doc = new FixtureElement('document');
doc.body = new FixtureElement('body');
doc.appendChild(doc.body);
const elements = Object.fromEntries(['mallTileField', 'foundupViewPlane', 'foundupViewBody', 'foundupViewClose', 'foundupViewScrim'].map(id => [id, new FixtureElement(id.endsWith('Close') ? 'button' : 'div', id)]));
const wrapper = new FixtureElement();
wrapper.classList.add('mall-tile-field-wrapper');
wrapper.appendChild(elements.mallTileField);
doc.body.appendChild(wrapper);
doc.body.appendChild(elements.foundupViewPlane);
doc.body.appendChild(elements.foundupViewScrim);
elements.foundupViewPlane.appendChild(elements.foundupViewClose);
elements.foundupViewPlane.appendChild(elements.foundupViewBody);
elements.foundupViewPlane.setAttribute('inert', '');
doc.getElementById = id => elements[id] || null;
doc.createElement = tag => new FixtureElement(tag);
const imageRequests = [];
const windowEvents = new Map();
const fullscreenCalls = [];
const sb = {
  document: doc, console: { log() {}, warn() {} }, URL,
  innerWidth: 1100, innerHeight: 800,
  matchMedia: () => ({ matches: false }),
  location: { href: 'https://foundups.com/move2japan/' },
  setTimeout, clearTimeout,
  Image: class { set src(value) { imageRequests.push(value); } },
  addEventListener: (name, fn) => windowEvents.set(name, [...(windowEvents.get(name) || []), fn]),
  mallVideoPlayer: { open: (...args) => fullscreenCalls.push(args) }
};
sb.window = sb;
for (const filename of ['gesture-engine.js', 'mall-planes.js', 'mall-tile-field.js']) {
  runInNewContext(readFileSync(join(memberRoot, 'js', filename), 'utf8'), sb, { filename });
}

const first = {
  source_type: 'property_listing', foundup_id: 'move2japan', listing_id: 'fukui-87', source_item_id: '87',
  name: 'Wakasa house', theme: 'move2japan', price_jpy: 800000, municipality: 'Wakasa', prefecture: 'Fukui',
  land_area_m2: 253.26, building_area_m2: 173.09, building_area_label_ja: '建築面積',
  construction_date: null, floors: '2', repair_level: 'major', address_ja: '福井県若狭町',
  summary: 'Original short factual summary.', source_name: 'Fukui Akiya Bank',
  source_url: 'https://akiya.pref.fukui.lg.jp/webroot/public/estate/detail/87',
  last_checked: '2026-10-17', availability: 'source_listed',
  // These intentionally conflicting fields must not turn a house into a video/token tile.
  video_count: 4, videos: [{ embed_url: 'https://www.youtube.com/embed/example' }],
  poster_url: 'https://example.com/unlicensed.jpg', channel_avatar_url: 'https://example.com/avatar.jpg',
  token_symbol: 'FAKE_TOKEN', launch_readiness: 'ready'
};
const second = { ...first, listing_id: 'fukui-85', source_item_id: '85', name: 'Fukui City house', municipality: 'Fukui City', price_jpy: 750000, repair_level: 'unknown', source_url: 'https://akiya.pref.fukui.lg.jp/webroot/public/estate/detail/85' };
const field = elements.mallTileField;
const plane = elements.foundupViewPlane;
const detail = elements.foundupViewBody;
const tiles = () => field.querySelectorAll('.mall-tile');
const listenerCounts = () => JSON.stringify({ document: [...doc.events].map(([k, v]) => [k, v.length]), window: [...windowEvents].map(([k, v]) => [k, v.length]), scroll: [...wrapper.events].map(([k, v]) => [k, v.length]) });

sb.mallTileField.initialize([first, second]);
assert.equal(tiles().length, 2);
assert.deepEqual(tiles().map(tile => tile.dataset.foundupId), ['move2japan', 'move2japan']);
assert.deepEqual(tiles().map(tile => tile.dataset.listingId), ['fukui-87', 'fukui-85']);
assert.match(field.innerHTML, /¥800,000/);
assert.match(field.innerHTML, /Photos at source/);
assert.doesNotMatch(field.innerHTML, /FAKE_TOKEN|mall-tile-queue-count|mall-tile-play-indicator|unlicensed\.jpg|avatar\.jpg/);
assert.equal(imageRequests.length, 0);

tiles()[1].fire('click');
assert.equal(sb.mallPlanes.getActiveIndex(), 1);
assert.match(detail.innerHTML, /Fukui City house/);
assert.match(detail.innerHTML, /¥750,000/);
assert.match(detail.innerHTML, /2026-10-17/);
assert.match(detail.innerHTML, /Listed at source when checked/);
assert.match(detail.innerHTML, /建築面積/);
assert.doesNotMatch(detail.innerHTML, /FAKE_TOKEN|fv-badge-ready|iframe|<video/);
assert.equal(plane.hasAttribute('inert'), false);
assert.equal(doc.activeElement, elements.foundupViewClose);
sb.mallPlanes.closeView();
assert.equal(plane.hasAttribute('inert'), true);
assert.equal(doc.activeElement, tiles()[1]);

for (const key of ['Enter', ' ']) {
  tiles()[1].fire('keydown', { key });
  assert.match(detail.innerHTML, /Fukui City house/);
  assert.equal(sb.mallPlanes.isOpen(), true);
  doc.fire('keydown', { key: 'Escape' });
  assert.equal(sb.mallPlanes.isOpen(), false);
  assert.equal(doc.activeElement, tiles()[1]);
}
assert.equal(fullscreenCalls.length, 0);
sb.mallTileField.expandFoundUp(1);
assert.equal(sb.mallTileField.isExpanded(), false);
assert.equal(sb.mallPlanes.getActiveIndex(), 1);
doc.fire('keydown', { key: 'ArrowLeft' });
assert.match(detail.innerHTML, /Wakasa house/);
sb.mallPlanes.closeView();
assert.equal(doc.activeElement, tiles()[0]);
sb.mallTileField.startLanePreview(0, 0, false);
assert.equal(sb.mallTileField.getPlayingIndex(), null);

const listenersBefore = listenerCounts();
for (let i = 0; i < 8; i++) sb.mallTileField.updateCatalog(i % 2 ? [second] : [first, second]);
assert.equal(listenerCounts(), listenersBefore);
assert.equal(tiles().length, 1);
tiles()[0].fire('click');
assert.match(detail.innerHTML, /Fukui City house/);
sb.mallTileField.updateCatalog([]);
assert.equal(sb.mallPlanes.isOpen(), false);
assert.equal(tiles().length, 0);
assert.match(field.innerHTML, /No results/);
sb.mallTileField.initialize([second, first]);
assert.equal(listenerCounts(), listenersBefore);
tiles()[0].fire('keydown', { key: 'Enter' });
sb.mallPlanes.closeView();
assert.equal(doc.activeElement, tiles()[0]);

sb.mallPlanes.setCatalog([first, second]);
assert.equal(sb.mallPlanes.openListingById('another-foundup', 'fukui-87'), false);
assert.equal(sb.mallPlanes.openListingById('move2japan', 'missing'), false);
sb.mallPlanes.setCatalog([first, { ...first, name: 'Ambiguous duplicate' }]);
assert.equal(sb.mallPlanes.openListingById('move2japan', 'fukui-87'), false);
assert.equal(sb.mallPlanes.isOpen(), false);

for (const source_url of ['javascript:alert(1)', 'data:text/html,test', 'http://example.com/house', '//example.com/house', 'https://user:pass@example.com/house', 'https://example.com/house\n', 'https://example.com\\house']) {
  sb.mallTileField.updateCatalog([{ ...first, source_url }]);
  tiles()[0].fire('click');
  assert.equal(detail.querySelectorAll('a[href]').length, 0, source_url);
  assert.match(detail.innerHTML, /link is unavailable/);
  sb.mallPlanes.closeView();
}
const hostile = { ...first, name: 'House"><img src=x onerror=alert(1)>', summary: '<script>alert(1)</script>', listing_id: 'quoted"listing', source_url: 'https://example.com/house?a=1&b=2' };
sb.mallTileField.updateCatalog([hostile]);
assert.doesNotMatch(field.innerHTML, /<img/);
tiles()[0].fire('click');
assert.doesNotMatch(detail.innerHTML, /<script>|<img/);
assert.match(detail.innerHTML, /&lt;script&gt;/);
assert.match(detail.innerHTML, /a=1&amp;b=2/);
const sourceLink = detail.querySelectorAll('a[href]')[0];
assert.equal(sourceLink.attributes.target, '_blank');
assert.equal(sourceLink.attributes.rel, 'noopener noreferrer');
sourceLink.focus();
assert.equal(doc.fire('keydown', { key: 'Tab' }).prevented, true);
assert.equal(doc.activeElement, elements.foundupViewClose);
assert.equal(doc.fire('keydown', { key: 'Tab', shiftKey: true }).prevented, true);
assert.equal(doc.activeElement, sourceLink);
sb.mallPlanes.closeView();
assert.equal(doc.activeElement, tiles()[0]);

// Replacing a focused source link must leave focus on a live dialog control.
sb.mallTileField.updateCatalog([first, second]);
tiles()[0].fire('click');
detail.querySelectorAll('a[href]')[0].focus();
const detachmentsBeforeNavigation = focusDetachments;
doc.fire('keydown', { key: 'ArrowRight' });
assert.equal(focusDetachments, detachmentsBeforeNavigation + 1, 'fixture observed detached source-link focus');
assert.equal(doc.activeElement === elements.foundupViewClose, true, 'property navigation restores stable focus');
assert.match(detail.innerHTML, /Fukui City house/);
doc.body.focus();
assert.equal(doc.fire('keydown', { key: 'Tab' }).prevented, true, 'outside Tab is contained');
assert.equal(doc.activeElement === elements.foundupViewClose, true);
doc.body.focus();
assert.equal(doc.fire('keydown', { key: 'Tab', shiftKey: true }).prevented, true, 'outside Shift-Tab is contained');
assert.equal(doc.activeElement === detail.querySelectorAll('a[href]')[0], true);
sb.mallPlanes.closeView();
assert.equal(doc.activeElement, tiles()[1]);

// Real gesture-engine events: scrolling a long property must not dismiss it.
sb.mallTileField.updateCatalog([first, second]);
tiles()[0].fire('click');
plane.scrollHeight = 1400;
plane.clientHeight = 650;
plane.fire('touchstart', { touches: [{ clientX: 150, clientY: 500 }] });
plane.scrollTop = 200;
plane.fire('touchend', { touches: [], changedTouches: [{ clientX: 150, clientY: 300 }] });
assert.equal(sb.mallPlanes.isOpen(), true, 'vertical property scrolling retains detail');
assert.doesNotMatch(detail.innerHTML, /Swipe up to close/);
plane.fire('touchstart', { touches: [{ clientX: 350, clientY: 300 }] });
plane.fire('touchend', { touches: [], changedTouches: [{ clientX: 150, clientY: 300 }] });
assert.match(detail.innerHTML, /Fukui City house/);
assert.equal(doc.activeElement === elements.foundupViewClose, true);
sb.mallPlanes.closeView();
assert.equal(doc.activeElement, tiles()[1]);

// Existing video Enter/fullscreen behavior is still routed to the video player.
const video = { foundup_id: 'channel', name: 'Existing channel', video_count: 1, videos: [{ video_id: 'old-video' }] };
sb.mallTileField.updateCatalog([video]);
assert.match(field.innerHTML, /mall-tile-play-indicator/);
tiles()[0].fire('keydown', { key: 'Enter' });
assert.equal(fullscreenCalls.length, 1);
assert.equal(fullscreenCalls[0][0], 'channel');
assert.equal(fullscreenCalls[0][1][0].video_id, 'old-video');
sb.mallPlanes.setCatalog([video]);
sb.mallPlanes.openFoundUp(0);
assert.match(detail.innerHTML, /Swipe up to close/);
plane.fire('touchstart', { touches: [{ clientX: 150, clientY: 500 }] });
plane.fire('touchend', { touches: [], changedTouches: [{ clientX: 150, clientY: 300 }] });
assert.equal(sb.mallPlanes.isOpen(), false, 'existing non-property swipe-up close remains');
assert.equal(imageRequests.length, 0);
console.log('Mall property runtime: identity, keyboard, filtering, focus, URLs, inert state, and video compatibility passed.');
