# Inclusion rules

## Threshold
An entry qualifies if both hold:

1. **Deliberate or knowing.** The harm was intended, or was a foreseen cost the actor accepted.
2. **Locatable with a source.** It can be tied to a place with a citation. If it cannot, it goes to the unmapped register, not to deletion.

Period floor: 1500. Stored as a setting, not a research decision. Events below it are recorded and flagged.

Rome Statute Article 7 is the reference for what counts as a widespread or systematic attack. Applying it before 1998 is descriptive, not legal. The site must say so.

## The product test
Where the harm comes from a product or technology rather than an attack, two further questions decide what is mappable.

1. Did it deliver substantial real benefit?
2. Was a comparable alternative available, known, and rejected?

**Alternative existed and was rejected.** The harm itself is mappable. Leaded petrol qualifies: ethanol worked and could not be patented. Asbestos qualifies. White phosphorus in matches qualifies: red phosphorus worked and cost more.

**Real benefit, no comparable alternative.** The product itself is not mappable. Concealment is mappable only where it caused direct harm to people. Most of pharmaceuticals sits here: the wrong in Vioxx is the buried cardiovascular signal, not the existence of an anti-inflammatory, and its patients can be counted. Fossil fuels also sit here and are not mapped at all: the harm from concealing climate science is real but global and indirect, with no people or place it can be tied to.

**No offsetting benefit.** Both the harm and the concealment are mappable. Tobacco sits here.

This test is why the file contains no fossil fuel records. Mortality from combustion is real and large, and it is not separable from the mortality that fossil fuels prevented.

## Toll recording
Never store a single number. Store a range with the estimator named, and a `toll_basis` saying what kind of number it is:

- `counted` — bodies named, exhumed, or in a perpetrator's own register
- `documented_estimate` — historians or commissions working from records
- `excess_mortality` — modelled against a counterfactual, cumulative
- `attributable_annual` — epidemiological attribution, per year
- `not_quantified` — harm real, no defensible figure exists

Non-fatal harm goes in `affected_low` / `affected_high` with `affected_measure` saying what is being counted. Anything weighting pins by size must read `toll_basis` first, or the diffuse harms render as zero.

## Site roles
`victim_site`, `perpetrator_site`, `decision_site`, `evidence_site`, `burial_site`. Source sites are a separate layer, shown by default and drawn as squares. A pin on a boardroom must never read as a pin on a grave.
