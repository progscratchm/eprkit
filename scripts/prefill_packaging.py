#!/usr/bin/env python3
"""Pre-fill a brand's packaging sheet from its Shopify products export.

    python3 scripts/prefill_packaging.py clients/<brand>/input/products_export.csv [--out clients/<brand>/input/packaging-prefilled.csv]

Reads Shopify's standard product export (Handle, Title, Type, Tags, Variant SKU, Option values...).
For every SKU it guesses the primary packaging from the product name and type, and adds a default
shipping set. Every row is a GUESS: the brand checks it, fixes what is wrong and sets confirmed=Y.
build_reports.py flags any row not confirmed.

Output columns = templates/packaging-template.csv plus:
  product, guess_basis, confidence (high/medium/low), check_this, confirmed
"""
import argparse, csv, os, re, sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT_COLS = ["sku", "level", "component", "library_id", "qty", "max_units", "weight_g", "ca_id", "or_co_id",
            "plastic_components", "plastic_weight_g", "weight_source", "compostable",
            "product", "guess_basis", "confidence", "check_this", "confirmed"]

# Size-picking helpers: (fl oz capacity, library id)
GLASS_ROUND = [(1, "PKG-101"), (4, "PKG-102"), (8, "PKG-103"), (16, "PKG-104")]
GLASS_JAR = [(4, "PKG-105"), (8, "PKG-106")]
TUBE = [(1, "PKG-121"), (2, "PKG-122"), (6, "PKG-123")]
HDPE_BOTTLE = [(16, "PKG-112"), (32, "PKG-113")]
POUCH_KRAFT = [(4, "PKG-124"), (8, "PKG-125")]
CANDLE_TIN = [(4, "PKG-127"), (8, "PKG-128")]

# Rules are checked in order; first match wins. (name, keywords, builder)
def nearest(options, oz):
    if oz is None:   # no size in the name: take the smaller common size
        return options[0 if len(options) <= 2 else 1][1], False
    return min(options, key=lambda o: abs(o[0] - oz))[1], True

def r_unit(lib_id, note="", qty=1):
    return {"level": "unit", "library_id": lib_id, "qty": qty, "check_this": note}

def r_gap(component, note):
    return {"level": "unit", "component": component, "check_this": note}

RULES = [
    ("serum / oil / dropper", r"\b(serum|face oil|hair oil|body oil|oil|tincture|dropper|elixir|essence)\b",
     lambda oz: [r_unit(nearest(GLASS_ROUND, oz)[0], "Amber glass bottle assumed. Clear or plastic? Change it"),
                 r_gap("Glass dropper with rubber bulb", "Not in our library yet: give the supplier's gram weight or weigh 10")]),
    ("cream / balm / mask jar", r"\b(cream|balm|butter|mask|salve|pomade|scrub|polish|moisturi[sz]er)\b",
     lambda oz: [r_unit(nearest(GLASS_JAR, oz)[0], "Glass jar assumed. Plastic or tin jar? Change it"),
                 r_gap("Jar lid", "Not in our library yet: plastic or metal lid? Give the gram weight or weigh 10")]),
    ("sunscreen / tube", r"\b(sunscreen|spf|hand cream|lip|tube|toothpaste|gel)\b",
     lambda oz: [r_unit(nearest(TUBE, oz)[0], "Squeeze tube with flip cap assumed")]),
    ("shampoo / wash / lotion", r"\b(shampoo|conditioner|wash|cleanser|lotion|soap(?! bar)|liquid soap|toner|mist|spray)\b",
     lambda oz: [r_unit(nearest(HDPE_BOTTLE, oz)[0], "White HDPE bottle assumed. PET, glass or a different size? Change it"),
                 r_unit("PKG-117", "Snap-top cap assumed. Pump or sprayer? Change it")]),
    ("bar soap", r"\b(bar soap|soap bar|bar|shampoo bar)\b",
     lambda oz: [r_unit("PKG-096", "Paperboard carton assumed. Paper wrap or no wrap? Change it")]),
    ("supplement bottle", r"\b(capsule|capsules|softgel|tablet|vitamin|probiotic|gummies|gummy|supplement)\b",
     lambda oz: [r_unit("PKG-115", "250 cc white HDPE bottle assumed"),
                 r_gap("Bottle cap 45 mm with induction seal", "Not in our library yet: give the gram weight or weigh 10")]),
    ("powder", r"\b(powder|collagen|protein|greens|creatine|electrolyte)\b",
     lambda oz: [r_unit("PKG-126", "Plastic stand-up pouch assumed. Tub with scoop? Tell us")]),
    ("coffee / tea / snack", r"\b(coffee|beans|espresso|tea|granola|snack|chips|jerky|bark|cereal|nuts|blend)\b",
     lambda oz: [r_unit(nearest(POUCH_KRAFT, oz)[0], "Kraft/foil pouch assumed. All-plastic bag or tin? Change it")]),
    ("chocolate bar", r"\b(chocolate|candy|bar)\b",
     lambda oz: [r_gap("Bar wrapper", "Not in our library yet: paper, foil or plastic film? Weigh 10 wrappers")]),
    ("candle", r"\b(candle|wax melt)\b",
     lambda oz: [r_unit(nearest(CANDLE_TIN, oz)[0], "Steel tin with lid assumed. Glass vessel? Change it")]),
    ("jewelry / small item", r"\b(ring|necklace|earring|bracelet|jewelry|keychain|pin|sticker)\b",
     lambda oz: [r_unit("PKG-093", "Small paperboard box assumed")]),
]
APPAREL = (r"\b(t-?shirt|tee|tank|top|shirt|hoodie|sweatshirt|sweater|crew|jogger|pant|pants|short|shorts|legging|"
           r"bra|underwear|brief|boxer|sock|socks|dress|skirt|jacket|vest|coat|beanie|hat|cap|glove|scarf|"
           r"bikini|swim|robe|pajama|onesie)\b")
OUTERWEAR = r"\b(jacket|coat|parka|puffer|hoodie|sweatshirt|sweater|robe)\b"

def size_oz(text):
    m = re.search(r"(\d+(?:\.\d+)?)\s*(fl\.?\s*oz|oz|ounce)", text, re.I)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*ml\b", text, re.I)
    if m:
        return float(m.group(1)) / 29.57
    m = re.search(r"(\d+(?:\.\d+)?)\s*g\b", text, re.I)   # dry goods: grams ~ fl oz/28
    if m:
        return float(m.group(1)) / 28.35
    return None

def guess(product_text):
    t = product_text.lower()
    if re.search(APPAREL, t):
        big = bool(re.search(OUTERWEAR, t))
        unit = [r_unit("PKG-033" if big else "PKG-029",
                       "Clear poly bag assumed. No bag, or a paper bag? Change it")]
        ship = [{"level": "order", "library_id": "PKG-012" if big else "PKG-011", "max_units": 1 if big else 3,
                 "check_this": "Poly mailer assumed. Box? Change it. max_units = how many fit in one"}]
        return "apparel", unit, ship, "medium"
    oz = size_oz(t)
    for name, pat, build in RULES:
        if re.search(pat, t):
            rows = build(oz)
            if name == "shampoo / wash / lotion" and re.search(r"pump|lotion|body wash|hand wash|hand soap", t):
                rows[1] = r_unit("PKG-120", "Lotion pump assumed. Snap-top cap? Change it")
            conf = "high" if oz is not None and not any("Not in our library" in r["check_this"] for r in rows) else "medium"
            ship = [{"level": "order", "library_id": "PKG-059", "max_units": 4,
                     "check_this": "Mailer box assumed. Poly mailer or a different box? max_units = how many fit"},
                    {"level": "order", "library_id": "PKG-065", "check_this": "Paper fill assumed. None, air pillows or crinkle? Change it"}]
            return name, rows, ship, conf
    return "no match", [r_gap("Primary packaging", "We couldn't guess this one: describe or weigh the packaging")], \
        [{"level": "order", "library_id": "PKG-059", "max_units": 2, "check_this": "Mailer box assumed"}], "low"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("products")
    ap.add_argument("--out")
    a = ap.parse_args()
    out = a.out or os.path.join(os.path.dirname(a.products), "packaging-prefilled.csv")

    with open(a.products, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    # Shopify export: product fields only on the first row of each Handle
    products, last, skipped = [], {}, []
    for r in rows:
        h = r.get("Handle", "")
        if r.get("Title"):
            last = {"Title": r.get("Title", ""), "Type": r.get("Type", ""), "Tags": r.get("Tags", ""),
                    "Product Category": r.get("Product Category", "")}
        sku = (r.get("Variant SKU") or "").strip()
        if not sku:
            continue
        ships = (r.get("Variant Requires Shipping") or "TRUE").strip().upper()
        if ships == "FALSE" or re.search(r"gift card|e-?gift|digital", (last.get("Title", "") + " " + last.get("Type", "")).lower()):
            skipped.append(sku)
            continue
        opts = " ".join(r.get(k, "") for k in ("Option1 Value", "Option2 Value", "Option3 Value"))
        products.append((sku, f"{last.get('Title','')} {opts}".strip(),
                         " ".join([last.get("Title", ""), last.get("Type", ""), last.get("Product Category", ""),
                                   last.get("Tags", ""), opts])))

    out_rows, counts = [], {"high": 0, "medium": 0, "low": 0}
    for sku, label, text in products:
        basis, unit, ship, conf = guess(text)
        counts[conf] += 1
        ship = ship + [{"level": "order", "library_id": "PKG-084", "check_this": ""},
                       {"level": "order", "library_id": "PKG-085", "check_this": "Delete if you don't print packing slips"}]
        for r in unit + ship:
            row = {c: "" for c in OUT_COLS}
            row.update({"sku": sku, "qty": 1, "product": label, "guess_basis": basis, "confidence": conf,
                        "confirmed": ""})
            row.update({k: v for k, v in r.items() if v is not None})
            out_rows.append(row)

    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLS)
        w.writeheader(); w.writerows(out_rows)
    print(f"{len(products)} SKUs -> {len(out_rows)} rows -> {out}")
    if skipped:
        print(f"skipped {len(skipped)} SKUs that don't ship (gift cards, digital): {', '.join(skipped[:10])}")
    print(f"confidence: {counts['high']} high, {counts['medium']} medium, {counts['low']} low")

if __name__ == "__main__":
    main()
