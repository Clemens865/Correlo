/**
 * app.js — Main application logic for the API Correlation Explorer.
 * Wires up UI, state management, WASM engine, and API layer.
 */

import { fetchCatalog, fetchDataset, proxyFetch, aiParse, aiDiscover, aiInsight } from './api.js?v=3';
import { drawOverlay, drawScatter, drawDualAxis, drawTimeSeries, renderMatrixHTML } from './charts.js?v=3';

// --- WASM engine -----------------------------------------------------------
let wasm = null;
async function initWasm() {
  const mod = await import('../pkg/correlation_engine.js');
  await mod.default();
  wasm = mod;
  log('WASM correlation engine loaded', 'success');
}

// --- State ------------------------------------------------------------------
const state = {
  catalog: [],
  locations: [],
  countries: [],
  periods: [],
  dataA: null,
  dataB: null,
  selectedA: '',
  selectedB: '',
  customDatasets: [],
  matrixSelected: new Set(),
  matrixData: {},
};

// --- DOM refs ---------------------------------------------------------------
const $ = id => document.getElementById(id);
const selA = $('selA');
const selB = $('selB');
const selLocation = $('selLocation');
const selCountry = $('selCountry');
const selDays = $('selDays');
const fetchBtn = $('fetchBtn');
const clearBtn = $('clearBtn');
const aiSearchInput = $('aiSearch');
const aiSearchBtn = $('aiSearchBtn');

// --- Initialize -------------------------------------------------------------
async function init() {
  log('Loading catalog...');
  try {
    const { apis, locations, countries, periods } = await fetchCatalog();
    state.catalog = apis;
    state.locations = locations;
    state.countries = countries || [];
    state.periods = periods || [];
    populateDropdowns();
    populateMatrixControls();
    const cats = new Set(apis.map(a => a.category));
    log(`Loaded ${apis.length} APIs across ${cats.size} categories`, 'success');
  } catch (e) {
    log(`Failed to load catalog: ${e.message}`, 'error');
  }

  await initWasm();
  setupEventListeners();
  log('Ready. Select two datasets or ask AI a question.');
}

// --- Dropdowns --------------------------------------------------------------
function populateDropdowns() {
  const allApis = [...state.catalog, ...state.customDatasets];
  const categories = [...new Set(allApis.map(a => a.category))];

  for (const sel of [selA, selB]) {
    const currentVal = sel.value;
    sel.innerHTML = '<option value="">Choose dataset...</option>';
    for (const cat of categories) {
      const group = document.createElement('optgroup');
      group.label = `${cat} (${allApis.filter(a => a.category === cat).length})`;
      for (const api of allApis.filter(a => a.category === cat)) {
        const opt = document.createElement('option');
        opt.value = api.id;
        opt.textContent = `${api.name} ${api.unit ? '(' + api.unit + ')' : ''}`;
        group.appendChild(opt);
      }
      sel.appendChild(group);
    }
    sel.value = currentVal;
  }

  // Locations (include country code for auto-derivation)
  selLocation.innerHTML = '';
  for (const loc of state.locations) {
    const opt = document.createElement('option');
    opt.value = JSON.stringify({ lat: loc.lat, lon: loc.lon, country: loc.country || 'WLD' });
    opt.textContent = loc.name;
    selLocation.appendChild(opt);
  }

  // Countries
  if (selCountry) {
    selCountry.innerHTML = '';
    for (const c of state.countries) {
      const opt = document.createElement('option');
      opt.value = c.code;
      opt.textContent = c.name;
      selCountry.appendChild(opt);
    }
  }

  // Periods (from server)
  selDays.innerHTML = '';
  const periods = state.periods.length ? state.periods : [
    { value: '30d', label: '30 days', days: 30 },
  ];
  for (const p of periods) {
    const opt = document.createElement('option');
    opt.value = p.days;
    opt.textContent = p.label;
    if (p.value === '1y') opt.selected = true;
    selDays.appendChild(opt);
  }
}

function populateMatrixControls() {
  const el = $('matrixControls');
  const allApis = [...state.catalog, ...state.customDatasets];
  el.innerHTML = allApis.map(a =>
    `<div class="matrix-chip" data-id="${a.id}" title="${a.desc}">${a.name}</div>`
  ).join('');

  el.querySelectorAll('.matrix-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const id = chip.dataset.id;
      if (state.matrixSelected.has(id)) {
        state.matrixSelected.delete(id);
        chip.classList.remove('selected');
      } else {
        state.matrixSelected.add(id);
        chip.classList.add('selected');
      }
      $('matrixBtn').disabled = state.matrixSelected.size < 2;
    });
  });
}

// --- Location type awareness ------------------------------------------------
function updateLocationVisibility() {
  const allApis = [...state.catalog, ...state.customDatasets];
  const apiA = allApis.find(a => a.id === state.selectedA);
  const apiB = allApis.find(a => a.id === state.selectedB);

  // Determine what location controls to show based on selected datasets
  const types = new Set();
  if (apiA) types.add(apiA.location_type);
  if (apiB) types.add(apiB.location_type);

  const locationGroup = $('locationGroup');
  const countryGroup = $('countryGroup');

  if (types.has('latlon')) {
    locationGroup.style.display = '';
  } else {
    locationGroup.style.display = 'none';
  }

  if (types.has('country')) {
    countryGroup.style.display = '';
  } else {
    countryGroup.style.display = 'none';
  }
}

// --- Event listeners --------------------------------------------------------
function setupEventListeners() {
  selA.addEventListener('change', () => {
    state.selectedA = selA.value;
    updateSlots();
    updateFetchBtn();
    updateLocationVisibility();
    filterDropdownCompatibility(selA.value, selB);
  });
  selB.addEventListener('change', () => {
    state.selectedB = selB.value;
    updateSlots();
    updateFetchBtn();
    updateLocationVisibility();
    filterDropdownCompatibility(selB.value, selA);
  });

  fetchBtn.addEventListener('click', () => {
    if (state.selectedA && state.selectedB && state.selectedA !== state.selectedB) {
      doFetchAndCompare();
    } else if (state.selectedA) {
      doFetchSingle();
    }
  });
  clearBtn.addEventListener('click', doClear);

  aiSearchBtn.addEventListener('click', doAiSearch);
  aiSearchInput.addEventListener('keydown', e => { if (e.key === 'Enter') doAiSearch(); });

  $('matrixBtn').addEventListener('click', doBuildMatrix);
  $('customFetchBtn').addEventListener('click', doCustomFetch);
  $('customAddBtn')?.addEventListener('click', doCustomAdd);
  $('exportCsv').addEventListener('click', doExportCsv);

  // Tabs
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      $(`tab-${tab.dataset.tab}`).classList.add('active');
    });
  });
}

function updateFetchBtn() {
  const hasA = !!state.selectedA;
  const hasB = !!state.selectedB;
  const hasBoth = hasA && hasB && state.selectedA !== state.selectedB;

  fetchBtn.disabled = !hasA;
  fetchBtn.textContent = hasBoth ? 'Fetch & Compare' : hasA ? 'Explore Dataset' : 'Fetch & Compare';
}

// Estimate the year range a dataset covers based on its max_history_days and granularity
function estimateRange(api) {
  if (!api) return null;
  const now = new Date().getFullYear();
  const yearsBack = Math.ceil(api.max_history_days / 365);
  // Yearly/monthly APIs often have data lag (WB: 2-3 years, WHO: 3-5 years)
  const lag = api.granularity === 'yearly' ? 2 : api.granularity === 'monthly' ? 1 : 0;
  return { start: now - yearsBack, end: now - lag, gran: api.granularity };
}

function checkCompatibility(apiA, apiB) {
  if (!apiA || !apiB) return null;
  const rA = estimateRange(apiA);
  const rB = estimateRange(apiB);
  if (!rA || !rB) return null;

  const overlapStart = Math.max(rA.start, rB.start);
  const overlapEnd = Math.min(rA.end, rB.end);
  const overlapYears = overlapEnd - overlapStart;

  if (overlapYears < 1) {
    return { ok: false, msg: `No time overlap: ${apiA.name} covers ~${rA.start}-${rA.end}, ${apiB.name} covers ~${rB.start}-${rB.end}` };
  }
  if (overlapYears < 3 && rA.gran === 'yearly' || rB.gran === 'yearly') {
    return { ok: true, msg: `Limited overlap (~${overlapYears} years). Cross-granularity: ${rA.gran} → ${rB.gran}`, warn: true };
  }
  if (rA.gran !== rB.gran) {
    const target = { daily: 0, monthly: 1, yearly: 2 }[rA.gran] > { daily: 0, monthly: 1, yearly: 2 }[rB.gran] ? rA.gran : rB.gran;
    return { ok: true, msg: `Will aggregate ${rA.gran === target ? rB.gran : rA.gran} → ${target} (${overlapYears}yr overlap)` };
  }
  return { ok: true };
}

// Grey out incompatible datasets in the opposite dropdown
function filterDropdownCompatibility(selectedApiId, targetSel) {
  if (!selectedApiId) {
    // Nothing selected — enable all options
    for (const opt of targetSel.querySelectorAll('option')) {
      opt.disabled = false;
      opt.style.color = '';
    }
    return;
  }

  const allApis = [...state.catalog, ...state.customDatasets];
  const selectedApi = allApis.find(a => a.id === selectedApiId);
  if (!selectedApi) return;

  for (const opt of targetSel.querySelectorAll('option')) {
    if (!opt.value) continue; // skip "Choose dataset..." placeholder
    if (opt.value === selectedApiId) {
      opt.disabled = true;
      opt.style.color = '#555';
      continue;
    }
    const otherApi = allApis.find(a => a.id === opt.value);
    if (!otherApi) continue;
    const compat = checkCompatibility(selectedApi, otherApi);
    if (compat && !compat.ok) {
      opt.disabled = true;
      opt.style.color = '#555';
    } else {
      opt.disabled = false;
      opt.style.color = '';
    }
  }
}

function updateSlots() {
  const allApis = [...state.catalog, ...state.customDatasets];
  const apiA = allApis.find(a => a.id === state.selectedA);
  const apiB = allApis.find(a => a.id === state.selectedB);
  const slotA = $('slotA');
  const slotB = $('slotB');

  if (apiA) {
    slotA.classList.add('filled');
    const locTag = apiA.location_type === 'latlon' ? 'city' : apiA.location_type === 'country' ? 'country' : 'global';
    slotA.innerHTML = `<div class="slot-label">Dataset A</div><div class="slot-name">${apiA.name}</div><div class="slot-meta">${apiA.category} / ${apiA.unit || ''} / ${locTag} / ${apiA.granularity}</div>`;
  } else {
    slotA.classList.remove('filled');
    slotA.innerHTML = '<div class="slot-label">Dataset A</div><div class="slot-name" style="color:var(--dim)">Select from dropdown</div>';
  }

  if (apiB) {
    slotB.classList.add('filled');
    const locTag = apiB.location_type === 'latlon' ? 'city' : apiB.location_type === 'country' ? 'country' : 'global';
    slotB.innerHTML = `<div class="slot-label">Dataset B</div><div class="slot-name">${apiB.name}</div><div class="slot-meta">${apiB.category} / ${apiB.unit || ''} / ${locTag} / ${apiB.granularity}</div>`;
  } else {
    slotB.classList.remove('filled');
    slotB.innerHTML = '<div class="slot-label">Dataset B</div><div class="slot-name" style="color:var(--dim)">Select from dropdown</div>';
  }

  // Show compatibility info between selected datasets
  const compat = checkCompatibility(apiA, apiB);
  const compatEl = $('compatInfo');
  if (compatEl && compat) {
    if (!compat.ok) {
      compatEl.innerHTML = `<span style="color:var(--red)">⚠ ${compat.msg}</span>`;
      compatEl.style.display = 'block';
    } else if (compat.msg) {
      compatEl.innerHTML = `<span style="color:${compat.warn ? 'var(--yellow)' : 'var(--dim)'}">ℹ ${compat.msg}</span>`;
      compatEl.style.display = 'block';
    } else {
      compatEl.style.display = 'none';
    }
  } else if (compatEl) {
    compatEl.style.display = 'none';
  }
}

// --- Smart fetch parameters -------------------------------------------------
// Minimum days to request per granularity to ensure meaningful data
const MIN_DAYS_BY_GRAN = { yearly: 7300, monthly: 1825, weekly: 730, daily: 365, '10-day': 365 };

function getSmartFetchParams(apiId, otherApiId = null) {
  const allApis = [...state.catalog, ...state.customDatasets];
  const api = allApis.find(a => a.id === apiId);
  const otherApi = otherApiId ? allApis.find(a => a.id === otherApiId) : null;
  const locData = JSON.parse(selLocation.value || '{"lat":48.21,"lon":16.37,"country":"AT"}');
  const userDays = parseInt(selDays.value);
  const userCountry = selCountry ? selCountry.value : 'WLD';

  if (!api) return { lat: locData.lat, lon: locData.lon, days: userDays, country: userCountry };

  // --- Days: ensure enough history for this granularity ---
  const minDays = MIN_DAYS_BY_GRAN[api.granularity] || 365;
  let days = Math.max(userDays, minDays);

  // If comparing with another API, ensure overlap is possible
  // When one API is yearly (data lag 2-3 years), request max history from the other
  // so their time ranges overlap after aggregation
  if (otherApi) {
    const otherMin = MIN_DAYS_BY_GRAN[otherApi.granularity] || 365;
    days = Math.max(days, otherMin);

    // If the OTHER api is yearly/monthly (has data lag), we need more history
    // from THIS api to overlap with the lagged data
    if (otherApi.granularity === 'yearly') {
      days = Math.max(days, api.max_history_days || 7300);
    } else if (otherApi.granularity === 'monthly') {
      days = Math.max(days, Math.min(api.max_history_days || 3650, 3650));
    }
  }

  // Cap to API's max
  if (api.max_history_days) days = Math.min(days, api.max_history_days);

  // --- Country: auto-derive from location for country-type APIs ---
  let country = userCountry;
  if (api.location_type === 'country') {
    // Use the country from the selected location (city), not the country dropdown
    // This way, selecting "Vienna" automatically uses "AT" for country APIs
    const locCountry = locData.country || userCountry;
    country = locCountry !== 'WLD' ? locCountry : userCountry;
  }

  return { lat: locData.lat, lon: locData.lon, days, country };
}

// --- Fetch & Compare --------------------------------------------------------
async function doFetchAndCompare() {
  fetchBtn.disabled = true;
  fetchBtn.innerHTML = '<span class="loader"></span> Fetching...';
  $('explorePanel').style.display = 'none';

  try {
    const paramsA = getSmartFetchParams(state.selectedA, state.selectedB);
    const paramsB = getSmartFetchParams(state.selectedB, state.selectedA);

    log(`Fetching dataset A: ${state.selectedA} (${paramsA.days}d, ${paramsA.country})...`);
    state.dataA = await fetchDataset(state.selectedA, paramsA);
    log(`Got ${state.dataA.count} points from ${state.dataA.name}`, 'success');

    log(`Fetching dataset B: ${state.selectedB} (${paramsB.days}d, ${paramsB.country})...`);
    state.dataB = await fetchDataset(state.selectedB, paramsB);
    log(`Got ${state.dataB.count} points from ${state.dataB.name}`, 'success');

    updateSlots();
    alignAndCorrelate();

  } catch (e) {
    log(`Error: ${e.message}`, 'error');
  }

  fetchBtn.disabled = false;
  updateFetchBtn();
}

// --- Fetch & Explore (single dataset) ---------------------------------------
async function doFetchSingle() {
  fetchBtn.disabled = true;
  fetchBtn.innerHTML = '<span class="loader"></span> Fetching...';

  // Hide compare panels
  $('resultsPanel').style.display = 'none';
  $('chartsPanel').style.display = 'none';
  $('statsPanel').style.display = 'none';
  $('tablePanel').style.display = 'none';
  $('explorePanel').style.display = 'none';

  try {
    const params = getSmartFetchParams(state.selectedA);
    log(`Fetching ${state.selectedA} (${params.days}d, ${params.country})...`);
    state.dataA = await fetchDataset(state.selectedA, params);
    const d = state.dataA;
    log(`Got ${d.count} points from ${d.name}`, 'success');

    if (!d.values || d.values.length === 0) {
      log('Dataset returned no data', 'error');
      return;
    }

    // Compute stats via WASM
    const statsJson = wasm.compute_stats(JSON.stringify(d.values));
    const stats = JSON.parse(statsJson);

    // Moving average
    const window = d.values.length > 60 ? 7 : d.values.length > 14 ? 3 : 0;
    let movAvg = null;
    if (window > 0) {
      const maJson = wasm.moving_average(JSON.stringify(d.values), window);
      movAvg = JSON.parse(maJson);
    }

    // Show explore panel
    showExploreResults(d, stats, movAvg);

  } catch (e) {
    log(`Error: ${e.message}`, 'error');
  } finally {
    fetchBtn.disabled = false;
    updateFetchBtn();
  }
}

function showExploreResults(d, stats, movAvg) {
  const panel = $('explorePanel');
  panel.style.display = 'block';

  // Stats cards
  $('exploreStats').innerHTML = `
    <div class="stat-card">
      <div class="label">Mean</div>
      <div class="value">${stats.mean.toFixed(2)}</div>
      <div class="sub">${d.unit}</div>
    </div>
    <div class="stat-card">
      <div class="label">Median</div>
      <div class="value">${stats.median.toFixed(2)}</div>
      <div class="sub">${d.unit}</div>
    </div>
    <div class="stat-card">
      <div class="label">Std Dev</div>
      <div class="value">${stats.std_dev.toFixed(2)}</div>
      <div class="sub">Dispersion</div>
    </div>
    <div class="stat-card">
      <div class="label">Range</div>
      <div class="value">${stats.min.toFixed(2)} — ${stats.max.toFixed(2)}</div>
      <div class="sub">${d.unit}</div>
    </div>
    <div class="stat-card">
      <div class="label">IQR</div>
      <div class="value">${stats.q1.toFixed(2)} — ${stats.q3.toFixed(2)}</div>
      <div class="sub">25th — 75th percentile</div>
    </div>
    <div class="stat-card">
      <div class="label">Data Points</div>
      <div class="value">${d.count}</div>
      <div class="sub">${d.labels[0]} to ${d.labels[d.labels.length - 1]}</div>
    </div>
  `;

  // Chart
  requestAnimationFrame(() => {
    drawTimeSeries('exploreChart', d.labels, d.values, d.name, d.unit);
  });

  // Data table
  $('exploreTableWrap').innerHTML = buildSingleTable(d);

  // Store for CSV export
  state._tableLabels = d.labels;
  state._tableA = d.values;
  state._tableB = null;
}

function buildSingleTable(d) {
  let html = `<table class="data-table"><thead><tr>
    <th>Date</th><th>${d.name} (${d.unit})</th>
  </tr></thead><tbody>`;
  for (let i = 0; i < d.labels.length; i++) {
    const v = d.values[i];
    html += `<tr><td>${d.labels[i]}</td><td>${v != null ? v.toFixed(2) : '—'}</td></tr>`;
  }
  html += '</tbody></table>';
  return html;
}

function alignAndCorrelate() {
  const a = state.dataA;
  const b = state.dataB;

  // Detect granularity from labels: YYYY = yearly, YYYY-MM = monthly, YYYY-MM-DD = daily
  function detectGranularity(labels) {
    if (!labels.length) return 'unknown';
    const sample = labels[0];
    if (/^\d{4}$/.test(sample)) return 'yearly';
    if (/^\d{4}-\d{2}$/.test(sample)) return 'monthly';
    if (/^\d{4}-\d{2}-\d{2}$/.test(sample)) return 'daily';
    return 'unknown';
  }

  // Aggregate values by a key function (e.g., daily→monthly: "2025-03-15" → "2025-03")
  function aggregateBy(labels, values, keyFn) {
    const buckets = new Map();
    for (let i = 0; i < labels.length; i++) {
      if (values[i] == null) continue;
      const key = keyFn(labels[i]);
      if (!buckets.has(key)) buckets.set(key, []);
      buckets.get(key).push(values[i]);
    }
    const aggLabels = [], aggValues = [];
    for (const [key, vals] of [...buckets.entries()].sort((a, b) => a[0].localeCompare(b[0]))) {
      aggLabels.push(key);
      aggValues.push(vals.reduce((s, v) => s + v, 0) / vals.length); // mean
    }
    return { labels: aggLabels, values: aggValues };
  }

  const granA = detectGranularity(a.labels);
  const granB = detectGranularity(b.labels);
  const granOrder = { daily: 0, monthly: 1, yearly: 2, unknown: -1 };

  let labelsA = a.labels, valsA = a.values;
  let labelsB = b.labels, valsB = b.values;

  // Cross-granularity alignment: aggregate finer to coarser
  if (granA !== granB && granOrder[granA] >= 0 && granOrder[granB] >= 0) {
    const target = granOrder[granA] > granOrder[granB] ? granA : granB;
    log(`Cross-granularity: ${granA} vs ${granB} → aggregating to ${target}`);

    const toMonthly = label => label.slice(0, 7);  // "2025-03-15" → "2025-03"
    const toYearly = label => label.slice(0, 4);    // "2025-03-15" → "2025" or "2025-03" → "2025"

    if (target === 'yearly') {
      if (granA !== 'yearly') ({ labels: labelsA, values: valsA } = aggregateBy(labelsA, valsA, toYearly));
      if (granB !== 'yearly') ({ labels: labelsB, values: valsB } = aggregateBy(labelsB, valsB, toYearly));
    } else if (target === 'monthly') {
      if (granA === 'daily') ({ labels: labelsA, values: valsA } = aggregateBy(labelsA, valsA, toMonthly));
      if (granB === 'daily') ({ labels: labelsB, values: valsB } = aggregateBy(labelsB, valsB, toMonthly));
    }
  }

  // Align by matching labels
  const bSet = new Set(labelsB);
  const commonLabels = labelsA.filter(l => bSet.has(l));
  if (commonLabels.length < 3) {
    // Provide helpful diagnostic
    const rangeA = labelsA.length ? `${labelsA[0]} to ${labelsA[labelsA.length-1]}` : 'none';
    const rangeB = labelsB.length ? `${labelsB[0]} to ${labelsB[labelsB.length-1]}` : 'none';
    log(`Only ${commonLabels.length} common points — no temporal overlap`, 'error');
    log(`  ${a.name}: ${labelsA.length} pts (${rangeA})`, 'error');
    log(`  ${b.name}: ${labelsB.length} pts (${rangeB})`, 'error');
    if (labelsA.length && labelsB.length && labelsA[labelsA.length-1] < labelsB[0]) {
      log(`  Hint: Try selecting a longer period to get overlapping data`, 'error');
    }
    return;
  }

  // Build index maps for O(n) alignment instead of O(n²)
  const aIndex = new Map(labelsA.map((l, i) => [l, i]));
  const bIndex = new Map(labelsB.map((l, i) => [l, i]));
  const alignedA = commonLabels.map(l => valsA[aIndex.get(l)]);
  const alignedB = commonLabels.map(l => valsB[bIndex.get(l)]);

  log(`Aligned ${commonLabels.length} common data points`);
  log('Computing correlation via WASM...', 'ai');

  // WASM calls
  const corrJson = wasm.compute_correlation(JSON.stringify(alignedA), JSON.stringify(alignedB));
  const corr = JSON.parse(corrJson);

  const statsAJson = wasm.compute_stats(JSON.stringify(alignedA));
  const statsBJson = wasm.compute_stats(JSON.stringify(alignedB));
  const statsA = JSON.parse(statsAJson);
  const statsB = JSON.parse(statsBJson);

  const normAJson = wasm.normalize_series(JSON.stringify(alignedA));
  const normBJson = wasm.normalize_series(JSON.stringify(alignedB));
  const normA = JSON.parse(normAJson);
  const normB = JSON.parse(normBJson);

  const regLineJson = wasm.regression_line(JSON.stringify(alignedA), JSON.stringify(alignedB));
  const regLine = JSON.parse(regLineJson);

  log(`Pearson: ${corr.pearson.toFixed(4)} | Spearman: ${corr.spearman.toFixed(4)} | R²: ${corr.r_squared.toFixed(4)} | ${corr.strength}`, 'success');

  showResults(corr, statsA, statsB);
  drawCharts(commonLabels, alignedA, alignedB, normA, normB, regLine);
  showDataTable(commonLabels, alignedA, alignedB);

  // AI insight (async, non-blocking)
  fetchAiInsight(corr);
}

// --- Display results --------------------------------------------------------
function showResults(corr, statsA, statsB) {
  const a = state.dataA;
  const b = state.dataB;

  $('resultsPanel').style.display = 'block';

  const strengthClass = corr.strength.replace(/\s+/g, '-');
  $('resultGrid').innerHTML = `
    <div class="stat-card">
      <div class="label">Pearson</div>
      <div class="value">${corr.pearson.toFixed(4)}</div>
      <div class="sub">Linear correlation</div>
    </div>
    <div class="stat-card">
      <div class="label">Spearman</div>
      <div class="value">${corr.spearman.toFixed(4)}</div>
      <div class="sub">Rank correlation</div>
    </div>
    <div class="stat-card">
      <div class="label">R Squared</div>
      <div class="value">${corr.r_squared.toFixed(4)}</div>
      <div class="sub">${(corr.r_squared * 100).toFixed(1)}% variance explained</div>
    </div>
    <div class="stat-card">
      <div class="label">Strength</div>
      <div class="value"><span class="badge ${strengthClass}">${corr.strength}</span></div>
      <div class="sub">${corr.direction} direction</div>
    </div>
    <div class="stat-card">
      <div class="label">Regression</div>
      <div class="value" style="font-size:14px">y = ${corr.slope.toFixed(3)}x + ${corr.intercept.toFixed(1)}</div>
      <div class="sub">Linear fit</div>
    </div>
    <div class="stat-card">
      <div class="label">Data Points</div>
      <div class="value">${corr.n}</div>
      <div class="sub">Aligned observations</div>
    </div>
  `;

  $('statsPanel').style.display = 'block';
  $('statsGrid').innerHTML = `
    <div class="stat-card"><div class="label">${a.name} Mean</div><div class="value">${statsA.mean.toFixed(2)}</div><div class="sub">${a.unit}</div></div>
    <div class="stat-card"><div class="label">${a.name} Std Dev</div><div class="value">${statsA.std_dev.toFixed(2)}</div></div>
    <div class="stat-card"><div class="label">${a.name} Range</div><div class="value">${statsA.min.toFixed(1)} — ${statsA.max.toFixed(1)}</div></div>
    <div class="stat-card"><div class="label">${b.name} Mean</div><div class="value">${statsB.mean.toFixed(2)}</div><div class="sub">${b.unit}</div></div>
    <div class="stat-card"><div class="label">${b.name} Std Dev</div><div class="value">${statsB.std_dev.toFixed(2)}</div></div>
    <div class="stat-card"><div class="label">${b.name} Range</div><div class="value">${statsB.min.toFixed(1)} — ${statsB.max.toFixed(1)}</div></div>
  `;
}

function drawCharts(labels, alignedA, alignedB, normA, normB, regLine) {
  $('chartsPanel').style.display = 'block';
  const a = state.dataA;
  const b = state.dataB;

  requestAnimationFrame(() => {
    drawOverlay('overlayChart', labels, normA, normB, a.name, b.name);
    drawScatter('scatterChart', alignedA, alignedB, regLine, a.name, b.name);
    drawDualAxis('dualAxisChart', labels, alignedA, alignedB, a.name, b.name, a.unit, b.unit);
  });
}

function showDataTable(labels, valsA, valsB) {
  $('tablePanel').style.display = 'block';
  $('tableCount').textContent = `${labels.length} rows`;

  const a = state.dataA;
  const b = state.dataB;

  let html = `<table class="data-table"><thead><tr>
    <th>Date</th><th>${a.name} (${a.unit})</th><th>${b.name} (${b.unit})</th>
  </tr></thead><tbody>`;

  for (let i = 0; i < labels.length; i++) {
    html += `<tr><td>${labels[i]}</td><td>${valsA[i].toFixed(2)}</td><td>${valsB[i].toFixed(2)}</td></tr>`;
  }
  html += '</tbody></table>';
  $('tableWrap').innerHTML = html;

  state._tableLabels = labels;
  state._tableA = valsA;
  state._tableB = valsB;
}

// Lightweight markdown → HTML converter
function renderMarkdown(md) {
  let html = md
    // Escape HTML entities
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    // Headers
    .replace(/^### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^## (.+)$/gm, '<h3>$1</h3>')
    .replace(/^# (.+)$/gm, '<h2>$1</h2>')
    // Bold and italic
    .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // Inline code
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // Horizontal rule
    .replace(/^---$/gm, '<hr>');

  // Process blocks: lists and paragraphs
  const lines = html.split('\n');
  const out = [];
  let inUl = false, inOl = false;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const ulMatch = line.match(/^[\s]*[-*]\s+(.+)/);
    const olMatch = line.match(/^[\s]*\d+\.\s+(.+)/);

    if (ulMatch) {
      if (!inUl) { out.push('<ul>'); inUl = true; }
      out.push(`<li>${ulMatch[1]}</li>`);
    } else if (olMatch) {
      if (!inOl) { out.push('<ol>'); inOl = true; }
      out.push(`<li>${olMatch[1]}</li>`);
    } else {
      if (inUl) { out.push('</ul>'); inUl = false; }
      if (inOl) { out.push('</ol>'); inOl = false; }
      // Skip empty lines between blocks, wrap non-tag text in <p>
      if (line.trim() === '') {
        out.push('');
      } else if (/^<(h[2-4]|hr|ul|ol|li)/.test(line.trim())) {
        out.push(line);
      } else {
        out.push(`<p>${line}</p>`);
      }
    }
  }
  if (inUl) out.push('</ul>');
  if (inOl) out.push('</ol>');

  return out.join('\n');
}

async function fetchAiInsight(corr) {
  const a = state.dataA;
  const b = state.dataB;
  const insightEl = $('aiInsight');
  insightEl.innerHTML = '<div class="ai-insight"><div class="ai-tag">AI Analysis</div><div class="ai-body"><span class="loader"></span> Generating insight...</div></div>';

  try {
    const days = parseInt(selDays.value);
    const periodLabel = state.periods.find(p => p.days === days)?.label || `${days} days`;
    const result = await aiInsight({
      nameA: a.name, unitA: a.unit,
      nameB: b.name, unitB: b.unit,
      pearson: corr.pearson, spearman: corr.spearman,
      r_squared: corr.r_squared, n: corr.n,
      period: periodLabel,
    });
    insightEl.innerHTML = `<div class="ai-insight"><div class="ai-tag">AI Analysis (Sonnet)</div><div class="ai-body">${renderMarkdown(result.insight)}</div></div>`;
    log('AI insight generated', 'ai');
  } catch (e) {
    insightEl.innerHTML = `<div class="ai-insight"><div class="ai-tag">AI Analysis</div><div class="ai-body" style="color:var(--red)">Failed: ${e.message}</div></div>`;
  }
}

// --- AI Search --------------------------------------------------------------
async function doAiSearch() {
  const query = aiSearchInput.value.trim();
  if (!query) return;

  aiSearchBtn.disabled = true;
  aiSearchBtn.innerHTML = '<span class="loader"></span>';
  log(`AI search: "${query}"`, 'ai');

  try {
    const result = await aiDiscover(query);

    let html = '';
    if (result.interpretation) {
      html += `<p style="font-size:12px;color:var(--dim);margin:12px 0 8px">${result.interpretation}</p>`;
    }
    if (result.suggestions?.length) {
      html += '<div class="ai-suggestions">';
      for (const s of result.suggestions) {
        html += `<div class="suggestion-card" data-catalog-id="${s.catalog_id || ''}" data-url="${s.custom_url || ''}">
          <div class="name">${s.name}</div>
          <div class="why">${s.why}</div>
        </div>`;
      }
      html += '</div>';
    }
    if (result.comparison_pairs?.length) {
      html += '<div style="margin-top:12px">';
      for (const pair of result.comparison_pairs) {
        html += `<div style="font-size:12px;color:var(--dim);margin:4px 0"><strong>${pair.a}</strong> vs <strong>${pair.b}</strong> — ${pair.hypothesis}</div>`;
      }
      html += '</div>';
    }
    if (result.also_try) {
      html += `<p style="font-size:12px;color:var(--purple);margin-top:8px">${result.also_try}</p>`;
    }

    $('aiSuggestions').innerHTML = html;

    // Wire up suggestion cards to auto-select dropdowns
    $('aiSuggestions').querySelectorAll('.suggestion-card').forEach(card => {
      card.addEventListener('click', () => {
        const catId = card.dataset.catalogId;
        if (catId && state.catalog.find(a => a.id === catId)) {
          if (!state.selectedA) {
            selA.value = catId;
            state.selectedA = catId;
          } else if (!state.selectedB || state.selectedB === state.selectedA) {
            selB.value = catId;
            state.selectedB = catId;
          }
          updateSlots();
          updateFetchBtn();
          updateLocationVisibility();
        }
      });
    });

    log(`AI suggested ${result.suggestions?.length || 0} datasets`, 'success');
  } catch (e) {
    log(`AI search failed: ${e.message}`, 'error');
  }

  aiSearchBtn.disabled = false;
  aiSearchBtn.textContent = 'Ask AI';
}

// --- Matrix -----------------------------------------------------------------
async function doBuildMatrix() {
  const ids = [...state.matrixSelected];
  if (ids.length < 2) return;

  const matrixBtn = $('matrixBtn');
  matrixBtn.disabled = true;
  matrixBtn.innerHTML = '<span class="loader"></span> Fetching...';

  try {
    const datasets = [];
    const names = [];
    const allApis = [...state.catalog, ...state.customDatasets];

    // Find the coarsest granularity among selected to optimize fetch params
    const granOrderLookup = { daily: 0, monthly: 1, yearly: 2 };
    let coarsestId = ids[0];
    for (const id of ids) {
      const api = allApis.find(a => a.id === id);
      const cur = allApis.find(a => a.id === coarsestId);
      if (api && cur && (granOrderLookup[api.granularity] || 0) > (granOrderLookup[cur.granularity] || 0)) {
        coarsestId = id;
      }
    }

    for (const id of ids) {
      // Pass the coarsest-granularity dataset as "other" so time ranges expand
      const params = getSmartFetchParams(id, coarsestId !== id ? coarsestId : null);
      log(`Matrix: fetching ${id} (${params.days}d)...`);
      const data = await fetchDataset(id, params);
      state.matrixData[id] = data;
      datasets.push(data);
      names.push(data.name);
    }

    // Detect granularities and find coarsest
    function detectGran(labels) {
      if (!labels.length) return 'unknown';
      const s = labels[0];
      if (/^\d{4}$/.test(s)) return 'yearly';
      if (/^\d{4}-\d{2}$/.test(s)) return 'monthly';
      if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return 'daily';
      return 'unknown';
    }
    function aggBy(labels, values, keyFn) {
      const buckets = new Map();
      for (let i = 0; i < labels.length; i++) {
        if (values[i] == null) continue;
        const key = keyFn(labels[i]);
        if (!buckets.has(key)) buckets.set(key, []);
        buckets.get(key).push(values[i]);
      }
      const aL = [], aV = [];
      for (const [k, vs] of [...buckets.entries()].sort((a, b) => a[0].localeCompare(b[0]))) {
        aL.push(k);
        aV.push(vs.reduce((s, v) => s + v, 0) / vs.length);
      }
      return { labels: aL, values: aV };
    }

    const granOrder = { daily: 0, monthly: 1, yearly: 2, unknown: -1 };
    const grans = datasets.map(d => detectGran(d.labels));
    const coarsest = grans.reduce((a, b) => granOrder[a] >= granOrder[b] ? a : b);

    // Aggregate all datasets to coarsest granularity
    const toMonthly = l => l.slice(0, 7);
    const toYearly = l => l.slice(0, 4);
    const normalized = datasets.map((d, i) => {
      if (grans[i] === coarsest) return { labels: d.labels, values: d.values };
      if (coarsest === 'yearly') return aggBy(d.labels, d.values, toYearly);
      if (coarsest === 'monthly' && grans[i] === 'daily') return aggBy(d.labels, d.values, toMonthly);
      return { labels: d.labels, values: d.values };
    });

    if (grans.some(g => g !== coarsest)) {
      log(`Matrix: aggregating to ${coarsest} granularity for alignment`);
    }

    // Align all by common labels
    let commonLabels = normalized[0].labels;
    for (let i = 1; i < normalized.length; i++) {
      const set = new Set(normalized[i].labels);
      commonLabels = commonLabels.filter(l => set.has(l));
    }

    if (commonLabels.length < 3) {
      log(`Only ${commonLabels.length} common dates across all datasets — need at least 3. Try datasets with more overlapping time ranges.`, 'error');
      matrixBtn.disabled = false;
      matrixBtn.textContent = 'Build Matrix';
      return;
    }

    const aligned = normalized.map(d => {
      const idx = new Map(d.labels.map((l, i) => [l, i]));
      return commonLabels.map(l => d.values[idx.get(l)]);
    });

    log(`Matrix: ${ids.length} datasets, ${commonLabels.length} common points. Computing...`, 'ai');

    const input = JSON.stringify({ ids: names, datasets: aligned });
    const resultJson = wasm.compute_matrix(input);
    const result = JSON.parse(resultJson);

    $('matrixPanel').style.display = 'block';
    $('matrixGrid').innerHTML = renderMatrixHTML(result);

    log(`Correlation matrix computed (${ids.length}x${ids.length})`, 'success');

  } catch (e) {
    log(`Matrix error: ${e.message}`, 'error');
  } finally {
    matrixBtn.disabled = false;
    matrixBtn.textContent = 'Build Matrix';
  }
}

// --- Custom API -------------------------------------------------------------
async function doCustomFetch() {
  const url = $('customUrl').value.trim();
  if (!url) return;

  const btn = $('customFetchBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="loader"></span>';

  try {
    log(`Custom fetch: ${url}`);
    const data = await proxyFetch(url);

    const preview = JSON.stringify(data, null, 2).slice(0, 2000);
    $('customPreview').innerHTML = `<div class="json-preview">${escapeHtml(preview)}</div>`;

    log('AI detecting data structure...', 'ai');
    const parsed = await aiParse(data, url);

    $('customMapping').style.display = 'block';
    $('customLabels').value = parsed.path_labels || '';
    $('customValues').value = parsed.path_values || '';
    $('customName').value = parsed.name || 'Custom Dataset';
    $('customUnit').value = parsed.unit || '';

    log(`AI detected: ${parsed.name} (${parsed.data_type}, ${parsed.granularity})`, 'success');
    if (parsed.confidence < 0.7) {
      log('Low confidence — please verify the field mappings', 'error');
    }

    state._customRawData = data;

  } catch (e) {
    log(`Custom fetch error: ${e.message}`, 'error');
  }

  btn.disabled = false;
  btn.textContent = 'Fetch & Detect';
}

function doCustomAdd() {
  const rawData = state._customRawData;
  if (!rawData) return;

  const labelsPath = $('customLabels').value;
  const valuesPath = $('customValues').value;
  const name = $('customName').value || 'Custom';
  const unit = $('customUnit').value || '';

  try {
    const labels = extractPath(rawData, labelsPath);
    const values = extractPath(rawData, valuesPath).map(Number);

    if (!labels.length || !values.length) {
      log('Could not extract data with the given paths', 'error');
      return;
    }

    const id = 'custom-' + Date.now();
    const customApi = {
      id, name, category: 'Custom', desc: 'User-added dataset', unit,
      granularity: 'unknown', location_type: 'global', max_history_days: 0,
    };
    state.customDatasets.push(customApi);

    state.matrixData[id] = { labels, values, name, unit, category: 'Custom', count: values.length, id };

    populateDropdowns();
    populateMatrixControls();
    log(`Added custom dataset: ${name} (${values.length} points)`, 'success');

  } catch (e) {
    log(`Error extracting data: ${e.message}`, 'error');
  }
}

function extractPath(data, path) {
  const parts = path.split('.');
  let current = data;
  for (const part of parts) {
    if (current == null) return [];
    if (part.includes('[') && part.includes(']')) {
      const key = part.split('[')[0];
      current = key ? current[key] : current;
    } else {
      current = current[part];
    }
  }
  return Array.isArray(current) ? current : [current];
}

// --- Clear ------------------------------------------------------------------
function doClear() {
  state.selectedA = '';
  state.selectedB = '';
  state.dataA = null;
  state.dataB = null;
  selA.value = '';
  selB.value = '';
  updateSlots();
  updateFetchBtn();
  updateLocationVisibility();
  $('resultsPanel').style.display = 'none';
  $('chartsPanel').style.display = 'none';
  $('statsPanel').style.display = 'none';
  $('tablePanel').style.display = 'none';
  $('explorePanel').style.display = 'none';
  $('aiInsight').innerHTML = '';
  filterDropdownCompatibility('', selA);
  filterDropdownCompatibility('', selB);
}

// --- CSV Export --------------------------------------------------------------
function doExportCsv() {
  if (!state._tableLabels) return;
  const a = state.dataA;
  const b = state.dataB;
  let csv = `Date,${a.name} (${a.unit}),${b.name} (${b.unit})\n`;
  for (let i = 0; i < state._tableLabels.length; i++) {
    csv += `${state._tableLabels[i]},${state._tableA[i]},${state._tableB[i]}\n`;
  }
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `correlation_${a.id}_${b.id}.csv`;
  link.click();
  URL.revokeObjectURL(url);
  log('CSV exported', 'success');
}

// --- Logging ----------------------------------------------------------------
function log(msg, type = '') {
  const el = $('log');
  if (!el) return;
  const time = new Date().toLocaleTimeString();
  const div = document.createElement('div');
  div.className = `log-entry ${type}`;
  div.textContent = `[${time}] ${msg}`;
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
}

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// --- Boot -------------------------------------------------------------------
init();
