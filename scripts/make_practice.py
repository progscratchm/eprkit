#!/usr/bin/env python3
"""Generate a realistic fictional client for a full practice run: clients/_practice/raw/

"Juniper & Moss" (made up): a $9M clean-skincare brand on Shopify. 60 shippable variants plus a gift card,
full-year 2026 orders in Shopify's own export format, with the mess real stores have:
  - bundles/gift sets sold as one SKU that contain other products
  - free samples added to orders at $0
  - subscription (Recharge-style) orders tagged "Subscription"
  - wholesale orders to retailers placed through Shopify (tagged "wholesale", ship to a retailer warehouse)
  - local pickup orders (no shipping address state, pickup at the Portland, OR studio)
  - refunds, partial refunds, cancellations, international orders
  - SKUs sold early in the year that are no longer in the product export (discontinued)
  - state names in mixed formats
"""
import csv, os, random, datetime

random.seed(2026)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "clients", "_practice", "raw")
os.makedirs(D, exist_ok=True)

# handle, title, type, tags, [(option value, sku, grams, price)]
P = []
def prod(handle, title, typ, tags, variants):
    P.append((handle, title, typ, tags, variants))

serums = ["Vitamin C Brightening Serum", "Hyaluronic Hydration Serum", "Niacinamide Clarifying Serum",
          "Bakuchiol Renewal Serum", "Peptide Firming Serum", "Calming Cica Serum"]
for i, t in enumerate(serums):
    prod(f"serum-{i}", t, "Serum", "skincare, serum, dropper",
         [("0.5 oz", f"SER{i}-15", 60, 38), ("1 oz", f"SER{i}-30", 95, 64)])
for i, t in enumerate(["Rosehip Face Oil", "Squalane Face Oil", "Blue Tansy Face Oil"]):
    prod(f"oil-{i}", t, "Face Oil", "skincare, oil", [("1 oz", f"OIL{i}-30", 95, 58)])
for i, t in enumerate(["Gentle Gel Cleanser", "Oat Milk Cream Cleanser", "Clarifying Foaming Wash"]):
    prod(f"clean-{i}", t, "Cleanser", "skincare, cleanser",
         [("4 oz", f"CLN{i}-4", 150, 24), ("8 oz", f"CLN{i}-8", 270, 38)])
for i, t in enumerate(["Daily Barrier Cream", "Rich Night Cream", "Whipped Body Butter"]):
    prod(f"cream-{i}", t, "Moisturizer", "skincare, cream, jar",
         [("4 oz", f"CRM{i}-4", 260, 46), ("8 oz", f"CRM{i}-8", 420, 72)])
prod("lip", "Tinted Lip Balm", "Lip", "lip, balm",
     [(c, f"LIP-{c[:3].upper()}", 15, 14) for c in ["Clear", "Rose", "Berry", "Nude"]])
prod("spf", "Mineral Sunscreen SPF 30", "Sunscreen", "spf, sunscreen, tube",
     [("2 oz", "SPF-2", 80, 28), ("6 oz", "SPF-6", 210, 44)])
prod("bodywash", "Juniper Body Wash", "Body", "body wash, pump", [("16 oz", "BW-16", 560, 32)])
prod("deo", "Natural Deodorant", "Body", "deodorant, stick",
     [(s, f"DEO-{s[:3].upper()}", 95, 16) for s in ["Juniper", "Lavender", "Unscented"]])
prod("dryshampoo", "Dry Shampoo Spray", "Hair", "hair, spray", [("5 oz", "DRY-5", 190, 26)])
prod("candle", "Forest Ceramic Candle", "Home", "candle, ceramic, vessel",
     [("8.5 oz", "CND-85", 620, 54), ("Mini 5 oz", "CND-5", 360, 34)])
prod("refill", "Hydration Serum Refill Pouch", "Serum", "refill, pouch", [("2 oz", "REF-SER", 75, 52)])
prod("travel", "Travel Kit", "Set", "gift set, kit",
     [("Kit", "KIT-TRAVEL", 210, 48)])
prod("routine", "Complete Routine Gift Set", "Set", "gift set, holiday",
     [("Set", "SET-ROUTINE", 640, 129), ("Mini Set", "SET-MINI", 330, 79)])
prod("tool", "Gua Sha Stone", "Tool", "tool, stone", [("Rose quartz", "GUA-RQ", 110, 32), ("Jade", "GUA-JD", 110, 32)])
prod("headband", "Spa Headband", "Accessory", "accessory, headband, cotton", [("One size", "HB-1", 40, 18)])
prod("gift-card", "Juniper & Moss Gift Card", "Gift Card", "gift card", [("$50", "GC-50", 0, 50)])

variants = [(h, t, typ, tags, o, sku, g, pr) for h, t, typ, tags, vs in P for (o, sku, g, pr) in vs]

# --- products_export.csv (Shopify format: product fields on the first row of each handle only)
cols = ["Handle", "Title", "Body (HTML)", "Vendor", "Product Category", "Type", "Tags", "Published",
        "Option1 Name", "Option1 Value", "Variant SKU", "Variant Grams", "Variant Requires Shipping",
        "Variant Price", "Status"]
with open(os.path.join(D, "products_export.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
    for h, t, typ, tags, vs in P:
        for k, (o, sku, g, pr) in enumerate(vs):
            first = k == 0
            w.writerow({"Handle": h, "Title": t if first else "", "Body (HTML)": "", "Vendor": "Juniper & Moss" if first else "",
                        "Product Category": "Health & Beauty" if first else "", "Type": typ if first else "",
                        "Tags": tags if first else "", "Published": "TRUE" if first else "",
                        "Option1 Name": "Size" if first else "", "Option1 Value": o, "Variant SKU": sku,
                        "Variant Grams": g, "Variant Requires Shipping": "FALSE" if sku.startswith("GC") else "TRUE",
                        "Variant Price": pr, "Status": "active"})
# bundle contents (what the brand would tell us; not in Shopify's export)
with open(os.path.join(D, "bundles-from-brand.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["bundle_sku", "contains_sku", "qty"])
    for b, items in {"SET-ROUTINE": [("CLN0-4", 1), ("SER1-30", 1), ("CRM0-4", 1), ("LIP-CLE", 1)],
                     "SET-MINI": [("SER1-15", 1), ("CRM0-4", 1)],
                     "KIT-TRAVEL": [("CLN0-4", 1), ("SER0-15", 1), ("SPF-2", 1)]}.items():
        for s, q in items:
            w.writerow([b, s, q])

# --- orders_export.csv (Shopify format)
pop = {"CA": 39.0, "TX": 30.5, "FL": 22.6, "NY": 19.6, "PA": 13.0, "IL": 12.5, "OH": 11.8, "GA": 11.0, "NC": 10.8,
       "MI": 10.0, "NJ": 9.3, "VA": 8.7, "WA": 7.8, "AZ": 7.4, "TN": 7.1, "MA": 7.0, "IN": 6.9, "MD": 6.2,
       "MO": 6.2, "WI": 5.9, "CO": 5.9, "MN": 5.7, "SC": 5.4, "AL": 5.1, "LA": 4.6, "KY": 4.5, "OR": 4.2,
       "OK": 4.0, "CT": 3.6, "UT": 3.4, "IA": 3.2, "NV": 3.2, "AR": 3.0, "KS": 2.9, "MS": 2.9, "NM": 2.1,
       "NE": 2.0, "ID": 2.0, "WV": 1.8, "HI": 1.4, "NH": 1.4, "ME": 1.4, "MT": 1.1, "RI": 1.1, "DE": 1.0,
       "SD": 0.9, "ND": 0.8, "AK": 0.7, "DC": 0.7, "VT": 0.6, "WY": 0.6}
skew = {"CA": 1.5, "OR": 2.2, "WA": 1.6, "CO": 1.4, "NY": 1.3}     # West-coast clean-beauty skew; OR is home
weights = {s: v * skew.get(s, 1) for s, v in pop.items()}
names = {"CA": ["California", "CA", "Calif."], "OR": ["Oregon", "OR"], "CO": ["Colorado", "CO"]}
states, sw = list(weights), list(weights.values())
ship_skus = [v for v in variants if not v[5].startswith("GC")]
discontinued = [("Matcha Clay Mask 2 oz", "MSK-MATCHA", 30), ("Holiday Ornament Set 2025", "SET-ORN25", 60)]

ocols = ["Name", "Email", "Financial Status", "Fulfillment Status", "Created at", "Lineitem quantity",
         "Lineitem name", "Lineitem price", "Lineitem sku", "Lineitem requires shipping", "Shipping Method",
         "Shipping Province", "Shipping Country", "Cancelled at", "Tags", "Refunded Amount"]
rows, n = [], 1000
start = datetime.date(2026, 1, 1)
def add_order(lines, state, country="US", status="paid", tags="", method="Standard", cancelled="", refunded=""):
    global n
    n += 1
    day = start + datetime.timedelta(days=random.randrange(365))
    for k, (name, sku, qty, price) in enumerate(lines):
        first = k == 0
        rows.append({"Name": f"#{n}", "Email": f"customer{n}@example.com" if first else "",
                     "Financial Status": status if first else "", "Fulfillment Status": "fulfilled" if first else "",
                     "Created at": f"{day} 10:{n%60:02d}:00 -0800" if first else "", "Lineitem quantity": qty,
                     "Lineitem name": name, "Lineitem price": price, "Lineitem sku": sku,
                     "Lineitem requires shipping": "false" if sku.startswith("GC") else "true",
                     "Shipping Method": method if first else "",
                     "Shipping Province": state if first else "", "Shipping Country": country if first else "",
                     "Cancelled at": cancelled if first else "", "Tags": tags if first else "",
                     "Refunded Amount": refunded if first else ""})

for _ in range(21000):
    st = random.choices(states, sw)[0]
    disp = random.choice(names.get(st, [st]))
    k = random.choices([1, 2, 3, 4], [55, 28, 12, 5])[0]
    lines = []
    for v in random.sample(ship_skus, k):
        lines.append((f"{v[1]} - {v[4]}", v[5], random.choices([1, 2, 3], [85, 12, 3])[0], v[7]))
    if random.random() < 0.35:   # free sample sachet, no SKU in the product export
        lines.append(("Free sample: Hydration Serum sachet", "SAMPLE-SER", 1, 0))
    r = random.random()
    if r < 0.04:
        add_order(lines, disp, status="refunded", refunded="full")
    elif r < 0.06:
        add_order(lines, disp, status="partially_refunded", refunded="partial")
    elif r < 0.075:
        add_order(lines, disp, status="voided", cancelled="2026-06-01 09:00:00 -0800")
    elif r < 0.24:
        add_order(lines, disp, tags="Subscription, Recharge")
    else:
        add_order(lines, disp)
for _ in range(600):            # international
    v = random.choice(ship_skus)
    add_order([(f"{v[1]} - {v[4]}", v[5], 1, v[7])], random.choice(["ON", "BC", "NSW", ""]),
              country=random.choice(["CA", "AU", "GB"]))
for _ in range(350):            # local pickup at the Portland studio: no shipping province
    v = random.choice(ship_skus)
    add_order([(f"{v[1]} - {v[4]}", v[5], 1, v[7])], "", country="", method="Local pickup")
for _ in range(900):            # discontinued SKUs sold early in the year
    name, sku, price = random.choice(discontinued)
    add_order([(name, sku, 1, price)], random.choices(states, sw)[0])
for _ in range(250):            # gift cards alone
    add_order([("Juniper & Moss Gift Card - $50", "GC-50", 1, 50)], random.choices(states, sw)[0])
retailers = [("Credo Beauty DC", "NJ"), ("Detox Market DC", "CA"), ("New Seasons Market DC", "OR"), ("Indie boutiques", None)]
for _ in range(140):            # wholesale through Shopify: cases to retailer warehouses
    name, st = random.choice(retailers)
    lines = [(f"{v[1]} - {v[4]}", v[5], random.choice([12, 24, 48]), round(v[7] * 0.5, 2))
             for v in random.sample(ship_skus, random.randint(3, 8))]
    add_order(lines, st or random.choices(states, sw)[0], tags="wholesale, Faire" if not st else "wholesale")
for _ in range(80):             # a few rows with no state at all
    v = random.choice(ship_skus)
    add_order([(f"{v[1]} - {v[4]}", v[5], 1, v[7])], "", country="US")

with open(os.path.join(D, "orders_export.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=ocols); w.writeheader(); w.writerows(rows)
print(f"{len(variants)} variants ({len(ship_skus)} shippable), {n-1000} orders, {len(rows)} lines -> {D}")
