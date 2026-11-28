#!/usr/bin/env python3
"""Build a client's packaging EPR reports from order exports and a packaging list.

Usage:  python3 scripts/build_reports.py clients/<client>

Input folder  clients/<client>/input/
  orders*.csv     One or more order exports (Shopify, Amazon, 3PL or our simple template).
                  Column names are matched against ALIASES below.
  packaging.csv   One row per packaging component per SKU. Columns:
                    sku, level (unit|order), component, library_id, qty, max_units,
                    weight_g, ca_id, or_co_id, plastic_components, plastic_weight_g, weight_source, compostable
                  level=unit  : used once per unit sold (poly bag, carton, bottle).
                  level=order : the SKU's shipping set (box, mailer, fill, label). An order uses ONE set:
                                the heaviest set among the SKUs in it, repeated ceil(units / max_units)
                                times when max_units is set.
                  library_id fills weight and categories from data/packaging-library.csv. Any custom_
                  column given on the row overrides the library value.
Output folder clients/<client>/output/
  ca-supply-report.csv, oregon-supply-report.csv, colorado-supply-report.csv
  minnesota/maryland/washington-simplified-report.csv   8 CAA simplified categories
  working.csv       every state x SKU x component line behind the totals
  exceptions.csv    rows we excluded or could not place, with the reason and units
  checks.txt        the portal validation rules, pass or fail
  summary.md        what went in, what came out, what needs a human (internal)
  methodology.md    client-facing: data used, exclusions, packaging per product, calculations, totals
"""
import csv, glob, math, os, re, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G_PER_LB = 453.59237
REPORT_STATES = ["CA", "OR", "CO"]          # states with full category reports built here
FLAG_STATES = ["MN", "MD", "WA"]            # simplified supply report, 8 broad categories
SIMPLE_NAMES = {"MN": "minnesota", "MD": "maryland", "WA": "washington"}
# CAA simplified categories, mapped from the Oregon/Colorado material class of each item.
# Items marked compostable=Y in packaging.csv go to Compostable Materials instead.
SIMPLE_MAP = {"Printing and Writing Paper": "Printing and Writing Paper", "Glass and Ceramics": "Glass and Ceramics",
              "Metal": "Metal", "Paper/Fiber": "Paper/Fiber", "Plastic - Rigid": "Rigid Plastic",
              "Plastic - Flexible": "Flexible Plastic",
              "Plastic - Other": "Rigid Plastic",   # OR/CO #58 small-format plastic (caps, pumps, droppers): rigid
              "Wood and Other Organic Materials": "Wood and Other Organic Materials"}
SIMPLE_ORDER = ["Printing and Writing Paper", "Glass and Ceramics", "Metal", "Paper/Fiber", "Rigid Plastic",
                "Flexible Plastic", "Wood and Other Organic Materials", "Compostable Materials"]

ALIASES = {
    "order_id": ["order_id", "name", "order id", "amazon-order-id", "order number", "order", "order #"],
    "sku": ["sku", "lineitem sku", "seller-sku", "item sku", "product sku"],
    "qty": ["qty", "quantity", "lineitem quantity", "quantity-shipped", "units", "qty shipped"],
    "state": ["state", "ship_state", "shipping province", "ship-state", "shipping state", "ship to state",
              "shipping province code", "province"],
    "country": ["country", "shipping country", "ship-country", "ship to country"],
    "status": ["status", "financial status", "order status"],
    "fulfillment": ["fulfillment status", "fulfillment-status"],
    "tags": ["tags", "order tags"],
    "requires_shipping": ["lineitem requires shipping", "requires shipping", "requires_shipping"],
    "method": ["shipping method", "ship method", "ship-service-level", "shipping service"],
    "cancelled": ["cancelled at", "cancelled_at"],
}
EXCLUDE_STATUS = {"refunded", "voided", "cancelled", "canceled"}

STATES = {"alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA", "colorado": "CO",
          "connecticut": "CT", "delaware": "DE", "district of columbia": "DC", "florida": "FL", "georgia": "GA",
          "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
          "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD", "massachusetts": "MA",
          "michigan": "MI", "minnesota": "MN", "mississippi": "MS", "missouri": "MO", "montana": "MT",
          "nebraska": "NE", "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
          "new york": "NY", "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
          "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
          "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
          "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY", "puerto rico": "PR"}
CODES = set(STATES.values())
ABBREV = {"calif": "CA", "cal": "CA", "ore": "OR", "oreg": "OR", "colo": "CO", "col": "CO", "wash": "WA",
          "minn": "MN", "md": "MD", "mass": "MA", "penn": "PA", "penna": "PA", "tex": "TX", "fla": "FL",
          "ill": "IL", "mich": "MI", "wis": "WI", "ariz": "AZ", "nev": "NV", "n y": "NY", "d c": "DC"}


def norm_state(v):
    v = (v or "").strip()
    if not v:
        return None
    if v.upper() in CODES:
        return v.upper()
    key = re.sub(r"\s+", " ", v.lower().replace(".", " ")).strip()
    if key.startswith("us-") and key[3:].upper() in CODES:     # ISO style, e.g. US-CA
        return key[3:].upper()
    return STATES.get(key) or ABBREV.get(key)


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def pick(row, field):
    low = {k.strip().lower(): v for k, v in row.items() if k}
    for a in ALIASES[field]:
        if a in low and low[a] not in (None, ""):
            return low[a].strip()
    return ""


def num(v, default=0.0):
    try:
        return float(str(v).replace(",", "").strip())
    except ValueError:
        return default


def load_reference():
    lib = {r["id"]: r for r in read_csv(os.path.join(ROOT, "data", "packaging-library.csv"))}
    ca = {r["calrecycle_id"]: r for r in read_csv(os.path.join(ROOT, "data", "ca-cmc-2026.csv"))}
    orco = {r["id"]: r for r in read_csv(os.path.join(ROOT, "data", "or-co-categories.csv"))}
    return lib, ca, orco


def load_packaging(path, lib, ca, orco, problems):
    unit, order = collections.defaultdict(list), collections.defaultdict(list)
    for i, r in enumerate(read_csv(path), start=2):
        sku = (r.get("sku") or "").strip()
        if not sku:
            continue
        base = lib.get((r.get("library_id") or "").strip(), {})
        if r.get("library_id") and not base:
            problems.append(f"packaging.csv line {i}: library_id {r['library_id']} not found")
        c = {
            "component": r.get("component") or base.get("name", ""),
            "library_id": r.get("library_id", ""),
            "qty": num(r.get("qty") or 1, 1),
            "max_units": int(num(r.get("max_units"), 0)) or None,
            "weight_g": num(r.get("weight_g") or base.get("weight_g")),
            "ca_id": (r.get("ca_id") or base.get("ca_calrecycle_id", "")).strip(),
            "or_co_id": (r.get("or_co_id") or base.get("or_co_category_id", "")).strip(),
            "plastic_components": num(r.get("plastic_components") or base.get("ca_plastic_components") or 0),
            "plastic_weight_g": num(r.get("plastic_weight_g") or base.get("ca_plastic_weight_g") or 0),
            "weight_source": r.get("weight_source") or (f"library {base['id']}: {base['weight_method']}" if base else ""),
            "material_class": base.get("majority_material_class", ""),
            "compostable": (r.get("compostable") or "").strip().upper() in ("Y", "YES", "TRUE", "1"),
        }
        if c["weight_g"] <= 0:
            problems.append(f"packaging.csv line {i}: {sku} / {c['component']} has no weight")
        if c["ca_id"] and c["ca_id"] not in ca:
            problems.append(f"packaging.csv line {i}: CA category {c['ca_id']} not in the CalRecycle list")
        if c["or_co_id"] and c["or_co_id"] not in orco:
            problems.append(f"packaging.csv line {i}: OR/CO category {c['or_co_id']} not in the list")
        if not c["weight_source"]:
            problems.append(f"packaging.csv line {i}: {sku} / {c['component']} has no weight source")
        if "confirmed" in r and (r.get("confirmed") or "").strip().upper() not in ("Y", "YES"):
            problems.append(f"packaging.csv line {i}: {sku} / {c['component']} is a pre-filled guess the brand hasn't confirmed")
        lvl = (r.get("level") or "unit").strip().lower()
        (order if lvl == "order" else unit)[sku].append(c)
    return unit, order


def load_config(client_dir):
    """Optional clients/<c>/client.json: pickup_state, wholesale_tags, include_refunded_if_fulfilled."""
    import json
    cfg = {"pickup_state": None, "wholesale_tags": ["wholesale"], "include_refunded_if_fulfilled": True}
    p = os.path.join(client_dir, "client.json")
    if os.path.exists(p):
        cfg.update(json.load(open(p)))
    return cfg


def load_bundles(indir):
    """input/bundles.csv: bundle_sku, contains_sku, qty. A bundle's units also count its contents' unit packaging."""
    b = collections.defaultdict(list)
    p = os.path.join(indir, "bundles.csv")
    if os.path.exists(p):
        for r in read_csv(p):
            if r.get("bundle_sku") and r.get("contains_sku"):
                b[r["bundle_sku"].strip()].append((r["contains_sku"].strip(), num(r.get("qty") or 1, 1)))
    return b


def load_orders(indir, exceptions, cfg=None):
    """Return {order_key: {"state":, "lines": {sku: units}}}. Forward-fills order-level fields (Shopify style)."""
    orders = {}
    files = sorted(glob.glob(os.path.join(indir, "orders*.csv")))
    for path in files:
        src = os.path.basename(path)
        last = {}
        for i, r in enumerate(read_csv(path), start=2):
            oid = pick(r, "order_id") or f"{src}:{i}"
            if last.get("order_id") == oid:   # Shopify: order fields only on first line item
                for k in ("state", "country", "status", "cancelled", "fulfillment", "tags", "method"):
                    if not pick(r, k):
                        r = dict(r); r["__" + k] = last.get(k, "")
            st_raw = pick(r, "state") or r.get("__state", "")
            country = (pick(r, "country") or r.get("__country", "") or "US").upper()
            status = (pick(r, "status") or r.get("__status", "")).lower()
            cancelled = pick(r, "cancelled") or r.get("__cancelled", "")
            fulfil = (pick(r, "fulfillment") or r.get("__fulfillment", "")).lower()
            tags = (pick(r, "tags") or r.get("__tags", "")).lower()
            method = (pick(r, "method") or r.get("__method", "")).lower()
            last = {"order_id": oid, "state": st_raw, "country": country, "status": status, "cancelled": cancelled,
                    "fulfillment": fulfil, "tags": tags, "method": method}
            sku = pick(r, "sku")
            qty = num(pick(r, "qty"), 0)
            where = f"{src} line {i}"
            cfg = cfg or {}
            refunded_shipped = (status in ("refunded",) and fulfil in ("fulfilled", "shipped")
                                and cfg.get("include_refunded_if_fulfilled", True) and not cancelled)
            if (cancelled or status in EXCLUDE_STATUS) and not refunded_shipped:
                exceptions.append([where, oid, sku, qty, "excluded: cancelled or refunded"]); continue
            pickup = "pickup" in method or "pick up" in method
            if pickup and not st_raw and cfg.get("pickup_state"):
                st_raw, country = cfg["pickup_state"], "US"
            if country in ("", "NONE") and pickup:
                country = "US"
            if country not in ("US", "USA", "UNITED STATES"):
                exceptions.append([where, oid, sku, qty, f"excluded: ships outside the US ({country})"]); continue
            if qty <= 0:
                exceptions.append([where, oid, sku, qty, "excluded: zero or negative quantity (return line?)"]); continue
            if pick(r, "requires_shipping").lower() in ("false", "no", "0"):
                exceptions.append([where, oid, sku, qty, "excluded: doesn't ship (gift card or digital)"]); continue
            if not sku:
                exceptions.append([where, oid, sku, qty, "needs review: no SKU"]); continue
            state = norm_state(st_raw)
            if not state:
                exceptions.append([where, oid, sku, qty, f"needs review: ship-to state missing or unknown ({st_raw!r})"]); continue
            key = f"{src}:{oid}"
            if refunded_shipped:
                exceptions.append([where, oid, sku, qty, "included: refunded after it shipped (the packaging still went out)"])
            wholesale = any(t.strip() in [w.lower() for w in cfg.get("wholesale_tags", [])] for t in tags.split(","))
            o = orders.setdefault(key, {"state": state, "lines": collections.Counter(), "pickup": pickup,
                                        "wholesale": wholesale})
            o["lines"][sku] += qty
    return orders, files


def build(client_dir):
    indir, outdir = os.path.join(client_dir, "input"), os.path.join(client_dir, "output")
    os.makedirs(outdir, exist_ok=True)
    lib, ca, orco = load_reference()
    problems, exceptions = [], []
    unit, order_sets = load_packaging(os.path.join(indir, "packaging.csv"), lib, ca, orco, problems)
    cfg = load_config(client_dir)
    bundles = load_bundles(indir)
    orders, files = load_orders(indir, exceptions, cfg)
    if any(o["wholesale"] for o in orders.values()) and "_WHOLESALE" not in order_sets:
        problems.append("Wholesale orders found but packaging.csv has no _WHOLESALE shipping set (case boxes): they "
                        "would get consumer mailers. Add rows with sku _WHOLESALE, level order")

    work = collections.defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])  # (state,sku,component,ca,orco,src) -> units, g, plastic g, plastic n
    units_by_state = collections.Counter()
    unknown = collections.Counter()
    for key, o in orders.items():
        st, lines = o["state"], o["lines"]
        known = {s: q for s, q in lines.items() if s in unit or s in order_sets or s in bundles}
        for s, q in lines.items():
            if s not in known:
                unknown[s] += q
                exceptions.append([key, key.split(":", 1)[1], s, q, "needs review: SKU not in packaging list"])
        if not known:
            continue
        expanded = collections.Counter()
        for s, q in known.items():
            units_by_state[st] += q
            expanded[s] += q
            for inner, iq in bundles.get(s, []):     # a bundle's contents carry their own unit packaging
                if inner in unit:
                    expanded[(inner, s)] += q * iq
                else:
                    problems.append(f"bundle {s} contains {inner}, which has no packaging rows")
        for s2, q in expanded.items():
            s, label = (s2[0], f"{s2[1]} > {s2[0]}") if isinstance(s2, tuple) else (s2, s2)
            for c in unit.get(s, []):
                n = q * c["qty"]
                w = work[(st, label, c["component"], c["ca_id"], c["or_co_id"], c["weight_source"], c["compostable"])]
                w[0] += n; w[1] += n * c["weight_g"]; w[2] += n * c["plastic_weight_g"]; w[3] += n * c["plastic_components"]
        if o.get("pickup"):
            continue    # collected in person: no shipping packaging
        if o.get("wholesale") and "_WHOLESALE" in order_sets:
            cands = ["_WHOLESALE"]
        else:
            cands = [s for s in known if order_sets.get(s)]
            for s in known:                    # a bundle without its own shipping set uses its contents' sets
                if s in bundles and not order_sets.get(s):
                    cands += [i for i, _ in bundles[s] if order_sets.get(i)]
        if not cands:
            continue
        ship_sku = max(cands, key=lambda s: sum(c["weight_g"] * c["qty"] for c in order_sets[s]))
        total_units = sum(known.values())
        caps = [c["max_units"] for c in order_sets[ship_sku] if c["max_units"]]
        packages = math.ceil(total_units / min(caps)) if caps else 1
        for c in order_sets[ship_sku]:
            n = packages * c["qty"]
            w = work[(st, f"order set: {ship_sku}", c["component"], c["ca_id"], c["or_co_id"], c["weight_source"], c["compostable"])]
            w[0] += n; w[1] += n * c["weight_g"]; w[2] += n * c["plastic_weight_g"]; w[3] += n * c["plastic_components"]

    with open(os.path.join(outdir, "working.csv"), "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["State", "SKU", "Component", "CA category", "OR/CO category", "Weight source", "Compostable", "Components counted",
                     "Weight (g)", "Plastic weight (g)", "Plastic components"])
        for k, v in sorted(work.items()):
            wr.writerow(list(k[:6]) + ["Y" if k[6] else ""] + [round(v[0], 2), round(v[1], 2), round(v[2], 2), round(v[3])])

    checks = []

    # California
    agg = collections.defaultdict(lambda: [0.0, 0.0, 0.0])
    for (st, _, _, cid, _, _, _), v in work.items():
        if st == "CA":
            a = agg[cid]; a[0] += v[1]; a[1] += v[2]; a[2] += v[3]
    ca_rows = []
    for cid, (g, pg, pn) in sorted(agg.items()):
        if not cid:
            checks.append(("FAIL", f"CA: {g/G_PER_LB:.2f} lbs have no CA category")); continue
        c = ca[cid]; plastic = c["plastic_cmc"] == "Plastic"
        tot, pl, cnt = round(g / G_PER_LB, 2), round(pg / G_PER_LB, 2), int(round(pn))
        ca_rows.append([c["caa_material_id"], cid, c["reporting_category"], f"{tot:.2f}",
                        f"{pl:.2f}" if plastic else "", str(cnt) if plastic else ""])
        if plastic and (pl <= 0 or cnt <= 0):
            checks.append(("FAIL", f"CA {cid}: plastic category needs plastic weight and count"))
        if not plastic and (pl > 0 or cnt > 0):
            checks.append(("FAIL", f"CA {cid}: non-plastic category carries plastic weight or count"))
        if pl > tot:
            checks.append(("FAIL", f"CA {cid}: plastic weight {pl} above total {tot}"))
        if plastic and not c["material_class"].startswith("Plastic") and pl > tot * 0.5:
            checks.append(("FAIL", f"CA {cid}: plastic is over 50% of a non-plastic category ({pl} of {tot})"))
    with open(os.path.join(outdir, "ca-supply-report.csv"), "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["Circular Action Material ID", "CalRecycle Material ID", "Reporting Category", "Total Weight (lbs)",
                     "Weight - Plastic Components (lbs)", "# of Plastic Components"])
        wr.writerows(ca_rows)
    for r in ca_rows:   # format rule: two decimals, whole counts
        for v in r[3:5]:
            if v and not re.fullmatch(r"\d+\.\d{2}", v):
                checks.append(("FAIL", f"CA {r[1]}: weight {v} not in 2-decimal format"))
        if r[5] and not r[5].isdigit():
            checks.append(("FAIL", f"CA {r[1]}: count {r[5]} not a whole number"))

    # Oregon and Colorado
    orco_totals = {}
    for st, name in (("OR", "oregon"), ("CO", "colorado")):
        agg = collections.Counter()
        for (s, _, _, _, oid, _, _), v in work.items():
            if s == st:
                agg[oid] += v[1]
        rows = []
        for oid, g in sorted(agg.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999):
            if not oid:
                checks.append(("FAIL", f"{st}: {g/G_PER_LB:.2f} lbs have no OR/CO category")); continue
            o = orco[oid]
            rows.append([oid, o["material_class"], o["category"], f"{g/G_PER_LB:.2f}"])
        orco_totals[st] = sum(float(r[3]) for r in rows)
        with open(os.path.join(outdir, f"{name}-supply-report.csv"), "w", newline="") as f:
            wr = csv.writer(f)
            wr.writerow(["Category #", "Material class", "Category", "Total Weight (lbs)"])
            wr.writerows(rows)

    # Minnesota, Maryland, Washington: simplified supply report, 8 categories
    simple = collections.defaultdict(collections.Counter)
    for (st, sku, comp, _, oid, _, comp_flag), v in work.items():
        if st not in FLAG_STATES:
            continue
        if comp_flag:
            cat = "Compostable Materials"
        else:
            cat = SIMPLE_MAP.get(orco[oid]["material_class"]) if oid in orco else None
            if oid in ("51", "56"):
                checks.append(("REVIEW", f"{st}: {comp} is PLA/PHA. Mark compostable=Y if certified compostable"))
        if not cat:
            checks.append(("FAIL", f"{st}: {comp} ({sku}) has no simplified category (OR/CO #{oid or 'none'})"))
            continue
        simple[st][cat] += v[1]
    for st in FLAG_STATES:
        if not simple[st]:
            continue
        placed = sum(v[1] for k, v in work.items() if k[0] == st)
        if abs(placed - sum(simple[st].values())) > 1:
            checks.append(("FAIL", f"{st}: simplified total does not match the working lines"))
        with open(os.path.join(outdir, f"{SIMPLE_NAMES[st]}-simplified-report.csv"), "w", newline="") as f:
            wr = csv.writer(f)
            wr.writerow(["Simplified Category", "Total Weight (lbs)"])
            for cat in SIMPLE_ORDER:
                wr.writerow([cat, f"{simple[st][cat] / G_PER_LB:.2f}"])

    with open(os.path.join(outdir, "exceptions.csv"), "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["Where", "Order", "SKU", "Units", "Reason"])
        wr.writerows(exceptions)

    if not any(c[0] == "FAIL" for c in checks):
        checks.append(("PASS", "CA: plastic weight and count present wherever required, absent elsewhere"))
        checks.append(("PASS", "CA: plastic weight never above total weight"))
        checks.append(("PASS", "CA: plastic at or under 50% in non-plastic categories"))
        checks.append(("PASS", "CA: weights at 2 decimals, counts whole numbers"))
    for p in problems:
        checks.append(("FAIL", p))
    with open(os.path.join(outdir, "checks.txt"), "w") as f:
        f.writelines(f"{a}  {b}\n" for a, b in checks)

    reasons = collections.Counter(e[4].split(" (")[0] for e in exceptions)
    review_units = sum(num(e[3]) for e in exceptions if e[4].startswith("needs review"))
    total_units = sum(units_by_state.values())
    ca_total = sum(float(r[3]) for r in ca_rows)
    lines = [f"# Build summary: {os.path.basename(os.path.abspath(client_dir))}", "",
             f"Order files: {', '.join(os.path.basename(p) for p in files)}",
             f"Orders placed in a state: {len(orders):,}  ·  units counted: {int(total_units):,}", "",
             "## Units by state (report states)", ""]
    lines += [f"- {s}: {int(units_by_state[s]):,}" for s in REPORT_STATES + FLAG_STATES if units_by_state[s]]
    lines += ["", "## Report totals", "",
              f"- California: {ca_total:,.2f} lbs across {len(ca_rows)} categories",
              f"- Oregon: {orco_totals['OR']:,.2f} lbs", f"- Colorado: {orco_totals['CO']:,.2f} lbs"]
    for st in FLAG_STATES:
        if simple[st]:
            lines.append(f"- {st} (simplified): {sum(simple[st].values()) / G_PER_LB:,.2f} lbs, " +
                         ", ".join(f"{k} {v / G_PER_LB:,.2f}" for k, v in simple[st].items() if v))
    lines += ["", "## Exceptions", ""] + [f"- {k}: {v} rows" for k, v in reasons.most_common()]
    if unknown:
        lines += ["", "SKUs missing from the packaging list (units, all states): " +
                  ", ".join(f"{s} {int(q):,}" for s, q in unknown.most_common())]
    fails = [c for c in checks if c[0] == "FAIL"]
    lines += ["", "## Checks", "", f"{len(fails)} failing. See checks.txt." if fails else "All portal checks pass.", "",
              "## Before delivery", ""]
    share = review_units / (total_units + review_units) if total_units + review_units else 0
    lines.append(f"- {int(review_units):,} units need review ({share:.1%} of units). Resolve or explain them in the methodology."
                 if review_units else "- No units need review.")
    write_methodology(outdir, client_dir, files, unit, order_sets, exceptions, units_by_state, ca_total, orco_totals,
                      simple, orders=orders, cfg=cfg, bundles=bundles)
    with open(os.path.join(outdir, "summary.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return not fails


def write_methodology(outdir, client_dir, files, unit, order_sets, exceptions, units_by_state, ca_total, orco_totals,
                      simple, orders=None, cfg=None, bundles=None):
    """Client-facing methodology: how every number in the delivered files was produced."""
    name = os.path.basename(os.path.abspath(client_dir))
    excl = collections.Counter()
    for e in exceptions:
        excl[e[4].split(" (")[0]] += abs(num(e[3]))
    L = [f"# Packaging EPR methodology: {name}", "",
         "Prepared by EPR Kit for the 2027 filing season (calendar year 2026 supply). Every figure in the attached "
         "reports can be traced in working.csv to a product, a packaging item, a weight source and a count of units.", "",
         "## 1. Data we used", ""]
    L += [f"- `{os.path.basename(p)}`" for p in files]
    L += ["", "Units are counted by the state in the shipping address. We excluded or set aside:", ""]
    L += [f"- {(lambda t: t[0].upper() + t[1:])(k.split(': ', 1)[1])}: {int(v):,} units"
          + (" (set aside for review)" if k.startswith("needs review") else "") for k, v in excl.most_common()
          if not k.startswith("included")] or ["- nothing"]
    rules = []
    if any(e[4].startswith("included: refunded") for e in exceptions):
        rules.append("Orders refunded after they shipped are included: the packaging still reached the customer.")
    orders, cfg, bundles = orders or {}, cfg or {}, bundles or {}
    n_pick = sum(1 for o in orders.values() if o.get("pickup"))
    if n_pick:
        rules.append(f"{n_pick:,} local pickup orders are counted in {cfg.get('pickup_state')}, where they were collected, "
                     "with product packaging only (no shipping box).")
    n_whole = sum(1 for o in orders.values() if o.get("wholesale"))
    if n_whole:
        rules.append(f"{n_whole:,} wholesale orders are counted in the state they shipped to (usually the retailer's "
                     "warehouse), packed in the case boxes you described rather than consumer mailers.")
    if bundles:
        rules.append(f"{len(bundles)} sets or kits are counted with their own packaging plus the packaging of every "
                     "product inside them.")
    if rules:
        L += ["", "How we handled special orders:", ""] + [f"- {r}" for r in rules]
    L += ["", "Units marked \"needs review\" were resolved with you before delivery, or are explained in section 6.", "",
          "## 2. Units by state", "", "| State | Units |", "| --- | ---: |"]
    L += [f"| {s} | {int(units_by_state[s]):,} |" for s in REPORT_STATES + FLAG_STATES if units_by_state[s]]
    L += ["", "## 3. Packaging per product", "",
          "Per-unit items are counted once for each unit sold. Each order uses one shipping set: the heaviest set "
          "among the products in it. When an order holds more units than fit in one package, the whole set repeats "
          "for each package.", "",
          "| SKU | Level | Component | Qty | Units per package | Weight (g) | CA category | OR/CO # | Weight source |",
          "| --- | --- | --- | ---: | ---: | ---: | --- | --- | --- |"]
    for lvl, book in (("unit", unit), ("order", order_sets)):
        for sku in sorted(book):
            for c in book[sku]:
                L.append(f"| {sku} | {lvl} | {c['component']} | {c['qty']:g} | {c['max_units'] or ''} | "
                         f"{c['weight_g']:g} | {c['ca_id']} | {c['or_co_id']} | {c['weight_source']} |")
    L += ["", "## 4. Calculations and checks", "",
          "- Weights are summed in grams per category and state, converted at 453.59237 g per lb and rounded to two "
          "decimals once, at the end.",
          "- California: plastic component weight and count are reported for every category that requires them. Each "
          "separate plastic piece counts as one component.",
          "- Oregon and Colorado: weights by the 60 Oregon/Colorado categories.",
          "- Minnesota, Maryland and Washington: CAA's 8 simplified categories, from each item's Oregon/Colorado "
          "material class.",
          "- Before delivery we check the California rules the portal enforces: plastic weight and count present where "
          "required, plastic weight never above total, plastic at or under 50% in non-plastic categories, two decimals "
          "for weights and whole numbers for counts. Results are in checks.txt.", "",
          "## 5. Totals delivered", "",
          f"- California: {ca_total:,.2f} lbs", f"- Oregon: {orco_totals['OR']:,.2f} lbs",
          f"- Colorado: {orco_totals['CO']:,.2f} lbs"]
    L += [f"- {s}: {sum(simple[s].values()) / G_PER_LB:,.2f} lbs" for s in FLAG_STATES if simple[s]]
    L += ["", "## 6. Judgment calls and open items", "", "[Fill in before delivery: anything estimated, any SKU "
          "resolved by phone, and anything you should raise with counsel, such as whether you are the producer "
          "for a product.]", "",
          "This methodology explains our calculations. It is not legal advice on what you are obliged to report."]
    with open(os.path.join(outdir, "methodology.md"), "w") as f:
        f.write("\n".join(L) + "\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(0 if build(sys.argv[1]) else 1)
