# Packaging library: method

`data/packaging-library.csv` holds 149 common stock packaging components used by DTC brands, each with a weight, SPDC-style material fields and the California (CalRecycle ID) and Oregon/Colorado category it reports under. Regenerate with `python3 scripts/build_library.py`.

## Coverage (149 entries)

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
| Glass Boston rounds (1, 4, 8, 16 oz amber) and straight-sided jars | 7 |
| PET and HDPE bottles, supplement packers | 9 |
| Snap-top cap, lotion pumps | 4 |
| LDPE squeeze tubes with flip cap | 3 |
| Stand-up pouches (kraft/foil/LLDPE, PET/LLDPE) | 3 |
| Tinplate candle and screw-top tins | 5 |
| Rigid two-piece gift boxes | 2 |

## Primary packaging (added Nov 28, 2026)

Rigid containers can't be calculated from dimensions because wall thickness varies by mould. Their weights are the gram weight a supplier publishes for one stock item (`weight_method = published`), with the supplier and part number in `weight_basis`. Two exceptions are calculated: tins (0.22 mm tinplate, gauge assumed) and rigid gift boxes (1.5 mm chipboard). Pouch weights are case weight / 1,000 and include the carton share, so they run slightly high.

Rules applied:

- **Small format.** CalRecycle's "Small" categories apply when two or more sides are 2 in or less. A round bottle of 2 in diameter or less qualifies (width and depth). Caps and pumps are small format (25_P47P; OR/CO 58). Tins are wider than 2 in, so they are not.
- **Glass** is "w/o plastic component" only with a paper label or no label. A plastic label or shrink band moves it to the "w/ plastic" category. The cap is always a separate row.
- **Kraft pouches** report under paper (25_PF7P / OR/CO 23) because kraft is the majority material. The plastic share is estimated at 40% and must be confirmed with the supplier.
- **Pumps** usually have a steel spring. It stays with the pump.

Gaps not yet covered: PP screw caps without a published weight (20-410 to 89-400), metal jar lids, droppers, fine-mist sprayers, shrink bands, aluminum bottles and aerosol cans. Map these from the brand's supplier spec or a weighed sample.

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

## Added Nov 28, 2026 (PKG-134 to PKG-145): gaps for the first outreach brands
- **Dropper assemblies** are split into three lines (glass pipette, PP collar, rubber bulb). The total (6.06 g) is a published case weight per unit; the split between parts is our estimate. Bulbs are treated as plastic, the cautious reading.
- **Coffee bags with a valve** are plastic-majority by weight (~64% from a published kraft/LDPE/met PET/LLDPE layer spec), so they map to Multi-Material Laminate - Pouches, not paper. Note this differs from the kraft stand-up pouches (PKG-121/122), which assume kraft is the majority: check each brand's layer spec.
- **Ceramic candle vessels** are calculated from published dimensions (+/-25%): weigh one empty vessel.
- **Aluminium aerosol can** (22.9 g, published). The valve and actuator are its plastic components; their weight must come from the filler.
- **Stick container** (2.5 oz PP twist-up), **snack bar flow wrap**, **chocolate bar foil and sleeve**: published or calculated as noted on each line.
