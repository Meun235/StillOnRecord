#!/usr/bin/env python3
"""Still on Record — build script.

    CSV in git  ->  this script  ->  static files  ->  CDN

Finds its inputs at the repo root or inside site/, and always writes to dist/.

    python3 build.py

No dependencies beyond the standard library. Run it in CI on push; a failing
validation should fail the build.
"""

import csv, json, html, os, re, shutil, sys
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

DOMAIN = 'stillonrecord.org'   # written to dist/CNAME on every build
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

LICENCES = {'own', 'public_domain', 'cc0', 'cc_by', 'cc_by_sa', 'permission'}

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
        if d.get('image_file'):
            for f2 in ('image_caption', 'image_credit', 'image_licence'):
                if not d.get(f2):
                    errors.append(f'{i}: image present with no {f2}')
            if d.get('image_licence') and d['image_licence'] not in LICENCES:
                errors.append(f'{i}: image_licence "{d["image_licence"]}" not recognised')
            if d.get('image_tier') not in ('A', 'B', 'C'):
                errors.append(f'{i}: image_tier must be A, B or C, see image policy')
            if d.get('image_tier') == 'C' and not d.get('image_warning'):
                errors.append(f'{i}: tier C image with no image_warning line')
        if d.get('quote') and not d.get('quote_source'):
            errors.append(f'{i}: quote present with no quote_source')
        if d.get('quote') and not d.get('quote_speaker'):
            errors.append(f'{i}: quote present with no quote_speaker')
        if d.get('quote') and len(d['quote'].split()) > 45:
            errors.append(f'{i}: quote is {len(d["quote"].split())} words, keep it short')
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
<br><a href="method.html">Method</a> \u00b7 <a href="rules.html">Inclusion rules</a>
\u00b7 <a href="images.html">Image policy</a> \u00b7 <a href="register.html">Register</a>
<br>Seed stage: records name their sources, and those sources have not yet been opened and
checked one by one. Coordinates are approximate and unverified. Not for citation.
</div></footer>"""


# ---------------------------------------------------------------- map page


def build_index(recs):
    fields = ('id event_name parent_campaign layer geometry_type site_role place_name '
              'country_today perpetrator perpetrator_today succession_type target_group '
              'category deaths_low deaths_high toll_basis affected_low affected_high '
              'affected_measure toll_note evidence_tier status documentation_completeness '
              'key_source notes quote quote_speaker quote_source '
              'register_reason unlock').split()
    slim = []
    for d in recs:
        o = {k: d[k] for k in fields if d.get(k)}
        o['sy'], o['ey'] = d['sy'], d['ey']
        if d['lat'] is not None:
            o['lat'], o['lon'] = d['lat'], d['lon']
        slim.append(o)

    located = sum(1 for d in recs if d['lat'] is not None)
    unver = sum(1 for d in recs if d.get('coord_source') == 'unverified_ai'
                or d.get('coord_source') == 'fixture_dev')

    body = f"""
<div class="caveat">
  <span><b>Work in progress. Nothing here is verified yet.</b>
  {len(recs)} records are seeded and each one names a real, relevant source, but nobody has
  yet opened those sources to confirm they say what the record claims. {located} records carry
  coordinates and {unver} of those are unchecked, placed from general knowledge rather than a
  gazetteer. Verification and geocoding are the work of the coming weeks, and records will
  carry their state on their own page as it changes. Use this as a research lead, not a
  citation.</span>
  <a href="method.html#verification">How verification works</a>
</div>

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
      <button class="mapmsg-x" id="mapmsg-x" aria-label="Dismiss">\u00d7</button>
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
    if d.get('image_file'):
        cred = (f'<span class="credit">{e(d["image_credit"])}'
                f' \u00b7 {e(d["image_licence"].replace("_", " "))}</span>')
        img = (f'<img src="../{e(d["image_file"])}" alt="{e(d["image_caption"])}" loading="lazy">')
        if d.get('image_tier') == 'C':
            prose += (f'<figure class="rec-img graphic">'
                      f'<details><summary>{e(d["image_warning"])}'
                      '<span class="show">Show image</span></summary>'
                      f'{img}</details>'
                      f'<figcaption>{e(d["image_caption"])}{cred}</figcaption></figure>')
        else:
            prose += (f'<figure class="rec-img">{img}'
                      f'<figcaption>{e(d["image_caption"])}{cred}</figcaption></figure>')
    if d.get('quote'):
        sp = e(d['quote_speaker']) if d.get('quote_speaker') else 'Unattributed'
        src = f'<span class="qsrc">{e(d["quote_source"])}</span>' if d.get('quote_source') else ''
        prose += ('<blockquote class="testimony">'
                  f'<p>{e(d["quote"])}</p>'
                  f'<footer>{sp}{src}</footer></blockquote>')
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
        f'<li><b>{k.replace("_", " ").capitalize()}.</b> {e(v.split(": ", 1)[1])}</li>'
        for k, v in BASIS.items())

    body = f"""<main class="page">
<h1 class="title">Method</h1>
<p class="lead">Every record names the document it rests on. It says how good that document is,
whether historians argue about it, and what kind of number its death figures are. This page is
how those calls get made.</p>

<h2 id="threshold">What qualifies</h2>
<p>Two tests, and both have to hold. The harm was deliberate, or it was a cost somebody foresaw
and accepted anyway. And it can be tied to a place with a citation.</p>
<p>When the second test fails the event isn't dropped. It goes to
<a href="register.html">the register</a>, where it sits with a note saying what evidence would
place it.</p>
<p>The period starts at {YEAR_FLOOR}. That's a setting in a configuration file rather than a
claim about history, and anything earlier gets recorded and flagged instead of thrown away.</p>
<p>For what counts as a widespread or systematic attack, the reference is Article 7 of the Rome
Statute. Using it on anything before 1998 is description, not law. This site says so out loud,
because the alternative is implying a verdict that no court ever reached.</p>

<h2 id="product-test">Harm that comes from a product</h2>
<p>Some of this isn't an attack at all. It's a thing that was made and sold. Two more questions
sort those out. Did the product do real good? And was there a comparable alternative that
somebody knew about and turned down?</p>
<p>Leaded petrol fails the second question badly. Ethanol worked as an anti-knock agent and
nobody could patent it, which is the whole reason tetraethyl lead won. So the harm itself is on
the map, and so is the laboratory in Dayton where the choice was made.</p>
<p>Fossil fuels pass both questions. Roughly half the world eats because of nitrogen fixed with
natural gas, and for most of the twentieth century there was nothing else. So combustion isn't
mapped here. The concealment is: the research the industry commissioned and shelved, the
coalition whose own scientific advisers wrote that the greenhouse effect couldn't be refuted
before that passage was cut, the communications plan that set out to make uncertainty
conventional wisdom. Most of pharmaceuticals belongs in this group too. The wrong in Vioxx was
the buried cardiovascular signal, not the existence of a painkiller.</p>
<p>Tobacco has nothing on the other side of the ledger, so both the harm and the concealment
are here.</p>

<h2 id="tiers">How good is the source</h2>
<p>Three tiers, and they're about the kind of document rather than how much anyone trusts it.</p>
<ul>
<li><b>Tier 1.</b> {tiers['1']} records. A finding of fact by a body with the power to make one,
or a primary record. Court and tribunal judgments, truth commissions, state and perpetrator
archives, inquiries with investigative powers, peer-reviewed demography.</li>
<li><b>Tier 2.</b> {tiers['2']} records. Academic monographs, NGO reports that publish their
method, archival work without a state mandate. Plenty of solid history lives here.</li>
<li><b>Tier 3.</b> {tiers['3']} records. Journalism, testimony standing on its own, advocacy.
This tier is for things that are real but thinly evidenced. It isn't for things somebody
believes strongly.</li>
</ul>
<p>The commonest mistake is citing an article about a judgment instead of the judgment. Cite
the judgment, with the page.</p>

<h2 id="tolls">Death figures</h2>
<p>Never one number. Every figure is a range, the estimator is named, and a basis says what
kind of number you're looking at.</p>
<ul>
{basis_rows}
</ul>
<p>You can't add these together. An annual epidemiological attribution and a count of exhumed
bodies are different objects, and summing them produces nothing. That's why this site has no
total, no ranking and no score, and why it never will.</p>
<p>Harm that isn't death gets recorded separately, with a note saying what's being counted.
People exposed, children born with thalidomide embryopathy, IQ points lost across a population.
The unit changes from record to record, so the unit is always shown.</p>

<h2 id="density">Why a crowded map isn't a worse place</h2>
<p>The Holocaust has 44,000 documented sites. That's because the United States Holocaust
Memorial Museum spent decades cataloguing them, and the number reflects the cataloguing.</p>
<p>The Great Leap Forward famine killed more people and has a few dozen. Most Chinese
provincial archives have never been opened.</p>
<p>Put those two on the same map without saying anything and it reads as a claim about history
when it's really a claim about record-keeping. So every record carries a completeness field,
filled in only where an external dataset settles the question. Guessing it for the rest would
repeat the exact error the field exists to catch. When a region looks empty here, the first
question to ask is which archives are shut.</p>

<h2 id="layers">Pins</h2>
<p>Events are on by default. Source sites are off. Those are the rooms and works where
decisions were taken, and they're drawn as squares rather than circles, because a pin on a
boardroom must never read as a pin on a grave. Records with no location aren't pinned at all.
They're in the register.</p>
<p>Where several records land on the same spot at low zoom, one stands in for the group and the
others stay hidden until you zoom in. A fixed rule picks the stand-in, so the same view always
shows you the same record: parent campaign first, then evidence tier, then death figure, then
earliest year.</p>
<p>Cluster bubbles with counts were rejected. A bubble reading 44,000 next to one reading 12
invites precisely the conclusion the completeness field exists to prevent.</p>

<h2 id="verification">Verification</h2>
<p>Nobody cites a source they haven't opened. That's the rule the whole project rests on.</p>
<p>The seeded records name documents that exist and are relevant, but they were assembled from
research rather than from reading each one end to end. Until somebody opens the named document
and checks the event, the place, the dates, the perpetrator and the figure separately, the
record says so on its own page.</p>
<p>A correction that moves a record from confirmed to contested is a good day, not a bad one.</p>

<h2 id="images">Images</h2>
<p>Images go up where they document something the record needs. Scale, conditions, method, the
state of a place. Difficulty isn't the test, purpose is.</p>
<p>Photographs of the dead, of injury, of killing in progress: published, where they meet that
test, behind a control that tells you what you're about to see. They never turn up on the map,
in a preview or in a search result, so nobody arrives at one by accident. What's refused
outright, and why, is on the <a href="images.html">image policy</a> page.</p>

<h2>Corrections</h2>
<p>Sourced corrections get acted on. Unsourced ones don't get argued with. Send the record id,
what's wrong, and the source, to
<a href="mailto:corrections@stillonrecord.org">corrections@stillonrecord.org</a>. Every change
is logged in public with its date and where it came from.</p>
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
<p class="lead">Still on Record is an index of events where people were harmed on purpose, or
where somebody worked out the harm in advance and went ahead anyway.</p>

<p>That covers a lot of ground. Genocide and state killing. Colonial conquest. Slavery and
forced labour. Famine used as a weapon. Forced displacement, religious persecution,
institutional abuse. And industrial harm, where the company knew and kept going, which turns
out to be one of the best documented categories of all, because discovery forces the internal
memos into the public record.</p>

<h2>What it isn't</h2>
<p>It isn't a ranking. There's no total and no score, and there won't be. The categories don't
compare and the death figures can't be added up, for reasons the <a href="method.html#tolls">
method page</a> goes into.</p>
<p>It isn't a verdict either. Where proceedings are live, the record names the case and stops
there.</p>

<h2>Where it's up to</h2>
<p>Seed stage, and honestly so. There are {n} records here, {located} of them with coordinates.
Every one names a real and relevant source. Not one of those sources has yet been opened and
checked line by line, and the coordinates were placed from general knowledge rather than a
gazetteer.</p>
<p>Records carry their own state on their own page. Read it before you cite anything. The work
of the coming months is verification, and the site will say so until it's done.</p>

<h2>The name</h2>
<p>These events are still on record. The documents survived. The judgments were handed down,
the registers were kept, the photographs were taken. Denial works by betting that nobody will
go and look.</p>
<p>So this goes and looks, and shows its working.</p>

<h2>Who runs it</h2>
<p>A stichting registered in the Netherlands. The board, the policy plan and the annual figures
are published.</p>
<p>No advertising, no paywall, nothing sponsored. Donations cover the hosting, which is close
to nothing because the site is static files. Research and development are funded by grants and
commissioned work, and the accounts are public. If you want to know who pays for this, the
answer is on the page rather than in an email.</p>

<h2>Licence</h2>
<p>The data is under the Open Database License and the text under CC BY-SA 4.0. Use it for
anything, including commercially. Credit it, and keep whatever you build from it open.</p>
<p>The whole dataset is <a href="data/dataset.csv">a single file you can download</a>, and
every record is also there as JSON.</p>

<h2>Standing on other people's work</h2>
<p>This exists because gulag.online showed it could be done.</p>
<p>It leans on Memorial, the United States Holocaust Memorial Museum, the Documentation Center
of Cambodia, the University of Newcastle's frontier massacre project, SlaveVoyages, the UCSF
Industry Documents Library and ToxicDocs. Above all it leans on the truth commissions and the
tribunals, whose findings are what make most of these records possible at all.</p>
<p>Basemap tiles come from <a href="https://openfreemap.org">OpenFreeMap</a>, the schema from
<a href="https://www.openmaptiles.org/">OpenMapTiles</a>, and the underlying data from
<a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors.</p>

<h2>Corrections</h2>
<p>Sourced corrections get acted on and logged in public.
<a href="mailto:corrections@stillonrecord.org">corrections@stillonrecord.org</a></p>
</main>
{FOOT}"""
    return shell(('About \u2014 Still on Record', 'about.html'), body)


# ---------------------------------------------------------------- policy pages


def md_to_html(text):
    """Minimal markdown: headings, tables, lists, bold, italic, code, links, rules."""
    out, para, rows = [], [], []

    def flush_para():
        if para:
            out.append('<p>' + inline(' '.join(para)) + '</p>')
            para.clear()

    def flush_table():
        if not rows:
            return
        head, body = rows[0], [r for r in rows[1:] if not set(r) <= set('-: ')]
        out.append('<table><thead><tr>' +
                   ''.join(f'<th>{inline(c)}</th>' for c in head) + '</tr></thead><tbody>' +
                   ''.join('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>'
                           for r in body) + '</tbody></table>')
        rows.clear()

    def inline(t):
        t = e(t)
        t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
        t = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', t)
        t = re.sub(r'(?<![*\w])\*([^*]+)\*(?!\w)', r'<em>\1</em>', t)
        t = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', t)
        return t

    lines = text.split('\n')
    i, in_list = 0, False
    while i < len(lines):
        ln = lines[i].rstrip()
        if ln.startswith('|'):
            flush_para()
            rows.append([c.strip() for c in ln.strip('|').split('|')])
            i += 1
            continue
        flush_table()
        if not ln.strip():
            flush_para()
            if in_list:
                out.append('</ul>')
                in_list = False
        elif ln.startswith('#'):
            flush_para()
            if in_list:
                out.append('</ul>')
                in_list = False
            lvl = len(ln) - len(ln.lstrip('#'))
            out.append(f'<h{min(lvl + 1, 4)}>{inline(ln.lstrip("# ").strip())}</h{min(lvl + 1, 4)}>')
        elif ln.strip() in ('---', '***'):
            flush_para()
            if in_list:
                out.append('</ul>')
                in_list = False
            out.append('<hr>')
        elif ln.lstrip().startswith(('- ', '* ')):
            flush_para()
            if not in_list:
                out.append('<ul>')
                in_list = True
            out.append('<li>' + inline(ln.lstrip()[2:]) + '</li>')
        else:
            if in_list:
                out.append('</ul>')
                in_list = False
            para.append(ln.strip())
        i += 1
    flush_para()
    flush_table()
    if in_list:
        out.append('</ul>')
    return '\n'.join(out)


def build_policy(title, path, lead):
    """Render a markdown document from docs/ as a site page."""
    src = None
    for base in (ROOT, os.path.join(ROOT, 'site')):
        cand = os.path.join(base, 'docs', path)
        if os.path.exists(cand):
            src = cand
            break
    if src is None:
        return None
    with open(src, encoding='utf-8') as f:
        text = f.read()
    text = re.sub(r'^#[^#\n]*\n', '', text, count=1)   # drop the H1, the page has its own
    body = (f'<main class="page policy">\n<h1 class="title">{e(title)}</h1>\n'
            f'<p class="lead">{e(lead)}</p>\n{md_to_html(text)}\n</main>\n{FOOT}')
    return shell((f'{title} \u2014 Still on Record', ''), body, desc=lead)


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
    for base in (ROOT, os.path.join(ROOT, 'site')):
        img = os.path.join(base, 'images')
        if os.path.isdir(img):
            shutil.copytree(img, os.path.join(OUT, 'images'))
            break

    pages = {'index.html': build_index(recs),
             'register.html': build_register(recs),
             'method.html': build_method(recs),
             'about.html': build_about(recs)}

    extras = [
        ('images.html', 'Image policy', 'image_policy.md',
         'What may be published, what sits behind a click, and what is refused.'),
        ('rules.html', 'Inclusion rules', 'inclusion_rules.md',
         'The threshold an event has to meet, and how harm from a product is handled.'),
    ]
    for fname, title, doc, lead in extras:
        page = build_policy(title, doc, lead)
        if page:
            pages[fname] = page
        else:
            print(f'  note: docs/{doc} not found, {fname} not generated')
    for name, content in pages.items():
        with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f:
            f.write(content)

    for d in recs:
        with open(os.path.join(OUT, 'record', d['id'] + '.html'), 'w', encoding='utf-8') as f:
            f.write(build_record(d, recs))

    with open(os.path.join(OUT, 'CNAME'), 'w', encoding='utf-8') as f:
        f.write(DOMAIN + '\n')

    write_artifacts(recs)

    located = sum(1 for d in recs if d['lat'] is not None)
    print(f'\n{len(recs)} records, {located} located, {len(recs) - located} not plotted')
    print(f'{len(pages)} pages + {len(recs)} record pages -> {OUT}')


if __name__ == '__main__':
    main()
