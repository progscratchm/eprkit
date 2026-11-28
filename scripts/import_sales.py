#!/usr/bin/env python3
"""Turn any sales file a brand sends (CSV or Excel, from any store, 3PL, ERP or distributor) into the input files
build_reports.py reads.

    python3 scripts/import_sales.py <file.csv|file.xlsx> clients/<brand> [--kind orders|retail] [--name amazon]

What it does:
  1. Reads every sheet (Excel) or the file (CSV). Finds the header row even if there are title rows above it.
  2. Finds the columns it needs by name (many spellings) and, when names don't help, by what the values look like:
     a column of US state names or codes is the state, a column whose values match the brand's SKUs is the SKU,
     a column of whole numbers next to it is the quantity.
  3. Decides whether the file is ORDERS (one line per order line, with an order number and a ship-to state) or a
     RETAIL summary (units per SKU, maybe per state or retailer, no order numbers).
  4. Writes clients/<brand>/input/orders-<name>.csv or retail-<name>.csv with standard headers, and prints the
     mapping it used so a person can confirm it before the reports are built.
Nothing is guessed silently: anything it can't place is listed at the end.
"""
import argparse, csv, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_reports import norm_state, num, read_csv  # noqa: E402

NAMES = {
    "order_id": ["order_id", "order id", "order", "order #", "order number", "order no", "name", "amazon-order-id",
                 "sales order", "so number", "po number", "invoice", "invoice number", "shipment id"],
    "sku": ["sku", "lineitem sku", "seller-sku", "item sku", "product sku", "item", "item number", "item code",
            "product code", "upc", "style", "variant sku", "part number", "material"],
    "qty": ["qty", "quantity", "lineitem quantity", "quantity-shipped", "units", "units sold", "qty shipped",
            "shipped qty", "quantity shipped", "quantity-purchased", "quantity purchased", "eaches", "unit sales", "total units", "pos units"],
    "state": ["state", "ship_state", "ship state", "shipping province", "ship-state", "shipping state",
              "ship to state", "ship-to state", "province", "region", "st", "dest state", "destination state",
              "store state", "shipping province code"],
    "country": ["country", "shipping country", "ship-country", "ship to country", "country code"],
    "status": ["status", "financial status", "order status", "order-status"],
    "retailer": ["retailer", "customer", "account", "banner", "chain", "distributor", "customer name"],
    "date": ["date", "created at", "order date", "ship date", "purchase-date", "invoice date", "week ending"],
}


def norm(h):
    return re.sub(r"[\s_]+", " ", (h or "").strip().lower())


def read_any(path):
    """Return list of (sheet name, rows as lists)."""
    if path.lower().endswith((".xlsx", ".xlsm")):
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        return [(ws.title, [["" if c is None else str(c).strip() for c in row] for row in ws.iter_rows(values_only=True)])
                for ws in wb.worksheets]
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
        sample = f.read(4096); f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        return [("csv", [[c.strip() for c in row] for row in csv.reader(f, dialect)])]


def header_row(rows):
    """The first row in the top 20 with at least 3 non-empty cells that look like labels, not numbers."""
    for i, r in enumerate(rows[:20]):
        cells = [c for c in r if c]
        if len(cells) >= 3 and sum(1 for c in cells if not re.fullmatch(r"[\d.,$%-]+", c)) >= len(cells) * 0.7:
            return i
    return 0


def detect(headers, body, known_skus):
    cols, how = {}, {}
    hn = [norm(h) for h in headers]
    for field, names in NAMES.items():           # 1. by name
        for i, h in enumerate(hn):
            if h in names and i not in cols.values():
                cols[field], how[field] = i, f'column "{headers[i]}" (by name)'
                break
    FUZZY = {"order_id": r"\border\b|\binvoice\b", "sku": r"\bsku\b|\bitem\b|\bupc\b|product code",
             "qty": r"\bqty\b|quantit|\bunits?\b|\beaches\b", "state": r"\bstate\b|\bst\b|province",
             "country": r"country", "retailer": r"customer|retailer|account|chain|distributor|banner"}
    for field, pat in FUZZY.items():              # 1b. by a keyword in the name
        if field in cols:
            continue
        for i, h in enumerate(hn):
            if re.search(pat, h) and i not in cols.values() and not re.search(r"\$|price|amount|sales \$|revenue|net", h):
                cols[field], how[field] = i, f'column "{headers[i]}" (by name)'
                break
    sample = body[:500]
    def share(i, test):
        vals = [r[i] for r in sample if i < len(r) and r[i]]
        return (sum(1 for v in vals if test(v)) / len(vals)) if vals else 0
    free = [i for i in range(len(headers)) if i not in cols.values()]
    if "state" not in cols:                       # 2. by content
        best = max(free, key=lambda i: share(i, lambda v: norm_state(v) is not None), default=None)
        if best is not None and share(best, lambda v: norm_state(v) is not None) > 0.8:
            cols["state"], how["state"] = best, f'column "{headers[best]}" (values look like US states)'
    if "sku" not in cols and known_skus:
        free = [i for i in range(len(headers)) if i not in cols.values()]
        best = max(free, key=lambda i: share(i, lambda v: v in known_skus), default=None)
        if best is not None and share(best, lambda v: v in known_skus) > 0.5:
            cols["sku"], how["sku"] = best, f'column "{headers[best]}" (values match your SKUs)'
    if "qty" not in cols:
        free = [i for i in range(len(headers)) if i not in cols.values()]
        ints = [i for i in free if share(i, lambda v: re.fullmatch(r"\d{1,6}(\.0+)?", v.replace(",", "")) is not None) > 0.9]
        if len(ints) == 1:
            cols["qty"], how["qty"] = ints[0], f'column "{headers[ints[0]]}" (only whole-number column)'
    return cols, how


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file"); ap.add_argument("client")
    ap.add_argument("--kind", choices=["orders", "retail"])
    ap.add_argument("--name", help="short name for the output file, e.g. amazon or unfi")
    a = ap.parse_args()
    indir = os.path.join(a.client, "input"); os.makedirs(indir, exist_ok=True)
    known = set()
    pk = os.path.join(indir, "packaging.csv")
    if os.path.exists(pk):
        known = {r["sku"].strip() for r in read_csv(pk) if r.get("sku")}
    name = a.name or re.sub(r"[^a-z0-9]+", "-", os.path.splitext(os.path.basename(a.file))[0].lower()).strip("-")

    problems, written = [], []
    for sheet, rows in read_any(a.file):
        rows = [r for r in rows if any(c for c in r)]
        if len(rows) < 2:
            continue
        h = header_row(rows)
        headers, body = rows[h], rows[h + 1:]
        cols, how = detect(headers, body, known)
        if "sku" not in cols or "qty" not in cols:
            problems.append(f"sheet {sheet!r}: couldn't find {'SKU' if 'sku' not in cols else 'quantity'} column; "
                            f"headers were {headers}")
            continue
        kind = a.kind or ("orders" if "order_id" in cols and "state" in cols else "retail")
        get = lambda r, f: (r[cols[f]] if f in cols and cols[f] < len(r) else "")
        out_rows, skipped = [], 0
        for r in body:
            sku, q = get(r, "sku"), num(get(r, "qty"), 0)
            if not sku or q == 0 or re.fullmatch(r"(?i)(grand )?total|subtotal", sku):
                skipped += 1; continue
            if kind == "orders":
                out_rows.append({"order_id": get(r, "order_id"), "sku": sku, "qty": q, "state": get(r, "state"),
                                 "country": get(r, "country") or "US", "status": get(r, "status")})
            else:
                out_rows.append({"sku": sku, "units": q, "state": get(r, "state"), "retailer": get(r, "retailer"),
                                 "source": f"{os.path.basename(a.file)} / {sheet}"})
        suffix = "" if len(read_any(a.file)) == 1 else "-" + re.sub(r"[^a-z0-9]+", "-", sheet.lower()).strip("-")
        out = os.path.join(indir, f"{kind}-{name}{suffix}.csv")
        with open(out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()) if out_rows else ["sku"]); w.writeheader(); w.writerows(out_rows)
        written.append(out)
        print(f"\n{os.path.basename(a.file)} / {sheet}: read as {kind.upper()}, header on row {h + 1}, {len(out_rows):,} lines kept, {skipped:,} skipped (blank, zero or total rows)")
        for field in ("order_id", "sku", "qty", "state", "country", "status", "retailer"):
            if field in how:
                print(f"  {field:9} <- {how[field]}")
        if kind == "orders" and "state" not in cols:
            problems.append(f"{sheet}: no ship-to state column found: orders can't be placed in a state")
        if known:
            miss = {r["sku"] for r in out_rows} - known
            if miss:
                problems.append(f"{sheet}: {len(miss)} SKUs not in packaging.csv yet: {', '.join(sorted(miss)[:12])}")
        if kind == "retail" and "state" in cols:
            bad = {r["state"] for r in out_rows if r["state"] and not norm_state(r["state"])}
            if bad:
                problems.append(f"{sheet}: state values we don't recognise: {', '.join(sorted(bad)[:10])}")
    print("\nWritten:", *written, sep="\n  ")
    if problems:
        print("\nCheck before building:", *problems, sep="\n  - ")
    return 0 if written else 1


if __name__ == "__main__":
    sys.exit(main())
