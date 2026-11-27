import json
W,H=1280,720
CSS='''*{box-sizing:border-box}body{margin:0;width:1280px;height:720px;background:#fbfcfa;font-family:Inter,sans-serif;color:#13241b;overflow:hidden}
.frame{position:absolute;inset:0;padding:64px 88px;display:flex;flex-direction:column}
.top{display:flex;justify-content:space-between;align-items:center;font-weight:700;font-size:22px}.top span{color:#1d6b47}
.step{color:#1d6b47;font-weight:700;letter-spacing:.08em;text-transform:uppercase;font-size:18px;margin-top:40px}
h1{font-family:"Inter Display",Inter,sans-serif;font-size:56px;line-height:1.08;letter-spacing:-.02em;margin:14px 0 18px;font-weight:700}
p{font-size:24px;color:#5a6a61;margin:0 0 24px;max-width:1000px;line-height:1.4}
table{border-collapse:collapse;font-size:21px;background:#fff;border:1px solid #dfe6e1}
th,td{padding:12px 18px;border-bottom:1px solid #dfe6e1;text-align:left}th{font-size:15px;color:#5a6a61;text-transform:uppercase;letter-spacing:.05em}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}code{font-family:"DejaVu Sans Mono";font-size:18px;background:#eef3ef;padding:2px 6px;border-radius:4px}
.row{display:flex;gap:24px}.box{flex:1;background:#fff;border:1px solid #dfe6e1;border-radius:14px;padding:26px}
.big{font-size:64px;font-weight:700;color:#1d6b47;font-family:"Inter Display",Inter}
.chk{font-size:26px;margin:12px 0;display:flex;gap:16px;align-items:center}.chk b{display:inline-grid;place-items:center;width:38px;height:38px;border-radius:50%;background:#1d6b47;color:#fff;font-size:22px;flex:none}
.arrow{font-size:40px;color:#1d6b47;align-self:center}
.dark{background:#13241b;color:#fff}.dark p{color:#d6e2db}.dark .top span{color:#bfe3cf}
.btn{display:inline-block;background:#1d6b47;color:#fff;padding:16px 26px;border-radius:10px;font-weight:700;font-size:24px}
.foot{margin-top:auto;font-size:16px;color:#8a978f}'''
TOP='<div class="top"><div>EPR<span>Kit</span></div><div style="font-weight:500;font-size:16px;color:#8a978f">eprkit.com</div></div>'
S=[]
S.append(("title",5,f'''<div class="frame dark">{TOP}<div style="margin:auto 0">
<h1 style="font-size:72px">How we build your<br>packaging EPR report</h1><p style="font-size:28px">From your order exports to upload-ready files, in five steps.</p></div></div>'''))
S.append(("ask",8,f'''<div class="frame">{TOP}<div class="step">What the states ask for</div><h1>Pounds of packaging,<br>by material, by state.</h1>
<div class="row"><div class="box"><div class="big">95</div><p style="margin:0">California categories, plus plastic component weight and count</p></div>
<div class="box"><div class="big">60</div><p style="margin:0">Oregon and Colorado categories</p></div>
<div class="box"><div class="big">8</div><p style="margin:0">broad categories in Minnesota, Maryland and Washington</p></div></div>
<div class="foot">Annual reports due May 31.</div></div>'''))
S.append(("s1",8,f'''<div class="frame">{TOP}<div class="step">Step 1 &middot; You send exports</div><h1>A full year of orders, by ship-to state.</h1>
<p>From Shopify, Amazon and your 3PL. About 30 minutes of your time.</p>
<table><tr><th>Order</th><th>SKU</th><th class=n>Units</th><th>Ship-to state</th></tr>
<tr><td>#10482</td><td>TEE-01</td><td class=n>1</td><td>CA</td></tr><tr><td>#10483</td><td>GIFT-01</td><td class=n>1</td><td>OR</td></tr>
<tr><td>#10484</td><td>HOOD-01</td><td class=n>1</td><td>CO</td></tr><tr><td>#10485</td><td>TEE-01</td><td class=n>1</td><td>CA</td></tr></table>
<div class="foot">Illustrative data for a fictional brand.</div></div>'''))
S.append(("s2",9,f'''<div class="frame">{TOP}<div class="step">Step 2 &middot; We map your packaging</div><h1>Every product, every component.</h1>
<p>Stock items come from our library of 100 packaging items with checked weights. You only measure what's custom.</p>
<table><tr><th>TEE-01 ships in</th><th class=n>Weight</th><th>California</th><th>Oregon / Colorado</th></tr>
<tr><td>Self-seal poly bag 9&times;12 in, 1.5 mil</td><td class=n>5.2 g</td><td><code>25_P16P</code></td><td>#53 LDPE film</td></tr>
<tr><td>Poly mailer 10&times;13 in, 2.5 mil</td><td class=n>10.4 g</td><td><code>25_P16P</code></td><td>#53 LDPE film</td></tr>
<tr><td>Shipping label 4&times;6 in</td><td class=n>1.5 g</td><td><code>25_PF12N</code></td><td>#24 Other paper</td></tr></table></div>'''))
S.append(("s3",9,f'''<div class="frame">{TOP}<div class="step">Step 3 &middot; We calculate by state</div><h1>Units shipped &times; packaging weight.</h1>
<div class="row" style="align-items:center"><div class="box"><p style="margin:0 0 8px">California, LDPE film</p>
<div style="font-size:26px;line-height:1.7">26,000 tees &times; 2 items<br>9,500 hoodies &times; 2 items</div></div><div class="arrow">&rarr;</div>
<div class="box"><p style="margin:0 0 6px"><code>25_P16P</code></p><div class="big">1,585.35 lbs</div><p style="margin:0">71,000 plastic components</p></div></div>
<div class="foot">Illustrative figures from our sample report for a fictional brand.</div></div>'''))
S.append(("s4",8,f'''<div class="frame">{TOP}<div class="step">Step 4 &middot; We check before you upload</div><h1>The same rules the portal enforces.</h1>
<div class="chk"><b>&#10003;</b>Plastic weight and count wherever California requires them</div>
<div class="chk"><b>&#10003;</b>Plastic weight never above total weight</div>
<div class="chk"><b>&#10003;</b>Under 50% plastic in non-plastic categories</div>
<div class="chk"><b>&#10003;</b>Two decimals for weights, whole numbers for counts</div></div>'''))
S.append(("s5",8,f'''<div class="frame">{TOP}<div class="step">Step 5 &middot; You review and file</div><h1>Upload-ready files, plus the working.</h1>
<div class="row"><div class="box"><p style="margin:0;color:#13241b;font-size:24px">&#128196; California supply report</p></div><div class="box"><p style="margin:0;color:#13241b;font-size:24px">&#128196; Oregon and Colorado reports</p></div></div>
<div class="row" style="margin-top:22px"><div class="box"><p style="margin:0;color:#13241b;font-size:24px">&#128203; Packaging per product, with weight sources</p></div><div class="box"><p style="margin:0;color:#13241b;font-size:24px">&#9998; Written methodology</p></div></div>
<p style="margin-top:28px">A person walks you through the numbers. You submit under your own account.</p></div>'''))
S.append(("cta",7,f'''<div class="frame dark">{TOP}<div style="margin:auto 0"><h1 style="font-size:64px">Every state you owe.<br>One fixed price.<br>Delivered before May 31.</h1>
<div class="btn">Book your 2027 filing at eprkit.com</div></div></div>'''))
json.dump({"css":CSS,"scenes":S},open("scenes.json","w"))
print(sum(s[1] for s in S),"s of stills")
