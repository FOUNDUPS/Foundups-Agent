/* Move2Japan supplies public facts and geographic projections.
 * The shared Mall owns shell, row navigation, tiles and detail planes.
 */
(function (root, factory) {
  'use strict';
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root && root.document) {
    root.Move2JapanSearch = api;
    // Select the product before the existing Mall controllers bind their DOM.
    // The Mall's boot script mounts data after those shared controllers load.
    api.prepareShell(root);
  }
})(typeof window !== 'undefined' ? window : null, function () {
  'use strict';
  var SCHEMA = 'move2japan_property_catalog.v2';
  var SAFE_ID = /^fukui-\d{1,8}$/;
  var DATE = /^\d{4}-\d{2}-\d{2}$/;
  var SORTS = ['price_asc', 'price_desc', 'land_desc', 'town'];
  var LAND = ['with_land', 'no_land', 'unknown'];
  var REPAIRS = ['major', 'some', 'none_reported', 'unknown'];
  function isShellProductRoute(location) {
    if (!location || (location.pathname !== '/member/' && location.pathname !== '/member/index.html')) return false;
    var products = new URLSearchParams(location.search || '').getAll('foundup');
    return products.length === 1 && products[0] === 'move2japan';
  }
  function prepareShell(win) {
    if (!isShellProductRoute(win.location)) return false;
    var doc = win.document;
    if (doc.body.classList.contains('m2j-site')) return true;
    var field = doc.getElementById('mallTileField');
    var main = doc.querySelector('.mall-main');
    var plane = doc.getElementById('accountPlane');
    var host = doc.querySelector('[data-reddog-discovery]');
    var fieldTemplate = doc.getElementById('move2japanFieldTemplate');
    var searchTemplate = doc.getElementById('move2japanSearchTemplate');
    if (!field || !main || !plane || !host || !fieldTemplate || !searchTemplate) return false;
    var content = fieldTemplate.content.cloneNode(true);
    var wrapper = content.querySelector('#propertyFieldWrapper');
    if (!wrapper) return false;
    field.setAttribute('aria-label', 'Houses grouped by area');
    field.setAttribute('aria-describedby', 'fieldDirections');
    field.setAttribute('tabindex', '-1');
    wrapper.replaceChildren(field);
    main.replaceChildren(content);
    main.setAttribute('aria-label', 'House discovery');
    host.appendChild(searchTemplate.content.cloneNode(true));
    host.hidden = false;
    plane.setAttribute('data-reddog-mode', 'product-discovery');
    doc.body.classList.add('m2j-site');
    doc.body.setAttribute('data-foundup-id', 'move2japan');
    doc.title = 'Move2Japan — Houses in the Foundups Mall';
    doc.getElementById('loadingState').style.display = 'none';
    doc.getElementById('memberArea').style.display = 'block';
    doc.getElementById('mallUserHandle').textContent = 'Foundups account';
    var brand = doc.querySelector('.mall-brand-minimal');
    if (brand) {
      brand.href = 'https://foundups.com/member/';
      brand.setAttribute('aria-label', 'Foundups Mall');
      var group = doc.createElement('div'); group.className = 'm2j-brand-group';
      brand.parentNode.insertBefore(group, brand); group.appendChild(brand);
      var title = doc.createElement('h1'); title.className = 'm2j-title'; title.textContent = 'Move2Japan'; group.appendChild(title);
      var videos = doc.createElement('a'); videos.className = 'm2j-account';
      videos.href = 'https://foundups.com/member/?creator=move2japan'; videos.textContent = 'Videos'; group.appendChild(videos);
    }
    var hints = doc.getElementById('gestureHints');
    if (hints) {
      var labels = ['↔ Houses in the same area', '↕ Scroll between different areas', 'Tap a house for details and its source'];
      hints.querySelectorAll('.gesture-hint-item').forEach(function (item, index) { item.textContent = labels[index] || ''; });
    }
    var account = host.querySelector('[data-reddog-discovery-account]');
    if (account) account.addEventListener('click', function () {
      if (!win.mallStateRestore) return;
      win.mallStateRestore.save();
      win.mallStateRestore.rememberProductReturn('move2japan');
    });
    return true;
  }
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
    return typeof value === 'string' && DATE.test(value) && !Number.isNaN(Date.parse(value)) &&
      new Date(value).toISOString().slice(0, 10) === value;
  }
  function normalizeCatalog(data) {
    if (!data || data.schema_version !== SCHEMA || data.foundup_id !== 'move2japan' ||
        data.catalog_kind !== 'curated_public_source_observations' || !validDate(data.observed_on) ||
        !Array.isArray(data.properties) || data.properties.length > 500) {
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
      var validPrice = row.price_status === 'asking' ? price !== null && Number.isInteger(price) :
        (row.price_status === 'negotiable' || row.price_status === 'unknown') && row.price_jpy === null;
      var landArea = number(row.land_area_m2, 1e7);
      var validLand = row.land_status === 'with_land' ? landArea !== null && landArea > 0 :
        row.land_status === 'no_land' ? row.land_area_m2 === 0 :
        row.land_status === 'unknown' && row.land_area_m2 === null;
      if (!source || !validPrice || !validLand || !validDate(row.last_checked) ||
          !text(row.name, 120) || !text(row.municipality, 80) || row.prefecture !== 'Fukui' ||
          row.country_code !== 'JP' || row.country !== 'Japan' || !text(row.locality_ja, 80) ||
          REPAIRS.indexOf(row.repair_level) === -1) throw new Error('Invalid public listing provenance');
      seen.add(row.listing_id);
      // Public allowlist: no account, token, poster, private note or release fields.
      return {
        foundup_id: 'move2japan', source_type: 'property_listing',
        listing_id: row.listing_id, source_item_id: row.source_item_id,
        name: text(row.name, 120), theme: 'move2japan', transaction: 'sale',
        price_jpy: price, price_status: row.price_status,
        country_code: 'JP', country: 'Japan', prefecture: 'Fukui',
        municipality: text(row.municipality, 80), municipality_ja: text(row.municipality_ja, 80),
        locality: text(row.locality, 80) || text(row.locality_ja, 80), locality_ja: text(row.locality_ja, 80),
        address_ja: text(row.address_ja, 180), land_area_m2: landArea, land_status: row.land_status,
        building_area_m2: number(row.building_area_m2, 1e7),
        building_area_label_ja: text(row.building_area_label_ja, 40),
        floors: Number.isInteger(row.floors) ? number(row.floors, 100) : null,
        construction_date: typeof row.construction_date === 'string' && /^\d{4}-(0[1-9]|1[0-2])$/.test(row.construction_date) ? row.construction_date : null,
        layout: text(row.layout, 40), repair_level: row.repair_level, summary: text(row.summary, 1000),
        source_notes: Array.isArray(row.source_notes) ? row.source_notes.slice(0, 6).map(function (v) { return text(v, 400); }).filter(Boolean) : [],
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
    var country = text(filters.country, 80).toUpperCase();
    var prefecture = text(filters.prefecture, 80).toLocaleLowerCase('en');
    var city = text(filters.city || filters.area, 80).toLocaleLowerCase('en');
    var locality = text(filters.locality, 80);
    var budget = number(filters.max_price_jpy, 1e12);
    var result = properties.filter(function (row) {
      if (country && row.country_code !== country) return false;
      if (prefecture && row.prefecture.toLocaleLowerCase('en') !== prefecture) return false;
      if (city && row.municipality.toLocaleLowerCase('en') !== city) return false;
      if (locality && row.locality_ja !== locality) return false;
      if (budget !== null && (row.price_jpy === null || row.price_jpy > budget)) return false;
      if (filters.land && row.land_status !== filters.land) return false;
      if (filters.large_plots && (row.land_area_m2 === null || row.land_area_m2 < 500)) return false;
      if (filters.virtual_tours && !row.virtual_tour_at_source) return false;
      var haystack = [row.name, row.country, row.municipality, row.municipality_ja, row.prefecture,
        row.locality, row.locality_ja, row.address_ja, row.summary].concat(row.tags).join(' ').toLocaleLowerCase('en');
      return query.every(function (term) { return haystack.indexOf(term) !== -1; });
    });
    result.sort(function (a, b) {
      var difference;
      if (filters.sort === 'land_desc') {
        difference = (b.land_area_m2 === null ? -1 : b.land_area_m2) - (a.land_area_m2 === null ? -1 : a.land_area_m2);
      } else if (filters.sort === 'town') {
        difference = a.municipality.localeCompare(b.municipality, 'en');
      } else {
        // Unpriced homes go after every known price in either direction.
        if (a.price_jpy === null && b.price_jpy !== null) return 1;
        if (a.price_jpy !== null && b.price_jpy === null) return -1;
        difference = filters.sort === 'price_desc' ? b.price_jpy - a.price_jpy : a.price_jpy - b.price_jpy;
      }
      return difference || a.listing_id.localeCompare(b.listing_id, 'en');
    });
    return result;
  }
  function groupProperties(properties, groupBy) {
    var groups = new Map();
    properties.forEach(function (row) {
      // Full hierarchy prevents identically named localities from merging.
      var parts = [row.country_code, row.prefecture, row.municipality];
      if (groupBy === 'locality') parts.push(row.locality_ja);
      var key = JSON.stringify(parts);
      if (!groups.has(key)) groups.set(key, { key: key,
        label: groupBy === 'locality' ? row.locality : row.municipality,
        subtitle: groupBy === 'locality' ? row.municipality + ' · Fukui · Japan' : 'Fukui · Japan', itemIds: [] });
      groups.get(key).itemIds.push(row.listing_id);
    });
    return Array.from(groups.values());
  }
  function locationOptions(properties, filters) {
    filters = filters || {};
    function unique(rows, value, label) {
      var options = new Map();
      rows.forEach(function (row) { options.set(row[value], label(row)); });
      return Array.from(options, function (entry) { return { value: entry[0], label: entry[1] }; })
        .sort(function (a, b) { return a.label.localeCompare(b.label, 'en'); });
    }
    var inCountry = properties.filter(function (r) { return !filters.country || r.country_code === filters.country; });
    var inPrefecture = inCountry.filter(function (r) { return !filters.prefecture || r.prefecture === filters.prefecture; });
    var inCity = inPrefecture.filter(function (r) { return !filters.city || r.municipality === filters.city; });
    return {
      country: unique(properties, 'country_code', function (r) { return r.country; }),
      prefecture: unique(inCountry, 'prefecture', function (r) { return r.prefecture; }),
      city: unique(inPrefecture, 'municipality', function (r) { return r.municipality; }),
      locality: unique(inCity, 'locality_ja', function (r) {
        return (r.locality === r.locality_ja ? r.locality : r.locality + ' / ' + r.locality_ja) + ' · ' + r.municipality;
      })
    };
  }
  function mount(win, catalogUrl) {
    var doc = win.document;
    var form = doc.getElementById('propertySearch');
    if (!form || form.getAttribute('data-m2j-mounted') === 'true') return;
    form.setAttribute('data-m2j-mounted', 'true');
    var query = doc.getElementById('propertyQuery');
    var geo = { country: doc.getElementById('propertyCountry'), prefecture: doc.getElementById('propertyPrefecture'),
      city: doc.getElementById('propertyCity'), locality: doc.getElementById('propertyLocality') };
    var budget = doc.getElementById('propertyBudget'), land = doc.getElementById('propertyLand');
    var sort = doc.getElementById('propertySort'), groupBy = doc.getElementById('propertyGroup');
    var large = doc.getElementById('largePlots'), tours = doc.getElementById('virtualTours');
    var count = doc.getElementById('resultCount'), panelCount = doc.getElementById('filterResultCount');
    var error = doc.getElementById('listingError'), empty = doc.getElementById('noResults');
    var wrapper = doc.getElementById('propertyFieldWrapper');
    var catalog = null, initialized = false, loading = false, stateBound = false;
    if (win.redDog && win.redDog.registerDiscoveryAdapter) {
      win.redDog.registerDiscoveryAdapter({ element: doc.getElementById('propertySearchPanel'), focusElement: query });
    }
    function filters() {
      return { query: query.value, country: geo.country.value, prefecture: geo.prefecture.value,
        city: geo.city.value, locality: geo.locality.value, max_price_jpy: budget.value === '' ? null : Number(budget.value),
        land: land.value, sort: sort.value, group_by: groupBy.value, large_plots: large.checked, virtual_tours: tours.checked };
    }
    function populateLocations(selected) {
      // Match the search predicate's case rules before resolving child options.
      // Unknown values remain selected and visible as unavailable deep links.
      Object.keys(geo).forEach(function (key) {
        var requested = text(selected[key], 80).toLocaleLowerCase('en');
        var known = locationOptions(catalog.properties, selected)[key].find(function (item) {
          return item.value.toLocaleLowerCase('en') === requested;
        });
        if (known) selected[key] = known.value;
      });
      var options = locationOptions(catalog.properties, selected);
      Object.keys(geo).forEach(function (key) {
        var select = geo[key]; select.replaceChildren();
        var all = doc.createElement('option'); all.value = ''; all.textContent = 'All available'; select.appendChild(all);
        options[key].forEach(function (item) {
          var option = doc.createElement('option'); option.value = item.value; option.textContent = item.label; select.appendChild(option);
        });
        // Stale/unsupported geographic deep links produce no matches, never broader results.
        if (selected[key] && !options[key].some(function (item) { return item.value === selected[key]; })) {
          var unavailable = doc.createElement('option'); unavailable.value = selected[key];
          unavailable.textContent = selected[key] + ' (not in this collection)'; select.appendChild(unavailable);
        }
        select.value = selected[key] || '';
      });
    }
    function restoreUrl() {
      var params = new URL(win.location.href).searchParams;
      query.value = text(params.get('q'), 80);
      populateLocations({ country: text(params.get('country'), 80).toUpperCase(),
        prefecture: text(params.get('prefecture'), 80), city: text(params.get('city') || params.get('area'), 80),
        locality: text(params.get('locality'), 80) });
      var max = params.get('max');
      budget.value = max !== null && max.trim() !== '' && number(Number(max), 1e12) !== null ? max : '';
      land.value = LAND.indexOf(params.get('land')) !== -1 ? params.get('land') : '';
      sort.value = SORTS.indexOf(params.get('sort')) !== -1 ? params.get('sort') : 'price_asc';
      groupBy.value = params.get('group') === 'locality' ? 'locality' : 'city';
      large.checked = params.get('large') === '1'; tours.checked = params.get('tour') === '1';
    }
    function updateUrl() {
      var url = new URL(win.location.href);
      var values = { q: query.value.trim(), country: geo.country.value, prefecture: geo.prefecture.value,
        city: geo.city.value, locality: geo.locality.value, max: budget.value, land: land.value,
        sort: sort.value === 'price_asc' ? '' : sort.value, group: groupBy.value === 'city' ? '' : groupBy.value,
        large: large.checked ? '1' : '', tour: tours.checked ? '1' : '' };
      url.searchParams.delete('area');
      Object.keys(values).forEach(function (key) { if (values[key]) url.searchParams.set(key, values[key]); else url.searchParams.delete(key); });
      win.history.replaceState(null, '', url.pathname + url.search + url.hash);
    }
    function paint(persist) {
      if (!catalog) return;
      var selection = filters(), rows = searchProperties(catalog.properties, selection);
      var groups = groupProperties(rows, selection.group_by);
      wrapper.hidden = rows.length === 0;
      if (!initialized) { win.mallTileField.initialize(rows, { groups: groups }); initialized = true; }
      else win.mallTileField.updateCatalog(rows, { groups: groups });
      empty.hidden = rows.length !== 0;
      var total = rows.length + (rows.length === 1 ? ' home' : ' homes');
      count.textContent = total + ' · ' + groups.length + (groups.length === 1 ? ' area' : ' areas');
      panelCount.textContent = total + ' match';
      doc.getElementById('showHomes').textContent = 'View ' + total;
      doc.getElementById('areaGrouping').textContent = selection.group_by === 'locality' ? 'Suburbs / localities' : 'Cities & towns';
      var active = [selection.query, selection.country, selection.prefecture, selection.city, selection.locality,
        budget.value, selection.land, selection.large_plots, selection.virtual_tours].filter(Boolean).length;
      doc.getElementById('filterButtonLabel').textContent = active ? 'Filters · ' + active : 'Filters';
      if (persist) updateUrl();
    }
    function reset() {
      form.reset(); populateLocations({}); large.checked = false; tours.checked = false; paint(true);
    }
    async function load() {
      if (loading) return;
      loading = true; error.hidden = true; empty.hidden = true;
      count.textContent = 'Loading homes…'; panelCount.textContent = 'Loading homes…'; form.setAttribute('aria-busy', 'true');
      try {
        if (!win.mallTileField || !win.mallPlanes || !win.redDog || !win.redDog.registerDiscoveryAdapter) throw new Error('Mall unavailable');
        var response = await win.fetch(catalogUrl, { cache: 'no-cache', credentials: 'same-origin' });
        if (!response.ok) throw new Error('Catalog unavailable');
        catalog = normalizeCatalog(await response.json()); restoreUrl();
        var dateLabel = new Date(catalog.observed_on + 'T00:00:00Z').toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
        doc.getElementById('checkedDate').textContent = 'Source pages checked ' + dateLabel; paint(false);
        if (!stateBound && win.mallStateRestore) {
          win.mallStateRestore.restore();
          win.mallStateRestore.bindAutoSave();
          stateBound = true;
        }
      } catch (_) {
        catalog = null;
        if (initialized) win.mallTileField.updateCatalog([], { groups: [] });
        wrapper.hidden = true; error.hidden = false;
        count.textContent = 'Collection unavailable'; panelCount.textContent = 'Collection unavailable';
        doc.getElementById('checkedDate').textContent = '';
      } finally { loading = false; form.removeAttribute('aria-busy'); }
    }
    form.addEventListener('submit', function (event) {
      event.preventDefault(); paint(true); if (win.redDog) win.redDog.close();
    });
    form.addEventListener('input', function (event) {
      var keys = Object.keys(geo), parentIndex = keys.findIndex(function (key) { return geo[key] === event.target; });
      if (catalog && parentIndex !== -1) {
        var selected = filters();
        keys.slice(parentIndex + 1).forEach(function (key) { selected[key] = ''; });
        populateLocations(selected);
      }
      paint(true);
    });
    doc.getElementById('resetSearch').addEventListener('click', function () { if (catalog) reset(); });
    doc.getElementById('clearEmptySearch').addEventListener('click', function () {
      if (!catalog) return;
      reset();
      // The reset button is now hidden. Continue browsing on a live house tile.
      var first = doc.querySelector('#mallTileField .mall-tile');
      (first || doc.getElementById('redDogBtn')).focus();
    });
    doc.getElementById('retryListings').addEventListener('click', load);
    win.addEventListener('popstate', function () { if (catalog) { restoreUrl(); paint(false); } });
    load();
  }
  return { normalizeCatalog: normalizeCatalog, searchProperties: searchProperties,
    groupProperties: groupProperties, locationOptions: locationOptions,
    isShellProductRoute: isShellProductRoute, prepareShell: prepareShell, mount: mount };
});
