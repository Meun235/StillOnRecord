/* Still on Record — the small map on a record page
   REC is injected by the page: this record, plus located records close by, each with
   id, name, lat, lon, status and role. Pins use the same markup and styles as the main map;
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

  // Records on exactly the same spot fan out around it, as on the main map.
  const spots = new Map();
  pins.forEach(p => {
    const k = p.lat + ',' + p.lon;
    if (!spots.has(k)) spots.set(k, []);
    spots.get(k).push(p);
  });

  const esc = s => String(s).replace(/[&<>"]/g,
    c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  pins.forEach(p => {
    const self = p === REC.self;
    const el = document.createElement(self ? 'span' : 'a');
    el.className = 'mk' + (self ? ' sel' : '');
    el.dataset.st = p.st || 'confirmed';
    el.dataset.role = p.role;
    if (!self) {
      el.href = p.id + '.html';
      el.setAttribute('aria-label', p.name + ', ' + p.y);
    }
    let offset = [0, 0], leg = '';
    const group = spots.get(p.lat + ',' + p.lon);
    if (group.length > 1) {
      const i = group.indexOf(p), n = group.length;
      const r = Math.max(18, Math.ceil(n * 24 / (2 * Math.PI)));
      const a = -Math.PI / 2 + i * 2 * Math.PI / n;
      offset = [Math.round(r * Math.cos(a)), Math.round(r * Math.sin(a))];
      leg = `<span class="leg" style="width:${r}px;transform:rotate(${a + Math.PI}rad)"></span>`;
    }
    el.innerHTML = leg + '<span class="dot"></span>' +
      (self ? '' : '<span class="tip">' + esc(p.name) + '</span>');
    new maplibregl.Marker({ element: el, offset }).setLngLat([p.lon, p.lat]).addTo(map);
  });

  // The box can still be settling when the map starts (fonts, the phone layout), so keep
  // the map's canvas matched to it, and re-frame once it has its real size.
  if ('ResizeObserver' in window) new ResizeObserver(() => map.resize()).observe(box);

  map.on('load', () => {
    map.resize();
    if (REC.near.length) {
      const b = new maplibregl.LngLatBounds();
      pins.forEach(p => b.extend([p.lon, p.lat]));
      map.fitBounds(b, { padding: 44, maxZoom: 11, animate: false });
    }
  });

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
