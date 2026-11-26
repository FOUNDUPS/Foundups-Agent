/**
 * Mall Tile Graph Client — Public-Projection Enforcer, Voice/Text Intent Engine & Patch Client
 *
 * Contract: public/member/INTERFACE.md
 * WSP References: WSP 11 (Interface), WSP 97 (Truth Signalling)
 *
 * Security / Projection Boundary (§9.6):
 *   - Public Mall sessions MUST only accept `scope === 'public_mall'` graphs.
 *   - Refuses `scope === '012_architect'`, any `RED` tile, or any `principal_only` tile.
 *   - Search, counts, links (`#tile:<id>`), and ETag are computed strictly from `graph.tiles`
 *     of the `public_mall` projection alone.
 */
(function(root, factory) {
  'use strict';
  var api = factory();
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
  if (root && typeof root === 'object') {
    root.mallTileGraphClient = api;
  }
  if (typeof globalThis !== 'undefined' && globalThis && !globalThis.mallTileGraphClient) {
    globalThis.mallTileGraphClient = api;
  }
})(typeof window !== 'undefined' ? window : (typeof self !== 'undefined' ? self : this), function() {
  'use strict';

  var SCHEMA_VERSION = 'fractal_tile_graph.v1';
  var PUBLIC_SCOPE = 'public_mall';
  var ARCHITECT_SCOPE = '012_architect';
  var DEFAULT_PATCH_ENDPOINT = '/pfmall/tile-graph/patches';

  var OPERATING_LENSES = [
    'ALL',
    'MODE_1_COBUILD',
    'MODE_2_USER_FRACTAL',
    'MODE_3_INVESTOR_LICENSE',
    'MODE_4_MARKET_OVERRIDE',
    'MODE_5_WIKITUBE_STREAM'
  ];

  var LENS_LABELS = {
    ALL: 'All',
    MODE_1_COBUILD: 'Co-Build Sockets',
    MODE_2_USER_FRACTAL: 'User Fractals [HPC]',
    MODE_3_INVESTOR_LICENSE: 'Investor & Licensing',
    MODE_4_MARKET_OVERRIDE: 'Akiya Market',
    MODE_5_WIKITUBE_STREAM: 'WikiTube Autoplay'
  };

  var ELEMENT_MODES = [
    'video',
    'pictures',
    'podcast',
    'cards'
  ];

  var ELEMENT_MODE_LABELS = {
    video: 'Video',
    pictures: 'Pictures',
    podcast: 'Podcast / Audio',
    cards: 'Cards / Tools'
  };

  // Stopwords stripped in shared voice/text intent normalization (preserve 'papers', 'on', etc.)
  var INTENT_STOPWORDS = Object.create(null);
  ['all', 'show', 'open', 'go', 'to', 'me', 'find', 'search', 'for', 'the', 'a', 'an', 'please'].forEach(function(w) {
    INTENT_STOPWORDS[w] = true;
  });

  // Canonical phrase routing targets (only honored when present and visible in active graph.tiles)
  var CANONICAL_INTENT_TARGETS = {
    'papers': 'tile:opus:papers',
    'paper': 'tile:opus:papers',
    'research papers': 'tile:opus:papers',
    'undaodu': 'tile:opus:undaodu_linkedin',
    'undaodu linkedin': 'tile:opus:undaodu_linkedin',
    'return on compute': 'tile:opus:roc',
    'roc': 'tile:opus:roc',
    'japan hyperscaler report': 'tile:opus:jhr',
    'jhr': 'tile:opus:jhr',
    'hpc': 'tile:space:hpc',
    'schumerout': 'tile:space:hpc',
    'hasan piker coalition': 'tile:space:hpc',
    'autopost': 'tile:engine:autopost',
    'akiya': 'tile:market:japan_akiya',
    'japan akiya': 'tile:market:japan_akiya',
    'simulator': 'tile:sys:simulator',
    'foundups simulator': 'tile:sys:simulator',
    'tools': 'tile:tools:root',
    'pc tools': 'tile:tools:root',
    'benchmark': 'tile:tools:benchmark',
    'benchmarks': 'tile:tools:benchmark',
    'tools benchmark': 'tile:tools:benchmark',
    'benchmark harness': 'tile:harness:model_combination_benchmark',
    'model combination benchmark': 'tile:harness:model_combination_benchmark',
    'auto researcher': 'tile:harness:wre_auto_researcher',
    'wre auto researcher': 'tile:harness:wre_auto_researcher',
    'pubs': 'tile:pubs:root',
    'publications': 'tile:pubs:root',
    'wikitube': 'tile:stream:root',
    'modules': 'tile:modules:root',
    'domains': 'tile:modules:root',
    'repository': 'tile:modules:root',
    'codebase': 'tile:modules:root',
    'wsp': 'tile:sys:wsp_framework',
    'wsp framework': 'tile:sys:wsp_framework',
    'holo index': 'tile:sys:holo_index',
    'holoindex': 'tile:sys:holo_index'
  };

  var TYPED_DAG_EDGE_FIELDS = [
    'calls',
    'reads_from',
    'evaluates',
    'runs_through',
    'produces_receipt',
    'verified_by'
  ];

  // ========== Synchronous Canonical JSON & SHA-256 ==========

  function canonicalJsonString(value) {
    if (value === null || value === undefined) return 'null';
    var t = typeof value;
    if (t === 'boolean') return value ? 'true' : 'false';
    if (t === 'number') return Number.isFinite(value) ? JSON.stringify(value) : 'null';
    if (t === 'string') return JSON.stringify(value);
    if (Array.isArray(value)) {
      var arrParts = [];
      for (var i = 0; i < value.length; i++) {
        arrParts.push(value[i] === undefined ? 'null' : canonicalJsonString(value[i]));
      }
      return '[' + arrParts.join(',') + ']';
    }
    if (t === 'object') {
      var keys = Object.keys(value).filter(function(k) {
        return value[k] !== undefined;
      }).sort(function(a, b) {
        return a < b ? -1 : (a > b ? 1 : 0);
      });
      var objParts = [];
      for (var j = 0; j < keys.length; j++) {
        var k = keys[j];
        objParts.push(JSON.stringify(k) + ':' + canonicalJsonString(value[k]));
      }
      return '{' + objParts.join(',') + '}';
    }
    return 'null';
  }

  function utf8Bytes(str) {
    if (typeof TextEncoder !== 'undefined') {
      return new TextEncoder().encode(str);
    }
    var out = [];
    for (var i = 0; i < str.length; i++) {
      var code = str.charCodeAt(i);
      if (code < 0x80) {
        out.push(code);
      } else if (code < 0x800) {
        out.push(0xc0 | (code >> 6), 0x80 | (code & 0x3f));
      } else if (code >= 0xd800 && code <= 0xdbff && i + 1 < str.length) {
        var next = str.charCodeAt(++i);
        var cp = 0x10000 + (((code & 0x3ff) << 10) | (next & 0x3ff));
        out.push(
          0xf0 | (cp >> 18),
          0x80 | ((cp >> 12) & 0x3f),
          0x80 | ((cp >> 6) & 0x3f),
          0x80 | (cp & 0x3f)
        );
      } else {
        out.push(0xe0 | (code >> 12), 0x80 | ((code >> 6) & 0x3f), 0x80 | (code & 0x3f));
      }
    }
    return new Uint8Array(out);
  }

  var SHA256_K = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
  ];

  function sha256Hex(str) {
    var bytes = utf8Bytes(str);
    var bitLenHi = Math.floor((bytes.length * 8) / 0x100000000);
    var bitLenLo = (bytes.length * 8) >>> 0;
    var paddedLen = ((bytes.length + 9 + 63) >> 6) << 6;
    var buf = new Uint8Array(paddedLen);
    buf.set(bytes);
    buf[bytes.length] = 0x80;
    buf[paddedLen - 8] = (bitLenHi >>> 24) & 0xff;
    buf[paddedLen - 7] = (bitLenHi >>> 16) & 0xff;
    buf[paddedLen - 6] = (bitLenHi >>> 8) & 0xff;
    buf[paddedLen - 5] = bitLenHi & 0xff;
    buf[paddedLen - 4] = (bitLenLo >>> 24) & 0xff;
    buf[paddedLen - 3] = (bitLenLo >>> 16) & 0xff;
    buf[paddedLen - 2] = (bitLenLo >>> 8) & 0xff;
    buf[paddedLen - 1] = bitLenLo & 0xff;

    var H = [
      0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
      0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
    ];
    var W = new Uint32Array(64);
    var rotr = function(x, n) { return (x >>> n) | (x << (32 - n)); };

    for (var offset = 0; offset < paddedLen; offset += 64) {
      for (var t = 0; t < 16; t++) {
        var i = offset + t * 4;
        W[t] = ((buf[i] << 24) | (buf[i + 1] << 16) | (buf[i + 2] << 8) | buf[i + 3]) >>> 0;
      }
      for (var t2 = 16; t2 < 64; t2++) {
        var s0 = rotr(W[t2 - 15], 7) ^ rotr(W[t2 - 15], 18) ^ (W[t2 - 15] >>> 3);
        var s1 = rotr(W[t2 - 2], 17) ^ rotr(W[t2 - 2], 19) ^ (W[t2 - 2] >>> 10);
        W[t2] = (W[t2 - 16] + s0 + W[t2 - 7] + s1) >>> 0;
      }
      var a = H[0], b = H[1], c = H[2], d = H[3], e = H[4], f = H[5], g = H[6], h = H[7];
      for (var r = 0; r < 64; r++) {
        var S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
        var ch = (e & f) ^ ((~e) & g);
        var temp1 = (h + S1 + ch + SHA256_K[r] + W[r]) >>> 0;
        var S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
        var maj = (a & b) ^ (a & c) ^ (b & c);
        var temp2 = (S0 + maj) >>> 0;
        h = g; g = f; f = e; e = (d + temp1) >>> 0;
        d = c; c = b; b = a; a = (temp1 + temp2) >>> 0;
      }
      H[0] = (H[0] + a) >>> 0;
      H[1] = (H[1] + b) >>> 0;
      H[2] = (H[2] + c) >>> 0;
      H[3] = (H[3] + d) >>> 0;
      H[4] = (H[4] + e) >>> 0;
      H[5] = (H[5] + f) >>> 0;
      H[6] = (H[6] + g) >>> 0;
      H[7] = (H[7] + h) >>> 0;
    }
    var hex = '';
    for (var k = 0; k < 8; k++) {
      hex += ('00000000' + H[k].toString(16)).slice(-8);
    }
    return hex;
  }

  // ========== Normalization & Public-Projection Enforcement (§9.6) ==========

  function normalizeTilesMap(graph) {
    if (!graph || !graph.tiles) return {};
    if (Array.isArray(graph.tiles)) {
      var map = Object.create(null);
      for (var i = 0; i < graph.tiles.length; i++) {
        var item = graph.tiles[i];
        if (item && typeof item.tile_id === 'string' && item.tile_id) {
          map[item.tile_id] = item;
        }
      }
      return map;
    }
    if (typeof graph.tiles === 'object') {
      return graph.tiles;
    }
    return {};
  }

  function isPublicTile(tile) {
    if (!tile || typeof tile !== 'object') return false;
    if (tile.visibility_scope !== 'public') return false;
    if (tile.lifecycle && tile.lifecycle.state === 'RED') return false;
    if (tile.metadata && (tile.metadata.editorial_stage === 'DRAFT' || tile.metadata.editorial_stage === 'SCHEDULED_VERIFIED')) {
      return false;
    }
    return true;
  }

  function assertPublicProjection(graph) {
    if (!graph || typeof graph !== 'object' || Array.isArray(graph)) {
      throw new Error('Public projection violation: graph payload must be an object');
    }
    if (graph.scope === ARCHITECT_SCOPE) {
      throw new Error('Public projection violation: 012_architect scope is forbidden in public Mall sessions');
    }
    if (graph.scope !== PUBLIC_SCOPE) {
      throw new Error('Public projection violation: expected scope="public_mall", got "' + String(graph.scope) + '"');
    }
    if (!graph.tiles || typeof graph.tiles !== 'object') {
      throw new Error('Public projection violation: missing graph.tiles');
    }

    var tiles = normalizeTilesMap(graph);
    var tileIds = Object.keys(tiles);
    for (var i = 0; i < tileIds.length; i++) {
      var tid = tileIds[i];
      var tile = tiles[tid];
      if (!tile || typeof tile !== 'object') {
        throw new Error('Public projection violation: invalid tile entry at ' + tid);
      }
      if (tile.lifecycle && tile.lifecycle.state === 'RED') {
        throw new Error('Public projection violation: RED tile refused in public session (' + tid + ')');
      }
      if (tile.visibility_scope === 'principal_only' || tile.visibility_scope !== 'public') {
        throw new Error('Public projection violation: principal_only/non-public tile refused (' + tid + ')');
      }
      if (tile.metadata && (tile.metadata.editorial_stage === 'DRAFT' || tile.metadata.editorial_stage === 'SCHEDULED_VERIFIED')) {
        throw new Error('Public projection violation: private draft/scheduled tile refused (' + tid + ')');
      }
    }

    return {
      ok: true,
      scope: PUBLIC_SCOPE,
      tileCount: tileIds.length
    };
  }

  function getPublicCounts(graph, options) {
    if (!(options && options.validated === true && graph && graph.scope === PUBLIC_SCOPE &&
          graph.tiles && typeof graph.tiles === 'object')) {
      assertPublicProjection(graph);
    }
    var tiles = normalizeTilesMap(graph);
    var ids = Object.keys(tiles);
    var byState = {};
    var byKind = {};
    for (var i = 0; i < ids.length; i++) {
      var tile = tiles[ids[i]];
      var st = (tile.lifecycle && tile.lifecycle.state) || 'UNKNOWN';
      var kd = tile.tile_kind || 'unknown';
      byState[st] = (byState[st] || 0) + 1;
      byKind[kd] = (byKind[kd] || 0) + 1;
    }
    return {
      total_tiles: ids.length,
      by_state: byState,
      by_kind: byKind
    };
  }

  function getPublicTileLink(graph, tileId) {
    assertPublicProjection(graph);
    if (typeof tileId !== 'string' || !tileId) return null;
    var tiles = normalizeTilesMap(graph);
    if (!Object.prototype.hasOwnProperty.call(tiles, tileId)) return null;
    if (!isPublicTile(tiles[tileId])) return null;
    return '#tile:' + tileId;
  }

  function getPublicGraphEtag(graph) {
    assertPublicProjection(graph);
    var tiles = normalizeTilesMap(graph);
    return sha256Hex(canonicalJsonString(tiles));
  }

  function verifyPublicGraphEtag(graph) {
    var computed = getPublicGraphEtag(graph);
    var serverEtag = (graph && typeof graph.public_graph_etag === 'string') ? graph.public_graph_etag.trim() : '';
    return {
      ok: true,
      computedEtag: computed,
      serverEtag: serverEtag || null,
      matched: !!serverEtag && computed === serverEtag
    };
  }

  // ========== Graph Hierarchy & Lens Helpers ==========

  function tileMatchesScope(tile, allowArchitect) {
    if (!tile || typeof tile !== 'object') return false;
    return allowArchitect ? true : isPublicTile(tile);
  }

  function getVisibleTileMap(graph, options) {
    var allowArchitect = !!(options && options.allowArchitect && graph && graph.scope === ARCHITECT_SCOPE);
    if (!allowArchitect) {
      if (!(options && options.validated === true && graph && graph.scope === PUBLIC_SCOPE &&
            graph.tiles && typeof graph.tiles === 'object')) {
        assertPublicProjection(graph);
      }
    }
    return {
      tiles: normalizeTilesMap(graph),
      allowArchitect: allowArchitect
    };
  }

  function collectChildIdsFromCtx(ctx, tileId) {
    var tiles = ctx.tiles;
    var tile = tiles[tileId];
    if (!tile) return [];
    var seen = Object.create(null);
    var out = [];

    function pushIfVisible(id) {
      if (typeof id !== 'string' || !id || id === tileId || seen[id]) return;
      var target = tiles[id];
      if (!target || !tileMatchesScope(target, ctx.allowArchitect)) return;
      seen[id] = true;
      out.push(id);
    }

    var children = Array.isArray(tile.children_tile_ids) ? tile.children_tile_ids : [];
    for (var i = 0; i < children.length; i++) {
      pushIfVisible(children[i]);
    }
    if (tile.tile_kind === 'opus_series' && tile.dag_edges && Array.isArray(tile.dag_edges.collection_refs)) {
      var refs = tile.dag_edges.collection_refs;
      for (var j = 0; j < refs.length; j++) {
        pushIfVisible(refs[j]);
      }
    }
    return out;
  }

  function getChildTileIds(graph, tileId, options) {
    return collectChildIdsFromCtx(getVisibleTileMap(graph, options), tileId);
  }

  function getCrossLinkTileIds(graph, tileId, options) {
    var ctx = getVisibleTileMap(graph, options);
    var tiles = ctx.tiles;
    var tile = tiles[tileId];
    if (!tile || !tile.dag_edges || !Array.isArray(tile.dag_edges.cross_links)) return [];
    var childSet = Object.create(null);
    var children = collectChildIdsFromCtx(ctx, tileId);
    for (var i = 0; i < children.length; i++) childSet[children[i]] = true;

    var out = [];
    var seen = Object.create(null);
    for (var j = 0; j < tile.dag_edges.cross_links.length; j++) {
      var cid = tile.dag_edges.cross_links[j];
      if (typeof cid !== 'string' || !cid || cid === tileId || childSet[cid] || seen[cid]) continue;
      var target = tiles[cid];
      if (!target || !tileMatchesScope(target, ctx.allowArchitect)) continue;
      seen[cid] = true;
      out.push(cid);
    }
    return out;
  }

  function isParentCube(graph, tileId, options) {
    return getChildTileIds(graph, tileId, options).length > 0;
  }

  function getTypedNeighbors(graph, tileId, options) {
    var ctx = getVisibleTileMap(graph, options);
    var tiles = ctx.tiles;
    var tile = tiles[tileId];
    var edgeNames = ['imports_tiles', 'reusable_candidates', 'cross_links', 'collection_refs'].concat(TYPED_DAG_EDGE_FIELDS);
    var result = {};
    for (var i = 0; i < edgeNames.length; i++) {
      result[edgeNames[i]] = [];
    }
    if (!tile || !tile.dag_edges || typeof tile.dag_edges !== 'object') {
      return result;
    }
    for (var j = 0; j < edgeNames.length; j++) {
      var efield = edgeNames[j];
      var rawList = Array.isArray(tile.dag_edges[efield]) ? tile.dag_edges[efield] : [];
      var seen = Object.create(null);
      for (var k = 0; k < rawList.length; k++) {
        var targetId = rawList[k];
        if (typeof targetId !== 'string' || !targetId || targetId === tileId || seen[targetId]) continue;
        var target = tiles[targetId];
        if (!target || !tileMatchesScope(target, ctx.allowArchitect)) continue;
        seen[targetId] = true;
        result[efield].push({
          tile_id: targetId,
          display_name: target.display_name || targetId,
          tile_kind: target.tile_kind || 'unknown',
          state: (target.lifecycle && target.lifecycle.state) || 'GRAY'
        });
      }
    }
    return result;
  }

  function getInboundNeighbors(graph, tileId, options) {
    var ctx = getVisibleTileMap(graph, options);
    var tiles = ctx.tiles;
    var target = tiles[tileId];
    var out = {
      called_by: [],
      used_by: [],
      evaluated_by: []
    };
    if (!target) return out;
    var seenCalled = Object.create(null);
    var seenUsed = Object.create(null);
    var seenEval = Object.create(null);
    var allIds = Object.keys(tiles);
    for (var i = 0; i < allIds.length; i++) {
      var sid = allIds[i];
      if (!sid || sid === tileId) continue;
      var src = tiles[sid];
      if (!src || !tileMatchesScope(src, ctx.allowArchitect) || !src.dag_edges) continue;
      var de = src.dag_edges;
      var callsArr = (Array.isArray(de.calls) ? de.calls : []).concat(Array.isArray(de.imports_tiles) ? de.imports_tiles : []);
      if (callsArr.indexOf(tileId) !== -1 && !seenCalled[sid]) {
        seenCalled[sid] = true;
        out.called_by.push({
          tile_id: sid,
          display_name: src.display_name || sid,
          tile_kind: src.tile_kind || 'unknown',
          state: (src.lifecycle && src.lifecycle.state) || 'GRAY'
        });
      }
      var crossArr = Array.isArray(de.cross_links) ? de.cross_links : [];
      if (crossArr.indexOf(tileId) !== -1 && !seenUsed[sid] && !seenCalled[sid]) {
        seenUsed[sid] = true;
        out.used_by.push({
          tile_id: sid,
          display_name: src.display_name || sid,
          tile_kind: src.tile_kind || 'unknown',
          state: (src.lifecycle && src.lifecycle.state) || 'GRAY'
        });
      }
      var evalArr = Array.isArray(de.evaluates) ? de.evaluates : [];
      if (evalArr.indexOf(tileId) !== -1 && !seenEval[sid]) {
        seenEval[sid] = true;
        out.evaluated_by.push({
          tile_id: sid,
          display_name: src.display_name || sid,
          tile_kind: src.tile_kind || 'unknown',
          state: (src.lifecycle && src.lifecycle.state) || 'GRAY'
        });
      }
    }
    function resolveUsedByTileId(rawId) {
      if (typeof rawId !== 'string' || !rawId) return null;
      if (tiles[rawId] && tileMatchesScope(tiles[rawId], ctx.allowArchitect)) {
        return rawId;
      }
      if (rawId.indexOf('tile:') !== 0) {
        var candidates = [
          'tile:investor:' + rawId,
          'tile:mod:foundups.' + rawId,
          'tile:sys:' + rawId,
          'tile:engine:' + rawId,
          'tile:space:' + rawId
        ];
        for (var c = 0; c < candidates.length; c++) {
          var cid = candidates[c];
          if (tiles[cid] && tileMatchesScope(tiles[cid], ctx.allowArchitect)) {
            return cid;
          }
        }
      }
      return null;
    }

    if (target.dag_edges && Array.isArray(target.dag_edges.used_by_foundups)) {
      for (var u = 0; u < target.dag_edges.used_by_foundups.length; u++) {
        var uid = resolveUsedByTileId(target.dag_edges.used_by_foundups[u]);
        if (uid && uid !== tileId && !seenUsed[uid]) {
          seenUsed[uid] = true;
          out.used_by.push({
            tile_id: uid,
            display_name: tiles[uid].display_name || uid,
            tile_kind: tiles[uid].tile_kind || 'unknown',
            state: (tiles[uid].lifecycle && tiles[uid].lifecycle.state) || 'GRAY'
          });
        }
      }
    }
    return out;
  }

  function deriveStandardStatusSurface(tile) {
    if (!tile || typeof tile !== 'object') {
      return {
        verdictSurface: 'UNVERIFIED',
        decisionLifecycle: null,
        functionalityState: 'UNKNOWN',
        integrationState: 'UNKNOWN'
      };
    }
    var meta = tile.metadata || {};
    var be = meta.benchmark_evidence || null;
    var rv = meta.registry_verification || null;
    var st = (tile.lifecycle && tile.lifecycle.state) || 'GRAY';

    var verdictSurface = 'UNVERIFIED';
    var decisionLifecycle = (be && be.decision_lifecycle) || null;
    if (be) {
      var rawV = String(be.effective_verdict || be.verdict || '').toUpperCase();
      var avail = String(be.availability || '').toUpperCase();
      if (rawV === 'PLANNED_SOCKET' || st === 'BLUE' && tile.tile_kind === 'socket_slot') {
        verdictSurface = 'PLANNED';
      } else if (avail.indexOf('UNAVAILABLE') !== -1 || avail.indexOf('OFFLINE') !== -1 || avail.indexOf('BLOCKED') !== -1 || rawV === 'UNAVAILABLE' || rawV === 'BLOCKED') {
        verdictSurface = 'UNAVAILABLE';
      } else if (rawV === 'ACCEPT' || rawV === 'ACCEPTED') {
        verdictSurface = 'ACCEPTED';
      } else if (rawV === 'REJECT' || rawV === 'REJECTED') {
        verdictSurface = 'REJECTED';
      } else if (be.rehydrated_ok === true) {
        verdictSurface = 'ACCEPTED';
      } else {
        verdictSurface = 'UNVERIFIED';
      }
    } else if (st === 'BLUE' || tile.tile_kind === 'socket_slot') {
      verdictSurface = 'PLANNED';
    } else if (rv) {
      var fs = String(rv.functionality_state || '');
      if (fs === 'LOCALLY_TEST_EXECUTED_PASS' || fs === 'OBSERVED_RUNTIME') {
        verdictSurface = 'ACCEPTED';
      } else {
        verdictSurface = 'UNVERIFIED';
      }
    } else if (st === 'GREEN') {
      verdictSurface = 'ACCEPTED';
    }

    return {
      verdictSurface: verdictSurface,
      decisionLifecycle: decisionLifecycle,
      functionalityState: (rv && rv.functionality_state) || 'UNKNOWN',
      integrationState: (rv && rv.integration_state) || 'UNKNOWN'
    };
  }

  var APP_SYS_TILE_IDS = {
    'tile:mall:root': true,
    'tile:sys:simulator': true,
    'tile:sys:gotjunk': true,
    'tile:sys:antifafm': true,
    'tile:sys:move2japan': true,
    'tile:sys:esingularity': true,
    'tile:sys:yumori': true,
    'tile:sys:pfmall': true,
    'tile:sys:public_member': true,
    'tile:mockup:gotjunk': true,
    'tile:mockup:antifafm': true,
    'tile:mockup:move2japan': true,
    'tile:mockup:esingularity': true,
    'tile:mockup:yumori': true
  };

  function deriveFoundupKind(tile) {
    if (!tile || typeof tile !== 'object') return 'tool';
    var meta = tile.metadata || {};
    var tkind = tile.tile_kind || '';
    if (tkind === 'opus_series' || tkind === 'opus_item') {
      return 'card';
    }
    if (meta.foundup_kind === 'application' || meta.foundup_kind === 'tool' || meta.foundup_kind === 'card') {
      return meta.foundup_kind;
    }
    var tid = tile.tile_id || '';
    if (APP_SYS_TILE_IDS[tid] ||
        tkind === 'community_fractal' ||
        tkind === 'foundup_venture' ||
        tkind === 'market_override' ||
        tkind === 'wikitube_stream') {
      return 'application';
    }
    return 'tool';
  }

  function deriveElementModes(tile) {
    if (!tile || typeof tile !== 'object') return ['cards'];
    var meta = tile.metadata || {};
    if (Array.isArray(meta.canonical_element_modes) && meta.canonical_element_modes.length) {
      var filtered = ELEMENT_MODES.filter(function(m) {
        return meta.canonical_element_modes.indexOf(m) !== -1;
      });
      if (filtered.length) return filtered;
    }
    var tid = String(tile.tile_id || '');
    var lowTid = tid.toLowerCase();
    var tkind = tile.tile_kind || '';
    var modes;
    if (tid === 'tile:mall:root') {
      modes = ['video', 'pictures', 'cards'];
    } else if (tkind === 'wikitube_stream' || tid.indexOf('tile:stream:') === 0) {
      modes = lowTid.indexOf('antifafm') !== -1 ? ['video', 'podcast', 'cards'] : ['video', 'cards'];
    } else if (tkind === 'community_fractal' || tkind === 'foundup_venture') {
      modes = lowTid.indexOf('antifafm') !== -1 ? ['video', 'podcast', 'cards'] : ['video', 'pictures', 'cards'];
    } else if (tkind === 'market_override' || tkind === 'mockup_cube') {
      modes = ['pictures', 'cards'];
    } else if (tkind === 'opus_series' || tkind === 'opus_item') {
      modes = ['cards'];
    } else if (tid === 'tile:engine:autopost') {
      modes = ['video', 'pictures', 'cards'];
    } else {
      modes = ['cards'];
    }
    return ELEMENT_MODES.filter(function(m) { return modes.indexOf(m) !== -1; });
  }

  function deriveElementMediaStatus(tile, elementMode) {
    var mode = ELEMENT_MODES.indexOf(elementMode) !== -1 ? elementMode : 'video';
    if (!tile || typeof tile !== 'object') {
      return { mode: mode, state: 'unavailable', available: false, label: 'Media unavailable offline' };
    }
    var meta = tile.metadata || {};
    var dom = tile.domain_override_manifest || {};
    var payload = dom.payload || {};
    var modes = deriveElementModes(tile);
    var hasPlaylist = dom.override_type === 'wikitube_playlist' && Array.isArray(payload.ordered_segments) && payload.ordered_segments.length > 0;
    var hasVideoRef = !!(hasPlaylist || meta.video_id || meta.embed_url || tile.tile_kind === 'wikitube_stream');
    var hasAudioRef = !!(meta.audio_url || meta.podcast_url || meta.stream_audio_url);
    var hasPictureRef = !!(meta.poster_url || meta.image_url || meta.thumbnail_url || (Array.isArray(meta.gallery) && meta.gallery.length > 0));

    if (mode === 'video') {
      if (hasVideoRef) {
        return {
          mode: mode,
          state: 'local_snapshot_stream',
          available: true,
          label: 'Video · Local snapshot metadata (live stream requires network/auth)'
        };
      }
      if (modes.indexOf('video') !== -1) {
        return {
          mode: mode,
          state: 'snapshot_unavailable',
          available: false,
          label: 'Video · Local snapshot only (no stream offline)'
        };
      }
      return {
        mode: mode,
        state: 'unavailable',
        available: false,
        label: 'No video stream in local snapshot'
      };
    }
    if (mode === 'podcast') {
      if (hasAudioRef) {
        return {
          mode: mode,
          state: 'local_snapshot_audio',
          available: true,
          label: 'Podcast / Audio · Local snapshot metadata (stream requires network/auth)'
        };
      }
      if (modes.indexOf('podcast') !== -1) {
        return {
          mode: mode,
          state: 'snapshot_unavailable',
          available: false,
          label: 'Podcast / Audio · Local snapshot metadata only (no audio stream offline)'
        };
      }
      return {
        mode: mode,
        state: 'unavailable',
        available: false,
        label: 'Audio stream unavailable in local snapshot'
      };
    }
    if (mode === 'pictures') {
      if (hasPictureRef) {
        return {
          mode: mode,
          state: 'local_snapshot_pictures',
          available: true,
          label: 'Pictures · Local snapshot metadata'
        };
      }
      if (modes.indexOf('pictures') !== -1) {
        return {
          mode: mode,
          state: 'snapshot_unavailable',
          available: false,
          label: 'Pictures · Local snapshot metadata only (no image/poster offline)'
        };
      }
      return {
        mode: mode,
        state: 'unavailable',
        available: false,
        label: 'No pictures in local snapshot'
      };
    }
    if (mode === 'cards') {
      var fKind = deriveFoundupKind(tile);
      return {
        mode: 'cards',
        state: 'snapshot_ready',
        available: true,
        label: (fKind === 'card' ? 'Card element · Papers & text' : (fKind === 'application' ? 'Application card' : 'Tool card') + ' · Local snapshot')
      };
    }
    if (deriveFoundupKind(tile) === 'card') {
      return {
        mode: mode,
        state: 'unavailable',
        available: false,
        label: 'Card element · Open as card (no ' + mode + ' stream)'
      };
    }
  }

  function isBenchmarkOrToolId(tid) {
    return (
      tid.indexOf('tile:tools:') === 0 ||
      tid.indexOf('tile:tool:') === 0 ||
      tid.indexOf('tile:harness:') === 0 ||
      tid.indexOf('tile:benchcfg:') === 0 ||
      tid.indexOf('tile:benchrun:') === 0 ||
      tid.indexOf('tile:benchevidence:') === 0 ||
      tid.indexOf('tile:receipt:') === 0
    );
  }

  function tileMatchesLens(tile, lens) {
    if (!tile) return false;
    if (!lens || lens === 'ALL') return true;
    var tid = tile.tile_id || '';
    var kind = tile.tile_kind || '';
    switch (lens) {
      case 'MODE_1_COBUILD':
        return (
          kind === 'system_cube' ||
          kind === 'code_module' ||
          kind === 'socket_slot' ||
          kind === 'mockup_cube' ||
          tid.indexOf('tile:sys:') === 0 ||
          tid.indexOf('tile:sub:') === 0 ||
          tid.indexOf('tile:socket:') === 0 ||
          tid.indexOf('tile:mod:') === 0 ||
          isBenchmarkOrToolId(tid)
        );
      case 'MODE_2_USER_FRACTAL':
        return (
          kind === 'community_fractal' ||
          tid.indexOf('tile:space:') === 0 ||
          (tile.owner_namespace && tile.owner_namespace.indexOf('hpc') === 0)
        );
      case 'MODE_3_INVESTOR_LICENSE':
        return (
          kind === 'foundup_venture' ||
          kind === 'licensable_engine' ||
          tid.indexOf('tile:investor:') === 0 ||
          tid.indexOf('tile:engine:') === 0
        );
      case 'MODE_4_MARKET_OVERRIDE':
        return kind === 'market_override' || tid.indexOf('tile:market:') === 0;
      case 'MODE_5_WIKITUBE_STREAM':
        return kind === 'wikitube_stream' || tid.indexOf('tile:stream:') === 0 || tid.indexOf('tile:space:hpc.schumerout') === 0;
      default:
        return true;
    }
  }

  function inferLensForTile(tile) {
    if (!tile) return 'ALL';
    var tid = tile.tile_id || '';
    var kind = tile.tile_kind || '';
    if (tid.indexOf('tile:pubs:') === 0 || tid.indexOf('tile:opus:') === 0 || kind === 'opus_series' || kind === 'opus_item') {
      return 'ALL';
    }
    if (kind === 'community_fractal' || tid.indexOf('tile:space:hpc') === 0) {
      return 'MODE_2_USER_FRACTAL';
    }
    if (kind === 'licensable_engine' || kind === 'foundup_venture' || tid.indexOf('tile:engine:') === 0 || tid.indexOf('tile:investor:') === 0) {
      return 'MODE_3_INVESTOR_LICENSE';
    }
    if (kind === 'market_override' || tid.indexOf('tile:market:') === 0) {
      return 'MODE_4_MARKET_OVERRIDE';
    }
    if (kind === 'wikitube_stream' || tid.indexOf('tile:stream:') === 0) {
      return 'MODE_5_WIKITUBE_STREAM';
    }
    if (kind === 'system_cube' || kind === 'code_module' || kind === 'socket_slot' || tid.indexOf('tile:sys:') === 0 || tid.indexOf('tile:sub:') === 0 || isBenchmarkOrToolId(tid)) {
      return 'MODE_1_COBUILD';
    }
    return 'ALL';
  }

  // ========== Shared Search & Voice/Text Navigation Intent Engine ==========

  function cleanPunctuationLower(rawInput) {
    return String(rawInput == null ? '' : rawInput)
      .normalize('NFKC')
      .toLowerCase()
      .replace(/[^\p{L}\p{N}\s]/gu, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function normalizeIntentQuery(rawInput) {
    var cleaned = cleanPunctuationLower(rawInput);
    if (!cleaned) return '';
    var words = cleaned.split(' ').filter(function(token) {
      return token && !INTENT_STOPWORDS[token];
    });
    return words.join(' ').trim();
  }

  function escapeRegExp(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  function hasWordBoundaryMatch(haystack, needle) {
    if (!needle) return false;
    var re = new RegExp('(?:^|\\s|[^\\p{L}\\p{N}])' + escapeRegExp(needle) + '(?:$|\\s|[^\\p{L}\\p{N}])', 'u');
    return re.test(haystack);
  }

  function scoreTileMatch(tile, rawClean, normQuery, tokens) {
    if (!tile || !normQuery) return 0;
    var tid = (tile.tile_id || '').toLowerCase();
    var display = cleanPunctuationLower(tile.display_name || '');
    var englishTitle = cleanPunctuationLower((tile.metadata && tile.metadata.english_title) || '');
    var metaTitle = cleanPunctuationLower((tile.metadata && tile.metadata.title) || '');
    var keywords = (tile.search_keywords || []).map(cleanPunctuationLower).filter(Boolean);
    var aliases = (tile.author_aliases || []).map(cleanPunctuationLower).filter(Boolean);
    var metaText = cleanPunctuationLower([
      tile.metadata && tile.metadata.subtitle,
      tile.metadata && tile.metadata.issue_key,
      tile.metadata && tile.metadata.foundup_id,
      tile.metadata && tile.metadata.domain,
      tile.metadata && tile.metadata.module_name,
      tile.metadata && tile.metadata.municipality,
      tile.metadata && tile.metadata.prefecture,
      tile.metadata && tile.metadata.description
    ].filter(Boolean).join(' '));

    var idTail = tid.split(':').pop() || '';
    var idLeafSegment = idTail.split('.').pop() || '';
    var score = 0;

    // Canonical identifier / exact display matches
    if (idTail === normQuery || idLeafSegment === normQuery) score += 1200;
    if (display === normQuery || englishTitle === normQuery) score += 1000;
    if (display.indexOf(normQuery) === 0 || englishTitle.indexOf(normQuery) === 0) score += 600;
    if (hasWordBoundaryMatch(display, normQuery) || hasWordBoundaryMatch(englishTitle, normQuery)) score += 450;

    // Keywords & author aliases
    for (var i = 0; i < keywords.length; i++) {
      var kw = keywords[i];
      if (kw === normQuery || kw === rawClean) {
        score += 320;
      } else if (hasWordBoundaryMatch(kw, normQuery)) {
        score += 180;
      } else if (normQuery.length > 4 && kw.indexOf(normQuery) !== -1) {
        score += 110;
      }
    }
    for (var j = 0; j < aliases.length; j++) {
      var al = aliases[j];
      if (al === normQuery) {
        score += 220;
      } else if (hasWordBoundaryMatch(al, normQuery)) {
        score += 120;
      }
    }

    // Token coverage across searchable fields (all tokens must appear for multi-word queries)
    var combined = [tid.replace(/[:._-]/g, ' '), display, englishTitle, metaTitle, keywords.join(' '), aliases.join(' '), metaText].join(' ');
    var allTokensMatch = true;
    var tokenScore = 0;
    for (var k = 0; k < tokens.length; k++) {
      var tok = tokens[k];
      if (tok.length <= 4) {
        if (hasWordBoundaryMatch(combined, tok)) {
          tokenScore += 60;
        } else {
          allTokensMatch = false;
          break;
        }
      } else {
        if (hasWordBoundaryMatch(combined, tok)) {
          tokenScore += 70;
        } else if (combined.indexOf(tok) !== -1) {
          tokenScore += 40;
        } else {
          allTokensMatch = false;
          break;
        }
      }
    }
    if (allTokensMatch) {
      score += tokenScore;
    } else if (score === 0) {
      return 0;
    }

    // Avoid letting broad root containers outrank specific collections when query targets a child collection
    if (tid === 'tile:mall:root' && normQuery !== 'mall' && normQuery !== 'playfoundups' && normQuery !== 'playfoundups mall') {
      score = Math.max(0, score - 500);
    }
    if (tid === 'tile:pubs:root' && normQuery !== 'pubs' && normQuery !== 'publications') {
      score = Math.max(0, score - 250);
    }
    if (tile.tile_kind === 'opus_series') {
      score += 45;
    }

    return score;
  }

  function publicSearch(graph, query, options) {
    assertPublicProjection(graph);
    options = options || {};
    var tiles = normalizeTilesMap(graph);
    var rawClean = cleanPunctuationLower(query);
    var normQuery = normalizeIntentQuery(query);
    if (!normQuery) return [];
    var tokens = normQuery.split(' ').filter(Boolean);
    var limit = typeof options.limit === 'number' && options.limit > 0 ? options.limit : 250;

    var results = [];
    var ids = Object.keys(tiles);
    for (var i = 0; i < ids.length; i++) {
      var tid = ids[i];
      var tile = tiles[tid];
      if (!isPublicTile(tile)) continue;
      if (options.lens && options.lens !== 'ALL' && !tileMatchesLens(tile, options.lens)) continue;
      if (options.tileKind && tile.tile_kind !== options.tileKind) continue;

      var s = scoreTileMatch(tile, rawClean, normQuery, tokens);
      if (s > 0) {
        results.push({
          tile_id: tid,
          display_name: tile.display_name || tid,
          tile_kind: tile.tile_kind || 'unknown',
          state: (tile.lifecycle && tile.lifecycle.state) || 'UNKNOWN',
          score: s,
          link: '#tile:' + tid,
          tile: tile
        });
      }
    }

    results.sort(function(a, b) {
      if (b.score !== a.score) return b.score - a.score;
      return a.tile_id < b.tile_id ? -1 : (a.tile_id > b.tile_id ? 1 : 0);
    });

    return results.slice(0, limit);
  }

  function resolveNavigationIntent(graph, rawInput, channel) {
    var normalizedChannel = channel === 'voice' ? 'voice' : 'text';
    assertPublicProjection(graph);
    var tiles = normalizeTilesMap(graph);
    var normQuery = normalizeIntentQuery(rawInput);

    if (normQuery === 'back') {
      return {
        action: 'back',
        targetTileId: null,
        matchedTileIds: [],
        lens: null,
        normalizedQuery: 'back',
        channel: normalizedChannel
      };
    }

    if (!normQuery) {
      return {
        action: 'clear',
        targetTileId: null,
        matchedTileIds: [],
        lens: 'ALL',
        normalizedQuery: '',
        channel: normalizedChannel
      };
    }

    var matches = publicSearch(graph, normQuery);
    var matchedIds = matches.map(function(m) { return m.tile_id; });

    var canonicalTarget = Object.prototype.hasOwnProperty.call(CANONICAL_INTENT_TARGETS, normQuery)
      ? CANONICAL_INTENT_TARGETS[normQuery]
      : null;

    var targetTileId = null;
    if (canonicalTarget && tiles[canonicalTarget] && isPublicTile(tiles[canonicalTarget])) {
      targetTileId = canonicalTarget;
      var filtered = [canonicalTarget];
      for (var i = 0; i < matchedIds.length; i++) {
        if (matchedIds[i] !== canonicalTarget) filtered.push(matchedIds[i]);
      }
      matchedIds = filtered;
    } else if (matchedIds.length > 0) {
      targetTileId = matchedIds[0];
    }

    if (!targetTileId) {
      return {
        action: 'no_match',
        targetTileId: null,
        matchedTileIds: [],
        lens: null,
        normalizedQuery: normQuery,
        channel: normalizedChannel
      };
    }

    var targetTile = tiles[targetTileId];
    var isContainer = isParentCube(graph, targetTileId);
    var action = isContainer ? 'explode' : 'inspect';
    var lens = inferLensForTile(targetTile);

    return {
      action: action,
      targetTileId: targetTileId,
      matchedTileIds: matchedIds,
      lens: lens,
      normalizedQuery: normQuery,
      channel: normalizedChannel
    };
  }

  // ========== Authenticated UI Patch Client (§9.5) ==========

  var lastPatchRequest = null;

  function clonePayload(val) {
    if (val === undefined) return {};
    return JSON.parse(JSON.stringify(val));
  }

  function formatIfMatch(etag) {
    var s = String(etag || '').trim();
    if (!s) return '';
    if (s.charAt(0) === '"' && s.charAt(s.length - 1) === '"') return s;
    return '"' + s + '"';
  }

  async function executePatchRequest(cfg) {
    var endpoint = cfg.endpoint || DEFAULT_PATCH_ENDPOINT;
    var fetchFn = cfg.fetchImpl || (typeof fetch === 'function' ? fetch : null);
    if (typeof fetchFn !== 'function') {
      return {
        ok: false,
        httpStatus: 0,
        outcome: 'unavailable',
        detail: 'fetch_unavailable',
        patch_id: cfg.patchId,
        data: null
      };
    }
    if (!cfg.bearerToken || typeof cfg.bearerToken !== 'string') {
      return {
        ok: false,
        httpStatus: 401,
        outcome: 'unauthorized',
        detail: 'missing_bearer_token',
        patch_id: cfg.patchId,
        data: null
      };
    }
    if (!cfg.patchId || !cfg.baseGraphEtag || !cfg.op || !cfg.targetTileId) {
      return {
        ok: false,
        httpStatus: 400,
        outcome: 'invalid_request',
        detail: 'patchId, baseGraphEtag, op, and targetTileId are required',
        patch_id: cfg.patchId || null,
        data: null
      };
    }

    var headers = {
      'Authorization': 'Bearer ' + cfg.bearerToken,
      'If-Match': formatIfMatch(cfg.baseGraphEtag),
      'Content-Type': 'application/json'
    };
    var resolvedOrigin = cfg.origin || (typeof window !== 'undefined' && window.location && window.location.origin) || '';
    if (resolvedOrigin) {
      headers['Origin'] = resolvedOrigin;
    }

    var body = {
      patch_id: cfg.patchId,
      base_graph_etag: cfg.baseGraphEtag,
      tenant: cfg.tenant || null,
      scope: cfg.scope || null,
      op: cfg.op,
      target_tile_id: cfg.targetTileId,
      payload: clonePayload(cfg.payload)
    };

    var response;
    try {
      response = await fetchFn(endpoint, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(body)
      });
    } catch (err) {
      return {
        ok: false,
        httpStatus: 0,
        outcome: 'network_error',
        detail: String(err && err.message ? err.message : err),
        patch_id: cfg.patchId,
        data: null
      };
    }

    var data = {};
    try {
      if (typeof response.json === 'function') {
        data = await response.json();
      } else if (typeof response.text === 'function') {
        var rawText = await response.text();
        data = rawText ? JSON.parse(rawText) : {};
      }
    } catch (_e) {
      data = {};
    }
    if (!data || typeof data !== 'object') data = {};

    var status = Number(response.status || 0);
    if (status === 201) {
      return {
        ok: true,
        httpStatus: 201,
        outcome: 'committed',
        idempotent_replay: false,
        patch_id: data.patch_id || cfg.patchId,
        receipt: data.receipt !== undefined ? data.receipt : data,
        graph_etag: data.graph_etag || data.current_graph_etag || null,
        public_graph_etag: data.public_graph_etag || null,
        data: data
      };
    }
    if (status === 200) {
      return {
        ok: true,
        httpStatus: 200,
        outcome: 'idempotent_replay',
        idempotent_replay: true,
        patch_id: data.patch_id || cfg.patchId,
        receipt: data.receipt !== undefined ? data.receipt : data,
        graph_etag: data.graph_etag || data.current_graph_etag || null,
        public_graph_etag: data.public_graph_etag || null,
        data: data
      };
    }
    if (status === 409) {
      return {
        ok: false,
        httpStatus: 409,
        outcome: 'conflict',
        detail: data.detail || 'etag_conflict',
        current_graph_etag: data.current_graph_etag || data.graph_etag || null,
        patch_id: cfg.patchId,
        data: data
      };
    }
    if (status === 401 || status === 403) {
      return {
        ok: false,
        httpStatus: status,
        outcome: 'unauthorized',
        detail: data.detail || 'unauthorized',
        patch_id: cfg.patchId,
        data: data
      };
    }
    if (status === 503) {
      return {
        ok: false,
        httpStatus: 503,
        outcome: 'unavailable',
        detail: data.detail || 'unavailable',
        patch_id: cfg.patchId,
        data: data
      };
    }
    return {
      ok: false,
      httpStatus: status,
      outcome: 'error',
      detail: data.detail || ('http_' + status),
      patch_id: cfg.patchId,
      data: data
    };
  }

  async function submitGraphPatch(options) {
    options = options || {};
    var cfg = {
      endpoint: options.endpoint || DEFAULT_PATCH_ENDPOINT,
      fetchImpl: options.fetchImpl || null,
      bearerToken: options.bearerToken || '',
      origin: options.origin || '',
      patchId: options.patchId || '',
      baseGraphEtag: options.baseGraphEtag || '',
      tenant: options.tenant || '',
      scope: options.scope || '',
      op: options.op || '',
      targetTileId: options.targetTileId || '',
      payload: clonePayload(options.payload)
    };
    lastPatchRequest = cfg;
    return executePatchRequest(cfg);
  }

  async function retryLastPatch(overrides) {
    if (!lastPatchRequest) {
      return {
        ok: false,
        httpStatus: 0,
        outcome: 'no_previous_patch',
        detail: 'no_previous_patch_to_retry',
        data: null
      };
    }
    overrides = overrides || {};
    var replayCfg = {
      endpoint: overrides.endpoint || lastPatchRequest.endpoint,
      fetchImpl: overrides.fetchImpl || lastPatchRequest.fetchImpl,
      bearerToken: overrides.bearerToken || lastPatchRequest.bearerToken,
      origin: overrides.origin || lastPatchRequest.origin,
      // Strictly preserve idempotency identity and payload across retries
      patchId: lastPatchRequest.patchId,
      baseGraphEtag: lastPatchRequest.baseGraphEtag,
      tenant: lastPatchRequest.tenant,
      scope: lastPatchRequest.scope,
      op: lastPatchRequest.op,
      targetTileId: lastPatchRequest.targetTileId,
      payload: clonePayload(lastPatchRequest.payload)
    };
    return executePatchRequest(replayCfg);
  }

  function sortFractalTiles(tilesList, sortOrder, options) {
    options = options || {};
    var allowArchitect = !!(options.allowArchitect && options.scope === ARCHITECT_SCOPE);
    var list = Array.isArray(tilesList) ? tilesList.slice() : [];
    var order = sortOrder || 'default';

    if (order === 'scheduled_asc' && !allowArchitect) {
      throw new Error('Public projection violation: scheduled_asc sort is restricted to 012_architect scope');
    }

    if (order === 'default') return list;

    function getPublishedTimestamp(tile) {
      var m = tile && tile.metadata;
      if (!m) return null;
      var raw = m.published_at_utc || m.published_date || null;
      if (!raw || typeof raw !== 'string') return null;
      var ms = Date.parse(raw);
      return Number.isFinite(ms) ? ms : null;
    }

    function getScheduledTimestamp(tile) {
      var m = tile && tile.metadata;
      if (!m || typeof m.scheduled_release_at !== 'string') return null;
      var ms = Date.parse(m.scheduled_release_at);
      return Number.isFinite(ms) ? ms : null;
    }

    function cmpId(a, b) {
      var aid = (a && a.tile_id) || '';
      var bid = (b && b.tile_id) || '';
      return aid < bid ? -1 : (aid > bid ? 1 : 0);
    }

    list.sort(function(a, b) {
      if (order === 'published_desc' || order === 'published_asc') {
        var ta = getPublishedTimestamp(a);
        var tb = getPublishedTimestamp(b);
        if (ta === null && tb === null) return cmpId(a, b);
        if (ta === null) return 1;
        if (tb === null) return -1;
        if (ta !== tb) return order === 'published_desc' ? (tb - ta) : (ta - tb);
        return cmpId(a, b);
      }
      if (order === 'title_asc') {
        var na = String((a && a.display_name) || '').toLowerCase();
        var nb = String((b && b.display_name) || '').toLowerCase();
        if (na !== nb) return na < nb ? -1 : 1;
        return cmpId(a, b);
      }
      if (order === 'scheduled_asc') {
        var sa = getScheduledTimestamp(a);
        var sb = getScheduledTimestamp(b);
        if (sa === null && sb === null) return cmpId(a, b);
        if (sa === null) return 1;
        if (sb === null) return -1;
        if (sa !== sb) return sa - sb;
        return cmpId(a, b);
      }
      return cmpId(a, b);
    });

    return list;
  }

  function getLastPatchMeta() {
    if (!lastPatchRequest) return null;
    return {
      endpoint: lastPatchRequest.endpoint,
      patchId: lastPatchRequest.patchId,
      baseGraphEtag: lastPatchRequest.baseGraphEtag,
      tenant: lastPatchRequest.tenant,
      scope: lastPatchRequest.scope,
      op: lastPatchRequest.op,
      targetTileId: lastPatchRequest.targetTileId,
      payload: clonePayload(lastPatchRequest.payload)
    };
  }

  return {
    SCHEMA_VERSION: SCHEMA_VERSION,
    PUBLIC_SCOPE: PUBLIC_SCOPE,
    ARCHITECT_SCOPE: ARCHITECT_SCOPE,
    OPERATING_LENSES: OPERATING_LENSES.slice(),
    LENS_LABELS: Object.assign({}, LENS_LABELS),
    ELEMENT_MODES: ELEMENT_MODES.slice(),
    ELEMENT_MODE_LABELS: Object.assign({}, ELEMENT_MODE_LABELS),
    TYPED_DAG_EDGE_FIELDS: TYPED_DAG_EDGE_FIELDS.slice(),
    assertPublicProjection: assertPublicProjection,
    isPublicTile: isPublicTile,
    normalizeTilesMap: normalizeTilesMap,
    getPublicCounts: getPublicCounts,
    getPublicTileLink: getPublicTileLink,
    getPublicGraphEtag: getPublicGraphEtag,
    verifyPublicGraphEtag: verifyPublicGraphEtag,
    getChildTileIds: getChildTileIds,
    getCrossLinkTileIds: getCrossLinkTileIds,
    getTypedNeighbors: getTypedNeighbors,
    getInboundNeighbors: getInboundNeighbors,
    deriveStandardStatusSurface: deriveStandardStatusSurface,
    deriveFoundupKind: deriveFoundupKind,
    deriveElementModes: deriveElementModes,
    deriveElementMediaStatus: deriveElementMediaStatus,
    isParentCube: isParentCube,
    tileMatchesLens: tileMatchesLens,
    inferLensForTile: inferLensForTile,
    normalizeIntentQuery: normalizeIntentQuery,
    publicSearch: publicSearch,
    resolveNavigationIntent: resolveNavigationIntent,
    sortFractalTiles: sortFractalTiles,
    submitGraphPatch: submitGraphPatch,
    retryLastPatch: retryLastPatch,
    getLastPatchMeta: getLastPatchMeta,
    canonicalJsonString: canonicalJsonString,
    sha256Hex: sha256Hex
  };
});
