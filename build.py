#!/usr/bin/env python3
"""Still on Record — build script.

    CSV in git  ->  this script  ->  static files  ->  CDN

Finds its inputs at the repo root or inside site/, and always writes to dist/.

    python3 build.py

No dependencies beyond the standard library. Run it in CI on push; a failing
validation should fail the build.
"""

import csv, json, html, os, shutil, sys
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))


def _find(rel):
    """Look for a file or folder at the repo root, then inside site/."""
    for base in (ROOT, os.path.join(ROOT, 'site')):
        p = os.path.join(base, rel)
        if os.path.exists(p):
            return p
    sys.exit(f'Cannot find {rel} at the repo root or in site/')


SOURCE = _find(os.path.join('data', 'suffering_map_MASTER.csv'))
REGISTER = _find(os.path.join('data', 'suffering_map_register.csv'))
ASSETS = _find('assets')
OUT = os.path.join(ROOT, 'dist')

YEAR_FLOOR = 1500          # config value, not a research decision
YEAR_CEIL = date.today().year

TAGLINE = 'A sourced map of deliberately caused mass suffering, 1500 to now.'

BASIS = {
    'counted': 'Counted: bodies named, exhumed, or entered in the perpetrator\u2019s own register.',
    'documented_estimate': 'Documented estimate: historians or commissions working from records.',
    'excess_mortality': 'Excess mortality: modelled against a counterfactual, cumulative.',
    'attributable_annual': 'Attributable annual: epidemiological attribution, per year.',
    'not_quantified': 'Not quantified: the harm is documented, no defensible figure exists.',
}
STATUS = {'confirmed': 'Confirmed', 'contested': 'Historians disagree',
          'ongoing_adjudication': 'Before the courts'}
SUCC = {
    'liability_spinoff': 'Liability spinoff: assets kept, liabilities parked elsewhere.',
    'court_ordered': 'Court-ordered restructuring, imposed as a remedy. Not a rebrand.',
    'rename': 'Renamed. Same entity throughout.',
    'acquisition': 'Ordinary acquisition.',
    'dissolved': 'Dissolved, no successor.',
    'unchanged': 'Same entity, listed for clarity.',
}
ROLE = {'victim_site': 'Site of harm', 'decision_site': 'Room where decisions were taken',
        'perpetrator_site': 'Perpetrator site', 'evidence_site': 'Evidence site'}
COMPLETE = {'near_complete': 'near complete', 'extensive': 'extensive', 'partial': 'partial',
            'sparse': 'sparse', 'not_assessed': 'not assessed'}
TIER = {'1': 'Court judgment, tribunal, truth commission, state archive, or peer-reviewed demography',
        '2': 'Academic or NGO work with published methodology',
        '3': 'Journalism, testimony, or advocacy'}

e = html.escape


# ---------------------------------------------------------------- load


def load():
    with open(SOURCE, newline='', encoding='utf-8') as f:
        rows = [r for r in csv.DictReader(f)]
    with open(REGISTER, newline='', encoding='utf-8') as f:
        reg = {r['id']: r for r in csv.DictReader(f)}

    recs = []
    for r in rows:
        d = {k: (v or '').strip() for k, v in r.items()}
        d['sy'] = int(d['start_year'])
        d['ey'] = int(d['end_year'] or d['start_year'])
        if d['lat'] and d['lon']:
            d['lat'] = round(float(d['lat']), 5)
            d['lon'] = round(float(d['lon']), 5)
        else:
            d['lat'] = d['lon'] = None
        if d['id'] in reg:
            d['register_reason'] = reg[d['id']]['register_reason']
            d['unlock'] = reg[d['id']]['what_would_unlock_it']
        recs.append(d)
    recs.sort(key=lambda x: (x['sy'], x['id']))
    return recs


def validate(recs):
    """Fail the build rather than publish a broken record."""
    errors, seen = [], set()
    for d in recs:
        i = d['id']
        if i in seen:
            errors.append(f'{i}: duplicate id')
        seen.add(i)
        for field in ('key_source', 'evidence_tier', 'event_name', 'start_year'):
            if not d.get(field):
                errors.append(f'{i}: missing {field}')
        if d['toll_basis'] == 'not_quantified' and d['deaths_low']:
            errors.append(f'{i}: toll_basis is not_quantified but deaths_low is set')
        if d['deaths_high'] and not d['deaths_low']:
            errors.append(f'{i}: deaths_high set while deaths_low is empty')
        if d['geometry_type'] == 'unmapped' and d['layer'] != 'register':
            errors.append(f'{i}: unmapped geometry outside the register layer')
        if d['layer'] == 'register' and d['default_visible'] == 'TRUE':
            errors.append(f'{i}: register row marked visible by default')
        if d['ey'] < d['sy']:
            errors.append(f'{i}: end_year before start_year')
        if d['sy'] < YEAR_FLOOR:
            errors.append(f'{i}: start_year below the {YEAR_FLOOR} floor with no flag')
        if d['lat'] is not None and not (-90 <= d['lat'] <= 90 and -180 <= d['lon'] <= 180):
            errors.append(f'{i}: coordinates out of range')
    return errors


# ---------------------------------------------------------------- helpers


def years(d):
    return str(d['sy']) if d['sy'] == d['ey'] else f"{d['sy']}\u2013{d['ey']}"


def toll(d):
    if not d['deaths_low']:
        return 'No defensible figure'
    lo = f"{int(d['deaths_low']):,}"
    if d['deaths_high']:
        return f"{lo}\u2013{int(d['deaths_high']):,}"
    return lo


def affected(d):
    if not d['affected_low']:
        return ''
    s = f"{int(d['affected_low']):,}"
    if d['affected_high']:
        s += f"\u2013{int(d['affected_high']):,}"
    return f"{s} {d['affected_measure']}".strip()


def shell(title, body, desc=TAGLINE, depth=0, body_class='', extra_head='', extra_js=''):
    up = '../' * depth
    nav = [('index.html', 'Map'), ('register.html', 'Register'), ('method.html', 'Method'),
           ('about.html', 'About')]
    parts = []
    for h, t in nav:
        cur = ' aria-current="page"' if h == title[1] else ''
        parts.append(f'<a href="{up}{h}"{cur}>{t}</a>')
    links = ''.join(parts)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(title[0])}</title>
<meta name="description" content="{e(desc)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;450;600&family=IBM+Plex+Serif:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{up}assets/site.css">
{extra_head}</head>
<body{f' class="{body_class}"' if body_class else ''}>
<header class="mast">
  <a class="wordmark" href="{up}index.html">Still on Record</a>
  <p class="line">{e(TAGLINE)}</p>
  <nav>{links}</nav>
</header>
{body}
{extra_js}</body>
</html>
"""


FOOT = """<footer class="foot"><div class="in">
Data under the Open Database License, text under CC BY-SA 4.0. Free for any use including
commercial, with attribution and share-alike. Run by a Netherlands stichting; board, policy
plan and annual figures are published. No advertising, no paywall, no sponsored content.
<br>Seed stage: records name their sources, and those sources have not yet been opened and
checked one by one. Coordinates are approximate and unverified. Not for citation.
</div></footer>"""


# ---------------------------------------------------------------- map page


def build_index(recs):
    fields = ('id event_name parent_campaign layer geometry_type site_role place_name '
              'country_today perpetrator perpetrator_today succession_type target_group '
              'category deaths_low deaths_high toll_basis affected_low affected_high '
              'affected_measure toll_note evidence_tier status documentation_completeness '
              'key_source notes register_reason unlock').split()
    slim = []
    for d in recs:
        o = {k: d[k] for k in fields if d.get(k)}
        o['sy'], o['ey'] = d['sy'], d['ey']
        if d['lat'] is not None:
            o['lat'], o['lon'] = d['lat'], d['lon']
        slim.append(o)

    body = f"""
<div class="caveat">
  <span><b>Record density reflects which archives opened and which courts sat, not which
  atrocities were worst.</b> The Holocaust has 44,000 documented sites because the USHMM
  catalogued them. Most Chinese provincial archives have never been opened.</span>
  <a href="method.html#density">Why this matters</a>
</div>

<div class="wrap">
  <div class="idx">
    <div class="idxtop">
      <input class="search" id="q" type="search" autocomplete="off"
        placeholder="Search event, place, perpetrator, source" aria-label="Search records">
      <div class="chips" id="chips"></div>
      <div class="tline">
        <button class="play" id="play">Run</button>
        <div class="track">
          <div class="bar"></div><div class="fill" id="fill"></div>
          <input type="range" id="r1" min="{YEAR_FLOOR}" max="{YEAR_CEIL}" step="1"
            value="{YEAR_FLOOR}" aria-label="Start year">
          <input type="range" id="r2" min="{YEAR_FLOOR}" max="{YEAR_CEIL}" step="1"
            value="{YEAR_CEIL}" aria-label="End year">
        </div>
        <span class="yrs" id="years"></span>
      </div>
    </div>
    <div class="tally">
      <span><b id="nShown">0</b> records listed</span>
      <span><b id="nPlot">0</b> on the map, <b id="nReg">0</b> not plotted</span>
    </div>
    <div class="list" id="list"></div>
  </div>

  <div class="mapwrap">
    <div id="map"></div>
    <div class="toggles">
      <button id="t-core" aria-pressed="true">Events</button>
      <button id="t-src" aria-pressed="false">Source sites</button>
    </div>
    <div class="key">
      <span class="sw" style="background:var(--confirmed)"></span>Confirmed
      <span class="sw" style="background:var(--contested)"></span>Historians disagree
      <span class="sw" style="background:var(--ongoing)"></span>Before the courts<br>
      <span class="sw sq"></span>A room where decisions were taken, not a site of harm.
      A dashed ring covers an area rather than a point. A thin outer ring means more records
      underneath, so zoom in. Unlocated records stay in the list and never get a pin.
    </div>
    <div class="mapmsg" id="mapmsg" hidden>
      <b>The basemap didn\u2019t load.</b>
      Tiles come from OpenFreeMap and need a connection. Every record is still readable in the
      index on the left, and the register never needed the map.
    </div>
  </div>
</div>
"""
    head = ('<link href="https://unpkg.com/maplibre-gl@5/dist/maplibre-gl.css" rel="stylesheet">\n'
            '<script src="https://unpkg.com/maplibre-gl@5/dist/maplibre-gl.js"></script>\n')
    js = ('<script>window.RECORDS=' + json.dumps(slim, separators=(',', ':'),
                                                 ensure_ascii=False) + ';</script>\n'
          '<script src="assets/basemap.js"></script>\n'
          '<script src="assets/map.js"></script>\n')
    return shell(('Still on Record', 'index.html'), body, body_class='map',
                 extra_head=head, extra_js=js)


# ---------------------------------------------------------------- record pages


def build_record(d, recs):
    st = d['status'] or 'confirmed'
    siblings = [x for x in recs if x['parent_campaign'] and
                x['parent_campaign'] == d['parent_campaign'] and x['id'] != d['id']]
    children = [x for x in recs if x['parent_campaign'] == d['event_name']]
    sib_ids = {x['id'] for x in siblings} | {x['id'] for x in children}
    nearby = [x for x in recs if x['country_today'] == d['country_today']
              and x['id'] != d['id'] and x['id'] not in sib_ids][:6]

    rows = [('Years', e(years(d))),
            ('Place', e(d['place_name'] or 'Not recorded')),
            ('Country today', e(d['country_today'] or 'Not recorded')),
            ('Perpetrator', e(d['perpetrator'] or 'Not recorded'))]
    if d['perpetrator_today']:
        rows.append(('Entity today', e(d['perpetrator_today']) +
                     f'<span class="basis">{e(SUCC.get(d["succession_type"], ""))}</span>'))
    if d['target_group']:
        rows.append(('Targeted', e(d['target_group'])))
    rows.append(('Category', e(d['category'])))
    rows.append(('Deaths', e(toll(d)) +
                 f'<span class="basis">{e(BASIS.get(d["toll_basis"], ""))}</span>'))
    if affected(d):
        rows.append(('Affected', e(affected(d))))
    rows.append(('Evidence tier', f'Tier {e(d["evidence_tier"])}'
                 f'<span class="basis">{e(TIER.get(d["evidence_tier"], ""))}</span>'))
    rows.append(('Status', e(STATUS.get(st, st))))
    rows.append(('Key source', f'<span class="src">{e(d["key_source"])}</span>'))
    rows.append(('Documentation', e(COMPLETE.get(d['documentation_completeness'], 'not assessed')) +
                 (f'<span class="basis">{e(d["completeness_note"])}</span>'
                  if d['completeness_note'] else '')))
    rows.append(('Site role', e(ROLE.get(d['site_role'], d['site_role'] or 'Not recorded'))))
    rows.append(('Geometry', e(d['geometry_type'])))
    if d['parent_campaign']:
        rows.append(('Part of', e(d['parent_campaign'])))
    rows.append(('Record id', e(d['id'])))

    dl = '\n'.join(f'  <dt>{k}</dt><dd>{v}</dd>' for k, v in rows)

    prose = ''
    if d.get('notes'):
        prose += f'<p>{e(d["notes"])}.</p>'
    if d.get('toll_note'):
        prose += f'<h2>On the figures</h2><p>{e(d["toll_note"])}.</p>'
    if d.get('register_reason'):
        prose += ('<h2>Why this is not on the map</h2>'
                  f'<p>{e(d["register_reason"])}.</p>'
                  f'<p>What would place it: {e(d["unlock"])}.</p>')

    def lst(items, heading, note=''):
        if not items:
            return ''
        li = '\n'.join(
            f'<li><a href="{x["id"]}.html">{e(x["event_name"])}</a>'
            f'<span class="m">{e(years(x))}, {e(x["place_name"] or x["country_today"])}</span></li>'
            for x in items)
        return (f'<h2>{heading}</h2>' + (f'<p>{note}</p>' if note else '') +
                f'<ul class="siblings">{li}</ul>')

    mapped = d['lat'] is not None
    actions = []
    if mapped:
        actions.append(f'<a href="../index.html#{d["id"]}">Show this on the map</a>')
    actions.append(f'<a href="../data/entries/{d["id"]}.json">Download this record as JSON</a>')
    actions.append(f'<a href="mailto:corrections@stillonrecord.org?subject={d["id"]}%20correction">'
                   'Suggest a correction</a>')
    actions.append('<a href="../index.html">Back to the index</a>')

    tail = (', ' + e(d['country_today'])
            if d['country_today'] and d['country_today'] != d['place_name'] else '')

    body = f"""<main class="page" data-st="{e(st)}">
<p class="crumb"><a href="../index.html">Index</a> / Record {e(d['id'])}</p>
<h1 class="title">{e(d['event_name'])}</h1>
<p class="subtitle"><span class="py">{e(years(d))}</span>, {e(d['place_name'] or '')}{tail}</p>
<p class="statusline">{e(d['category'])}. Tier {e(d['evidence_tier'])},
{e(STATUS.get(st, st).lower())}.</p>

<p class="banner"><b>Seeded, not yet verified.</b> The source below is real and relevant, and
nobody has yet opened it to confirm it says what this record claims. Treat it as a lead until
that happens. <a href="../method.html#verification">How verification works</a></p>

{prose}

<h2>The record</h2>
<dl class="record">
{dl}
</dl>

{lst(children, 'Records under this campaign')}
{lst(siblings, 'Other records in the same campaign')}
{lst(nearby, 'Nearby in ' + e(d['country_today'] or 'the same country'),
     'Proximity only. These are not claimed to be connected.')}

<div class="actions">{''.join(actions)}</div>
</main>
{FOOT}"""
    return shell((f"{d['event_name']} \u2014 Still on Record", ''), body,
                 desc=f"{d['event_name']}, {years(d)}, {d['place_name']}. "
                      f"Tier {d['evidence_tier']}, {STATUS.get(st, st).lower()}.",
                 depth=1)


# ---------------------------------------------------------------- register


def build_register(recs):
    reg = [d for d in recs if d['layer'] == 'register']
    items = '\n'.join(f"""<div class="regitem">
  <h3><a href="record/{d['id']}.html">{e(d['event_name'])}</a></h3>
  <p class="m">{e(years(d))}, {e(d['place_name'] or d['country_today'])}</p>
  <p><span class="lab">Why it cannot be placed:</span> {e(d.get('register_reason', ''))}.</p>
  <p><span class="lab">What would place it:</span> {e(d.get('unlock', ''))}.</p>
</div>""" for d in reg)

    body = f"""<main class="page">
<h1 class="title">The register</h1>
<p class="lead">{len(reg)} events pass the inclusion rule and cannot be tied to a place with a
source. They are not deleted and they are never pinned. Each one is published here with the
reason it cannot be located and the evidence that would unlock it.</p>
<p>Publishing what cannot be proven is part of the method. A map that quietly drops the events
it cannot place looks more complete than it is, and the gaps it hides are exactly where the
archives are closed. Every entry below is an open research question.</p>
<p>If you can supply the missing evidence, the correction channel is
<a href="mailto:corrections@stillonrecord.org">corrections@stillonrecord.org</a>. Include the
record id and the source.</p>

<h2>Entries</h2>
{items}
</main>
{FOOT}"""
    return shell(('The register \u2014 Still on Record', 'register.html'), body,
                 desc='Events that qualify for the map and cannot be located, '
                      'each with the evidence that would place it.')


# ---------------------------------------------------------------- method


def build_method(recs):
    tiers = {t: sum(1 for d in recs if d['evidence_tier'] == t) for t in ('1', '2', '3')}
    basis_rows = '\n'.join(
        f'<li><b>{k.replace("_", " ")}</b> \u2014 {e(v.split(": ", 1)[1])}</li>'
        for k, v in BASIS.items())

    body = f"""<main class="page">
<h1 class="title">Method</h1>
<p class="lead">Every record names the specific document it rests on, states how good that
document is, says whether historians dispute it, and says what kind of number its death
figures are. This page is how those judgments are made.</p>

<h2 id="threshold">What qualifies</h2>
<p>Two tests, and both have to hold.</p>
<ul>
<li><b>Deliberate or knowing.</b> The harm was intended, or it was a foreseen cost that the
actor accepted.</li>
<li><b>Locatable with a source.</b> It can be tied to a place with a citation. If it cannot,
it goes to <a href="register.html">the register</a>, never to deletion.</li>
</ul>
<p>The period floor is {YEAR_FLOOR}. That is a setting, not a research decision, and events
below it are recorded and flagged rather than dropped.</p>
<p>Rome Statute Article 7 is the reference for what counts as a widespread or systematic
attack. Applying it to anything before 1998 is descriptive, not legal, and this site says so
rather than implying a verdict that no court reached.</p>

<h2 id="product-test">The product test</h2>
<p>Where harm comes from a product rather than an attack, two further questions decide what
can be mapped. Did the product deliver substantial real benefit? Was a comparable alternative
available, known, and rejected?</p>
<ul>
<li><b>An alternative existed and was rejected.</b> The harm itself is mappable. Leaded petrol
qualifies, because ethanol worked and could not be patented. So does asbestos, and white
phosphorus in matches.</li>
<li><b>Real benefit, no comparable alternative.</b> Only the concealment is mappable, as
decision and evidence sites. No mortality row. Fossil fuels sit here, and so does most of
pharmaceuticals: the wrong in Vioxx is the buried cardiovascular signal, not the existence of
an anti-inflammatory.</li>
<li><b>No offsetting benefit.</b> Both the harm and the concealment are mappable. Tobacco sits
here.</li>
</ul>
<p>This is why the dataset holds fossil fuel source sites and no fossil fuel death toll.
Mortality from combustion is real and large, and it is not separable from the mortality that
fossil fuels prevented. The concealment is separable, documented and litigated.</p>

<h2 id="tiers">Evidence tiers</h2>
<ul>
<li><b>Tier 1</b> ({tiers['1']} records here) \u2014 a finding of fact by a body with the power
to make one, or a primary record: court and tribunal judgments, truth commissions, state and
perpetrator archives, government inquiries with investigative powers, peer-reviewed demographic
reconstruction.</li>
<li><b>Tier 2</b> ({tiers['2']}) \u2014 academic monographs, NGO reports with published
methodology, archival work without a state mandate. Most historical records sit here
legitimately.</li>
<li><b>Tier 3</b> ({tiers['3']}) \u2014 journalism, survivor testimony standing alone, advocacy.
Tier 3 is for things that are real but thinly evidenced, not for things anyone believes
strongly.</li>
</ul>
<p>A common error is treating a report about a judgment as the judgment. The judgment gets
cited, with the page.</p>

<h2 id="tolls">Death figures</h2>
<p>Never a single number. Every figure is a range with the estimator named and a basis
attached, and the basis says what kind of number it is.</p>
<ul>
{basis_rows}
</ul>
<p><b>These values cannot be added together.</b> Adding an annual epidemiological attribution
to a count of exhumed bodies produces a number that means nothing, which is why this site has
no total, no ranking and no score. Non-fatal harm is recorded separately with a measure
attached, because what is being counted differs by record: people exposed, children with
embryopathy, IQ points lost.</p>

<h2 id="density">Why record density is not severity</h2>
<p>The Holocaust has 44,000 documented sites because the USHMM spent decades cataloguing them.
The Great Leap Forward famine, which killed more people, has a few dozen, because most Chinese
provincial archives have never been opened. A map that ignores this reads as a claim about
history when it is really a claim about record-keeping.</p>
<p>So the dataset carries a completeness field, filled only where an external dataset defines
the answer. Guessing it for unchecked records would repeat the error it exists to prevent.
Where a region looks empty on the map, the first question is which archives are shut.</p>

<h2 id="layers">Layers and pins</h2>
<p>Events are on by default. Source sites, meaning rooms and works where decisions were taken,
are off by default and drawn as a square rather than a circle. A pin on a boardroom must never
read as a pin on a grave. Unlocated records are never pinned at all; they live in the register.</p>
<p>Where several records fall in the same spot at low zoom, one record stands in for the group
and the rest are hidden until you zoom in. The stand-in is chosen by a fixed rule, so the same
view always shows the same record: parent campaign first, then evidence tier, then death
figure, then earliest year. Cluster bubbles with counts were rejected, because a bubble reading
44,000 next to one reading 12 invites exactly the conclusion the completeness field exists to
prevent.</p>

<h2 id="verification">Verification</h2>
<p>The core rule is that nobody cites a source they have not opened. The seed records name
documents that exist and are relevant; they were assembled from research, not from reading each
one end to end. Until someone opens the named document and checks the event, the place, the
dates, the perpetrator and the figure separately, the record carries its seeded state on its
own page.</p>
<p>A correction that moves a record from confirmed to contested is a success, not a defeat.</p>

<h2>Corrections</h2>
<p>Sourced corrections are acted on. Unsourced ones are not argued with. Send the record id,
what is wrong, and the source, to
<a href="mailto:corrections@stillonrecord.org">corrections@stillonrecord.org</a>. Every change
is logged publicly with its date and its origin.</p>
</main>
{FOOT}"""
    return shell(('Method \u2014 Still on Record', 'method.html'), body,
                 desc='Inclusion rules, evidence tiers, how death figures are recorded, '
                      'and why record density is not severity.')


# ---------------------------------------------------------------- about


def build_about(recs):
    n = len(recs)
    located = sum(1 for d in recs if d['lat'] is not None)
    body = f"""<main class="page">
<h1 class="title">About</h1>
<p class="lead">Still on Record is an index of events where people were harmed deliberately, or
where the harm was a foreseen cost that someone accepted. It covers genocide and state killing,
colonial conquest, slavery and forced labour, famine used as a weapon, forced displacement,
religious persecution, institutional abuse, and industrial harm where the producer knew.</p>

<h2>What it is not</h2>
<p>Not a ranking. There is no total, no leaderboard and no score. The categories are not
comparable and the death figures are not summable. Not a verdict either: where proceedings are
live, the record names the case and stops there.</p>

<h2>Status</h2>
<p>Seed stage. This build carries {n} records, of which {located} have coordinates and appear on
the map. The rest are listed and not plotted. Every record names a real and relevant source, and
none of those sources has yet been opened and checked one by one. Coordinates are approximate
and unverified. Records carry their state on their own page. Read it before citing anything
here.</p>

<h2>The name</h2>
<p>These events are still on record. The documents survive, the judgments were handed down, the
registers were kept. Denial works by betting that nobody will go and look. This project goes
and looks, and shows its working.</p>

<h2>Who runs it</h2>
<p>A stichting registered in the Netherlands. Board, policy plan and annual figures are
published. No advertising, no paywall, no sponsored content. Hosting is covered by donations;
research and development work is funded by grants and commissioned projects, and the accounts
are public.</p>

<h2>Licence</h2>
<p>Data under the Open Database License, text and documentation under CC BY-SA 4.0. Free for
any use, including commercial, with attribution and share-alike. If you build on it, the result
stays open. The whole dataset is
<a href="data/dataset.csv">one file you can download</a>, and every record is also available as
JSON.</p>

<h2>Credit where it is owed</h2>
<p>This project exists because gulag.online showed it could be done. It depends on the work of
Memorial, the USHMM, DC-Cam, the University of Newcastle, SlaveVoyages, the UCSF Industry
Documents Library, ToxicDocs, and the truth commissions and tribunals whose findings make most
of these records possible.</p>
<p>Basemap tiles from <a href="https://openfreemap.org">OpenFreeMap</a>, schema by
<a href="https://www.openmaptiles.org/">OpenMapTiles</a>, data by
<a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors.</p>

<h2>Corrections</h2>
<p>Sourced corrections are acted on and logged publicly.
<a href="mailto:corrections@stillonrecord.org">corrections@stillonrecord.org</a></p>
</main>
{FOOT}"""
    return shell(('About \u2014 Still on Record', 'about.html'), body)


# ---------------------------------------------------------------- artifacts


def write_artifacts(recs):
    d_out = os.path.join(OUT, 'data')
    os.makedirs(os.path.join(d_out, 'entries'), exist_ok=True)

    features = []
    for d in recs:
        if d['lat'] is None:
            continue
        features.append({
            'type': 'Feature',
            'geometry': {'type': 'Point', 'coordinates': [d['lon'], d['lat']]},
            'properties': {'id': d['id'], 'name': d['event_name'], 'sy': d['sy'], 'ey': d['ey'],
                           'status': d['status'], 'tier': d['evidence_tier'],
                           'layer': d['layer'], 'role': d['site_role'],
                           'geometry_type': d['geometry_type'],
                           'parent': d['parent_campaign'] or None,
                           'deaths_high': d['deaths_high'] or d['deaths_low'] or None}
        })
    with open(os.path.join(d_out, 'points.geojson'), 'w', encoding='utf-8') as f:
        json.dump({'type': 'FeatureCollection', 'features': features}, f,
                  separators=(',', ':'), ensure_ascii=False)

    search = [{'id': d['id'], 'n': d['event_name'], 'p': d['place_name'],
               'c': d['country_today'], 'y': d['sy']} for d in recs]
    with open(os.path.join(d_out, 'search.json'), 'w', encoding='utf-8') as f:
        json.dump(search, f, separators=(',', ':'), ensure_ascii=False)

    for d in recs:
        rec = {k: v for k, v in d.items() if v not in ('', None)}
        with open(os.path.join(d_out, 'entries', d['id'] + '.json'), 'w', encoding='utf-8') as f:
            json.dump(rec, f, indent=1, ensure_ascii=False)

    shutil.copyfile(SOURCE, os.path.join(d_out, 'dataset.csv'))


# ---------------------------------------------------------------- main


def main():
    print(f'source:   {SOURCE}')
    print(f'register: {REGISTER}')
    print(f'assets:   {ASSETS}')
    print(f'output:   {OUT}')

    recs = load()
    errors = validate(recs)
    if errors:
        print(f'\nSchema validation failed, {len(errors)} problems:')
        for x in errors:
            print('  ' + x)
        sys.exit(1)

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, 'record'), exist_ok=True)
    shutil.copytree(ASSETS, os.path.join(OUT, 'assets'))

    pages = {'index.html': build_index(recs),
             'register.html': build_register(recs),
             'method.html': build_method(recs),
             'about.html': build_about(recs)}
    for name, content in pages.items():
        with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f:
            f.write(content)

    for d in recs:
        with open(os.path.join(OUT, 'record', d['id'] + '.html'), 'w', encoding='utf-8') as f:
            f.write(build_record(d, recs))

    write_artifacts(recs)

    located = sum(1 for d in recs if d['lat'] is not None)
    print(f'\n{len(recs)} records, {located} located, {len(recs) - located} not plotted')
    print(f'{len(pages)} pages + {len(recs)} record pages -> {OUT}')


if __name__ == '__main__':
    main()
