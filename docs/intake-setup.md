# Turning on the upload page (eprkit.com/intake)

eprkit.com is a Cloudflare **Worker** with static assets (Workers & Pages → `eprkit`), built from this repo on
every push with `npx wrangler deploy`. `wrangler.jsonc` serves `site/` and sends only `/api/*` to
`worker/index.js`, which handles uploads in `worker/intake.js`. Until the bucket and secret below exist, the
upload page tells clients to email their files instead.

## 1. Storage bucket (once)
1. Cloudflare → **R2 Object Storage** → **Add R2 subscription to my account** ($0; only billed past 10 GB).
2. **Create bucket** `eprkit-intake`, location Automatic, public access **off**.
3. `wrangler.jsonc` connects it as `UPLOADS` (done).

## 2. Secrets (once)
Workers & Pages → `eprkit` → **Settings → Variables and secrets → Add**, type **Secret**:
- `INTAKE_SECRET`: a long random string (`openssl rand -base64 32`). Keep a copy in your password manager.
- `RESEND_API_KEY`: from resend.com → API keys (sending access, domain updates.eprkit.com).

`NOTIFY_TO` and `NOTIFY_FROM` are already in `wrangler.jsonc`. Secrets survive later deploys.

## 3. Upload alerts (Resend)
Sending domain `updates.eprkit.com` is added in Resend, with its three DNS records (DKIM TXT
`resend._domainkey.updates`, CNAMEs `rsend.updates` and `send.updates`, DNS only) in Cloudflare.
Alerts go from `uploads@updates.eprkit.com` to support@eprkit.com. If Resend is down or the key is
missing, uploads still work; only the alert is skipped.

## 4. Make a client's upload code
```
INTAKE_SECRET='the same secret' python3 scripts/intake_code.py acme-apparel
```
It prints the code and a link, e.g. `https://eprkit.com/intake?code=acme-apparel.y6zyap4qake4`. Paste both
into email 1. The slug (`acme-apparel`) becomes the client's folder in the bucket.

## 5. Getting the files
R2 → `eprkit-intake` → `clients/<slug>/` → `orders/`, `products/`, `packaging/`, `sales/`, `other/`.
Download them into `clients/<slug>/input/` in this repo (git-ignored) and run the report builder.

## Deleting a client's files
Select `clients/<slug>/` in R2 and delete it. The privacy policy promises this within 30 days of a request.

## Local testing
`npx wrangler dev` runs the site and the upload API locally with a simulated bucket. Pass test secrets with
`--var INTAKE_SECRET:test`.

## Safety notes
- Codes can't be guessed: each is signed with INTAKE_SECRET. Changing the secret invalidates every code.
- One client's code only shows and writes that client's folder.
- Allowed: spreadsheets, CSV, PDF, images, zip; up to 95 MB per file.
