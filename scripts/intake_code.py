#!/usr/bin/env python3
"""Make a client's upload code and link for eprkit.com/intake.

Usage:  INTAKE_SECRET=... python3 scripts/intake_code.py acme-apparel

The secret must be the same value as the INTAKE_SECRET variable in the Cloudflare Pages project.
Keep it in your password manager; never commit it. The slug is lowercase letters, digits and hyphens,
2 to 40 characters, and becomes the client's folder name in the storage bucket.
"""
import base64, hashlib, hmac, os, re, sys

if len(sys.argv) != 2 or not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,39}", sys.argv[1]):
    sys.exit(__doc__)
secret = os.environ.get("INTAKE_SECRET")
if not secret:
    sys.exit("Set INTAKE_SECRET first (same value as in Cloudflare).")
slug = sys.argv[1]
sig = base64.b32encode(hmac.new(secret.encode(), slug.encode(), hashlib.sha256).digest()).decode().lower()[:12]
code = f"{slug}.{sig}"
print("Upload code:", code)
print("Link:       ", f"https://eprkit.com/intake?code={code}")
