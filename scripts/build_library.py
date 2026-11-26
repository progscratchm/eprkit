"""Build data/packaging-library.csv: common stock DTC packaging with calculated weights
and CA / OR-CO category mappings. Method and assumptions: docs/packaging-library-method.md
"""
import csv, os

IN2 = 0.00064516          # m2 per square inch
MIL = 25.4e-6             # m per mil
LB_MSF_TO_GSM = 453.592 / 92.903   # lb per 1000 sq ft -> g/m2 (4.8824)
REAM_3000_TO_GSM = 453.592 / 278.709  # lb per 3000 sq ft ream -> g/m2 (1.6275)

LDPE, HDPE, BOPP, ADH = 920, 950, 905, 1000   # kg/m3
C_32ECT_GSM = 110 * LB_MSF_TO_GSM              # 32 ECT C-flute combined board, 110 lb/MSF
E_FLUTE_GSM = (42 + 42 + 26 * 1.25) * LB_MSF_TO_GSM  # 42/26/42 E-flute, take-up 1.25
SBS_18PT_GSM = 290
TISSUE_GSM = 10 * 453.592 / (2880 * 0.092903)   # 10 lb tissue, 24x36x480 ream

rows = []
def add(name, ctype, role, dims, spec, mclass, material, ric, form, grams, method, basis,
        ca, ca_pc, or_id, sep, note=""):
    plastic = mclass.startswith("Plastic")
    rows.append({
        "id": f"PKG-{len(rows)+1:03d}", "name": name, "component_type": ctype, "role": role,
        "dimensions_in": dims, "spec": spec, "majority_material_class": mclass,
        "majority_material": material, "resin_code": ric, "plastic_form": form,
        "weight_g": round(grams, 1), "weight_lb": round(grams / 453.592, 4),
        "weight_method": method, "weight_basis": basis,
        "ca_calrecycle_id": ca, "ca_plastic_components": ca_pc,
        "ca_plastic_weight_g": round(grams, 1) if plastic and ca_pc != "" else 0,
        "or_co_category_id": or_id, "separability": sep, "mapping_note": note})

def film_g(area_in2, mil, density):
    return area_in2 * IN2 * mil * MIL * density * 1000

# 1. Poly mailers (LDPE co-ex, flat, 1.5in adhesive lip)
for w, l in [(6, 9), (7.5, 10.5), (9, 12), (10, 13), (12, 15.5), (14.5, 19), (19, 24), (24, 24)]:
    for mil in (2.0, 2.5, 3.0):
        a = w * (2 * l + 1.5)
        add(f"Poly mailer {w}x{l} in, {mil} mil", "mailer", "shipper", f"{w} x {l}",
            f"{mil} mil LDPE co-ex", "Plastic - Flexible", "LDPE", "4", "flexible",
            film_g(a, mil, LDPE), "calculated", f"2 plies x {w} x ({l}x2 + 1.5 lip) in, {mil} mil, 0.92 g/cm3",
            "25_P16P", 1, 53, "standalone",
            "Release liner on the adhesive strip is removed at packing and not counted")

# 2. Flat self-seal poly bags (apparel / product bags)
for w, l in [(4, 6), (6, 9), (9, 12), (11, 14), (12, 15), (14, 20)]:
    for mil in (1.5, 2.0):
        a = w * (2 * l + 1.5)
        add(f"Self-seal poly bag {w}x{l} in, {mil} mil", "bag", "primary_bag", f"{w} x {l}",
            f"{mil} mil LDPE clear", "Plastic - Flexible", "LDPE", "4", "flexible",
            film_g(a, mil, LDPE), "calculated", f"2 plies x {w} x ({l}x2 + 1.5 lip) in, {mil} mil, 0.92 g/cm3",
            "25_P16P", 1, 53, "standalone")

# 3. Regular slotted container (RSC) boxes, 32 ECT single wall C-flute
for L, W, H in [(6,6,6),(8,6,4),(8,8,8),(9,6,3),(10,8,6),(10,10,10),(12,9,6),(12,12,6),(12,12,12),
                (14,10,4),(14,14,14),(16,12,8),(16,16,16),(18,12,6),(18,18,18),(20,16,12),(24,18,12),(24,24,24)]:
    a = (2 * (L + W) + 1.5) * (H + W)
    add(f"Shipping box RSC {L}x{W}x{H} in, 32 ECT", "box", "shipper", f"{L} x {W} x {H}",
        "32 ECT single wall C-flute, kraft", "Paper/Fiber", "Corrugated cardboard", "", "",
        a * IN2 * C_32ECT_GSM, "calculated",
        f"Blank (2x({L}+{W}) + 1.5 glue flap) x ({H}+{W}) in at 110 lb/MSF",
        "25_PF9N", 0, 19, "standalone",
        "If plastic tape is counted as attached, CA may treat the box as 25_PF9P with tape as its plastic component; confirm with CAA guidance")

# 4. E-flute mailer boxes (roll end tuck front)
for L, W, H in [(6,4,2),(8,6,2),(9,6,4),(10,8,2),(10,8,4),(12,9,3),(12,9,4),(13,10,3),(14,10,4),(16,12,4)]:
    a = (2 * L * W + 3 * L * H + 6 * W * H) * 1.10
    add(f"Mailer box {L}x{W}x{H} in, E-flute", "box", "shipper", f"{L} x {W} x {H}",
        "Single wall E-flute, kraft or white", "Paper/Fiber", "Corrugated cardboard", "", "",
        a * IN2 * E_FLUTE_GSM, "calculated (approximate, +/-20%)",
        "Blank approx (2LW + 3LH + 6WH) x 1.10 at 42/26/42 E-flute, take-up 1.25",
        "25_PF9N", 0, 19, "standalone")

# 5. Kraft paper void fill (30 lb basis)
kgsm = 30 * REAM_3000_TO_GSM
for width, ft in [(15, 3), (15, 5), (24, 3), (24, 6)]:
    add(f"Kraft paper void fill, {width} in roll x {ft} ft", "void_fill", "fill", f"{width} x {ft*12}",
        "30 lb kraft", "Paper/Fiber", "Kraft paper", "", "",
        width * ft * 12 * IN2 * kgsm, "calculated", f"{width} x {ft*12} in at 30 lb/3000 sq ft (48.8 g/m2)",
        "25_PF1N", 0, 18, "standalone")

# 6. Crinkle paper fill (by weight)
for oz in (1, 2):
    add(f"Crinkle cut paper fill, {oz} oz", "void_fill", "fill", "",
        "Kraft crinkle paper", "Paper/Fiber", "Kraft paper", "", "",
        oz * 28.3495, "by definition", f"{oz} oz as dispensed", "25_PF1N", 0, 18, "standalone")

# 7. Air pillows (HDPE, 1.5 mil)
for w, l, n in [(4, 8, 1), (8, 8, 1), (4, 8, 10), (8, 8, 10)]:
    add(f"Air pillow {w}x{l} in, 1.5 mil" + (f", strip of {n}" if n > 1 else ""), "void_fill", "fill",
        f"{w} x {l}", "1.5 mil HDPE", "Plastic - Flexible", "HDPE", "2", "flexible",
        n * film_g(2 * w * l, 1.5, HDPE), "calculated", f"{n} x 2 plies x {w} x {l} in, 1.5 mil, 0.95 g/cm3",
        "25_P10P", n, 53, "standalone")

# 8. Carton sealing tape (BOPP + acrylic adhesive), 2 in wide
for total, film, adh in [(1.6, 1.0, 0.6), (2.0, 1.2, 0.8)]:
    for ft in (1, 3):
        a = 2 * 12 * ft
        g = film_g(a, film, BOPP) + film_g(a, adh, ADH)
        add(f"Packing tape 2 in, {total} mil, {ft} ft", "tape", "closure", f"2 x {ft*12}",
            f"{total} mil BOPP acrylic", "Plastic - Flexible", "PP", "5", "flexible", g, "calculated",
            f"{film} mil BOPP (0.905) + {adh} mil adhesive (1.0 assumed), 2 x {ft*12} in",
            "25_P22P", 1, 55, "attached, non-removable",
            "Mapping depends on whether tape is reported on its own or as a plastic component of the box")

# 9. Water-activated kraft paper tape (non-reinforced, 3 in)
for ft in (1, 3):
    gsm = 60 * REAM_3000_TO_GSM + 30
    add(f"Water-activated kraft tape 3 in, {ft} ft", "tape", "closure", f"3 x {ft*12}",
        "60 lb kraft + starch gum, non-reinforced", "Paper/Fiber", "Kraft paper", "", "",
        3 * 12 * ft * IN2 * gsm, "calculated (approximate)", "97.6 g/m2 kraft + ~30 g/m2 gum (assumed)",
        "25_PF1N", 0, 18, "attached, non-removable")

# 10. Tissue paper
for w, l, n in [(20, 30, 1), (20, 30, 2), (15, 20, 1)]:
    add(f"Tissue paper {w}x{l} in" + (f", {n} sheets" if n > 1 else ", 1 sheet"), "wrap", "insert",
        f"{w} x {l}", "10 lb tissue (~17 g/m2)", "Paper/Fiber", "Other paper", "", "",
        n * w * l * IN2 * TISSUE_GSM, "calculated", "10 lb basis on 24x36x480 ream (16.9 g/m2)",
        "25_PF12N", 0, 24, "standalone")

# 11. Shipping label and packing slip
add("Shipping label 4x6 in, direct thermal", "label", "label", "4 x 6", "Direct thermal paper, liner removed",
    "Paper/Fiber", "Other paper", "", "", 24 * IN2 * 95, "calculated (approximate)",
    "~75 g/m2 facestock + ~20 g/m2 adhesive (assumed); liner discarded at packing",
    "25_PF12N", 0, 24, "attached, non-removable", "Labels may be treated as part of the box; confirm")
add("Packing slip 8.5x11 in, 20 lb bond", "insert", "insert", "8.5 x 11", "20 lb bond (75 g/m2)",
    "Paper/Fiber", "White paper", "", "", 8.5 * 11 * IN2 * 75.2, "calculated", "8.5 x 11 in at 75.2 g/m2",
    "25_PF11N", 0, 4, "standalone",
    "Oregon covers printing and writing paper; whether CA counts a packing slip as packaging needs confirming")

# 12. Glassine bags (40 g/m2)
for w, l in [(4, 6), (6, 9), (9, 12)]:
    add(f"Glassine bag {w}x{l} in", "bag", "primary_bag", f"{w} x {l}", "40 g/m2 glassine",
        "Paper/Fiber", "Other paper", "", "", w * (2 * l + 1) * IN2 * 40, "calculated",
        f"2 plies x {w} x ({l}x2 + 1 flap) in at 40 g/m2", "25_PF12N", 0, 24, "standalone")

# 13. Flat kraft paper mailers (single ply, 120 g/m2)
for w, l in [(6, 9), (9, 12), (10, 13), (12, 15.5)]:
    add(f"Kraft paper mailer {w}x{l} in", "mailer", "shipper", f"{w} x {l}", "120 g/m2 kraft, single ply",
        "Paper/Fiber", "Kraft paper", "", "", w * (2 * l + 1.5) * IN2 * 120, "calculated (approximate)",
        f"2 plies x {w} x ({l}x2 + 1.5 lip) in at 120 g/m2 (assumed grade)", "25_PF1N", 0, 18, "standalone",
        "Adhesive strip liner removed at packing")

# 14. Folding cartons (SBS 18 pt, straight tuck end)
for L, W, H in [(2, 2, 5), (3, 3, 6), (4, 4, 4), (6, 4, 2)]:
    a = (2 * (L + W) + 0.6) * (H + 2 * (W + 0.75))
    add(f"Folding carton {L}x{W}x{H} in, 18 pt SBS", "carton", "primary_carton", f"{L} x {W} x {H}",
        "18 pt SBS paperboard, tuck end", "Paper/Fiber", "Paperboard", "", "",
        a * IN2 * SBS_18PT_GSM, "calculated (approximate, +/-20%)",
        "Blank (2x(L+W) + 0.6 glue) x (H + 2x(W + 0.75 tuck)) at ~290 g/m2", "25_PF10N", 0, 21, "standalone",
        "If laminated or window-patched, CA category becomes a 'w/ plastic component' or laminate code")

# 15. Corrugated pads
for w, l in [(12, 12), (18, 24)]:
    add(f"Corrugated pad {w}x{l} in, 32 ECT", "insert", "insert", f"{w} x {l}", "32 ECT single wall C-flute",
        "Paper/Fiber", "Corrugated cardboard", "", "", w * l * IN2 * C_32ECT_GSM, "calculated",
        "Area at 110 lb/MSF", "25_PF9N", 0, 19, "standalone")

# 16. Kraft wrapping sheets
for lb in (30, 50):
    add(f"Kraft wrapping sheet 24x36 in, {lb} lb", "wrap", "fill", "24 x 36", f"{lb} lb kraft",
        "Paper/Fiber", "Kraft paper", "", "", 24 * 36 * IN2 * lb * REAM_3000_TO_GSM, "calculated",
        f"{lb} lb/3000 sq ft ({lb*REAM_3000_TO_GSM:.1f} g/m2)", "25_PF1N", 0, 18, "standalone")

here = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(here, "..", "data", "packaging-library.csv")
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
print(len(rows), "entries ->", os.path.normpath(out))

# Validation against published weights
pm = film_g(10 * (2 * 13 + 1.5), 2.5, LDPE)
print(f"Check poly mailer 10x13 2.5 mil: {pm:.1f} g calc vs ~11.8 g published (26 lb / 1000 incl. carton)")
fefco = (2 * (575 + 385) + 35) * (225 + 385) / 1e6 * (175 + 175 + 140 * 1.44)
print(f"Check FEFCO C-flute 575x385x225 mm: {fefco:.0f} g calc vs 650 g published")
