# Still on Record

Static site for stillonrecord.org. A CSV in git, a build script, files on a CDN. No database, no backend, nothing to patch.

```
python3 build.py        # reads site/data/suffering_map_MASTER.csv, writes dist/
```

No dependencies beyond the standard library. **Python 3.12 or later.** The build validates the schema first and exits non-zero on any failure, so a broken record can't reach the site.

To preview locally, serve the output rather than opening files directly, so relative paths and the JSON artifacts behave:

```
cd dist && python3 -m http.server 8000
```

`build.py` looks for `data/`, `assets/`, `docs/` and `images/` at the repo root first, then inside `site/`. It always writes to `dist/`.

## What gets built

```
dist/
  index.html              the map, with the record index beside it
  register.html           events that qualify and cannot be located
  method.html             inclusion rules, tiers, toll basis, the density caveat
  about.html              status, licence, who runs it, what the site knows about you
  images.html             the image policy, generated from docs/image_policy.md
  rules.html              inclusion rules, generated from docs/inclusion_rules.md
  record/EV0001.html      one static page per record, own URL, indexable
  data/points.geojson     map pins, minimal fields
  data/search.json        name, place, year, id
  data/entries/EV0001.json  full record, with an embedded attribution block
  data/dataset.csv        the whole file, for download
  data/README.txt         licence and citation, sits beside the download
  assets/                 css, js, self-hosted fonts and maplibre
  images/                 record images, copied as-is
  CNAME                   the custom domain, written on every build
```

At 604 records the map page inlines the data, which costs about 370 KB. That's past the point where it should. Switch `build_index` to emit a `<script>` that fetches `data/points.geojson`, and have the panel fetch `data/entries/<id>.json` when it opens. Both artifacts are already written.

## Nothing calls out to a third party

Except two things, and both are named on the About page.

- `tiles.openfreemap.org` for the basemap
- `gc.zgo.at` for the visitor count

Fonts are IBM Plex under the SIL Open Font License, subsetted to Latin1/2/3 with unicode ranges, served from `assets/fonts/`. MapLibre GL is BSD licensed and served from `assets/vendor/`. **Do not reintroduce Google Fonts or unpkg.** That was a deliberate removal.

## Analytics

GoatCounter, EUPL licensed, EU hosted, no cookies, nothing stored on the visitor's device, so no consent banner. Set by one constant at the top of `build.py`:

```python
ANALYTICS = 'https://stillonrecord.goatcounter.com/count'
```

Empty string emits no script at all, and the About page rewrites itself to match whichever state it's in. Self-hosting the Go binary later is a change to that line and nothing else.

## The map

MapLibre GL JS with vector tiles from OpenFreeMap. No API key, no usage limits, no terms-of-service risk. The style lives in `assets/basemap.js` and is ours, not a fork of a default one:

- roads as hairlines in one colour, no casings, **no road labels and no shields**
- place names kept: country, state, city, town, village, and smaller places from z13
- water, coastline, sea and lake names
- country boundaries solid, admin 3 to 6 dashed from z5
- buildings as a faint fill from z15, so a village reads as a village
- no POIs, no landuse colour, no parks, no rail, no hillshade

Zoom runs to 17. Tiles are served to z14 and overzoomed above that.

If OpenFreeMap ever becomes unreliable, the fallback is a self-hosted `.pmtiles` planet file on Cloudflare R2 served by range requests. Change `OFM_TILES` in `assets/basemap.js`; the schema is the same OpenMapTiles schema, so nothing else moves.

## Pins

Shape carries the site role, fill carries the status, and nothing carries the toll.

| | |
|---|---|
| filled circle | a site of harm |
| hollow square | a room where decisions were taken. Never clusters with victim sites. |
| dashed ring | the record covers an area, not a located point |
| thin outer ring | more records underneath, zoom to separate them |
| no pin at all | unlocated. It stays in the index and in the register. |

Where several records fall in one place at low zoom, one stands in for the group and the rest are hidden. The stand-in is picked by a fixed rule, so the same view always shows the same record: parent campaign row first, then evidence tier, then death figure, then earliest start year. There are no cluster bubbles with counts, deliberately. A bubble reading 44,000 next to one reading 12 makes a quantitative claim the data can't support.

Records with no date are published and stay visible at every slider position, because unknown shouldn't mean excluded. `map.js` renders them as "Date not recorded".

## Deploying

GitHub Actions to GitHub Pages, on every push to `main`. The workflow is `.github/workflows/build.yml`: it runs `build.py`, uploads `dist/`, and deploys.

Build takes a few seconds. Deploy is GitHub queuing on their side and runs anywhere from 10 seconds to a couple of minutes. A slow green deploy is normal. A fast red build means validation caught something, and the log names the record and the problem.

Annual cost: the domain.

## Design tokens

Everything is in `:root` at the top of `assets/site.css`. Dark mode is the same set redefined under `prefers-color-scheme`.

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

Basemap colours are separate, in `PALETTE` in `assets/basemap.js`, because MapLibre can't read CSS variables. Keep the two in step by hand.

Type: IBM Plex Serif for record names and headings, IBM Plex Sans for everything else. Sizes run 11.5 / 12.5 / 13 / 14 / 15 / 16 / 19 / 30. Transitions are 200ms ease and all drop to zero under `prefers-reduced-motion`.

Colour is information only. There's no decorative colour anywhere, and status is the only thing colour encodes.

## Fields the build enforces

Validation fails the build, it doesn't warn. Current rules:

- duplicate id, missing `key_source`, `evidence_tier` or `event_name`
- `toll_basis` of `not_quantified` alongside a death figure
- `deaths_high` set while `deaths_low` is empty
- `unmapped` geometry outside the register layer, or a register row marked visible
- `end_year` before `start_year`, or `start_year` below the 1500 floor
- coordinates out of range
- a `description` over 350 words
- a quote with no speaker or no source, or over 45 words
- an image with no caption, credit or recognised licence
- an `image_licence` outside `own`, `public_domain`, `cc0`, `cc_by`, `cc_by_sa`, `permission`
- an `image_tier` outside A, B, C, or a tier C image with no warning line

Empty `start_year` is allowed. Those records publish, and stay visible at every slider position.

## Done

- map, index, filters, time slider, layer toggles, search
- deterministic representative points, keyboard and screen reader paths
- filter and selection state in the URL, so a view can be shared and cited
- static record pages with sibling and campaign navigation
- register, method, image policy and inclusion rules pages
- schema validation that fails the build
- self-hosted fonts and map library, no Google, no unpkg
- cookieless analytics with a matching privacy statement
- description, quote and image fields, with the image tier system
- attribution embedded in every data artifact
- custom domain with CNAME written on every build

## Not done

- **Coordinates.** 289 records have them and **none are verified.** They were placed from general knowledge, not a gazetteer. Add a `wikidata` column, backfill QIDs, take coordinates from there, and check each one against satellite imagery. An auto-geocoded massacre site on the wrong village is the worst error this project can make.
- **The inline data split.** 370 KB before first paint, and growing. See "What gets built".
- Region, route and network geometries. They render as a point with a dashed ring today. Points carry the project; polygons can wait.
- Recently-added changelog, driven from git history rather than written by hand.
- `about.html` names a stichting that has no name in it yet, and the correction addresses don't exist yet.
- The stale generated files still committed under `site/` should be deleted. `site/data/`, `site/assets/`, `site/docs/` and `site/images/` stay.

## Documents

`docs/` holds the project's own rules, and two of them are rendered onto the site by the build.

| | |
|---|---|
| `DATA_HANDBOOK.md` | how to verify and collect records. Read before touching the CSV. |
| `DATA_DICTIONARY.md` | every field, its values, the validation rules |
| `inclusion_rules.md` | what qualifies. Rendered to `rules.html`. |
| `image_policy.md` | what may be published. Rendered to `images.html`. |
| `HANDOFF_stage2.md` | the original build spec |

## Licence

Data under ODbL 1.0, text and documentation under CC BY-SA 4.0. See `LICENSE.md`. Credit is a condition, and share-alike means anything built on this stays open.
