#!/usr/bin/env python3
"""Play the brand's part: review the pre-filled sheet the way a careful brand would, and answer our questions.
Produces clients/_practice/input/{packaging.csv, bundles.csv, client.json}. Every edit here is something a real
brand would have to tell us; the practice-run notes count them.
"""
import csv, json, os, shutil
D = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(D, "raw", "packaging-prefilled.csv")
rows = list(csv.DictReader(open(src)))
cols = list(rows[0].keys())
edits = []

out = []
for r in rows:
    r = dict(r); r["confirmed"] = "Y"
    sku = r["sku"]
    if sku.endswith("-15") and sku.startswith("SER") and r["library_id"] == "PKG-101":
        r.update(library_id="", component="Amber glass Boston round 0.5 oz", weight_g="26", ca_id="25_G3N",
                 or_co_id="6", weight_source="brand weighed 10 bottles: 260 g")
        edits.append(f"{sku}: 0.5 oz bottle weighed (26 g) instead of the 1 oz library bottle (44 g)")
    if sku == "CND-85" and r["library_id"] == "PKG-139":
        r.update(library_id="", component="Ceramic tumbler 8.5 oz (supplier)", weight_g="340", ca_id="25_C1N",
                 or_co_id="7", weight_source="brand weighed 5 empty vessels: 1,700 g")
        edits.append("CND-85: vessel weighed 340 g vs our 275 g estimate")
    if sku == "DRY-5" and r["library_id"] == "PKG-141":
        r.update(plastic_weight_g="4.2", plastic_components="2",
                 weight_source="library PKG-141 + filler spec: valve and actuator 4.2 g")
        edits.append("DRY-5: filler gave valve + actuator plastic weight (4.2 g)")
    if sku in ("GUA-RQ", "GUA-JD") and not r["library_id"] and r["level"] == "unit":
        r.update(component="", library_id="PKG-096", check_this="")
        edits.append(f"{sku}: brand says 'kraft folding carton' (no match before)")
    if sku == "HB-1" and not r["library_id"] and r["level"] == "unit":
        r.update(component="", library_id="PKG-027")
        edits.append("HB-1: brand says 'clear poly bag'")
    out.append(r)

def add(sku, level, lib="", **kw):
    r = {c: "" for c in cols}; r.update(sku=sku, level=level, library_id=lib, qty=1, confirmed="Y"); r.update(kw)
    out.append(r)
# free sample sachets (not in the product export)
add("SAMPLE-SER", "unit", "PKG-149"); edits.append("SAMPLE-SER: brand added free sample sachet")
# discontinued SKUs still in 2026 orders
add("MSK-MATCHA", "unit", component="Glass jar 2 oz (discontinued mask)", weight_g="85", ca_id="25_G1N", or_co_id="6",
    weight_source="brand: supplier spec 85 g")
add("MSK-MATCHA", "unit", "PKG-146")
for lib, mu in (("PKG-059", 4), ("PKG-065", ""), ("PKG-084", ""), ("PKG-085", "")):
    add("MSK-MATCHA", "order", lib, max_units=mu)
add("SET-ORN25", "unit", "PKG-132")
for lib, mu in (("PKG-059", 2), ("PKG-065", ""), ("PKG-084", ""), ("PKG-085", "")):
    add("SET-ORN25", "order", lib, max_units=mu)
edits.append("MSK-MATCHA, SET-ORN25: discontinued, brand described their packaging")
# wholesale case packs
for lib, mu in (("PKG-048", 48), ("PKG-065", 48), ("PKG-084", 48)):
    add("_WHOLESALE", "order", lib, max_units=mu)
edits.append("_WHOLESALE: brand says retailer orders go in 16x12x8 cases of up to 48 units")

os.makedirs(os.path.join(D, "input"), exist_ok=True)
with open(os.path.join(D, "input", "packaging.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(out)
shutil.copy(os.path.join(D, "raw", "bundles-from-brand.csv"), os.path.join(D, "input", "bundles.csv"))
edits.append("bundles.csv: brand listed what's in 3 sets")
json.dump({"pickup_state": "OR", "wholesale_tags": ["wholesale"]}, open(os.path.join(D, "client.json"), "w"), indent=1)
edits.append("client.json: local pickup is at the Portland, OR studio")
print(len(edits), "brand answers needed:"); print("\n".join(" - " + e for e in edits))
