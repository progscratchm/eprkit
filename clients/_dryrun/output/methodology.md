# Packaging EPR methodology: _dryrun

Prepared by EPR Kit for the 2027 filing season (calendar year 2026 supply). Every figure in the attached reports can be traced in working.csv to a product, a packaging item, a weight source and a count of units.

## 1. Data we used

- `orders-amazon.csv`
- `orders-shopify.csv`

Units are counted by the state in the shipping address. We excluded or set aside:

- Cancelled or refunded: 263 units
- Sku not in packaging list: 157 units (set aside for review)
- Ships outside the us: 80 units
- Ship-to state missing or unknown: 33 units (set aside for review)
- Zero or negative quantity: 1 units

Units marked "needs review" were resolved with you before delivery, or are explained in section 6.

## 2. Units by state

| State | Units |
| --- | ---: |
| CA | 4,006 |
| OR | 454 |
| CO | 552 |
| MN | 302 |
| MD | 309 |
| WA | 592 |

## 3. Packaging per product

Per-unit items are counted once for each unit sold. Each order uses one shipping set: the heaviest set among the products in it. When an order holds more units than fit in one package, the whole set repeats for each package.

| SKU | Level | Component | Qty | Units per package | Weight (g) | CA category | OR/CO # | Weight source |
| --- | --- | --- | ---: | ---: | ---: | --- | --- | --- |
| BUNDLE-TEE3 | unit | Self-seal poly bag 9x12 in, 1.5 mil | 3 |  | 5.2 | 25_P16P | 53 | library PKG-029: calculated |
| GIFT-01 | unit | Folding carton 6x4x2 in, 18 pt SBS | 1 |  | 44.3 | 25_PF10N | 21 | library PKG-096: calculated (approximate, +/-20%) |
| GIFT-01 | unit | Tissue paper 20x30 in, 1 sheet | 1 |  | 6.6 | 25_PF12N | 24 | library PKG-081: calculated |
| GIFT-01 | unit | Branded hang tag with cotton string | 1 |  | 3.2 | 25_PF12N | 24 | client weighed 10 tags on 2027-01-08: 32 g |
| HOOD-01 | unit | Self-seal poly bag 12x15 in, 2.0 mil | 1 |  | 11.4 | 25_P16P | 53 | library PKG-034: calculated |
| TEE-01 | unit | Self-seal poly bag 9x12 in, 1.5 mil | 1 |  | 5.2 | 25_P16P | 53 | library PKG-029: calculated |
| BUNDLE-TEE3 | order | Poly mailer 14.5x19 in, 2.5 mil | 1 |  | 21.6 | 25_P16P | 53 | library PKG-017: calculated |
| BUNDLE-TEE3 | order | Shipping label 4x6 in, direct thermal | 1 |  | 1.5 | 25_PF12N | 24 | library PKG-084: calculated (approximate) |
| GIFT-01 | order | Shipping box RSC 10x8x6 in, 32 ECT | 1 | 2 | 181.9 | 25_PF9N | 19 | library PKG-041: calculated |
| GIFT-01 | order | Kraft paper void fill, 15 in roll x 3 ft | 1 | 2 | 17 | 25_PF1N | 18 | library PKG-065: calculated |
| GIFT-01 | order | Packing tape 2 in, 2.0 mil, 3 ft | 1 | 2 | 2.2 | 25_P22P | 55 | library PKG-078: calculated |
| GIFT-01 | order | Shipping label 4x6 in, direct thermal | 1 |  | 1.5 | 25_PF12N | 24 | library PKG-084: calculated (approximate) |
| GIFT-01 | order | Packing slip 8.5x11 in, 20 lb bond | 1 |  | 4.5 | 25_PF11N | 4 | library PKG-085: calculated |
| HOOD-01 | order | Poly mailer 14.5x19 in, 2.5 mil | 1 | 3 | 21.6 | 25_P16P | 53 | library PKG-017: calculated |
| HOOD-01 | order | Shipping label 4x6 in, direct thermal | 1 |  | 1.5 | 25_PF12N | 24 | library PKG-084: calculated (approximate) |
| TEE-01 | order | Poly mailer 10x13 in, 2.5 mil | 1 | 4 | 10.4 | 25_P16P | 53 | library PKG-011: calculated |
| TEE-01 | order | Shipping label 4x6 in, direct thermal | 1 |  | 1.5 | 25_PF12N | 24 | library PKG-084: calculated (approximate) |

## 4. Calculations and checks

- Weights are summed in grams per category and state, converted at 453.59237 g per lb and rounded to two decimals once, at the end.
- California: plastic component weight and count are reported for every category that requires them. Each separate plastic piece counts as one component.
- Oregon and Colorado: weights by the 60 Oregon/Colorado categories.
- Minnesota, Maryland and Washington: CAA's 8 simplified categories, from each item's Oregon/Colorado material class.
- Before delivery we check the California rules the portal enforces: plastic weight and count present where required, plastic weight never above total, plastic at or under 50% in non-plastic categories, two decimals for weights and whole numbers for counts. Results are in checks.txt.

## 5. Totals delivered

- California: 426.22 lbs
- Oregon: 45.57 lbs
- Colorado: 55.00 lbs
- MN: 30.37 lbs
- MD: 30.55 lbs
- WA: 61.19 lbs

## 6. Judgment calls and open items

[Fill in before delivery: anything estimated, any SKU resolved by phone, and anything you should raise with counsel, such as whether you are the producer for a product.]

This methodology explains our calculations. It is not legal advice on what you are obliged to report.
