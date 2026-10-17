/* Move2Japan public discovery adapter. Rendering and navigation belong to Mall.
 * This catalog contains public observations only; this is not an entitlement gate.
 */
(function (root, factory) {
  'use strict';
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root && root.document) {
    root.Move2JapanSearch = api;
    var scriptUrl = root.document.currentScript && root.document.currentScript.src;
    api.mount(root, new URL('properties.json', scriptUrl || root.location.href).href);
  }
})(typeof window !== 'undefined' ? window : null, function () {
  'use strict';
  var SCHEMA = 'move2japan_property_catalog.v1';
  var SAFE_ID = /^fukui-\d{1,8}$/;
  var DATE = /^\d{4}-\d{2}-\d{2}$/;
  var SORTS = ['price_asc', 'price_desc', 'land_desc', 'town'];

  function text(value, limit) {
    return typeof value === 'string' ? value.replace(/[\u0000-\u001f\u007f]/g, ' ').trim().slice(0, limit) : '';
  }
  function number(value, max) {
    return typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= max ? value : null;
  }
  function sourceUrl(value, sourceId) {
    try {
      var url = new URL(value);
      if (url.protocol !== 'https:' || url.hostname !== 'akiya.pref.fukui.lg.jp' ||
          url.port || url.username || url.password || url.search || url.hash ||
          url.pathname !== '/webroot/public/estate/detail/' + sourceId) return '';
      return url.href;
    } catch (_) { return ''; }
  }
  function validDate(value) {
    return typeof value === 'string' && DATE.test(value) &&
      !Number.isNaN(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value;
  }

  function normalizeCatalog(data) {
    if (!data || data.schema_version !== SCHEMA || data.foundup_id !== 'move2japan' ||
        data.catalog_kind !== 'curated_public_source_observations' ||
        !validDate(data.observed_on) || !Array.isArray(data.properties) || data.properties.length > 500) {
      throw new Error('Unsupported public property catalog');
    }
    var seen = new Set();
    var properties = data.properties.map(function (row) {
      if (!row || row.source_type !== 'property_listing' || row.foundup_id !== 'move2japan' ||
          row.transaction !== 'sale' || row.availability !== 'source_listed' ||
          !SAFE_ID.test(row.listing_id) || typeof row.source_item_id !== 'string' ||
          row.listing_id !== 'fukui-' + row.source_item_id || seen.has(row.listing_id)) {
        throw new Error('Invalid or duplicate public listing identity');
      }
      var source = sourceUrl(row.source_url, row.source_item_id);
      var price = number(row.price_jpy, 1e12);
      if (!source || price === null || !Number.isInteger(price) || !validDate(row.last_checked) ||
          !text(row.name, 120) || !text(row.municipality, 80) || row.prefecture !== 'Fukui') {
        throw new Error('Invalid public listing provenance');
      }
      seen.add(row.listing_id);
      // Deliberate allowlist: no account, token, poster, private notes or entitlement fields.
      return {
        foundup_id: 'move2japan', source_type: 'property_listing',
        listing_id: row.listing_id, source_item_id: row.source_item_id,
        name: text(row.name, 120), theme: 'move2japan', transaction: 'sale',
        price_jpy: price, prefecture: 'Fukui', municipality: text(row.municipality, 80),
        address_ja: text(row.address_ja, 180),
        land_area_m2: number(row.land_area_m2, 1e7),
        building_area_m2: number(row.building_area_m2, 1e7),
        building_area_label_ja: text(row.building_area_label_ja, 40),
        floors: Number.isInteger(row.floors) ? number(row.floors, 100) : null,
        construction_date: typeof row.construction_date === 'string' && /^\d{4}-(0[1-9]|1[0-2])$/.test(row.construction_date) ? row.construction_date : null,
        repair_level: row.repair_level === 'major' ? 'major' : 'unknown',
        summary: text(row.summary, 1000),
        tags: Array.isArray(row.tags) ? row.tags.slice(0, 12).map(function (v) { return text(v, 40); }).filter(Boolean) : [],
        virtual_tour_at_source: row.virtual_tour_at_source === true,
        source_name: text(row.source_name, 100), source_url: source,
        last_checked: row.last_checked, availability: 'source_listed'
      };
    });
    return { schema_version: SCHEMA, observed_on: data.observed_on, properties: properties };
  }

  function searchProperties(properties, filters) {
    filters = filters || {};
    var query = text(filters.query, 80).toLocaleLowerCase('en').split(/\s+/).filter(Boolean);
    var area = text(filters.area, 80).toLocaleLowerCase('en');
    var budget = number(filters.max_price_jpy, 1e12);
    var result = properties.filter(function (row) {
      if (area && row.municipality.toLocaleLowerCase('en') !== area) return false;
      if (budget !== null && row.price_jpy > budget) return false;
      if (filters.large_plots && (row.land_area_m2 === null || row.land_area_m2 < 500)) return false;
      if (filters.virtual_tours && !row.virtual_tour_at_source) return false;
      var haystack = [row.name, row.municipality, row.prefecture, row.address_ja, row.summary].concat(row.tags).join(' ').toLocaleLowerCase('en');
      return query.every(function (term) { return haystack.indexOf(term) !== -1; });
    });
    result.sort(function (a, b) {
      var difference = filters.sort === 'price_desc' ? b.price_jpy - a.price_jpy :
        filters.sort === 'land_desc' ? (b.land_area_m2 === null ? -1 : b.land_area_m2) - (a.land_area_m2 === null ? -1 : a.land_area_m2) :
        filters.sort === 'town' ? a.municipality.localeCompare(b.municipality, 'en') : a.price_jpy - b.price_jpy;
      return difference || a.listing_id.localeCompare(b.listing_id, 'en');
    });
    return result;
  }

  function mount(win, catalogUrl) {
    var doc = win.document;
    var form = doc.getElementById('propertySearch');
    if (!form) return;
    var query = doc.getElementById('propertyQuery');
    var area = doc.getElementById('propertyArea');
    var budget = doc.getElementById('propertyBudget');
    var sort = doc.getElementById('propertySort');
    var large = doc.getElementById('largePlots');
    var tours = doc.getElementById('virtualTours');
    var count = doc.getElementById('resultCount');
    var error = doc.getElementById('listingError');
    var empty = doc.getElementById('noResults');
    var wrapper = doc.getElementById('propertyFieldWrapper');
    var catalog = null;
    var initialized = false;
    var loading = false;

    function filters() {
      return { query: query.value, area: area.value,
        max_price_jpy: budget.value === '' ? null : Number(budget.value),
        sort: sort.value, large_plots: large.checked, virtual_tours: tours.checked };
    }
    function restoreUrl() {
      var params = new URL(win.location.href).searchParams;
      query.value = text(params.get('q'), 80);
      area.value = params.get('area') || '';
      budget.value = params.get('max') || '';
      sort.value = SORTS.indexOf(params.get('sort')) !== -1 ? params.get('sort') : 'price_asc';
      large.checked = params.get('large') === '1';
      tours.checked = params.get('tour') === '1';
    }
    function updateUrl() {
      var url = new URL(win.location.href);
      var values = { q: query.value.trim(), area: area.value, max: budget.value,
        sort: sort.value === 'price_asc' ? '' : sort.value,
        large: large.checked ? '1' : '', tour: tours.checked ? '1' : '' };
      Object.keys(values).forEach(function (key) { if (values[key]) url.searchParams.set(key, values[key]); else url.searchParams.delete(key); });
      win.history.replaceState(null, '', url.pathname + url.search + url.hash);
    }
    function paint(persist) {
      if (!catalog) return;
      var rows = searchProperties(catalog.properties, filters());
      if (!initialized) {
        win.mallPlanes.setCatalog(rows);
        win.mallTileField.initialize(rows);
        win.mallTileField.setMotionMode('glide');
        initialized = true;
      } else win.mallTileField.updateCatalog(rows);
      wrapper.hidden = rows.length === 0;
      empty.hidden = rows.length !== 0;
      count.textContent = rows.length + (rows.length === 1 ? ' home' : ' homes') + ' in this collection';
      if (persist) updateUrl();
    }
    function reset() {
      form.reset(); large.checked = false; tours.checked = false;
      paint(true);
    }
    async function load() {
      if (loading) return;
      loading = true; error.hidden = true; empty.hidden = true;
      count.textContent = 'Loading source listings…';
      form.setAttribute('aria-busy', 'true');
      try {
        if (!win.mallTileField || !win.mallPlanes) throw new Error('Mall unavailable');
        var response = await win.fetch(catalogUrl, { cache: 'no-cache', credentials: 'same-origin' });
        if (!response.ok) throw new Error('Catalog unavailable');
        catalog = normalizeCatalog(await response.json());
        area.replaceChildren();
        var allOption = doc.createElement('option'); allOption.value = ''; allOption.textContent = 'All of Fukui'; area.appendChild(allOption);
        Array.from(new Set(catalog.properties.map(function (row) { return row.municipality; }))).sort().forEach(function (town) {
          var option = doc.createElement('option'); option.value = town; option.textContent = town; area.appendChild(option);
        });
        restoreUrl();
        var dateLabel = new Date(catalog.observed_on + 'T00:00:00Z').toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
        doc.getElementById('checkedDate').textContent = 'Source pages checked ' + dateLabel;
        paint(false);
      } catch (_) {
        catalog = null;
        if (initialized) win.mallTileField.updateCatalog([]);
        wrapper.hidden = true; error.hidden = false;
        count.textContent = 'Collection unavailable';
        doc.getElementById('checkedDate').textContent = '';
      } finally { loading = false; form.removeAttribute('aria-busy'); }
    }
    form.addEventListener('submit', function (event) { event.preventDefault(); paint(true); });
    form.addEventListener('input', function () { paint(true); });
    large.addEventListener('change', function () { paint(true); });
    tours.addEventListener('change', function () { paint(true); });
    doc.getElementById('resetSearch').addEventListener('click', reset);
    doc.getElementById('clearEmptySearch').addEventListener('click', function () { reset(); query.focus(); });
    doc.getElementById('retryListings').addEventListener('click', load);
    win.addEventListener('popstate', function () { if (catalog) { restoreUrl(); paint(false); } });
    load();
  }
  return { normalizeCatalog: normalizeCatalog, searchProperties: searchProperties, mount: mount };
});
