# Shopify connection: setup and use

Clients connect their store from the upload page (eprkit.com/intake). We get read-only access, pull 2026
orders and all products with Shopify bulk exports, and the Worker's cron saves the raw files to the private
bucket. Code: `worker/shopify.js`. Converter: `scripts/shopify_to_csv.py`.

## One-time setup (Thibault)

1. **Create the app.** Sign in to Shopify's Dev Dashboard (dev.shopify.com) with a Partner account, then
   Apps > Create app. Name it "EPR Kit". You create the account and accept Shopify's terms yourself.
2. **Distribution: public (chosen Nov 27, 2026, permanent).** One app for every brand, installed by link,
   listable in the App Store later. Requires the one-time App Store registration ($19) and Shopify's review
   before stores outside our own dev stores can install it. (Earlier draft, kept for reference:) **custom.** Choose custom distribution, so the app isn't listed in the App Store.
   Shopify ties a custom-distribution app to the stores you generate install links for, so add each
   client's `*.myshopify.com` store when they book. **Check on the development store which install path
   works:** our Connect button (which runs the OAuth flow through `/api/shopify/install`) or Shopify's
   generated install link. If only the generated link works, the callback needs a small change to accept
   Shopify's managed install; note it and I'll adapt `worker/shopify.js`.
3. **URLs.**
   - App URL: `https://eprkit.com/intake`
   - Allowed redirection URL: `https://eprkit.com/api/shopify/callback`
4. **Access scopes:** `read_products`, `read_orders` in the app version. `read_all_orders` can't be added at
   creation; request it under Settings > Access requests (after choosing distribution). Once approved, add
   it to the app version's scopes and set the Cloudflare variable
   `SHOPIFY_SCOPES=read_products,read_orders,read_all_orders`.
   - `read_all_orders` lets us see orders older than 60 days. It has to be requested in the app's
     settings with a reason. Suggested reason: *"Packaging EPR reports cover a full calendar year of
     orders shipped into each state. We read SKU, quantity, ship-to state and order status for January
     to December of the reporting year."* Without it, only the last 60 days come through and the
     client sends a full-year order export instead.
5. **Protected customer data.** Ship-to state comes from the shipping address, which Shopify treats as
   protected customer data. Request access to the **address** field only (Level 2), with the same reason.
   We don't request name, email or phone. Fill in the data-protection questions honestly: data is
   encrypted at rest in R2, kept for the filing season, deleted on request or on uninstall.
6. **Bulk queries:** in the app's settings under access requests, enable bulk queries (granted at once).
7. **Webhooks:** subscribe `app/uninstalled`, and set the three privacy webhooks (`customers/data_request`,
   `customers/redact`, `shop/redact`) all to `https://eprkit.com/api/shopify/webhooks`.
8. **Secrets in Cloudflare** (Workers & Pages > eprkit > Settings > Variables and secrets):
   - `SHOPIFY_API_KEY` = the app's Client ID
   - `SHOPIFY_API_SECRET` = the app's Client secret (type: secret)
   Until both are set, the Connect button shows "isn't switched on yet" and clients use exports.
9. **Test on a development store** before the first client: install via the upload page with a test
   code, check the email alert, then run the converter on the files the cron saved.

## Each client

1. Generate the install link for their store in the app's distribution settings, and send their upload
   link as usual.
2. They click **Connect Shopify** on the upload page and approve.
3. Within about an hour (bigger stores longer) the cron saves `clients/<slug>/shopify/<stamp>-orders.jsonl`
   and `-products.jsonl`, and emails support@eprkit.com.
4. Download that folder, then:

       python3 scripts/shopify_to_csv.py <downloaded folder> --out clients/<slug>/input
       python3 scripts/prefill_packaging.py clients/<slug>/input/products_export.csv

5. Send the client `packaging-prefilled.csv` to check. When it's confirmed, save as `packaging.csv` and run
   `build_reports.py` as usual. Amazon, 3PL and wholesale orders still come in as uploads.

## Notes

- Orders are filtered on `created_at` in the shop's 2026 calendar year (UTC). Test orders and line items
  that don't require shipping are left out; quantity is Shopify's `currentQuantity` (after removals).
- We store the access token in the bucket next to the client's files. It's deleted on `app/uninstalled`,
  and `shop/redact` also deletes the Shopify exports. We store no customer-level data, so the two
  customer privacy webhooks have nothing to return or erase.
- Later: submitting to the App Store needs Shopify's review, the full privacy webhooks, and embedded-app
  requirements. Worth it once a few clients have used the custom app.

## Install flow (Nov 28, 2026)

The app uses Shopify-managed installation, because app-wide webhooks (including the mandatory privacy
webhooks) aren't allowed with the legacy install flow. Scopes come from `shopify/shopify.app.toml`, pushed
with `npx @shopify/cli@latest app deploy --allow-updates` from a folder holding that file. Our Connect
button still sends the brand to `/admin/oauth/authorize`; for a non-embedded app that's the standard way to
get the access token, and the scopes requested must match the ones in the config. Test this on the
development store before any client uses it.
