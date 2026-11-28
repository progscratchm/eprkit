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
        ca, ca_pc, or_id, sep, note="", plastic_g=None):
    plastic = mclass.startswith("Plastic")
    rows.append({
        "id": f"PKG-{len(rows)+1:03d}", "name": name, "component_type": ctype, "role": role,
        "dimensions_in": dims, "spec": spec, "majority_material_class": mclass,
        "majority_material": material, "resin_code": ric, "plastic_form": form,
        "weight_g": round(grams, 1), "weight_lb": round(grams / 453.592, 4),
        "weight_method": method, "weight_basis": basis,
        "ca_calrecycle_id": ca, "ca_plastic_components": ca_pc,
        "ca_plastic_weight_g": round(plastic_g, 1) if plastic_g is not None else (round(grams, 1) if plastic and ca_pc != "" else 0),
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


# ================================================================ PRIMARY PACKAGING (added Nov 2026)
# Rigid containers can't be calculated from dimensions (wall thickness varies), so weights are published
# supplier gram weights for a specific stock item. Treat them as typical and weigh a sample when a brand's
# supplier differs. California "small" categories apply when two or more sides are 2 in or less; Oregon and
# Colorado have matching small-format categories for plastic (58), metal (15) and paper (25).
PUB = "published"
GLASS_NOTE = ("Glass with a paper label or no label. A plastic label or shrink band makes it 'w/ plastic component' "
              "(25_G1P / 25_G3P) and the label counts as a plastic component. The cap is a separate item.")

# 17. Amber glass Boston round bottles (Uline gram weights; 1-4 oz are 2 in diameter or less: small format)
for oz, g, dia, ht, src in [(1, 44, 1.25, 3.2, "Uline S-20888 spec sheet, 44 +/- 3 g"),
                            (4, 108, 1.9, 4.5, "Uline S-15649 spec sheet, 108 +/- 7 g"),
                            (8, 165, 2.4, 5.4, "Uline S-23396 spec sheet, 165 +/- 5 g"),
                            (16, 250, 2.9, 6.6, "Uline S-15651 spec sheet, 250 +/- 10 g")]:
    small = dia <= 2
    add(f"Glass Boston round bottle {oz} oz, amber", "bottle", "primary", f"{dia} dia x {ht}",
        "Type III soda-lime glass, narrow neck", "Glass", "Glass", "", "", g, PUB, src,
        "25_G3N" if small else "25_G1N", "", 6, "separate from cap", GLASS_NOTE)

# 18. Clear glass straight-sided jars
for oz, finish, g, dia, src in [(4, "58-400", 114, 2.6, "TricorBraun 052087, 114 g"),
                                (8, "58-400", 184, 2.9, "TricorBraun 012092, 184 g"),
                                (8, "70-400", 200, 2.9, "TricorBraun 052093 200.2 g; Uline S-17983 7.06 oz (200 g)")]:
    add(f"Glass straight-sided jar {oz} oz, {finish}", "jar", "primary", f"{dia} dia",
        f"Clear soda-lime glass, {finish} neck", "Glass", "Glass", "", "", g, PUB, src,
        "25_G1N", "", 6, "separate from lid", GLASS_NOTE)

# 19. PET bottles
for name, g, ca, orid, src in [
        ("PET squat Boston round bottle 100 ml (3.4 oz), white", 16, "25_P2P", 27, "Supplier datasheet 119-188, 16 g"),
        ("PET Boston round bottle 16 oz, clear", 37.3, "25_P1P", 26, "Uline S-21697 spec sheet, 37.3 +/- 3 g"),
        ("PET squat Boston round bottle 16 oz, clear", 41.3, "25_P1P", 26, "The Cary Company 16 oz squat, 0.091 lb")]:
    add(name, "bottle", "primary", "", "PET #1", "Plastic - Rigid", "PET", "1", "rigid", g, PUB, src,
        ca, 1, orid, "separate from cap", "The cap or pump is a separate plastic component")

# 20. HDPE bottles and supplement packers
for name, g, ca, orid, src in [
        ("HDPE Boston round bottle 16 oz, natural", 33, "25_P6P", 32, "Uline S-17977 spec sheet, 33 g"),
        ("HDPE cylinder bottle 16 oz, white", 34, "25_P7P", 33, "The Cary Company 30W15W, 34 g"),
        ("HDPE cylinder bottle 32 oz, white", 58, "25_P7P", 33, "The Cary Company 30WQW3, 58 g"),
        ("HDPE packer bottle 150 cc, white, 38-400", 16.5, "25_P7P", 33, "TricorBraun SET-104-150XC, 16.5 g"),
        ("HDPE packer bottle 250 cc, white, 45-400", 27.5, "25_P7P", 33, "TricorBraun 305520, 27.5 g"),
        ("HDPE packer bottle 250 cc, natural, 48-400", 19.0, "25_P6P", 32, "TricorBraun 025952, 19.0 g")]:
    add(name, "bottle", "primary", "", "HDPE #2", "Plastic - Rigid", "HDPE", "2", "rigid", g, PUB, src,
        ca, 1, orid, "separate from cap",
        "Supplement bottles often add an induction seal liner, cotton or a desiccant: list those separately")

# 21. Closures and dispensers (all small format: two sides 2 in or less)
for name, g, src, note in [
        ("Snap-top cap 28-410, PP", 6.35, "The Cary Company 28-410 smooth snap top, 6.35 g", ""),
        ("Lotion pump 24-410, PP, 2 cc", 11.4, "O.Berk 28810075, 11.4 g",
         "Most pumps have a steel spring; it stays with the pump in this category"),
        ("Lotion pump 24-410, mono-material PP, 1.5 cc", 10.5, "O.Berk 1012639, 10.5 g", "Metal-free spring"),
        ("Lotion pump 28-410, e-commerce lock, 4 cc", 16.4, "O.Berk 10122275, 16.4 g",
         "Most pumps have a steel spring; it stays with the pump in this category")]:
    add(name, "closure", "closure", "", "Polypropylene", "Plastic - Other", "PP", "5", "rigid", g, PUB, src,
        "25_P47P", 1, 58, "separate from bottle", note)

# 22. LDPE squeeze tubes with PP flip cap (weight is tube + cap; 2 plastic components)
for oz, g, dia, ht, src in [(1, 7.4, 1.0, 3.5, "Container & Packaging M1300WH, 0.26 oz"),
                            (2, 10.8, 1.4, 4.7, "Container & Packaging M1306WH, 0.38 oz"),
                            (6, 29.2, 1.5, 7.5, "Container & Packaging M1303WH, 1.03 oz")]:
    small = oz == 1  # flattened crimp end of 2 oz and larger tubes is wider than 2 in
    add(f"LDPE squeeze tube {oz} oz with flip cap", "tube", "primary", f"{dia} dia x {ht}",
        "LDPE 5-layer tube, PP flip cap", "Plastic - Other" if small else "Plastic - Rigid", "LDPE", "4", "rigid",
        g, PUB, src, "25_P47P" if small else "25_P14P", 2, 58 if small else 41, "cap attached in use",
        "Tube body and flip cap are 2 plastic components. Split the cap (about 2-3 g, PP) out if your supplier "
        "lists it separately")

# 23. Stand-up pouches (weights are case weight / 1000 incl. the carton: an upper bound)
for name, g, mclass, ca, orid, src, plastic_g, note in [
        ("Stand-up pouch 4 oz, kraft/foil/LLDPE, zipper", 10.9, "Paper/Fiber", "25_PF7P", 23,
         "International Plastics SU-1.7-KRAFT, 24.1 lb per 1000", 4.4,
         "Kraft is the majority material. Plastic share (LLDPE layer + zipper) estimated at 40%: confirm with supplier"),
        ("Stand-up pouch 8 oz, kraft/foil/LLDPE, zipper", 13.8, "Paper/Fiber", "25_PF7P", 23,
         "International Plastics SU-1.9-KRAFT, 30.4 lb per 1000", 5.5,
         "Kraft is the majority material. Plastic share (LLDPE layer + zipper) estimated at 40%: confirm with supplier"),
        ("Stand-up pouch 8 oz, PET/LLDPE with window, zipper", 15.9, "Plastic - Flexible", "25_P46P", 57,
         "International Plastics SU-9.4, 35 lb per 1000", None, "All-plastic laminate")]:
    add(name, "pouch", "primary", "", "Laminate", mclass, "Multi-material laminate", "", "flexible", g, PUB, src,
        ca, 1, orid, "standalone", note, plastic_g)

# 24. Tinplate steel tins (calculated: 0.22 mm tinplate, 7.85 g/cm3; body + base + lid top + 0.3 in lid skirt)
def tin_g(dia_in, h_in):
    r = dia_in / 2
    area_in2 = 3.14159 * dia_in * h_in + 2 * 3.14159 * r * r + 3.14159 * dia_in * 0.3
    return area_in2 * 6.4516 * 0.022 * 7.85
for name, d, h in [("Candle tin 4 oz with lid, steel", 2.5625, 1.8125), ("Candle tin 8 oz with lid, steel", 3.125, 2.0),
                   ("Screw-top tin 2 oz, shallow, steel", 2.5, 0.875), ("Screw-top tin 4 oz, deep, steel", 2.5, 1.75),
                   ("Screw-top tin 8 oz, deep, steel", 3.125, 2.0)]:
    add(name, "tin", "primary", f"{d} dia x {h}", "Tinplate steel, ~0.22 mm", "Metal", "Tinplate steel", "", "",
        tin_g(d, h), "calculated", f"Body {d} x {h} in + base + lid, 0.22 mm tinplate at 7.85 g/cm3 (gauge assumed)",
        "25_M6N", "", 12, "lid stays with tin",
        "Height is 2 in or less but the diameter is over 2 in, so only one side qualifies: not small format")

# 25. Rigid two-piece gift boxes (1.5 mm grey chipboard ~900 g/m2 + 120 g/m2 wrap paper, calculated)
for L, W, H in [(6, 6, 3), (10, 8, 3)]:
    base = L * W + 2 * (L + W) * H
    lid = L * W + 2 * (L + W) * 1.0
    gsm = 900 + 120 * 1.25
    add(f"Rigid two-piece gift box {L}x{W}x{H} in", "box", "primary", f"{L} x {W} x {H}",
        "1.5 mm chipboard, paper wrapped", "Paper/Fiber", "Paperboard", "", "", (base + lid) * IN2 * gsm,
        "calculated", "Base + 1 in deep lid; 900 g/m2 board + wrap paper with 25% turn-in",
        "25_PF10N", 0, 21, "standalone",
        "Magnetic closures or a plastic insert make it 'w/ plastic component' or add separate items")

# ================================================================ GAPS FOR WAVE-1 BRANDS (added Nov 28, 2026)
# Serum droppers, coffee bags, ceramic candle vessels, aerosol cans, stick packs and bar wrappers.
# "case weight / count" figures include the shipping carton, so they are an upper bound.

# 26. Glass dropper assembly for 1 oz Boston round (20-400), split into its three parts.
# Whole assembly: Container & Packaging M652BK-L25, 230.72 oz per case of 1,080 = 6.06 g each.
# The split between parts is our estimate (glass tube 7 x 76 mm, ~0.8 mm wall): ask the supplier or weigh one.
DROP_SRC = "Container & Packaging M652BK-L25: 230.72 oz / 1,080 per case = 6.06 g per assembly; split estimated"
for name, g, mclass, mat, ric, form, ca, ca_pc, orid, note in [
        ("Dropper pipette, glass 7 x 76 mm (1 oz dropper)", 2.5, "Glass", "Glass", "", "", "25_G3N", "", 6,
         "Part of a dropper assembly: report it alongside the collar and bulb"),
        ("Dropper collar, PP ribbed skirt 20-400 (1 oz dropper)", 2.3, "Plastic - Other", "PP", "5", "rigid",
         "25_P47P", 1, 58, "Part of a dropper assembly"),
        ("Dropper bulb, rubber (1 oz dropper)", 1.3, "Plastic - Other", "Rubber/elastomer", "7", "rigid",
         "25_P47P", 1, 58,
         "Synthetic rubber, silicone or TPE bulbs are treated as plastic here (the cautious reading). A natural "
         "rubber bulb may fall outside the plastic categories: confirm with CAA")]:
    add(name, "closure", "closure", "", "Dropper assembly part", mclass, mat, ric, form, g,
        "estimated (from published assembly weight)", DROP_SRC, ca, ca_pc, orid, "separate from bottle", note)

# 27. Coffee bags with one-way degassing valve (block bottom). Layer spec from NFC Bags ABV12K:
# 25 lb kraft / 5 lb LDPE / 48 ga met PET / 2 mil LLDPE -> plastic layers are ~64% of the weight,
# so plastic is the majority material: Multi-Material Laminate - Pouches (CA 25_P46P, OR/CO 57).
kraft = 25 * REAM_3000_TO_GSM; ldpe5 = 5 * REAM_3000_TO_GSM
pet48 = 12.2e-6 * 1390 * 1000; lldpe2 = 2 * MIL * LDPE * 1000
plastic_share = (ldpe5 + pet48 + lldpe2) / (kraft + ldpe5 + pet48 + lldpe2)
bag1lb = 16 * 453.592 / 500   # Mr Takeout Bags XFSASUBBZ-075-VALVE: 16 lb per case of 500
area = lambda w, h, d: 2 * w * h + 2 * d * h + w * d
for size, g, dims, method, basis in [
        ("1 lb", bag1lb, "5 x 9.5 x 3.125", "published (case weight / count)",
         "Mr Takeout Bags XFSASUBBZ-075-VALVE, 16 lb per case of 500 incl. carton"),
        ("12 oz", bag1lb * area(5, 7.875, 3.125) / area(5, 9.5, 3.125), "5 x 7.875 x 3.125", "calculated",
         "1 lb bag weight scaled by panel area to a 5 x 7.875 x 3.125 in 12 oz bag")]:
    add(f"Coffee bag {size}, kraft laminate, one-way valve", "pouch", "primary", dims,
        "Kraft / LDPE / met PET / LLDPE, degassing valve, tin tie or zipper", "Plastic - Flexible",
        "Multi-material laminate", "", "flexible", g, method, basis, "25_P46P", 2, 57, "standalone",
        f"Plastic layers are ~{plastic_share*100:.0f}% of the weight (layer spec NFC Bags ABV12K), so the bag is "
        "plastic-majority even though it looks like paper. Valve counts as a second plastic component. "
        "A foil (ALU) layer instead of met PET changes the split: check the supplier spec. A metal tin tie is a separate item",
        g)

# 28. Ceramic candle vessels (calculated from published dimensions; stoneware 2.3 g/cm3, 6 mm base: +/-25%)
import math
def ceramic_g(od_cm, id_cm, h_cm, base_cm=0.6, rho=2.3):
    wall = math.pi / 4 * (od_cm**2 - id_cm**2) * h_cm
    base = math.pi / 4 * id_cm**2 * base_cm
    return (wall + base) * rho
for name, od, idm, h, src in [
        ("Ceramic candle tumbler 8.5 oz wax", 7.62, 6.78, 10.29, "CandleScience White Dream Ceramic Tumbler: 3.00 in OD, 2.67 in ID, 4.05 in tall"),
        ("Ceramic candle tumbler mini 5 oz wax", 8.26, 7.62, 5.41, "CandleScience Mini Modern Ceramic Tumbler: 3.25 in OD, 3.00 in ID, 2.13 in tall")]:
    add(name, "jar", "primary", f"{od/2.54:.2f} dia x {h/2.54:.2f}", "Glazed ceramic/stoneware", "Ceramic", "Ceramic",
        "", "", ceramic_g(od, idm, h), "calculated (approximate, +/-25%)",
        f"{src}; wall volume + 6 mm base at 2.3 g/cm3", "25_C1N", "", 7, "separate from lid",
        "Wood, cork or bamboo lids are separate items (Wood/Organics). A refill vessel sold once and refilled "
        "is reported when sold, not at each refill. Weigh one empty vessel to replace this estimate")

# 29. Aluminium aerosol can (cosmetics, 150 ml fill)
add("Aluminium aerosol can 45 x 150 mm (150 ml fill)", "can", "primary", "1.77 dia x 5.9",
    "Impact-extruded aluminium, 1 in opening", "Metal", "Aluminium", "", "", 22.9, PUB,
    "Fidel-Fillaud ref 26224, 45 x 150 mm coated aluminium aerosol can, 0.02289 kg", "25_M4P", 2, 10,
    "valve stays with can",
    "California only has a 'w/ plastic component' aerosol category: the valve and actuator are the plastic "
    "components (count 2). Add the actuator and valve weight from the filler or supplier; an overcap is a separate "
    "plastic item. One side is under 2 in, the other is not: not small format", 0)

# 30. Twist-up stick containers (deodorant, sunscreen and balm sticks)
add("Stick container 2.5 oz oval, PP, twist-up with cap", "tube", "primary", "2.25 x 1.24 x 4.58",
    "PP body, elevator, dial and cap", "Plastic - Rigid", "PP", "5", "rigid", 464 * 28.3495 / 450,
    "published (case weight / count)", "Container & Packaging M17375WH: 464 oz per case of 450 incl. carton",
    "25_P41P", 3, 43, "cap attached in use",
    "Body with dial, elevator and cap counted as 3 plastic components. Only one side is 2 in or less, so it is "
    "not small format")

# 31. Bar and chocolate wrappers (calculated; +/-30%)
OPP_LAM_GSM = 16.4 * 2 + 2   # two 18 um OPP films (Jindal: 16.4 g/m2 each) + adhesive
for name, w, h, L in [("Snack bar flow wrap, met OPP laminate (40-50 g bar)", 1.4, 0.6, 5.5)]:
    blank = (2 * (w + h) + 0.6) * (L + h + 1.0)
    add(name, "wrapper", "primary", f"{L} x {w} x {h} bar", "OPP / met OPP laminate, fin seal", "Plastic - Flexible",
        "PP", "5", "flexible", blank * IN2 * OPP_LAM_GSM, "calculated (approximate, +/-30%)",
        f"Blank (2x({w}+{h}) + 0.6 fin) x ({L}+{h}+1.0 end seals) in at ~35 g/m2 (2 x 18 um OPP, Jindal Films datasheet)",
        "25_P22P", 1, 55, "standalone",
        "Mono-PP laminate. A PET/PE or paper-based wrapper maps to a different category")
foil_gsm = 9e-6 * 2700 * 1000
add("Chocolate bar inner foil, aluminium 9 um (2.5-3 oz bar)", "wrapper", "primary", "8 x 7 sheet",
    "Plain aluminium foil", "Metal", "Aluminium", "", "", 8 * 7 * IN2 * foil_gsm, "calculated",
    "8 x 7 in sheet of 9 um aluminium at 2.7 g/cm3", "25_M2N", "", 9, "standalone",
    "Paper-backed or lacquered foil may count as 'w/ plastic component': check the supplier spec")
add("Chocolate bar sleeve, paperboard ~16 pt (2.5-3 oz bar)", "carton", "secondary", "6.5 x 3.25 x 0.4",
    "Folding paperboard sleeve", "Paper/Fiber", "Paperboard", "", "", (2 * (3.25 + 0.4) + 0.5) * 6.5 * IN2 * 250,
    "calculated", "Blank (2x(3.25+0.4) + 0.5 glue) x 6.5 in at ~250 g/m2", "25_PF10N", 0, 21, "standalone",
    "A paper wrapper instead of a board sleeve maps to White Paper (25_PF11N)")

# 32. Jar lids, lip balm tube and sample sachets (added Nov 28, 2026, from the practice run)
for name, g, src in [
        ("Jar lid 58-400, PP smooth, lined", 5.8, "Supplier drawing DWG32006, 58-400 PP smooth cap with PS22 liner: part weight 5.80 +/- 1.5 g"),
        ("Jar lid 70-400, PP smooth, PS liner", 0.37 * 28.3495, "Container & Packaging L461WHP1, 0.37 oz")]:
    add(name, "closure", "closure", "", "Polypropylene", "Plastic - Rigid", "PP", "5", "rigid", g, PUB, src,
        "25_P41P", 1, 43, "separate from jar",
        "Over 2 in across, so not small format. A foam or paper liner stays with the lid")
add("Lip balm tube 0.15 oz with cap, PP", "tube", "primary", "0.6 dia x 2.7", "PP tube, elevator and cap",
    "Plastic - Other", "PP", "5", "rigid", 0.016 * 453.592, PUB, "US Plastic 102841 (Federal Package), 0.016 lb",
    "25_P47P", 3, 58, "cap attached in use", "Tube, elevator and cap counted as 3 plastic components. Small format")
SACHET_GSM = 12 * 1.39 + 7 * 2.7 + 50 * 0.92    # 12 um PET / 7 um ALU / 50 um PE
add("Sample sachet 2 x 3 in, PET/foil/PE", "pouch", "primary", "2 x 3", "Laminate sachet, heat sealed",
    "Plastic - Flexible", "Multi-material laminate", "", "flexible", 2 * 2 * 3 * IN2 * SACHET_GSM,
    "calculated", "2 plies of 2 x 3 in, 12 um PET / 7 um ALU / 50 um PE (~81 g/m2)", "25_P46P", 1, 57, "standalone",
    "Free samples count too: they are packaging shipped into the state")

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
