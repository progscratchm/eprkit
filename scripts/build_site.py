"""Generate the static pages of eprkit.com that share a layout (everything except index.html),
plus the sample report files and the category lookup data.
Run: python3 scripts/build_site.py   (writes into site/)
"""
import csv, json, os, html

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SITE = os.path.join(ROOT, "site")
DATA = os.path.join(ROOT, "data")
CHECKED = "November 26, 2026"

def rd(name):
    with open(os.path.join(DATA, name)) as f:
        return list(csv.DictReader(f))

CA = rd("ca-cmc-2026.csv")
ORC = rd("or-co-categories.csv")
LIB = rd("packaging-library.csv")
ca_by_id = {r["calrecycle_id"]: r for r in CA}
or_by_id = {r["id"]: r for r in ORC}
lib_by_name = {r["name"]: r for r in LIB}

HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} | EPR Kit</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{title} | EPR Kit">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="https://eprkit.com/og.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/style.css">
</head>
<body>
<header class="top"><div class="wrap">
  <a class="logo" href="/"><svg viewBox="0 0 64 64" width="28" height="28" aria-hidden="true" style="vertical-align:-7px;margin-right:8px"><rect width="64" height="64" rx="14" fill="#1d6b47"/><path d="M32 11 L51 20.5 L32 30 L13 20.5 Z" fill="#bfe3cf"/><path d="M13 20.5 L32 30 L32 53 L13 43.5 Z" fill="#ffffff"/><path d="M51 20.5 L51 43.5 L32 53 L32 30 Z" fill="#d9ece0"/><path d="M18 36.5 L22.5 41.5 L28.5 32.5" fill="none" stroke="#1d6b47" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round"/></svg>EPR<span> Kit</span></a>
  <nav>
    <a href="/guides/">Guides</a>
    <a href="/lookup.html">Category lookup</a>
    <a href="/methodology.html">Methodology</a>
    <a href="/sample-report.html">Sample report</a>
    <a class="btn small" href="/#pricing">Book your filing</a>
  </nav>
</div></header>
<main class="page"><div class="wrap narrow">
"""

FOOT = """
</div></main>
<footer><div class="wrap">
  <b>EPR Kit</b> &middot; 418 Broadway, Ste N, Albany, NY 12207 &middot; <a href="mailto:support@eprkit.com">support@eprkit.com</a><br>
  <a href="/privacy.html">Privacy</a> &middot; <a href="/terms.html">Terms</a> &middot; <a href="/changes.html">Rule changes log</a> &middot; Regulatory information last checked {checked}.<br>
  EPR Kit prepares packaging report data and is not a law firm. Each brand submits its own report under its own account.
</div></footer>
</body>
</html>
"""

def page(path, title, desc, body):
    full = os.path.join(SITE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as f:
        f.write(HEAD.format(title=html.escape(title), desc=html.escape(desc)) + body + FOOT.format(checked=CHECKED))

def esc(s):
    return html.escape(str(s))

# ---------------------------------------------------------------- sample report
# A fictional apparel brand: three products, packaging per product, orders per state.
SKUS = [
    {"sku": "TEE-01", "name": "Organic cotton tee", "parts": ["Self-seal poly bag 9x12 in, 1.5 mil", "Poly mailer 10x13 in, 2.5 mil"]},
    {"sku": "HOOD-01", "name": "Fleece hoodie", "parts": ["Self-seal poly bag 12x15 in, 2.0 mil", "Poly mailer 14.5x19 in, 2.5 mil"]},
    {"sku": "GIFT-01", "name": "Gift box set", "parts": ["Folding carton 6x4x2 in, 18 pt SBS", "Shipping box RSC 10x8x6 in, 32 ECT",
                                                         "Kraft paper void fill, 15 in roll x 3 ft", "Packing tape 2 in, 2.0 mil, 3 ft",
                                                         "Tissue paper 20x30 in, 1 sheet"]},
]
PER_ORDER = ["Shipping label 4x6 in, direct thermal", "Packing slip 8.5x11 in, 20 lb bond"]
UNITS = {  # units shipped in 2025 (fictional); each unit ships as one order
    "California": {"TEE-01": 26000, "HOOD-01": 9500, "GIFT-01": 4200},
    "Oregon": {"TEE-01": 3100, "HOOD-01": 1200, "GIFT-01": 450},
    "Colorado": {"TEE-01": 4300, "HOOD-01": 1600, "GIFT-01": 620},
}

def totals(state, key):
    agg = {}
    for sku in SKUS:
        n = UNITS[state][sku["sku"]]
        for p in sku["parts"] + PER_ORDER:
            item = lib_by_name[p]
            cat = item[key]
            g = float(item["weight_g"]) * n
            pc = int(item["ca_plastic_components"] or 0) * n
            pg = float(item["ca_plastic_weight_g"] or 0) * n
            a = agg.setdefault(cat, [0.0, 0.0, 0])
            a[0] += g; a[1] += pg; a[2] += pc
    return agg

os.makedirs(os.path.join(SITE, "sample"), exist_ok=True)
ca_tot = totals("California", "ca_calrecycle_id")
with open(os.path.join(SITE, "sample", "sample-ca-supply-report.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Circular Action Material ID", "CalRecycle Material ID", "Reporting Category", "Total Weight (lbs)",
                "Weight - Plastic Components (lbs)", "# of Plastic Components"])
    ca_rows = []
    for cid, (g, pg, pc) in sorted(ca_tot.items()):
        c = ca_by_id[cid]
        plastic = c["plastic_cmc"] == "Plastic"
        row = [c["caa_material_id"], cid, c["reporting_category"], f"{g/453.592:.2f}",
               f"{pg/453.592:.2f}" if plastic else "", str(pc) if plastic else ""]
        w.writerow(row); ca_rows.append(row)
or_rows = []
for state in ("Oregon", "Colorado"):
    t = totals(state, "or_co_category_id")
    fn = f"sample-{state.lower()}-supply-report.csv"
    with open(os.path.join(SITE, "sample", fn), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Category #", "Material class", "Category", "Total Weight (lbs)"])
        for oid, (g, _, _) in sorted(t.items(), key=lambda x: int(x[0])):
            o = or_by_id[oid]
            row = [oid, o["material_class"], o["category"], f"{g/453.592:.2f}"]
            w.writerow(row)
            if state == "Oregon":
                or_rows.append(row)
with open(os.path.join(SITE, "sample", "sample-packaging-bom.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["SKU", "Product", "Component", "Library ID", "Weight (g)", "Weight source", "CA category", "OR/CO category #"])
    for sku in SKUS:
        for p in sku["parts"] + PER_ORDER:
            it = lib_by_name[p]
            w.writerow([sku["sku"], sku["name"], p, it["id"], it["weight_g"], it["weight_method"], it["ca_calrecycle_id"], it["or_co_category_id"]])

def table(headers, rows, num_from=3):
    h = "".join(f"<th{' class=num' if i >= num_from else ''}>{esc(x)}</th>" for i, x in enumerate(headers))
    b = "".join("<tr>" + "".join(f"<td{' class=num' if i >= num_from else ''}>{esc(x)}</td>" for i, x in enumerate(r)) + "</tr>" for r in rows)
    return f"<table><tr>{h}</tr>{b}</table>"

bom_rows = []
for sku in SKUS:
    for p in sku["parts"] + PER_ORDER:
        it = lib_by_name[p]
        bom_rows.append([sku["sku"], p, it["ca_calrecycle_id"], it["or_co_category_id"], it["weight_g"]])

page("sample-report.html", "Sample report",
     "What an EPR Kit report pack looks like, for a fictional apparel brand: California, Oregon and Colorado supply reports, packaging per product and methodology.",
     f"""
<div class="kicker">Sample report</div>
<h1>What you get, for a fictional brand.</h1>
<p class="lead">"Sample Apparel Co." is made up: three products, shipped to California, Oregon and Colorado in 2025. The categories, rules and packaging weights are real, built from the same library and checks we use for clients.</p>

<h2>1. Packaging per product</h2>
<p>Every product is mapped to the packaging it ships in. Each item carries its weight, where the weight came from, and its category in each state.</p>
{table(["SKU", "Component", "CA category", "OR/CO #", "Weight (g)"], bom_rows, num_from=3)}
<p class="note">Download: <a href="/sample/sample-packaging-bom.csv">sample-packaging-bom.csv</a></p>

<h2>2. California annual supply report</h2>
<p>Pounds per CalRecycle category, plus plastic component weight and count where the portal requires them. Columns match the portal's upload template.</p>
{table(["CAA ID", "CalRecycle ID", "Category", "Total lbs", "Plastic lbs", "# plastic"], ca_rows, num_from=3)}
<p class="note">Download: <a href="/sample/sample-ca-supply-report.csv">sample-ca-supply-report.csv</a></p>

<h2>3. Oregon annual supply report</h2>
{table(["#", "Material class", "Category", "Total lbs"], or_rows, num_from=3)}
<p class="note">Downloads: <a href="/sample/sample-oregon-supply-report.csv">Oregon</a> &middot; <a href="/sample/sample-colorado-supply-report.csv">Colorado</a></p>

<h2>4. Checks run before delivery</h2>
<ul class="check">
  <li>Every California category with plastic components has both plastic weight and plastic count</li>
  <li>Plastic component weight never exceeds total weight, or 50% of total weight in non-plastic categories</li>
  <li>Weights rounded to two decimals and counts to whole numbers, as the portal requires</li>
  <li>Every product shipped in the year is mapped to packaging; unmapped products are listed for you to confirm</li>
</ul>

<h2>5. Methodology (excerpt)</h2>
<div class="card"><p>Units shipped per state were taken from the brand's 2025 Shopify order export, using the shipping address state, and exclude returns and cancelled orders. Each product was mapped to its primary and shipping packaging. Weights for stock packaging come from the EPR Kit packaging library, calculated from dimensions and material specifications and checked against published supplier weights; custom packaging was weighed by the brand. Per-order items (shipping label and packing slip) were applied once per order. Category assignments follow CalRecycle's 2026 covered material categories and CAA's Oregon and Colorado category lists.</p></div>
""")

# ---------------------------------------------------------------- methodology
page("methodology.html", "Methodology",
     "How EPR Kit calculates packaging weights, maps them to state categories, and checks reports before you file.",
     f"""
<div class="kicker">Methodology</div>
<h1>How we get to the numbers.</h1>
<p class="lead">Every figure in an EPR Kit report can be traced back to a product, a packaging item, a weight source and a count of units shipped. This page explains each step.</p>

<h2>1. Units shipped per state</h2>
<p>We count units from your order exports (Shopify, Amazon, 3PL) for the full calendar year, by the state in the shipping address. Returns and cancelled orders are excluded, and wholesale shipments are flagged separately because some states treat business-to-business packaging differently.</p>

<h2>2. Packaging per product</h2>
<p>Each product is mapped to every packaging component it ships with: primary packaging (bottle, pouch, carton), shipping packaging (mailer or box), fill, tape, labels and inserts. Items used once per order, such as a shipping label, are counted per order rather than per unit.</p>

<h2>3. Weights</h2>
<p>Stock packaging comes from our library of {len(LIB)} common items. Weights are calculated from dimensions and material specifications, then checked against weights suppliers publish:</p>
<table>
  <tr><th>Check</th><th class="num">Calculated</th><th class="num">Published</th></tr>
  <tr><td>Poly mailer 10 x 13 in, 2.5 mil</td><td class="num">10.4 g</td><td class="num">about 11.8 g each, including carton share</td></tr>
  <tr><td>Reference C-flute box 575 x 385 x 225 mm</td><td class="num">658 g</td><td class="num">650 g</td></tr>
</table>
<p>Main assumptions: LDPE film at 0.92 g/cm&sup3;; 32 ECT C-flute board at 110 lb per 1,000 sq ft; kraft paper by basis weight (30 lb = 48.8 g/m&sup2;). Items whose blank size is estimated, such as mailer boxes and folding cartons, are marked approximate (around &plusmn;20%). Custom packaging is weighed by you or taken from your supplier's specification, and every weight in your report says which.</p>

<h2>4. Categories</h2>
<p>California reports use CalRecycle's 2026 list of 95 covered material categories. Oregon and Colorado use CAA's list of about 60 categories. Our data follows the Sustainable Packaging Data Council's attribute standard, so it can be reused for other programs. You can <a href="/lookup.html">look up any category</a>.</p>

<h2>5. Checks before delivery</h2>
<ul class="check">
  <li>Plastic component weight and count present wherever California requires them</li>
  <li>Plastic weight within total weight, and within 50% of total in non-plastic categories</li>
  <li>Decimal rules the California portal enforces</li>
  <li>Every shipped product mapped; anything unmapped listed for you to confirm</li>
  <li>A person reviews the full report before it reaches you</li>
</ul>

<h2>Open questions we flag rather than guess</h2>
<p>Some treatments aren't settled in public guidance, for example whether plastic tape on a cardboard box makes the box a "with plastic component" category in California. Where that's the case, your report says which treatment we used and why, so you can confirm it with the producer responsibility organization.</p>
""")

# ---------------------------------------------------------------- lookup
lookup_items = [{"t": "item", "n": r["name"], "ca": r["ca_calrecycle_id"], "or": r["or_co_category_id"], "w": r["weight_g"]} for r in LIB]
lookup_ca = [{"id": r["calrecycle_id"], "n": r["reporting_category"], "cls": r["material_class"], "rec": r["recyclable"], "pl": r["plastic_cmc"]} for r in CA]
lookup_or = [{"id": r["id"], "n": r["category"], "cls": r["material_class"]} for r in ORC]
page("lookup.html", "Category lookup",
     "Find the California (CalRecycle) and Oregon/Colorado EPR category for common packaging: mailers, boxes, pouches, bottles, tape and more.",
     """
<div class="kicker">Free tool</div>
<h1>Which category is it?</h1>
<p class="lead">Type a packaging item or material, such as "poly mailer", "kraft", "PET bottle" or "pouch". You'll see matching items from our packaging library with their California and Oregon/Colorado categories, and the matching official categories.</p>
<input id="q" type="search" placeholder="e.g. poly mailer, corrugated, PET, pouch" autofocus>
<div id="out"></div>
<p class="note">California: CalRecycle 2026 covered material categories (95). Oregon/Colorado: CAA reporting categories (60), from the Oregon program plan; confirm against the current list in the CAA portal. Category choice can depend on details such as attached plastic parts, so treat results as a starting point.</p>
<script>
const ITEMS=""" + json.dumps(lookup_items) + """;
const CA=""" + json.dumps(lookup_ca) + """;
const OR=""" + json.dumps(lookup_or) + """;
const caById=Object.fromEntries(CA.map(c=>[c.id,c])), orById=Object.fromEntries(OR.map(o=>[o.id,o]));
const e=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function run(){
  const q=document.getElementById('q').value.trim().toLowerCase(); const out=document.getElementById('out');
  if(q.length<2){out.innerHTML='';return;}
  const terms=q.split(/\\s+/), hit=s=>terms.every(t=>s.toLowerCase().includes(t));
  const items=ITEMS.filter(i=>hit(i.n)).slice(0,12);
  const ca=CA.filter(c=>hit(c.n+' '+c.cls+' '+c.id)).slice(0,15);
  const or=OR.filter(o=>hit(o.n+' '+o.cls)).slice(0,15);
  let h='';
  if(items.length) h+='<h2>Library items</h2><table><tr><th>Item</th><th>California</th><th>Oregon / Colorado</th><th class=num>Weight</th></tr>'+items.map(i=>`<tr><td>${e(i.n)}</td><td><code>${e(i.ca)}</code> ${e(caById[i.ca]?.n||'')}</td><td>#${e(i.or)} ${e(orById[i.or]?.n||'')}</td><td class=num>${e(i.w)} g</td></tr>`).join('')+'</table>';
  if(ca.length) h+='<h2>California categories</h2><table><tr><th>Code</th><th>Category</th><th>Recyclable</th></tr>'+ca.map(c=>`<tr><td><code>${e(c.id)}</code></td><td>${e(c.n)}</td><td>${e(c.rec)}</td></tr>`).join('')+'</table>';
  if(or.length) h+='<h2>Oregon / Colorado categories</h2><table><tr><th>#</th><th>Category</th><th>Class</th></tr>'+or.map(o=>`<tr><td>${e(o.id)}</td><td>${e(o.n)}</td><td>${e(o.cls)}</td></tr>`).join('')+'</table>';
  out.innerHTML=h||'<p class="note">No match. Try a material (PET, HDPE, kraft, glass) or a form (bottle, film, box).</p>';
}
document.getElementById('q').addEventListener('input',run);
</script>
""")

# ---------------------------------------------------------------- guides
page("guides/index.html", "Guides",
     "Plain-English guides to US packaging EPR reporting for consumer brands.",
     f"""
<div class="kicker">Guides</div>
<h1>Packaging EPR, in plain English.</h1>
<p class="lead">Short guides for brands that have to file. Each one lists its sources and the date it was last checked.</p>
<ul class="check">
  <li><a href="/guides/california-sb54-supply-report.html">How to file California's SB 54 annual supply report</a></li>
  <li><a href="/guides/oregon-epr-exemptions.html">Oregon packaging EPR: are you exempt?</a></li>
</ul>
<p>Want to know which states apply to you? Use the <a href="/#check">free obligation check</a>.</p>
""")

page("guides/california-sb54-supply-report.html", "How to file California's SB 54 annual supply report",
     "What California's SB 54 annual supply report asks for, how the portal validates it, and how to prepare your data before May 31.",
     f"""
<div class="kicker">Guide &middot; California</div>
<h1>How to file California's SB 54 annual supply report</h1>
<p class="note">Last checked {CHECKED}.</p>
<p class="lead">California's packaging program launches on January 1, 2027. Each year, producers report the packaging they supplied into the state through the Circular Action Alliance (CAA) producer portal. Here is what the report asks for and how to get it right.</p>

<h2>Who has to file</h2>
<p>Generally the brand owner of a product sold into California, or the importer or first distributor when the brand owner isn't in the US. Producers with less than $1 million in California gross sales can apply for a small producer exemption; it isn't automatic.</p>

<h2>What goes in the report</h2>
<table>
  <tr><th>Screen</th><th>What you enter</th></tr>
  <tr><td>Exemptions</td><td>Any CalRecycle exemptions you are seeking, such as specific materials or health and safety</td></tr>
  <tr><td>Supplied weights</td><td>For each of 95 categories: total weight in pounds, weight of plastic components in pounds, and number of plastic components</td></tr>
  <tr><td>Brands</td><td>Every brand covered by the report</td></tr>
  <tr><td>Affiliates</td><td>Parent companies or subsidiaries that also supply packaging into California: EIN, legal name, and whether their pounds are in your report</td></tr>
  <tr><td>Methodology</td><td>A written description of your data sources, calculation methods and assumptions</td></tr>
  <tr><td>Submission</td><td>Requires a signed California Interim State Addendum; only the primary contact or authorized representative can submit, and the report locks once submitted</td></tr>
</table>

<h2>The rules the portal enforces</h2>
<ul class="check">
  <li>Weights to at most two decimal places; component counts as whole numbers</li>
  <li>For any category "with plastic component" that has weight, plastic weight and plastic count are required</li>
  <li>Plastic component weight can't exceed total weight</li>
  <li>In non-plastic categories, plastic component weight can't exceed 50% of total weight</li>
</ul>

<h2>How the categories work</h2>
<p>Categories combine material, form and whether a non-plastic item has a plastic part. Cardboard alone is <code>25_PF9N</code>; cardboard with a plastic component is <code>25_PF9P</code>. Glass, metal, paper and wood come in these "with" and "without" pairs; plastics are split by resin and form, such as PET bottles or LDPE film. Items with two or more sides of 2 inches or less have their own "small" categories. <a href="/lookup.html">Look up a category</a>.</p>

<h2>Preparing your data</h2>
<ol>
  <li>Export a full calendar year of orders with ship-to states, from every channel.</li>
  <li>List the packaging for each product, including shipping packaging and per-order items like labels.</li>
  <li>Get a weight for each packaging item, from a scale, your supplier's spec, or a reference library.</li>
  <li>Assign each item a category, then multiply by units shipped into California.</li>
  <li>Check the totals against the rules above and write down how you did it.</li>
</ol>

<h2>Key dates</h2>
<ul>
  <li><b>January 1, 2027:</b> program launches; producers who aren't compliant can be barred from selling covered packaging in California</li>
  <li><b>Early 2027:</b> first fee invoices, with rates that depend partly on recyclability</li>
  <li><b>May 31, 2027:</b> annual supply report for 2026 data</li>
</ul>

<h2>Sources</h2>
<ul>
  <li>CAA, <a href="https://circularactionalliance.org/producer-guidance-ca">California producer guidance</a> and 2026 Annual Supply Report Preparation Workbook</li>
  <li>Holland &amp; Knight, <a href="https://www.hklaw.com/en/insights/publications/2026/05/californias-final-epr-regulations-now-in-effect">California's final EPR regulations now in effect</a></li>
  <li>DLA Piper, <a href="https://www.dlapiper.com/en-cl/insights/publications/2026/06/californias-epr-program-plan">California's EPR program plan</a></li>
</ul>
<p><a class="btn" href="/#pricing">Have us prepare it for you</a></p>
""")

page("guides/oregon-epr-exemptions.html", "Oregon packaging EPR: are you exempt?",
     "Oregon's small producer exemptions for packaging EPR: the $5 million revenue and one metric ton tests, associated producers, and what to file.",
     f"""
<div class="kicker">Guide &middot; Oregon</div>
<h1>Oregon packaging EPR: are you exempt?</h1>
<p class="note">Last checked {CHECKED}.</p>
<p class="lead">Oregon's program has been charging producers since July 2025, through the Circular Action Alliance (CAA). Small producers are exempt, but the tests have details that catch growing brands.</p>

<h2>The two exemption tests</h2>
<table>
  <tr><th>Test</th><th>Exempt if</th></tr>
  <tr><td>Revenue</td><td>Less than $5 million in global gross revenue</td></tr>
  <tr><td>Volume</td><td>Less than 1 metric ton (about 2,205 lbs) of covered packaging supplied into Oregon</td></tr>
</table>
<p>Meeting either test is generally enough. Oregon is the only state that counts in metric tons.</p>

<h2>The detail that catches brands: associated producers</h2>
<p>Oregon adds together the revenue and packaging of associated producers, such as a parent company and its subsidiaries, before applying the tests. Two small sister brands can be exempt on their own and obligated together.</p>

<h2>A quick way to estimate your tonnage</h2>
<p>Multiply your orders into Oregon by the packaging weight per order. Oregon is about 1.3% of the US population, so a brand shipping 150,000 US orders a year with 0.6 lbs of packaging each sends roughly 1,100 lbs into Oregon, under the 1 metric ton line. Use the <a href="/#check">free obligation check</a> for all states at once.</p>

<h2>If you are obligated</h2>
<ul>
  <li>Join CAA and report annually; reports are due May 31 for the prior year</li>
  <li>Report pounds in about 60 material categories (<a href="/lookup.html">look them up</a>)</li>
  <li>Producers with $5 million to $10 million in revenue pay a uniform annual fee rather than per-material fees</li>
  <li>Penalties can reach $25,000 per day</li>
</ul>

<h2>Sources</h2>
<ul>
  <li>EPR Atlas, <a href="https://epratlas.com/epr-de-minimis/">EPR de minimis thresholds by state</a></li>
  <li>Strategic Packaging Insights, <a href="https://www.strategicpackaginginsights.com/insights/us-state-packaging-epr/">US packaging EPR by state, 2026</a></li>
  <li>Resource Recycling, <a href="https://resource-recycling.com/?p=13423">Oregon fees for small producers</a></li>
  <li>EcoEnclose, <a href="https://ecoenclose.com/resources/epr-packaging-requirements">EPR packaging requirements</a></li>
</ul>
<p><a class="btn" href="/#pricing">Have us prepare it for you</a></p>
""")

# ---------------------------------------------------------------- changes log
page("changes.html", "Rule changes log",
     "Dated changes to the EPR rules, categories and data behind EPR Kit.",
     """
<div class="kicker">Rule changes log</div>
<h1>What changed, and when.</h1>
<p class="lead">EPR rules move quickly. We log changes to the rules, categories and reference data we use, with dates and sources.</p>
<table>
  <tr><th>Date</th><th>Change</th></tr>
  <tr><td>Nov 26, 2026</td><td>California 2026 covered material categories confirmed at 95 (IDs run to MAT-US-CA-0096; 0049 is unused), from CAA's 2026 Annual Supply Report Preparation Workbook.</td></tr>
  <tr><td>Nov 26, 2026</td><td>Sustainable Packaging Data Council template v2 adopted as our data standard: 47 attributes across product, component and sales levels, covering California, Colorado and Oregon.</td></tr>
  <tr><td>Nov 26, 2026</td><td>Packaging library published: 100 stock items with calculated weights, checked against published supplier weights.</td></tr>
  <tr><td>Aug 12, 2026</td><td>EU Packaging and Packaging Waste Regulation (PPWR) applies; national small-seller thresholds removed.</td></tr>
  <tr><td>Jun 1, 2026</td><td>California producer registration with CAA and 2023 baseline data due.</td></tr>
  <tr><td>May 1, 2026</td><td>California's final SB 54 regulations take effect.</td></tr>
</table>
""")

# ---------------------------------------------------------------- privacy and terms
page("privacy.html", "Privacy policy",
     "How EPR Kit collects, uses and protects your information.",
     f"""
<div class="kicker">Privacy policy</div>
<h1>Privacy policy</h1>
<p class="note">Effective {CHECKED}.</p>
<p>This policy explains how EPR Kit ("we") handles information. Questions: <a href="mailto:support@eprkit.com">support@eprkit.com</a> or by post to EPR Kit, 418 Broadway, Ste N, Albany, NY 12207.</p>
<h2>What we collect</h2>
<ul>
  <li><b>Contact details</b> you send us by email or form: name, company, email, phone.</li>
  <li><b>Client data</b> you share to have reports prepared: product lists, order exports, packaging specifications and related business records.</li>
  <li><b>Website usage:</b> the free tools on this site run in your browser; what you type into them is not sent to us.</li>
</ul>
<h2>How we use it</h2>
<p>To reply to you, to prepare your reports, and to run our business (billing, records). We don't sell personal information or client data, and we don't use client data to market to anyone.</p>
<h2>Sharing</h2>
<p>Only with service providers that help us operate (for example email, file storage and payment processing), under confidentiality obligations, or where the law requires it.</p>\n<p>Payments are processed by Stripe. Card and bank details go directly to Stripe and are never seen or stored by us; Stripe's own privacy policy applies to them.</p>
<h2>Retention and deletion</h2>
<p>Client data is kept while we work together and for as long as needed to support your filings and answer questions about them. Ask us at any time and we'll delete it, unless the law requires us to keep it.</p>
<h2>Security</h2>
<p>Client files are stored in access-controlled accounts with two-factor authentication, and access is limited to the people preparing your reports.</p>
<h2>Your choices</h2>
<p>You can ask to see, correct or delete your personal information by emailing us. California residents can make these requests under the CCPA.</p>
<h2>Changes</h2>
<p>We'll post any changes here with a new effective date.</p>
""")

page("terms.html", "Terms of service",
     "Terms for EPR Kit's packaging EPR report preparation service.",
     f"""
<div class="kicker">Terms of service</div>
<h1>Terms of service</h1>
<p class="note">Effective {CHECKED}.</p>
<p>These terms apply to the report preparation service provided by EPR Kit ("we") to the brand that engages us ("you"). A written order or email confirming your engagement sets out the price, states and delivery date.</p>
<h2>The service</h2>
<p>We prepare packaging EPR report data from the information you provide, and review it with you. You submit your own reports under your own account with the producer responsibility organization, and you're responsible for what you submit.</p>
<h2>Your information</h2>
<p>Reports depend on the accuracy and completeness of the data you send us, including order data and packaging details. We'll tell you about gaps or assumptions we notice, and our methodology states the assumptions used.</p>
<h2>Not legal advice</h2>
<p>We're not a law firm and don't give legal advice, including on whether you are the producer of a product. Regulatory information on this site is provided for general guidance and may change.</p>
<h2>Fees, deposit and refund</h2>
<p>Clients pay a $750 deposit to book their filing and the balance on delivery, both through Stripe's secure checkout. If we don't deliver your reports by the delivery date in your order (May 15, 2027 for the 2027 filing season), we refund your deposit in full. Fees owed to producer responsibility organizations are separate and paid by you.</p>
<h2>Confidentiality</h2>
<p>We keep your data confidential and use it only to provide the service, as described in our <a href="/privacy.html">privacy policy</a>.</p>
<h2>Liability</h2>
<p>To the extent the law allows, our total liability for any claim relating to the service is limited to the fees you paid us for that filing season, and we aren't liable for indirect or consequential losses, or for fees, fines or penalties assessed by regulators or producer responsibility organizations.</p>
<h2>Changes and contact</h2>
<p>We may update these terms; the version in effect when you engage us applies to that engagement. Questions: <a href="mailto:support@eprkit.com">support@eprkit.com</a> or by post to EPR Kit, 418 Broadway, Ste N, Albany, NY 12207.</p>
""")

# ---------------------------------------------------------------- sitemap
pages = ["", "guides/", "guides/california-sb54-supply-report.html", "guides/oregon-epr-exemptions.html", "lookup.html",
         "methodology.html", "sample-report.html", "changes.html", "privacy.html", "terms.html"]
with open(os.path.join(SITE, "sitemap.xml"), "w") as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
    for p in pages:
        f.write(f"  <url><loc>https://eprkit.com/{p}</loc><lastmod>2026-11-26</lastmod></url>\n")
    f.write("</urlset>\n")
with open(os.path.join(SITE, "robots.txt"), "w") as f:
    f.write("User-agent: *\nAllow: /\nSitemap: https://eprkit.com/sitemap.xml\n")
print("built", len(pages) - 1, "pages; CA sample rows:", len(ca_rows), "OR sample rows:", len(or_rows))
