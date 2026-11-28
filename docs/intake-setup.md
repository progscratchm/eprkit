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

## 3. Make a client's upload code
```
INTAKE_SECRET='the same secret' python3 scripts/intake_code.py acme-apparel
```
It prints the code and a link, e.g. `https://eprkit.com/intake?code=acme-apparel.y6zyap4qake4`. Paste both
into email 1. The slug (`acme-apparel`) becomes the client's folder in the bucket.

## 4. Getting the files
R2 → `eprkit-intake` → `clients/<slug>/` → `orders/`, `products/`, `packaging/`, `sales/`, `other/`.
Download them into `clients/<slug>/input/` in this repo (that folder is git-ignored) and run the report builder.
Check the bucket each business day while clients are sending data; nothing notifies you of new uploads yet.

## Deleting a client's files
Select `clients/<slug>/` in R2 and delete it. The privacy policy promises this within 30 days of a request.

## Safety notes
- Codes can't be guessed: each is signed with INTAKE_SECRET. Changing the secret invalidates every code.
- One client's code only shows and writes that client's folder.
- Allowed: spreadsheets, CSV, PDF, images, zip; up to 95 MB per file.
