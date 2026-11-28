#!/usr/bin/env python3
"""Turn the raw Shopify bulk exports (saved by worker/shopify.js) into the files our scripts read.

    python3 scripts/shopify_to_csv.py <folder with *-orders.jsonl / *-products.jsonl> [--out clients/<brand>/input]

Writes, using the newest export of each kind:
  orders-shopify-api.csv   order_id, created_at, sku, quantity, ship_state, country, status   (build_reports.py)
  products_export.csv      Shopify product-export columns                                   (prefill_packaging.py)

Bulk JSONL is flat: each order or product is one line, and each line item or variant is its own line with
"__parentId" pointing at its parent. Test orders and line items that don't ship are left out. Quantity is
currentQuantity (after removals and refunds of items) when Shopify gives it.
"""
import argparse, csv, glob, json, os, sys


def newest(folder, kind):
    files = sorted(glob.glob(os.path.join(folder, f"*-{kind}.jsonl")))
    return files[-1] if files else None


def orders(path, out):
    heads, n_orders, n_lines, skipped = {}, 0, 0, 0
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            o = json.loads(line)
            pid = o.get("__parentId")
            if pid is None and "/Order/" in o.get("id", ""):
                heads[o["id"]] = o
                n_orders += 1
                continue
            parent = heads.get(pid)
            if parent is None:
                continue
            if parent.get("test") or o.get("requiresShipping") is False:
                skipped += 1
                continue
            qty = o.get("currentQuantity")
            qty = o.get("quantity") if qty is None else qty
            addr = parent.get("shippingAddress") or {}
            status = "cancelled" if parent.get("cancelledAt") else (parent.get("displayFinancialStatus") or "").lower()
            rows.append([parent.get("name") or parent["id"], (parent.get("createdAt") or "")[:10], o.get("sku") or "",
                         qty, addr.get("provinceCode") or "", addr.get("countryCodeV2") or "", status])
            n_lines += 1
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["order_id", "created_at", "sku", "quantity", "ship_state", "country", "status"])
        w.writerows(rows)
    blank_sku = sum(1 for r in rows if not r[2])
    print(f"orders: {n_orders} orders, {n_lines} line items -> {out}"
          f" ({skipped} test/non-shipping lines left out, {blank_sku} lines without a SKU)")


def products(path, out):
    prods, rows = {}, []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            o = json.loads(line)
            pid = o.get("__parentId")
            if pid is None and "/Product/" in o.get("id", ""):
                prods[o["id"]] = {"p": o, "variants": []}
            elif pid in prods:
                prods[pid]["variants"].append(o)
    cols = ["Handle", "Title", "Type", "Tags", "Vendor", "Status", "Option1 Name", "Option1 Value",
            "Option2 Name", "Option2 Value", "Option3 Name", "Option3 Value", "Variant SKU"]
    for entry in prods.values():
        p = entry["p"]
        for i, v in enumerate(entry["variants"] or [{}]):
            opts = (v.get("selectedOptions") or [])[:3]
            row = {"Handle": p.get("handle", ""), "Variant SKU": v.get("sku") or ""}
            if i == 0:   # same convention as Shopify's own export: product fields on the first row only
                row.update({"Title": p.get("title", ""), "Type": p.get("productType", ""),
                            "Tags": ", ".join(p.get("tags") or []), "Vendor": p.get("vendor", ""),
                            "Status": (p.get("status") or "").lower()})
            for k, opt in enumerate(opts, start=1):
                row[f"Option{k} Name"], row[f"Option{k} Value"] = opt.get("name", ""), opt.get("value", "")
            rows.append(row)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"products: {len(prods)} products, {len(rows)} variants -> {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--out")
    a = ap.parse_args()
    out = a.out or a.folder
    os.makedirs(out, exist_ok=True)
    o, p = newest(a.folder, "orders"), newest(a.folder, "products")
    if not o and not p:
        sys.exit(f"No *-orders.jsonl or *-products.jsonl in {a.folder}")
    if o:
        orders(o, os.path.join(out, "orders-shopify-api.csv"))
    if p:
        products(p, os.path.join(out, "products_export.csv"))


if __name__ == "__main__":
    main()
