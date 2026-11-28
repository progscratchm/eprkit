# Turning on the upload page (eprkit.com/intake)

The page and its function are deployed with the site. Until the two settings below exist, the page tells
clients to email their files instead. About 10 minutes, all in the Cloudflare dashboard.

## 1. Create the storage bucket
1. Cloudflare dashboard → **R2 Object Storage**. If asked, turn R2 on. The free tier covers 10 GB, far more
   than a season of client exports.
2. **Create bucket** → name `eprkit-intake`, location Automatic. Leave public access **off**.

## 2. Connect it to the site
1. **Workers & Pages** → the eprkit project → **Settings** → **Bindings** → **Add** → **R2 bucket**.
   Variable name `UPLOADS`, bucket `eprkit-intake`. Save.
2. Same page → **Variables and secrets** → **Add** → type **Secret**, name `INTAKE_SECRET`, value: a long
   random string. On a Mac: `openssl rand -base64 32`. Save it in your password manager too; you need it to
   make client codes.
3. **Deployments** → latest → **Retry deployment**, so the new settings take effect.

## 3. Upload alerts by email (optional, about 10 minutes)
Without this, check the bucket each business day. With it, support@eprkit.com gets an email for every upload.
Cloudflare can't send the email itself because eprkit.com's mail runs on Microsoft 365, so the alert goes
through Resend (free up to 100 emails a day). Its DNS records sit beside Microsoft's and don't change your mailbox.
1. Sign up at resend.com with support@eprkit.com. **Domains → Add domain** → `eprkit.com`.
2. Resend lists 3–4 DNS records (a DKIM TXT record at `resend._domainkey`, and an MX and SPF TXT record on
   the `send` subdomain). Add each in Cloudflare DNS exactly as shown, proxy off (grey cloud). Don't touch
   the existing Microsoft records. Wait for Resend to show **Verified**.
3. **API keys → Create** → permission "Sending access", domain eprkit.com. Copy the key (`re_...`).
4. In the eprkit Pages project → **Settings → Variables and secrets**, add:
   - `RESEND_API_KEY` (type Secret): the key
   - `NOTIFY_TO`: `support@eprkit.com`
   - `NOTIFY_FROM`: `EPR Kit uploads <uploads@eprkit.com>`
5. Retry the latest deployment. Upload a test file with your own code to check an alert arrives.

If Resend is down or a setting is missing, uploads still work; only the alert is skipped.

## 4. Make a client's upload code
```
INTAKE_SECRET='the same secret' python3 scripts/intake_code.py acme-apparel
```
It prints the code and a link, e.g. `https://eprkit.com/intake?code=acme-apparel.y6zyap4qake4`. Paste both
into email 1. The slug (`acme-apparel`) becomes the client's folder in the bucket.

## 5. Getting the files
R2 → `eprkit-intake` → `clients/<slug>/` → `orders/`, `products/`, `packaging/`, `sales/`, `other/`.
Download them into `clients/<slug>/input/` in this repo (that folder is git-ignored) and run the report builder.
If alerts aren't set up, check the bucket each business day while clients are sending data.

## Deleting a client's files
Select `clients/<slug>/` in R2 and delete it. The privacy policy promises this within 30 days of a request.

## Safety notes
- Codes can't be guessed: each is signed with INTAKE_SECRET. Changing the secret invalidates every code.
- One client's code only shows and writes that client's folder.
- Allowed: spreadsheets, CSV, PDF, images, zip; up to 95 MB per file.
