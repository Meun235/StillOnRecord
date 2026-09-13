/* Still on Record — map page
   RECORDS is injected by index.html. At fixture size it is inlined; past a few hundred
   records, swap the inline block for a fetch of data/points.geojson and pull the full
   record from data/entries/<id>.json when the panel opens. */

const DATA = window.RECORDS || [];
const S = { lo: 1500, hi: 2026, q: '', cat: null, core: true, src: false, sel: null };

const BASIS = {
  counted: 'Counted: bodies named, exhumed, or entered in the perpetrator\u2019s own register.',
  documented_estimate: 'Documented estimate: historians or commissions working from records.',
  excess_mortality: 'Excess mortality: modelled against a counterfactual, cumulative.',
  attributable_annual: 'Attributable annual: epidemiological attribution, per year.',
  not_quantified: 'Not quantified: the harm is documented, no defensible figure exists.'
};
const STATUS = { confirmed: 'Confirmed', contested: 'Historians disagree',
  ongoing_adjudication: 'Before the courts' };
const SUCC = {
  liability_spinoff: 'Liability spinoff: assets kept, liabilities parked elsewhere.',
  court_ordered: 'Court-ordered restructuring, imposed as a remedy. Not a rebrand.',
  rename: 'Renamed. Same entity throughout.',
  acquisition: 'Ordinary acquisition.',
  dissolved: 'Dissolved, no successor.',
  unchanged: 'Same entity, listed for clarity.'
};
const CAT_SHORT = { 'corporate and industrial harm': 'industrial harm',
  'cult and coercive organisation': 'coercive organisation' };

const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g,
  c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const num = n => n ? (+n).toLocaleString('en-GB') : '';
const yrs = d => d.sy === d.ey ? String(d.sy) : d.sy + '\u2013' + d.ey;
const toll = d => !d.deaths_low ? 'No defensible figure'
  : num(d.deaths_low) + (d.deaths_high ? '\u2013' + num(d.deaths_high) : '');
const reduced = () => window.matchMedia('(prefers-reduced-motion:reduce)').matches;

DATA.forEach(d => {
  d.hay = [d.event_name, d.place_name, d.country_today, d.perpetrator, d.key_source,
    d.target_group, d.parent_campaign, d.category].filter(Boolean).join(' ').toLowerCase();
  d.role = d.layer === 'source_sites' ? 'source'
    : (['region', 'route', 'network'].includes(d.geometry_type) ? 'area' : 'point');
});

function pass(d) {
  if (d.sy > S.hi || d.ey < S.lo) return false;
  if (S.q && !d.hay.includes(S.q)) return false;
  if (S.cat && d.category !== S.cat) return false;
  return d.layer === 'source_sites' ? S.src : S.core;
}
const plottable = d => d.lat !== undefined && d.lon !== undefined;

/* ---------- map ---------- */
let map = null, ready = false;
const markers = new Map();

function initMap() {
  if (typeof maplibregl === 'undefined') { mapFailed(); return; }
  const dark = window.matchMedia('(prefers-color-scheme:dark)').matches;
  map = new maplibregl.Map({
    container: 'map',
    style: buildStyle(dark),
    center: [12, 25],
    zoom: 1.4,
    minZoom: 0,
    maxZoom: 17,
    attributionControl: false,
    dragRotate: false,
    pitchWithRotate: false
  });
  map.touchZoomRotate.disableRotation();
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
  map.addControl(new maplibregl.AttributionControl({
    compact: true,
    customAttribution: '<a href="https://openfreemap.org">OpenFreeMap</a> \u00b7 ' +
      '<a href="https://www.openmaptiles.org/">OpenMapTiles</a> \u00b7 ' +
      '<a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
  }), 'bottom-right');

  map.on('load', () => {
    ready = true;
    // Frame the inhabited world, whatever the container is. A phone gets the same view a
    // desktop does, just smaller.
    if (!S.sel) map.fitBounds([[-168, -56], [178, 74]], { padding: 12, animate: false });
    syncMarkers();
    openFromHash();
  });
  map.on('zoomend', syncMarkers);
  map.on('moveend', syncMarkers);
  // Only warn if the tiles genuinely never arrive. A single failed tile is not a failure.
  setTimeout(() => {
    try { if (!ready || !map.isSourceLoaded('openmaptiles')) mapFailed(); }
    catch (_) { mapFailed(); }
  }, 8000);

  window.matchMedia('(prefers-color-scheme:dark)').addEventListener('change', ev => {
    map.setStyle(buildStyle(ev.matches));
  });
}
function mapFailed() {
  const el = document.getElementById('mapmsg');
  if (el) el.hidden = false;
}
function hideMapMsg() {
  const el = document.getElementById('mapmsg');
  if (el) el.hidden = true;
}

document.getElementById('mapmsg-x').addEventListener('click', hideMapMsg);

/* Deterministic representative points. Same input, same point, every time.
   Rank: parent campaign row, then evidence tier, then death figure, then earliest year. */
function representatives() {
  const vis = DATA.filter(d => plottable(d) && pass(d));
  if (!ready) return vis.map(d => ({ rep: d, n: 1 }));
  const z = Math.floor(map.getZoom());
  const scale = 512 * Math.pow(2, z), cell = 34;
  const cells = new Map();
  for (const d of vis) {
    if (d.mx === undefined) {
      const mc = maplibregl.MercatorCoordinate.fromLngLat([d.lon, d.lat]);
      d.mx = mc.x; d.my = mc.y;
    }
    const k = Math.floor(d.mx * scale / cell) + ':' + Math.floor(d.my * scale / cell);
    if (!cells.has(k)) cells.set(k, []);
    cells.get(k).push(d);
  }
  const out = [];
  for (const arr of cells.values()) {
    if (arr.length === 1) { out.push({ rep: arr[0], n: 1 }); continue; }
    const parents = new Set(arr.map(d => d.parent_campaign).filter(Boolean));
    const ranked = arr.slice().sort((a, b) =>
      (parents.has(b.event_name) ? 1 : 0) - (parents.has(a.event_name) ? 1 : 0)
      || (+a.evidence_tier || 9) - (+b.evidence_tier || 9)
      || (+(b.deaths_high || b.deaths_low) || 0) - (+(a.deaths_high || a.deaths_low) || 0)
      || a.sy - b.sy || (a.id < b.id ? -1 : 1));
    out.push({ rep: ranked[0], n: arr.length });
  }
  return out;
}

function makeMarker(d, group) {
  const el = document.createElement('button');
  el.className = 'mk';
  el.type = 'button';
  el.dataset.id = d.id;
  el.dataset.st = d.status || 'confirmed';
  el.dataset.role = d.role;
  el.setAttribute('aria-label', d.event_name + ', ' + yrs(d) +
    (group > 1 ? '. ' + (group - 1) + ' further records in this area' : ''));
  el.innerHTML = (group > 1 ? '<span class="ring"></span>' : '') +
    '<span class="dot"></span><span class="tip">' + esc(d.event_name) + '</span>';
  el.addEventListener('click', ev => { ev.stopPropagation(); select(d.id, true); });
  el.addEventListener('pointerenter', () => hoverRow(d.id, true));
  el.addEventListener('pointerleave', () => hoverRow(d.id, false));
  return new maplibregl.Marker({ element: el }).setLngLat([d.lon, d.lat]);
}

function syncMarkers() {
  if (!ready) return;
  const reps = representatives();
  const keep = new Set();
  reps.forEach(g => {
    const key = g.rep.id + '|' + (g.n > 1 ? 'g' : 's');
    keep.add(key);
    if (!markers.has(key)) {
      const m = makeMarker(g.rep, g.n);
      m.addTo(map);
      markers.set(key, m);
    }
    const el = markers.get(key).getElement();
    el.classList.toggle('sel', S.sel === g.rep.id);
    el.dataset.group = g.n;
  });
  for (const [key, m] of markers) {
    if (!keep.has(key)) { m.remove(); markers.delete(key); }
  }
  const count = DATA.filter(d => plottable(d) && pass(d)).length;
  document.getElementById('nPlot').textContent = count;
}

/* ---------- index list ---------- */
const list = document.getElementById('list');

function detail(d) {
  return `<div class="det">
    <dl class="f">
      <dt>Perpetrator</dt><dd>${esc(d.perpetrator || 'Not recorded')}</dd>
      ${d.target_group ? `<dt>Targeted</dt><dd>${esc(d.target_group)}</dd>` : ''}
      <dt>Deaths</dt><dd>${toll(d)}<span class="basis">${BASIS[d.toll_basis] || ''}</span></dd>
      ${d.affected_low ? `<dt>Affected</dt><dd>${num(d.affected_low)}${d.affected_high ? '\u2013' + num(d.affected_high) : ''} ${esc(d.affected_measure || '')}</dd>` : ''}
      <dt>Evidence</dt><dd>Tier ${esc(d.evidence_tier)}, ${(STATUS[d.status] || '').toLowerCase()}</dd>
      <dt>Source</dt><dd class="src">${esc(d.key_source || '')}</dd>
      ${d.perpetrator_today ? `<dt>Entity today</dt><dd>${esc(d.perpetrator_today)}<span class="basis">${SUCC[d.succession_type] || ''}</span></dd>` : ''}
      ${d.notes ? `<dt>Note</dt><dd>${esc(d.notes)}</dd>` : ''}
    </dl>
    ${d.register_reason ? `<div class="reg"><p>Not on the map: ${esc(d.register_reason)}.</p>
      <p>What would place it: ${esc(d.unlock)}.</p></div>` : ''}
    <a class="cta" href="record/${d.id}.html">Read the full record</a>
  </div>`;
}

function draw() {
  const rows = DATA.filter(pass).sort((a, b) => a.sy - b.sy || (a.id < b.id ? -1 : 1));
  document.getElementById('nShown').textContent = rows.length;
  document.getElementById('nReg').textContent = rows.filter(d => !plottable(d)).length;
  if (!rows.length) {
    list.innerHTML = '<p class="empty">Nothing matches. Widen the years, clear the search, ' +
      'or drop the category.</p>';
  } else {
    list.innerHTML = rows.map(d => {
      const un = !plottable(d);
      return `<article class="row${un ? ' unmapped' : ''}${S.sel === d.id ? ' sel' : ''}"
        data-id="${d.id}" data-st="${d.status || 'confirmed'}" tabindex="0">
        <h3 class="rname">${esc(d.event_name)}${un ? '<span class="nolo">no location</span>' : ''}</h3>
        <p class="rmeta"><span class="y">${yrs(d)}</span><span class="p">${esc(d.place_name || '')}</span></p>
        ${S.sel === d.id ? detail(d) : ''}
      </article>`;
    }).join('');
  }
  syncMarkers();
  writeUrl();
}

function hoverRow(id, on) {
  const r = list.querySelector(`[data-id="${id}"]`);
  if (r) r.classList.toggle('hov', on);
}
function hoverMarker(id, on) {
  for (const [key, m] of markers) {
    if (key.split('|')[0] === id) m.getElement().classList.toggle('hov', on);
  }
}

function select(id, fromMap) {
  S.sel = S.sel === id ? null : id;
  draw();
  const r = list.querySelector(`[data-id="${S.sel}"]`);
  if (r) r.scrollIntoView({ block: fromMap ? 'center' : 'nearest',
    behavior: reduced() ? 'auto' : 'smooth' });
  if (S.sel && !fromMap && ready) {
    const d = DATA.find(x => x.id === S.sel);
    if (d && plottable(d)) {
      map.flyTo({ center: [d.lon, d.lat], zoom: Math.max(map.getZoom(), 12),
        duration: reduced() ? 0 : 900 });
    }
  }
}

list.addEventListener('click', e => {
  const r = e.target.closest('.row');
  if (r && !e.target.closest('a')) select(r.dataset.id, false);
});
list.addEventListener('keydown', e => {
  const r = e.target.closest('.row');
  if (r && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); select(r.dataset.id, false); }
});
list.addEventListener('pointerover', e => {
  const r = e.target.closest('.row');
  if (r) hoverMarker(r.dataset.id, true);
});
list.addEventListener('pointerout', e => {
  const r = e.target.closest('.row');
  if (r && (!e.relatedTarget || !r.contains(e.relatedTarget))) hoverMarker(r.dataset.id, false);
});
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && S.sel) { S.sel = null; draw(); }
});

/* ---------- controls ---------- */
const cats = {};
DATA.forEach(d => { if (d.category) cats[d.category] = (cats[d.category] || 0) + 1; });
const chips = document.getElementById('chips');
Object.entries(cats).sort((a, b) => b[1] - a[1]).slice(0, 6).forEach(([c]) => {
  const b = document.createElement('button');
  b.className = 'chip';
  b.setAttribute('aria-pressed', 'false');
  b.textContent = CAT_SHORT[c] || c;
  b.onclick = () => {
    S.cat = S.cat === c ? null : c;
    [...chips.children].forEach(x => x.setAttribute('aria-pressed', String(x === b && S.cat === c)));
    draw();
  };
  chips.appendChild(b);
});

document.getElementById('q').addEventListener('input', e => {
  S.q = e.target.value.trim().toLowerCase(); draw();
});
const tc = document.getElementById('t-core'), ts = document.getElementById('t-src');
tc.onclick = () => { S.core = !S.core; tc.setAttribute('aria-pressed', String(S.core)); draw(); };
ts.onclick = () => { S.src = !S.src; ts.setAttribute('aria-pressed', String(S.src)); draw(); };

const r1 = document.getElementById('r1'), r2 = document.getElementById('r2');
function syncT() {
  S.lo = Math.min(+r1.value, +r2.value);
  S.hi = Math.max(+r1.value, +r2.value);
  document.getElementById('years').textContent = S.lo + '\u2013' + S.hi;
  const f = document.getElementById('fill');
  f.style.left = ((S.lo - 1500) / 526 * 100) + '%';
  f.style.width = ((S.hi - S.lo) / 526 * 100) + '%';
  draw();
}
r1.addEventListener('input', syncT);
r2.addEventListener('input', syncT);

let anim = null;
document.getElementById('play').onclick = function () {
  if (anim) { cancelAnimationFrame(anim); anim = null; this.textContent = 'Run'; return; }
  this.textContent = 'Stop';
  const t0 = performance.now(), btn = this;
  r1.value = 1500;
  const step = t => {
    const p = Math.min(1, (t - t0) / 20000);
    r2.value = Math.round(1500 + p * 526);
    syncT();
    if (p < 1) anim = requestAnimationFrame(step);
    else { anim = null; btn.textContent = 'Run'; }
  };
  anim = requestAnimationFrame(step);
};

/* ---------- shareable state ---------- */
function writeUrl() {
  const p = new URLSearchParams();
  if (S.lo !== 1500 || S.hi !== 2026) p.set('years', S.lo + '-' + S.hi);
  if (S.q) p.set('q', S.q);
  if (S.cat) p.set('cat', S.cat);
  if (!S.core) p.set('events', '0');
  if (S.src) p.set('sources', '1');
  const qs = p.toString();
  history.replaceState(null, '',
    location.pathname + (qs ? '?' + qs : '') + (S.sel ? '#' + S.sel : ''));
}
function readUrl() {
  const p = new URLSearchParams(location.search);
  const y = (p.get('years') || '').match(/^(\d{4})-(\d{4})$/);
  if (y) { r1.value = y[1]; r2.value = y[2]; }
  if (p.get('q')) { S.q = p.get('q').toLowerCase(); document.getElementById('q').value = p.get('q'); }
  if (p.get('cat')) {
    S.cat = p.get('cat');
    [...chips.children].forEach(x =>
      x.setAttribute('aria-pressed', String((CAT_SHORT[S.cat] || S.cat) === x.textContent)));
  }
  if (p.get('events') === '0') { S.core = false; tc.setAttribute('aria-pressed', 'false'); }
  if (p.get('sources') === '1') { S.src = true; ts.setAttribute('aria-pressed', 'true'); }
  const id = location.hash.replace('#', '');
  if (DATA.some(d => d.id === id)) S.sel = id;
}
function openFromHash() {
  if (!S.sel) return;
  const d = DATA.find(x => x.id === S.sel);
  if (d && plottable(d)) map.jumpTo({ center: [d.lon, d.lat], zoom: 11 });
  const r = list.querySelector(`[data-id="${S.sel}"]`);
  if (r) r.scrollIntoView({ block: 'center' });
  syncMarkers();
}

readUrl();
syncT();
initMap();
