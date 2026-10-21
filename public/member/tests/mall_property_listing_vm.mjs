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
    this.scrollWidth = this.clientWidth = 320;
    this.offsetLeft = this.offsetTop = 0;
    this.offsetWidth = 240;
  }
  set className(value) { this.classes = new Set(value.split(/\s+/)); }
  get className() { return [...this.classes].join(' '); }
  set textContent(value) { this._html = htmlEscape(value); }
  get textContent() {
    // This fixture only reads text from leaf elements; it is not an HTML sanitizer.
    assert.equal(this.children.length, 0, 'textContent fixture requires a leaf element');
    return decode(this._html || '');
  }
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
    // Preserve actual nested section/header/track/tile structure. Geometry below
    // is an explicit fixture, not a browser-layout or screenshot assertion.
    const stack = [{ el: this, start: 0 }];
    const voidTags = new Set(['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr']);
    for (const match of value.matchAll(/<(\/?)([a-z][\w:-]*)\b([^>]*)>/gi)) {
      const tag = match[2].toLowerCase();
      if (match[1]) {
        if (stack.length > 1 && stack.at(-1).el.tagName.toLowerCase() === tag) {
          const item = stack.pop();
          item.el._html = value.slice(item.start, match.index);
        }
        continue;
      }
      const el = new FixtureElement(tag);
      for (const attr of match[3].matchAll(/([\w-]+)(?:="([^"]*)")?/g)) el.setAttribute(attr[1], decode(attr[2] || ''));
      stack.at(-1).el.appendChild(el);
      if (!voidTags.has(tag) && !match[3].endsWith('/')) stack.push({ el, start: match.index + match[0].length });
    }
    if (this.id === 'mallTileField') this.layoutGroups();
  }
  layoutGroups() {
    const groups = this.querySelectorAll('.mall-field-group, .mall-category-row');
    groups.forEach((group, rowIndex) => {
      group.offsetTop = rowIndex * 330;
      const track = group.querySelector('.mall-field-group-track, .mall-category-track');
      const items = track.querySelectorAll('.mall-tile');
      track.clientWidth = 300;
      track.scrollWidth = Math.max(track.clientWidth, items.length * 250 - 10);
      items.forEach((tile, index) => { tile.offsetLeft = index * 250; });
    });
    if (groups.length && this.parentElement) {
      this.parentElement.clientHeight = 420;
      this.parentElement.scrollHeight = Math.max(420, groups.length * 330);
    }
  }
  getBoundingClientRect() {
    return { left: this.offsetLeft, top: this.offsetTop, width: this.offsetWidth, height: 140,
      right: this.offsetLeft + this.offsetWidth, bottom: this.offsetTop + 140 };
  }
  scrollBy({ left = 0, top = 0 }) {
    this.scrollLeft = Math.max(0, Math.min(this.scrollLeft + left, this.scrollWidth - this.clientWidth));
    this.scrollTop = Math.max(0, Math.min(this.scrollTop + top, this.scrollHeight - this.clientHeight));
  }
  setAttribute(name, value) {
    this.attributes[name] = String(value);
    if (name === 'id') this.id = String(value);
    if (name === 'class') this.className = value;
    if (name.startsWith('data-')) this.dataset[name.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = String(value);
  }
  getAttribute(name) { return this.attributes[name] ?? null; }
  removeAttribute(name) { delete this.attributes[name]; }
  hasAttribute(name) { return Object.hasOwn(this.attributes, name); }
  appendChild(child) { this.children.push(child); child.parentElement = child.parentNode = this; return child; }
  addEventListener(name, fn, options = {}) { this.events.set(name, [...(this.events.get(name) || []), { fn, once: options.once }]); }
  removeEventListener(name, fn) { this.events.set(name, (this.events.get(name) || []).filter(item => item.fn !== fn)); }
  fire(name, values = {}) {
    const event = { target: this, bubbles: name !== 'focus' && name !== 'scroll', preventDefault() { this.prevented = true; }, stopPropagation() { this.stopped = true; }, ...values };
    for (let target = this; target; target = event.bubbles && !event.stopped ? target.parentElement : null) {
      event.currentTarget = target;
      for (const item of [...(target.events.get(name) || [])]) {
        if (item.once) target.removeEventListener(name, item.fn);
        item.fn(event);
      }
    }
    return event;
  }
  focus() {
    if (!doc.contains(this) || this.closest('[inert]') || this.disabled) return;
    if (doc.activeElement !== this) {
      doc.activeElement = this;
      this.fire('focus');
    }
  }
  contains(node) { return this === node || this.children.some(child => child.contains(node)); }
  matches(selector) {
    if (selector.includes(',')) return selector.split(',').some(part => this.matches(part.trim()));
    let valid = true;
    let rest = selector.replace(/\[([\w-]+)(?:="([^"]*)")?\]/g, (_, name, value) => {
      if (!this.hasAttribute(name) || value !== undefined && this.attributes[name] !== value) valid = false;
      return '';
    });
    rest = rest.replace(/\.([\w-]+)/g, (_, name) => { if (!this.classes.has(name)) valid = false; return ''; });
    rest = rest.replace(/#([\w-]+)/g, (_, id) => { if (this.id !== id) valid = false; return ''; });
    return valid && (!rest || rest.toUpperCase() === this.tagName);
  }
  closest(selector) { for (let el = this; el; el = el.parentElement) { if (el.matches(selector)) return el; } return null; }
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
  getComputedStyle: element => ({ backgroundColor: element.style.backgroundColor || '' }),
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
for (const [imageTag, scriptTag] of [['img', 'script'], ['IMG', 'SCRIPT'], ['ImG', 'ScRiPt']]) {
  sb.mallTileField.updateCatalog([{ ...first, name: `<${imageTag} src=x onerror=alert(1)>`, summary: `<${scriptTag} data-x="1">alert(1)</${scriptTag}>` }]);
  assert.doesNotMatch(field.innerHTML, /<(?:img|script)\b/i);
  tiles()[0].fire('click');
  assert.doesNotMatch(detail.innerHTML, /<(?:img|script)\b/i);
  assert.ok(detail.innerHTML.includes(`&lt;${scriptTag}`));
  sb.mallPlanes.closeView();
}
const hostile = { ...first, name: 'House"><img src=x onerror=alert(1)>', summary: '<script>alert(1)</script>', listing_id: 'quoted"listing', source_url: 'https://example.com/house?a=1&b=2' };
sb.mallTileField.updateCatalog([hostile]);
assert.doesNotMatch(field.innerHTML, /<img\b/i);
tiles()[0].fire('click');
assert.doesNotMatch(detail.innerHTML, /<(?:script|img)\b/i);
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

// Explicit geographic projection: nested rows, both axes, and stable identities.
const third = { ...first, listing_id: 'fukui-89', source_item_id: '89', name: 'Second Wakasa home',
  country: 'Japan', locality: 'Kumagawa', locality_ja: '熊川', price_jpy: null, price_status: 'negotiable',
  land_area_m2: null, repair_level: 'some', source_notes: ['Source dates disagree.', '<img src=x onerror=alert(1)>'],
  source_url: 'https://akiya.pref.fukui.lg.jp/webroot/public/estate/detail/89' };
const fourth = { ...second, listing_id: 'fukui-90', source_item_id: '90', name: 'Second Fukui City home', land_area_m2: 0,
  price_jpy: null, price_status: 'unknown', repair_level: 'none_reported' };
const fifth = { ...first, listing_id: 'fukui-91', name: 'Third Wakasa home' };
const sixth = { ...first, listing_id: 'fukui-92', name: 'Awara home', municipality: 'Awara' };
const groupedCatalog = [first, second, third, fourth, fifth, sixth];
const groups = [
  { key: 'wakasa', label: 'Wakasa', subtitle: 'Fukui · Japan', itemIds: [first.listing_id, third.listing_id, fifth.listing_id] },
  { key: 'fukui-city', label: 'Fukui City', subtitle: 'Fukui · Japan', itemIds: [second.listing_id, fourth.listing_id] },
  { key: 'awara', label: 'Awara', itemIds: [sixth.listing_id] }
];
const groupRow = key => field.querySelectorAll('.mall-field-group').find(row => row.dataset.groupKey === key);
const groupTrack = key => groupRow(key).querySelector('.mall-field-group-track');
const groupTiles = key => groupTrack(key).querySelectorAll('.mall-tile');
const selectedId = () => doc.activeElement.dataset.listingId;
sb.mallTileField.setMotionMode('glide');
sb.mallTileField.updateCatalog(groupedCatalog, { groups });
assert.equal(field.dataset.layout, 'grouped');
assert.equal(sb.mallTileField.getLayoutMode(), 'grouped');
assert.equal(sb.mallTileField.getMotionMode(), 'snap', 'entering grouped mode defaults to Snap');
assert.equal(wrapper.classList.contains('mall-field-grouped-wrapper'), true);
assert.equal(wrapper.classList.contains('browse-rows'), false, 'category wrapper mode is cleared');
assert.equal(wrapper.classList.contains('motion-glide'), false);
const declaredGeographicMarkup = field.innerHTML;
for (const query of ['show me houses', '', '   ']) {
  assert.equal(sb.mallTileField.searchCatalog(query), false, 'global search cannot bypass the geographic form');
}
for (const layout of ['grid', 'rows']) assert.equal(sb.mallTileField.setLayoutMode(layout), false);
assert.equal(sb.mallTileField.getFieldScope(), null);
assert.equal(field.innerHTML, declaredGeographicMarkup, 'refused commands leave the adapter projection intact');
sb.mallTileField.setDensity('4x6');
assert.equal(sb.mallTileField.getDensity(), '4x6');
assert.equal(sb.mallTileField.getLayoutMode(), 'grouped', 'manual density cannot flatten geographic rows');
assert.equal(field.innerHTML, declaredGeographicMarkup);
assert.deepEqual(field.querySelectorAll('.mall-field-group').map(row => row.dataset.groupKey), ['wakasa', 'fukui-city', 'awara']);
assert.deepEqual(groupTiles('wakasa').map(tile => tile.dataset.listingId), ['fukui-87', 'fukui-89', 'fukui-91']);
assert.deepEqual(groupTiles('wakasa').map(tile => tile.dataset.index), ['0', '2', '4'], 'row order does not replace catalog indices');
assert.deepEqual(groupTiles('wakasa').map(tile => tile.dataset.tileIndex), [0, 2, 4], 'loading state uses the same catalog indices');
assert.equal(groupTiles('wakasa')[1].parentElement, groupTrack('wakasa'), 'tile is nested in its horizontal owner');
assert.equal(groupTrack('wakasa').parentElement, groupRow('wakasa'));
assert.equal(groupRow('wakasa').querySelector('.mall-field-group-heading').textContent, 'Wakasa');
assert.equal(groupRow('wakasa').querySelectorAll('.mall-group-nav')[0].disabled, true);
assert.equal(groupRow('wakasa').querySelectorAll('.mall-group-nav')[1].disabled, false);

groupTiles('wakasa')[0].focus();
assert.equal(groupTiles('wakasa')[0].fire('keydown', { key: 'ArrowLeft' }).prevented, true);
assert.equal(selectedId(), first.listing_id, 'left boundary does not wrap');
groupRow('wakasa').querySelectorAll('.mall-group-nav')[1].fire('click');
assert.equal(selectedId(), third.listing_id, 'visible next button moves within row');
assert.equal(groupTrack('wakasa').scrollLeft, 250);
groupTiles('wakasa')[1].fire('keydown', { key: 'ArrowRight' });
assert.equal(selectedId(), fifth.listing_id);
assert.equal(groupTrack('wakasa').scrollLeft, 440, 'horizontal position clamps to row extent');
groupTiles('wakasa')[2].fire('keydown', { key: 'ArrowRight' });
assert.equal(selectedId(), fifth.listing_id, 'right boundary stays in Wakasa');
groupTiles('wakasa')[2].fire('keydown', { key: 'ArrowLeft' });
assert.equal(selectedId(), third.listing_id);
groupTiles('wakasa')[1].fire('keydown', { key: 'ArrowDown' });
assert.equal(selectedId(), second.listing_id, 'down changes area');
assert.equal(wrapper.scrollTop, 330);
groupTiles('fukui-city')[0].fire('keydown', { key: 'ArrowRight' });
assert.equal(selectedId(), fourth.listing_id);
assert.equal(groupTrack('fukui-city').scrollLeft, 190);
groupTiles('fukui-city')[1].fire('keydown', { key: 'ArrowDown' });
assert.equal(selectedId(), sixth.listing_id);
groupTiles('awara')[0].fire('keydown', { key: 'ArrowDown' });
assert.equal(selectedId(), sixth.listing_id, 'last area does not wrap');
groupTiles('awara')[0].fire('keydown', { key: 'ArrowUp' });
assert.equal(selectedId(), fourth.listing_id, 'up restores the previous area active item');
assert.equal(groupTrack('fukui-city').scrollLeft, 190);
groupTiles('fukui-city')[1].fire('keydown', { key: 'ArrowUp' });
assert.equal(selectedId(), third.listing_id, 'each row retains its own item');
assert.equal(groupTrack('wakasa').scrollLeft, 250);
groupTiles('wakasa')[1].fire('keydown', { key: 'ArrowUp' });
assert.equal(selectedId(), third.listing_id, 'first area does not wrap');

// The real plane receives only the active area's catalog, including Enter.
tiles().forEach(tile => tile.classList.remove('tap-pulse'));
plane.scrollTop = 200;
groupTiles('wakasa')[1].fire('keydown', { key: 'Enter' });
assert.equal(groupTiles('wakasa')[1].classList.contains('tap-pulse'), true, 'feedback targets the noncontiguous catalog index');
assert.equal(groupTiles('wakasa')[2].classList.contains('tap-pulse'), false, 'the tile at the same DOM offset is not pulsed');
assert.equal(sb.mallPlanes.getActiveIndex(), 1, 'plane index is local to its area');
assert.equal(plane.scrollTop, 0, 'a newly opened property starts at its heading');
assert.match(detail.innerHTML, /Second Wakasa home|Price negotiable/);
assert.match(detail.innerHTML, /Kumagawa|熊川|Japan/);
assert.match(detail.innerHTML, /Some repairs required/);
assert.match(detail.innerHTML, /Source dates disagree\./);
assert.match(detail.innerHTML, /&lt;img/);
assert.doesNotMatch(detail.innerHTML, /<img|¥0|Land area<\/dt><dd>0/);
doc.fire('keydown', { key: 'ArrowRight' });
assert.match(detail.innerHTML, /Third Wakasa home/);
doc.fire('keydown', { key: 'ArrowRight' });
assert.match(detail.innerHTML, /Third Wakasa home/);
assert.doesNotMatch(detail.innerHTML, /Fukui City house/);
doc.fire('keydown', { key: 'ArrowLeft' });
sb.mallPlanes.closeView();
assert.equal(selectedId(), third.listing_id);
groupTiles('fukui-city')[1].fire('click');
assert.match(detail.innerHTML, /Land area<\/dt><dd>0 m²/);
assert.match(detail.innerHTML, /Price not stated/);
assert.match(detail.innerHTML, /No repairs reported at source/);
assert.doesNotMatch(detail.innerHTML, /¥0/);
sb.mallPlanes.closeView();

// Drag from a tile descendant bubbles through the actual existing mouse handler.
groupTiles('wakasa')[0].focus();
groupTrack('wakasa').scrollLeft = 0;
wrapper.scrollTop = 0;
const dragStart = groupTiles('wakasa')[0].querySelector('.mall-property-price');
dragStart.fire('mousedown', { button: 0, clientX: 280, clientY: 160 });
doc.fire('mousemove', { clientX: 80, clientY: 155 });
assert.equal(groupTrack('wakasa').scrollLeft, 200, 'drag starting on a tile scrolls its row');
assert.equal(wrapper.scrollTop, 0, 'horizontal drag leaves other axis alone');
doc.fire('mouseup', { clientX: 80, clientY: 155 });
dragStart.fire('click');
assert.equal(sb.mallPlanes.isOpen(), false, 'post-drag click cannot activate house');
assert.equal(wrapper.classList.contains('is-dragging'), false);
await new Promise(resolve => setTimeout(resolve, 120));
dragStart.fire('mousedown', { button: 0, clientX: 180, clientY: 400 });
doc.fire('mousemove', { clientX: 182, clientY: 100 });
assert.equal(wrapper.scrollTop, 300, 'vertical tile drag scrolls areas');
assert.equal(groupTrack('wakasa').scrollLeft, 200, 'vertical drag retains row X');
doc.fire('mouseup', { clientX: 182, clientY: 100 });
dragStart.fire('click');
assert.equal(sb.mallPlanes.isOpen(), false);
await new Promise(resolve => setTimeout(resolve, 120));
dragStart.fire('mousedown', { button: 0, clientX: 180, clientY: 200 });
doc.fire('mouseup', { clientX: 181, clientY: 201 });
dragStart.fire('click');
assert.equal(sb.mallPlanes.isOpen(), true, 'a tap without a drag still opens the house');
sb.mallPlanes.closeView();

// Catalog order, group order and filtering do not confuse listing identity.
groupTiles('wakasa')[0].fire('keydown', { key: 'ArrowRight' });
groupTrack('fukui-city').scrollLeft = 190;
groupTrack('fukui-city').fire('scroll');
wrapper.scrollTop = 0;
const reorderedGroups = [groups[1], groups[0], groups[2]];
sb.mallTileField.updateCatalog([sixth, fifth, second, first, third, fourth], { groups: reorderedGroups });
assert.equal(selectedId(), third.listing_id, 'focused listing survives changed global index');
assert.equal(groupTrack('wakasa').scrollLeft, 250, 'row X survives a moved group');
assert.equal(groupTrack('fukui-city').scrollLeft, 190, 'other row has independent X');
assert.equal(wrapper.scrollTop, 330, 'the same area remains at the field position');
const searchInput = new FixtureElement('input');
doc.body.appendChild(searchInput);
searchInput.focus();
sb.mallTileField.updateCatalog(groupedCatalog, { groups });
assert.equal(doc.activeElement, searchInput, 'search reprojects without stealing input focus');
assert.equal(groupTrack('wakasa').scrollLeft, 250);

groupTiles('wakasa')[1].fire('click');
sb.mallTileField.updateCatalog([first, second, fourth, fifth, sixth], { groups });
assert.equal(sb.mallPlanes.isOpen(), false);
assert.equal(doc.contains(doc.activeElement), true, 'filtering after closing details leaves live focus');
assert.equal(selectedId(), fifth.listing_id, 'removed selected listing falls back to a same-row neighbor');
assert.equal(groupTrack('wakasa').scrollLeft, 190, 'shorter filtered row clamps safely');
sb.mallTileField.updateCatalog([], { groups: [] });
assert.equal(tiles().length, 0);
assert.equal(sb.mallTileField.searchCatalog(''), false, 'empty geographic projection still owns query clearing');
assert.equal(sb.mallTileField.setLayoutMode('grid'), false);
assert.deepEqual(Object.keys(sb.mallTileField.getTileLoadStates()), [], 'empty projection drops old tile load states');
assert.equal(doc.activeElement, field, 'an empty projection retains a live focus target');
assert.match(field.innerHTML, /No results/);

// Empty or unresolved groups do not create blank areas in the navigation field.
sb.mallTileField.updateCatalog(groupedCatalog, { groups: [groups[0], { key: 'empty', label: 'Empty area', itemIds: [] }, groups[2]] });
assert.equal(groupRow('empty'), undefined);
groupTiles('wakasa')[0].focus();
groupTiles('wakasa')[0].fire('keydown', { key: 'ArrowDown' });
assert.equal(selectedId(), sixth.listing_id);
wrapper.setAttribute('inert', '');
groupTiles('awara')[0].fire('keydown', { key: 'ArrowUp' });
groupTiles('awara')[0].fire('click');
assert.equal(sb.mallPlanes.isOpen(), false, 'inert discovery does not react behind the search dialog');
wrapper.removeAttribute('inert');

// A native swipe/scroll changes row controls and the row's remembered item.
sb.mallTileField.updateCatalog(groupedCatalog, { groups });
groupTiles('wakasa')[0].focus();
const nativeTrack = groupTrack('wakasa');
nativeTrack.scrollLeft = 0;
nativeTrack.fire('scroll');
doc.body.focus();
nativeTrack.scrollLeft = nativeTrack.scrollWidth - nativeTrack.clientWidth;
nativeTrack.fire('scroll');
assert.equal(groupRow('wakasa').querySelectorAll('.mall-group-nav')[0].disabled, false, 'Previous becomes usable after native scroll');
assert.equal(groupRow('wakasa').querySelectorAll('.mall-group-nav')[1].disabled, true, 'Next reflects the last visible house');
groupRow('wakasa').querySelectorAll('.mall-group-nav')[0].fire('click');
assert.equal(selectedId(), third.listing_id, 'Previous starts from the naturally scrolled house');
// The queued scroll event from keyboard/button movement keeps explicit focus.
nativeTrack.fire('scroll');
assert.equal(groupRow('wakasa').querySelectorAll('.mall-group-nav')[0].disabled, false);
groupTiles('wakasa')[1].fire('keydown', { key: 'ArrowDown' });
groupTiles('fukui-city')[0].fire('keydown', { key: 'ArrowUp' });
assert.equal(selectedId(), third.listing_id);

const dangerousKey = 'quoted"group';
sb.mallTileField.updateCatalog([first, { ...first }, second], { groups: [
  { key: dangerousKey, label: '<img src=x>', subtitle: '<script>x</script>', itemIds: [first.listing_id, second.listing_id, second.listing_id, 'missing'] },
  { key: dangerousKey, label: 'Duplicate group', itemIds: [second.listing_id] }
] });
assert.equal(field.querySelectorAll('.mall-field-group').length, 1);
assert.equal(groupRow(dangerousKey).dataset.groupKey, dangerousKey);
assert.deepEqual(tiles().map(tile => tile.dataset.listingId), [second.listing_id], 'ambiguous, duplicate and missing memberships are excluded');
assert.doesNotMatch(field.innerHTML, /<(?:img|script)\b/i);
assert.match(field.innerHTML, /&lt;img/);
assert.equal(listenerCounts(), listenersBefore, 'group changes install no extra page listeners');

// Persisted geographic position is keyed by the actual tenant, area and home.
sb.mallTileField.updateCatalog(groupedCatalog, { groups });
groupTiles('wakasa')[0].focus();
groupTiles('wakasa')[0].fire('keydown', { key: 'ArrowRight' });
groupTrack('fukui-city').scrollLeft = 190;
groupTrack('fukui-city').fire('scroll');
wrapper.scrollTop = 330;
const geographicSaved = JSON.parse(JSON.stringify(sb.mallTileField.getGeographicState()));
assert.equal(geographicSaved.foundup_id, 'move2japan');
assert.equal(geographicSaved.activeGroupKey, 'fukui-city');
assert.equal(geographicSaved.rows.find(row => row.key === 'wakasa').activeId, third.listing_id);
groupTrack('wakasa').scrollLeft = 0;
groupTrack('wakasa').fire('scroll');
wrapper.scrollTop = 0;
assert.equal(sb.mallTileField.restoreGeographicState(geographicSaved), true);
assert.equal(groupTrack('wakasa').scrollLeft, 250);
assert.equal(groupTrack('fukui-city').scrollLeft, 190);
assert.equal(wrapper.scrollTop, 330);
sb.mallTileField.updateCatalog(groupedCatalog, { groups: reorderedGroups });
assert.equal(sb.mallTileField.restoreGeographicState(geographicSaved), true);
assert.equal(wrapper.scrollTop, 0, 'the same area is restored after row reorder');
assert.equal(sb.mallTileField.restoreGeographicState({ ...geographicSaved, foundup_id: 'another-product' }), false);
assert.equal(sb.mallTileField.restoreGeographicState({ ...geographicSaved, scrollTop: Infinity }), false);
assert.equal(sb.mallTileField.restoreGeographicState({ ...geographicSaved, rows: [...geographicSaved.rows, geographicSaved.rows[0]] }), false);
const boundedRestore = JSON.parse(JSON.stringify(geographicSaved));
boundedRestore.rows[0].activeId = 'not-in-this-catalog';
boundedRestore.rows[0].anchorId = 'not-in-this-catalog';
boundedRestore.rows[0].left = 999999;
boundedRestore.activeGroupKey = 'removed-area';
boundedRestore.scrollTop = 999999;
assert.equal(sb.mallTileField.restoreGeographicState(boundedRestore), true);
assert.equal(groupTrack('wakasa').scrollLeft, groupTrack('wakasa').scrollWidth - groupTrack('wakasa').clientWidth);
assert.equal(wrapper.scrollTop, wrapper.scrollHeight - wrapper.clientHeight);
assert.equal(listenerCounts(), listenersBefore, 'geographic restoration adds no listeners');

// Existing video Enter/fullscreen behavior is still routed to the video player.
const video = { foundup_id: 'channel', name: 'Existing channel', video_count: 1, videos: [{ video_id: 'old-video' }] };
sb.mallTileField.updateCatalog([video]);
assert.equal(sb.mallTileField.getGeographicState(), null);
assert.equal(sb.mallTileField.restoreGeographicState(geographicSaved), false, 'video Mall cannot consume product state');
assert.equal(field.dataset.layout, 'rows', 'omitting groups restores the upstream category browse field');
assert.equal(sb.mallTileField.getLayoutMode(), 'rows');
assert.equal(wrapper.classList.contains('mall-field-grouped-wrapper'), false);
assert.equal(wrapper.classList.contains('browse-rows'), true);
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

// Category and geographic projections share one renderer without sharing state.
const categoryCatalog = Array.from({ length: 12 }, (_, i) => ({
  foundup_id: 'channel_' + i, name: 'Channel ' + i,
  category: ['travel', 'housing', 'automotive', 'clothing'][i % 4],
  geo: i === 0 ? 'Fukui, Japan' : 'Tokyo',
  videos: i === 5 ? [] : [{ video_id: 'video_' + i, title: 'Episode ' + i }],
  video_count: i === 5 ? 0 : 1
}));
sb.mallTileField.updateCatalog(categoryCatalog);
const categoryTracks = () => field.querySelectorAll('.mall-category-track');
const firstCategory = () => categoryTracks()[0];
assert.equal(categoryTracks().length, 4);
assert.deepEqual(firstCategory().querySelectorAll('.mall-tile').map(tile => tile.dataset.index), ['0', '4', '8']);
assert.deepEqual(firstCategory().querySelectorAll('.mall-tile').map(tile => Number(tile.dataset.tileIndex)), [0, 4, 8], 'load-state indexes follow catalog identity');
sb.mallTileField.togglePlay(5);
assert.equal(field.querySelector('.mall-tile[data-index="5"]').classList.contains('tap-pulse'), true, 'activation selects catalog index after category grouping');
assert.equal(field.querySelector('.mall-tile[data-index="9"]').classList.contains('tap-pulse'), false);
sb.mallPlanes.closeView();
firstCategory().scrollLeft = 0;
wrapper.scrollTop = 0;
const categoryCard = firstCategory().querySelector('.mall-tile-name');
categoryCard.fire('mousedown', { button: 0, clientX: 280, clientY: 160 });
doc.fire('mousemove', { clientX: 80, clientY: 140 });
doc.fire('mouseup');
assert.equal(firstCategory().scrollLeft, 200, 'ordinary category cards keep upstream horizontal drag');
assert.equal(wrapper.scrollTop, 20, 'ordinary drag retains upstream two-axis behavior');
await new Promise(resolve => setTimeout(resolve, 120));
field.querySelectorAll('[data-row-step]')[1].fire('click');
assert.equal(firstCategory().scrollLeft, 440, 'upstream row controls keep working');
sb.mallTileField.restoreRowOffsets({ travel: 180, housing: 90 });
const categoryOffsets = sb.mallTileField.getRowOffsets();
assert.equal(categoryOffsets.travel, 180);
assert.equal(sb.mallTileField.setLayoutMode('grid'), true);
assert.equal(categoryTracks().length, 0);
assert.equal(wrapper.classList.contains('browse-rows'), false);
assert.equal(sb.mallTileField.setLayoutMode('rows'), true);
assert.equal(firstCategory().scrollLeft, 180);
sb.matchMedia = query => ({ matches: query === '(prefers-reduced-motion: reduce)' });
wrapper.scrollTop = 330;
sb.mallTileField.expandFoundUp(0);
assert.equal(sb.mallTileField.isExpanded(), true);
sb.mallTileField.searchCatalog('show me houses');
assert.equal(sb.mallTileField.isExpanded(), false, 'catalog query clears old expanded media scope');
assert.equal(tiles().length, 3);
assert.equal(field.classList.contains('expanded-mode'), false);
for (const query of ['show me cars', 'show me clothes']) {
  sb.mallTileField.searchCatalog(query);
  assert.equal(tiles().length, 3);
}
sb.mallTileField.searchCatalog('show me videos on Fukui');
assert.deepEqual(tiles().map(tile => tile.dataset.foundupId), ['channel_0']);
sb.mallTileField.searchCatalog('unlisted category');
assert.equal(tiles().length, 0);
assert.deepEqual(Object.keys(sb.mallTileField.getTileLoadStates()), []);
sb.mallTileField.searchCatalog('');
assert.equal(tiles().length, 12);
assert.equal(sb.mallTileField.getFieldScope(), null);
wrapper.scrollTop = 330;
sb.mallTileField.expandFoundUp(0);
sb.mallTileField.collapseFoundUp();
assert.equal(wrapper.scrollTop, 330, 'upstream collapse restores vertical browse position');
assert.equal(firstCategory().scrollLeft, 180);
sb.mallTileField.setDensity('4x6');
assert.equal(sb.mallTileField.getLayoutMode(), 'grid', 'ordinary manual density still selects grid');
sb.mallTileField.updateCatalog(groupedCatalog, { groups });
assert.equal(sb.mallTileField.getLayoutMode(), 'grouped');
assert.equal(categoryTracks().length, 0);
assert.equal(wrapper.classList.contains('browse-rows'), false);
assert.equal(sb.mallTileField.restoreGeographicState(geographicSaved), true);
assert.equal(groupTrack('wakasa').scrollLeft, 250);
sb.mallTileField.updateCatalog(categoryCatalog);
assert.equal(sb.mallTileField.getLayoutMode(), 'grid', 'geography preserves the prior ordinary layout choice');
sb.mallTileField.setLayoutMode('rows');
assert.equal(firstCategory().scrollLeft, 180, 'category row offsets survive a geographic visit');
assert.equal(wrapper.classList.contains('mall-field-grouped-wrapper'), false);
assert.equal(listenerCounts(), listenersBefore, 'switching layouts, catalog queries and products adds no page listeners');
assert.equal(imageRequests.length, 0);
console.log('Mall property runtime: geographic/category projections, queries, both drag axes, stable indexes, restore, density, source facts, focus, URLs, and video compatibility passed.');
