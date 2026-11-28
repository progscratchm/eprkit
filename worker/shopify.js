// Shopify connection for EPR Kit clients (called from worker/index.js).
//
// A client opens their upload page, types their store address and clicks "Connect Shopify". Shopify asks
// them to approve read-only access. We then start two bulk exports (2026 orders and all products) and a
// cron job saves the raw results to the private bucket. scripts/shopify_to_csv.py turns them into the
// orders CSV the report builder reads and the product export prefill_packaging.py reads.
//
// Setup (once): create the app in Shopify's Dev Dashboard with custom distribution, then set
//   SHOPIFY_API_KEY     plain var or secret: the app's Client ID
//   SHOPIFY_API_SECRET  secret: the app's Client secret
// and see docs/shopify-setup.md for scopes, the redirect URL, bulk queries and protected customer data.
//
// GET  /api/shopify/install?shop=<store>.myshopify.com&code=<upload code>  → redirect to Shopify approval
// GET  /api/shopify/callback  (Shopify redirects here)                     → saves token, starts exports
// POST /api/shopify/webhooks  (app/uninstalled + the 3 privacy webhooks)   → verified, deletes the token
// cron (wrangler.jsonc triggers)                                            → saves finished exports to R2
//
// Bucket layout:
//   clients/<slug>/shopify/connection.json        { shop, token, scope, connected_at }   (never served)
//   clients/<slug>/shopify/<stamp>-orders.jsonl   raw bulk export
//   clients/<slug>/shopify/<stamp>-products.jsonl raw bulk export
//   shopify-jobs/<slug>.json                      pending bulk operations
//   shopify-shops/<shop>.json                     { slug }  (to find a client from a webhook)

import { checkCode, notifyText } from "./intake.js";

const API_VERSION = "2026-10";
// read_all_orders (orders older than 60 days) is granted separately by Shopify. Until it is, request only
// the two base scopes; add it with the SHOPIFY_SCOPES variable once approved.
const DEFAULT_SCOPES = "read_products,read_orders";
const SHOP_RE = /^[a-z0-9][a-z0-9-]*\.myshopify\.com$/;
const YEAR = 2026;

const ORDERS_QUERY = `{
  orders(query: "created_at:>=${YEAR}-01-01 AND created_at:<${YEAR + 1}-01-01") {
    edges { node {
      id name createdAt cancelledAt displayFinancialStatus test
      shippingAddress { provinceCode countryCodeV2 }
      lineItems { edges { node { id sku quantity currentQuantity requiresShipping } } }
    } }
  }
}`;

const PRODUCTS_QUERY = `{
  products {
    edges { node {
      id handle title productType vendor tags status
      variants { edges { node { id sku title selectedOptions { name value } } } }
    } }
  }
}`;

const enc = new TextEncoder();

async function hmac(secret, message) {
  const key = await crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return new Uint8Array(await crypto.subtle.sign("HMAC", key, enc.encode(message)));
}
const hex = (b) => [...b].map((x) => x.toString(16).padStart(2, "0")).join("");
const b64 = (b) => btoa(String.fromCharCode(...b));
function same(a, b) {
  if (a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}

function page(title, body, status = 200) {
  return new Response(`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>${title} · EPR Kit</title><link rel="stylesheet" href="/style.css"><link rel="icon" href="/favicon.svg"></head>
<body><main class="wrap" style="max-width:640px;padding:64px 20px"><h1>${title}</h1>${body}
<p><a href="/intake.html">Back to your upload page</a></p></main></body></html>`,
    { status, headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store", "x-robots-tag": "noindex" } });
}

// State carries the client slug and expires after 30 minutes; signed so it can't be forged.
async function makeState(env, slug) {
  const exp = Math.floor(Date.now() / 1000) + 1800;
  const nonce = hex(crypto.getRandomValues(new Uint8Array(8)));
  const body = `${slug}.${nonce}.${exp}`;
  return `${body}.${hex(await hmac(env.INTAKE_SECRET, "shopify-state:" + body)).slice(0, 32)}`;
}
async function readState(env, state) {
  const parts = String(state || "").split(".");
  if (parts.length !== 4) return null;
  const [slug, nonce, exp, sig] = parts;
  const want = hex(await hmac(env.INTAKE_SECRET, `shopify-state:${slug}.${nonce}.${exp}`)).slice(0, 32);
  if (!same(sig, want) || Number(exp) < Date.now() / 1000) return null;
  return slug;
}

// Shopify signs the query string of the OAuth redirect: all params except hmac, sorted, joined with &.
async function validQueryHmac(env, url) {
  const params = [...url.searchParams.entries()].filter(([k]) => k !== "hmac" && k !== "signature");
  params.sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));
  const message = params.map(([k, v]) => `${k}=${v}`).join("&");
  const want = hex(await hmac(env.SHOPIFY_API_SECRET, message));
  return same(url.searchParams.get("hmac") || "", want);
}

async function gql(shop, token, query, variables = {}) {
  const r = await fetch(`https://${shop}/admin/api/${API_VERSION}/graphql.json`, {
    method: "POST",
    headers: { "content-type": "application/json", "x-shopify-access-token": token },
    body: JSON.stringify({ query, variables }),
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok || j.errors) throw new Error(`Shopify ${r.status}: ${JSON.stringify(j.errors || j).slice(0, 300)}`);
  return j.data;
}

async function startBulk(shop, token, query) {
  const data = await gql(shop, token,
    `mutation run($q: String!) { bulkOperationRunQuery(query: $q) { bulkOperation { id status } userErrors { field message } } }`,
    { q: query });
  const res = data.bulkOperationRunQuery;
  if (res.userErrors && res.userErrors.length) throw new Error(res.userErrors.map((e) => e.message).join("; "));
  return res.bulkOperation.id;
}

function ready(env) {
  return env.UPLOADS && env.INTAKE_SECRET && env.SHOPIFY_API_KEY && env.SHOPIFY_API_SECRET;
}

export async function shopifyInstall(request, env) {
  if (!ready(env)) return page("Shopify connection isn't switched on yet", "<p>Please send your exports on the upload page instead, or email support@eprkit.com.</p>", 503);
  const url = new URL(request.url);
  const shop = (url.searchParams.get("shop") || "").trim().toLowerCase().replace(/^https?:\/\//, "").replace(/\/.*$/, "");
  const slug = await checkCode(url.searchParams.get("code"), env.INTAKE_SECRET);
  if (!slug) return page("That upload code didn't work", "<p>Check the code in your welcome email and try again.</p>", 403);
  if (!SHOP_RE.test(shop)) return page("That store address didn't work", "<p>Use your Shopify admin address, which ends in <code>.myshopify.com</code>. You'll find it in Shopify under Settings &gt; Domains.</p>", 400);
  const auth = new URL(`https://${shop}/admin/oauth/authorize`);
  auth.searchParams.set("client_id", env.SHOPIFY_API_KEY);
  auth.searchParams.set("scope", env.SHOPIFY_SCOPES || DEFAULT_SCOPES);
  auth.searchParams.set("redirect_uri", `${url.origin}/api/shopify/callback`);
  auth.searchParams.set("state", await makeState(env, slug));
  return Response.redirect(auth.toString(), 302);
}

export async function shopifyCallback(request, env, waitUntil) {
  if (!ready(env)) return page("Shopify connection isn't switched on yet", "<p>Please email support@eprkit.com.</p>", 503);
  const url = new URL(request.url);
  const shop = (url.searchParams.get("shop") || "").toLowerCase();
  const slug = await readState(env, url.searchParams.get("state"));
  if (!SHOP_RE.test(shop) || !slug || !(await validQueryHmac(env, url))) {
    return page("We couldn't confirm that connection", "<p>The link may have expired. Go back to your upload page and click Connect Shopify again.</p>", 403);
  }
  const tr = await fetch(`https://${shop}/admin/oauth/access_token`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ client_id: env.SHOPIFY_API_KEY, client_secret: env.SHOPIFY_API_SECRET, code: url.searchParams.get("code") }),
  });
  const tok = await tr.json().catch(() => ({}));
  if (!tr.ok || !tok.access_token) return page("Shopify didn't approve the connection", "<p>Please try again, or send your exports on the upload page.</p>", 502);

  const now = new Date().toISOString();
  await env.UPLOADS.put(`clients/${slug}/shopify/connection.json`,
    JSON.stringify({ shop, token: tok.access_token, scope: tok.scope, connected_at: now }));
  await env.UPLOADS.put(`shopify-shops/${shop}.json`, JSON.stringify({ slug }));

  let note = "";
  try {
    const job = { slug, shop, started_at: now, ops: {} };
    job.ops.orders = await startBulk(shop, tok.access_token, ORDERS_QUERY);
    job.ops.products = await startBulk(shop, tok.access_token, PRODUCTS_QUERY);
    await env.UPLOADS.put(`shopify-jobs/${slug}.json`, JSON.stringify(job));
  } catch (e) {
    note = String(e);
    console.log("bulk start failed", slug, note);
  }
  waitUntil(notifyText(env, `Shopify connected: ${slug}`,
    [`${slug} connected ${shop}.`, `Scopes: ${tok.scope}`, note ? `Export didn't start: ${note}` : `Exports started; the cron saves them to clients/${slug}/shopify/.`].join("\n")));

  return page("Your Shopify store is connected", `<p>Thanks. We're pulling your ${YEAR} orders and your product list now. Large stores can take an hour or two, and you don't need to keep this page open.</p>
<p>We read orders (SKU, quantity, ship-to state and country) and products only. We don't see customer names, emails or payment details, and we can't change anything in your store.</p>
<p>You can disconnect at any time in Shopify under Settings &gt; Apps. We'll email you once your packaging sheet is ready to check.</p>`);
}

// Webhooks: app/uninstalled, customers/data_request, customers/redact, shop/redact.
export async function shopifyWebhook(request, env) {
  if (!env.SHOPIFY_API_SECRET) return new Response("not configured", { status: 503 });
  const raw = await request.text();
  const want = b64(await hmac(env.SHOPIFY_API_SECRET, raw));
  if (!same(request.headers.get("x-shopify-hmac-sha256") || "", want)) return new Response("bad hmac", { status: 401 });
  const topic = request.headers.get("x-shopify-topic") || "";
  const shop = (request.headers.get("x-shopify-shop-domain") || "").toLowerCase();
  if (SHOP_RE.test(shop) && (topic === "app/uninstalled" || topic === "shop/redact")) {
    const map = await env.UPLOADS.get(`shopify-shops/${shop}.json`);
    if (map) {
      const { slug } = JSON.parse(await map.text());
      await env.UPLOADS.delete([`clients/${slug}/shopify/connection.json`, `shopify-jobs/${slug}.json`]);
      if (topic === "shop/redact") {
        const listed = await env.UPLOADS.list({ prefix: `clients/${slug}/shopify/` });
        if (listed.objects.length) await env.UPLOADS.delete(listed.objects.map((o) => o.key));
      }
      await notifyText(env, `Shopify ${topic}: ${slug}`, `${shop} sent ${topic}. Access token deleted${topic === "shop/redact" ? ", Shopify exports deleted" : ""}.`);
    }
  }
  // customers/data_request and customers/redact: we store no customer-level data (no names, emails or
  // addresses: only ship-to state and country per order), so there is nothing to return or erase.
  return new Response("ok");
}

async function saveExport(env, key, url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`download ${r.status}`);
  const len = Number(r.headers.get("content-length") || 0);
  if (len > 0) {
    const { readable, writable } = new FixedLengthStream(len);
    const [, put] = await Promise.all([r.body.pipeTo(writable), env.UPLOADS.put(key, readable)]);
    return put;
  }
  return env.UPLOADS.put(key, await r.arrayBuffer());
}

// Cron: check pending bulk exports and save the finished ones.
export async function shopifyCron(env) {
  if (!ready(env)) return;
  const jobs = await env.UPLOADS.list({ prefix: "shopify-jobs/" });
  for (const o of jobs.objects) {
    const job = JSON.parse(await (await env.UPLOADS.get(o.key)).text());
    const conn = await env.UPLOADS.get(`clients/${job.slug}/shopify/connection.json`);
    if (!conn) { await env.UPLOADS.delete(o.key); continue; }
    const { token } = JSON.parse(await conn.text());
    const stamp = job.started_at.replace(/[-:]/g, "").replace(/\.\d+Z$/, "Z");
    const messages = [];
    for (const [kind, id] of Object.entries(job.ops)) {
      try {
        const d = await gql(job.shop, token, `query($id: ID!) { node(id: $id) { ... on BulkOperation { status errorCode objectCount url } } }`, { id });
        const op = d.node || {};
        if (op.status === "COMPLETED") {
          if (op.url) await saveExport(env, `clients/${job.slug}/shopify/${stamp}-${kind}.jsonl`, op.url);
          messages.push(`${kind}: ${op.objectCount} objects saved${op.url ? "" : " (empty)"}`);
          delete job.ops[kind];
        } else if (["FAILED", "CANCELED", "EXPIRED"].includes(op.status)) {
          messages.push(`${kind}: ${op.status} ${op.errorCode || ""}`.trim());
          delete job.ops[kind];
        }
      } catch (e) {
        console.log("cron check failed", job.slug, kind, String(e));
      }
    }
    if (Object.keys(job.ops).length) await env.UPLOADS.put(o.key, JSON.stringify(job));
    else await env.UPLOADS.delete(o.key);
    if (messages.length) {
      await notifyText(env, `Shopify export: ${job.slug}`, [`${job.shop}`, ...messages, ``,
        `Convert: python3 scripts/shopify_to_csv.py clients/${job.slug}/shopify/`].join("\n"));
    }
  }
}
