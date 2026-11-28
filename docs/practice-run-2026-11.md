# Practice run, November 28, 2026

A full run on a made-up brand, "Juniper & Moss" (clean skincare, Shopify, Portland OR): 48 variants, 23,320 orders in
2026 in Shopify's own export format, with the mess real stores have. Regenerate: `python3 scripts/make_practice.py`,
pre-fill, `python3 clients/_practice/simulate_brand.py`, then `python3 scripts/build_reports.py clients/_practice`.

## Result

All portal checks pass. 80 units (0.1%) left for review: orders with no state at all.
California 3,935 lbs, Oregon 1,459 lbs, Colorado 396 lbs, plus the three simplified reports.

## What broke, and what we fixed

| Problem | Effect before | Fix |
| --- | --- | --- |
| Small plastic (caps, pumps, dropper collars, OR/CO #58) had no simplified category | Every MN/MD/WA report failed its checks for any brand with caps or pumps | Mapped to Rigid Plastic |
| Gift sets and kits | No guess; their contents' packaging was not counted | `bundles.csv`: a set counts its gift box plus every product inside |
| Wholesale orders through Shopify | Cases of 48 units got 12 consumer mailers each: Oregon came out 500 lbs too heavy | Orders tagged "wholesale" use a `_WHOLESALE` case-box set; the build warns if it's missing |
| Local pickup orders | No state, set aside | Counted in the pickup state from `client.json`, no shipping packaging |
| Orders refunded after they shipped | Excluded, though the packaging went out | Included and explained in the methodology |
| Gift cards | Flagged as unknown SKU | Lines that don't ship are excluded |
| Free samples | Not in the product export | Library sachet item; brand adds the sample SKU |
| Pre-fill guesses | Gel cleanser read as a tube, cream cleanser as a jar, lip balm as a jar, refill pouch as a dropper bottle | Rules for cleanser, lip balm, refills and sets now come first |
| Jar lids | Always a gap | Library: 58-400 and 70-400 PP lids |

Library is now 149 items (jar lids, lip balm tube, sample sachet added).

## What the brand still has to tell us (16 answers for this brand)

- Sizes the library doesn't have (0.5 oz bottles): weigh 10.
- Items we estimate (ceramic candle: our estimate was 275 g, the real one 340 g): weigh one.
- Aerosol valve and actuator weight: ask the filler.
- What's inside each set; how retailer orders are packed; where local pickup happens.
- Discontinued products still in 2026 orders, free samples, and anything with no match (tools, accessories).

## Time per client (estimate)

Computer time is about a second. Our time, at this complexity:

| Step | Time |
| --- | --- |
| Pull data, pre-fill, send the sheet and questions | 30 min |
| Answer the brand's questions, apply their edits (over a few days) | 1-2 h |
| Run reports, read checks and exceptions, write the cover note | 1 h |
| Review call | 45 min |
| **Total** | **about 3.5-4.5 h** |

At $1,500 that is roughly $330-$430 an hour before costs. Capacity of 10-15 clients this season holds.

## Not covered yet

- Amazon and retail sell-through by state (see the connections research doc).
- Brands with more than one shipping location.
- A client-facing summary shorter than the full methodology (the packaging table runs to 300+ rows here).
