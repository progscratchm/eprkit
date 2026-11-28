// Client file intake for eprkit.com/intake (called from worker/index.js).
//
// Bindings (wrangler.jsonc, and secrets in the dashboard):
//   UPLOADS        R2 bucket (private), e.g. "eprkit-intake"
//   INTAKE_SECRET  encrypted environment variable, a long random string
// Optional upload alerts (sent through Resend's API; skipped if RESEND_API_KEY is not set):
//   RESEND_API_KEY encrypted environment variable
//   NOTIFY_TO      e.g. support@eprkit.com
//   NOTIFY_FROM    e.g. EPR Kit uploads <uploads@eprkit.com>  (domain verified in Resend)
//
// Each client gets an upload code "<slug>.<sig>", where sig is the first 12 characters of
// base32(HMAC-SHA256(INTAKE_SECRET, slug)), lowercase. scripts/intake_code.py makes codes.
// Files land at  clients/<slug>/<category>/<UTC timestamp>-<safe filename>  in the bucket.
//
// GET  /api/intake?code=...                     → { ok, client, files: [{name, category, size, uploaded}] }
// POST /api/intake  (multipart: code, category, file)  → { ok, name }

const MAX_BYTES = 95 * 1024 * 1024; // Pages Functions request bodies are capped at 100 MB
const CATEGORIES = ["orders", "products", "packaging", "sales", "other"];
const EXTENSIONS = ["csv", "tsv", "txt", "xlsx", "xls", "xlsm", "ods", "numbers", "json", "zip",
                    "pdf", "jpg", "jpeg", "png", "heic", "webp", "docx"];
const SLUG = /^[a-z0-9][a-z0-9-]{1,39}$/;

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", "cache-control": "no-store", "x-robots-tag": "noindex" },
  });
}

function base32(bytes) {
  const alphabet = "abcdefghijklmnopqrstuvwxyz234567";
  let bits = 0, value = 0, out = "";
  for (const b of bytes) {
    value = (value << 8) | b; bits += 8;
    while (bits >= 5) { out += alphabet[(value >>> (bits - 5)) & 31]; bits -= 5; }
  }
  if (bits > 0) out += alphabet[(value << (5 - bits)) & 31];
  return out;
}

function sameString(a, b) {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

export async function checkCode(code, secret) {
  if (!secret || typeof code !== "string") return null;
  const [slug, sig] = code.trim().toLowerCase().split(".");
  if (!slug || !sig || !SLUG.test(slug)) return null;
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret),
                                            { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const mac = new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(slug)));
  return sameString(base32(mac).slice(0, 12), sig) ? slug : null;
}

function safeName(name) {
  const base = String(name || "file").split(/[\\/]/).pop().normalize("NFKD");
  const cleaned = base.replace(/[^A-Za-z0-9._ -]+/g, "_").replace(/\s+/g, " ").trim().slice(-120);
  return cleaned.replace(/^\.+/, "") || "file";
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

export async function notifyText(env, subject, text) {
  if (!env.RESEND_API_KEY || !env.NOTIFY_TO || !env.NOTIFY_FROM) return;
  try {
    const r = await fetch(env.RESEND_API_URL || "https://api.resend.com/emails", {
      method: "POST",
      headers: { authorization: `Bearer ${env.RESEND_API_KEY}`, "content-type": "application/json" },
      body: JSON.stringify({ from: env.NOTIFY_FROM, to: env.NOTIFY_TO.split(",").map((s) => s.trim()).filter(Boolean),
                             subject, text, html: `<pre style="font:14px/1.5 ui-monospace,monospace">${escapeHtml(text)}</pre>` }),
    });
    if (!r.ok) console.log("alert failed", r.status, await r.text());
  } catch (e) {
    console.log("alert error", String(e));
  }
}

async function notify(env, { slug, category, name, size, key }) {
  if (!env.RESEND_API_KEY || !env.NOTIFY_TO || !env.NOTIFY_FROM) return;
  const human = size >= 1048576 ? `${(size / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(size / 1024))} KB`;
  const text = [
    `New upload from ${slug}`,
    ``,
    `File: ${name}`,
    `For: ${category}`,
    `Size: ${human}`,
    `Stored at: ${key}`,
    ``,
    `Open it in Cloudflare: R2 > eprkit-intake > clients/${slug}/${category}/`,
  ].join("\n");
  try {
    const r = await fetch(env.RESEND_API_URL || "https://api.resend.com/emails", {
      method: "POST",
      headers: { authorization: `Bearer ${env.RESEND_API_KEY}`, "content-type": "application/json" },
      body: JSON.stringify({
        from: env.NOTIFY_FROM,
        to: env.NOTIFY_TO.split(",").map((s) => s.trim()).filter(Boolean),
        subject: `Upload: ${slug} sent ${name}`,
        text,
        html: `<pre style="font:14px/1.5 ui-monospace,monospace">${escapeHtml(text)}</pre>`,
      }),
    });
    if (!r.ok) console.log("upload alert failed", r.status, await r.text());
  } catch (e) {
    console.log("upload alert error", String(e));
  }
}

export async function onRequestGet({ request, env }) {
  if (!env.UPLOADS || !env.INTAKE_SECRET) return json({ ok: false, error: "Uploads aren't switched on yet. Email your files to support@eprkit.com." }, 503);
  const code = new URL(request.url).searchParams.get("code");
  const slug = await checkCode(code, env.INTAKE_SECRET);
  if (!slug) return json({ ok: false, error: "That upload code isn't valid. Check the code in your welcome email." }, 403);
  const files = [];
  let cursor;
  do {
    const page = await env.UPLOADS.list({ prefix: `clients/${slug}/`, cursor, limit: 1000 });
    for (const o of page.objects) {
      const [, , category, stored] = o.key.split("/");
      files.push({ name: stored.replace(/^\d{8}T\d{6}Z-/, ""), category, size: o.size, uploaded: o.uploaded });
    }
    cursor = page.truncated ? page.cursor : undefined;
  } while (cursor);
  files.sort((a, b) => String(b.uploaded).localeCompare(String(a.uploaded)));
  return json({ ok: true, client: slug, files });
}

export async function onRequestPost({ request, env, waitUntil }) {
  if (!env.UPLOADS || !env.INTAKE_SECRET) return json({ ok: false, error: "Uploads aren't switched on yet. Email your files to support@eprkit.com." }, 503);
  const length = Number(request.headers.get("content-length") || 0);
  if (length > MAX_BYTES + 1024 * 1024) return json({ ok: false, error: "That file is over 95 MB. Zip it, or email us and we'll send another way to share it." }, 413);
  let form;
  try { form = await request.formData(); } catch { return json({ ok: false, error: "The upload didn't come through. Please try again." }, 400); }
  const slug = await checkCode(form.get("code"), env.INTAKE_SECRET);
  if (!slug) return json({ ok: false, error: "That upload code isn't valid. Check the code in your welcome email." }, 403);
  const category = CATEGORIES.includes(form.get("category")) ? form.get("category") : "other";
  const file = form.get("file");
  if (!file || typeof file === "string") return json({ ok: false, error: "No file was attached." }, 400);
  if (file.size > MAX_BYTES) return json({ ok: false, error: "That file is over 95 MB. Zip it, or email us and we'll send another way to share it." }, 413);
  const name = safeName(file.name);
  const ext = name.includes(".") ? name.split(".").pop().toLowerCase() : "";
  if (!EXTENSIONS.includes(ext)) return json({ ok: false, error: `We can't take .${ext || "?"} files here. Send spreadsheets, CSV, PDF, photos or a zip.` }, 415);
  const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d+/, "");
  const key = `clients/${slug}/${category}/${stamp}-${name}`;
  await env.UPLOADS.put(key, file.stream(), {
    httpMetadata: { contentType: file.type || "application/octet-stream", contentDisposition: "attachment" },
    customMetadata: { client: slug, category, original: String(file.name).slice(0, 200) },
  });
  const alert = notify(env, { slug, category, name, size: file.size, key });
  if (typeof waitUntil === "function") waitUntil(alert); else await alert;
  return json({ ok: true, name, category });
}

export async function onRequest() {
  return json({ ok: false, error: "Method not allowed" }, 405);
}
