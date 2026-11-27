# Client intake: what we ask for and how to get it

Send this to a client right after they sign. Data is due by February 15, 2027, for delivery by May 15, 2027.
Everything goes to support@eprkit.com or a shared folder we set up for them.

## 1. Numbers for the threshold check (5 minutes)

- Total 2026 revenue, all channels.
- 2026 sales shipped into California, Oregon, Colorado, Minnesota, Maryland and Washington, in dollars.
- Whether they sell wholesale, and to whom. Business-to-business shipments are handled separately.

## 2. Order exports for January 1 to December 31, 2026 (about 30 minutes)

One file per channel, unedited. We clean them. Name each file `orders-<channel>.csv`.

- **Shopify:** Orders, filter by date 2026-01-01 to 2026-12-31, Export, "All orders matching your search", CSV
  for Excel. The builder reads Name, Lineitem sku, Lineitem quantity, Shipping Province, Shipping Country,
  Financial Status and Cancelled at.
- **Amazon FBA:** Seller Central, Reports, Fulfillment, "Amazon Fulfilled Shipments", 2026. Uses
  amazon-order-id, sku, quantity-shipped, ship-state.
- **Amazon merchant-fulfilled, other marketplaces, 3PL or wholesale:** any export with order ID, SKU, units and
  ship-to state. If their tool can't do that, they fill `templates/orders-template.csv`.

## 3. Product list (5 minutes)

- Product export with every SKU sold in 2026, including bundles and discontinued items.

## 4. Packaging (the 20-minute mapping call)

For each SKU we fill `templates/packaging-template.csv` together:

- **Per unit** (`level=unit`): anything that travels with one unit. Poly bag, product carton, bottle, cap, label,
  hang tag, tissue.
- **Per order** (`level=order`): the shipping set. Mailer or box, void fill, tape, shipping label, packing slip,
  inserts. Set `max_units` to how many units fit in one package; bigger orders become several packages.
- Stock items get a `library_id` from the [category lookup](https://eprkit.com/lookup.html). Custom items need a
  measured weight (weigh 10 and divide), the material and where the weight came from.
- Ask for photos of anything custom, and supplier spec sheets if they have them.

## 5. What we send back

Run `python3 scripts/build_reports.py clients/<client>`. Before delivery:

1. `checks.txt` shows all PASS.
2. Every "needs review" line in `exceptions.csv` is resolved or explained in the methodology.
3. Spot-check three SKUs by hand from `working.csv`.
4. Minnesota, Maryland and Washington: the summary gives totals by material class. Map them to the state's 8
   categories by hand until that mapping is built into the script.

Client folders under `clients/` are ignored by git. Only `clients/_dryrun` (fake data) is committed.
