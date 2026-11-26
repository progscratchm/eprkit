# EPR Kit: research summary

As of 26 Nov 2026.

## What it is
Software plus expert review that turns a DTC brand's Shopify/Amazon order data and packaging specs into ready-to-file US packaging EPR reports (Circular Action Alliance: CA, OR, CO, MN, MD, WA), later EU filings, California textiles (SB 707) and Spain's plastic packaging tax. Target: $5M to $50M brands. The brand files under its own CAA account; EPR Kit prepares the data. In California, "reporting contacts" can enter data and the brand's primary contact or authorized representative submits.

## Verdict so far
A real but small niche. 20+ Shopify EPR apps launched in 2026 with almost no reviews; cheap EU report apps are a commodity. US filing with expert review sells for $1K to $10K a year (Packledger: $1,188 self-file, $3,588 reviewed, $9,588 managed). Illustrative ceiling: 10 to 20% of 1,000 to 3,000 reachable US brands at about $500 a year is $50K to $300K a year, higher with review tiers and expansion.

## What brands file (all due May 31)
| State | Report | Data |
| --- | --- | --- |
| California | Annual supply report, plus source reduction report | 95 categories: total lbs, plastic component lbs, plastic component count; brands; affiliates; methodology |
| Oregon, Colorado | Annual supply report | Lbs across about 60 categories |
| Minnesota, Maryland, Washington | Simplified report | Lbs across 8 broad categories |

## Data model
Adopt the SPDC v2 attributes (`data/spdc-attributes.csv`): product level (from Shopify catalog), component level (supplier specs, the manual part) and sales level (orders). A library of common stock packaging (`data/packaging-library.csv`) removes most of the component-level work for DTC brands.

## Next
1. Microsoft 365 mailbox on eprkit.com; DNS on Cloudflare with email CNAMEs grey-cloud, DMARC, DKIM
2. Warm up the inbox; connect Apollo; fill contacts for 65 target brands
3. Deploy `site/` on Cloudflare Pages
4. First outreach batch on 1 Dec; 15 interviews; go/kill review around 19 Dec
