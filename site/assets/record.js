/* Still on Record — the small map on a record page
   REC is injected by the page: this record, plus the located records of its campaign,
   each with id, name, lat, lon, status and role. With no campaign, only this record. Pins use the same markup and styles as the main map;
   this record is drawn selected, and every other pin links to its own record page. */

(function () {
  const REC = window.REC;
  const box = document.getElementById('minimap');
  if (!REC || !box) return;

  const failed = () => box.classList.add('failed');
  if (typeof maplibregl === 'undefined') { failed(); return; }

  const dark = window.matchMedia('(prefers-color-scheme:dark)').matches;
  const map = new maplibregl.Map({
    container: box,
    style: buildStyle(dark),
    center: [REC.self.lon, REC.self.lat],
    zoom: 9,
    maxZoom: 16,
    attributionControl: false,
    dragRotate: false,
    pitchWithRotate: false,
    scrollZoom: false,        // a map inside a page must not hijack page scrolling
    cooperativeGestures: false
  });
  map.touchZoomRotate.disableRotation();
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
  map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right');

  const pins = [REC.self].concat(REC.near);
  const esc = t => String(t).replace(/[&<>"]/g,
    c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  /* Grouping works exactly as on the main map (see representatives() in map.js): pins that
     land close together on screen are grouped under one pin with a ring and split apart
     as you zoom in, and records on one exact spot fan out only from SPREAD_ZOOM. This
     record always stands in for its own group, so it never disappears. */
  const SPREAD_ZOOM = 10, CELL = 34;
  pins.forEach(p => {
    const mc = maplibregl.MercatorCoordinate.fromLngLat([p.lon, p.lat]);
    p.mx = mc.x; p.my = mc.y;
  });

  function groups() {
    const z = Math.floor(map.getZoom()), scale = 512 * Math.pow(2, z);
    const cells = new Map();
    pins.forEach(p => {
      const k = Math.floor(p.mx * scale / CELL) + ':' + Math.floor(p.my * scale / CELL);
      if (!cells.has(k)) cells.set(k, []);
      cells.get(k).push(p);
    });
    const out = [];
    for (const arr of cells.values()) {
      if (arr.length === 1) { out.push({ rep: arr[0], n: 1 }); continue; }
      const names = new Set(arr.map(p => p.pc).filter(Boolean));
      const ranked = arr.slice().sort((a, b) =>
        (b === REC.self) - (a === REC.self)
        || (names.has(b.name) ? 1 : 0) - (names.has(a.name) ? 1 : 0)
        || (+a.t || 9) - (+b.t || 9)
        || (+b.dh || 0) - (+a.dh || 0)
        || (a.sy ?? 9999) - (b.sy ?? 9999) || (a.id < b.id ? -1 : 1));
      const same = arr.every(p => p.lat === arr[0].lat && p.lon === arr[0].lon);
      if (same && z >= SPREAD_ZOOM) {
        ranked.forEach((p, i) => out.push({ rep: p, n: 1, fan: [i, ranked.length] }));
        continue;
      }
      out.push({ rep: ranked[0], n: arr.length });
    }
    return out;
  }

  function marker(p, n, fan) {
    const self = p === REC.self;
    const el = document.createElement(self ? 'span' : 'a');
    el.className = 'mk' + (self ? ' sel' : '');
    el.dataset.st = p.st || 'confirmed';
    el.dataset.role = p.role;
    if (!self) {
      el.href = p.id + '.html';
      el.setAttribute('aria-label', p.name + ', ' + p.y +
        (n > 1 ? '. ' + (n - 1) + ' further records in this area, zoom in to separate them' : ''));
    }
    let offset = [0, 0], leg = '';
    if (fan) {
      const [i, k] = fan;
      const r = Math.max(18, Math.ceil(k * 24 / (2 * Math.PI)));
      const a = -Math.PI / 2 + i * 2 * Math.PI / k;
      offset = [Math.round(r * Math.cos(a)), Math.round(r * Math.sin(a))];
      leg = `<span class="leg" style="width:${r}px;transform:rotate(${a + Math.PI}rad)"></span>`;
    }
    el.innerHTML = leg + (n > 1 ? '<span class="ring"></span>' : '') + '<span class="dot"></span>' +
      (self ? '' : '<span class="tip">' + esc(p.name) + '</span>');
    return new maplibregl.Marker({ element: el, offset }).setLngLat([p.lon, p.lat]);
  }

  const shown = new Map();
  function sync() {
    const keep = new Set();
    groups().forEach(g => {
      const key = g.rep.id + '|' + (g.fan ? 'f' + g.fan.join('/') : g.n > 1 ? 'g' + g.n : 's');
      keep.add(key);
      if (!shown.has(key)) shown.set(key, marker(g.rep, g.n, g.fan).addTo(map));
    });
    for (const [key, m] of shown) if (!keep.has(key)) { m.remove(); shown.delete(key); }
  }
  map.on('zoomend', sync);

  // The box can still be settling when the map starts (fonts, the phone layout), so keep
  // the map's canvas matched to it, and re-frame once it has its real size.
  if ('ResizeObserver' in window) new ResizeObserver(() => map.resize()).observe(box);

  // Frame the whole campaign right away, not only once the basemap has loaded, so the
  // pins are in view even on a slow connection or if the tiles never arrive.
  const frame = () => {
    if (!REC.near.length) return;
    const b = new maplibregl.LngLatBounds();
    pins.forEach(p => b.extend([p.lon, p.lat]));
    map.fitBounds(b, { padding: 44, maxZoom: 11, animate: false });
  };
  frame();
  sync();
  map.on('load', () => { map.resize(); frame(); sync(); });

  window.matchMedia('(prefers-color-scheme:dark)').addEventListener('change', ev => {
    map.setStyle(buildStyle(ev.matches));
  });

  // Only give up if the tiles never arrive at all.
  let loaded = false;
  map.on('load', () => { loaded = true; });
  setTimeout(() => {
    try { if (!loaded || !map.isSourceLoaded('openmaptiles')) failed(); }
    catch (_) { failed(); }
  }, 8000);
})();
