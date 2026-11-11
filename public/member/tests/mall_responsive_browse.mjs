/** Browser integration: real Mall renderer, fixture catalog, no auth/provider calls.
 * PLAYWRIGHT_MODULE_PATH may point to a runtime-owned Playwright installation.
 * Run: node public/member/tests/mall_responsive_browse.mjs
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE_PATH
  ? pathToFileURL(process.env.PLAYWRIGHT_MODULE_PATH).href : 'playwright');
const root = resolve('public/member');
const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE_PATH || undefined });
const errors = [];
try {
  const page = await browser.newPage({ viewport: { width: 390, height: 844 }, reducedMotion: 'reduce' });
  page.on('pageerror', e => errors.push(e.message));
  await page.route('**/*', route => route.fulfill({ contentType: 'text/html', body: '<!doctype html><title>Mall fixture</title>' }));
  await page.goto('http://mall.test/');
  await page.setContent('<style>body{margin:0;color:white;background:#111}main{height:100vh;display:flex;flex-direction:column;min-width:0}.mall-tile{position:relative;background:#334;overflow:hidden}</style><main><div id="mallTileField"></div></main>');
  await page.addStyleTag({ content: readFileSync(root + '/css/mall-tile-field.css', 'utf8') });
  for (const name of ['gesture-engine', 'mall-tile-field', 'mall-state-restore', 'pfmall-control-dispatcher']) {
    await page.addScriptTag({ content: readFileSync(root + '/js/' + name + '.js', 'utf8') });
  }
  await page.evaluate(() => {
    window.fixture = Array.from({ length: 60 }, (_, i) => ({
      foundup_id: 'channel_' + i, name: 'Channel ' + i, category: ['travel','housing','automotive','clothing','music'][i % 5],
      geo: i === 0 ? 'Fukui, Japan' : 'Tokyo', tags: ['catalog'], creator: 'creator_' + i,
      videos: [{video_id: 'video_' + i, title: i === 0 ? 'Fukui walk' : 'Episode ' + i}], video_count: 1
    }));
    mallTileField.initialize(fixture);
    mallStateRestore.bindAutoSave();
  });
  let counts = [];
  for (const width of [390, 768, 1024, 1440]) {
    await page.setViewportSize({width, height: 600});
    const geometry = await page.evaluate(() => {
      const outer = document.querySelector('.mall-tile-field-wrapper');
      const row = document.querySelector('.mall-category-track');
      const tile = row.querySelector('.mall-tile');
      return {vertical: outer.scrollHeight > outer.clientHeight, horizontal: row.scrollWidth > row.clientWidth,
        visible: row.clientWidth / tile.getBoundingClientRect().width, pageOverflow: document.documentElement.scrollWidth > innerWidth};
    });
    assert(geometry.vertical && geometry.horizontal, 'two-axis browsing at ' + width);
    assert(!geometry.pageOverflow, 'no whole-page horizontal overflow at ' + width);
    counts.push(geometry.visible);
  }
  assert(counts[3] > counts[0] + 2, 'wider device reveals more cards');
  assert.deepEqual(await page.locator('.mall-category-track').first().locator('.mall-tile').evaluateAll(tiles => tiles.map(t => Number(t.dataset.index))), [0,5,10,15,20,25,30,35,40,45,50,55]);
  await page.setViewportSize({width: 768, height: 600});
  const tile = page.locator('.mall-category-track').first().locator('.mall-tile').first();
  const box = await tile.boundingBox();
  await page.mouse.move(box.x + box.width - 20, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + 10, box.y + box.height / 2, { steps: 12 });
  await page.mouse.up();
  await page.waitForTimeout(200);
  assert(await page.locator('.mall-category-track').first().evaluate(row => row.scrollLeft > 0), 'drag on card scrolls row');
  assert.equal(await page.evaluate(() => mallTileField.getPlayingIndex()), null, 'drag does not start playback');
  await page.evaluate(() => { document.querySelector('.mall-category-track').scrollLeft = 350; mallStateRestore.save(); });
  const savedOffset = await page.evaluate(() => mallStateRestore.peek().rowOffsets.travel);
  assert(savedOffset > 0);
  await page.evaluate(() => mallTileField.expandFoundUp(0));
  await page.waitForTimeout(100);
  assert(await page.evaluate(() => mallTileField.isExpanded()));
  await page.evaluate(() => mallTileField.searchCatalog('show me houses'));
  assert.equal(await page.evaluate(() => mallTileField.isExpanded()), false, 'search exits expanded channel');
  assert.equal(await page.locator('.mall-tile').count(), 12, 'housing alias matches');
  await page.evaluate(() => mallTileField.searchCatalog('show me videos on Fukui'));
  assert.equal(await page.locator('.mall-tile').count(), 1, 'location + media query');
  assert.equal(await page.locator('.mall-tile').first().getAttribute('data-foundup-id'), 'channel_0');
  await page.evaluate(() => mallTileField.searchCatalog('show me cars'));
  assert.equal(await page.locator('.mall-tile').count(), 12);
  await page.evaluate(() => mallTileField.searchCatalog('show me clothes'));
  assert.equal(await page.locator('.mall-tile').count(), 12);
  await page.evaluate(() => mallTileField.searchCatalog('unlisted category'));
  assert.equal(await page.locator('.mall-tile').count(), 0, 'unknown query has truthful empty state');
  await page.evaluate(() => mallStateRestore.restore());
  await page.waitForTimeout(100);
  assert.equal(await page.locator('.mall-tile').count(), 60, 'restore unfiltered scope');
  assert(await page.locator('.mall-category-track').first().evaluate(row => row.scrollLeft > 0), 'restore row offset');
  const result = await page.evaluate(() => pfmallControlDispatcher.dispatch('search_catalog', {query: 'show me cars'}));
  assert.equal(result.status, 'ok');
  assert.equal(await page.locator('.mall-tile').count(), 12);
  const invalid = await page.evaluate(() => pfmallControlDispatcher.dispatch('search_catalog', {query: 'x'.repeat(301)}));
  assert.equal(invalid.status, 'error');
  await page.evaluate(() => mallTileField.clearFieldScope());
  const beforeExpand = await page.evaluate(() => {
    const wrapper = document.querySelector('.mall-tile-field-wrapper');
    wrapper.scrollTop = wrapper.scrollHeight;
    return wrapper.scrollTop;
  });
  await page.evaluate(() => { mallTileField.expandFoundUp(4); mallTileField.collapseFoundUp(); });
  assert.equal(await page.locator('.mall-tile-field-wrapper').evaluate(el => el.scrollTop), beforeExpand, 'collapse preserves vertical browse position');
  await page.evaluate(() => mallTileField.setLayoutMode('grid'));
  assert.equal(await page.locator('.mall-category-track').count(), 0);
  await page.evaluate(() => mallTileField.setLayoutMode('rows'));
  assert.equal(await page.locator('.mall-category-track').count(), 5);
  assert.deepEqual(errors, []);
  console.log('PASS responsive rows, four widths, drag, indexes, search, expand, restore, grid compatibility');
} finally { await browser.close(); }
