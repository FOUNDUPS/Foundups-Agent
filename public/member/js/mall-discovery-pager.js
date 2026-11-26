(function (global) {
  'use strict';

  const ROOT = '/member/discovery/';
  const SLUG = /^[a-z0-9][a-z0-9_-]{0,63}$/i;
  const GENERATION = /^[a-f0-9]{64}$/;
  const VIDEO_ID = /^[A-Za-z0-9_-]{11}$/;
  const PAGE_PATH = /^\/member\/discovery\/[a-f0-9]{64}\/(?:catalog\/[0-9]{4,}\.json|videos\/[A-Za-z0-9][A-Za-z0-9_-]{0,63}\/catalog\/[0-9]{4,}\.json)$/;
  const reserved = new Set(['__proto__', 'constructor', 'prototype']);
  const validId = value => typeof value === 'string' && SLUG.test(value) && !reserved.has(value.toLowerCase());
  const catalogOrder = value => Array.isArray(value) && value.length === 1 && value[0] === 'catalog';

  function pathFor(generation, kind, id, page) {
    if (typeof generation !== 'string' || !GENERATION.test(generation) ||
        !Number.isSafeInteger(page) || page < 0 || (kind !== 'catalog' && kind !== 'videos') ||
        (kind === 'videos' && !validId(id))) throw new Error('Invalid discovery page identity.');
    const branch = kind === 'catalog' ? 'catalog/' : 'videos/' + id + '/catalog/';
    return ROOT + generation + '/' + branch + String(page).padStart(4, '0') + '.json';
  }

  function checkedPath(path) {
    if (typeof path !== 'string' || (path !== ROOT + 'catalog.json' && !PAGE_PATH.test(path))) {
      throw new Error('Unapproved discovery path.');
    }
    const url = new URL(path, global.location.origin);
    if (url.origin !== global.location.origin || url.pathname !== path || url.search || url.hash ||
        url.username || url.password || /%|\\/.test(path)) throw new Error('Unapproved discovery path.');
    return path;
  }

  function validatePage(page, expected) {
    if (!page || page.schema_version !== 1 || page.kind !== expected.kind || page.record_id !== expected.id ||
        page.order !== 'catalog' || page.page !== expected.page || page.page_size !== 6 ||
        typeof page.generation !== 'string' || !GENERATION.test(page.generation) ||
        (expected.generation && page.generation !== expected.generation) ||
        !Number.isSafeInteger(page.total) || page.total < 0 ||
        (expected.total !== undefined && page.total !== expected.total) ||
        !Number.isSafeInteger(page.page) || page.page < 0 ||
        !Array.isArray(page.items) || page.items.length > 6) {
      throw new Error('Discovery page does not match the selected generation or scope.');
    }
    const offset = page.page * 6;
    const length = Math.min(6, page.total - offset);
    if (!Number.isSafeInteger(offset) || length < 0 || (page.page > 0 && !length) ||
        page.items.length !== length || page.next !== (offset + length < page.total
          ? pathFor(page.generation, expected.kind, expected.id, page.page + 1) : null)) {
      throw new Error('Discovery page has an inconsistent count or cursor.');
    }
    const ids = new Set();
    if (expected.kind === 'catalog') {
      for (const item of page.items) {
        const key = validId(item?.foundup_id) ? item.foundup_id.toLowerCase() : null;
        if (!key || ids.has(key) || expected.seen.has(key) ||
            ['videos', 'creator_id', 'data_namespace', 'entry_url'].some(field => field in item) ||
            (item.canonical_foundup_id !== null && !validId(item.canonical_foundup_id)) ||
            !catalogOrder(item.available_orders) || !Number.isSafeInteger(item.video_count) ||
            item.video_count < 0 || !item.video_pages || Object.keys(item.video_pages).length !== 1 ||
            item.video_pages.catalog !== (item.video_count ? pathFor(page.generation, 'videos', item.foundup_id, 0) : null)) {
          throw new Error('Invalid discovery metadata.');
        }
        ids.add(key);
      }
    } else {
      if (!catalogOrder(page.available_orders)) throw new Error('Unsupported video ordering.');
      for (const item of page.items) {
        if (!item || typeof item.video_id !== 'string' || !VIDEO_ID.test(item.video_id) ||
            ids.has(item.video_id) || expected.seen.has(item.video_id) ||
            typeof item.title !== 'string') throw new Error('Invalid discovery video identity.');
        ids.add(item.video_id);
      }
    }
    return page;
  }

  async function open(path, identity, options) {
    const controller = new AbortController();
    const externalSignal = options?.signal;
    let closed = false;
    let epoch = 0;
    let inFlight = null;
    let next = null;
    let cursor = 0;
    let generation = identity.generation;
    let total = identity.total;
    const seen = new Set();
    const abortError = () => new DOMException('The discovery scope was closed.', 'AbortError');

    function close() {
      if (closed) return;
      closed = true;
      epoch++;
      next = null;
      externalSignal?.removeEventListener('abort', close);
      controller.abort();
    }
    if (externalSignal?.aborted) throw abortError();
    externalSignal?.addEventListener('abort', close, { once: true });

    async function read(target, pageNumber) {
      const requestEpoch = epoch;
      try {
        if (closed) throw abortError();
        const response = await global.fetch(checkedPath(target), {
          credentials: 'omit', cache: 'no-store', redirect: 'error', signal: controller.signal
        });
        if (closed || requestEpoch !== epoch) throw abortError();
        if (!response.ok || response.redirected ||
            !/^application\/json(?:\s*;|\s*$)/i.test(response.headers.get('content-type') || '')) {
          throw new Error('Discovery data is unavailable.');
        }
        if (response.url && response.url !== new URL(target, global.location.origin).href) {
          throw new Error('Discovery response changed its verified path.');
        }
        const data = await response.json();
        if (closed || requestEpoch !== epoch) throw abortError();
        return validatePage(data, { ...identity, generation, total, page: pageNumber, seen });
      } catch (error) {
        if (closed || requestEpoch !== epoch) throw abortError();
        throw error;
      }
    }

    function accept(page) {
      for (const item of page.items) {
        seen.add(identity.kind === 'catalog' ? item.foundup_id.toLowerCase() : item.video_id);
      }
      cursor = page.page;
      next = page.next;
    }

    let first;
    try {
      first = await read(path, 0);
      if (closed) throw abortError();
    } catch (error) {
      close();
      throw error;
    }
    generation = first.generation;
    total = first.total;
    accept(first);
    return {
      items: first.items.slice(),
      generation: generation,
      total: first.total,
      availableOrders: ['catalog'],
      get hasMore() { return !closed && next !== null; },
      loadNext: function () {
        if (closed) return Promise.reject(abortError());
        if (inFlight) return inFlight;
        if (!next) return Promise.resolve([]);
        const target = next;
        inFlight = read(target, cursor + 1).then(function (page) {
          if (closed) throw abortError();
          accept(page);
          return page.items.slice();
        }).finally(function () { inFlight = null; });
        return inFlight;
      },
      close: close
    };
  }

  global.mallDiscoveryPager = {
    openCatalog: function (options) { return open(ROOT + 'catalog.json', { kind: 'catalog', id: null }, options); },
    openVideos: function (record, order, options) {
      if (!record || !validId(record.foundup_id) || (order !== undefined && order !== 'catalog') ||
          !catalogOrder(record.available_orders) || !Number.isSafeInteger(record.video_count) || record.video_count < 0) {
        return Promise.reject(new Error('Unsupported discovery scope or ordering.'));
      }
      const path = record.video_pages?.catalog;
      const match = typeof path === 'string' && path.match(/^\/member\/discovery\/([a-f0-9]{64})\/videos\/([A-Za-z0-9][A-Za-z0-9_-]{0,63})\/catalog\/0000\.json$/);
      if (!record.video_count || !match || match[2] !== record.foundup_id) return Promise.reject(new Error('No verified video page is available.'));
      return open(path, { kind: 'videos', id: record.foundup_id, generation: match[1], total: record.video_count }, options);
    }
  };
})(window);
