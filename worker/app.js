// Embedded Shopify app (App Store path). Shopify opens https://eprkit.com/app inside the Shopify admin.
//
// Flow (no OAuth redirects, per App Store rules 2.3.x):
//   1. Shopify installs the app (managed install, scopes from shopify/shopify.app.toml) and opens /app in the admin.
//   2. The page loads App Bridge, gets a session token (shopify.idToken()) and calls GET /api/app/status.
//   3. The server verifies the session token, exchanges it for an expiring offline access token (token exchange),
//      saves the connection, starts the 2026 order and product exports the first time, and returns the status.
//   4. "Book my 2027 reports" calls POST /api/app/book, which creates a one-time $1,500 charge through the
//      Shopify Billing API and returns Shopify's confirmation URL; the page opens it at the top level.
//
// The connection is stored in the same place as /api/shopify/* (clients/<slug>/shopify/connection.json), so the
// cron in worker/shopify.js saves the exports for both paths.

import { checkCode, notifyText } from "./intake.js";
import { saveConnection, freshToken, startBulk, ORDERS_QUERY, PRODUCTS_QUERY, gql, sec } from "./shopify.js";

const PRICE = { amount: 1500, currencyCode: "USD" };
const PURCHASE_NAME = "EPR Kit: 2027 packaging EPR reports (all states you owe)";
const enc = new TextEncoder();

const b64url = (s) => Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(s.length / 4) * 4, "=")), (c) => c.charCodeAt(0));

// Verify a Shopify session token (HS256 JWT signed with the app secret). Returns the shop domain or null.
export async function verifySessionToken(env, token) {
  try { return await verifyInner(env, token); } catch { return null; }
}

async function verifyInner(env, token) {
  const parts = String(token || "").split(".");
  if (parts.length !== 3) return null;
  const key = await crypto.subtle.importKey("raw", enc.encode(sec(env.SHOPIFY_API_SECRET)), { name: "HMAC", hash: "SHA-256" }, false, ["verify"]);
  const ok = await crypto.subtle.verify("HMAC", key, b64url(parts[2]), enc.encode(`${parts[0]}.${parts[1]}`));
  if (!ok) return null;
  let p;
  try { p = JSON.parse(new TextDecoder().decode(b64url(parts[1]))); } catch { return null; }
  const now = Math.floor(Date.now() / 1000);
  if (p.aud !== sec(env.SHOPIFY_API_KEY)) return null;
  if (typeof p.exp !== "number" || p.exp + 5 < now) return null;
  if (typeof p.nbf === "number" && p.nbf - 5 > now) return null;
  const dest = String(p.dest || "").replace(/^https:\/\//, "").toLowerCase();
  if (!/^[a-z0-9][a-z0-9-]*\.myshopify\.com$/.test(dest)) return null;
  if (!String(p.iss || "").startsWith(`https://${dest}`)) return null;
  return dest;
}

function json(body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json", "cache-control": "no-store" } });
}

function slugFor(shop) {
  return ("s-" + shop.replace(/\.myshopify\.com$/, "")).replace(/[^a-z0-9-]/g, "-").slice(0, 40);
}

async function uploadCode(env, slug) {
  const key = await crypto.subtle.importKey("raw", enc.encode(sec(env.INTAKE_SECRET)), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const mac = new Uint8Array(await crypto.subtle.sign("HMAC", key, enc.encode(slug)));
  const a = "abcdefghijklmnopqrstuvwxyz234567"; let bits = 0, v = 0, out = "";
  for (const b of mac) { v = (v << 8) | b; bits += 8; while (bits >= 5) { out += a[(v >>> (bits - 5)) & 31]; bits -= 5; } }
  return `${slug}.${out.slice(0, 12)}`;
}

// Session token → connection (exchanging for an offline token when we don't have a working one).
async function connect(request, env, waitUntil) {
  const auth = request.headers.get("authorization") || "";
  const shop = await verifySessionToken(env, auth.replace(/^Bearer\s+/i, ""));
  if (!shop) return { error: json({ ok: false, error: "Session expired. Reload the app." }, 401) };

  const map = await env.UPLOADS.get(`shopify-shops/${shop}.json`);
  const slug = map ? JSON.parse(await map.text()).slug : slugFor(shop);
  if (!map) await env.UPLOADS.put(`shopify-shops/${shop}.json`, JSON.stringify({ slug }));

  const stored = await env.UPLOADS.get(`clients/${slug}/shopify/connection.json`);
  let conn = stored ? JSON.parse(await stored.text()) : null;
  let token = null;
  if (conn && conn.refresh_token) {
    try { token = await freshToken(env, slug, conn); } catch (e) { console.log("refresh failed, exchanging again", String(e)); }
  }
  let firstConnect = false;
  if (!token) {
    const r = await fetch(`https://${shop}/admin/oauth/access_token`, {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded", accept: "application/json" },
      body: new URLSearchParams({
        client_id: sec(env.SHOPIFY_API_KEY), client_secret: sec(env.SHOPIFY_API_SECRET),
        grant_type: "urn:ietf:params:oauth:grant-type:token-exchange",
        subject_token: auth.replace(/^Bearer\s+/i, ""),
        subject_token_type: "urn:ietf:params:oauth:token-type:id_token",
        requested_token_type: "urn:shopify:params:oauth:token-type:offline-access-token",
        expiring: "1",
      }),
    });
    const tok = await r.json().catch(() => ({}));
    if (!r.ok || !tok.access_token) {
      console.log("token exchange failed", r.status, JSON.stringify(tok).slice(0, 300));
      return { error: json({ ok: false, error: "We couldn't connect to your store. Reload the app, or email support@eprkit.com." }, 502) };
    }
    firstConnect = !conn;
    conn = await saveConnection(env, slug, shop, tok, (conn && conn.connected_at) || new Date().toISOString());
    token = conn.token;
  }

  // First time (or no export yet): start the 2026 order and product exports.
  const status = await readStatus(env, slug);
  const job = await env.UPLOADS.get(`shopify-jobs/${slug}.json`);
  if (!status.exported_at && !job) {
    try {
      const j = { slug, shop, started_at: new Date().toISOString(), ops: {} };
      j.ops.orders = await startBulk(shop, token, ORDERS_QUERY);
      j.ops.products = await startBulk(shop, token, PRODUCTS_QUERY);
      await env.UPLOADS.put(`shopify-jobs/${slug}.json`, JSON.stringify(j));
    } catch (e) {
      console.log("bulk start failed", slug, String(e));
    }
  }
  if (firstConnect) waitUntil(notifyText(env, `App installed: ${slug}`, `${shop} opened EPR Kit in Shopify. Exports started for ${slug}.`));
  return { shop, slug, token };
}

async function readStatus(env, slug) {
  const s = await env.UPLOADS.get(`clients/${slug}/shopify/status.json`);
  return s ? JSON.parse(await s.text()) : {};
}

async function purchases(shop, token) {
  const d = await gql(shop, token, `{
    shop { name plan { partnerDevelopment } }
    currentAppInstallation { app { handle } oneTimePurchases(first: 10, reverse: true) { nodes { id name status createdAt price { amount } } } }
  }`);
  const nodes = d.currentAppInstallation.oneTimePurchases.nodes || [];
  return {
    shopName: d.shop.name,
    dev: !!(d.shop.plan && d.shop.plan.partnerDevelopment),
    handle: d.currentAppInstallation.app.handle,
    booked: nodes.find((n) => n.status === "ACTIVE") || null,
    pending: nodes.find((n) => n.status === "PENDING") || null,
  };
}

export async function appStatus(request, env, waitUntil) {
  if (!env.UPLOADS || !env.SHOPIFY_API_SECRET) return json({ ok: false, error: "Not configured" }, 503);
  const c = await connect(request, env, waitUntil);
  if (c.error) return c.error;
  const status = await readStatus(env, c.slug);
  const job = await env.UPLOADS.get(`shopify-jobs/${c.slug}.json`);
  let p = {};
  try { p = await purchases(c.shop, c.token); } catch (e) { console.log("purchase lookup failed", String(e)); }
  if (p.booked && !status.booked_at) {
    status.booked_at = p.booked.createdAt;
    await env.UPLOADS.put(`clients/${c.slug}/shopify/status.json`, JSON.stringify(status));
    waitUntil(notifyText(env, `Booked through Shopify: ${c.slug}`, `${c.shop} (${p.shopName}) paid $${p.booked.price.amount} for 2027 reports on ${p.booked.createdAt}.${p.dev ? " (development store test charge)" : ""}`));
  }
  return json({
    ok: true,
    shop: c.shop,
    shopName: p.shopName || c.shop,
    export: status.exported_at
      ? { state: "done", at: status.exported_at, orders: status.orders, products: status.products }
      : { state: job ? "running" : "not_started" },
    booked: p.booked ? { at: p.booked.createdAt } : null,
    uploadUrl: `https://eprkit.com/intake?code=${encodeURIComponent(await uploadCode(env, c.slug))}`,
    price: PRICE.amount,
  });
}

export async function appBook(request, env, waitUntil) {
  if (!env.UPLOADS || !env.SHOPIFY_API_SECRET) return json({ ok: false, error: "Not configured" }, 503);
  const c = await connect(request, env, waitUntil);
  if (c.error) return c.error;
  const p = await purchases(c.shop, c.token);
  if (p.booked) return json({ ok: true, already: true });
  const store = c.shop.replace(/\.myshopify\.com$/, "");
  const returnUrl = `https://admin.shopify.com/store/${store}/apps/${p.handle}`;
  const d = await gql(c.shop, c.token, `mutation buy($name: String!, $price: MoneyInput!, $returnUrl: URL!, $test: Boolean) {
      appPurchaseOneTimeCreate(name: $name, price: $price, returnUrl: $returnUrl, test: $test) {
        confirmationUrl userErrors { field message } } }`,
    { name: PURCHASE_NAME, price: PRICE, returnUrl, test: p.dev });
  const res = d.appPurchaseOneTimeCreate;
  if (res.userErrors && res.userErrors.length) return json({ ok: false, error: res.userErrors.map((e) => e.message).join("; ") }, 400);
  return json({ ok: true, confirmationUrl: res.confirmationUrl });
}

export function appPage(env) {
  const key = sec(env.SHOPIFY_API_KEY);
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="shopify-api-key" content="${key}">
<script src="https://cdn.shopify.com/shopifycloud/app-bridge.js"></script>
<title>EPR Kit</title>
<style>
:root{--ink:#13241b;--green:#1d6b47;--mint:#e9f5ee;--line:#e3e8e5;--muted:#5b6b62}
*{box-sizing:border-box}body{margin:0;font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif;color:var(--ink);background:#f6f7f6}
main{max-width:860px;margin:0 auto;padding:24px 20px 48px}
h1{font-size:20px;margin:0 0 4px}h2{font-size:16px;margin:0 0 8px}.muted{color:var(--muted)}
.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:20px;margin:16px 0}
ol.steps{list-style:none;margin:0;padding:0}ol.steps li{display:flex;gap:12px;padding:12px 0;border-top:1px solid var(--line)}ol.steps li:first-child{border-top:0}
.dot{flex:0 0 26px;height:26px;border-radius:50%;display:grid;place-items:center;font-weight:600;background:#eef1ef;color:var(--muted)}
.done .dot{background:var(--green);color:#fff}.now .dot{background:var(--mint);color:var(--green);outline:2px solid var(--green)}
button,a.btn{font:inherit;font-weight:600;border:0;border-radius:10px;padding:10px 16px;background:var(--ink);color:#fff;cursor:pointer;text-decoration:none;display:inline-block}
a.ghost{background:#fff;color:var(--ink);border:1px solid var(--line)}button[disabled]{opacity:.5;cursor:default}
.price{font-size:28px;font-weight:700}.err{color:#a5412d}.ok{color:var(--green);font-weight:600}
ul.check{padding-left:18px;margin:8px 0}
</style></head><body><main>
<h1>EPR Kit</h1>
<p class="muted" id="sub">Packaging EPR reports for every US state you owe, prepared from your store data and checked by a person.</p>

<div class="card"><h2>Your 2027 filing</h2>
<ol class="steps">
 <li id="s1"><span class="dot">1</span><div><b>Store data</b><div class="muted" id="s1t">Connecting…</div></div></li>
 <li id="s2"><span class="dot">2</span><div><b>Book your reports</b><div class="muted" id="s2t">One fixed price for every state you owe.</div></div></li>
 <li id="s3"><span class="dot">3</span><div><b>Check your packaging sheet</b><div class="muted">We pre-fill it from your products. You confirm each line and send photos or specs for anything custom.</div><div id="s3a" style="margin-top:8px"></div></div></li>
 <li id="s4"><span class="dot">4</span><div><b>Review call and delivery</b><div class="muted">Upload-ready reports for California, Oregon, Colorado, Minnesota, Maryland and Washington as needed, delivered by May 15, 2027. You submit them under your own account.</div></div></li>
</ol></div>

<div class="card" id="buy"><h2>Book your 2027 reports</h2>
<div class="price">$1,500 <span class="muted" style="font-size:14px;font-weight:400">one-time, billed by Shopify</span></div>
<ul class="check">
 <li>Obligation check for all seven EPR states</li>
 <li>Packaging mapped for every product, with weights and their sources</li>
 <li>Upload-ready reports, California plastic counts, written methodology</li>
 <li>Review call before you file</li>
 <li>We fix it free if Circular Action Alliance or a state questions anything we prepared</li>
 <li>Full refund if your reports aren't delivered by May 15, 2027</li>
</ul>
<button id="bookbtn" disabled>Book my 2027 reports</button>
<p class="muted">Shopify's charge page calls this purchase non-refundable. Our refund promise still applies: if we miss May 15, 2027, EPR Kit refunds you in full through Shopify.</p>
<p class="muted" id="booknote">Not sure you owe anything? <a href="https://eprkit.com/#check" target="_blank" rel="noopener">Run the free check</a> or email <a href="mailto:support@eprkit.com">support@eprkit.com</a> first.</p>
<p class="err" id="err" role="alert"></p>
</div>

<p class="muted">Read-only access: we read orders (SKU, quantity, ship-to state and country) and products. We never see payment details and can't change your store. <a href="https://eprkit.com/privacy.html" target="_blank" rel="noopener">Privacy</a> · <a href="https://eprkit.com/terms.html" target="_blank" rel="noopener">Terms</a> · <a href="mailto:support@eprkit.com">support@eprkit.com</a></p>
</main>
<script>
(function(){
  function $(id){ return document.getElementById(id); }
  async function call(path, opts){
    var token = await shopify.idToken();
    var r = await fetch(path, Object.assign({ headers: { authorization: "Bearer " + token } }, opts || {}));
    var d = await r.json().catch(function(){ return { ok:false, error:"Something went wrong." }; });
    if (!d.ok) throw new Error(d.error || "Something went wrong.");
    return d;
  }
  function n(c, w){ return c + " " + w + (c === 1 ? "" : "s"); }
  function set(id, cls){ var el=$(id); el.classList.remove("done","now"); if (cls) el.classList.add(cls); }
  async function load(){
    try {
      var d = await call("/api/app/status");
      $("sub").textContent = "Packaging EPR reports for " + d.shopName + ", for every US state you owe.";
      if (d.export.state === "done") { set("s1","done"); $("s1t").textContent = "Connected. " + n(d.export.orders,"order") + " and " + n(d.export.products,"product") + " from 2026 received."; }
      else { set("s1","now"); $("s1t").textContent = "Connected. We're pulling your 2026 orders and products; large stores can take an hour. You can close this page."; setTimeout(load, 30000); }
      if (d.booked) {
        set("s2","done"); $("s2t").innerHTML = '<span class="ok">Booked on ' + new Date(d.booked.at).toLocaleDateString() + ".</span> We'll email you within one business day.";
        set("s3","now"); $("s3a").innerHTML = '<a class="btn ghost" target="_blank" rel="noopener" href="' + d.uploadUrl + '">Open your upload page</a>';
        $("buy").hidden = true;
      } else { set("s2","now"); $("bookbtn").disabled = false; }
    } catch (e) { $("s1t").textContent = e.message; $("s1t").className = "err"; }
  }
  $("bookbtn").addEventListener("click", async function(){
    this.disabled = true; $("err").textContent = "";
    try {
      var d = await call("/api/app/book", { method: "POST" });
      if (d.already) return load();
      window.open(d.confirmationUrl, "_top");
    } catch (e) { $("err").textContent = e.message; this.disabled = false; }
  });
  load();
})();
</script></body></html>`;
  return new Response(html, {
    headers: {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "no-store",
      "content-security-policy": "frame-ancestors https://*.myshopify.com https://admin.shopify.com;",
    },
  });
}
