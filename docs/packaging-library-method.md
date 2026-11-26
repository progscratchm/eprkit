# Packaging library: method

`data/packaging-library.csv` holds 100 common stock packaging components used by DTC brands, each with a weight, SPDC-style material fields and the California (CalRecycle ID) and Oregon/Colorado category it reports under. Regenerate with `python3 scripts/build_library.py`.

## Coverage (100 entries)

| Group | Entries |
| --- | --- |
| Poly mailers, 8 sizes x 2.0 / 2.5 / 3.0 mil | 24 |
| Self-seal poly bags, 6 sizes x 1.5 / 2.0 mil | 12 |
| RSC shipping boxes, 32 ECT C-flute | 18 |
| E-flute mailer boxes | 10 |
| Kraft void fill, crinkle fill, air pillows | 10 |
| Tape (BOPP and water-activated kraft) | 6 |
| Tissue, label, packing slip, glassine bags | 8 |
| Kraft paper mailers, folding cartons, corrugated pads, wrapping sheets | 12 |

Primary containers (glass and plastic bottles, jars, closures, pumps) are not included yet: their weights vary too much by mould to calculate, so they need published supplier specs.

## How weights are calculated

Weights are calculated from dimensions and standard material specs, not weighed. Every row says how in `weight_method` and `weight_basis`.

| Material | Assumption |
| --- | --- |
| LDPE film | 0.92 g/cm3; mailers and bags are 2 plies plus a 1.5 in lip |
| HDPE film (air pillows) | 0.95 g/cm3, 2 plies |
| BOPP tape | 0.905 g/cm3 film plus adhesive at 1.0 g/cm3 (assumed) |
| 32 ECT C-flute board | 110 lb/MSF combined (537 g/m2) |
| E-flute board | 42/26/42 with take-up factor 1.25 (569 g/m2) |
| RSC blank | (2 x (L + W) + 1.5 in glue flap) x (H + W), inside dimensions |
| Kraft paper | Basis weight per 3,000 sq ft ream: 30 lb = 48.8 g/m2 |
| Tissue | 10 lb on a 24 x 36 x 480 ream = 16.9 g/m2 |
| SBS 18 pt | About 290 g/m2 |

Rows marked "approximate" (mailer boxes, folding cartons, label, water-activated tape, kraft paper mailers) use estimated blank areas or grades and could be off by around 20%.

## Validation

| Check | Calculated | Published |
| --- | --- | --- |
| Poly mailer 10 x 13 in, 2.5 mil | 10.4 g | About 11.8 g each (26 lb per case of 1,000 including carton), [International Plastics PM1013](https://www.interplas.com/10-x-13-poly-mailer-p-pm1013) |
| C-flute box 575 x 385 x 225 mm, 175/140/175 g/m2 | 658 g | 650 g, [FEFCO](https://www.fefco.org/node/1588) |

Constants: 32 ECT combined board weight from a corrugated grade table ([Richbox](https://www.scribd.com/document/362321722/Www-Richbox-Com)); C-flute take-up factor 1.44 from the [EPA](https://www.epa.gov/node/137737).

## Category mapping notes

- California IDs come from `data/ca-cmc-2026.csv`, Oregon/Colorado IDs from `data/or-co-categories.csv`.
- Plastic items carry `ca_plastic_components` (count per entry) and `ca_plastic_weight_g`.
- Open questions flagged in `mapping_note`: whether plastic tape and labels make a box "w/ plastic component" in California, and whether a packing slip counts as packaging in California.
- A brand should confirm weights for its own SKUs on a scale before filing; the library is a starting point that removes most data entry.
