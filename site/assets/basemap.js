/* Still on Record — basemap style
 *
 * Built on OpenFreeMap's hosted OpenMapTiles vector tiles. No API key, no usage limits.
 * Attribution is required: OpenFreeMap, OpenMapTiles, OpenStreetMap contributors.
 *
 * What this style shows, and why:
 *   roads          hairlines, one colour, no casings, no labels, no shields
 *   place names    country, state, city, town, village, and at high zoom suburb/hamlet
 *   water          fill and coastline, plus sea and lake names
 *   boundaries     country solid hairline, admin 3-6 dashed from z5
 *   buildings      faint fill from z15, so a village reads as a village
 * What it leaves out: POIs, road names, house numbers, landuse colour, parks, rail,
 * aeroways, hillshade. The pins are the content.
 *
 * If OpenFreeMap becomes unreliable, swap SOURCE_URL for a self-hosted PMTiles file on
 * R2. Nothing else in this file changes; the schema is the same.
 */

const OFM_TILES = 'https://tiles.openfreemap.org/planet';
const OFM_GLYPHS = 'https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf';

const PALETTE = {
  light: {
    land:     '#EFF1EC',
    water:    '#DAE1E2',
    waterline:'#C6D0D1',
    road:     '#D3D8D2',
    roadMajor:'#C6CCC5',
    boundary: '#B0B8B1',
    building: '#E4E7E1',
    label:    '#3A4442',
    labelSoft:'#6C7672',
    labelWater:'#7C8C8E',
    halo:     '#EFF1EC'
  },
  dark: {
    land:     '#141818',
    water:    '#0D1213',
    waterline:'#1B2324',
    road:     '#2A3130',
    roadMajor:'#39413F',
    boundary: '#39413F',
    building: '#1B2020',
    label:    '#A9B3AF',
    labelSoft:'#78837F',
    labelWater:'#5E6C6E',
    halo:     '#141818'
  }
};

/* road width ramp: invisible until the zoom where the class matters, hairline after */
function roadWidth(a, b) {
  return ['interpolate', ['exponential', 1.4], ['zoom'], a[0], a[1], b[0], b[1]];
}

function buildStyle(dark) {
  const c = dark ? PALETTE.dark : PALETTE.light;
  const placeLabel = [
    'case',
    ['has', 'name:nonlatin'],
    ['concat', ['get', 'name:latin'], ' ', ['get', 'name:nonlatin']],
    ['coalesce', ['get', 'name_en'], ['get', 'name']]
  ];

  return {
    version: 8,
    glyphs: OFM_GLYPHS,
    sources: {
      openmaptiles: { type: 'vector', url: OFM_TILES }
    },
    layers: [
      { id: 'background', type: 'background', paint: { 'background-color': c.land } },

      { id: 'water', type: 'fill', source: 'openmaptiles', 'source-layer': 'water',
        filter: ['!=', ['get', 'brunnel'], 'tunnel'],
        paint: { 'fill-color': c.water } },

      { id: 'water-outline', type: 'line', source: 'openmaptiles', 'source-layer': 'water',
        minzoom: 4,
        paint: { 'line-color': c.waterline, 'line-width': 0.6 } },

      { id: 'waterway', type: 'line', source: 'openmaptiles', 'source-layer': 'waterway',
        minzoom: 8,
        paint: { 'line-color': c.waterline, 'line-width': roadWidth([8, 0.4], [18, 2.2]) } },

      { id: 'building', type: 'fill', source: 'openmaptiles', 'source-layer': 'building',
        minzoom: 15,
        paint: { 'fill-color': c.building, 'fill-antialias': false,
                 'fill-opacity': ['interpolate', ['linear'], ['zoom'], 15, 0, 16, 1] } },

      /* roads. one family, no casings, no colour coding by class. */
      { id: 'road-minor', type: 'line', source: 'openmaptiles', 'source-layer': 'transportation',
        minzoom: 12,
        filter: ['match', ['get', 'class'], ['minor', 'service', 'track', 'path', 'pedestrian'], true, false],
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': c.road, 'line-width': roadWidth([12, 0.3], [18, 3.5]) } },

      { id: 'road-secondary', type: 'line', source: 'openmaptiles', 'source-layer': 'transportation',
        minzoom: 8,
        filter: ['match', ['get', 'class'], ['secondary', 'tertiary'], true, false],
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': c.road, 'line-width': roadWidth([8, 0.4], [18, 5]) } },

      { id: 'road-primary', type: 'line', source: 'openmaptiles', 'source-layer': 'transportation',
        minzoom: 6,
        filter: ['match', ['get', 'class'], ['primary', 'trunk'], true, false],
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': c.roadMajor, 'line-width': roadWidth([6, 0.4], [18, 6]) } },

      { id: 'road-motorway', type: 'line', source: 'openmaptiles', 'source-layer': 'transportation',
        minzoom: 5,
        filter: ['==', ['get', 'class'], 'motorway'],
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': c.roadMajor, 'line-width': roadWidth([5, 0.5], [18, 7]) } },

      /* boundaries */
      { id: 'boundary-sub', type: 'line', source: 'openmaptiles', 'source-layer': 'boundary',
        minzoom: 5,
        filter: ['all', ['>=', ['get', 'admin_level'], 3], ['<=', ['get', 'admin_level'], 6],
                 ['!=', ['get', 'maritime'], 1]],
        paint: { 'line-color': c.boundary, 'line-dasharray': [2, 2], 'line-width': 0.6,
                 'line-opacity': 0.7 } },

      { id: 'boundary-country', type: 'line', source: 'openmaptiles', 'source-layer': 'boundary',
        filter: ['all', ['==', ['get', 'admin_level'], 2], ['!=', ['get', 'maritime'], 1],
                 ['!=', ['get', 'disputed'], 1]],
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': c.boundary,
                 'line-width': ['interpolate', ['linear'], ['zoom'], 2, 0.5, 6, 0.8, 12, 1.2] } },

      { id: 'boundary-disputed', type: 'line', source: 'openmaptiles', 'source-layer': 'boundary',
        filter: ['all', ['!=', ['get', 'maritime'], 1], ['==', ['get', 'disputed'], 1]],
        paint: { 'line-color': c.boundary, 'line-dasharray': [1, 2],
                 'line-width': ['interpolate', ['linear'], ['zoom'], 2, 0.5, 12, 1.2] } },

      /* names. no road labels anywhere. */
      { id: 'label-sea', type: 'symbol', source: 'openmaptiles', 'source-layer': 'water_name',
        filter: ['match', ['geometry-type'], ['Point', 'MultiPoint'], true, false],
        layout: { 'text-field': placeLabel, 'text-font': ['Noto Sans Italic'],
                  'text-size': ['interpolate', ['linear'], ['zoom'], 2, 10, 8, 13],
                  'text-letter-spacing': 0.12, 'text-max-width': 6 },
        paint: { 'text-color': c.labelWater, 'text-halo-color': c.halo, 'text-halo-width': 1 } },

      { id: 'label-other', type: 'symbol', source: 'openmaptiles', 'source-layer': 'place',
        minzoom: 13,
        filter: ['match', ['get', 'class'],
                 ['city', 'continent', 'country', 'state', 'town', 'village'], false, true],
        layout: { 'text-field': placeLabel, 'text-font': ['Noto Sans Regular'],
                  'text-size': ['interpolate', ['linear'], ['zoom'], 13, 10, 16, 12],
                  'text-max-width': 9 },
        paint: { 'text-color': c.labelSoft, 'text-halo-color': c.halo, 'text-halo-width': 1.2 } },

      { id: 'label-village', type: 'symbol', source: 'openmaptiles', 'source-layer': 'place',
        minzoom: 10,
        filter: ['==', ['get', 'class'], 'village'],
        layout: { 'text-field': placeLabel, 'text-font': ['Noto Sans Regular'],
                  'text-size': ['interpolate', ['linear'], ['zoom'], 10, 10, 15, 13],
                  'text-max-width': 8 },
        paint: { 'text-color': c.labelSoft, 'text-halo-color': c.halo, 'text-halo-width': 1.2 } },

      { id: 'label-town', type: 'symbol', source: 'openmaptiles', 'source-layer': 'place',
        minzoom: 7,
        filter: ['==', ['get', 'class'], 'town'],
        layout: { 'text-field': placeLabel, 'text-font': ['Noto Sans Regular'],
                  'text-size': ['interpolate', ['linear'], ['zoom'], 7, 10, 14, 14],
                  'text-max-width': 8 },
        paint: { 'text-color': c.label, 'text-halo-color': c.halo, 'text-halo-width': 1.2 } },

      { id: 'label-city', type: 'symbol', source: 'openmaptiles', 'source-layer': 'place',
        minzoom: 4,
        filter: ['==', ['get', 'class'], 'city'],
        layout: { 'text-field': placeLabel, 'text-font': ['Noto Sans Regular'],
                  'text-size': ['interpolate', ['exponential', 1.2], ['zoom'], 4, 11, 8, 13, 14, 17],
                  'text-max-width': 8 },
        paint: { 'text-color': c.label, 'text-halo-color': c.halo, 'text-halo-width': 1.4 } },

      { id: 'label-state', type: 'symbol', source: 'openmaptiles', 'source-layer': 'place',
        minzoom: 5, maxzoom: 9,
        filter: ['==', ['get', 'class'], 'state'],
        layout: { 'text-field': placeLabel, 'text-font': ['Noto Sans Regular'],
                  'text-size': ['interpolate', ['linear'], ['zoom'], 5, 10, 8, 12],
                  'text-letter-spacing': 0.16, 'text-max-width': 9 },
        paint: { 'text-color': c.labelSoft, 'text-halo-color': c.halo, 'text-halo-width': 1.2 } },

      { id: 'label-country', type: 'symbol', source: 'openmaptiles', 'source-layer': 'place',
        minzoom: 2, maxzoom: 10,
        filter: ['==', ['get', 'class'], 'country'],
        layout: { 'text-field': placeLabel, 'text-font': ['Noto Sans Regular'],
                  'text-size': ['interpolate', ['linear'], ['zoom'], 2, 10, 6, 14, 9, 15],
                  'text-letter-spacing': 0.08, 'text-max-width': 7 },
        paint: { 'text-color': c.label, 'text-halo-color': c.halo, 'text-halo-width': 1.4 } }
    ]
  };
}
