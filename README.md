# Still on Record — site

Static site for stillonrecord.org. CSV in git, a build script, files on a CDN. No database,
no backend, nothing to patch.

```
python3 build.py        # reads data/fixture_dev.csv, writes site/
```

No dependencies. Python 3.9 or later. The build validates the schema first and exits non-zero
on any failure, so wiring it into CI is enough to stop a broken record reaching the site.

To preview locally, serve the output rather than opening the files directly, so relative paths
and the JSON artifacts behave:

```
cd site && python3 -m http.server 8000
```

## What gets built

```
site/
  index.html              the map, with the record index beside it
  register.html           events that qualify and cannot be located
  method.html             inclusion rules, tiers, toll basis, the density caveat
  about.html              status, licence, who runs it
  record/EV0001.html      one static page per record, own URL, indexable
  data/points.geojson     map pins, minimal fields
  data/search.json        name, place, year, id
  data/entries/EV0001.json  full record
  data/dataset.csv        the whole file, for download
  assets/                 css and js, copied as-is
```

At 62 records the map page inlines the data, which keeps it working from a file:// URL and
costs about 45 KB. Past a few hundred records, switch `build_index` to emit a `<script>` that
fetches `data/points.geojson`, and have the panel fetch `data/entries/<id>.json` when it opens.
The artifacts are already being written for that day.

## The map

MapLibre GL JS with vector tiles from OpenFreeMap. No API key, no usage limits, no
terms-of-service risk. The style lives in `assets/basemap.js` and is ours, not a fork of a
default one:

- roads as hairlines in one colour, no casings, **no road labels and no shields**
- place names kept: country, state, city, town, village, and smaller places from z13
- water, coastline, sea and lake names
- country boundaries solid, admin 3 to 6 dashed from z5
- buildings as a faint fill from z15, so a village reads as a village
- no POIs, no landuse colour, no parks, no rail, no hillshade

Zoom runs to 17, which is building level. Tiles are served to z14 and overzoomed above that.

If OpenFreeMap ever becomes unreliable, the fallback is a self-hosted `.pmtiles` planet file on
Cloudflare R2 served by range requests. Change `OFM_TILES` in `assets/basemap.js`; the schema is
the same OpenMapTiles schema, so nothing else moves.

Attribution is required and is in the map's attribution control: OpenFreeMap, OpenMapTiles,
OpenStreetMap contributors.

## Pins

Shape carries the site role, fill carries the status, and nothing carries the toll.

| | |
|---|---|
| filled circle | a site of harm |
| hollow square | a room where decisions were taken. Never clusters with victim sites. |
| dashed ring | the record covers an area, not a located point |
| thin outer ring | more records underneath, zoom to separate them |
| no pin at all | unlocated. It stays in the index and in the register. |

Where several records fall in one place at low zoom, one stands in for the group and the rest
are hidden. The stand-in is picked by a fixed rule, so the same view always shows the same
record: parent campaign row first, then evidence tier, then death figure, then earliest start
year. There are no cluster bubbles with counts, deliberately. A bubble reading 44,000 next to
one reading 12 makes a quantitative claim that the data cannot support.

## Deploying

Cloudflare Pages, repo on GitHub, build command `python3 build.py`, output directory `site`.
Free tier, unlimited bandwidth, global CDN. Set long cache headers on `record/*` and
`data/entries/*`, short on `data/points.geojson` so corrections propagate.

Expected annual cost: the domain.

## Design tokens

Everything is in `:root` at the top of `assets/site.css`. Dark mode is the same set redefined
under `prefers-color-scheme`.

| Token | Light | Use |
|---|---|---|
| `--paper` | `#EBEDE9` | page |
| `--card` | `#F6F7F4` | index column, panels, controls |
| `--sunk` | `#E0E4DF` | caveat strip, selected row |
| `--ink` | `#1F2527` | text |
| `--ink-soft` | `#616B68` | secondary text |
| `--rule` | `#CDD2CC` | borders |
| `--rule-soft` | `#DCE0DA` | row dividers |
| `--confirmed` | `#5C6B64` | status: confirmed |
| `--contested` | `#8A6A2F` | status: historians disagree |
| `--ongoing` | `#3D5F79` | status: before the courts |
| `--focus` | `#2E5E4E` | focus ring |

Basemap colours are separate, in `PALETTE` in `assets/basemap.js`, because MapLibre cannot read
CSS variables. Keep the two in step by hand.

Type: IBM Plex Serif for record names and headings, IBM Plex Sans for everything else. Sizes
run 11.5 / 12.5 / 13 / 14 / 15 / 16 / 19 / 30. Transitions are 200ms ease and all of them drop
to zero under `prefers-reduced-motion`.

Colour is information only. There is no decorative colour anywhere, and status is the only
thing colour encodes.

## Done

- map, index, filters, time slider, layer toggles, search
- deterministic representative points, keyboard and screen reader paths
- filter and selection state in the URL, so a view can be shared and cited
- static record pages with sibling and campaign navigation
- register and method pages
- schema validation that fails the build
- data artifacts for the client-side split

## Not done

- **Coordinates.** The fixture's 49 points are approximate development values and must not
  ship. Add a `wikidata` column, backfill QIDs, take coordinates from there, and check each one
  by eye against satellite imagery before it goes live. An auto-geocoded massacre site on the
  wrong village is the worst error this project can make.
- **`precision_m`.** A centroid of an administrative unit has to render as a circle with a
  radius, not a point. The dashed-ring styling is already in the CSS, waiting for the field.
- Region, route and network geometries. They currently render as a point with a dashed ring.
  Points carry the project; polygons can wait.
- Recently-added changelog, driven from git history rather than written by hand.
- Analytics. Still an open decision. If anything goes in, it should be something that needs no
  cookie banner.
- Copy on `about.html` names a stichting that has no name in it yet.

## Switching to the full dataset

Change `SOURCE` at the top of `build.py` to `suffering_map_MASTER.csv`. Nothing else changes.
Records without coordinates simply do not plot, which is the correct behaviour while geocoding
is in progress.
