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
<p>Stock packaging comes from our library of {len(LIB)} common items. Shipping packaging (mailers, boxes, fill, tape) is calculated from dimensions and material specifications, then checked against weights suppliers publish:</p>
<table>
  <tr><th>Check</th><th class="num">Calculated</th><th class="num">Published</th></tr>
  <tr><td>Poly mailer 10 x 13 in, 2.5 mil</td><td class="num">10.4 g</td><td class="num">about 11.8 g each, including carton share</td></tr>
  <tr><td>Reference C-flute box 575 x 385 x 225 mm</td><td class="num">658 g</td><td class="num">650 g</td></tr>
</table>
<p>Main assumptions: LDPE film at 0.92 g/cm&sup3;; 32 ECT C-flute board at 110 lb per 1,000 sq ft; kraft paper by basis weight (30 lb = 48.8 g/m&sup2;). Items whose blank size is estimated, such as mailer boxes and folding cartons, are marked approximate (around &plusmn;20%). Bottles, jars, closures, pumps, tubes and pouches can't be calculated from dimensions, so their weights are the gram weights suppliers publish for a specific stock item, with the source named on every row. If your supplier's item differs, we use your supplier's spec or ask you to weigh a sample. Custom packaging is weighed by you or taken from your supplier's specification, and every weight in your report says which.</p>

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
  <tr><td>Nov 28, 2026</td><td>Packaging library extended to 145 items: serum dropper parts (glass pipette, collar, bulb), coffee bags with degassing valves, ceramic candle vessels, aluminium aerosol cans, twist-up stick containers, snack bar flow wraps and chocolate bar foil and sleeves.</td></tr>
  <tr><td>Nov 28, 2026</td><td>Packaging library extended to 133 items: glass and plastic bottles, jars, caps, pumps, tubes, pouches, tins and rigid gift boxes, with published supplier weights.</td></tr>
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
<p>Only with service providers that help us operate (for example email, file storage and payment processing), under confidentiality obligations, or where the law requires it.</p>\n<p>Files you upload at eprkit.com/intake are stored in a private Cloudflare R2 storage bucket that only the EPR Kit team can access, encrypted at rest, and deleted within 30 days of a written request.</p>\n<p>If you connect your Shopify store, we get read-only access to your orders and products. We save each order's number, date, SKUs, quantities, ship-to state and country, and status, and nothing about your customers: no names, emails, street addresses or payment details. The access key is stored in the same private bucket and deleted when you remove the app in Shopify.</p>\n<p>Payments are processed by Stripe. Card and bank details go directly to Stripe and are never seen or stored by us; Stripe's own privacy policy applies to them.</p>
<h2>Retention and deletion</h2>
<p>Client data is kept while we work together so we can support your filings and answer questions about them, and no longer than 3 years after the last report we deliver to you. We then delete it. If you remove the EPR Kit app from your Shopify store, we delete the access key straight away and the order and product data we pulled from your store within 48 hours of Shopify's deletion request. Ask us at any time and we'll delete your data within 30 days, unless the law requires us to keep it.</p>
<h2>Security</h2>
<p>Client files are stored in access-controlled accounts with two-factor authentication, encrypted in transit and at rest, and access is limited to the people preparing your reports. Access to our systems is logged. If a security incident affects your data, we will tell you within 72 hours of confirming it.</p>
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
<h2>Our correction promise</h2>
<p>If Circular Action Alliance or a state program questions or rejects data we prepared, we'll correct it and help you resubmit at no extra charge until that reporting year closes. If a fee or penalty is assessed against you because of an error in our work (and not because of incomplete or inaccurate information you gave us), we'll refund the fees you paid us for that filing season. This refund is the full extent of our responsibility for such errors.</p>
<h2>Confidentiality</h2>
<p>We keep your data confidential and use it only to provide the service, as described in our <a href="/privacy.html">privacy policy</a>.</p>
<h2>Liability</h2>
<p>Apart from the correction promise above, and to the extent the law allows, our total liability for any claim relating to the service is limited to the fees you paid us for that filing season, and we aren't liable for indirect or consequential losses, or for fees, fines or penalties assessed by regulators or producer responsibility organizations.</p>
<h2>Changes and contact</h2>
<p>We may update these terms; the version in effect when you engage us applies to that engagement. Questions: <a href="mailto:support@eprkit.com">support@eprkit.com</a> or by post to EPR Kit, 418 Broadway, Ste N, Albany, NY 12207.</p>
""")


# ---------------------------------------------------------------- client intake (not in sitemap, noindex)
INTAKE_BODY = """
<h1>Send us your files</h1>
<p class="lead">Upload your 2026 data here. Files go to a private storage folder that only the EPR Kit team can open, and are deleted on request.</p>

<form id="codeform" class="card intake-card" autocomplete="off">
  <label for="code"><b>Your upload code</b></label>
  <p class="note" style="margin:4px 0 10px">It's in your welcome email, and looks like <code>your-brand.abc123def456</code>.</p>
  <div class="row">
    <input id="code" name="code" type="text" spellcheck="false" required style="flex:1;min-width:0">
    <button class="btn" type="submit">Continue</button>
  </div>
  <p id="codeerr" class="err" role="alert"></p>
</form>

<div id="up" hidden>
  <p>Uploading for <b id="client"></b>.</p>
  <form id="shopform" class="card shop-card" autocomplete="off">
    <h3 style="margin:0 0 6px">Fastest: connect your Shopify store</h3>
    <p class="note" style="margin:0 0 10px">We pull your 2026 orders and your product list for you, so you can skip the order and product exports below. Read-only: we see SKUs, quantities and ship-to state, never customer names, emails or payment details. Disconnect any time in Shopify under Settings &gt; Apps.</p>
    <div class="row">
      <input id="shop" name="shop" type="text" spellcheck="false" placeholder="your-store.myshopify.com" required style="flex:1;min-width:0">
      <button class="btn" type="submit">Connect Shopify</button>
    </div>
    <p id="shoperr" class="err" role="alert"></p>
  </form>
  <p>Sell on Amazon, through a 3PL or wholesale too? Drop those files in the boxes below; send them as they are, we clean them.</p>
  <div class="drops">
    <div class="drop card" data-cat="orders"><h3>Order exports</h3><p class="note">Every channel for January 1 to December 31, 2026: Amazon, your 3PL, wholesale, any other store. Send the export exactly as your system gives it, CSV or Excel. We map the columns.</p></div>
    <div class="drop card" data-cat="products"><h3>Product list</h3><p class="note">Every SKU sold in 2026, including bundles and discontinued items.</p></div>
    <div class="drop card" data-cat="packaging"><h3>Packaging</h3><p class="note">Photos, spec sheets or supplier invoices for anything custom.</p></div>
    <div class="drop card" data-cat="sales"><h3>Retail and distributor sales</h3><p class="note">Distributor or retailer reports (UNFI, KeHE, Faire, store sell-through), plus your total 2026 revenue. By state if you have it. If not, we allocate and tell you how.</p></div>
    <div class="drop card" data-cat="other"><h3>Anything else</h3><p class="note">Notes, last year's filing, questions.</p></div>
  </div>
  <p class="note">Spreadsheets, CSV, PDF, photos or zip files, up to 95 MB each. Bigger than that? Zip it, or email <a href="mailto:support@eprkit.com">support@eprkit.com</a>.</p>
  <div id="progress" aria-live="polite"></div>
  <h2 style="margin-top:32px">Received so far</h2>
  <table class="tbl"><thead><tr><th>File</th><th>For</th><th class="n">Size</th><th>Received</th></tr></thead><tbody id="received"><tr><td colspan="4" class="note">Nothing yet.</td></tr></tbody></table>
  <p class="note">We check uploads every business day and email you if anything is missing or unclear.</p>
</div>

<style>
.intake-card{max-width:560px}.row{display:flex;gap:10px;flex-wrap:wrap}
#code,#shop{font:inherit;padding:12px 14px;border:1px solid #c9d4cd;border-radius:10px}
.shop-card{max-width:640px;border:2px solid #1d6b47}
.err{color:#a5412d;margin:10px 0 0;min-height:1em}
.drops{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px;margin:18px 0}
.drop{border:2px dashed #b9cbbf;cursor:pointer;transition:background .15s,border-color .15s;margin:0}
.drop h3{margin:0 0 6px;font-size:17px}.drop p{margin:0}
.drop.over,.drop:focus-visible{background:#eef6f1;border-color:#1d6b47;outline:none}
.bar{height:6px;background:#e3ebe6;border-radius:4px;overflow:hidden;margin:4px 0 12px}.bar>i{display:block;height:100%;background:#1d6b47;width:0}
.tbl td.n,.tbl th.n{text-align:right}
</style>
<script>
(function(){
  var code = "", cats = {orders:"Order exports",products:"Product list",packaging:"Packaging",sales:"Revenue and state sales",other:"Other"};
  var form = document.getElementById("codeform"), input = document.getElementById("code"), err = document.getElementById("codeerr");
  var q = new URLSearchParams(location.search).get("code"); if (q) input.value = q;
  function size(n){ return n > 1048576 ? (n/1048576).toFixed(1)+" MB" : Math.max(1, Math.round(n/1024))+" KB"; }
  function esc(s){ var d=document.createElement("div"); d.textContent=s; return d.innerHTML; }
  function load(){
    return fetch("/api/intake?code="+encodeURIComponent(code)).then(function(r){ return r.json(); }).then(function(d){
      if (!d.ok) throw new Error(d.error || "Something went wrong.");
      document.getElementById("client").textContent = d.client;
      var rows = d.files.map(function(f){ return "<tr><td>"+esc(f.name)+"</td><td>"+esc(cats[f.category]||f.category)+"</td><td class=n>"+size(f.size)+"</td><td>"+new Date(f.uploaded).toLocaleString()+"</td></tr>"; });
      document.getElementById("received").innerHTML = rows.join("") || '<tr><td colspan="4" class="note">Nothing yet.</td></tr>';
    });
  }
  document.getElementById("shopform").addEventListener("submit", function(e){
    e.preventDefault();
    var shop = document.getElementById("shop").value.trim().toLowerCase().replace(/^https?:\\/\\//, "").replace(/\\/.*$/, "");
    if (shop && shop.indexOf(".") < 0) shop += ".myshopify.com";
    if (!/^[a-z0-9][a-z0-9-]*\\.myshopify\\.com$/.test(shop)) {
      document.getElementById("shoperr").textContent = "Use your Shopify admin address, ending in .myshopify.com (Shopify: Settings > Domains).";
      return;
    }
    location.href = "/api/shopify/install?shop=" + encodeURIComponent(shop) + "&code=" + encodeURIComponent(code);
  });
  form.addEventListener("submit", function(e){
    e.preventDefault(); err.textContent = ""; code = input.value.trim();
    load().then(function(){ form.hidden = true; document.getElementById("up").hidden = false;
      history.replaceState(null, "", "/intake?code="+encodeURIComponent(code)); }).catch(function(x){ err.textContent = x.message; });
  });
  function send(file, cat){
    var row = document.createElement("div"); row.innerHTML = "<div>"+esc(file.name)+" <span class=note>uploading</span></div><div class=bar><i></i></div>";
    document.getElementById("progress").appendChild(row);
    var fd = new FormData(); fd.append("code", code); fd.append("category", cat); fd.append("file", file);
    var x = new XMLHttpRequest(); x.open("POST", "/api/intake");
    x.upload.onprogress = function(e){ if (e.lengthComputable) row.querySelector("i").style.width = (100*e.loaded/e.total)+"%"; };
    x.onload = function(){ var d = {}; try { d = JSON.parse(x.responseText); } catch(_){}
      row.querySelector(".note").textContent = d.ok ? "received" : (d.error || "failed, please try again");
      row.querySelector(".note").style.color = d.ok ? "#1d6b47" : "#a5412d"; if (d.ok) load(); };
    x.onerror = function(){ row.querySelector(".note").textContent = "failed, check your connection and try again"; };
    x.send(fd);
  }
  document.querySelectorAll(".drop").forEach(function(box){
    var pick = document.createElement("input"); pick.type = "file"; pick.multiple = true; pick.hidden = true;
    pick.setAttribute("aria-label", "Choose files: " + box.querySelector("h3").textContent);
    box.appendChild(pick); box.tabIndex = 0; box.setAttribute("role", "button");
    box.setAttribute("aria-label", "Upload " + box.querySelector("h3").textContent);
    function files(list){ Array.prototype.forEach.call(list, function(f){ send(f, box.dataset.cat); }); }
    box.addEventListener("click", function(e){ if (e.target !== pick) pick.click(); });
    box.addEventListener("keydown", function(e){ if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick.click(); } });
    pick.addEventListener("change", function(){ files(pick.files); pick.value = ""; });
    box.addEventListener("dragover", function(e){ e.preventDefault(); box.classList.add("over"); });
    box.addEventListener("dragleave", function(){ box.classList.remove("over"); });
    box.addEventListener("drop", function(e){ e.preventDefault(); box.classList.remove("over"); files(e.dataTransfer.files); });
  });
  if (q) form.requestSubmit();
})();
</script>
"""
page("intake.html", "Send us your files", "Private upload page for EPR Kit clients.", INTAKE_BODY)
with open(os.path.join(SITE, "intake.html")) as f:
    _h = f.read()
with open(os.path.join(SITE, "intake.html"), "w") as f:
    f.write(_h.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n<meta name="robots" content="noindex, nofollow">', 1))

# ---------------------------------------------------------------- sitemap
pages = ["", "guides/", "guides/california-sb54-supply-report.html", "guides/oregon-epr-exemptions.html", "lookup.html",
         "methodology.html", "sample-report.html", "changes.html", "privacy.html", "terms.html"]
with open(os.path.join(SITE, "sitemap.xml"), "w") as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
    for p in pages:
        f.write(f"  <url><loc>https://eprkit.com/{p}</loc><lastmod>2026-11-26</lastmod></url>\n")
    f.write("</urlset>\n")
with open(os.path.join(SITE, "robots.txt"), "w") as f:
    f.write("User-agent: *\nDisallow: /intake\nDisallow: /api/\nSitemap: https://eprkit.com/sitemap.xml\n")
print("built", len(pages) - 1, "pages; CA sample rows:", len(ca_rows), "OR sample rows:", len(or_rows))
