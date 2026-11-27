#!/usr/bin/env python3
"""Generate messy fake client data in clients/_dryrun/input to test build_reports.py.

The fictional brand sells tees, hoodies and gift boxes on Shopify and Amazon. The data includes the problems real
exports have: Shopify line items with blank order-level fields, state names in mixed formats, cancelled and refunded
orders, a return line, international orders, a missing state, an unknown SKU, multi-SKU orders and a large order
that needs two boxes.
"""
import csv, os, random

random.seed(7)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "clients", "_dryrun", "input")
os.makedirs(D, exist_ok=True)

PACK = [  # sku, level, component, library_id, qty, max_units, custom weight_g, ca_id, or_co_id, plastic n, plastic g, source
    ("TEE-01", "unit", "", "PKG-029", 1, "", "", "", "", "", "", ""),
    ("TEE-01", "order", "", "PKG-011", 1, 4, "", "", "", "", "", ""),
    ("TEE-01", "order", "", "PKG-084", 1, "", "", "", "", "", "", ""),
    ("HOOD-01", "unit", "", "PKG-034", 1, "", "", "", "", "", "", ""),
    ("HOOD-01", "order", "", "PKG-017", 1, 3, "", "", "", "", "", ""),
    ("HOOD-01", "order", "", "PKG-084", 1, "", "", "", "", "", "", ""),
    ("GIFT-01", "unit", "", "PKG-096", 1, "", "", "", "", "", "", ""),
    ("GIFT-01", "unit", "", "PKG-081", 1, "", "", "", "", "", "", ""),
    ("GIFT-01", "unit", "Branded hang tag with cotton string", "", 1, "", "3.2", "25_PF12N", "24", "", "",
     "client weighed 10 tags on 2027-01-08: 32 g"),
    ("GIFT-01", "order", "", "PKG-041", 1, 2, "", "", "", "", "", ""),
    ("GIFT-01", "order", "", "PKG-065", 1, 2, "", "", "", "", "", ""),
    ("GIFT-01", "order", "", "PKG-078", 1, 2, "", "", "", "", "", ""),
    ("GIFT-01", "order", "", "PKG-084", 1, "", "", "", "", "", "", ""),
    ("GIFT-01", "order", "", "PKG-085", 1, "", "", "", "", "", "", ""),
    ("BUNDLE-TEE3", "unit", "", "PKG-029", 3, "", "", "", "", "", "", ""),
    ("BUNDLE-TEE3", "order", "", "PKG-017", 1, "", "", "", "", "", "", ""),
    ("BUNDLE-TEE3", "order", "", "PKG-084", 1, "", "", "", "", "", "", ""),
]
with open(os.path.join(D, "packaging.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["sku", "level", "component", "library_id", "qty", "max_units", "weight_g", "ca_id", "or_co_id",
                "plastic_components", "plastic_weight_g", "weight_source"])
    w.writerows(PACK)

STATE_FORMS = {"CA": ["CA", "California", "california", "Calif."], "OR": ["OR", "Oregon"], "CO": ["CO", "Colorado"],
               "WA": ["WA", "Washington"], "MN": ["MN"], "MD": ["MD"], "NY": ["NY"], "TX": ["TX"]}
WEIGHTS = [("CA", 40), ("NY", 15), ("TX", 12), ("WA", 6), ("OR", 5), ("CO", 6), ("MN", 3), ("MD", 3)]
SKUS = [("TEE-01", 55), ("HOOD-01", 25), ("GIFT-01", 12), ("BUNDLE-TEE3", 6), ("SOCK-01", 2)]


def choose(pairs):
    return random.choices([p[0] for p in pairs], [p[1] for p in pairs])[0]


rows = []
for n in range(1001, 7001):
    st = choose(WEIGHTS)
    state = random.choice(STATE_FORMS[st])
    country, status, cancelled = "US", "paid", ""
    r = random.random()
    if r < 0.02: status = "refunded"
    elif r < 0.035: cancelled = "2026-03-02 10:11:00"
    elif r < 0.045: country, state = "CA", "ON"          # Canada: country code CA, province Ontario
    elif r < 0.05: state = ""
    lines = {choose(SKUS): random.choice([1, 1, 1, 2])}
    if random.random() < 0.15:
        lines[choose(SKUS)] = 1
    if n == 1500:
        lines = {"HOOD-01": 7}                            # big order: needs 3 mailers
    for j, (sku, q) in enumerate(lines.items()):
        first = j == 0
        rows.append({"Name": f"#{n}", "Financial Status": status if first else "", "Cancelled at": cancelled if first else "",
                     "Lineitem quantity": q, "Lineitem sku": sku,
                     "Shipping Province": state if first else "", "Shipping Country": country if first else ""})
rows.append({"Name": "#1002", "Financial Status": "", "Cancelled at": "", "Lineitem quantity": -1,
             "Lineitem sku": "TEE-01", "Shipping Province": "", "Shipping Country": ""})  # stray return line
with open(os.path.join(D, "orders-shopify.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)

with open(os.path.join(D, "orders-amazon.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["amazon-order-id", "sku", "quantity-shipped", "ship-state", "ship-country"])
    for n in range(1500):
        st = choose(WEIGHTS)
        w.writerow([f"113-{1000000 + n}", choose(SKUS[:3]), 1, random.choice(STATE_FORMS[st]).upper(), "US"])
print("dry-run data written to", D)
